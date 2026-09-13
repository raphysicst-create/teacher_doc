# 평가자 진행·판정 안내

## 역할과 실행 순서

설계/구현 세션이 아닌 실제 평가 세션 ID를 사용한다. 이 패키지는 제품을 자동 실행하지 않는다. 입력·관측·사람 확인·판정은 평가자가 진행하며 집계기는 기록 누락과 변경을 찾는다.

1. 후보 동결: 작업 트리 변경을 확인하고 대상 파일 목록(JSON 상대경로 배열)을 만든다. 예시 목록에 실제 배포 후보·추가 모듈이 빠지지 않았는지 검수한다. HEAD만으로 미커밋 코드를 식별하지 않는다.
2. init: 새 run-dir 아래 lock.json, git-snapshot.json, fixtures.json, records 176개를 만든다. 기존 실행 폴더는 덮어쓰지 않는다. 초기 장부의 모든 항목은 pending이다.
3. fixture 결합: FIXTURES.md를 따라 평가 사본과 출처를 준비한다. 못 구한 자료는 pending/blocked로 명시한다. seal-fixtures로 manifest와 원문 파일 해시를 한 번 고정한다. 이후 변조는 lab 사본에만 한다.
4. CLI 사례부터 관측한다. 일부 기본 기능이 없으면 해당 사례를 pending으로 기록하고 독립적으로 실행 가능한 사례를 계속한다. 제품을 고쳐서 평가를 계속하지 않는다.
5. 실제 앱 사례는 앱별로 순차 수행한다. 환경·앱·엔진·모델·effort·실제 도구명·입력 원증거를 저장한다. 환경 확인과 호스트 보호는 별개다.
6. 평가 대상에게 cases/ 입력과 fixture만 제공하고 최초 응답·도구 출력을 first-response 파일로 고정한다. 그 후 rubrics/의 개별 항목을 적용한다. 같은 세션에서 먼저 rubric을 읽었다면 이미 노출된 시험임을 기록하며 최초 판단 능력 검증에는 새 문맥이 필요하다. 파일 분리는 절차적 분리이며 비밀/보안 경계가 아니다.
7. 사람 확인 단계가 남으면 기다린다. 도구/에이전트가 사람 승인·평점·시각 판독을 만들지 않는다. CLI 합성 승인에는 SYNTHETIC_TEST_NOT_USER를 명시한다.
8. 평가 행 records/ID--target--variant.json을 관측한 사실로 채운다. 원시 transcript/command/report/PNG 등의 경로·해시·locator를 붙인다. 평가자 확인을 기록하고 score로 누락을 점검한다.
9. 결과를 7단계·4대상(cli/claude/codex/teacher_selected)·176행별로 보고한다. 최종 보고서는 실행 폴더에 새 파일로 보존한다. 고유 파일 수를 원하면 별도 최종 SHA256으로 중복 제거한다.

## 독립 fixture와 고장 주입

각 행은 fixtures의 원문에서 새 lab/ID--target--variant/ 사본을 만든다. 이전 실패 행의 변경된 양식·승인·보고서를 다음 행의 입력으로 쓰지 않는다. 정상 대조군 실행 후 지정 오류 하나만 넣어 before/after·대조군 결과를 함께 남긴다.

