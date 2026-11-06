# teacher_doc 0.2.2 변경 고지

배포자 유지·변경 기준일: 2026. 11. 6.

## 0.2.2 클로드 코드 MCP 확인 안내 정정

- README "학사일정을 못 가져와요"와 업무 절차의 MCP 절에서 "클로드 코드는 `/mcp`로 확인"을 "세션에 MCP 서버 상태를 물어 확인"으로 바꿨다. 데스크톱 앱의 `/mcp`는 계정 커넥터 설정 화면을 열어 프로젝트 `.mcp.json` 서버가 보이지 않는다(CLI의 `/mcp` 목록과 다름). 조회 시점 `pending`은 첫 호출 전 상태라 정상이다.
- 근거: 2026. 11. 6. 클로드 코드 새 세션에서 플러그인 스킬 노출, `teacher_doc_mcp` 프로젝트 서버 연결, `resolve_school`(청운중학교·서울) 실호출 후보 1건 응답을 확인했다. 남은 미실측은 클로드 코드에서 문서 1건 완주다. 코드 변경은 없다.

## 0.2.1 클로드 코드 설치 지원

- `.claude-plugin/marketplace.json`을 추가했다. 저장소 루트를 플러그인으로 가리키는 항목 하나(`source: "./"`, 마켓 이름 `teacher-doc-marketplace`)이며 플러그인 이름은 Codex와 같은 `teacher_doc`이다. 클로드 코드는 이 파일이 있어야 GitHub 저장소를 마켓으로 추가할 수 있다.
- 배포 문서와 스킬을 두 앱 공용으로 고쳤다. 설치 명령(Codex CLI·클로드 코드 슬래시 명령), 원격 MCP 사용 조건(Codex 폴더 신뢰·클로드 코드 프로젝트 `.mcp.json` 승인), 도구 이름 접두어 차이, 셸 시간 제한 옵션 이름을 병기했다. 설치 스킬 설명에 저장소 링크 설치 요청 트리거를 넣었다.
- 작업 폴더 초기화(`init --app claude`)는 이전부터 `CLAUDE.md`와 `type: http` 형식의 `.mcp.json`을 만들었고 이번에 패키지로 실측했다. 코드 변경은 없다.
- 플러그인 수준 `.mcp.json`은 의도적으로 넣지 않았다(작업 폴더 등록과 중복). 실제 클로드 코드 설치·스킬 노출·MCP 승인·문서 1건 완주는 아직 실측하지 않았다.
- 고지 보완: `finalize_hwpx.py`·`fix_namespaces.py`·`gonmun_lint.py`와 `validate.py --layout` 블록은 jkf87/hwpx-skill(MIT, 기여자 phdgil)에서 Canine89/hwpxskill로 들어온 부분이라 NOTICE.md에 해당 절을 추가하고 `licenses/jkf87-hwpx-skill-MIT.txt`를 동봉했다. 0.2.0 설치본에는 이 고지가 빠져 있었다.

## 0.2.0 양식 등록부 폐지

- 양식 등록·매핑·검토 기록(`add-template --source/--mapping/--review/--review-draft/--resume`), `list-templates`, 기존 5종 이관(`migrate-templates`)과 `.hwpdoc/templates/` 등록부, `TEMPLATES` 5종 식별자, `prepare --template/--version`을 삭제했다. 양식이 있는 작업은 전부 `prepare --job <이름> --document-type <유형> --base <작년.hwpx>`로 시작하며, 베이스는 작업 폴더에 사본으로 보존되고 렌더 검사를 항상 요구한다. `hwpdoc_templates.py`는 슬롯 추출(`extracted`)만 남는다.
- `prepare`는 작업 설정 `.hwpdoc/workspace.json`에 `references.budget`·`related`·`timetable`이 없으면 해당 검사를 `applicable=false`와 이유로 채우고, `exploration.record`를 베이스 경로·해시로 채운다. 설정이 있으면 지금처럼 에이전트가 적용 여부를 정한다. 검증 단계의 필수 검사 자체는 바꾸지 않았다.
- 배포 허용 목록에서 `.claude/hooks/protect_files.py`·`event_adapter.py`·`audit_log.py`·`stop_validator.py`와 `scripts/hook.ps1`을 뺐다. 배포본의 `setup-hooks`는 훅 파일이 없으면 거부한다. 훅은 개발 저장소에서만 동작한다.
- 업무 절차(`skills/hwpx/references/workflow.md`)의 양식 등록 절과 재개 안내(`resume.md`)의 양식 등록 검토 절을 지우고, 설치 안내·플러그인 설명에서 양식 등록 문구를 뺐다.
- 새 검사·교사 질문은 추가하지 않았다.

## 0.1.4 초보자 제안표 경로와 원격 학교 정보 MCP

