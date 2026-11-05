#!/usr/bin/env python3
"""Delete or insert table rows while keeping the cell grid valid.

Removing hp:tr by hand leaves stale rowAddr values and merged cells that overrun
the table, and Hancom can hang while rendering such a file. Row and table numbers
are the ones in hwpx_slots keys (cell:<table>:<row>:<col>). Use only inside an
approved structure change.
"""

from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from edit_hwpx import (
    NS,
    SECTION_PATH,
    _parse_xml,
    _remove_linesegarrays,
    _serialize_xml_like_source,
    _validate_input,
    write_raw_preserving_zip,
)
from hwpx_slots import cell_edit_block_reason, owned_cells
from validate import table_grid_errors

HP = "{" + NS["hp"] + "}"


def _rows(table: etree._Element) -> list[etree._Element]:
    return table.findall("hp:tr", NS)


def _addr(cell: etree._Element) -> tuple[int, int]:
    addr = cell.find("hp:cellAddr", NS)
    return int(addr.get("rowAddr")), int(addr.get("colAddr"))


def _span(cell: etree._Element) -> tuple[int, int]:
    span = cell.find("hp:cellSpan", NS)
    return int(span.get("rowSpan", "1")), int(span.get("colSpan", "1"))


def _set_row(cell: etree._Element, row: int) -> None:
    cell.find("hp:cellAddr", NS).set("rowAddr", str(row))


def _set_row_span(cell: etree._Element, span: int) -> None:
    cell.find("hp:cellSpan", NS).set("rowSpan", str(span))


def _height(cell: etree._Element) -> int:
    size = cell.find("hp:cellSz", NS)
    return int(size.get("height", "0")) if size is not None else 0


def _grow_height(element: etree._Element, tag: str, amount: int) -> None:
    size = element.find(tag, NS)
    if size is not None and size.get("height"):
        size.set("height", str(max(0, int(size.get("height")) + amount)))


def _row_height(row: etree._Element) -> int:
    """Height of a row, read from a cell that covers that row only."""
    return max((_height(c) for c in row.findall("hp:tc", NS) if _span(c)[0] == 1), default=0)


def _place(row: etree._Element, cell: etree._Element) -> None:
    """Add a cell to a row in column order."""
    column = _addr(cell)[1]
    for index, other in enumerate(row.findall("hp:tc", NS)):
        if _addr(other)[1] > column:
            other.addprevious(cell)
            return
    row.append(cell)


def _refresh_row_addresses(table: etree._Element) -> None:
    rows = _rows(table)
    for index, row in enumerate(rows):
        for cell in row.findall("hp:tc", NS):
            _set_row(cell, index)
    table.set("rowCnt", str(len(rows)))


def delete_rows(table: etree._Element, targets: set[int]) -> None:
    rows = _rows(table)
    if not targets or min(targets) < 0 or max(targets) >= len(rows):
        raise SystemExit(f"행 번호 범위 초과: {sorted(targets)} (행 수: {len(rows)})")
    if len(targets) == len(rows):
        raise SystemExit("표의 모든 행은 지울 수 없습니다. 표 삭제는 별도 구조 변경입니다")
    heights = {index: _row_height(rows[index]) for index in targets}

    for cell in owned_cells(table):
        start = _addr(cell)[0]
        row_span = _span(cell)[0]
        covered = range(start, start + row_span)
        kept = [index for index in covered if index not in targets]
        if not kept:
            cell.getparent().remove(cell)
            continue
        if len(kept) == row_span:
            continue
        _set_row_span(cell, len(kept))
        _grow_height(cell, "hp:cellSz", -sum(heights[i] for i in covered if i in targets))
        if start in targets:  # 병합 칸의 시작 행이 지워지면 글자는 남는 첫 행으로 옮긴다
            cell.getparent().remove(cell)
            _place(rows[kept[0]], cell)

    for index in targets:
        table.remove(rows[index])
    _refresh_row_addresses(table)
    _grow_height(table, "hp:sz", -sum(heights.values()))