- 01: 5종 각각 기준/후보 동일 입력 2회. 전체 필수 검증과 실제 서식 비교를 포함한다. baseline의 WinError 5는 baseline 실패로 기록하며 기준 통과를 가정하지 않는다.
- 03: app 선택에 맞는 지침만 생성. existing은 KEEP_EXISTING 표식 파일의 해시를 고정. reinitialize는 초기화 성공 후 동일 위치 재호출. 실제 운영 root/부모는 시험하지 말고 경로 검사 회귀와 폐기용 복제 root로 확인한다.
- 04/07: 원본을 이동·삭제하지 않고 시험 workspace A를 B로 복사한다. B에서 A가 없어도 읽힐 수 있는지 격리한다. legacy_absolute와 portable_record를 구분하고 기존 승인 원문/해시를 보존한다. long_path는 실제 resolve 경로 길이를 기록한다. 미지원이면 명시적 사전 진단을 요구한다.
- 05/21: Python·Node·한글 부재는 격리 프로세스/계정/환경에서 구성한다. 운영 프로그램 제거·PATH 전역 수정·레지스트리 삭제는 하지 않는다. 새 환경 부재는 blocked.
- 06: FIXTURES의 두 학교 정답 원문과 비교. 3학년/같은 문서번호 다른 기관을 반드시 포함한다. 지원 파일 형식은 변환 전후 표를 남기고 정답 값은 바꾸지 않는다.
- 08: 5종 목록은 이관 전/초안/실제 확인 후를 각각 캡처한다. 실제 사람 확인이 없으면 그 부분은 pending/blocked이며 legacy_available를 registered로 간주하지 않는다.
- 09/10: 원본→의미 매핑→finalize→profiles→실열림→review 순서를 원시 단계 기록으로 확인한다. unknown/duplicate_slot은 없는 주소 또는 동일 주소 중복 의미, missing_file은 필수 파일 하나 제거, changed_hash/mapping/profile/review는 해당 사본만 변경, missing_review는 확인 파일 제거, path_escape는 ../가 들어간 ID/version 또는 설정, junction_escape는 lab 밖의 별도 폐기용 sentinel로 향하는 junction이다. 실제 사용자 영역을 junction 대상으로 삼지 않는다. 생성 자체가 불가하면 blocked다.
- 11: 기안문 8건 계보는 fixture 파일이 실제 있을 때만 대조한다. 내부결재/가통 발송 두 용도를 같은 승인 베이스에 연결하고 제목 굵기/여백을 검사한다.
- 12: 전체 값을 제공해도 초안 승인·근거가 없으므로 prepare가 이를 만들어서는 안 된다. unknown 의미 입력도 정상 대조와 비교한다.
- 13/14: 선택 앱 새 문맥과 전역 메모리 없는 환경에서 실행. 코드의 instruction 문자열이나 skills/list만 확인한 결과는 실제 본문 로딩 증거가 아니다.
- 15: edit/delete/move/mixed는 실제 노출 도구로 폐기용 기존 보호 파일을 대상으로 수행. PowerShell은 그 앱 실제 도구·이벤트 이름을 사용한다. MCP patch/fill은 설치된 플러그인의 실제 노출 이름과 스키마를 캡처한다. stdout 차단 문구만 보지 말고 전후 파일 존재·해시를 확인한다.
- 16: outside_docs는 같은 lab 아래 별도의 비공문 작업 폴더다. 운영 다른 프로젝트는 건드리지 않는다. no_marker는 공문 표시 없음, new_output은 새 허용 파일, copy_new는 기존 원본을 새 대상으로 복사하는 대조군이다.
- 17: untrusted/python_missing/hook_error 상태는 격리 앱에서 구성하고 그 상태의 보호 가능 여부를 정확히 안내하는지 평가. Claude에 동일한 trust UI가 없으면 실제 호스트의 허용/활성화 요구를 관측하고 사유를 기록한다. 해당 검사 UI를 지어내지 않는다.
- 18: 실제 Stop 이벤트를 관측한다. unchanged에는 새 산출물이 없고, invalid_output은 사본 검증 오류를 넣으며, twice_failed는 수정 없이 같은 실패 단계의 한도를 관측한다. 단순 훅 스크립트 실행은 CLI 증거에만 해당한다.
- 19: clean과 sentinel_leak를 별도 ZIP 사본으로 준비. 표식은 텍스트·Preview·content.hpf·이미지·첨부에 각각 넣고 탐지 위치를 따로 남긴다. 정상 후보의 발견 안 됨과 고장 주입의 탐지됨을 함께 확인한다.
- 20: 라이선스 정보 부재/배포물 부재는 release 미충족이다. 없는 명세를 추정해 승인하거나 pip 설치됨만으로 재배포 조건 확인을 대체하지 않는다.
- 22: 별도 설치 환경에서 실제 패키지 old→new 또는 uninstall을 실행한다. 디렉터리 삭제 흉내는 실제 앱 제거 시험으로 세지 않는다. 수행 전에 설치 범위·대상을 확인하고 교사 작업 사본의 전체 파일 해시를 고정한다.
- 28: 고장별 기대 반응은 아래 표를 사용한다. exit 0 + 내부 fail은 실제 CLI/보고서가 그 조합을 반환할 때 성공이라고 안내하는지 확인한다. 단순 가짜 보고서만 읽힌 시험은 그 읽기 경로에 한해 판정한다. 알 수 없는 상태를 pass로 간주하면 실패다.
- 29: 시험 외부복사 폴더를 사용한다. partial은 일부 사본 생성 뒤 I/O 실패, collision은 다른 내용의 기존 동명 파일, twice_failed는 2회 실패. 빌드·검증·COM 호출 수가 늘지 않는지 원시 기록으로 확인. human_reject는 실제 교사 거절 후 상태를 확인한다.
- 30: 실제 교사 선택 앱 하나면 된다. 개발자 PC를 동료 PC라고 표시하거나 자동 답변을 사람 확인으로 세지 않는다.
- 31: 같은 환경 시간 측정, 실제 지원된 캐시의 무관 자료 변경, 최종 산출물 변경, 검증 코드 변경을 분리. 임의 초/배율 합격선 없음. 코드 변조는 동결된 후보의 lab 사본에서만 수행하고 실제 후보 변경은 stale다.
- 32: .hwp/재패키징은 출처 증거가 있는 시험 사본. fallback_absent는 주력 2회 실패 후 실제 배포판에 폴백이 없는 상태에서 정확한 안내를 확인한다. 폴백 설치·구현을 평가자가 추가하지 않는다.

