# teacher_doc 배포 준비 및 설치

프로젝트·플러그인·배포 폴더 이름은 `teacher_doc`, 기본 명령은 `scripts/teacher_doc.ps1`이다. 기존 `scripts/hwpdoc.ps1`/`.py`, `.hwpdoc` 기록과 PC 데이터 경로, `HWPDOC_*` 환경변수는 호환용으로 유지한다.

현재 버전은 0.1.0 구현 후보다. **라이선스·포함 자산 검토와 앱별 독립 인수·교사 시범 사용이 완료되기 전에는 보급 완료로 표시하지 않는다.** 이 폴더는 배포 정의이며 설치 가능한 공개 릴리스가 아니다.

## 설치와 작업 폴더

허용 목록과 권리 검토가 통과한 패키지만 별도로 만든다. Claude Code에는 `.claude-plugin/plugin.json`, Codex에는 `.codex-plugin/plugin.json`이 들어간다. 선택한 앱에서 로컬 플러그인을 설치한 후 실제 노출된 hwpx 스킬 이름을 확인한다. 현재 운영 저장소를 공개본으로 바꾸거나 운영 파일을 삭제하지 않는다.

```powershell
# 설치된 플러그인 루트에서 실행. 작업 폴더는 설치 폴더 밖에 둔다.
./scripts/teacher_doc.ps1 init 'C:/교사 작업/공문' --app codex --skill-name '앱에서 확인한 이름'
./scripts/teacher_doc.ps1 --workspace 'C:/교사 작업/공문' doctor
./scripts/teacher_doc.ps1 --workspace 'C:/교사 작업/공문' setup-hooks --app codex
```

setup-hooks는 먼저 등록 제안을 만든다. 실제 이벤트/도구 이름을 확인한 후 `--tool`로 matcher를 지정할 수 있다. `--apply`는 기존 등록을 보존하여 병합하며 신뢰를 자동 승인하지 않는다. Codex의 해당 환경에서 프로젝트 훅 등록과 신뢰를 확인하고 새 작업에서 실제 차단을 시험한다. 목록 노출·등록 성공·신뢰·실제 차단은 서로 다른 증거다. 동적 셸/자식 프로세스 쓰기는 정적 훅의 완전 보호 범위가 아니다. 선택하지 않은 앱 설정을 함께 만들 필요가 없다.

Windows 훅 명령은 앱별 셸 차이에 맞춰 생성한다. 훅 실행기 업데이트 후에는 해당 앱의 `setup-hooks --apply`를 다시 실행한다. Codex에서는 `/hooks`로 변경된 정의를 검토·신뢰해야 한다. 로컬 스크립트 실행 정책은 훅 프로세스에만 적용하며 시스템·사용자 레지스트리 정책을 바꾸지 않는다. 관리자가 강제한 실행 정책이나 훅 시간 초과를 보호 성공으로 간주하지 않는다.

Python 3.12는 PC별 runtime.json 또는 해당 PC 설치 경로/레지스트리에서 찾는다. 의존성을 별도 환경에 설치하려면 `scripts/install-dependencies.ps1`을 사용한다. PC 데이터는 기본 `%LOCALAPPDATA%/hwpdoc`이며 `-DataDir`로 격리 시험 위치를 지정할 수 있다. 기본 XML/생성/PDF 읽기, Windows COM, 학교 자료(xlsx/xls), 시각 렌더 의존성을 나눴다. `-SchoolData`, `-Visual`은 해당 기능이 필요할 때 선택한다. PyMuPDF는 무료 AGPL-3.0으로 사용한다(2026. 9. 13. 사용자 확정). 배포본에는 AGPL 전문·저작권 고지와 AGPL 적용 대상 프로그램의 해당 버전 대응 소스 및 필요한 설치·빌드 자료를 제공한다. 라이선스 선택은 완료됐으며, 소스 제공·고지의 실제 이행은 배포 준비에서 검증한다. 버전은 개발 환경 관측값을 고정했으며 깨끗한 PC에서 설치 성공을 별도 확인해야 한다.

한글 프로그램과 FilePathCheckerModule 보안모듈은 Python 패키지와 별개다. doctor에서 미등록/실행 불가로 나오면 설치된 한글의 자동화 환경을 확인한다. Node.js/kordoc 및 school_task_guide는 선택 연결이다. 없으면 스킬에 적힌 추출/편집/신구대조 및 원문 확인 경로로 진행하고 미사용·미확인 사실을 보존한다.

