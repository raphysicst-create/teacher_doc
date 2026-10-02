---
name: teacher-doc-setup
description: "teacher_doc 저장소 링크 설치, 첫 실행, Python 환경 점검, 작업 폴더 준비와 개인정보 없는 첫 HWPX 연습 문서 생성. 설치·설정·실행 오류 또는 한글 없는 XML 모드 시작 요청에 사용한다."
---

# teacher_doc 설치와 첫 실행

사용자는 저장소 주소와 “설치해줘”만 말해도 된다. 에이전트가 다음 절차를 수행하고 결과를 보여준다. 명령어 입력이나 학교 설정 JSON 작성을 사용자에게 떠넘기지 않는다. 이 스킬은 설치와 합성 연습까지만 다루며 실제 학교 공문은 [HWPX 스킬](../hwpx/SKILL.md)의 업무 절차를 따른다.

## 1. 전체 패키지와 실제 루트 확인

- 저장소: `https://github.com/raphysicst-create/teacher_doc`
- 현재 스킬의 실제 파일 경로에서 상위 폴더를 탐색하여 `.codex-plugin/plugin.json`, `scripts/bootstrap.py`, `scripts/teacher_doc.py`, `distribution/requirements-base.txt`가 함께 있는 코드 루트를 확인한다. 링크를 따라 실제 위치를 확인한다
- `skills/hwpx`만 설치하지 않는다. 플러그인 루트 전체와 라이선스·소스 제공 파일이 필요하다. sparse checkout으로 줄이지 않는다
- 아직 받지 않았다면 사용자가 지정한 컴퓨터의 지속 보관 폴더에 전체 저장소를 clone한다. 기존 checkout은 origin·변경 사항을 확인해 재사용하고 강제 덮어쓰기하지 않는다. 임시 폴더를 영구 설치 경로로 쓰지 않는다

지원되는 Codex 클라이언트라면 먼저 `codex plugin --help`, `codex plugin marketplace add --help`, `codex plugin add --help`를 확인한다. CLI가 제공하는 경우:

```sh
codex plugin marketplace add https://github.com/raphysicst-create/teacher_doc.git
codex plugin add teacher_doc@teacher-doc-local --json
codex plugin list --json
```

이미 전체 checkout이 있고 로컬 원본을 설치하려면 첫 줄의 Git URL 대신 **checkout 루트 절대경로**를 쓴다. 같은 이름으로 다른 마켓플레이스가 등록되어 있으면 자동 교체하지 말고 충돌을 보고한다. 카탈로그의 `source.path: "./"`는 `.agents/plugins` 폴더가 아니라 저장소 루트를 뜻한다.

설치 결과의 `installedPath`와 목록의 설치/활성 상태를 확인한다. 그 실제 설치본의 이 스킬을 다시 읽고 이후 명령을 실행한다. CLI 추가가 없는 버전에서는 지원되는 앱의 로컬 마켓플레이스 화면을 이용하거나 전체 checkout에서 명시적으로 스킬을 읽어 설정을 진행한다. 전자는 실제 화면으로 확인하고, 후자는 앱 자동 로딩을 검증한 것으로 보고하지 않는다. 프로젝트 신뢰나 조직 정책을 우회하지 않는다.

앱/계정별 GitHub 가져오기 기능과 일반 Plugins Directory 검색은 다르다. “검색창에 링크만 넣으면 설치된다”는 보편적 안내를 하지 않는다. 앱을 새로 열어야 하는 경우 사용자에게 그 단계만 안내한다.

## 2. Python·작업 폴더 확인

