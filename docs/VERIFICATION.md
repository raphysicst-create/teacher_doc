# 설치 경로 검증

## 자동 XML 회귀시험

Python 3.12가 있는 저장소 루트에서 실행합니다.

```sh
python -B -X utf8 -m unittest discover -s tests -v
```

시험은 임시 HOME/CODEX_HOME, PC 데이터와 작업 폴더를 별도로 만들고, 의존성을 실제 새 venv에 설치합니다. 네트워크가 필요하며 시스템 Python 패키지와 사용자의 실제 문서·Codex 설정은 변경하지 않습니다. 시험이 끝나면 시험이 만든 임시 폴더만 정리합니다.

확인 항목:

- 한글·공백 경로의 설치 → XML doctor → 합성 양식·첫 HWPX 생성
- 같은 명령 재실행과 기존 workspace 설정·사용자 파일 보존
- 자식 Python이 전용 venv와 lxml 고정 버전을 유지하는지
- 의존성 누락, 잘못된 Python, 비 Windows full 검사에 대한 비정상 종료코드
- 수정된 연습 파일, 잘못된 runtime 설정, 손상된 workspace 설정 보존
- 코드 안의 작업 폴더 차단, 훅 미등록, JSON 객체/필드 형식 오류
- 외부 PIP_TARGET/PIP_USER/pip 설정을 통한 전용 venv 밖 패키지 설치 차단
- 전체 패키지 카탈로그와 설치 스킬 존재

GitHub Actions의 `Onboarding XML smoke`는 Ubuntu와 Windows에서 같은 시험을 실행합니다. Windows 러너에 한글을 설치하거나 COM을 활성화하지 않습니다. CI 성공은 XML 경로의 증거입니다.

## Python 없는 첫 설치 (별도 시험)

`No-Python first install`은 일반 XML CI와 분리된 Windows PowerShell 5.1 시험이다. 전용 GitHub-hosted 임시 러너에서만 실행되며 사용자 PC에서는 실행하지 않는다.

- PATH, 사용자 기본 설치 위치, Python registry, runtime 선택을 격리한 뒤 Python이 탐색되지 않는다는 baseline을 기록한다. 기존 toolcache 파일은 디스크에 남을 수 있지만 제품의 모든 기존 Python 탐색 경로에서 접근되지 않는다
- 제품에 탐색 우회용 시험 플래그를 넣지 않는다. 고정 공식 다운로드에서 새 앱 전용 CPython을 받았고 그 실제 실행 파일로 venv를 만들었다는 증거를 확인한다
- 동의 없는 실행은 다운로드 전에 중단한다. 동의한 설치는 XML doctor와 첫 HWPX까지 수행하고, 동의 플래그 없는 재실행은 기존 설치를 재사용한다
- 코드/작업/PC 데이터 모두 한글·공백 경로를 사용한다. 기존 사용자 파일과 설정의 해시, PATH·Python registry·실행 정책의 설치 전후 snapshot을 대조한다
- `windows-no-python-evidence` artifact에 명령 로그, 공급원/해시 receipt, 첫 설치/재실행 요약, 실제 HWPX/슬롯 JSON, doctor, 독립 runtime 경로/version probe, 파일 해시와 전후 snapshot을 남긴다
- CI fixture가 잠시 숨긴 runner의 Python registry는 `finally`에서 복구하고 원래 snapshot과 비교한다. 제품 bootstrap은 registry를 변경하지 않는다

Unix의 `tests/test_python_bootstrap.py`는 Python 없는 격리 PATH에서 동의 거절, uv 해시 불일치, 네트워크 실패, 재시도 보존, 기존 설정, 잘못된 Python, 코드 경계, symlink 경계를 시험한다. Windows helper 시험은 `tests/windows_bootstrap_unit.ps1`이다. 실패용 다운로드는 fixture 바이트를 쓰며 실행하지 않는다.

v0.1.2 개발 검증: Linux x86_64의 실제 no-Python 다운로드→첫 HWPX와 재실행, Python 회귀 21개, PowerShell 7 구문/실패 helper 검사를 수행했다. Windows PowerShell 5.1 실실행은 해당 commit의 `No-Python first install` CI 결과로 확인한다. macOS·ARM64는 메타데이터를 제공하지만 이 검증만으로 실실행을 확인했다고 하지 않는다. 한글 COM과 앱 GUI 스킬 로딩은 별도 미확인이다.

## Codex 플러그인 발견·재설치

실제 사용자의 HOME을 바꾸지 말고 격리 시험용 HOME과 CODEX_HOME에서 검사합니다. 현재 설치된 CLI 도움말로 명령 지원을 먼저 확인합니다.

```sh
codex plugin marketplace add https://github.com/raphysicst-create/teacher_doc.git
codex plugin add teacher_doc@teacher-doc-local --json
codex plugin list --json
```

반환된 설치 경로에 `scripts/bootstrap.py`, 두 스킬, 의존성·라이선스·소스가 있는지 확인하고 그 설치본에서 bootstrap을 실행합니다. 새 대화 또는 클라이언트의 실제 스킬 목록에서 `teacher_doc:hwpx`와 `teacher_doc:teacher-doc-setup` 로딩을 별도로 확인합니다. 전체 설치본의 스킬 이름은 클라이언트가 반환한 값을 우선합니다.

시험용 플러그인을 제거·재설치하는 동안 별도 작업 폴더와 PC 데이터, 생성한 HWPX 해시가 유지되는지 확인합니다. 코드 캐시 삭제를 사용자 문서 삭제로 확대하지 않습니다.

## 실제 Windows 한글 검증 (별도 필요)

1. 사용자가 허용한 Windows 사용자 세션, 설치된 정품 한글, Python 3.12와 필요한 보안모듈을 확인합니다
2. 설치 결과가 반환한 전용 Python과 같은 `HWPDOC_PC_DATA`를 사용해 `doctor --mode full`을 실행합니다
3. COM 검사 통과 후에도 `first-document.hwpx`를 한글에서 실제 열고, 별도 사본의 PDF 내보내기·전체 페이지 PNG·텍스트/잘림/줄바꿈을 확인합니다
4. 구조 검사와 COM 실열림, PDF/PNG 생성, 사람이 실제로 본 화면을 구분해 기록합니다
5. 실제 학교 양식은 기존 등록·초안 확인·문서별 검증 절차로 다시 검사합니다. 합성 연습 결과를 승인이나 등록으로 복제하지 않습니다

한글 없는 환경이나 샌드박스 차단에서는 이 단계를 미실행·미확인으로 남깁니다. 보안 완화, 실행 정책/레지스트리 수정, 관리자 권한 확대를 시험의 조건으로 요구하지 않습니다.

## 종료코드

- `bootstrap`: XML 준비 완료 0, `--mode full` 미완료는 해당 doctor의 비정상 코드, 설치/설정 오류 2
- `doctor`: 요청한 모드의 필수 검사 통과 0, 실패 1, 미확인 2
- `first-doc`: XML 연습 생성/동일 파일 재확인 0, 보존해야 할 충돌·설정 오류 2

종료코드 0과 함께 JSON의 `mode`, `checks`, `plugin_loaded_in_chat`, `human_approval`, `sent`를 읽습니다. `ready_xml`은 실사용 공문의 발송 가능 표시가 아닙니다.
