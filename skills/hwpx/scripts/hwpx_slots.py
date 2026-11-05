#!/usr/bin/env python3
"""List editable text slots in a HWPX template.

The output is intended to be filled back with scripts/edit_hwpx.py --slot-json.
It deliberately excludes container paragraphs that only wrap tables, pictures,
or text boxes, because editing them creates overlapping text.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from lxml import etree

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
}


def _parse_section(path: Path) -> etree._Element:
    with zipfile.ZipFile(path, "r") as zf:
        return etree.parse(BytesIO(zf.read("Contents/section0.xml"))).getroot()


def _node_text(node: etree._Element) -> str:
    return "".join(node.itertext())


def _direct_text(paragraph: etree._Element) -> str:
    return "".join(
        _node_text(t)
        for t in paragraph.xpath("./hp:run/hp:t", namespaces=NS)
    )


def _all_text(scope: etree._Element) -> str:
    return "".join(scope.xpath(".//hp:t//text()", namespaces=NS))


def _normalized_len(text: str) -> int:
    return len("".join(text.split()))


def _preview(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _has_nested_paragraph(paragraph: etree._Element) -> bool:
    return bool(paragraph.xpath(".//hp:p", namespaces=NS))


def _paragraph_slots(root: etree._Element, preview_len: int) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for index, paragraph in enumerate(root.xpath(".//hp:p", namespaces=NS)):
        text = _direct_text(paragraph)
        if not text.strip():
            continue
        if _has_nested_paragraph(paragraph):
            continue
        slots.append(
            {
                "key": f"p:{index}",
                "kind": "paragraph",
                "index": index,
                "max_chars": _normalized_len(text),
                "text_len": len(text),
                "text_len_nospace": _normalized_len(text),
                "preview": _preview(text, preview_len),
            }
        )
    return slots


def owned_cells(table: etree._Element) -> list[etree._Element]:
    """Each cell belongs to its nearest table, never to an enclosing table too."""
    return [cell for cell in table.xpath(".//hp:tc", namespaces=NS)
            if cell.xpath("ancestor::hp:tbl[1]", namespaces=NS)[0] is table]


def cell_edit_block_reason(cell: etree._Element) -> str | None:
    # A whole-cell rewrite intentionally clears text in that cell. Never include
    # a nested table, drawing, field/control, or a second sub-list in that scope.
    for run in cell.xpath(".//hp:run", namespaces=NS):
        if any(child.tag != f"{{{NS['hp']}}}t" for child in run):
            return "중첩 표/그림/상자/제어 요소를 포함한 복합 셀"
    if any(node.getparent() is not cell for node in cell.xpath(".//hp:subList", namespaces=NS)):
        return "내부 문단 컨테이너를 포함한 복합 셀"
    return None


def _cell_slots(
    root: etree._Element,
    preview_len: int,
    include_empty: bool,
    blocked: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for table_index, table in enumerate(root.xpath(".//hp:tbl", namespaces=NS)):
        seen: dict[tuple[str, str], int] = {}
        for cell in owned_cells(table):
            addr = cell.find("hp:cellAddr", namespaces=NS)
            if addr is None:
                continue
            row = addr.get("rowAddr", "0")
            col = addr.get("colAddr", "0")
            occurrence = seen.get((row, col), 0)
            seen[(row, col)] = occurrence + 1
            text = _all_text(cell)
            if not include_empty and not text.strip():
                continue
            key = f"cell:{table_index}:{row}:{col}"
            if occurrence:
                key += f":{occurrence}"
            reason = cell_edit_block_reason(cell)
            if reason or occurrence:
                blocked.append({"key": key, "reason": reason or "중복 좌표 셀은 전체 치환할 수 없음",
                                "next_action": "바깥 제목의 실제 p: 슬롯 또는 내부 셀을 선택하세요"})
                continue
            slots.append(
                {
                    "key": key,
                    "kind": "cell",
                    "table": table_index,
                    "row": int(row),
                    "col": int(col),
                    "occurrence": occurrence,
                    "max_chars": _normalized_len(text),
                    "text_len": len(text),
                    "text_len_nospace": _normalized_len(text),
                    "empty": not bool(text.strip()),
                    "preview": _preview(text, preview_len),
                }
            )
    return slots


def collect_slots(
    path: Path,
    preview_len: int = 80,
    include_empty_cells: bool = True,
) -> dict[str, Any]:
    root = _parse_section(path)
    paragraph_slots = _paragraph_slots(root, preview_len)
    blocked: list[dict[str, Any]] = []
    cell_slots = _cell_slots(root, preview_len, include_empty_cells, blocked)
    with zipfile.ZipFile(path) as archive:
        sections = [name for name in archive.namelist()
                    if name.startswith("Contents/section") and name.endswith(".xml")]

    return {
        "source": str(path),
        "version": 1,
        "usage": "Fill with scripts/edit_hwpx.py template.hwpx -o out.hwpx --slot-json values.json",
        "slots": paragraph_slots + cell_slots,
        "blocked_slots": blocked,
        "edit_scope": {"section": "Contents/section0.xml", "section_count": len(sections)},
        "warnings": (["여러 섹션 중 section0만 편집합니다. 다른 섹션은 보존되며 별도 확인이 필요합니다."]
                     if len(sections) > 1 else []),
    }


# Explicit cell shading and base-derived semantic checks.
HH = 'http://www.hancom.co.kr/hwpml/2011/head'
HC = 'http://www.hancom.co.kr/hwpml/2011/core'
CELL_KEY = re.compile(r'cell:(0|[1-9]\d*):(0|[1-9]\d*):(0|[1-9]\d*)')
NO_FILL = '무색'
FILL_NOTICE = 'cell_fills는 borderFillIDRef 단위로 복사하므로 배경뿐 아니라 테두리 등도 함께 옮겨집니다.'
_UNSET = object()


def cell_map(root):
    """Map nearest-table-owned cells; ambiguous duplicate addresses are refused."""
    cells, duplicates = {}, set()
    for index, table in enumerate(root.xpath('.//hp:tbl', namespaces=NS)):
        for cell in owned_cells(table):
            addr = cell.find('hp:cellAddr', NS)
            if addr is None:
                continue
            key = f"cell:{index}:{addr.get('rowAddr', '0')}:{addr.get('colAddr', '0')}"
            if key in cells:
                duplicates.add(key)
            cells[key] = cell
    return cells, duplicates


def validate_cell_fills(root, fills):
    if not isinstance(fills, dict):
        raise ValueError('cell_fills는 대상 칸→같은 표 원본 칸 JSON 객체여야 합니다')
    cells, duplicates = cell_map(root)
    for target, source in fills.items():
        for key in (target, source):
            if not isinstance(key, str) or not CELL_KEY.fullmatch(key) or key not in cells:
                raise ValueError('cell_fills: 베이스에 없는 칸 키: ' + str(key))
            if key in duplicates:
                raise ValueError('cell_fills: 중복 좌표 칸은 사용할 수 없습니다: ' + key)
        if target.split(':')[1] != source.split(':')[1]:
            raise ValueError(f'cell_fills: 같은 표의 칸만 복사할 수 있습니다: {target} <- {source}')
    return cells


def apply_cell_fills(root, fills):
    cells = validate_cell_fills(root, fills)
    # Snapshot first: A<-B, B<-A is a swap of BASE references, not a cascade.
    refs = {target: cells[source].get('borderFillIDRef') for target, source in fills.items()}
    for target, ref in refs.items():
        if ref is None:
            cells[target].attrib.pop('borderFillIDRef', None)
        else:
            cells[target].set('borderFillIDRef', ref)
    return len(refs)


def background_colors(path):
    with zipfile.ZipFile(path) as archive:
        if 'Contents/header.xml' not in archive.namelist():
            return {}
        header = etree.fromstring(archive.read('Contents/header.xml'),
                                  etree.XMLParser(resolve_entities=False))
    colors = {}
    for fill in header.findall(f'.//{{{HH}}}borderFill'):
        brush = fill.find(f'{{{HC}}}fillBrush/{{{HC}}}winBrush')
        color = brush.get('faceColor') if brush is not None else None
        colors[fill.get('id')] = color.upper() if color and color.lower() != 'none' else NO_FILL
    return colors


def border_signatures(path):
    """borderFill id → its definition without the fill, to compare borders only."""
    with zipfile.ZipFile(path) as archive:
        if 'Contents/header.xml' not in archive.namelist():
            return {}
        header = etree.fromstring(archive.read('Contents/header.xml'),
                                  etree.XMLParser(resolve_entities=False))
    signatures = {}
    for fill in header.findall(f'.//{{{HH}}}borderFill'):
        bare = copy.deepcopy(fill)
        bare.attrib.pop('id', None)
        for brush in bare.findall(f'{{{HC}}}fillBrush'):
            bare.remove(brush)
        # Exclusive c14n: the removed fill's namespace must not make borders differ.
        signatures[fill.get('id')] = etree.tostring(bare, method='c14n', exclusive=True)
    return signatures


def normalized_text(cell):
    return ' '.join(_all_text(cell).split())


def background(cell, colors):
    ref = cell.get('borderFillIDRef')
    if ref is not None and ref not in colors:
        raise ValueError('header.xml에 없는 borderFillIDRef: ' + ref)
    return colors.get(ref, NO_FILL)


def shading_report(base: Path, values, fills=_UNSET, ack=_UNSET, *, output: Path | None = None):
    """Compare planned or actual cells with the SAME base-derived expectations.

    Empty text has no semantic color. A multi-color table is eligible only if
    every nonempty normalized base text has exactly one background. A new text
    on several backgrounds is reported without an expected color; old texts
    always retain their base expectation. Suggested donors share the target's
    borders.
    """
    fills = {} if fills is _UNSET else fills
    ack = [] if ack is _UNSET else ack
    root = _parse_section(base)
    original = validate_cell_fills(root, fills)
    _, duplicates = cell_map(root)
    if (not isinstance(ack, list) or any(not isinstance(key, str) or not CELL_KEY.fullmatch(key)
            or key not in original or key in duplicates for key in ack) or len(set(ack)) != len(ack)):
        raise ValueError('shading_ack는 베이스에 존재하는 고유한 칸 키 목록이어야 합니다')
    planned = copy.deepcopy(root)
    # Use the real editor's paragraph/cell semantics, including multi-paragraph
    # cells; never concatenate independently guessed alias values.
    from edit_hwpx import _targets_from_slots, set_cells, set_paragraphs
    paragraphs, cells = _targets_from_slots(values)
    set_cells(planned, cells)
    set_paragraphs(planned, paragraphs, {})
    apply_cell_fills(planned, fills)
    planned_cells, _ = cell_map(planned)
    touched = {key.split(':')[1] for key in original
               if normalized_text(original[key]) != normalized_text(planned_cells[key])
               or original[key].get('borderFillIDRef') != planned_cells[key].get('borderFillIDRef')}
    final_cells = cell_map(_parse_section(output))[0] if output is not None else planned_cells
    base_colors = background_colors(base)
    final_colors = background_colors(output) if output is not None else base_colors
    borders = border_signatures(base)

    def donor_for(target, color, members):
        # cell_fills copies the whole borderFill: only a donor whose borders
        # equal the target's may be suggested (11. 3.: the first white cell
        # was the diagonal header, which would have drawn a slash).
        want = borders.get(original[target].get('borderFillIDRef'))
        return next((key for key, cell in members.items() if background(cell, base_colors) == color
                     and borders.get(cell.get('borderFillIDRef')) == want), None)
    tables = defaultdict(dict)
    for key, cell in original.items():
        tables[key.split(':')[1]][key] = cell
    issues, checked, skipped = [], [], {}
    for table, members in tables.items():
        if table not in touched:
            skipped[table] = '편집 없는 표'
            continue
        if any(key in duplicates for key in members):
            skipped[table] = '중복 좌표가 있는 표'
            continue
        palette = {background(cell, base_colors) for cell in members.values()}
        if len(palette) < 2:
            skipped[table] = '배경이 한 가지뿐인 표'
            continue
        expectations = defaultdict(set)
        for cell in members.values():
            text = normalized_text(cell)
            if text:
                expectations[text].add(background(cell, base_colors))
        if any(len(colors) != 1 for colors in expectations.values()):
            skipped[table] = '베이스 글자→배경이 일관되지 않은 표'
            continue
        checked.append(table)
        groups = defaultdict(list)
        for key in members:
            if key not in final_cells:
                raise ValueError('음영 검사 결과 문서에 칸이 없습니다: ' + key)
            text = normalized_text(final_cells[key])
            if text:
                groups[text].append((key, background(final_cells[key], final_colors)))
        for text, group in groups.items():
            if text not in expectations:
                # A text new to the table has no base meaning. If it lands on
                # several backgrounds, the teacher decides which one is right;
                # a majority vote picked gray for 정상수업 on 11. 3.
                colors = sorted({color for _, color in group})
                if len(colors) < 2:
                    continue
                for key, color in group:
                    donors = {other: donor_for(key, other, members) for other in colors}
                    issues.append(dict(key=key, text=text, current=color, expected=None,
                                       acknowledged=key in ack,
                                       problem=f'{key}: 새 글자 {text!r}이 표 안에서 서로 다른 배경({", ".join(colors)})에 놓임 — 현재 {color}',
                                       how_to_fix='교사에게 이 글자 칸의 배경 뜻을 확인해 한 배경으로 맞추세요. cell_fills 원본 후보(테두리 같은 칸): '
                                                  + json.dumps(donors, ensure_ascii=False)
                                                  + '; 지금 음영을 유지하면 shading_ack에 이 칸 키를 넣고 승인받으세요. ' + FILL_NOTICE))
                continue
            expected = next(iter(expectations[text]))
            for key, color in group:
                if color == expected:
                    continue
                donor = donor_for(key, expected, members)
                example = ('cell_fills: ' + json.dumps({key: donor}, ensure_ascii=False)
                           if donor else '테두리가 같은 기대 배경 원본 칸이 없어 cell_fills 후보를 만들지 않음 — 한글에서 직접 바꾸세요')
                issues.append(dict(key=key, text=text, current=color, expected=expected,
                                   acknowledged=key in ack,
                                   problem=f'{key}: 글자 {text!r}, 현재 배경 {color}, 기대 배경 {expected}',
                                   how_to_fix=example + '; 또는 교사가 현재 음영 유지를 명시하면 shading_ack에 이 칸 키를 넣고 승인받으세요. ' + FILL_NOTICE))
    return dict(issues=issues, checked_tables=checked, skipped_tables=skipped,
                cell_fills=fills, shading_ack=ack, notice=FILL_NOTICE if fills else '')


def main() -> int:
    parser = argparse.ArgumentParser(description="HWPX 편집 가능 텍스트 슬롯 추출")
    parser.add_argument("input", type=Path, help="템플릿 .hwpx")
    parser.add_argument("--output", "-o", type=Path, help="슬롯 JSON 저장 경로")
    parser.add_argument("--preview-len", type=int, default=80)
    parser.add_argument(
        "--no-empty-cells",
        action="store_true",
        help="빈 표 셀 슬롯을 출력하지 않음",
    )
    parser.add_argument("--pretty", action="store_true", help="표 형태 요약 출력")
    args = parser.parse_args()

    profile = collect_slots(
        args.input,
        args.preview_len,
        include_empty_cells=not args.no_empty_cells,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"WROTE: {args.output}")
        print(f"  slots: {len(profile['slots'])}")
        return 0

    if args.pretty:
        for slot in profile["slots"]:
            print(
                f"{slot['key']}\t{slot['kind']}\tmax={slot['max_chars']}\t"
                f"empty={slot.get('empty', False)}\t{slot['preview']}"
            )
    else:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
