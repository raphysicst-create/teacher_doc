# Claude 데스크톱 Cowork 확인 — 2026. 9. 13.

## 결론

Claude 데스크톱 앱을 실제로 열어 현재 Cowork 세션의 도구·실행 환경을 조회했다. **현재 구성에는 Windows 한글 COM을 호출할 연결 도구가 없어, W1·W2 한글 실열림/PDF 검증을 실행하지 못한다.** 이는 Claude Code CLI의 기존 통과 결과와 별개다. 앱의 다른 모드나 연결을 추가한 구성을 검증한 결과는 아니다.

## 관측

- 앱: Claude Desktop 1.52386.3, Windows x64. 사용자가 앱을 연 후 실제 데스크톱 창에서 `Claude 데스크톱 실행 환경 점검` 작업을 진행했다. 모델 표시는 Opus 5 엑스트라였다.
- `Checked computer status` 도구의 원시 Response를 펼쳐 `platform: win32`, `connectedFolders: []`, `localMcpServers: []`를 직접 확인했다.
- Claude의 실행 결과 보고: 클라우드 런타임은 Ubuntu 24.04.4 LTS, `win32com`은 ModuleNotFoundError. 클라우드 런타임 검사 도구 호출 목록은 관측했으나 개별 원시 stdout은 추가로 펼쳐 대조하지 못했다.
- Claude의 실행 결과 보고: `device_bash`는 연결 폴더가 없다는 오류로 실행되지 않았다. 도구 설명상 로컬 Linux VM에서 실행된다. 폴더를 연결한 뒤의 런타임 OS는 직접 시험하지 않았다.
- 한글 COM 객체 생성·문서 열기·PDF 내보내기는 미실행이다. 문서 실패나 전체 흐름 통과로 기록하지 않는다.

공식 아키텍처 문서도 클라우드 실행과 데스크톱 연결을 구분하며, 로컬 코드 실행은 호스트 OS와 격리된 Linux VM이라고 설명한다. 이 설명과 현재 연결 도구가 없다는 관측을 바탕으로, 한글 COM 실행에는 Windows 사용자 세션에서 동작하는 별도의 연결 도구가 필요하다고 판단한다. [Anthropic Cowork 아키텍처](https://support.claude.com/en/articles/14479288-claude-cowork-architecture-overview)

## 범위와 기록

현재 등록된 로컬 MCP가 없다는 상태만 확인했으며, 새 서버 설치·권한 변경·폴더 연결은 수행하지 않았다. W1·W2 원본이나 승인 기록도 수정하지 않았다. Claude는 읽기 전용 점검 요청 후 자체 메모리 2개를 업데이트했다고 표시했다. 이를 프로젝트 파일 변경과 구분해 기록하며 임의로 되돌리지 않았다.

최초 자동 실행 두 번의 도구 시간 초과 기록은 보존했다. 사용자 실행 후 앱 창과 진단 응답은 확인했으나, 추가 원시 로그 확인 중 해당 데스크톱 창이 목록에서 사라졌다. 원인을 앱 충돌로 단정하지 않는다.

- `tmp/claude-desktop-check-20260913/launch-status.json`: 최초 실행 시도
- `tmp/claude-desktop-check-20260913/cowork-result.json`: 직접 확인값·앱 보고값·미검증 범위
- `tmp/claude-desktop-check-20260913/cowork-response.txt`: 앱 진단 응답(UI 추출, 장치명 생략)

**판정: 현재 Claude Desktop Cowork 구성의 COM 연결 미구성 / W1·W2 전체 흐름 미실행.**
