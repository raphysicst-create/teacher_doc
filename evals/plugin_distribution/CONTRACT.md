# 구현 세션과 맞춘 관측 계약

2026. 9. 13. 구현 세션의 최종 인계와 [구현 결과](../../docs/플러그인-보급-구현결과-2026-09-13.md), [배포 안내](../../distribution/README.md)를 반영했다. **구현자의 계약·개발 검증 보고이며 독립 평가 결과가 아니다.** 정답은 개선 계획이며 구현이 미완성이라고 기대 결과를 낮추지 않는다. 실행 전에 실제 --help·등록 스키마·대상 해시를 새 binding으로 고정한다.

## CLI

```text
scripts/hwpdoc.ps1 [--workspace 작업폴더] 명령
init PATH --app claude|codex --skill-name 실제노출이름 [--school 이름 --prefix 접두어 --year 연도 --copy-to 경로]
add-template --id ID --version VERSION [--source HWPX | --mapping JSON | --review JSON | --review-draft] [--purpose 용도 ...] [--provenance native|converted|repackaged|unconfirmed]
list-templates
migrate-templates
prepare --job ID --document-type TYPE [--workflow W1|W2] [--template ID --version VERSION] [--source 원문 ...] [--values JSON]
setup-hooks --app claude|codex [--tool 실제도구명] [--apply]
setup-runtime (인수는 실제 --help 확인)
build --manifest JSON
validate (--job ID | --manifest JSON)
deliver --job ID [--draft]
status --job ID
doctor
```

--workspace는 현재 서브명령보다 앞에 둔다. 같은 실패를 새 job ID로 우회하지 않는다. init은 현재 운영 root/부모를 거절한다. setup-hooks는 제안 생성 후 --apply로 기존 등록을 보존해 병합한다. 등록·신뢰·실제 차단은 별도 증거이며 실제 설치/업데이트/제거는 미검증이다.

## 관측할 파일·상태

- 작업 설정: .hwpdoc/workspace.json, kind=hwpdoc-workspace, version=1, app/skill_name, school{name,document_prefix,academic_year}, delivery{external_copy|null}, references, timetable_mapping, preferences, connections.
- PC 설정: %LOCALAPPDATA%/hwpdoc/runtime.json의 version=1, python. 격리 시험에는 HWPDOC_PC_DATA, HWPDOC_WORKSPACE를 자식 프로세스 범위에서 지정한다. 실제 사용자 설정에는 쓰지 않는다.
- 등록: .hwpdoc/templates/ID/VERSION/. original.hwpx/template.hwpx/slots.json/mapping.json/budget.json/structure.json/registration.json/review.json. mapping은 의미→실제 슬롯 주소, purposes는 복수 배열.
- 등록 상태: draft → awaiting_review → registered. 목록에는 legacy_available/changed/invalid. 이관은 human_review_pending이며 자동 전환이 아니다.
- review 초안은 confirmed/by/at/record, 필수 파일 hashes, purposes, provenance를 요구하며 등록 초안과 일치해야 한다. 비native는 현재 파일 해시의 PDF/PNG 판독 증거도 요구한다. **필드 존재는 실제 사람 확인의 증거가 아니다.**
- prepare manifest version=2는 draft_approval.confirmed=false, evidence.record 빈 값, checks.applicable=null, unresolved를 남긴다.
- prepare는 status=unconfirmed, 종료 2다. v2는 원문/첨부/evidence/source/reference의 현재 해시와 작업 폴더 상대경로를 요구한다. 승인 해시는 draft_approval를 제외한 입력 전체의 정렬 JSON SHA256이며 실제 승인 뒤 기록한다.
- 보고서는 version=1 + path_format=2이고 workspace:/plugin: 참조를 사용한다. v1 절대경로 기록도 읽는다. 역사 기록인 진단 문자열/원문 출처의 옛 경로와 현재 실행에 쓰는 경로를 구분한다. top-level 변환만 보고 이동 완료로 판정하지 않는다.
- 제품 전체 상태 pass/fail/unconfirmed; 단계 pass/fail/unconfirmed/not_applicable; 전달 human_review=pending, sent=false. 평가 장부의 pending/blocked와 다른 축이다.
- 후속 인계: 보고서는 runtime(Python 경로/버전·패키지 버전)을 기록하며 변경 또는 구형 보고서의 기록 부재는 status=unconfirmed다. validate는 입력·원문이 불변일 때만 기존 문안 승인/manifest 해시를 보존하고 tool_updates/runtime_updates를 남겨 전체 재검증한다. case 07/28/31에서 현재 구현과 이 계약을 대조한다.
- 후속 인계: add-template --review-draft는 필요한 COM PDF 대조와 전체 PNG를 준비하지만 confirmed=false 및 awaiting_review를 유지한다. 준비된 판독 자료가 실제 사람 확인을 대체하지 않는지 case 08/09/26에서 확인한다.

## 알려진 미충족과 주의

- add-template 단계 실패는 이제 비영 종료 코드라고 인계됐다. registry draft/awaiting_review/registered와 단계 fail/unconfirmed는 별개다. 과거 exit 0 결함을 현재 상태로 단정하지 않되 case 28의 성공 오보고 회귀 기준은 유지한다. doctor 종료 0도 인수 pass가 아니다.
- 초기 47개 시험 중 보고서 교체 오류가 있었고 이후 수정됐다. 구현자는 개발 회귀시험 69개에 이어 후속 인계에서 89개 통과를 보고했다. 독립 평가자는 원시 출력과 대상 해시를 확인하며 이 수치를 실제 앱/교사 인수로 합산하지 않는다.
- 학교 자료 설정, 업무 절차 workflow.md, 훅 제안/병합, 배포 정의가 구현됐다고 인계됐다. 실제 앱 본문 로딩·차단·신뢰, 새 PC·긴 경로, 설치·업데이트·제거·교사 시범은 미검증이다.
- 기존 5종은 초기 inventory의 human_review_pending에서 후속 실제 등록 초안까지 준비됐다고 인계됐다. 사람 승인 전 draft이며 기존 선택 경로는 유지된다. 8건 계보는 header·여백을 읽기 대조한 결과이므로 새 COM/시각 검토가 아니다.
- 배포 정의는 초기 67개에서 후속 70개 파일 허용 목록으로 변경됐다. 파일별 권리/개인정보 해시 검토와 의존성 8개 조건 확인을 요구한다. 현재 해당 기록 미확인으로 blocked이며 설치 가능한 배포본은 만들지 않았다고 인계됐다. 숫자·목록은 평가 후보에서 다시 확인한다.
- 배포 스킬 경로는 skills/hwpx, 개발 정본은 .claude/skills/hwpx다. Codex descriptor에 hooks 필드를 넣지 않고 workspace 등록을 별도로 한다. 실제 앱 계약 부합 여부는 독립 평가한다.
- config/legacy-workspace.json에는 현 학교 설정이 있으므로 배포 허용 목록에 넣지 않는다.
- 새 코드 작성됨 ≠ CLI 동작 검증 ≠ 실제 앱 인수 ≠ 사람 품질 확인 ≠ 배포 준비 완료.
