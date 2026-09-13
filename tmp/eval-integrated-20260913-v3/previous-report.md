# 플러그인 보급 평가 통합표 — 2026. 9. 13. (2차 갱신)

이 표를 최신 통합 기준으로 사용한다. 최초 독립 평가 176행의 판정은 그대로 두고 이후 실제 시험·사용자 결정·현재 배포 게이트를 반영했다. 이번에는 새 앱 시험이나 독립 재채점을 하지 않았다. 이전 통합 JSON과 [이전 표 사본](../tmp/eval-integrated-20260913-v2/previous-report.md)을 보존했다.

## 현재 집계

| 상태 | 이전 | 현재 |
|---|---:|---:|
| 과거 합격 | 56 | 56 |
| 수정 후 확인 | 3 | 3 |
| 동작 확인 | 36 | 51 |
| 부분 확인 | 13 | 20 |
| 자료 확보·후속 대기 | 26 | 28 |
| 선행 조건 대기 | 29 | 7 |
| 미실행 | 4 | 2 |
| 범위 제외 | 9 | 9 |
| 합계 | **176** | **176** |

**후속 작업이 남은 행: 72 → 57개.** 부분 확인·자료 확보·선행 조건 대기·미실행의 합계다. 서로 다른 결함이나 사람 승인 횟수가 아니다. 동작 확인은 해당 후속 시험의 범위이며 독립 인수 합격으로 승격하지 않는다. 과거 합격도 최신 코드 전체 재시험을 뜻하지 않는다.

최초 독립 판정은 **합격 56 / 실패 3 / 미실행 2 / 차단 115**를 유지한다. 최초 실패 3행은 두 결함의 수정 재현 근거가 있으며 원래 기록을 삭제하지 않았다. 배포 판단은 **보류**다.

## 이번에 반영한 결과

- Claude Code CLI MCP 사전 차단, 두 앱 무표시 cwd, Stop 2회 실패 제한, Codex 미신뢰 훅 상태를 반영했다.
- 승인된 W1 기능 시험 계획과 W2 시스템 제출 내부결재는 Codex Desktop·Claude Code CLI에서 생성→전체 검증→시험 폴더 전달을 마쳤다. W2 system 2행에 반영하고 W1 기안문은 별도 실적으로 기록했다. 일반/회신형 가통(23·24)과 W2 공문·메일 제출은 통과로 바꾸지 않았다.
- 전달 성공·충돌·2회 실패 한도 6행을 동작 확인으로 반영했다. 폴더 부재 복구는 일부 파일 복사 뒤 실패와 달라 copy_partial은 부분 확인이다. 실제 OneDrive 전송·사람 최종 평점은 별도다.
- 새 등록은 완료했으나 양식 출처 unconfirmed와 네이티브 가통 조건 차이를 유지한다. 기안문 W2의 문단 1자 초과 판독을 사례 26의 표 셀 초과 판독으로 전용하지 않았다.
- HWP 변환 렌더 오탐 수정 후 PASS와 원본 기인 경고, 7쪽 픽셀 동일 결과를 반영했다. 과거 FAIL과 앱별 전체 경로 미완료는 보존했다.

## 환경별 범위 — 176행과 별도 표시

| 환경 | 확인한 범위 | 남은 범위 |
|---|---|---|
| Codex Desktop | 승인 W1·W2 생성·전체 검증·시험 전달 | 다른 업무 분기·배포 인수 |
| Claude Code CLI 2.1.270 | 승인 W1·W2 생성·전체 검증·시험 전달 | Claude Desktop 결과와 구분 |
| 독립 Codex CLI 0.147.0 기본 사용자 환경 | W1·W2 COM 열기·PDF 비교 통과 | 독립 CLI 전체 흐름 인수와 구분 |
| Codex CLI workspace-write | COM 불가를 1초 이내 실패·미확인으로 반환 | 제한 모드 COM 지원 미완료 |
| Claude Desktop Cowork 1.52386.3 | 실제 앱에서 localMcpServers=[] 확인 | Windows COM 연결 없음·W1/W2 미실행 |
| VS Code | 이번 최신 전체 흐름 근거 없음 | 현재 소스로 별도 인수 필요 |
| 외부 PC | 사용자 요청으로 제외 | 현재 작업에서 시험하지 않음 |

Claude Desktop·VS Code 상태는 기존 target 이름에 끼워 넣어 176행의 수를 바꾸지 않았다. 후속 자료의 claude는 실제 호스트가 Claude Code CLI임을 명시한다.

[승인 후 흐름 보고서](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) · [CLI COM 보고서](../docs/Codex-CLI-COM-시간초과-수정-2026-09-13.md) · [Claude 앱 보고서](../docs/Claude-데스크톱-Cowork-확인-2026-09-13.md)

## 배포 검토

Canine89 개인 MIT 허락과 무료 AGPL 선택·소스/고지 준비 완료. 현재 허용 목록 101파일의 게이트: rights_unconfirmed 73, privacy_unconfirmed 73, dependency_license_unconfirmed 7. 정식 패키지 미생성.

파일별 권리/개인정보 미확인 수는 같은 파일에 대한 서로 다른 검토 항목이다. 고지 동봉이나 MIT 허락을 기존 파일 전체의 현재 해시 검토 완료로 간주하지 않는다. 실제 패키지 생성·설치·업데이트·제거 시험은 남아 있다. [현재 게이트 원시 결과](../tmp/eval-integrated-20260913-v2/release-gate.json)

## 남은 실행 목록

| 사례 | 남은 행 | 다음 처리 |
|---|---:|---|
| 09 새 네이티브 양식 등록 | 2 | 네이티브 출처가 확인된 가통으로 사례 09의 등록 조건을 확인. |
| 11 양식 복수 용도와 기안문 계보 | 4 | 같은 승인 베이스를 가통 발송 용도에도 연결하고 제목 굵기·여백·용도 선택을 확인. |
| 13 새 세션의 업무 지침 실제 로딩 | 2 | 격리 설치의 새 문맥에서 스킬/업무 지침 본문 로딩 근거 확인. |
| 14 메모리 없이 학교 정책·공통 규칙 유지 | 8 | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. |
| 15 실제 도구의 원본 수정 차단 | 2 | 해당 앱 MCP 도구 연결·실호출·사전 차단을 같은 인수 환경에서 확인. |
| 16 정상 작업과 다른 프로젝트 오차단 방지 | 1 | 폐기용 무표시 cwd/비공문 경로를 포함한 앱 권한 조건으로 실행. |
| 17 훅 신뢰·실행 실패·한글 인코딩 | 1 | 미신뢰 진입 거부 관측을 유지하고 호스트 허용 조건·보호 가능 안내의 남은 범위를 확인. |
| 19 배포 허용 목록과 식별정보 검사 | 2 | 허가된 릴리스 사본에서 clean 또는 5위치 시험 표식 탐지를 실행. |
| 20 라이선스·출처·버전 고정 | 1 | 현재 해시별 권리·개인정보와 나머지 의존성 조건 검토를 완료. MIT/AGPL 선택을 다시 요청하지 않음. |
| 22 설치 업데이트·제거의 자료 보존 | 4 | 허가된 구·신 패키지로 실제 앱 업데이트/제거와 자료 보존 확인. |
| 23 W1 일반 가정통신문 전체 과정 | 2 | 기존 일반 가통으로 앱 초안을 제시하고 문안 확인→전체 검증→전달 진행. |
| 24 참가 회신형 가통 전체 과정 | 2 | 기존 회신형으로 앱 초안을 제시하고 문안 확인→전체 검증→전달 진행. |
| 25 활동 행 부족과 구조 변경 범위 | 2 | 구체적인 데이터 1행 추가 범위의 확인 후 구조·쪽수·렌더 검증. |
| 26 셀 글자 예산 초과와 판독 증거 | 4 | 오래된 판독 또는 현재 판독 조건을 각각 구성하고 최종 해시와 대조. |
| 27 W2 제출 방법 네 분기 | 4 | 해당 제출 방식의 원문으로 초안을 제시하고 확인 후 생성·검증·시험 전달. |
| 28 내용·검증 실패와 성공 오보고 방지 | 2 | 실제 불가 상태가 실행기 전체 보고·전달 금지까지 유지되는지 확인; 렌더 자체 부재는 COM 불가와 별도 시험. |
| 29 검토본 전달·재시도·사람 확인 | 8 | 준비된 시험 작업 사본으로 해당 전달 분기를 실행하고 검증 상태·sent=false 보존 확인. / 일부 파일 복사 뒤 실패하는 조건을 구성해 복사만 재시도하고 기존 검증·파일 보존 확인. / 검토할 앱 산출물을 준비하고 해당 복사/검토 분기를 실행. |
| 32 HWP 변환·재패키징·폴백 경로 | 6 | 해당 앱에서 지정한 입력·폴백 조건의 전체 흐름을 실행. 원본 기인 경고와 새 잔재 실패 구분 유지. |

