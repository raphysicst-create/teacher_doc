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
- 전체 패키지 카탈로그와 설치 스킬 존재

GitHub Actions의 `Onboarding XML smoke`는 Ubuntu와 Windows에서 같은 시험을 실행합니다. Windows 러너에 한글을 설치하거나 COM을 활성화하지 않습니다. CI 성공은 XML 경로의 증거입니다.

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