현재 PC의 별도 가상환경과 한글·공백이 있는 격리 작업 폴더에서 설치·doctor·합성 양식 등록 기계 단계·COM/PDF/PNG를 확인했다. init은 생성할 디렉터리가 248자 이상이거나 파일 경로가 260자 이상이면 생성 전에 짧은 경로를 안내한다. Windows 장경로 설정만으로 한글·앱 전체의 지원을 가정하지 않는다. 다른 계정/PC와 정식 패키지의 앱별 전체 인수는 별도 검증 대상이며 Mac과 두 앱 동시 실행도 지원 대상으로 표시하지 않는다.

## 학교 자료

작업 폴더 `.hwpdoc/workspace.json`에서 references.timetable_source/timetable, budget_source/budget, related를 상대경로로 지정한다. 원문은 작업용 사본으로 가져온다.

- 시간표 첫 지원 형식: xlsx, `timetable_mapping.format=grade-columns-v1`. sheet(없으면 활성 시트), grades(식별자→표시명), day_columns(요일→그룹 순서별 1-based 열 배열), period_rows(교시 순서별 1-based 행 배열), subject_full, non_subject, 선택 strip_pattern을 명시한다. 학년·반 구분은 식별자와 표시명으로 설정한다. 병합 셀은 좌상단 값으로 읽는다. 다른 형식을 임의 추정하지 않는다.
- 사업관리카드 첫 지원 형식: 구형 xls 첫 시트, 0열 이름/들여쓰기, 1열 산출내역, 2열 금액. 처음 4행은 헤더, 이름만 있는 행의 들여쓰기 5 이하가 세부사업, 그보다 깊으면 세부항목이다. 다른 배치는 지원 어댑터가 필요하다. 이름만 실존 대조하며 금액을 자동 확정하지 않는다.
- 관련번호: Markdown frontmatter의 문서번호/제목/시행일/결재일/관련 목록. 학교 document_prefix를 명시한다. 시행일이 있으면 먼저 사용한다.

원문 갱신 후 `HWPDOC_WORKSPACE`를 지정하여 `refresh_reference.py --only timetable|budget`를 실행한다. 파생 JSON/MD를 수동 편집하지 않는다. 원문과 파생 경로를 같게 지정하지 않는다.

## 양식 등록·작성

양식 매핑 검증이 끝나면 `add-template --id <이름> --version <버전> --review-draft`로 검토 입력을 준비한다. 변환/재패키징/출처 미확인 양식은 한글 PDF 내보내기·원문 대비 검사와 전체 페이지 PNG 생성을 수행한다. review.draft.json의 confirmed/by/at/record는 승인 없이 채우지 않는다. 검토 준비 자체가 막히면 단계 실패/미확인 이력을 유지한다. 기존 검토 초안은 덮어쓰지 않는다.

스킬의 references/workflow.md를 먼저 읽는다. add-template의 source → mapping → review 순서, prepare → 실제 문안 확인 → build → validate → deliver 순서를 따른다. 등록 review에는 confirmed/by/at/record, hashes, purposes, provenance가 필요하다. provenance는 등록 초안의 원본 종류와 일치해야 한다. 실제 확인 기록을 파일과 연결할 뿐, 확인 행위의 진위를 자동 보증하지 않는다. 기존 5종은 운영 프로젝트에서 계속 사용할 수 있다. migrate-templates는 기존 파일·해시·출처를 모아 사람의 등록 확인을 기다린다. 학교가 들어간 기존 양식은 이 공개 후보에 포함하지 않는다.

prepare는 교사가 복잡한 입력 JSON을 직접 작성하라는 기능이 아니다. 에이전트가 수집 가능한 정보를 준비하고 누락된 판단을 묶어 물은 뒤 실제 대화 근거로 입력을 완성한다. version=2 입력에서는 sources/attachments의 sha256, evidence.sha256, source/reference를 쓰는 경우 각각 source_sha256/reference_sha256을 현재 파일에서 수집한다. 초안 승인 input_sha256은 draft_approval를 제외한 전체 입력의 정렬 JSON SHA256이다. 이를 기록하는 것은 실제 승인을 받은 뒤이며, 경로 이동/수정으로 승인을 만들어내지 않는다.

## 업데이트와 제거

### Codex CLI의 한글 COM 검사