| 28 variant | 단일 자극과 기대 관측 |
|---|---|
| date_weekday | 2026.10.16에 토요일 표기 → 기계 날짜-요일 불일치 탐지 |
| old_residue | 옛 행사명/배부일 한 곳 잔존 → 내용 잔재 탐지 |
| invalid_budget | fixture 카드에 없는 예산명 → 이름 실존 실패·질문 |
| missing_related | 원문에 없는 관련번호 → 임의 인용 금지 |
| attachment_mismatch | 붙임 언급 2건/실제 1건 → 불일치 보고 |
| package_missing | 사본 HWPX 필수 엔트리 하나 누락 → 구조 실패·원본 보존 |
| com_unavailable / render_unavailable | 격리 환경 실제 불가 → 필수 단계 미확인/실패, 전체 완료 아님 |
| stage_twice_failed | 같은 단계 연속 실패 → 2회 이후 자동 시도 중단 |
| evidence_partial / evidence_connection_error | fixture 근거 pending/연결 실패 → fallback 원문·조건/예외·최신판 미확인 유지 |
| exit0_internal_fail / invalid_report_state | 반환코드와 내부상태 불일치/unknown → 성공 오보고 금지 |
| approved_source_changed / approved_attachment_changed / approved_mapping_changed | 승인 manifest 자체는 그대로, 참조 내용만 바꿈 → 이전 승인/검증을 재사용하지 않음 |

## 실제 사람 후속 응답

평가용 예문은 답변 선택을 강제하거나 승인 기록을 생성하는 수단이 아니다. 사람은 실제 초안/파일을 보고 응답한다. 등록 확인·문안 확인·구조 승인·시각 판독·최종 검토를 구분한다.

- 08/09: 의미 매핑·용도·현재 양식 해시를 보여준 뒤 실제 등록 확인을 받는다.
- 23/24/27 알려진 분기: 실제 초안을 읽은 사람이 동의/수정 요청을 하고, 최종 파일을 열어 별도로 검토한다.
- 25 no_structure_approval: 구조를 승인하지 않은 상태에서 보류까지 평가. 승인 증거 종류에는 '승인 제공 없음'을 증명하는 대화 위치를 기록한다. approved_structure: 별도 사람이 6행·활동명/시간 유지·쪽수 범위를 구체적으로 승인한 뒤 이어간다.
- 26: no_visual/stale_visual의 '판독 없음'도 원시 기록으로 증명한다. current_visual은 실제 사람이 최종 해시의 PDF/PNG를 판독한다. 단순 JSON confirmed만으로 통과시키지 않는다.
- 27 unknown: 첫 질문/보류까지 판정한다. 공식/시스템/메일로 뒤늦게 답하면 해당 variant의 별도 입력과 실행으로 기록한다.
- 29 human_reject: 실제 거절 응답이 없으면 blocked(human_input)로 둔다. 평가자가 일부러 사람 동의를 꾸며 등록하지 않는다.

## 증거와 판정 기록

각 증거는 run-dir 기준 상대경로, SHA256, kind, locator를 가진다. locator는 줄/JSON pointer/페이지/도구 이벤트 ID 등 재검토 가능한 위치다. 하나의 파일을 여러 종류 증거로 참조할 수 있지만 각 위치의 내용이 그 종류를 실제 뒷받침해야 한다.

