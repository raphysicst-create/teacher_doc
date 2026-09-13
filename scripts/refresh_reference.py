#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""knowledge/reference/ 원본(xlsx/xls)에서 파생 데이터(JSON·MD)를 재생성한다.

LLM 개입 없는 결정적 변환. 새 학기 시간표나 갱신된 사업관리카드를 받으면
knowledge/reference/의 원본 파일을 교체한 뒤 이 스크립트만 다시 실행한다.

생성물:
  - 기초시간표-<이름>.json / .md   (주제선택 표기 (주)·㈜·(원) 제거)
  - 예산과목-<연도>.json           (세부사업 > 세부항목 > 비목·산출내역 이름 목록)

사용: python scripts/refresh_reference.py
의존: openpyxl(xlsx), python-calamine(구형 xls)
"""
import datetime
import json
import re
import sys
from pathlib import Path

from hwpdoc_config import current_context
CONTEXT = current_context()
ROOT = CONTEXT.workspace
REF = ROOT / "knowledge" / "reference"

TIMETABLE_XLSX = CONTEXT.optional_reference('timetable_source')
TIMETABLE_JSON = CONTEXT.optional_reference('timetable')
BUDGET_XLS = CONTEXT.optional_reference('budget_source')
BUDGET_JSON = CONTEXT.optional_reference('budget')

def _merged_value(ws, row, col):
    """병합 셀이면 병합 범위 좌상단 값을 반환."""
    for rng in ws.merged_cells.ranges:
        if rng.min_row <= row <= rng.max_row and rng.min_col <= col <= rng.max_col:
            return ws.cell(rng.min_row, rng.min_col).value
    return ws.cell(row, col).value


def build_timetable():
    import openpyxl
    if not TIMETABLE_XLSX or not TIMETABLE_JSON:
        raise ValueError('시간표 source/파생 경로 설정이 필요합니다')
    if TIMETABLE_JSON.suffix.lower() != '.json' or TIMETABLE_JSON.resolve() == TIMETABLE_XLSX.resolve():
        raise ValueError('시간표 원본과 파생 JSON은 서로 다른 파일이어야 합니다')
    mapping = CONTEXT.settings.get('timetable_mapping', {})
    if mapping.get('format') != 'grade-columns-v1':
        raise ValueError('지원 시간표 형식은 grade-columns-v1입니다. 다른 형식을 추정하지 않습니다')
    days = mapping['day_columns']
    grades = mapping['grades']
    rows = mapping['period_rows']
    subject_full, non_subject = mapping['subject_full'], mapping['non_subject']
    if not grades or not rows or any(len(cols) != len(grades) for cols in days.values()):
        raise ValueError('요일별 열/학년·반/교시 행 매핑 불일치')
    if any(type(n) is not int or n < 1 for n in [*rows, *[c for cols in days.values() for c in cols]]):
        raise ValueError('엑셀 행·열은 1 이상의 정수여야 합니다')
    marker = re.compile(mapping['strip_pattern']) if mapping.get('strip_pattern') else None
    wb = openpyxl.load_workbook(TIMETABLE_XLSX)
    ws = wb[mapping['sheet']] if mapping.get('sheet') else wb.active
    title = str(ws.cell(1, 1).value).strip()
    table = {}
    for day, columns in days.items():
        table[day] = {g: [] for g in grades}
        for r in rows:
            for grade, col in zip(grades, columns):
                v = _merged_value(ws, r, col)
                v = '' if v is None else str(v).strip()
                v = marker.sub('', v).strip() if marker else v
                table[day][grade].append(v)
    wb.close()
    # 검증: 모든 칸이 알려진 과목 약어이거나 비교과 항목이어야 함
    unknown = set()
    for day in days:
        for grade in grades:
            for v in table[day][grade]:
                if v and v not in subject_full and v not in non_subject:
                    unknown.add(v)
    if unknown:
        raise SystemExit(f"[refresh] 알 수 없는 시간표 항목: {sorted(unknown)} — SUBJECT_FULL/NON_SUBJECT 갱신 필요")
    data = {
        "title": title,
        "source": TIMETABLE_XLSX.name,
        "generated": datetime.date.today().isoformat(),
        "grades": grades,
        "subject_full": subject_full,
        "non_subject": non_subject,
        "note": '학교 설정의 명시적 시간표 매핑 적용. 특별시간표 미반영.',
        "시간표": table,
    }
    TIMETABLE_JSON.parent.mkdir(parents=True, exist_ok=True)
    TIMETABLE_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 사람용 MD 재생성
    lines = [
        f"# {title}",
        "",
        f"- 원본: `{TIMETABLE_XLSX.name}` — refresh_reference.py 재생성 자료. 직접 수정 금지.",
        '- 학년/반: ' + ', '.join(f'{k}={v}' for k, v in grades.items()),
        '- 제거 패턴: ' + str(mapping.get('strip_pattern') or '없음'),
        "- 융합교과 산출은 이 md가 아니라 `scripts/fusion_timetable.py`(기계 계산)를 사용한다. 요일 LLM 암산 금지.",
        "- 한계: 단축수업·고사기간·학사행사 등 특별시간표 미반영 → 활동일이 걸릴 가능성 있으면 사용자 확인.",
        "",
        "| 교시 | " + " | ".join(f"{d}·{g}" for d in days for g in grades) + " |",
        "|---|" + "---|" * (len(days) * len(grades)),
    ]
    for p in range(1, len(rows) + 1):
        cells = [table[d][g][p - 1] for d in days for g in grades]
        lines.append(f"| {p} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## 구조 메모",
        "- 과목 약어: " + ", ".join(f"{k}={v}" for k, v in subject_full.items()) + ".",
        "",
    ]
    TIMETABLE_JSON.with_suffix('.md').write_text("\n".join(lines), encoding="utf-8")
    return data


def read_budget_rows(path):
    from python_calamine import CalamineWorkbook
    with CalamineWorkbook.from_path(str(path)) as book:
        # Header detection below uses original Excel row positions.
        return book.get_sheet_by_index(0).to_python(skip_empty_area=False)


def build_budget():
    if not BUDGET_XLS or not BUDGET_JSON:
        raise ValueError('사업관리카드 source/파생 경로 설정이 필요합니다')
    if BUDGET_JSON.suffix.lower() != '.json' or BUDGET_JSON.resolve() == BUDGET_XLS.resolve():
        raise ValueError('사업관리카드 원본과 파생 JSON은 서로 다른 파일이어야 합니다')
    rows = read_budget_rows(BUDGET_XLS)
    snapshot = datetime.date.fromtimestamp(BUDGET_XLS.stat().st_mtime).isoformat()
    programs = []
    cur_prog = cur_item = None
    for r, row in enumerate(rows):
        raw = row[0] if row else ""
        if not isinstance(raw, str) or not raw.strip():
            continue
        name = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        detail = row[1] if len(row) > 1 else ""
        # xlrd exposed numeric cells as floats; retain its string representation.
        detail = str(float(detail) if type(detail) is int else int(detail) if type(detail) is bool else detail).strip()
        amount = row[2] if len(row) > 2 else ""
        amount = int(amount) if type(amount) in (int, float) else None
        if name in ("사업관리카드(예산)",) or "합 계" in name:
            continue
        if r <= 3:  # 헤더 행
            continue
        if detail:  # 원가통계비목 행: col0=비목, col1=산출내역
            if cur_item is None:
                raise SystemExit(f"[refresh] {r}행: 상위 세부항목 없이 산출내역 등장: {name}/{detail}")
            cur_item["산출내역"].append({"비목": name, "명": detail, "예산현액": amount})
        elif indent <= 5:  # 세부사업
            cur_prog = {"세부사업": name, "예산현액": amount, "세부항목": []}
            programs.append(cur_prog)
            cur_item = None
        else:  # 세부항목
            if cur_prog is None:
                raise SystemExit(f"[refresh] {r}행: 상위 세부사업 없이 세부항목 등장: {name}")
            cur_item = {"명": name, "예산현액": amount, "산출내역": []}
            cur_prog["세부항목"].append(cur_item)
    n_names = sum(len(i["산출내역"]) for p in programs for i in p["세부항목"])
    if not programs or n_names == 0:
        raise SystemExit("[refresh] 사업관리카드 파싱 결과가 비었음 — 파일 구조 변경 여부 확인 필요")
    data = {
        "source": BUDGET_XLS.name,
        "snapshot": snapshot,
        "note": "예산과목 '이름' 대조가 목적(2026. 7. 15. 사용자 확인). 금액은 스냅샷 참고치일 뿐 검증 대상 아님.",
        "사업": programs,
    }
    BUDGET_JSON.parent.mkdir(parents=True, exist_ok=True)
    BUDGET_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(programs), n_names


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', choices=['timetable', 'budget'])
    args = ap.parse_args()
    if args.only in (None, 'timetable'):
        tt = build_timetable()
        print(f"[refresh] 시간표 JSON/MD 재생성 완료: {len(tt['시간표'])}개 요일 x {len(tt['grades'])}개 그룹")
    if args.only in (None, 'budget'):
        n_prog, n_names = build_budget()
        print(f"[refresh] 예산과목 JSON 재생성 완료: 세부사업 {n_prog}개, 산출내역 {n_names}개")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