`doctor`와 `validate`는 실행 중인 Windows 사용자·제한 토큰·데스크톱과 보안 모듈을 확인한다. `HANCOM_RESTRICTED_CONTEXT`이면 COM 객체를 만들기 전에 미확인으로 반환한다. 현재 PC에서 Codex의 `workspace-write` 제한 환경은 한글 COM 생성이 멈추므로, 이 환경의 전체 검증은 완료로 처리하지 않는다. 한글과 보안 모듈이 설치된 사용자 세션에서 실제 검증을 실행해야 한다. 실행기가 Codex·Windows 권한을 바꾸지는 않는다.

Codex CLI의 셸 도구는 전체 검증에 충분한 `timeout_ms`(300000)를 명시한다. 비동기 실행 도구가 세션 ID를 반환하면 같은 세션의 완료를 기다린다. 외부 셸의 기본 10초 종료와 실행기의 단계별 시간 초과를 구분하고, 이전 결과를 보존한 기존 작업으로 재개한다. 독립 CLI의 기본 설정 통과와 `workspace-write` 통과는 별도 시험이다.

### 기존 설치 유지

플러그인은 코드만 교체한다. 작업 폴더와 PC 데이터는 설치 폴더 밖에 유지한다. 새 설치 경로의 `setup-hooks --app <앱>`으로 제안을 확인하고 `--apply`로 적용한다. `.hwpdoc/hooks-<앱>-owned.json`의 소유 기록과 정확히 일치하는 이전 hwpdoc 항목만 교체한다. 다른 훅과 사용자 설정은 보존하며 수정된 관리 항목은 자동 교체하지 않는다. 변경 전 설정과 소유 기록은 `.hwpdoc/hooks-history/`에 남긴다. 소유 기록이 없는 과거 수동 등록은 자동 제거하지 않으므로 따로 확인한다.

코드·Python·패키지 버전이 바뀌면 status는 이전 검증을 미확인으로 표시한다. `validate --job <기존 작업>`은 입력·원문이 그대로인지 확인하고 전체 검증을 다시 수행한다. 기존 초안 승인과 manifest 해시는 유지하며 코드 해시 변경은 보고서 tool_updates, 실행 환경 변경은 runtime_updates에 기록한다. 과거 보고서에 실행 환경 기록이 없어도 재검증이 필요하다. 승인 입력이나 원문이 바뀐 경우에는 이 경로를 사용할 수 없다. doctor는 패키지의 실제 import와 고정 버전 일치 여부를 확인하며, 설치 흔적만으로 정상이라고 판단하지 않는다.

앱에서 플러그인을 제거해도 작업 폴더와 PC 데이터는 남겨둔다. 제거 전에 `setup-hooks --app <앱> --remove`의 제안을 확인하고 `--apply`로 적용하면 소유 기록과 일치하는 hwpdoc 훅만 제거한다. 교사 자료·PC 환경·다른 훅은 삭제하지 않는다. 코드만 사라진 훅은 실행 실패/미확인을 표시하며 보호 성공으로 보고하지 않는다. 실제 앱 업데이트/제거 시험은 별도 평가자가 수행한다.

기존 5종의 migrate-templates는 `.hwpdoc/templates/<이름>/legacy-1`에 원본 사본과 등록 초안을 만든다. 과거 슬롯/프로파일/README는 legacy 폴더에 보관하고 신규 검증 근거로 승격하지 않는다. mapping.proposed.json의 슬롯 키는 기계적 제안이며 에이전트가 실제 의미를 확인해야 한다. 실제 사람 확인 전에는 draft이고 기존 5종 선택 경로를 유지한다. 이관 조사 이후 원본이 바뀌면 source_changed로 표시한다.

변환·재패키징·출처 미확인 양식의 review.visual PDF/이미지는 작업 폴더 상대경로로 기록한다. 등록 때와 이후 양식 선택 때 모두 현재 파일 해시를 검사한다. 검토 파일이 사라지거나 달라졌으면 등록 양식을 사용할 수 없다.

## 배포 생성

다음 명령은 개발 저장소에서 실행한다. 배포본의 스킬은 `skills/hwpx/`에 들어가며 개발 정본 `.claude/skills/hwpx/`는 유지한다.

`release-files.json`은 허용 파일 목록이다. 권리 검토 기록은 source 경로별 sha256/license/source/permission_record/reviewed_by/reviewed_at/privacy_review/privacy_sha256을 요구한다. 개인정보 점검은 본문뿐 아니라 XML·Preview·메타데이터·이미지까지 포함한다. dependency_reviews도 라이선스와 적용 조건 확인 기록이 필요하다. 파일 변경 시 이전 검토 해시는 사용할 수 없다.

