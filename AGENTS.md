# teacher_doc 에이전트 안내

## 설치 요청부터 시작할 때

사용자가 이 저장소 링크를 붙여 넣고 설치를 부탁했다면 설명만 하고 끝내지 말고, 허용된 실행 환경에서 [설치 스킬](skills/teacher-doc-setup/SKILL.md)을 읽어 설치 → 환경 점검 → 첫 연습 문서 생성을 진행한다. 사용자가 명령어와 JSON을 직접 작성하게 하지 않는다. 작업할 컴퓨터가 명시되었다면 그 환경을 사용하고, 접근할 수 없으면 필요한 연결이나 권한만 요청한다.

- **전체 저장소/플러그인을 설치한다.** `skills/hwpx` 단독 복사, skill-only installer, sparse checkout은 사용하지 않는다. 루트 `scripts/`, `distribution/requirements-*.txt`, 라이선스·소스가 함께 필요하다
- 플러그인 이름 `teacher_doc`을 바꾸지 않는다. Codex 카탈로그는 `.agents/plugins/marketplace.json`, 마켓플레이스 이름은 `teacher-doc-local`, `source.path`는 마켓플레이스 루트 기준 `./`다
- 설치된 CLI가 지원하면 `codex plugin marketplace add`와 `codex plugin add teacher_doc@teacher-doc-local --json`을 사용한다. CLI 도움말과 결과에서 실제 지원·성공을 확인한다. GUI 검색창에 GitHub 링크를 넣으면 어디서나 설치된다고 안내하지 않는다
- 플러그인 캐시는 원본 checkout과 다를 수 있다. 설치 응답의 `installedPath` 또는 실제 로드된 스킬의 경로를 확인하고 그 루트의 안내를 읽는다. 경로를 추측하지 않는다
- CLI 설치가 지원되지 않으면 전체 저장소를 임시 폴더가 아닌 지속 보관 위치에 clone/복사한다. 기존 폴더는 origin과 상태를 확인하여 재사용하고, 덮어쓰기·삭제·강제 reset을 하지 않는다. 앱 발견과 스킬 로딩은 별도 확인한다

## 런타임과 자료의 경계

1. 코드 폴더 밖의 교사 작업 폴더와 PC 데이터 경로를 선택하고 기존 자료를 보존한다. 학교 이름·시간표·예산·실제 공문은 첫 연습에 필요하지 않다
2. Windows는 `scripts/bootstrap.ps1 -Workspace <외부 작업 폴더> -DataDir <외부 PC 데이터>`, macOS/Linux는 `bash scripts/bootstrap.sh --workspace <외부 작업 폴더> --data-dir <외부 PC 데이터>` 하나로 진행한다. 기존 Python 3.12 탐색은 진입점이 한다. `py`, `pymanager`, WindowsApps 별칭은 설치를 유발할 수 있으므로 탐색용으로 실행하지 않는다
3. Python이 없으면 자동 다운로드는 기본 거절된다. 사용자가 **“Python 포함 설치” 또는 이와 같은 앱 전용 Python 설치를 명시적으로 요청했다면** Windows `-AllowPythonInstall`, Unix `--allow-python-install`을 붙여 같은 명령을 실행한다. 이미 받은 승인을 다시 묻지 않는다. 단순 “플러그인 설치” 요청이면 Astral uv와 python-build-standalone의 CPython 3.12를 전용 폴더에 다운로드한다는 점을 한 번 설명하고 승인받는다. 모호한 요청에 동의 플래그를 임의로 붙이지 않는다
4. 자동 설치는 공식 Astral 릴리스에서 고정 버전과 SHA-256을 검증하며 앱 전용 폴더만 사용한다. 기존 Python이 있으면 재사용하고 전용 venv를 만든다. 고정 의존성 → 작업 폴더 초기화 → XML doctor → 합성 연습 HWPX까지 진입점이 수행한다. 자세한 공급원·라이선스는 [런타임 고지](docs/PYTHON-RUNTIME.md)를 읽는다
5. 기존 `.hwpdoc/workspace.json`, 작업 지침, PC `runtime.json`과 사용자 자료를 보존한다. 사용자 지정 데이터 경로는 `HWPDOC_PC_DATA`와 실행 인수 사이에 일관되게 사용한다
6. 설치된 한글의 전체 검사가 필요하면 Windows 사용자 세션에서 `doctor --mode full`을 별도로 수행한다. XML 모드 성공을 COM 성공으로 보고하지 않는다

한글·보안모듈 구매/설치, 훅·레지스트리·실행 정책·전역 PATH·Codex 권한 변경은 이 설치에 포함하지 않는다. 보안 경고, TLS 오류, 조직 정책 차단을 우회하지 않는다. 다운로드/해시/권한 오류는 실패로 보고하고 기존 자료를 보존한 채 원인 해결 후 같은 명령으로 재시도한다. 훅 설치는 초보자 설정에 포함하지 않는다.

## 문서 작업

실제 학교 문서는 [HWPX 스킬](skills/hwpx/SKILL.md)과 [업무 절차](skills/hwpx/references/workflow.md)를 읽고 진행한다. 기존 프로젝트의 명시적 사용자 결정을 유지한다.

- 원본은 보존하고 작업 폴더에 새 사본을 만든다
- 연습 문서는 합성 예제이며 등록된 학교 양식이나 승인된 초안으로 승격하지 않는다
- 승인·양식 등록 확인·육안 판독 필드를 추정해서 채우지 않는다
- 구조 검사, 한글 COM, 필수 렌더·육안 판독, 사람 검토는 서로 다른 단계다. 실패·미실행을 통과로 바꾸지 않는다
- 최종 발송은 사람이 한다. 발송 전 한글로 열어 확인하도록 안내한다

## 보고와 유지보수

설치 위치, 작업 폴더, 사용한 Python, 실제 생성 파일과 검사 보고서, 앱 스킬 로딩 확인 여부, XML 검사 결과, Windows COM·렌더의 미확인 항목을 짧게 보고한다. 필요 조치가 있으면 가장 작은 다음 단계만 제시한다.

`distribution/README.md`는 과거 배포 준비·운영 검토 기록이며 현재 공개 패키지에 없는 개발 전용 명령이 있다. 처음 설치에는 루트 README와 설치 스킬을 따른다. 원래 라이선스·고지·소스 제공 파일을 삭제하지 않는다. 업데이트 시 코드와 사용자 자료를 분리하고, 변경된 코드의 검증을 다시 수행한다.
