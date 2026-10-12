# 중단된 검사 명시적으로 재개하기 (에이전트용)

같은 단계 2회 실패의 자동 중단은 유지한다. 먼저 원인을 해결하고 실제 사용자에게 해결 내용과 재검증할 단계를 설명하여 재개 확인을 받는다. 카운터를 지우거나 새 job/version으로 같은 실패를 우회하지 않는다. 이 절차는 승인된 문안·업무 근거의 변경 승인이 아니다.

## 문서 검증

1. 원본은 보존하고 work 사본/필요한 도구·실행 환경만 원인에 맞게 수정한다. 승인 입력 manifest/초안/원문·근거가 바뀌었으면 이 명령으로 이전 승인을 재사용할 수 없다
2. `status --job <작업>`에서 `resume_challenges.<단계>`의 현재 `stage_sha256`, `document_sha256`, `input_sha256`을 읽는다. 수정 후 다시 status를 실행한다. 이 값은 persisted report와 CLI의 경로 인코딩 차이를 처리한다
3. 실제 사용자 확인과 원인 해결을 검증한 파일을 작업 폴더에 보존한다. 에이전트가 다음 JSON을 작성하되 확인자·원문·시각·진단 결과를 지어내지 않는다. 아래는 필드 설명용이며 실행 가능한 승인 예시가 아니다

```json
{
  "confirmed": false,
  "by": "실제 확인자",
  "at": "실제 확인 시각 ISO8601, 시간대 포함",
  "record": "실제 재개 확인 원문/출처",
  "cause": "확인한 실패 원인",
  "resolution": "실제로 고친 내용과 진단 결과",
  "stage": "content",
  "stage_sha256": "status의 값",
  "document_sha256": "status의 현재 work 값",
  "input_sha256": "status의 기존 승인 입력 값",
  "evidence": [{"path": "작업 폴더 기준 진단 또는 수정 증거 파일", "sha256": "실제 파일 해시"}]
}
```

4. 실제 확인을 받은 뒤 기록을 완성하여 같은 전용 Python 실행기로 `resume --job <작업> --stage <단계> --record <기록 상대경로.json>`을 실행한다
5. 이 명령의 결과는 `unconfirmed`이며 정상적으로 exit 2일 수 있다. `resumes`/`history`와 단계의 `retry_baseline`을 확인하고, 이어 `validate --job <작업>`으로 전체 검사를 실제 실행한다. 재개만으로 pass/등록/전달 허용 상태가 되지 않는다

실패 당시 문서·도구·runtime fingerprint와 현재가 같으면 새 설명이나 증거 파일만으로 재개할 수 없다. 외부 Windows 한글 환경이 원인이었던 `hancom`, `render`, `review_render`만 예외가 있다. 실제 사람이 외부 복구와 검증을 확인했을 때 `external_environment`에 `confirmed=true`, `by`, `at`, `change`, `verification`을 추가한다. 외부 확인 시각은 중단 이후·재개 승인 이전이어야 한다. `content` 같은 내용 단계에는 이 예외가 적용되지 않는다. 소프트웨어는 확인 기록의 연결을 검사하며 사람 진술의 진위를 대신 보증하지 않는다.

누적 실패 수와 이전 단계 결과는 삭제하지 않는다. 승인된 재시도 구간에서 다시 2회 실패하면 또 중단하며 원인을 다시 해결해야 한다. 확인 JSON·해시가 일치하는 증거 사본은 해당 작업의 `resumes` 폴더에 남는다. 상세 증거에는 원문이 포함될 수 있으므로 외부로 보내지 않는다.

## 양식 등록 검토

`add-template --id <이름> --version <버전> --resume --stage <단계> --resume-record <상대경로.json>`을 사용한다. 현재 `registration.json.stages[단계]`의 정렬 JSON SHA256이 stage_sha256이다(UTF-8, ensure_ascii=false, sort_keys=true, separators=(',', ':')). document_sha256은 현재 template.hwpx, input_sha256은 현재 등록 파일 해시 사전의 같은 정렬 JSON SHA256이다. 파일 사전에는 존재하는 `original.hwpx`, `template.hwpx`, `slots.json`, `mapping.json`, `budget.json`, `structure.json`만 포함한다.

등록 자체는 완료되지 않는다. 반환된 next_action에 따라 기존 mapping으로 검사를 다시 하거나 `--review-draft`를 재실행한다. 이후 현재 파일·용도·매핑에 연결한 실제 사용자 `--review` 확인이 여전히 필요하다. PyMuPDF 같은 선택 의존성이 없으면 먼저 환경 미준비로 표시하며 문서 검토 실패 횟수를 소모하지 않는다.