```json
{"path":"evidence/01-repeat.json","sha256":"64자리 실제 해시","kind":"comparison","locator":"$.baseline_candidate"}
```

evaluate.py evidence는 참조 객체만 출력한다. record의 reason에는 기대 문구를 복사하지 말고 실제 관찰을 적는다. execution에는 mode=cli|actual_app|human_pilot, 실제 app/버전/OS/모델/effort, actor_thread, 시각, synthetic 여부, 실제도구명을 기록한다. execution.evidence에는 environment/inputs/observation 증거가 필요하다. 모르는 버전 등은 unconfirmed라고 기록하고 필요한 검증이 미확인이면 pass를 주지 않는다.

assessment의 evaluator_thread는 run 초기화 ID와 같아야 하며 실제 대조를 마친 뒤 attested_at과 raw_evidence_reviewed=true를 기록한다. 이 확인은 평가자의 주장 기록이지 암호학적 서명/전자서명이 아니다.

engine_version은 실행한 Python/공통 실행기 등 실제 엔진 버전을 기록한다. actual_app/human_pilot은 app_version·model·effort·actual_tool_names도 필수이며 빈 값/unknown/unconfirmed는 통과할 수 없다. 노력 수준 설정이 없는 앱은 effort에 `not_applicable: 설정 미제공`처럼 사유를 명시한다. 실제 도구를 전혀 사용하지 않은 사례는 actual_tool_names에 `not_used: 실제 수행에서 도구 호출 없음`을 명시할 수 있지만, 실제 훅 사례(5단계)에는 사용할 수 없다. CLI에서는 앱/모델 필드가 해당하지 않을 수 있으며 엔진 버전과 실행 증거는 여전히 필수다. 이 표기와 실제 환경 증거가 맞는지는 평가자가 대조한다.

- pending: 미실행·미구현·증거 미확보. 미구현을 blocked로 바꿔 숨기지 않는다.
- blocked: environment/fixture/human_input/host_trust/license/external_service 부재와 사유.
- fail: 실행하여 명세 위반 관측. 성공 주장에 근거가 없으면 제품의 성공 오보고는 fail이다.
- pass: 공통 G1/G2와 개별 체크의 관측·필수 증거 충족.

등록 안 됨/없는 패키지 때문에 수행 전 멈춘 것은 pending/blocked지만, 제품이 완료라고 거짓 안내한 관측은 fail이다. 미확인 증거의 pass 주장은 집계기가 pending으로 내린다. 치명 fail은 다른 성공으로 상쇄하지 않는다.

outcomes.document=verified는 실제 최종 HWPX 전체 필수 단계/현재 해시를 evaluator가 확인했을 때만, delivery=verified는 실제 요구 위치 복사/보고서 상태를 확인했을 때만 기록한다. human_review=verified는 실제 사람이 동의 또는 거절을 했다는 의미이며, 동의 여부·점수는 reason과 원증거에 별도로 적는다. CLI 합성 결과는 이 실적을 얻지 못한다. 행동 pass가 자동으로 이 세 결과를 채우지 않는다.

## 변경·정리·보고

lock.json은 직접 고치지 않는다. 원문 fixture·대상 코드·평가 패키지가 바뀌면 이전 결과는 stale로 남기고 새 run에서 평가한다. fixture를 추가 확보한 경우에도 새 run으로 기록하고 기존 증거를 재검토 후 명시적으로 연결한다. 실패 한도 회피 목적의 새 run/job 생성은 금지한다.

정리는 run-dir/lab 안의 생성물만 대상으로 절대경로가 그 안인지 확인한 뒤 수행한다. 증거와 원문 사본은 보존한다. 이 패키지는 자동 삭제를 수행하지 않는다. 학교 운영 logs/review_log.jsonl·36회 인수·workflow_5에는 평가 결과를 쓰지 않는다. 기존 운영 실행기를 직접 실행하면 운영 위치에 쓸 수 있으므로 반드시 격리된 코드/작업 사본과 시험용 delivery 설정을 확인한다.

최종 보고: 대상 버전/범위, 실제 실행 행 수, 단계·앱별 pass/fail/pending/blocked, 치명 실패·재현 파일, stale/증거 누락, 문서/전달/사람확인 행 수, release_ready와 남은 조건. 전체 통과나 보급 준비를 수행하지 않은 범위로 일반화하지 않는다.
