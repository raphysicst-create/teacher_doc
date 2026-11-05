#!/usr/bin/env python3
"""Validate the structural integrity of an HWPX file.

Checks:
  - Valid ZIP archive
  - Required files present (HWPX 최소 패키지 11개 — REQUIRED_FILES 참고)
  - mimetype content is correct
  - mimetype is the first ZIP entry and stored without compression
  - All XML files are well-formed
  - content.hpf manifest hrefs exist in the package
  - section image references point to manifest items
  - table cell addresses and spans fill the row/column grid exactly
  - body text holds no tool output, Markdown syntax or characters lost to encoding

Usage:
    python validate.py document.hwpx
"""

import argparse
import re
import sys
from pathlib import Path
from zipfile import ZIP_STORED, BadZipFile, ZipFile

from lxml import etree

# HWPX 최소 패키지 11개 파일.
# 2026. 8. 20.: 이전에는 아래 4개(mimetype·content.hpf·header.xml·section0.xml)만
# 검사해서, Preview/ 2개와 META-INF/container.rdf가 빠진 9파일 패키지가 전 검사를
# 통과했다. 한글은 그래도 열리기 때문에 COM 실열림 검사로도 잡히지 않는다.
# output/ 26건 중 5건이 같은 3개 파일 누락 — 전부 가정통신문 재패키징 경로.
REQUIRED_FILES = [
    "mimetype",
    "version.xml",
    "settings.xml",
    "Contents/content.hpf",
    "Contents/header.xml",
    "Contents/section0.xml",
    "META-INF/container.xml",
    "META-INF/container.rdf",
    "META-INF/manifest.xml",
    "Preview/PrvImage.png",
    "Preview/PrvText.txt",
]

EXPECTED_MIMETYPE = "application/hwp+zip"

NS = {
    "opf": "http://www.idpf.org/2007/opf/",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
}

# 2026. 11. 1.: 행을 지운 뒤 rowAddr를 다시 매기지 않은 표가 전 검사를 통과했고,
# 한글은 그 파일의 PDF 저장에서 끝나지 않았다. 표 하나에 보고하는 오류 수만 제한한다.
GRID_ERROR_LIMIT = 3

# 2026. 11. 1.: 값 대조 366/370으로 완료 보고된 문서에 kordoc 머리글, 잘린 명령 출력,
# 인코딩이 깨진 ?? 문단이 본문으로 들어갔다. 표본 문서 40개에서 오탐 0건.
BODY_JUNK = (
    ("kordoc header", re.compile(r"\[포맷:\s*\w+\s*\\?\|")),
    ("command output", re.compile(r"Warning: truncated output|Total output lines:")),
    ("lost characters", re.compile(r"\?{2,}")),
    ("Markdown syntax", re.compile(r"\*\*|</?t[drh]\b|^#{1,6} |\|\s*---")),
)
BODY_JUNK_LIMIT = 5


def body_junk_errors(section_name: str, root: etree._Element) -> list[str]:
    """Return errors for text that came from a tool instead of the document."""

    found: list[str] = []
    for node in root.xpath(".//hp:t", namespaces=NS):
        text = "".join(node.itertext())
        found.extend(
            f"{section_name}: {name} in body: {text.strip()[:40]!r}"
            for name, pattern in BODY_JUNK
            if pattern.search(text)
        )
    if len(found) > BODY_JUNK_LIMIT:
        hidden = len(found) - BODY_JUNK_LIMIT
        found = found[:BODY_JUNK_LIMIT] + [f"{section_name}: {hidden} more body junk errors"]
    return found


def table_grid_errors(section_name: str, root: etree._Element) -> list[str]:
    """Return errors for tables whose cells do not fill rowCnt x colCnt exactly."""

    errors: list[str] = []
    for number, table in enumerate(root.xpath(".//hp:tbl", namespaces=NS)):
        label = f"{section_name} table {number}"
        table_rows = table.xpath("./hp:tr", namespaces=NS)
        # 내장 minutes 양식처럼 rowCnt·colCnt가 없는 표는 실제 칸에서 크기를 얻는다.
        try:
            rows = int(table.get("rowCnt", len(table_rows)))
            cols = int(
                table.get(
                    "colCnt",
                    max(
                        (
                            sum(
                                int(span.get("colSpan", "1"))
                                for span in tr.xpath("./hp:tc/hp:cellSpan", namespaces=NS)
                            )
                            for tr in table_rows
                        ),
                        default=0,
                    ),
                )
            )
        except ValueError:
            errors.append(f"{label}: invalid rowCnt/colCnt")
            continue
        found: list[str] = []
        filled: set[tuple[int, int]] = set()
        if len(table_rows) != rows:
            found.append(f"rowCnt={rows} but {len(table_rows)} rows")
        for row_index, tr in enumerate(table_rows):
            for tc in tr.xpath("./hp:tc", namespaces=NS):
                addr = tc.find("hp:cellAddr", NS)
                span = tc.find("hp:cellSpan", NS)
                try:
                    col, row = int(addr.get("colAddr")), int(addr.get("rowAddr"))
                    col_span, row_span = int(span.get("colSpan")), int(span.get("rowSpan"))
                except (AttributeError, TypeError, ValueError):
                    found.append(f"row {row_index} has a cell without cellAddr/cellSpan")
                    continue
                if row != row_index:
                    found.append(f"row {row_index} has rowAddr={row}")
                if row + row_span > rows or col + col_span > cols:
                    found.append(f"cell ({row},{col}) span {row_span}x{col_span} exceeds table")
                cells = {
                    (y, x)
                    for y in range(row, row + row_span)
                    for x in range(col, col + col_span)
                }
                if cells & filled:
                    found.append(f"cell ({row},{col}) overlaps another cell")
                filled |= cells
        if len(filled) != rows * cols:
            found.append(f"{len(filled)} of {rows * cols} grid cells filled")
        for message in found[:GRID_ERROR_LIMIT]:
            errors.append(f"{label}: {message}")
        if len(found) > GRID_ERROR_LIMIT:
            errors.append(f"{label}: {len(found) - GRID_ERROR_LIMIT} more grid errors")
    return errors