- 기존 **Python 3.12** 실행 파일의 경로와 `--version`을 확인한다. Windows에서는 `py -3.12`가 있으면 위치를 확인하는 데 사용할 수 있다. macOS/Linux에서는 실제 `python3.12`를 확인한다. `python`이라는 이름만 믿지 않는다
- Python 3.12가 없으면 [Python 공식 다운로드](https://www.python.org/downloads/)를 안내하고 필요한 설치 승인을 요청한다. 임의 배포본 설치, 다른 Python 버전으로 대체, 한글 자동 구매/설치는 하지 않는다
- 코드 설치 폴더 밖에 교사 작업 폴더를 정한다. 기존 작업 폴더가 있으면 그 경로를 유지한다. 새 경로는 운영체제의 사용자 문서 위치를 실제로 확인해 제안하고, 명시한 사용자 경로를 우선한다
- 기존 PC 데이터가 있으면 같은 경로를 유지한다. 기본은 `HWPDOC_PC_DATA`, 없으면 `%LOCALAPPDATA%/hwpdoc`, 그것도 없으면 사용자 홈의 `AppData/Local/hwpdoc`다. 마지막 호환 기본값은 macOS/Linux에도 적용된다. 새 설치에서는 위치가 분명한 별도 `--data-dir`을 권장하며 코드 폴더 밖에 둔다. 이후 실행에도 같은 `HWPDOC_PC_DATA`를 적용한다. 민감한 데이터가 필요 없는 연습에서 학교명·학생명·학교 원문을 요구하지 않는다

## 3. bootstrap 한 번으로 준비

먼저 `scripts/bootstrap.py --help`를 읽는다. 코드 루트에서 **확인한 Python 3.12 실행 파일**로 다음 명령을 실행한다. 아래 `python`은 그 실행 파일을 뜻하며 사용자가 직접 입력할 명령이 아니다.

```sh
python -X utf8 scripts/bootstrap.py --workspace "/코드/폴더/밖/교사 작업"
```

Windows PowerShell에서는 실행 파일·인수에 공백이 있을 수 있으므로 호출 연산자와 따옴표를 쓴다.

```powershell
& $python312 -X utf8 "$pluginRoot/scripts/bootstrap.py" --workspace $teacherWorkspace
```

기본은 `--mode xml`이다. bootstrap은 전용 가상환경에 고정 버전 의존성을 설치하고, 설정을 보존하면서 작업 폴더 초기화 → `doctor --mode xml` → 첫 연습 문서 생성을 진행한다. 설치 출력 JSON의 `python`(전용 Python 실행 파일), `pc_data`, `workspace`, `xml_doctor`, `practice.report`, `full_doctor`를 읽는다. 같은 요약은 작업 폴더의 `.hwpdoc/onboarding.json`에 있다. 가상환경을 만들었다는 사실만으로 성공이라 하지 않는다.

선택 사항은 해당 기능이 필요할 때만 붙인다.

- `--data-dir <경로>`: PC 데이터/전용 환경을 별도로 둘 위치. 이후 같은 값을 `HWPDOC_PC_DATA`로 전달한다
- `--app codex|claude`, `--skill-name <실제 이름>`: 기본값은 `codex`, `hwpx`다. 새 작업 폴더에서는 앱에서 실제 확인한 스킬 이름을 전달한다. 예를 들어 목록에서 `teacher_doc:hwpx`를 확인했다면 `--skill-name "teacher_doc:hwpx"`를 붙인다. 기본 문자열이 저장됐다고 스킬 로딩을 확인한 것은 아니다
- `--school-data`: 시간표·예산 원문(xlsx/xls) 관련 의존성
- `--visual`: PDF→PNG용 시각 검토 의존성. 설치만으로 한글 PDF 내보내기나 실제 육안 판독이 완료되지는 않는다
- `--mode full`: Windows·설치된 한글의 전체 모드 확인이 필요한 경우. 한글 설치와 COM 실행 가능 여부는 별도 조건이며, macOS/Linux XML 성공을 전체 성공으로 바꾸지 않는다

이미 설정이 있으면 같은 경로로 재실행한다. 기존 workspace 설정과 지침, `runtime.json`을 삭제해서 재설정하지 않는다. 기존 런타임에 선택 의존성이 없으면 bootstrap은 그 환경을 임의 변경하지 않고 새 격리 `--data-dir`을 안내할 수 있다. 충돌/손상/권한 오류는 원인을 보고하고 사용자 자료를 유지한다. pip/네트워크 실패 시 실패 단계와 오류를 확인하고 허용된 범위에서 재시도한다. TLS·조직 정책·보안 제한을 끄지 않는다.

## 4. 실제 파일과 검사 결과 확인

1. 작업 폴더 `output/teacher-doc-practice/`의 `template.hwpx`, `first-document.hwpx`, `slot-values.json`, `practice-report.json`이 실제 존재하는지 확인한다. 설치 요약은 `.hwpdoc/onboarding.json`, 최근 doctor 결과는 `.hwpdoc/doctor.json`이다
2. 보고서를 읽고 XML/슬롯 편집 검사 결과, 실패·미확인 항목을 구분한다. 필요하면 bootstrap이 기록한 전용 Python으로 다음 명령을 실행한다

```sh
python -X utf8 scripts/teacher_doc.py --workspace "/교사/작업/폴더" doctor --mode xml
python -X utf8 scripts/teacher_doc.py --workspace "/교사/작업/폴더" first-doc
```

3. 연습 파일은 학교 양식 등록이나 사용자 승인 기록을 만들지 않는다. 실제 승인·등록·렌더 증거를 흉내 내어 추가하지 않는다
4. Windows 한글 확인을 요청받은 경우 같은 전용 Python으로 `doctor --mode full`을 실행하고 실제 결과를 읽는다. `doctor --mode full`이 한글/COM을 사용할 수 없어 종료 코드 2를 반환하면 전체 검증 미완료로 보고한다. `--mode full` bootstrap에서도 XML 연습 결과와 `full_doctor`를 따로 읽는다. 요약 `status`만으로 전체 문서 검증 통과를 선언하지 않는다. PDF/PNG 육안 판독은 해당 작업의 실제 산출물로 따로 수행한다
5. 플러그인 목록에 보이는 것과 새 작업에서 스킬 본문을 실제 읽는 것은 별개다. 앱/CLI에서 확인한 범위까지만 보고한다

최종 안내에는 설치 위치·작업 폴더·연습 결과 파일, 성공한 검사, 아직 필요한 확인을 짧게 적는다. 파일 경로를 실제 환경에 맞게 제공하고 사용자가 열 수 있으면 결과물을 전달한다. “설치됨”, “XML 연습 성공”, “앱 로딩 확인”, “Windows 한글/렌더 확인”을 하나의 전체 성공으로 합치지 않는다.

## 설치 뒤 실제 공문

[업무 절차](../hwpx/references/workflow.md)를 읽고 학교 양식 확인 → 초안 확인 → build → 전체 validate → 사람 검토를 따른다. `first-doc`는 연습용이며 production `build`·`validate`·승인 절차를 대체하지 않는다. 원본을 보존하고 최종 사람 검토·사람 발송을 유지한다.

`distribution/README.md`는 과거 배포 준비 기록이다. 공개 패키지에 없는 개발 명령을 설치 필수 단계로 호출하지 않는다. 이 안내의 설치 형식 근거는 [OpenAI 공식 플러그인 안내](https://developers.openai.com/plugins/build/plugins), 확인일은 2026-10-02다. 실제 클라이언트의 도움말·화면을 우선하여 지원 여부를 확인한다.
