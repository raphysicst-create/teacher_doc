# 독립 Codex CLI 한글 COM 시간 초과 수정

2026. 9. 13. / teacher_doc / Codex CLI 0.147.0 / Python 3.12 / 한글 13.0.0.3903

## 판정

기존 사용자 설정을 상속한 **독립 Codex CLI에서 W1·W2의 한글 열기와 PDF 렌더 검사가 통과**했다. 이전 시험이 강제했던 `workspace-write`에서는 COM 검증이 여전히 불가하다. 이 경우 이제 COM 생성 전에 1초 이내에 구체적인 미확인 사유를 반환한다. 제한 모드의 성공으로 재분류하지 않는다.

사용자의 기존 `sandbox_mode = "danger-full-access"` 설정을 상속해 정상 실행을 확인했다. 이번 작업에서 사용자·프로젝트의 Codex 설정, Windows 권한, 레지스트리, 실행 정책은 변경하지 않았다. 제한 모드를 해제하는 코드를 실행기에 넣지 않았다.

## 확인된 원인

1. 이전 시험 드라이버가 `-s workspace-write`를 강제해 앱과 다른 실행 환경을 만들었다. 실제 CLI 명령에서 `CodexSandboxOffline`, `CodexSandboxDesktop-*`, 제한 토큰을 관측했다. 이 계정의 HKCU에는 FilePathCheckerModule 등록이 없었고 `DispatchEx`에서 25초 이상 대기했다.
2. 같은 사용자로 실행하는 `unelevated` 및 기본 데스크톱 호환 설정도 시험했으나 제한 토큰 환경에서는 COM 생성이 멈췄다. 이 설정들은 명령 한 번에만 적용했고 저장하지 않았다.
3. 사용자 기본 환경에서 COM 연결은 7.609초에 성공했지만, 독립 CLI 셸 도구가 전체 명령을 약 10초에 종료했다. 완료된 단계와 중단 기록을 보존하고, 동일 시험 사본으로 명령의 `timeout_ms=240000`을 명시해 재개했을 때 전체 검사가 완료됐다.

공식 문서는 elevated 모드의 별도 제한 사용자, unelevated 모드의 제한 토큰, 기본 격리 데스크톱을 설명한다. 한글 COM 지원 여부는 이 문서의 보장이 아니라 위 로컬 실측 결과다. [OpenAI Windows sandbox 문서](https://learn.chatgpt.com/docs/windows/windows-sandbox)

## 수정

- `hancom_com.py`에 제한 토큰·사용자·데스크톱 및 보안 모듈 사전 진단을 통합했다. `doctor`용 probe, `finalize --hancom`, `render_check`가 같은 진단을 사용한다.
- `DispatchEx`로 검사 전용 객체를 만들고, 보안 모듈 등록 실패 시 파일을 열지 않는다. 예외가 나도 소유 객체에 Quit를 호출하며, Quit 실패도 성공으로 숨기지 않는다.
- 실행기 시간 초과 출력에 기존 stdout/stderr를 보존한다. 전체 검증의 단계별 제한과 동일 단계 2회 실패 제한은 유지한다.
- HWPX 업무 절차에 CLI 셸 시간 한도 및 비동기 세션 대기 방법을 기록했다. 전체 검증에는 `timeout_ms=300000`을 명시하고, 세션 ID가 반환되면 재실행하지 않고 같은 세션을 기다린다.
- 배포 허용 목록에 공통 COM 모듈을 추가했다. 권리·자산 검토를 통과한 배포로 간주하지 않으며 패키지를 발행하지 않았다.

## 실제 독립 CLI 결과

| 검사 | 결과 | 실행 시간 |
|---|---|---:|
| COM 연결·보안 모듈 | 통과 | 7.609초 |
| W1 한글 열기 | 통과 | 10.360초 |
| W1 PDF·원본 대조 | 통과 | 26.797초 |
| W2 한글 열기 | 통과 | 7.969초 |
| W2 PDF·원본 대조 | 통과 | 21.063초 |

W1·W2 모두 결과/원본 1쪽, 텍스트 앵커 발견율과 순서 정합 1.0, 실패·경고 0건이다. 승인된 시험본의 사본만 사용했고 원본 HWPX 해시는 변하지 않았다. 발송이나 최종 사람 승인 기록은 만들지 않았다.

제한 환경 재시험은 probe 0.422초, Open 0.672초, render 0.484초에 `HANCOM_RESTRICTED_CONTEXT`를 반환했다. 검사 불가를 성공으로 바꾸지 않았으며 PDF도 생성하지 않았다.

회귀시험: COM 관련 9개, 실행기 20개, 문단 렌더 승인 4개, 렌더 비교 8개 — **41개 통과**. 스킬 기본 검증 및 `git diff --check` 통과.

## 증거

- `tmp/com-timeout-20260913/acceptance.json`: 단계별 명령·결과·원본 해시·중단/재개 기록
- `tmp/com-timeout-20260913/actual-cli.json`, `actual-cli.stdout.jsonl`: 실제 독립 CLI 실행과 종료 결과
- `tmp/com-timeout-20260913/restricted-acceptance.json`: 제한 모드에서 세 진입점의 즉시 미확인 결과
- `tmp/com-timeout-20260913/cli-shell-timeout.*`: 셸 기본 시간 한도로 중단된 최초 실행 보존
- `tmp/com-timeout-20260913/cli-staged.txt`, `cli-current-user.txt`, `cli-compatible.txt`: 수정 전 환경별 재현
- `tmp/com-timeout-20260913/launcher-policy-failure.*`: PowerShell 5 실행 정책으로 CLI 시작 전 중단된 별도 실행기 기록. 실행 정책을 바꾸지 않고 설치된 네이티브 CLI 실행 파일을 사용했다.

기존 176건 평가 및 과거 W1·W2 결과는 소급해서 덮어쓰지 않는다. 현재 판단은 **독립 CLI 기본 사용자 환경 COM 통과 / workspace-write COM 미지원·즉시 진단**이다. 외부 PC 검증, 전체 배포 판단, 최종 사람 문서 검토를 대신하지 않는다.