## 상태 변경 목록

| ID | 이전 | 현재 |
|---|---|---|
| 09--claude--default | 자료 확보·후속 대기 | 부분 확인 |
| 16--claude--no_marker | 미실행 | 동작 확인 |
| 18--claude--twice_failed | 부분 확인 | 동작 확인 |
| 27--claude--system | 선행 조건 대기 | 동작 확인 |
| 27--claude--official_reply | 선행 조건 대기 | 자료 확보·후속 대기 |
| 27--claude--email | 선행 조건 대기 | 자료 확보·후속 대기 |
| 29--claude--copy_success | 선행 조건 대기 | 동작 확인 |
| 29--claude--copy_collision | 선행 조건 대기 | 동작 확인 |
| 29--claude--copy_twice_failed | 선행 조건 대기 | 동작 확인 |
| 29--claude--copy_partial | 선행 조건 대기 | 부분 확인 |
| 29--claude--copy_off | 선행 조건 대기 | 자료 확보·후속 대기 |
| 29--claude--draft_only | 선행 조건 대기 | 자료 확보·후속 대기 |
| 32--claude--hwp_input | 자료 확보·후속 대기 | 부분 확인 |
| 32--claude--repackaged | 자료 확보·후속 대기 | 부분 확인 |
| 09--codex--default | 자료 확보·후속 대기 | 부분 확인 |
| 16--codex--no_marker | 미실행 | 동작 확인 |
| 18--codex--twice_failed | 부분 확인 | 동작 확인 |
| 27--codex--system | 선행 조건 대기 | 동작 확인 |
| 27--codex--official_reply | 선행 조건 대기 | 자료 확보·후속 대기 |
| 27--codex--email | 선행 조건 대기 | 자료 확보·후속 대기 |
| 29--codex--copy_success | 선행 조건 대기 | 동작 확인 |
| 29--codex--copy_collision | 선행 조건 대기 | 동작 확인 |
| 29--codex--copy_twice_failed | 선행 조건 대기 | 동작 확인 |
| 29--codex--copy_partial | 선행 조건 대기 | 부분 확인 |
| 29--codex--copy_off | 선행 조건 대기 | 자료 확보·후속 대기 |
| 29--codex--draft_only | 선행 조건 대기 | 자료 확보·후속 대기 |
| 32--codex--hwp_input | 자료 확보·후속 대기 | 부분 확인 |
| 32--codex--repackaged | 자료 확보·후속 대기 | 부분 확인 |
| 15--claude--mcp_patch | 선행 조건 대기 | 동작 확인 |
| 15--claude--mcp_fill | 선행 조건 대기 | 동작 확인 |
| 17--codex--untrusted | 부분 확인 | 동작 확인 |
| 28--cli--com_unavailable | 선행 조건 대기 | 부분 확인 |
| 28--cli--render_unavailable | 선행 조건 대기 | 부분 확인 |

## 176행 상세

최초 판정과 현재 후속 상태를 분리한다. 전체 근거 해시와 변경 이력은 JSON에 보관했다.

