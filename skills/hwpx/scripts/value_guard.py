#!/usr/bin/env python3
"""Check that provided values reached an HWPX and that old table values did not stay.

content_guard's require option needs the exact string, so a value rewritten to the
form's date style reads as missing and a value split across cells cannot be listed.
This guard compares normalized text, dates and fragments, and counts short Korean
values as whole tokens. Reference review only lists cells whose values were erased;
cells already empty in the base are never reported.

--values    JSON list, or Markdown table with a 값 column. Missing values fail;
            short values fail only when absent from the text, and appearing as whole
            tokens fewer times than supplied is review-only.
--reference base HWPX. Unchanged value-shaped and erased cells are review-only.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from hwpx_slots import owned_cells

NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
MIN_VALUE_CHARS = 4  # 과목명·숫자처럼 짧은 값은 문서 어디에나 있어 있고 없음을 가릴 수 없다
MIN_FRAGMENT_CHARS = 2
SHORT_KOREAN = re.compile(r"[가-힣]{2,3}")
TOKEN_SPLIT = re.compile(r"[\s·,/]+")
TOKEN_CONTROLS = tuple(f"{{{NS['hp']}}}{name}"
                       for name in ("lineBreak", "tab", "fwSpace", "nbSpace"))
PUNCTUATION = re.compile(r"[\s.,·:;()\[\]/~\-*|\\～∼–‘’“”'\"]")
LEADING_ZERO = re.compile(r"(?<!\d)0(\d)(?!\d)")
DATE = re.compile(r"(?:\d{4}\s*[.년]\s*)?(\d{1,2})\s*[.월]\s*(\d{1,2})(?!\d)\s*[.일]?")
RANGE_END = re.compile(r"\s*(?:\([월화수목금토일]\))?\s*[~～∼]\s*(\d{1,2})(?!\d|\s*\.\s*\d|\s*[월:])")
WEEKDAY = re.compile(r"\([월화수목금토일]\)")
ITEM_MARK = re.compile(r"^\s*(?:\d+[.)]|[가-하][.)]|\(\d+\)|\([가-하]\)|[-※*])\s*")  # 문단 번호는 본문 글자가 아니다
FRAGMENT_SPLIT = re.compile(r"\s*/\s*|(?<=[.)%])\s+(?=[가-하]\.)|\n")
VALUE_SHAPE = re.compile(r"\d{1,4}\s*[./월]\s*\d{1,2}|\d{1,2}:\d{2}|\d{1,3}(?:,\d{3})+|\d\s*(?:원|명|시간|일|회)")


def normalize(text: str) -> str:
    return PUNCTUATION.sub("", LEADING_ZERO.sub(r"\1", text))


def date_tokens(text: str) -> set[tuple[int, int]]:
    """Month-day pairs. A range end written as 28. takes its month from the start."""
    found: set[tuple[int, int]] = set()
    for match in DATE.finditer(text):
        month, day = int(match[1]), int(match[2])
        if 1 <= month <= 12 and 1 <= day <= 31:
            found.add((month, day))
            end = RANGE_END.match(text, match.end())
            if end:
                found.add((month, int(end[1])))
    return found


def is_delivered(value: str, whole: str, lines: list[str]) -> bool:
    value = ITEM_MARK.sub("", value)
    if normalize(value) in whole:
        return True
    fragments = [f for f in FRAGMENT_SPLIT.split(value) if len(normalize(f)) >= MIN_FRAGMENT_CHARS]
    if len(fragments) > 1 and all(normalize(f) in whole for f in fragments):
        return True
    dates = date_tokens(value)
    if not dates:
        return False
    rest = normalize(WEEKDAY.sub("", DATE.sub("", RANGE_END.sub("", value))))
    return any(dates <= date_tokens(line) and rest in normalize(line) for line in lines)


def load_values(path: Path) -> list[str]:
    """Keep repeated entries: short-value checks need the supplied occurrence count."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if not (isinstance(data, list) and all(isinstance(item, str) for item in data)):
            raise SystemExit("--values JSON은 문자열 배열이어야 합니다.")
        return data
    values: list[str] = []
    column = None
    for line in text.splitlines():
        if not line.lstrip().startswith("|") or re.fullmatch(r"[|:\-\s]+", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if column is None:
            if "값" not in cells:
                raise SystemExit("--values 표에 값 열이 없습니다.")
            column = cells.index("값")
        elif len(cells) > column:
            values.append(cells[column])
    return values


def check_values(values: list[str], text: str) -> dict:
    whole = normalize(text)
    lines = text.splitlines()
    checked = [v for v in dict.fromkeys(values) if len(normalize(v)) >= MIN_VALUE_CHARS]
    missing = [v for v in checked if not is_delivered(v, whole, lines)]
    expected = Counter(v for v in values if SHORT_KOREAN.fullmatch(v))
    actual = Counter(TOKEN_SPLIT.split(text))
    # 글자가 아예 없을 때만 실패. 낱말 단위 횟수 부족은 조사·괄호가 붙은 탓일 수 있어 확인만 요청한다.
    short_missing = [{"value": v, "expected": count, "actual": 0}
                     for v, count in expected.items() if v not in text]
    short_shortfall = [{"value": v, "expected": count, "actual": actual[v]}
                       for v, count in expected.items() if v in text and actual[v] < count]
    return {"checked": len(checked), "delivered": len(checked) - len(missing),
            "missing": missing, "too_short": len(set(values)) - len(checked),
            "short_missing": short_missing, "short_shortfall": short_shortfall}


def extract_value_text(path: Path) -> str:
    """Read each paragraph's own runs once, without recounting enclosing table text."""
    lines = []
    with ZipFile(path, "r") as archive:
        for name in sorted(archive.namelist()):
            if not (name.startswith("Contents/section") and name.endswith(".xml")):
                continue
            root = etree.fromstring(archive.read(name), etree.XMLParser(resolve_entities=False))
            # Empty HWPX controls separate tokens just like literal whitespace.
            # Change only this in-memory tree, leaving text_extract's behavior intact.
            for control in root.iter(*TOKEN_CONTROLS):
                control.tail = " " + (control.tail or "")
            for paragraph in root.xpath(".//hp:p", namespaces=NS):
                text = "".join(paragraph.xpath("./hp:run/hp:t//text()", namespaces=NS)).strip()
                if text:
                    lines.append(text)
    return "\n".join(lines)


def _tables(path: Path) -> list[etree._Element]:
    with ZipFile(path, "r") as archive:
        root = etree.fromstring(archive.read("Contents/section0.xml"))
    return root.xpath(".//hp:tbl", namespaces=NS)


def _table_cells(table: etree._Element, index: int) -> list[tuple[str, str]]:
    """Slot key and text of each owned cell in the same order as hwpx_slots."""
    cells = []
    seen: Counter[str] = Counter()
    for cell in owned_cells(table):
        addr = cell.find("hp:cellAddr", NS)
        if addr is None:
            continue
        key = f"cell:{index}:{addr.get('rowAddr', '0')}:{addr.get('colAddr', '0')}"
        occurrence = seen[key]
        seen[key] += 1
        if occurrence:
            key += f":{occurrence}"
        text = "".join(cell.xpath(".//hp:t//text()", namespaces=NS))
        cells.append((key, text))
    return cells


def table_cells(path: Path) -> list[tuple[str, str]]:
    return [cell for index, table in enumerate(_tables(path))
            for cell in _table_cells(table, index)]


def erased_table_cells(result: Path, reference: Path) -> list[dict]:
    """Review only nonempty-to-empty changes at matching slots in same-sized tables."""
    erased = []
    for index, (base, current) in enumerate(zip(_tables(reference), _tables(result))):
        shape = (base.get("rowCnt"), base.get("colCnt"))
        if None in shape or shape != (current.get("rowCnt"), current.get("colCnt")):
            continue
        before = dict(_table_cells(base, index))
        erased.extend({"slot": key} for key, text in _table_cells(current, index)
                      if before.get(key, "").strip() and not text.strip())
    return erased


def old_table_values(result: Path, reference: Path, values: list[str]) -> list[dict]:
    """Value-shaped cells copied unchanged from the base and not listed as this year's value."""
    base = {normalize(text) for _, text in table_cells(reference)}
    current = {normalize(v) for v in values}
    return [{"slot": key, "text": " ".join(text.split())[:80]}
            for key, text in table_cells(result)
            if VALUE_SHAPE.search(text) and normalize(text) in base and normalize(text) not in current]


def main() -> int:
    parser = argparse.ArgumentParser(description="HWPX 제공값 반영과 베이스 표 값 잔존 검사")
    parser.add_argument("input", type=Path, help="검사할 .hwpx")
    parser.add_argument("--values", type=Path, help="제공값 JSON 배열 또는 값 열이 있는 Markdown 표")
    parser.add_argument("--reference", type=Path, help="베이스 .hwpx")
    parser.add_argument("--json", action="store_true", help="JSON으로 결과 출력")
    args = parser.parse_args()
    if not args.input.is_file():
        print(f"Error: input not found: {args.input}", file=sys.stderr)
        return 2
    if not args.values and not args.reference:
        parser.error("--values 또는 --reference가 필요합니다.")

    values = load_values(args.values) if args.values else []
    report = {"input": str(args.input)}
    if args.values:
        report["values"] = check_values(values, extract_value_text(args.input))
    if args.reference:
        report["unchanged_cells"] = old_table_values(args.input, args.reference, values)
        report["erased_cells"] = erased_table_cells(args.input, args.reference)
    missing = report.get("values", {}).get("missing", [])
    short_missing = report.get("values", {}).get("short_missing", [])
    short_shortfall = report.get("values", {}).get("short_shortfall", [])
    failed = bool(missing or short_missing)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if args.values:
            result = report["values"]
            status = 'FAIL' if failed else ('WARN (확인 필요)' if short_shortfall else 'PASS')
            print(f"{status}: value-guard {result['delivered']}/{result['checked']}"
                  f" (짧아서 제외 {result['too_short']})")
            for value in missing:
                print(f"  - 미반영: {value[:100]}")
            for item in short_missing:
                print(f"  - short_missing: {item['value']} (N={item['expected']}, M={item['actual']})")
            for item in short_shortfall:
                print(f"  - [WARN] short_shortfall (확인 필요): {item['value']} (N={item['expected']}, M={item['actual']})")
        for cell in report.get("unchanged_cells", []):
            print(f"  - 베이스와 같음 {cell['slot']}: {cell['text']}")
        for cell in report.get("erased_cells", []):
            print(f"  - [WARN] erased_cells: {cell['slot']} (베이스 값 소거 검토)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