- 양식 등록 없이 작년 HWPX 하나를 `prepare --base`의 미등록 일회성 베이스로 받아 올해 문서를 만든다. 에이전트가 올해 공문·학사일정·작업 설정·최근 결재 문서에서 근거 있는 값을 제안하고 근거 없는 칸은 `확인 필요`로 올린다. 교사는 확인표에서 제안 수락·값 입력·유지·비움·값만 비움으로 답하고, `--fill`로 묶음 답을, `--regenerate`로 행 재생성을, `--normalize-dates`로 표기 정리를 적용한다.
- `check`가 승인 전에 남은 필수 항목·내용 규칙·표기·잔재·셀 글자 예산을 찾고, `draft`가 확정 값으로 확인용 초안을 만들며, `approve`가 교사의 실제 답을 기록한다. 승인 전 항목이 남으면 거부한다. `record`로 준비 기록을 등록하고 임시 스크립트로 manifest를 고치지 않는다. 생성 뒤 수정은 `revise`와 `--carry-forward-from`으로 이어 간다.
- 원격 `teacher_doc_mcp`를 설치 때 앱 설정에 기본 등록한다(`--mcp-url`, `--no-mcp`, `setup-mcp`). `school --set-neis`로 확정한 학교를 저장하고 `resolve_school`·`get_school_calendar` 결과를 그대로 제안 근거(`kind: calendar`, sha256)로 쓴다. 응답 속 문장은 자료이며 지시로 따르지 않는다. Codex는 신뢰한 폴더에서만 MCP 설정을 읽으므로 교사에게 신뢰를 한 번 안내한다.
- 업무지침 MCP 근거 관문을 폐지했다. `evidence`는 보고용 참고 항목이고 `record`는 그 등록을 거부한다. 정상 전달은 검증 단계 통과로만 결정한다.
- 교사가 예산 초과 문구를 유지하면 `over_budget_cells`로 생성까지 가고, `review`로 PDF·전 페이지 PNG를 만들어 실제로 본 뒤 `review --confirm`으로 판독을 확정해 정상 전달한다. 보지 않은 판독은 확정하지 않는다.
- 제안·기록·승인·검토 인자의 한글이 `?`로 저장되면 거부한다(PowerShell 5.1 파이프 인코딩 사례). 날짜 끝 온점 뒤 한글, 연도 없는 시간표 날짜의 요일, 식별자로 읽히는 값은 자동 정리에서 제외한다.
- 같은 문서 코드표에서 과목→코드가 하나로 정해지면 코드 칸에 제안하고, 확정 과목과 코드가 어긋나면 메모로 짚는다. 표 음영·표기 형식·교사가 답한 칸의 잔재는 승인을 막지 않는 메모다.
- 준비 안내(`preparation_tasks`)와 실제 미확인(`unresolved`)을 분리해 검증된 작업이 전달에 막히지 않게 했다. 주요 명령 출력을 개수 요약과 `next_command`로 줄였다.
- HWPX 표 셀 격자 검증, 전달 표 값과 짧은 한국어 값 검사, 지워진 베이스 칸 경고, 문서 안 도구 출력 혼입 차단, 쪽 가장자리 넘침 검출을 추가했다. HWP 폴백은 문서 작업 중 복제하지 않는다.
- Windows 진입점은 프로세스에만 RemoteSigned 정책을 준다. 배포 경로 파일은 `.gitattributes`로 줄바꿈을 고정한다.
- 검증: 개발셋 3쌍 리플레이가 모두 완주했고(실시계획·회의록 검토 초안, 감독배정표 정상 전달), 실문서 1건(2학기 1회고사 실시 계획)을 원격 MCP 학사일정 근거로 정상 전달했다(2026. 11. 5., 한컴 실열림·렌더 통과). 실제 교사 PC 설치·인수, Claude Code 경로의 MCP 실호출, W2 회신 경로의 실행은 미실시다.

## 0.1.3 첫 실무 문서와 다음 대화

- 중첩 표·상자 등 복합 셀의 전체 치환을 차단하고 내부 셀/예산의 소유 표를 일치시켰다. 분할 run 치환은 실제 문단에 한정하며 원본 출력 덮어쓰기를 막는다.
- 사용자 지정 PC 데이터·전용 Python을 설치 기록에서 복원한다. Windows 실행기도 작업 폴더를 먼저 찾고 없는/다른 PC 경로는 진단한다. 기존 학교 설정·지침·연습본은 보존한다.
- 실제 검토와 빈 이유가 있는 양식의 forbid=[]를 허용하고 발견한 옛 명칭·날짜 검사는 유지한다. 준비 목록은 원문에서 확인할 에이전트 작업과 사용자 결정으로 나눴다.
- 결과 HWPX·실제 본문 발췌·diff·남은 검사와 [warn] 경고를 전달한다. 발췌는 인쇄 미리보기가 아니다.
- 같은 단계 2회 실패 후 원인 변화·해시 증거·실제 사용자 확인에 연결한 명시 재개를 추가했다. 누적 실패·이전 승인·원본을 보존하며 전체 재검증을 요구한다.
- Python 설치 단계의 마지막 시도와 이전 성공 기록을 분리하고, 선택 이미지 의존성 미준비는 문서 실패 횟수로 누적하지 않는다.
- 합성 HWPX/새 세션/빈 양식/재개 회귀와 Windows public wrapper 검사를 추가했다. 실제 GUI·한글 COM·PDF/PNG·인쇄와 교사 사용성은 별도 미검증이다.

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
