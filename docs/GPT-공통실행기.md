# Hwp_doc 공통 실행기

프로젝트 지침(`CLAUDE.md`) → `hwpx` 정본 → 실행기 → 기존 자료로 구성한다. 자동 생성은 기존 슬롯 템플릿 5종만 지원한다. W2·비정형 HWPX는 기존 생성 경로를 사용한 뒤 같은 `validate`로 검사한다. 신규 XML 작성, HWP 변환, 승인된 표 구조 변경과 F4 폴백 재생성은 기존 경로를 유지한다.

## 실행

프로젝트 디렉터리에서 아래 PowerShell 진입점을 호출한다. 이 PC의 Windows PowerShell은 스크립트 실행이 기본 차단되어 있어 **해당 프로세스에서만** 실행정책을 지정한다. 전역 실행정책·샌드박스·훅 신뢰 설정은 변경하지 않는다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hwpdoc.ps1 doctor
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hwpdoc.ps1 build --manifest 작업입력.json
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hwpdoc.ps1 validate --job 작업ID
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hwpdoc.ps1 deliver --job 작업ID
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hwpdoc.ps1 status --job 작업ID
```

기존 경로에서 만든 문서는 `validate --manifest 작업입력.json`으로 작업용 사본을 만든다. 이 경우 `source`, `reference`, `expected_values`를 입력한다. `source` 원본을 수정하지 않는다.

`build` 성공은 생성만 완료했다는 뜻이다. `validate`까지 통과해야 검증 완료본이다. `deliver --draft`는 미확인/실패 결과를 **미확인_검토초안.hwpx**로 저장하며 사람 검토가 필요하다. build 자체가 미완료면 편집하지 않은 양식 사본은 배달하지 않는다.

종료 코드: build 0=슬롯 생성 성공, validate/status 0=전체 통과·1=실패·2=미확인, deliver 0=해당 상태의 검토본 복사 성공·1=복사 실패·2=배달 불가. doctor는 JSON의 개별 상태를 확인한다. 모든 산출물은 사람 검토 대기이며 발송하지 않는다.

## 입력 계약

입력 경로는 프로젝트 기준 상대경로 또는 절대경로다. 출력 경로는 실행기가 작업ID로 결정한다. 다른 프로젝트에 파일을 만들지 않는다.

| 필드 | 기록 내용 |
|---|---|
| `job_id`, `workflow`, `document_type` | 경로 없는 작업ID, W1/W2, 문서 유형 |
| `template` | 가정통신문 / 가정통신문-회신형 / 가정통신문-고사안내 / 성립전예산요구 / 회의록-교과협의회 |
| `slots.template_sha256`, `slots.values` | 현재 양식의 SHA256, Reader 추출 슬롯 키와 값. 실제 템플릿에서 다시 추출해 주소를 확인한다 |
| `shared_values_file` | 본문·첨부의 모든 생성 작업이 함께 참조하는 공유값 JSON. 각 작업에서 같은 파일을 사용하고 생성 중 변경하지 않는다 |
| `shared_values` | 단일 문서의 값 객체. 공유값 파일이 있으면 파일 값이 우선. 여러 문서 세트에서는 파일을 사용한다 |
| `sources` | 유사 공문/수신 원문/근거 `{path: ...}` 목록 |
| `exploration.record` | W1 유형·키워드·유사 공문·양식 선택 기록 |
| `evidence.record` | 초안 전 업무지침 조회 기록 JSON 파일 |
| `draft` | `{path, sha256, created_at}`. ISO 8601 시간대 포함 |
| `draft_approval` | `{confirmed, by, at, record, input_sha256}`. 실제 사용자 확인 후 작성 |
| `attachments`, `attachment_mentions` | 첨부 `{path, title}` 목록, 본문에서 확인한 붙임 제목 목록. 제목·파일 수·본문 존재를 대조 |
| `content_rules` | 기존 content_guard CLI의 require/forbid/정규식. `[[필드]]` 잔재도 자동 검사 |
| `reuse_review` | `{record, names, dates}`. 직전 문서 고유 명칭·옛 날짜는 모두 forbid에 포함. 빈 목록이면 `names_empty_reason`/`dates_empty_reason` 필요 |
| `checks` | budget_names/related/timetable 각각 적용 여부와 값 또는 해당 없음 이유 |
| `activities` | `{location, items, slot_keys}` 목록. 활동 수가 슬롯 수를 넘거나 슬롯값과 활동명이 다르면 기존 구조 변경 경로로 반환 |
| `base_provenance` | native / converted / repackaged. 미제공은 렌더 조건 미확인 |
| `over_budget_cells` | 기존 수동 경로에서 예산을 초과한 셀 목록. 자동 우회 없이 렌더·육안 증거 대기 |
| `visual_review` | 기존 수동 경로에서 완료한 실제 판독의 confirmed/by/at/record, document_sha256, cells, pdf `{path, sha256}`, images `[{path, sha256}]`. 최종 파일 및 증거 해시가 맞아야 인정 |
| `environment` | 실제 앱·앱 버전·엔진 버전·모델·reasoning effort. 알 수 없는 값은 미확인으로 기록 |
| `unresolved` | 사용자 미제공·판단 보류 목록. 비어 있지 않으면 검증 완료 상태가 되지 않음 |

슬롯 매핑 예: `{"p:13":{"shared":"title"},"p:40":{"shared":"distribution_date"}}`. 이는 문서별 추출 주소 예시이며 다른 템플릿에 그대로 적용하지 않는다. 한 셀을 `p:`와 `cell:`로 중복 지정하면 최종 슬롯값 대조에서 어긋난 값을 통과시키지 않는다.

승인 입력 해시는 `draft_approval`을 제외한 JSON을 `ensure_ascii=False, sort_keys=True, separators=(',', ':')`로 직렬화한 UTF-8 SHA256이다. `scripts/hwpdoc.py`의 `approval_payload`·`json_hash`를 사용할 수 있다. 이 해시는 사용자 승인 자체를 만들어 주지 않으며 승인 기록의 진위를 보증하는 전자서명이 아니다.

업무지침 기록 JSON에는 `status`, `steps`, `conditions`, `exceptions`, `pending_items`, `reviewed_at`, `freshness`가 필요하다. 정상 조회 steps는 `find_tasks → get_task_guide → search_task_evidence → read_evidence`. partial/needs_context/unsupported/connection_error이면 확인한 `fallback_sources`를 기록한다. `freshness`가 verified가 아니면 최신판 미확인으로 보존한다. 실행기는 기록 존재·순서만 확인하며 업무 해석을 보증하지 않는다.

조회 도구 입력:

```json
{
  "budget_names": {"applicable": true, "names": ["원문에서 확인한 모든 예산 항목명"]},
  "related": {"applicable": true, "numbers": ["실존 문서번호"]},
  "timetable": {"applicable": false, "reason": "수업 대체·융합교과 계획이 없음"}
}
```

timetable 적용 시 `dates`, `periods`, 필요하면 `grades`를 지정한다. 날짜·과목·시수는 도구 출력에서 초안으로 반영하고, 표 전 항목/관련 인용이 입력 목록에 빠짐없이 담겼는지는 초안 검토에서 확인한다. 관련번호 조회 성공은 인용 날짜·원문의 모든 의미를 자동 검증한 것이 아니다.

W2에는 `received` 객체의 `summary`, `requirements`, `deadline`, `submission_method`, `document_number`, `issue_date`, `source_quote`가 필요하다. 제출방법은 official_reply→회신 시행문, system/email→내부결재다. 미확인이라면 질문하고 초안 생성 입력을 확정하지 않는다.

## 검사·기록·저장

구조 → 네임스페이스 → finalize → layout → page_guard → COM → 조건부 렌더·육안 → content/승인값/gonmun/조회 도구/첨부 → 신구대조 순서다. 각 단계는 pass/fail/unconfirmed/not_applicable과 이유·명령·경고·전후 해시·실패 횟수를 기록한다. 빠른 `validate_pipeline.py`를 호출하지 않는다.

작업 상태는 `.hwpdoc/jobs/<ID>/report.json`, 검토본은 `output/<ID>/`이다. 원본·입력·근거·검증 코드가 바뀌면 이전 완료 근거를 재사용하지 않는다. 작업용 HWPX만 바뀌면 전체 재검증할 수 있지만 승인 입력/원문이 바뀌면 새 확인과 새 작업ID가 필요하다. 같은 단계 2회 실패 후 자동 재시도하지 않는다. 새 ID를 실패 한도 우회 용도로 만들지 않는다.

page_guard 프로파일은 원본의 **finalize 완료 사본**에서 생성한다. 결과물을 자기 자신의 기준으로 승인하지 않는다. COM은 프로세스 간 잠금으로 직렬화된다. 시간 초과 시 미확인으로 기록하고 잔존 한글 프로세스를 확인한다. 사용자의 다른 한글 프로세스를 강제 종료하지 않는다.

현재 학교 설정은 `delivery.external_copy: null`이며, 검토본·첨부·보고서는 `output/<ID>/`에만 저장한다. OneDrive 자동 복사는 사용하지 않는다 (2026. 10. 12. 사용자 요청). 외부 복사가 비활성화된 작업의 `copy.status`는 정상적으로 `not_applicable`이다.

최종 사람 검토 결과는 기존 `scripts/log_review.py --file ... --type W1|W2 --approved yes/no --score 1-5`와 `--summary`로 즉시 기록한다. 실행기는 사용자 대신 점수·동의를 만들지 않는다.

발송 전 한글로 열어 확인해주세요
