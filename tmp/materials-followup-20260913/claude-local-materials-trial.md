# 로컬 폐기용 사본 — 구현 후속 시험 결과

범위: `inputs/local-materials`의 로컬 폐기용 사본만 사용. 실제 발송/전송 없음. 원본·기존 파일은 변경하지 않았다.
기존 문서의 `approval_record`(과거 승인 사실)를 이번 시험에서 만든 새 문안·판단의 승인으로 옮기지 않았다.

## 1. 기안문 공통 베이스 대조 (sources.json + profiles/lineage-01~08.json ↔ profiles/gianmun.json)

| 항목 | lineage-01~08 (8건) | gianmun.json(양식) |
|---|---|---|
| header_sha256 | 전부 `c678c7afe236286636222b2b88f54f37e88a0813fa4737e1899488ea0a2a9d98` 동일 | 동일 |
| 제목 charPr | 전부 `<hh:bold/>` 있음, `height="1200"`(12pt) | 동일 |
| 페이지 여백(hp:margin) | 전부 `top="5668" left="8504" right="8504" footer="4252"` 동일 | 동일 |

8건(B1·B2·B4~B7-a·B7-b·B7-c)과 성립전예산요구 양식이 header_sha256까지 동일한 것으로 확인됐다. 기존 메모리에 남긴 "승인 기안문 8건 전부 성립전예산요구 양식 계보" 판단이 이번 파일 대조로 재확인된 것이며, 새로 승인한 사실은 아니다.

## 2. 회신형 가통 초안 — activities.json `six`(6개) vs 기존 표 구조

`sources/reply/slots.json`의 표1(일정표)은 헤더 1행 + **데이터 5행(row 1~5)** 고정 구조다 (row0=헤더, row1~5=08:20~16:50 활동 5개).
`activities.json.six`는 활동 6개(09:00 학교 출발 ~ 14:00 학교 복귀)다.

- **기존 데이터 행 수: 5행 / 필요 행 수: 6행 → 1행 부족.**
- 이 표의 행 추가(구조 변경)는 이번 지시에서 아직 승인되지 않았다. 5행에 6개를 그대로 채우려면 활동 두 개를 한 셀에 합쳐야 하는데, 이는 금지된 처리(활동 누락·행 병합으로 행 부족을 해소하지 않는다)에 해당해 시도하지 않았다.
- 따라서 `edit_hwpx.py --slot-json`으로 실제 파일을 만들지 않았다. 6개를 모두 보존하는 대응만 아래처럼 초안 형태로 남기고 빌드는 보류한다.

| 표1 행 | six 활동 | 비고 |
|---|---|---|
| row1(기존) | 09:00 학교 출발 | 그대로 매핑 가능 |
| row2(기존) | 10:00 천체 관측 체험 | 그대로 매핑 가능 |
| row3(기존) | 11:00 로봇 조종 체험 | 그대로 매핑 가능 |
| row4(기존) | 12:00 점심 식사 | 그대로 매핑 가능 |
| row5(기존) | 13:00 생태 탐사 | 그대로 매핑 가능 |
| row6(**신규, 구조 변경 필요**) | 14:00 학교 복귀 | 승인 전에는 추가하지 않음 |

**다음 판단 필요**: 표에 1행을 추가하는 구조 변경을 승인할지(승인 시 README의 행 높이 기준 2723~2730도 함께 확보), 아니면 활동 6개를 5행으로 재구성할 다른 방침이 있는지.

## 3. 예산 초과 조사 — long_text.txt 전체를 활동 설명 셀 하나에

- 대상 셀: `cell:1:2:2` (로봇 체험 행의 "비고" 열). slots.json 스냅샷 기준 `max_chars=11`(공백 제외), 원문 미리보기 "로봇을 활용한 다양한 체험"(11자).
- `long_text.txt` 전체 문장: 209자(공백 포함) / **161자(공백 제외)**.
- 실행 명령(플래그 우회 없이 1회):
  ```
  C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe -B -X utf8 \
    C:/Users/22/Desktop/maintain/Hwp_doc/.claude/skills/hwpx/scripts/edit_hwpx.py \
    inputs/local-materials/sources/reply.hwpx \
    -o tmp/budget-test/reply-over-budget-test.hwpx \
    --slot-json tmp/budget-test/values.json
  ```
- 결과: `입력 전 글자수 예산 검사 실패 — table=1, row=2, col=2, max=24, input=161` → **exit 1**. 출력 파일은 생성되지 않았다(재시도하지 않음). 원본·기존 파일 변경 없음.
  - 실행 시점 계산된 예산(24, 표 폭 기반 추정)과 slots.json 스냅샷 값(11) 사이에 차이가 있으나, 161자는 어느 기준으로도 명백한 초과다.
  - `--allow-over-budget`은 사용하지 않았고, 렌더(`render_check.py`)나 PDF 육안 판독도 수행하지 않았다(지시대로 이번 시험 범위 밖).

**다음 판단 필요**: 이런 수준의 긴 설명을 실제 업무에서 써야 한다면, 대상·조 구성·측정 간격·횟수·중단 조건을 보존한 축약안이 필요하다 — 자동 축약은 하지 않았고 사용자 판단을 요청할 사안이다.

## 시험 산출물 / 미수행 항목

- 생성: `tmp/budget-test/values.json`(시험용 슬롯 입력), 본 보고서.
- 실패로 산출물 없음: `tmp/budget-test/reply-over-budget-test.hwpx`(예산 검사 단계에서 거부돼 미생성).
- 이번 시험에서 하지 않은 것: 회신형 가통 실제 빌드(표 구조 승인 대기), COM 실열림, render_check, PDF 육안 판독, 승인/판독 기록 생성, 원본·기존 파일 수정, 실제 발송.