```powershell
./scripts/teacher_doc.ps1 --workspace 'C:/교사 작업/공문' status --job 작업이름
# 아래 Python은 runtime.ps1에서 확인한 실행 파일이다.
& $taskPython -X utf8 ./scripts/build_distribution.py --rights ./distribution/rights.pending.json
```

현재 `rights.pending.json`에는 파일별 권리·개인정보 검토가 기록돼 있다. 남은 배포 차단은 `xlrd==2.0.2` 과거 코드의 광고 조항과 AGPL 결합 조건이다. 고지 동봉이나 별도 pip 설치만으로 이 조건을 해소한 것으로 처리하지 않는다. 해당 조건을 해결한 뒤 현재 파일 해시로 게이트를 다시 통과해야 `--output <프로젝트 안 새 경로>/teacher_doc`으로 패키지를 만든다. 패키지 생성 성공도 별도 앱/교사 인수 완료를 뜻하지 않는다.

`prepare_distribution_assets.py`는 기본 content.hpf의 작성자·날짜와 proposal 예제의 과거 사업 내용을 제거한 배포 후보 사본을 distribution/assets에 준비한다. 운영 원본은 수정하지 않는다. preparation.json은 변환 전후 해시이며 권리 허가나 개인정보 검토 승인이 아니다. 허용 목록은 이 사본을 사용하며, 본문·미리보기·이미지의 파일별 검토는 여전히 필요하다. 패키지는 임시 폴더에서 모든 복사 해시를 확인한 뒤 완성 경로로 옮기므로 복사 실패를 설치 가능한 패키지로 남기지 않는다.

운영 프로젝트에 설치된 hwpx-fallback은 유지한다. 배포 후보에는 포함하지 않으므로 구조 검사 2회 실패 시 한글에서 새 HWPX 사본으로 저장하거나 지원 양식으로 재생성한 후 전체 검증하는 복구 경로를 안내한다. 원본 덮어쓰기와 검사 생략은 허용하지 않는다.

## xlrd 원저작자 표시

과거 시험 버전에서 사용한 xlrd의 원저작자 표시와 배포자 약속을 기록으로 유지합니다. 현재 배포 후보의 구형 Excel(`.xls`) 읽기는 MIT 라이선스의 `python-calamine==0.7.0`을 사용합니다. 기존 사업관리카드의 사용 셀 318개와 파생 예산 JSON이 이전 결과와 동일함을 확인했습니다.

> This product includes software developed by David Giffin <david@giffin.org>.

배포자는 향후 이 프로그램의 기능이나 사용을 소개하는 광고 자료를 제작하는 경우에도 위 표시를 반드시 포함합니다. 현재 별도 광고 페이지를 제작할 계획은 없습니다. xlrd의 기존 고지는 `licenses/dependencies/xlrd/LICENSE`에 기록으로 보존하며, 현재 XLS 읽기 의존성과 설치 목록에는 xlrd를 포함하지 않습니다. python-calamine과 기반 calamine의 MIT 고지는 `licenses/dependencies/python-calamine/`에 제공합니다.

## 무료 AGPL 소스·고지 제공

PyMuPDF의 무료 AGPL 선택과 소스·고지 준비를 완료했다. 배포 허용 목록에는 루트 LICENSE, NOTICE.md, CHANGES.md, SOURCE.md, SOURCE-BUNDLE.json과 licenses/의 구성요소별 고지를 포함한다. teacher_doc은 편집 가능한 소스로 제공하며 sources/에 PyMuPDF 1.28.0 및 MuPDF 1.28.0의 수정하지 않은 소스 압축본(합계 약 157MB)을 함께 넣는다. 학교 운영 자료는 이 소스 제공 대상에 포함하지 않는다.

패키지 생성기는 필수 고지·소스 누락, 해시·버전 불일치 및 오래된 소스 검토 해시를 차단한다. 소스 압축본을 임의로 제외하거나 의존성 바이너리를 추가하지 않는다. 압축본에 포함된 소스·빌드 파일과 버전을 확인했으며 C++ 전체 재빌드는 수행하지 않았다. 검토 근거는 개발 저장소의 distribution/agpl-review-2026-09-13.md와 distribution/release-review-2026-09-13.md, XLS 읽기 교체 후속 기록에 있다. 파일별 검토 이후 변경한 파일은 다시 검토하며 실제 패키지 생성 성공과 앱 인수·공개 배포 판단은 구분한다.
