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

## 2. 작업 폴더와 Python 설치 동의

- 코드 설치 폴더 밖에 교사 작업 폴더를 정한다. 기존 작업 폴더가 있으면 그 경로를 유지한다. 새 경로는 운영체제의 사용자 문서 위치를 확인하여 정하고 사용자 지정 경로를 우선한다
- PC 데이터도 코드 밖에 둔다. 기존 경로가 있으면 유지한다. 기본은 `HWPDOC_PC_DATA`, 없으면 `%LOCALAPPDATA%/hwpdoc`, 그것도 없으면 사용자 홈의 `AppData/Local/hwpdoc`이다. 새 설치에서는 명확한 별도 데이터 경로를 지정한다. 이후에는 작업 폴더의 `.hwpdoc/onboarding.json`에서 실제 `pc_data`·`python`을 복원한다. 명시 환경변수는 우선하므로 과거 대화의 변수를 추측하여 넣지 않는다
- “Python 포함 설치”, “Python이 없으면 전용 폴더에 설치해도 된다”는 명시적인 요청은 아래 동의 플래그를 허용한다. 이미 승인했으면 다시 묻지 않는다
- 단순 “설치해줘”만 말했을 때는 동의 플래그 없이 실행한다. `PYTHON_INSTALL_CONSENT_REQUIRED`라면 “Python 3.12가 없어요. 공식 Astral uv와 python-build-standalone의 CPython을 teacher_doc 전용 폴더에 다운로드해서 이어서 설치할까요? 전역 PATH·레지스트리는 바꾸지 않아요”라고 한 번 묻는다. 거절/미응답이면 다운로드하지 않는다
- [공급원과 라이선스](../../docs/PYTHON-RUNTIME.md)를 읽는다. 자동 설치는 Python Software Foundation의 python.org 설치기가 아닌 **Astral의 CPython 빌드**다. uv와 Python 아카이브 모두 고정 SHA-256을 검증한다. 다운로드나 해시 검증 실패를 성공으로 바꾸지 않는다

## 3. 운영체제에 맞는 명령 하나로 준비

설치 루트에서 아래 명령을 실행한다. 경로는 실제 환경에 맞게 에이전트가 채운다. 사용자가 명령어를 직접 입력하게 하지 않는다. Python이 없어도 이 진입점을 실행할 수 있다.

Windows PowerShell:

```powershell
& "$pluginRoot/scripts/bootstrap.ps1" -Workspace $teacherWorkspace -DataDir $pcData -AllowPythonInstall
```

macOS/Linux:

```sh
bash "$pluginRoot/scripts/bootstrap.sh" --workspace "$teacherWorkspace" --data-dir "$pcData" --allow-python-install
```

**위 동의 플래그는 Python 설치가 승인된 경우에만 붙인다.** 기존 Python 3.12는 진입점이 탐색한다. 명확히 지정해야 할 때 Windows `-Python <실제 절대경로>`, Unix `--python <실제 절대경로>`를 쓴다. `py`, `pymanager`, WindowsApps 별칭을 탐색용으로 실행하지 않는다. Python Install Manager는 탐색 호출만으로 다운로드할 수 있다. PowerShell 실행 정책이 막히면 오류와 필요한 조치를 보고하고 `Set-ExecutionPolicy`, `-ExecutionPolicy Bypass`, `Unblock-File`로 우회하지 않는다.

기본 XML 모드로 전용 venv → 고정 의존성 → 작업 폴더 초기화 → XML doctor → 첫 연습 문서를 연속 수행한다. 성공 JSON의 `python`(전용 venv), `source_python`, `source_python_version`, `pc_data`, `workspace`, `xml_doctor`, `practice.report`, `full_doctor`를 확인한다. 마지막 성공 요약은 `.hwpdoc/onboarding.json`, 마지막 Python 설치 단계 시도는 `.hwpdoc/onboarding-attempt.json`에 남는다. 후자가 failed이면 과거 ready_xml을 최근 성공으로 보고하지 않는다. shell/다운로드 단계에서 Python 실행 전 실패하면 stderr가 그 시도의 결과다. 손상된 작업 설정에는 진단 기록을 억지로 쓰지 않는다. Python 자동 다운로드 증거는 PC 데이터 아래 `managed-python/install-receipt.json`에 남는다. 폴더 생성만으로 성공이라고 하지 않는다.

추가 옵션은 필요한 경우에만 붙인다. Windows/Unix 대응은 `-Mode full`/`--mode full`, `-SchoolData`/`--school-data`, `-Visual`/`--visual`, `-App claude`/`--app claude`, `-SkillName <실제 스킬 이름>`/`--skill-name <실제 스킬 이름>`이다. 기본은 `xml`, `codex`, `hwpx`다. 앱에서 `teacher_doc:hwpx`처럼 다른 실제 이름을 확인했다면 그 값을 전달한다. 기본 문자열이 저장됐다고 앱 로딩을 확인한 것은 아니다.

