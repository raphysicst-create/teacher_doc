# 성립전 예산 요구 템플릿 (기안문 본문 HWPX)

승격: 2026. 7. 15. — 근거: 2224·3057·3459·3460 4건 **문안 완전 동일** (index.md 연도 반복쌍).
양식 출처: output/2026_농어촌유학_수리과학체험_기안문.hwpx (굴림·본문 12pt 원칙 적용본)에서
가나다 항 3개 제거 + 문안을 2224(최장 사례)로 교체. validate·layout·gonmun_lint 통과(2026. 7. 15.).
layout 경고 1건(body_paragraph_without_visible_indent)은 원 기안문에도 있던 승계 특성 — 무시.

## 구성
- `양식.hwpx` — 기안문 본문 양식 (수신·경유·제목·관련·2항·붙임, 굴림 12pt)
- `slots.json` — 슬롯 7개
- `budget.json` / `structure.json` — page_guard 프로파일 (그대로 사용)

## 슬롯 매핑 (문안은 4건 전건 동일 — 아래 4개만 갈아끼움)
| 슬롯 | 내용 | 예산(공백 제외) |
|------|------|------|
| p:5 | `제목  {학년도}학년도 {사업명} 성립전 예산 요구` | 30 |
| p:7 | `1. 관련: {기관}-{번호}({YYYY. M. D.})` — **related_lookup.py나 받은 공문 원문으로 확인된 값만** | 27 |
| p:9 | `2. {학년도}학년도 {사업명} 교부와 관련하여 붙임과 같이 성립전 예산을 편성하여 운영하고자 합니다.` | 54 |
| p:11 | `붙임  성립전 예산 요구 신청서({사업명 괄호표기}) 1부.  끝.` | 30 |
| p:1, p:3, p:4 | 기관명·수신·경유 — **건드리지 않음** | — |

- 사업명은 제목 = 2항 = 붙임 괄호표기 3곳 일치(괄호표기는 축약 가능, 3460 사례).
- 2항 동사문: "교부와 관련하여"는 지원금 교부형(2224). 사업 신청형(3460)은 "과 관련하여"만 — 원문 대조.
- 예산 초과 제목/2항은 `--no-strict-paragraph-budget`으로 처리(문단은 예산 이하 원칙이되 셀 아님).

## 사용법
```bash
SKILL=".claude/skills/hwpx/scripts"
python "$SKILL/edit_hwpx.py" 양식.hwpx -o out.hwpx --slot-json values.json
python "$SKILL/validate.py" out.hwpx && python "$SKILL/fix_namespaces.py" out.hwpx
python "$SKILL/finalize_hwpx.py" out.hwpx --strip-linesegarray --layout
python "$SKILL/page_guard.py" --reference 양식.hwpx --output out.hwpx \
  --budget-profile budget.json --structure-profile structure.json \
  --no-strict-paragraph-budget --skip-text-drift
python "$SKILL/content_guard.py" out.hwpx --rules rules.json   # forbid: 농어촌유학 거주비, 정책기획과-3100 등 잔재
python "$SKILL/gonmun_lint.py" --hwpx out.hwpx --format text
```

## 주의
- content_guard forbid에 **이 양식의 원 사업명("농어촌유학 거주비 지원금", "정책기획과-3100")**을 반드시 포함 — 복사 잔재 검사.
- 협조자: 행정실장 관행 (전자결재 단계 — 문서에는 안 나타남, 기안 시 사람이 지정).
- 유사형 주의: 추경예산요구서 제출(2435)은 문안이 다름 — 이 템플릿 쓰지 말고 2435 md 참조.