def _blank_copy(cell: etree._Element) -> etree._Element:
    reason = cell_edit_block_reason(cell)
    if reason:
        raise SystemExit(f"복제할 행에 {reason}이 있습니다. 다른 행을 고르세요")
    new = copy.deepcopy(cell)
    _set_row_span(new, 1)
    _remove_linesegarrays(new)
    sub_list = new.find("hp:subList", NS)
    for paragraph in sub_list.findall("hp:p", NS)[1:]:
        sub_list.remove(paragraph)
    for text in new.iter(f"{HP}t"):
        for child in list(text):
            text.remove(child)
        text.text = None
    return new


def insert_rows(table: etree._Element, after: int, count: int) -> None:
    """Insert empty rows below a row, copying its cell format.

    Merged cells that continue past the row stretch over the new rows.
    """
    rows = _rows(table)
    if not 0 <= after < len(rows) or count < 1:
        raise SystemExit(f"행 번호 범위 초과: {after} (행 수: {len(rows)})")
    height = _row_height(rows[after])
    sources = []
    for cell in owned_cells(table):
        start = _addr(cell)[0]
        row_span = _span(cell)[0]
        if not start <= after < start + row_span:
            continue
        if after + 1 < start + row_span:
            _set_row_span(cell, row_span + count)
            _grow_height(cell, "hp:cellSz", height * count)
        else:
            sources.append(cell)
    sources.sort(key=lambda cell: _addr(cell)[1])

    anchor = rows[after]
    for _ in range(count):
        row = etree.Element(rows[after].tag, attrib=dict(rows[after].attrib), nsmap=rows[after].nsmap)
        for cell in sources:
            new = _blank_copy(cell)
            if height:
                new.find("hp:cellSz", NS).set("height", str(height))
            row.append(new)
        anchor.addnext(row)
        anchor = row
    _refresh_row_addresses(table)
    _grow_height(table, "hp:sz", height * count)


def parse_rows(raw: str) -> set[int]:
    """3,5,7-9 → {3, 5, 7, 8, 9}."""
    rows: set[int] = set()
    for part in raw.split(","):
        match = re.fullmatch(r"\s*(\d+)(?:-(\d+))?\s*", part)
        if not match:
            raise SystemExit(f"행 번호 형식 오류: {raw}")
        rows.update(range(int(match[1]), int(match[2] or match[1]) + 1))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="HWPX 표 행 삭제·추가 (칸 주소·병합 유지)")
    parser.add_argument("input", type=Path, help="기준 .hwpx")
    parser.add_argument("--output", "-o", type=Path, required=True, help="결과 .hwpx")
    parser.add_argument("--table", type=int, required=True, help="슬롯 키의 표 번호")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--delete-rows", help="지울 행 번호. 예: 3,5,7-9")
    action.add_argument("--insert-after", type=int, help="이 행 아래에 빈 행 추가")
    parser.add_argument("--count", type=int, default=1, help="추가할 행 수")
    args = parser.parse_args()

    if args.input.resolve() == args.output.resolve():
        raise SystemExit("원본을 덮어쓰지 않습니다. 별도 출력 사본 경로를 선택하세요")
    with ZipFile(args.input, "r") as source:
        _validate_input(source)
        section = source.read(SECTION_PATH)
    tree = _parse_xml(section)
    root = tree.getroot()
    before = table_grid_errors(SECTION_PATH, root)
    if before:
        raise SystemExit("표 격자가 이미 깨져 있어 행을 바꿀 수 없습니다: " + "; ".join(before[:3]))
    tables = root.xpath(".//hp:tbl", namespaces=NS)
    if args.table >= len(tables):
        raise SystemExit(f"표 인덱스 범위 초과: {args.table} (문서 표 수: {len(tables)})")
    table = tables[args.table]

    if args.delete_rows:
        delete_rows(table, parse_rows(args.delete_rows))
    else:
        insert_rows(table, args.insert_after, args.count)

    after = table_grid_errors(SECTION_PATH, root)
    if after:
        raise SystemExit("행 변경 후 표 격자 오류: " + "; ".join(after[:3]))
    write_raw_preserving_zip(args.input, args.output, {SECTION_PATH: _serialize_xml_like_source(tree, section)})
    print(f"WROTE: {args.output} (표 {args.table}, 행 {table.get('rowCnt')}개)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
