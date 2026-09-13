# 가정통신문 템플릿

출처: (화동중학교-2348 (첨부)) 가정통신문(기출문제 공개 안내).hwpx — 2026. 7. 7. 승격.
검증 이력: 2026_농어촌문화체험_가정통신문_v2.hwpx 생성에 사용, 전체 가드 통과 + 사용자 육안 확인 완료.

## 구성
- `양식.hwpx` — 원본 양식 (헤더 표: 로고·문서번호·연락처·교훈 / 인사말 / 안내 박스 표 / 날짜 / 직인)
- `slots.json` — hwpx_slots.py 산출 슬롯 목록 (38개)
- `budget.json` / `structure.json` — page_guard 프로파일 (재생성 불필요, 그대로 사용)

## 사용법 (hwpx 스킬)
```bash
python "$SKILL_DIR/scripts/edit_hwpx.py" 양식.hwpx -o out.hwpx --slot-json values.json
# 검증: validate → fix_namespaces → finalize --strip-linesegarray --layout →
# page_guard --budget-profile budget.json --structure-profile structure.json \
#   --no-strict-paragraph-budget --skip-text-drift --allow-empty-fill →
# content_guard(기출문제/저작권/사교육비 forbid) → gonmun_lint
```

## 채워야 하는 주요 슬롯
| 슬롯 | 내용 | 예산(공백 제외) |
|------|------|------|
| p:3 | 문서번호 "화동중 제YYYY-N호" | 12 |
| p:13 | 큰 제목 | **8자 — 초과 시 page_guard 실패, 짧은 제목 필수** |
| p:14 | 인사말 1줄 | 34 |
| p:15 | 본문 도입 문단 | 90 |
| p:19 | 안내 박스 소제목 | 15 |
| p:21~p:37 | 박스 내 항목들 (1./1)/- 계층) | slots.json 참조 |
| p:40 | 배부일 "YYYY. M. D." | 10 |
| p:42 | "화동중학교장[직인생략]" | 12 |

미사용 항목 슬롯은 `""`로 비운다 (page_guard --allow-empty-fill 필요).
헤더의 연락처(p:4~p:8)·교훈(p:9~p:11)은 건드리지 않는다.