| ID | 시험 | 최초 | 현재 | 최신 관측 | 다음 처리 | 근거 |
|---|---|---|---|---|---|---|
| 01--cli--일반가통 | 기존 5종 반복 생성과 서식 보존 | pass | 과거 합격 | 양식 일반가통: 기준/후보 각 2회 실제 생성·검증, 4개 결과 SHA256 동일, ZIP 엔트리 차이 없음. 실제 PDF/PNG의 서식 일치 확인. 합성 승인만 사용. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/01--cli--일반가통.json) |
| 01--cli--회신형 | 기존 5종 반복 생성과 서식 보존 | pass | 과거 합격 | 양식 회신형: 기준/후보 각 2회 실제 생성·검증, 4개 결과 SHA256 동일, ZIP 엔트리 차이 없음. 실제 PDF/PNG의 서식 일치 확인. 합성 승인만 사용. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/01--cli--회신형.json) |
| 01--cli--고사안내 | 기존 5종 반복 생성과 서식 보존 | pass | 과거 합격 | 양식 고사안내: 기준/후보 각 2회 실제 생성·검증, 4개 결과 SHA256 동일, ZIP 엔트리 차이 없음. 실제 PDF/PNG의 서식 일치 확인. 합성 승인만 사용. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/01--cli--고사안내.json) |
| 01--cli--성립전예산요구 | 기존 5종 반복 생성과 서식 보존 | pass | 과거 합격 | 양식 성립전예산요구: 기준/후보 각 2회 실제 생성·검증, 4개 결과 SHA256 동일, ZIP 엔트리 차이 없음. 실제 PDF/PNG의 서식 일치 확인. 합성 승인만 사용. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/01--cli--성립전예산요구.json) |
| 01--cli--교과협의회 | 기존 5종 반복 생성과 서식 보존 | pass | 과거 합격 | 양식 교과협의회: 기준/후보 각 2회 실제 생성·검증, 4개 결과 SHA256 동일, ZIP 엔트리 차이 없음. 실제 PDF/PNG의 서식 일치 확인. 합성 승인만 사용. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/01--cli--교과협의회.json) |
| 02--cli--default | 기준 변경 검수와 배포 전 기록 분리 | pass | 과거 합격 | 미커밋·미추적 파일을 포함한 162개 대상 해시 및 영역별 목록 동결. 70개 배포 허용 소스 포함 여부 대조. 원격 공개 여부 미확인, 릴리스 미제작을 명시. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/02--cli--default.json) |
| 03--cli--claude_empty | 작업 폴더 초기화와 기존 지침 보존 | pass | 과거 합격 | 선택한 앱 지침만 생성. 기존 KEEP_EXISTING은 해시/본문 그대로이고 병합 제안 별도 생성. 동일 위치 재초기화와 폐기용 코드/부모 루트 초기화는 종료 2로 거절. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/03--cli--claude_empty.json) |
| 03--cli--codex_empty | 작업 폴더 초기화와 기존 지침 보존 | pass | 과거 합격 | 선택한 앱 지침만 생성. 기존 KEEP_EXISTING은 해시/본문 그대로이고 병합 제안 별도 생성. 동일 위치 재초기화와 폐기용 코드/부모 루트 초기화는 종료 2로 거절. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/03--cli--codex_empty.json) |
| 03--cli--claude_existing | 작업 폴더 초기화와 기존 지침 보존 | pass | 과거 합격 | 선택한 앱 지침만 생성. 기존 KEEP_EXISTING은 해시/본문 그대로이고 병합 제안 별도 생성. 동일 위치 재초기화와 폐기용 코드/부모 루트 초기화는 종료 2로 거절. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/03--cli--claude_existing.json) |
| 03--cli--codex_existing | 작업 폴더 초기화와 기존 지침 보존 | pass | 과거 합격 | 선택한 앱 지침만 생성. 기존 KEEP_EXISTING은 해시/본문 그대로이고 병합 제안 별도 생성. 동일 위치 재초기화와 폐기용 코드/부모 루트 초기화는 종료 2로 거절. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/03--cli--codex_existing.json) |
| 03--cli--reinitialize | 작업 폴더 초기화와 기존 지침 보존 | pass | 과거 합격 | 선택한 앱 지침만 생성. 기존 KEEP_EXISTING은 해시/본문 그대로이고 병합 제안 별도 생성. 동일 위치 재초기화와 폐기용 코드/부모 루트 초기화는 종료 2로 거절. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/03--cli--reinitialize.json) |
| 04--cli--separate_roots | 코드·작업 위치 분리와 폴더 이동 | pass | 과거 합격 | 분리한 작업 폴더 안에 prepare 원문 사본·상대경로 manifest·로그를 생성. 승인 없음 유지. 준비 상태에는 job report가 없어 status가 unconfirmed/종료 2. 정상 v2 이동 대조는 07 portable_record에 별도로 기록. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/04--cli--separate_roots.json) |
| 04--cli--workspace_relocation | 코드·작업 위치 분리와 폴더 이동 | pass | 과거 합격 | 분리한 작업 폴더 안에 prepare 원문 사본·상대경로 manifest·로그를 생성. 승인 없음 유지. 준비 상태에는 job report가 없어 status가 unconfirmed/종료 2. 정상 v2 이동 대조는 07 portable_record에 별도로 기록. 옛 A 경로는 lab 안에서 이름을 바꿔 참조할 수 없게 했고 B의 원문 사본/manifest 해시 보존. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/04--cli--workspace_relocation.json) |
| 04--cli--unicode_space | 코드·작업 위치 분리와 폴더 이동 | pass | 과거 합격 | 분리한 작업 폴더 안에 prepare 원문 사본·상대경로 manifest·로그를 생성. 승인 없음 유지. 준비 상태에는 job report가 없어 status가 unconfirmed/종료 2. 정상 v2 이동 대조는 07 portable_record에 별도로 기록. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/04--cli--unicode_space.json) |
| 04--cli--long_path | 코드·작업 위치 분리와 폴더 이동 | fail | 수정 후 확인 | 긴 경로를 mkdir 전에 거절하고 지원 범위 안내; 부분 폴더 생성 없음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/04-long-path.json) |
| 05--cli--valid_python | Python 진단과 외부 복사 선택 설정 | pass | 과거 합격 | 격리 PC 설정과 PowerShell 진입점을 실제 실행. Python312/8패키지 실제 import와 COM 진단, 누락/실행불가 Python 거절. 운영 PC 설정 변경 없음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/05--cli--valid_python.json) |
| 05--cli--missing_python | Python 진단과 외부 복사 선택 설정 | pass | 과거 합격 | 격리 PC 설정과 PowerShell 진입점을 실제 실행. Python312/8패키지 실제 import와 COM 진단, 누락/실행불가 Python 거절. 운영 PC 설정 변경 없음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/05--cli--missing_python.json) |
| 05--cli--wrong_python | Python 진단과 외부 복사 선택 설정 | pass | 과거 합격 | 격리 PC 설정과 PowerShell 진입점을 실제 실행. Python312/8패키지 실제 import와 COM 진단, 누락/실행불가 Python 거절. 운영 PC 설정 변경 없음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/05--cli--wrong_python.json) |
| 05--cli--copy_disabled | Python 진단과 외부 복사 선택 설정 | pass | 과거 합격 | 격리 PC 설정과 PowerShell 진입점을 실제 실행. Python312/8패키지 실제 import와 COM 진단, 누락/실행불가 Python 거절. 운영 PC 설정 변경 없음. 외부 복사 미설정은 not_applicable, 로컬 전달은 실제 성공. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/05--cli--copy_disabled.json) |
| 05--cli--copy_configured | Python 진단과 외부 복사 선택 설정 | pass | 과거 합격 | 격리 PC 설정과 PowerShell 진입점을 실제 실행. Python312/8패키지 실제 import와 COM 진단, 누락/실행불가 Python 거절. 운영 PC 설정 변경 없음. 최초 검증 전 시험 외부 경로를 설정한 대조군은 전체 검증/로컬·외부 전달 성공. 검증 뒤 설정만 바꾼 별도 입력은 재검증 요구로 거절. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/05--cli--copy_configured.json) |
| 06--cli--timetable | 학교별 시간표·예산·관련번호 조회 | pass | 과거 합격 | 가람 1·2학년 합계 과학2/수학1/국어1, 누리 1·2·3학년 과학3/영어1/수학1/체육1을 원문과 대조. 원문 xlsx/명시 매핑에서 기계 재생성. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/06--cli--timetable.json) |
| 06--cli--budget | 학교별 시간표·예산·관련번호 조회 | pass | 과거 합격 | 가상 두 학교 xls 원문에서 파생값 재생성, 각각 유효 2개 통과·미등록 이름 종료1. 금액 적정성 판단으로 승격하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/06--cli--budget.json) |
| 06--cli--related | 학교별 시간표·예산·관련번호 조회 | pass | 과거 합격 | 각 workspace에 같은 101번의 두 기관 원문을 함께 두고 각각 조회. 학교별 제목·시행일 구분, 결재일 2000년 대신 시행일 사용. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/06--cli--related.json) |
| 06--cli--missing_sources | 학교별 시간표·예산·관련번호 조회 | pass | 과거 합격 | 시간표/예산 설정 부재 종료2, 관련 원문 부재 종료1. 현재 학교 자료로 자동 대체하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/06--cli--missing_sources.json) |
| 07--cli--legacy_absolute | 기존 작업 기록과 승인 해시 호환 | pass | 과거 합격 | 정상 v2 사본 이동은 status pass/종료0. 원문 또는 manifest 변경은 unconfirmed/종료2, 기존 승인 해시를 재작성하지 않음. 실제 baseline v1 절대경로 보고서는 읽되 구형 runtime 증거 부재 등을 미확인으로 보존. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/07--cli--legacy_absolute.json) |
| 07--cli--portable_record | 기존 작업 기록과 승인 해시 호환 | pass | 과거 합격 | 정상 v2 사본 이동은 status pass/종료0. 원문 또는 manifest 변경은 unconfirmed/종료2, 기존 승인 해시를 재작성하지 않음. 실제 baseline v1 절대경로 보고서는 읽되 구형 runtime 증거 부재 등을 미확인으로 보존. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/07--cli--portable_record.json) |
| 07--cli--changed_source | 기존 작업 기록과 승인 해시 호환 | pass | 과거 합격 | 정상 v2 사본 이동은 status pass/종료0. 원문 또는 manifest 변경은 unconfirmed/종료2, 기존 승인 해시를 재작성하지 않음. 실제 baseline v1 절대경로 보고서는 읽되 구형 runtime 증거 부재 등을 미확인으로 보존. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/07--cli--changed_source.json) |
| 07--cli--changed_manifest | 기존 작업 기록과 승인 해시 호환 | pass | 과거 합격 | 정상 v2 사본 이동은 status pass/종료0. 원문 또는 manifest 변경은 unconfirmed/종료2, 기존 승인 해시를 재작성하지 않음. 실제 baseline v1 절대경로 보고서는 읽되 구형 runtime 증거 부재 등을 미확인으로 보존. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/07--cli--changed_manifest.json) |
| 08--cli--default | 기존 5종 등록 이관과 선택 연속성 | blocked | 동작 확인 | 사용자의 기존양식 5종 승인 기록과 현재 등록 해시 확인. 5종 목록/등록 버전 prepare 및 원본 보존 대조 완료. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/08-prepare-4.json) |
| 09--claude--default | 새 네이티브 양식 등록 | blocked | 부분 확인 | Claude Code CLI에서 trial-gianmun 매핑·8단계 준비·현재 검토 등록 후 W1/W2에 사용. 출처는 unconfirmed를 보존하고 실제 비교 렌더를 필수 실행했다. 새 네이티브 가통 등록 조건은 미완료. | 네이티브 출처가 확인된 가통으로 사례 09의 등록 조건을 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 09--codex--default | 새 네이티브 양식 등록 | blocked | 부분 확인 | Codex Desktop에서 trial-gianmun 매핑·8단계 준비·현재 검토 등록 후 W1/W2에 사용. 출처는 unconfirmed를 보존하고 실제 비교 렌더를 필수 실행했다. 새 네이티브 가통 등록 조건은 미완료. | 네이티브 출처가 확인된 가통으로 사례 09의 등록 조건을 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 10--cli--unknown_slot | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--unknown_slot.json) |
| 10--cli--duplicate_slot | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--duplicate_slot.json) |
| 10--cli--missing_file | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--missing_file.json) |
| 10--cli--changed_hash | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--changed_hash.json) |
| 10--cli--missing_review | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--missing_review.json) |
| 10--cli--changed_review | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--changed_review.json) |
| 10--cli--changed_mapping | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--changed_mapping.json) |
| 10--cli--changed_profile | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--changed_profile.json) |
| 10--cli--path_escape | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--path_escape.json) |
| 10--cli--junction_escape | 등록 오류와 변경 감지 | pass | 과거 합격 | 정상 등록 사본은 prepare에서 선택돼 미승인 manifest를 생성. 해당 오류 입력은 종료2 또는 changed/draft로 사용 거절. 소스 원본 해시와 기존 등록 기준을 보존. 합성 CLI 등록은 사람 확인 실적 아님. 실제 lab junction의 바깥 해석 대상을 경로 이탈로 거절, sentinel 보존. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/10--cli--junction_escape.json) |
| 11--claude--internal_approval | 양식 복수 용도와 기안문 계보 | blocked | 부분 확인 | 8건 기안문 계보 대조에 더해 Claude Code CLI의 승인된 W1 기능 시험 계획/W2 시스템 제출 내부결재를 생성·검증·전달. 같은 베이스의 가통 발송 용도까지 확인한 것은 아님. | 같은 승인 베이스를 가통 발송 용도에도 연결하고 제목 굵기·여백·용도 선택을 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 11--claude--notice_dispatch | 양식 복수 용도와 기안문 계보 | blocked | 부분 확인 | 8건 기안문 계보 대조에 더해 Claude Code CLI의 승인된 W1 기능 시험 계획/W2 시스템 제출 내부결재를 생성·검증·전달. 같은 베이스의 가통 발송 용도까지 확인한 것은 아님. | 같은 승인 베이스를 가통 발송 용도에도 연결하고 제목 굵기·여백·용도 선택을 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 11--codex--internal_approval | 양식 복수 용도와 기안문 계보 | blocked | 부분 확인 | 8건 기안문 계보 대조에 더해 Codex Desktop의 승인된 W1 기능 시험 계획/W2 시스템 제출 내부결재를 생성·검증·전달. 같은 베이스의 가통 발송 용도까지 확인한 것은 아님. | 같은 승인 베이스를 가통 발송 용도에도 연결하고 제목 굵기·여백·용도 선택을 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 11--codex--notice_dispatch | 양식 복수 용도와 기안문 계보 | blocked | 부분 확인 | 8건 기안문 계보 대조에 더해 Codex Desktop의 승인된 W1 기능 시험 계획/W2 시스템 제출 내부결재를 생성·검증·전달. 같은 베이스의 가통 발송 용도까지 확인한 것은 아님. | 같은 승인 베이스를 가통 발송 용도에도 연결하고 제목 굵기·여백·용도 선택을 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 12--cli--complete_values | prepare의 기계 기록과 미확인 유지 | pass | 과거 합격 | 원문 사본/해시·슬롯 추출과 version2 manifest 생성. confirmed=false, evidence.record 빈 값, checks=null 유지, 미승인 build 거절. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/12--cli--complete_values.json) |
| 12--cli--missing_values | prepare의 기계 기록과 미확인 유지 | fail | 수정 후 확인 | W1/W2 미제공 슬롯 목록을 표시하고 승인/제출 방법 미확인을 유지. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/12-W1-observation.json) |
| 12--cli--w2_missing_method | prepare의 기계 기록과 미확인 유지 | fail | 수정 후 확인 | W1/W2 미제공 슬롯 목록을 표시하고 승인/제출 방법 미확인을 유지. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/12-W2-observation.json) |
| 13--claude--default | 새 세션의 업무 지침 실제 로딩 | blocked | 부분 확인 | 앱의 새 시험 세션에서 로컬 지침/스킬 읽기 확인. 전역 메모리가 없는 정식 설치 패키지 조건을 충족한 독립 인수는 아님. | 격리 설치의 새 문맥에서 스킬/업무 지침 본문 로딩 근거 확인. | [근거](../tmp/followup-20260913/evidence/claude-final-normal.json) |
| 13--codex--default | 새 세션의 업무 지침 실제 로딩 | blocked | 부분 확인 | 앱의 새 시험 세션에서 로컬 지침/스킬 읽기 확인. 전역 메모리가 없는 정식 설치 패키지 조건을 충족한 독립 인수는 아님. | 격리 설치의 새 문맥에서 스킬/업무 지침 본문 로딩 근거 확인. | [근거](../tmp/followup-20260913/evidence/claude-final-normal.json) |
| 14--claude--precedent | 메모리 없이 학교 정책·공통 규칙 유지 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 14--claude--empty_cells | 메모리 없이 학교 정책·공통 규칙 유지 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 14--claude--grade_absent | 메모리 없이 학교 정책·공통 규칙 유지 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 14--claude--metadata | 메모리 없이 학교 정책·공통 규칙 유지 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 14--codex--precedent | 메모리 없이 학교 정책·공통 규칙 유지 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 14--codex--empty_cells | 메모리 없이 학교 정책·공통 규칙 유지 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 14--codex--grade_absent | 메모리 없이 학교 정책·공통 규칙 유지 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 14--codex--metadata | 메모리 없이 학교 정책·공통 규칙 유지 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 15--claude--edit | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-final-normal-after.json) |
| 15--claude--delete | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before.json) |
| 15--claude--move | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before.json) |
| 15--claude--mixed | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. Claude Bash의 복합 명령으로 시험했으며 Codex의 원자적 apply_patch와 도구 형태는 다름. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-mixed-after.json) |
| 15--claude--powershell_write | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-final-normal-after.json) |
| 15--claude--mcp_patch | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | Claude Code CLI 두 번째 좁힌 시험에서 kordoc patch_document/fill_form 실제 PreToolUse exit 2·deny 확인, 두 HWPX 사본 해시 불변. 첫 호출 생략·360초 종료는 실패 이력으로 보존. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 15--claude--mcp_fill | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | Claude Code CLI 두 번째 좁힌 시험에서 kordoc patch_document/fill_form 실제 PreToolUse exit 2·deny 확인, 두 HWPX 사본 해시 불변. 첫 호출 생략·360초 종료는 실패 이력으로 보존. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 15--claude--junction_escape | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before.json) |
| 15--codex--edit | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before-v4.json) |
| 15--codex--delete | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before-v4.json) |
| 15--codex--move | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before-v4.json) |
| 15--codex--mixed | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before-v4.json) |
| 15--codex--powershell_write | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before-v4.json) |
| 15--codex--mcp_patch | 실제 도구의 원본 수정 차단 | blocked | 부분 확인 | 현재 Codex Desktop 구현 세션에서 실제 kordoc patch_document/fill_form이 PreToolUse로 차단되고 원본 불변. 독립 설치 세션의 MCP 접두어/전체 설정 인수는 미완료. | 해당 앱 MCP 도구 연결·실호출·사전 차단을 같은 인수 환경에서 확인. | [근거](../tmp/followup-20260913/evidence/mcp-read-current.json) |
| 15--codex--mcp_fill | 실제 도구의 원본 수정 차단 | blocked | 부분 확인 | 현재 Codex Desktop 구현 세션에서 실제 kordoc patch_document/fill_form이 PreToolUse로 차단되고 원본 불변. 독립 설치 세션의 MCP 접두어/전체 설정 인수는 미완료. | 해당 앱 MCP 도구 연결·실호출·사전 차단을 같은 인수 환경에서 확인. | [근거](../tmp/followup-20260913/evidence/mcp-read-current.json) |
| 15--codex--junction_escape | 실제 도구의 원본 수정 차단 | blocked | 동작 확인 | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/extra-hook-before-v4.json) |
| 16--claude--read | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-final-normal-after.json) |
| 16--claude--copy_new | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. 앱 설명에서 정상 복사를 보호 공백으로 잘못 해석했으나 실제 동작은 명세대로 허용됨. 후속 시험 입력에서 허용 범위를 명확히 했고 보고에 이 한계를 보존함. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-final-normal-after.json) |
| 16--claude--new_output | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-final-normal-after.json) |
| 16--claude--outside_docs | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-final-normal-after.json) |
| 16--claude--no_marker | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | Claude 실제 pre/post가 빈 결과를 반환하고 Edit 성공; 공문 표시 없는 cwd에서 오차단 없음. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 16--codex--read | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/codex-host-after-v4.json) |
| 16--codex--copy_new | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/codex-host-after-v4.json) |
| 16--codex--new_output | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/codex-host-after-v4.json) |
| 16--codex--outside_docs | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 부분 확인 | 올바른 형제 fixture로 재실행했으나 Codex workspace-write 자체 경계에서 거절. hwpdoc 오차단으로 판정하지 않음. 폐기용 비공문 경로를 포함한 앱 샌드박스 인수 환경 필요. | 폐기용 무표시 cwd/비공문 경로를 포함한 앱 권한 조건으로 실행. | [근거](../tmp/followup-20260913/evidence/codex-outside-after.json) |
| 16--codex--no_marker | 정상 작업과 다른 프로젝트 오차단 방지 | blocked | 동작 확인 | Codex 훅을 정상 신뢰한 무표시 cwd에서 실제 apply_patch 성공; 최초 미신뢰 호출과 분리해 판정. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 17--claude--untrusted | 훅 신뢰·실행 실패·한글 인코딩 | blocked | 부분 확인 | Claude Code 미신뢰 진입에서 No, exit 선택을 실제 확인: exit 1, 모델/도구 턴 없음, 파일 불변. 쓰기 도구에 대한 훅 차단이나 보호 가능 여부의 모델 안내까지 시험한 결과는 아님. | 미신뢰 진입 거부 관측을 유지하고 호스트 허용 조건·보호 가능 안내의 남은 범위를 확인. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 17--claude--python_missing | 훅 신뢰·실행 실패·한글 인코딩 | blocked | 동작 확인 | 프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/bootstrap-claude-python_missing-after.json) |
| 17--claude--hook_error | 훅 신뢰·실행 실패·한글 인코딩 | blocked | 동작 확인 | 프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-utf8-after.json) |
| 17--claude--utf8_path | 훅 신뢰·실행 실패·한글 인코딩 | blocked | 동작 확인 | 실제 한글 경로 보호 이벤트 정상. 추가로 PowerShell의 한국어 오류 깨짐을 수정하고 두 앱 셸 회귀 + 실제 Claude 오류 출력 재확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-utf8-after.json) |
| 17--codex--untrusted | 훅 신뢰·실행 실패·한글 인코딩 | blocked | 동작 확인 | 실제 Codex에서 프로젝트 미신뢰 및 프로젝트 신뢰/훅 정의 미신뢰 조건 모두 쓰기 성공. 미신뢰 상태에서는 프로젝트 훅 보호를 주장할 수 없음을 확인했으며 정상 신뢰 후 차단 결과와 구분. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 17--codex--python_missing | 훅 신뢰·실행 실패·한글 인코딩 | blocked | 동작 확인 | 프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/bootstrap-codex-python_missing-after.json) |
| 17--codex--hook_error | 훅 신뢰·실행 실패·한글 인코딩 | blocked | 동작 확인 | 프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/bootstrap-codex-hook_error-after.json) |
| 17--codex--utf8_path | 훅 신뢰·실행 실패·한글 인코딩 | blocked | 동작 확인 | 실제 한글 경로 보호 이벤트 정상. 추가로 PowerShell의 한국어 오류 깨짐을 수정하고 두 앱 셸 회귀 + 실제 Claude 오류 출력 재확인. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-utf8-after.json) |
| 18--claude--unchanged | Stop 빠른 검사와 재시도 제한 | blocked | 동작 확인 | 깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-mixed.json) |
| 18--claude--invalid_output | Stop 빠른 검사와 재시도 제한 | blocked | 동작 확인 | 깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-mixed.json) |
| 18--claude--twice_failed | Stop 빠른 검사와 재시도 제한 | blocked | 동작 확인 | 실제 Stop에서 BROKEN_0 첫 차단→BROKEN_1 둘째 차단→BROKEN_2 자동 교정 중단 안내. 단계 실패를 유지했으며 저장된 ok=false는 통과로 바꾸지 않음. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 18--codex--unchanged | Stop 빠른 검사와 재시도 제한 | blocked | 동작 확인 | 깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/codex-outside-after.json) |
| 18--codex--invalid_output | Stop 빠른 검사와 재시도 제한 | blocked | 동작 확인 | 깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/codex-outside-after.json) |
| 18--codex--twice_failed | Stop 빠른 검사와 재시도 제한 | blocked | 동작 확인 | 실제 Stop에서 BROKEN_0 첫 차단→BROKEN_1 둘째 차단→BROKEN_2 자동 교정 중단 안내. 단계 실패를 유지했으며 저장된 ok=false는 통과로 바꾸지 않음. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 19--cli--clean | 배포 허용 목록과 식별정보 검사 | pending | 미실행 | 실제 릴리스 ZIP 미제작. 허용 목록 정의만으로 clean 또는 5위치 sentinel 탐지 실험을 수행했다고 보지 않음. 이번에도 실제 패키지 시험 미실행, 최초 stale 표시 보존. | 허가된 릴리스 사본에서 clean 또는 5위치 시험 표식 탐지를 실행. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/19--cli--clean.json) |
| 19--cli--sentinel_leak | 배포 허용 목록과 식별정보 검사 | pending | 미실행 | 실제 릴리스 ZIP 미제작. 허용 목록 정의만으로 clean 또는 5위치 sentinel 탐지 실험을 수행했다고 보지 않음. 이번에도 실제 패키지 시험 미실행, 최초 stale 표시 보존. | 허가된 릴리스 사본에서 clean 또는 5위치 시험 표식 탐지를 실행. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/19--cli--sentinel_leak.json) |
| 20--cli--default | 라이선스·출처·버전 고정 | blocked | 선행 조건 대기 | Canine89 개인 MIT 허락과 무료 AGPL 선택·소스/고지 준비 완료. 현재 허용 목록 101파일의 게이트: rights_unconfirmed 73, privacy_unconfirmed 73, dependency_license_unconfirmed 7. 정식 패키지 미생성. | 현재 해시별 권리·개인정보와 나머지 의존성 조건 검토를 완료. MIT/AGPL 선택을 다시 요청하지 않음. | [근거](../tmp/eval-integrated-20260913-v2/release-gate.json) |
| 21--claude--base_only | 신규 환경 설치와 선택 의존성 | blocked | 범위 제외 | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. | 현재 작업 범위에서 실행하지 않음. | [근거](../tmp/followup-20260913/evidence/relocation-observation.json) |
| 21--claude--kordoc_enabled | 신규 환경 설치와 선택 의존성 | blocked | 범위 제외 | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. | 현재 작업 범위에서 실행하지 않음. | [근거](../tmp/followup-20260913/evidence/relocation-observation.json) |
| 21--claude--no_hancom | 신규 환경 설치와 선택 의존성 | blocked | 범위 제외 | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. | 현재 작업 범위에서 실행하지 않음. | [근거](../tmp/followup-20260913/evidence/relocation-observation.json) |
| 21--claude--security_module_missing | 신규 환경 설치와 선택 의존성 | blocked | 범위 제외 | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. | 현재 작업 범위에서 실행하지 않음. | [근거](../tmp/followup-20260913/evidence/relocation-observation.json) |
| 21--codex--base_only | 신규 환경 설치와 선택 의존성 | blocked | 범위 제외 | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. | 현재 작업 범위에서 실행하지 않음. | [근거](../tmp/followup-20260913/evidence/relocation-observation.json) |
| 21--codex--kordoc_enabled | 신규 환경 설치와 선택 의존성 | blocked | 범위 제외 | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. | 현재 작업 범위에서 실행하지 않음. | [근거](../tmp/followup-20260913/evidence/relocation-observation.json) |
| 21--codex--no_hancom | 신규 환경 설치와 선택 의존성 | blocked | 범위 제외 | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. | 현재 작업 범위에서 실행하지 않음. | [근거](../tmp/followup-20260913/evidence/relocation-observation.json) |
| 21--codex--security_module_missing | 신규 환경 설치와 선택 의존성 | blocked | 범위 제외 | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. | 현재 작업 범위에서 실행하지 않음. | [근거](../tmp/followup-20260913/evidence/relocation-observation.json) |
| 22--claude--update | 설치 업데이트·제거의 자료 보존 | blocked | 선행 조건 대기 | 권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님. | 허가된 구·신 패키지로 실제 앱 업데이트/제거와 자료 보존 확인. | [근거](../tmp/followup-20260913/evidence/release-gate-final.json) |
| 22--claude--uninstall | 설치 업데이트·제거의 자료 보존 | blocked | 선행 조건 대기 | 권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님. | 허가된 구·신 패키지로 실제 앱 업데이트/제거와 자료 보존 확인. | [근거](../tmp/followup-20260913/evidence/release-gate-final.json) |
| 22--codex--update | 설치 업데이트·제거의 자료 보존 | blocked | 선행 조건 대기 | 권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님. | 허가된 구·신 패키지로 실제 앱 업데이트/제거와 자료 보존 확인. | [근거](../tmp/followup-20260913/evidence/release-gate-final.json) |
| 22--codex--uninstall | 설치 업데이트·제거의 자료 보존 | blocked | 선행 조건 대기 | 권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님. | 허가된 구·신 패키지로 실제 앱 업데이트/제거와 자료 보존 확인. | [근거](../tmp/followup-20260913/evidence/release-gate-final.json) |
| 23--claude--default | W1 일반 가정통신문 전체 과정 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 기존 일반 가통으로 앱 초안을 제시하고 문안 확인→전체 검증→전달 진행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 23--codex--default | W1 일반 가정통신문 전체 과정 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 기존 일반 가통으로 앱 초안을 제시하고 문안 확인→전체 검증→전달 진행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 24--claude--default | 참가 회신형 가통 전체 과정 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 기존 회신형으로 앱 초안을 제시하고 문안 확인→전체 검증→전달 진행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 24--codex--default | 참가 회신형 가통 전체 과정 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 기존 회신형으로 앱 초안을 제시하고 문안 확인→전체 검증→전달 진행. | [근거](../tmp/materials-followup-20260913/fixtures-local.json) |
| 25--claude--no_structure_approval | 활동 행 부족과 구조 변경 범위 | blocked | 동작 확인 | 두 앱에서 데이터 5행과 6개 활동을 대조, 모든 활동을 초안에 보존하고 1행 추가 승인 전 보류. | 해당 로컬 동작 확인 완료. 승인된 구조 변경/현재 판독은 다른 행에서 진행. | [근거](../tmp/materials-followup-20260913/evidence/claude-local-trial.json) |
| 25--claude--approved_structure | 활동 행 부족과 구조 변경 범위 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 구체적인 데이터 1행 추가 범위의 확인 후 구조·쪽수·렌더 검증. | [근거](../tmp/materials-followup-20260913/evidence/claude-local-trial.json) |
| 25--codex--no_structure_approval | 활동 행 부족과 구조 변경 범위 | blocked | 동작 확인 | 두 앱에서 데이터 5행과 6개 활동을 대조, 모든 활동을 초안에 보존하고 1행 추가 승인 전 보류. | 해당 로컬 동작 확인 완료. 승인된 구조 변경/현재 판독은 다른 행에서 진행. | [근거](../tmp/materials-followup-20260913/evidence/codex-local-finish.json) |
| 25--codex--approved_structure | 활동 행 부족과 구조 변경 범위 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 구체적인 데이터 1행 추가 범위의 확인 후 구조·쪽수·렌더 검증. | [근거](../tmp/materials-followup-20260913/evidence/codex-local-finish.json) |
| 26--claude--no_visual | 셀 글자 예산 초과와 판독 증거 | blocked | 동작 확인 | 두 앱이 같은 실제 셀에 161자 입력을 1회 실행. 현재 예산 24자 초과로 거절, 출력 없음. 판독/우회 승인 생성 없음. | 해당 로컬 동작 확인 완료. 승인된 구조 변경/현재 판독은 다른 행에서 진행. | [근거](../tmp/materials-followup-20260913/evidence/claude-local-trial.json) |
| 26--claude--stale_visual | 셀 글자 예산 초과와 판독 증거 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 오래된 판독 또는 현재 판독 조건을 각각 구성하고 최종 해시와 대조. | [근거](../tmp/materials-followup-20260913/evidence/claude-local-trial.json) |
| 26--claude--current_visual | 셀 글자 예산 초과와 판독 증거 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 오래된 판독 또는 현재 판독 조건을 각각 구성하고 최종 해시와 대조. | [근거](../tmp/materials-followup-20260913/evidence/claude-local-trial.json) |
| 26--codex--no_visual | 셀 글자 예산 초과와 판독 증거 | blocked | 동작 확인 | 두 앱이 같은 실제 셀에 161자 입력을 1회 실행. 현재 예산 24자 초과로 거절, 출력 없음. 판독/우회 승인 생성 없음. | 해당 로컬 동작 확인 완료. 승인된 구조 변경/현재 판독은 다른 행에서 진행. | [근거](../tmp/materials-followup-20260913/evidence/codex-local-finish.json) |
| 26--codex--stale_visual | 셀 글자 예산 초과와 판독 증거 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 오래된 판독 또는 현재 판독 조건을 각각 구성하고 최종 해시와 대조. | [근거](../tmp/materials-followup-20260913/evidence/codex-local-finish.json) |
| 26--codex--current_visual | 셀 글자 예산 초과와 판독 증거 | blocked | 자료 확보·후속 대기 | 기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소. | 오래된 판독 또는 현재 판독 조건을 각각 구성하고 최종 해시와 대조. | [근거](../tmp/materials-followup-20260913/evidence/codex-local-finish.json) |
| 27--claude--official_reply | W2 제출 방법 네 분기 | blocked | 자료 확보·후속 대기 | 가상 수신 원문과 검증된 W2 공통 경로 확보. 사용자 승인은 system 문안에 한정하며 이 제출 방식의 초안·확인·전체 흐름은 미실행. | 해당 제출 방식의 원문으로 초안을 제시하고 확인 후 생성·검증·시험 전달. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 27--claude--system | W2 제출 방법 네 분기 | blocked | 동작 확인 | Claude Code CLI: 사용자 승인된 가상 시스템 제출 내부결재 W2를 생성→전체 검증(COM·비교 렌더 포함)→시험 폴더 전달. 복사 해시 일치, sent=false. p:7 28/27자 경고 유지. 최종 사람 평점·실제 제출은 별도. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 27--claude--email | W2 제출 방법 네 분기 | blocked | 자료 확보·후속 대기 | 가상 수신 원문과 검증된 W2 공통 경로 확보. 사용자 승인은 system 문안에 한정하며 이 제출 방식의 초안·확인·전체 흐름은 미실행. | 해당 제출 방식의 원문으로 초안을 제시하고 확인 후 생성·검증·시험 전달. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 27--claude--unknown | W2 제출 방법 네 분기 | blocked | 동작 확인 | 실제 앱에서 제출 방법을 질문하고 변형 A/B·승인·발송을 임의 확정하지 않음. 실제 완성된 W2 문서 실적은 아님. Claude는 이미 제공한 가상 학교 값도 재확인했으며, 불필요한 질문이라는 사용성 관측을 보존함. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/claude-final-normal.json) |
| 27--codex--official_reply | W2 제출 방법 네 분기 | blocked | 자료 확보·후속 대기 | 가상 수신 원문과 검증된 W2 공통 경로 확보. 사용자 승인은 system 문안에 한정하며 이 제출 방식의 초안·확인·전체 흐름은 미실행. | 해당 제출 방식의 원문으로 초안을 제시하고 확인 후 생성·검증·시험 전달. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 27--codex--system | W2 제출 방법 네 분기 | blocked | 동작 확인 | Codex Desktop: 사용자 승인된 가상 시스템 제출 내부결재 W2를 생성→전체 검증(COM·비교 렌더 포함)→시험 폴더 전달. 복사 해시 일치, sent=false. p:7 28/27자 경고 유지. 최종 사람 평점·실제 제출은 별도. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 27--codex--email | W2 제출 방법 네 분기 | blocked | 자료 확보·후속 대기 | 가상 수신 원문과 검증된 W2 공통 경로 확보. 사용자 승인은 system 문안에 한정하며 이 제출 방식의 초안·확인·전체 흐름은 미실행. | 해당 제출 방식의 원문으로 초안을 제시하고 확인 후 생성·검증·시험 전달. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 27--codex--unknown | W2 제출 방법 네 분기 | blocked | 동작 확인 | 실제 앱에서 제출 방법을 질문하고 변형 A/B·승인·발송을 임의 확정하지 않음. 실제 완성된 W2 문서 실적은 아님. | 후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음. | [근거](../tmp/followup-20260913/evidence/codex-events-01a098b3-ef41-7713-8b40-6a4ae7071849.json) |
| 28--cli--date_weekday | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. DATE_WEEKDAY가 2026.10.16.(토)를 오류로 탐지. 단일 텍스트 추가에 따른 글자 예산 오류도 함께 나타나므로 단독 실패 격리 증거로 일반화하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--date_weekday.json) |
| 28--cli--old_residue | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. content_guard가 지정 forbid 토큰을 탐지. 주입 길이로 인한 예산 오류도 병존. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--old_residue.json) |
| 28--cli--invalid_budget | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--invalid_budget.json) |
| 28--cli--missing_related | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--missing_related.json) |
| 28--cli--attachment_mismatch | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--attachment_mismatch.json) |
| 28--cli--package_missing | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--package_missing.json) |
| 28--cli--com_unavailable | 내용·검증 실패와 성공 오보고 방지 | blocked | 부분 확인 | 독립 Codex CLI 기본 사용자 환경 COM·W1/W2 PDF 검사 통과. workspace-write 실제 제한 환경은 probe/Open/render가 HANCOM_RESTRICTED_CONTEXT로 1초 이내 실패·미확인 반환. 제한 모드 지원은 미완료. 렌더 도구 자체 부재와 build/validate/status/deliver 전체 전파는 별도. | 실제 불가 상태가 실행기 전체 보고·전달 금지까지 유지되는지 확인; 렌더 자체 부재는 COM 불가와 별도 시험. | [근거](../docs/Codex-CLI-COM-시간초과-수정-2026-09-13.md) |
| 28--cli--render_unavailable | 내용·검증 실패와 성공 오보고 방지 | blocked | 부분 확인 | 독립 Codex CLI 기본 사용자 환경 COM·W1/W2 PDF 검사 통과. workspace-write 실제 제한 환경은 probe/Open/render가 HANCOM_RESTRICTED_CONTEXT로 1초 이내 실패·미확인 반환. 제한 모드 지원은 미완료. 렌더 도구 자체 부재와 build/validate/status/deliver 전체 전파는 별도. | 실제 불가 상태가 실행기 전체 보고·전달 금지까지 유지되는지 확인; 렌더 자체 부재는 COM 불가와 별도 시험. | [근거](../docs/Codex-CLI-COM-시간초과-수정-2026-09-13.md) |
| 28--cli--stage_twice_failed | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. 구조 검사 failures=2 이후 실제 검사 호출이 추가되지 않고 한도 안내 유지. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--stage_twice_failed.json) |
| 28--cli--evidence_partial | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. fallback 미제공은 명시 거절. 이후 고정된 평가 원문을 제공한 CLI 후속 입력은 원문 조건/예외/최신판 미확인을 보존하고 전체 status unconfirmed/종료2. 실서비스 연결 시험은 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--evidence_partial.json) |
| 28--cli--evidence_connection_error | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. fallback 미제공은 명시 거절. 이후 고정된 평가 원문을 제공한 CLI 후속 입력은 원문 조건/예외/최신판 미확인을 보존하고 전체 status unconfirmed/종료2. 실서비스 연결 시험은 아님. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--evidence_connection_error.json) |
| 28--cli--exit0_internal_fail | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. 실제 old_residue 실패 보고서로 --draft 전달 시 exit0/status fail 조합 관측. 미확인 초안 이름·실패 상태·미발송 유지. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--exit0_internal_fail.json) |
| 28--cli--invalid_report_state | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--invalid_report_state.json) |
| 28--cli--approved_source_changed | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--approved_source_changed.json) |
| 28--cli--approved_attachment_changed | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--approved_attachment_changed.json) |
| 28--cli--approved_mapping_changed | 내용·검증 실패와 성공 오보고 방지 | pass | 과거 합격 | 정상 대조군에서 독립 lab 자극 후 원시 build/validate/status/deliver 응답과 보고서 확인. 안전한 미확인·실패를 문서/사람 검토 완료로 합산하지 않음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/28--cli--approved_mapping_changed.json) |
| 29--claude--copy_off | 검토본 전달·재시도·사람 확인 | blocked | 자료 확보·후속 대기 | 승인 W1/W2 작업과 실제 검증·전달 가능한 자료 확보. 복사 끄기 또는 미확인 초안 전달의 해당 분기는 아직 실행하지 않음. | 준비된 시험 작업 사본으로 해당 전달 분기를 실행하고 검증 상태·sent=false 보존 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 29--claude--copy_success | 검토본 전달·재시도·사람 확인 | blocked | 동작 확인 | Claude Code CLI에서 승인 W1/W2 검토본 2건을 시험 폴더로 전달하고 HWPX·보고서 복사 해시 일치 확인. 실제 OneDrive 전송이나 사람 최종 평점은 아님. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 29--claude--copy_partial | 검토본 전달·재시도·사람 확인 | blocked | 부분 확인 | 외부 복사 폴더 부재에서 로컬 검토본 보존, 폴더 복구 후 복사만 재시도 성공. 여러 전달 파일 중 일부만 복사된 중간 실패 조건을 따로 주입한 근거는 없음. | 일부 파일 복사 뒤 실패하는 조건을 구성해 복사만 재시도하고 기존 검증·파일 보존 확인. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 29--claude--copy_collision | 검토본 전달·재시도·사람 확인 | blocked | 동작 확인 | Claude Code CLI 실제 호출: 외부 기존 HWPX 충돌로 두 번 exit 1, 세 번째 exit 2. 기존 파일·작업 문서·manifest·검증 이력 보존. 과거 SYNTHETIC_TEST_NOT_USER 입력을 재사용한 전달 처리 시험이다. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 29--claude--copy_twice_failed | 검토본 전달·재시도·사람 확인 | blocked | 동작 확인 | Claude Code CLI 실제 호출: 외부 기존 HWPX 충돌로 두 번 exit 1, 세 번째 exit 2. 기존 파일·작업 문서·manifest·검증 이력 보존. 과거 SYNTHETIC_TEST_NOT_USER 입력을 재사용한 전달 처리 시험이다. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 29--claude--draft_only | 검토본 전달·재시도·사람 확인 | blocked | 자료 확보·후속 대기 | 승인 W1/W2 작업과 실제 검증·전달 가능한 자료 확보. 복사 끄기 또는 미확인 초안 전달의 해당 분기는 아직 실행하지 않음. | 준비된 시험 작업 사본으로 해당 전달 분기를 실행하고 검증 상태·sent=false 보존 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 29--claude--human_reject | 검토본 전달·재시도·사람 확인 | blocked | 선행 조건 대기 | 실제 교사가 검토본을 보고 거절한 응답 없음. CLI 합성 응답은 대체 불가. | 검토할 앱 산출물을 준비하고 해당 복사/검토 분기를 실행. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/29--claude--human_reject.json) |
| 29--codex--copy_off | 검토본 전달·재시도·사람 확인 | blocked | 자료 확보·후속 대기 | 승인 W1/W2 작업과 실제 검증·전달 가능한 자료 확보. 복사 끄기 또는 미확인 초안 전달의 해당 분기는 아직 실행하지 않음. | 준비된 시험 작업 사본으로 해당 전달 분기를 실행하고 검증 상태·sent=false 보존 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 29--codex--copy_success | 검토본 전달·재시도·사람 확인 | blocked | 동작 확인 | Codex Desktop에서 승인 W1/W2 검토본 2건을 시험 폴더로 전달하고 HWPX·보고서 복사 해시 일치 확인. 실제 OneDrive 전송이나 사람 최종 평점은 아님. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 29--codex--copy_partial | 검토본 전달·재시도·사람 확인 | blocked | 부분 확인 | 외부 복사 폴더 부재에서 로컬 검토본 보존, 폴더 복구 후 복사만 재시도 성공. 여러 전달 파일 중 일부만 복사된 중간 실패 조건을 따로 주입한 근거는 없음. | 일부 파일 복사 뒤 실패하는 조건을 구성해 복사만 재시도하고 기존 검증·파일 보존 확인. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 29--codex--copy_collision | 검토본 전달·재시도·사람 확인 | blocked | 동작 확인 | Codex Desktop 실제 호출: 외부 기존 HWPX 충돌로 두 번 exit 1, 세 번째 exit 2. 기존 파일·작업 문서·manifest·검증 이력 보존. 과거 SYNTHETIC_TEST_NOT_USER 입력을 재사용한 전달 처리 시험이다. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 29--codex--copy_twice_failed | 검토본 전달·재시도·사람 확인 | blocked | 동작 확인 | Codex Desktop 실제 호출: 외부 기존 HWPX 충돌로 두 번 exit 1, 세 번째 exit 2. 기존 파일·작업 문서·manifest·검증 이력 보존. 과거 SYNTHETIC_TEST_NOT_USER 입력을 재사용한 전달 처리 시험이다. | 현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 29--codex--draft_only | 검토본 전달·재시도·사람 확인 | blocked | 자료 확보·후속 대기 | 승인 W1/W2 작업과 실제 검증·전달 가능한 자료 확보. 복사 끄기 또는 미확인 초안 전달의 해당 분기는 아직 실행하지 않음. | 준비된 시험 작업 사본으로 해당 전달 분기를 실행하고 검증 상태·sent=false 보존 확인. | [근거](../docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md) |
| 29--codex--human_reject | 검토본 전달·재시도·사람 확인 | blocked | 선행 조건 대기 | 실제 교사가 검토본을 보고 거절한 응답 없음. CLI 합성 응답은 대체 불가. | 검토할 앱 산출물을 준비하고 해당 복사/검토 분기를 실행. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/29--codex--human_reject.json) |
| 30--teacher_selected--default | 동료 교사 PC의 첫 사용 | blocked | 범위 제외 | 동료 교사 PC 최초 사용은 사용자의 외부 PC 제외 대상. | 현재 작업 범위에서 실행하지 않음. | [근거](../docs/플러그인-보급-미충족분류-정정-2026-09-13.md) |
| 31--cli--timing | 성능 실측과 검증 캐시 정합 | pass | 과거 합격 | 후보 단계별 elapsed_seconds와 동일 출력/렌더 대조를 기록. v2 무관 자료 변경은 pass 유지, 최종 파일/validator 코드 변경은 unconfirmed로 전환. 임의 성능 합격선·속도 향상 주장 없음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/31--cli--timing.json) |
| 31--cli--unrelated_change | 성능 실측과 검증 캐시 정합 | pass | 과거 합격 | 후보 단계별 elapsed_seconds와 동일 출력/렌더 대조를 기록. v2 무관 자료 변경은 pass 유지, 최종 파일/validator 코드 변경은 unconfirmed로 전환. 임의 성능 합격선·속도 향상 주장 없음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/31--cli--unrelated_change.json) |
| 31--cli--artifact_change | 성능 실측과 검증 캐시 정합 | pass | 과거 합격 | 후보 단계별 elapsed_seconds와 동일 출력/렌더 대조를 기록. v2 무관 자료 변경은 pass 유지, 최종 파일/validator 코드 변경은 unconfirmed로 전환. 임의 성능 합격선·속도 향상 주장 없음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/31--cli--artifact_change.json) |
| 31--cli--validator_change | 성능 실측과 검증 캐시 정합 | pass | 과거 합격 | 후보 단계별 elapsed_seconds와 동일 출력/렌더 대조를 기록. v2 무관 자료 변경은 pass 유지, 최종 파일/validator 코드 변경은 unconfirmed로 전환. 임의 성능 합격선·속도 향상 주장 없음. | 최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음. | [근거](../.claude/scratchpad/plugin-distribution/run-01a097f3-20260913/records/31--cli--validator_change.json) |
| 32--claude--hwp_input | HWP 변환·재패키징·폴백 경로 | blocked | 부분 확인 | 후속 렌더 수정본: HWP→HWPX 7쪽 원본과 픽셀 동일, 원본 기인 ◯ 1개를 경고로 보존하며 PASS. 이전 FAIL 기록은 유지. 재패키징 사본도 비교 렌더 근거가 있으나 앱별 변환/재패키징/폴백 부재 전체 흐름은 미완료. | 해당 앱에서 지정한 입력·폴백 조건의 전체 흐름을 실행. 원본 기인 경고와 새 잔재 실패 구분 유지. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 32--claude--repackaged | HWP 변환·재패키징·폴백 경로 | blocked | 부분 확인 | 후속 렌더 수정본: HWP→HWPX 7쪽 원본과 픽셀 동일, 원본 기인 ◯ 1개를 경고로 보존하며 PASS. 이전 FAIL 기록은 유지. 재패키징 사본도 비교 렌더 근거가 있으나 앱별 변환/재패키징/폴백 부재 전체 흐름은 미완료. | 해당 앱에서 지정한 입력·폴백 조건의 전체 흐름을 실행. 원본 기인 경고와 새 잔재 실패 구분 유지. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 32--claude--fallback_absent | HWP 변환·재패키징·폴백 경로 | blocked | 자료 확보·후속 대기 | 후속 렌더 수정본: HWP→HWPX 7쪽 원본과 픽셀 동일, 원본 기인 ◯ 1개를 경고로 보존하며 PASS. 이전 FAIL 기록은 유지. 재패키징 사본도 비교 렌더 근거가 있으나 앱별 변환/재패키징/폴백 부재 전체 흐름은 미완료. | 해당 앱에서 지정한 입력·폴백 조건의 전체 흐름을 실행. 원본 기인 경고와 새 잔재 실패 구분 유지. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 32--codex--hwp_input | HWP 변환·재패키징·폴백 경로 | blocked | 부분 확인 | 후속 렌더 수정본: HWP→HWPX 7쪽 원본과 픽셀 동일, 원본 기인 ◯ 1개를 경고로 보존하며 PASS. 이전 FAIL 기록은 유지. 재패키징 사본도 비교 렌더 근거가 있으나 앱별 변환/재패키징/폴백 부재 전체 흐름은 미완료. | 해당 앱에서 지정한 입력·폴백 조건의 전체 흐름을 실행. 원본 기인 경고와 새 잔재 실패 구분 유지. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 32--codex--repackaged | HWP 변환·재패키징·폴백 경로 | blocked | 부분 확인 | 후속 렌더 수정본: HWP→HWPX 7쪽 원본과 픽셀 동일, 원본 기인 ◯ 1개를 경고로 보존하며 PASS. 이전 FAIL 기록은 유지. 재패키징 사본도 비교 렌더 근거가 있으나 앱별 변환/재패키징/폴백 부재 전체 흐름은 미완료. | 해당 앱에서 지정한 입력·폴백 조건의 전체 흐름을 실행. 원본 기인 경고와 새 잔재 실패 구분 유지. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |
| 32--codex--fallback_absent | HWP 변환·재패키징·폴백 경로 | blocked | 자료 확보·후속 대기 | 후속 렌더 수정본: HWP→HWPX 7쪽 원본과 픽셀 동일, 원본 기인 ◯ 1개를 경고로 보존하며 PASS. 이전 FAIL 기록은 유지. 재패키징 사본도 비교 렌더 근거가 있으나 앱별 변환/재패키징/폴백 부재 전체 흐름은 미완료. | 해당 앱에서 지정한 입력·폴백 조건의 전체 흐름을 실행. 원본 기인 경고와 새 잔재 실패 구분 유지. | [근거](../docs/플러그인-남은시험-실행결과-2026-09-13.md) |

## 기계 판독·검증

- [176행 JSON](../tmp/eval-integrated-20260913-v2/rows.json)
- [집계·원본 해시·환경 범위](../tmp/eval-integrated-20260913-v2/summary.json)
- [근거 색인](../tmp/eval-integrated-20260913-v2/evidence-index.json)
- [무결성 검증](../tmp/eval-integrated-20260913-v2/validation.json)

teacher_doc에서 평가표와 후속 집계를 최신화했다. 구현 코드·실무 원본·최초 평가 판정은 변경하지 않았다.
