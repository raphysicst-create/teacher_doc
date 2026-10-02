# teacher_doc 0.1.2 변경 고지

배포자 유지·변경 기준일: 2026. 10. 2.

## 0.1.2 Python 없는 첫 설치

- Python 없이 시작할 수 있는 PowerShell/Unix 진입점을 추가했다. 명시적 Python 설치 동의 후 공식 Astral uv와 CPython 3.12.15를 앱 전용 위치에 준비한다.
- 공급원·버전·SHA-256을 고정하고, py/WindowsApps 실행 없는 탐색, 전역 PATH·registry·보안 정책 비변경, 실패 중단과 기존 자료 보존을 유지한다.
- README·AGENTS·설치 스킬을 동일한 한 문장 요청/운영체제별 단일 명령으로 연결했다.
- 기존 Python이 있는 XML 회귀와 별도로 no-Python Windows 첫 설치 CI와 검증 증거 artifact를 추가했다. 한글 COM/렌더·앱 스킬 실로딩은 계속 별도 확인이다.

## 0.1.1 설치 경로 보완

- 저장소 전체를 찾는 Codex marketplace catalog, 설치 스킬, 루트 README와 초보자 안내를 추가했다.
- 격리 Python 3.12 환경 준비·재실행·XML doctor·비민감 합성 첫 HWPX 생성을 연결했다. 기존 사용자 설정과 문서는 보존한다.
- doctor 실패/미확인 종료코드와 Linux/macOS venv 자식 실행 경로를 바로잡았다.
- Windows/Linux 자동 XML 회귀시험을 추가했다. Windows 한글 COM, PDF/PNG와 앱 GUI 인수는 별도 검증이며 자동 성공으로 표시하지 않는다.

## 0.1.0 기존 변경


이 배포는 Canine89/hwpxskill 상류 원본 그대로가 아닌 teacher_doc용 수정·통합본이다. 원래 파일의 저작권 고지는 유지한다.

- HWPX 편집·검증 경로에 슬롯 입력, 페이지·내용 검사, 한글 실열림 및 렌더 검증을 통합했다.
- Python·PowerShell 공통 실행기, 작업 폴더 설정, 양식 등록, 검토·전달 기록과 앱별 보호 훅을 추가·수정했다.
- 스킬 지침과 템플릿을 교사 업무 흐름에 맞춰 조정했다. 배포 후보 일부 XML은 운영 식별정보를 제거한 사본이다.
- 프로젝트와 실행 진입점 이름을 teacher_doc으로 정리하고 기존 hwpdoc 호환 경로를 유지했다.
- AGPL 전문, 구성요소 고지와 고정 버전의 PyMuPDF/MuPDF 소스를 배포에 포함했다.
- 구형 XLS 읽기와 환경 진단 의존성을 xlrd에서 MIT 라이선스의 python-calamine 0.7.0으로 교체했다. 원래 Excel 행 위치를 보존하며 사업관리카드 318개 셀과 파생 JSON의 동일성을 확인했다.

배포 파일별 현재 해시는 함께 제공하는 `release-inventory.json`을 기준으로 한다. PyMuPDF와 MuPDF 소스 압축본에는 로컬 수정을 가하지 않았다.