기존 `runtime.json`, 작업 설정·지침과 사용자 자료를 삭제/덮어쓰지 않는다. 선택 의존성 부족이나 손상된 기존 환경은 별도 데이터 경로가 필요할 수 있다. 다운로드/네트워크/권한 오류가 나면 원인을 해결한 뒤 **같은 명령과 같은 경로**로 재실행한다. 앱 전용 설치만 이어서 진행하며 전역 Python 패키지는 바꾸지 않는다. 보안 경고·TLS·조직 정책을 우회하지 않는다. 기존 Python 3.12가 이미 확인된 고급 환경에서는 `scripts/bootstrap.py` 직접 실행도 지원하지만 초보자 설치의 기본 경로는 위 명령이다.

## 4. 실제 파일과 검사 결과 확인

1. 작업 폴더 `output/teacher-doc-practice/`의 `template.hwpx`, `first-document.hwpx`, `slot-values.json`, `practice-report.json`이 실제 존재하는지 확인한다. 설치 요약은 `.hwpdoc/onboarding.json`, 최근 doctor 결과는 `.hwpdoc/doctor.json`이다
2. 보고서를 읽고 XML/슬롯 편집 검사 결과, 실패·미확인 항목을 구분한다. 새 대화라면 `.hwpdoc/onboarding.json`의 `pc_data`·`python`을 읽고 runtime.json과 존재·일치를 확인한다. 아래 `$taskPython`은 그 절대경로다. 필요하면 전용 Python으로 다음 명령을 실행한다

```sh
"$taskPython" -X utf8 "$pluginRoot/scripts/teacher_doc.py" --workspace "$teacherWorkspace" doctor --mode xml
"$taskPython" -X utf8 "$pluginRoot/scripts/teacher_doc.py" --workspace "$teacherWorkspace" first-doc
```

3. 연습 파일은 학교 양식 등록이나 사용자 승인 기록을 만들지 않는다. 실제 승인·등록·렌더 증거를 흉내 내어 추가하지 않는다
4. Windows 한글 확인을 요청받은 경우 같은 전용 Python으로 `doctor --mode full`을 실행하고 실제 결과를 읽는다. `doctor --mode full`이 한글/COM을 사용할 수 없어 종료 코드 2를 반환하면 전체 검증 미완료로 보고한다. `--mode full` bootstrap에서도 XML 연습 결과와 `full_doctor`를 따로 읽는다. 요약 `status`만으로 전체 문서 검증 통과를 선언하지 않는다. PDF/PNG 육안 판독은 해당 작업의 실제 산출물로 따로 수행한다
5. 플러그인 목록에 보이는 것과 새 작업에서 스킬 본문을 실제 읽는 것은 별개다. 앱/CLI에서 확인한 범위까지만 보고한다

최종 안내는 실제 HWPX 파일 → `text_excerpt`의 실제 본문 2–4줄 → 바뀐 점 → 검사/미확인 상태 → 다음 행동 하나 순서로 짧게 적는다. 발췌는 읽기용이며 인쇄 미리보기가 아니다. 검사 통과 메시지만 결과로 내놓지 않는다. 첨부 불가 환경에서는 그 컴퓨터의 정확한 경로를 준다. 마지막에 설치 결과 `continue_prompt`처럼 실제 작업 폴더가 채워진 “이 작업 폴더에서 문서 작업 이어줘” 문장을 제공한다. 파일 경로를 실제 환경에 맞게 제공하고 사용자가 열 수 있으면 결과물을 전달한다. “설치됨”, “XML 연습 성공”, “앱 로딩 확인”, “Windows 한글/렌더 확인”을 하나의 전체 성공으로 합치지 않는다.

## 새 대화에서 이어가기

재설치부터 시작하지 않는다. 사용자가 준 작업 폴더의 지침·학교 설정·설치 기록을 읽고 실제 전용 Python을 확인하여 `doctor --mode xml`을 실행한다. Windows `teacher_doc.ps1 --workspace ...`도 같은 기록을 읽는다. macOS/Linux 재설치 진입점은 기록이 있으나 데이터 경로가 생략되면 중단하므로, 필요한 설치 재시도만 실제 `pc_data`를 `--data-dir`로 전달한다. 이동/다른 PC/없는 경로는 원인을 진단하고 사용자가 선택한 새 격리 환경이 필요하면 설명한다. 원본·작업 설정·수정된 연습본·기존 AGENTS.md를 덮어쓰지 않는다. 수정된 연습본은 보존 중단 이유와 “수정본 작업 이어가기 / 별도 연습 폴더에 새 사본”을 설명한다.

## 설치 뒤 실제 공문

[업무 절차](../hwpx/references/workflow.md)를 읽고 학교 양식 확인 → 초안 확인 → build → 전체 validate → 사람 검토를 따른다. `first-doc`는 연습용이며 production `build`·`validate`·승인 절차를 대체하지 않는다. 원본을 보존하고 최종 사람 검토·사람 발송을 유지한다.

`distribution/README.md`는 과거 배포 준비 기록이다. 공개 패키지에 없는 개발 명령을 설치 필수 단계로 호출하지 않는다. 이 안내의 설치 형식 근거는 [OpenAI 공식 플러그인 안내](https://developers.openai.com/plugins/build/plugins), 확인일은 2026-10-02다. 실제 클라이언트의 도움말·화면을 우선하여 지원 여부를 확인한다.