def validate(hwpx_path: str) -> list[str]:
    """Validate HWPX file and return a list of error messages (empty = valid)."""

    errors: list[str] = []
    path = Path(hwpx_path)

    if not path.is_file():
        return [f"File not found: {hwpx_path}"]

    # Check valid ZIP
    try:
        zf = ZipFile(hwpx_path, "r")
    except BadZipFile:
        return [f"Not a valid ZIP archive: {hwpx_path}"]

    with zf:
        names = zf.namelist()

        # Check required files
        for required in REQUIRED_FILES:
            if required not in names:
                errors.append(f"Missing required file: {required}")

        # Check mimetype content
        if "mimetype" in names:
            mimetype_content = zf.read("mimetype").decode("utf-8").strip()
            if mimetype_content != EXPECTED_MIMETYPE:
                errors.append(
                    f"Invalid mimetype: expected '{EXPECTED_MIMETYPE}', "
                    f"got '{mimetype_content}'"
                )

            # Check mimetype is first entry
            if names[0] != "mimetype":
                errors.append(
                    f"mimetype is not the first ZIP entry (found at index "
                    f"{names.index('mimetype')})"
                )

            # Check mimetype is stored without compression
            info = zf.getinfo("mimetype")
            if info.compress_type != ZIP_STORED:
                errors.append(
                    f"mimetype should use ZIP_STORED (0), "
                    f"got compress_type={info.compress_type}"
                )

        parsed_xml: dict[str, etree._Element] = {}

        # Check XML well-formedness
        for name in names:
            if name.endswith(".xml") or name.endswith(".hpf"):
                try:
                    data = zf.read(name)
                    parsed_xml[name] = etree.fromstring(data)
                except etree.XMLSyntaxError as e:
                    errors.append(f"Malformed XML in {name}: {e}")

        content = parsed_xml.get("Contents/content.hpf")
        if content is not None:
            manifest_ids: set[str] = set()
            for item in content.xpath(".//opf:item", namespaces=NS):
                item_id = item.get("id", "")
                href = item.get("href", "")
                if item_id:
                    manifest_ids.add(item_id)
                if href and href not in names:
                    errors.append(f"content.hpf references missing file: {href}")

            for section_name, section_root in parsed_xml.items():
                if not section_name.startswith("Contents/section"):
                    continue
                for img in section_root.xpath(".//hc:img", namespaces=NS):
                    ref = img.get("binaryItemIDRef", "")
                    if ref and ref not in manifest_ids:
                        errors.append(
                            f"{section_name} image references missing manifest item: {ref}"
                        )

        for section_name, section_root in parsed_xml.items():
            if section_name.startswith("Contents/section"):
                errors.extend(table_grid_errors(section_name, section_root))
                errors.extend(body_junk_errors(section_name, section_root))

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the structural integrity of an HWPX file"
    )
    parser.add_argument("input", help="Path to .hwpx file")
    parser.add_argument(
        "--layout",
        action="store_true",
        help="Also report layout risk warnings from finalize_hwpx.py",
    )
    args = parser.parse_args()

    errors = validate(args.input)

    if errors:
        print(f"INVALID: {args.input}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"VALID: {args.input}")
        print(f"  All structural checks passed.")
        if args.layout:
            from finalize_hwpx import find_layout_warnings

            warnings = find_layout_warnings(args.input)
            if warnings:
                print(f"  Layout warnings: {len(warnings)}")
                for warning in warnings[:30]:
                    location = ""
                    if "table" in warning:
                        location = (
                            f" table={warning['table']}"
                            f" row={warning['row']}"
                            f" col={warning['col']}"
                        )
                    print(f"  - {warning['type']}{location}: {warning['message']}")
                if len(warnings) > 30:
                    print(f"  - ... {len(warnings) - 30} more")
            else:
                print("  Layout warnings: 0")


if __name__ == "__main__":
    main()
