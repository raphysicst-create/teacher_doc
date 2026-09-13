# 최초 차단 115행의 구현 후속 분류

기존 행과 최초 판정을 보존했다. 아래 결과는 구현자가 수집한 동작 근거이며 독립 평가 pass 승격이 아니다.

| ID | 현재 분류 | 관측 | 남은 조건/근거 |
|---|---|---|---|
| 08--cli--default | 해소 | behavior_verified | 사용자의 기존양식 5종 승인 기록과 현재 등록 해시 확인. 5종 목록/등록 버전 prepare 및 원본 보존 대조 완료. |
| 09--claude--default | 시험자료·격리환경 | blocked | 가상학교 native_notice 원본·의미 매핑·사람 판독 증거 미결합. |
| 09--codex--default | 시험자료·격리환경 | blocked | 가상학교 native_notice 원본·의미 매핑·사람 판독 증거 미결합. |
| 11--claude--internal_approval | 시험자료·격리환경 | blocked | native_gianmun 및 실제 승인본 8건의 출처·사용 허용·기준 대응표 미결합. |
| 11--claude--notice_dispatch | 시험자료·격리환경 | blocked | native_gianmun 및 실제 승인본 8건의 출처·사용 허용·기준 대응표 미결합. |
| 11--codex--internal_approval | 시험자료·격리환경 | blocked | native_gianmun 및 실제 승인본 8건의 출처·사용 허용·기준 대응표 미결합. |
| 11--codex--notice_dispatch | 시험자료·격리환경 | blocked | native_gianmun 및 실제 승인본 8건의 출처·사용 허용·기준 대응표 미결합. |
| 13--claude--default | 시험자료·격리환경 | partial | 앱의 새 시험 세션에서 로컬 지침/스킬 읽기 확인. 전역 메모리가 없는 정식 설치 패키지 조건을 충족한 독립 인수는 아님. |
| 13--codex--default | 시험자료·격리환경 | partial | 앱의 새 시험 세션에서 로컬 지침/스킬 읽기 확인. 전역 메모리가 없는 정식 설치 패키지 조건을 충족한 독립 인수는 아님. |
| 14--claude--precedent | 시험자료·격리환경 | blocked | policy_fixture는 있으나 native_notice 원본·판독 기록과 메모리 격리 미확보. |
| 14--claude--empty_cells | 시험자료·격리환경 | blocked | policy_fixture는 있으나 native_notice 원본·판독 기록과 메모리 격리 미확보. |
| 14--claude--grade_absent | 시험자료·격리환경 | blocked | policy_fixture는 있으나 native_notice 원본·판독 기록과 메모리 격리 미확보. |
| 14--claude--metadata | 시험자료·격리환경 | blocked | policy_fixture는 있으나 native_notice 원본·판독 기록과 메모리 격리 미확보. |
| 14--codex--precedent | 시험자료·격리환경 | blocked | policy_fixture는 있으나 native_notice 원본·판독 기록과 메모리 격리 미확보. |
| 14--codex--empty_cells | 시험자료·격리환경 | blocked | policy_fixture는 있으나 native_notice 원본·판독 기록과 메모리 격리 미확보. |
| 14--codex--grade_absent | 시험자료·격리환경 | blocked | policy_fixture는 있으나 native_notice 원본·판독 기록과 메모리 격리 미확보. |
| 14--codex--metadata | 시험자료·격리환경 | blocked | policy_fixture는 있으나 native_notice 원본·판독 기록과 메모리 격리 미확보. |
| 15--claude--edit | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--claude--delete | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--claude--move | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--claude--mixed | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. Claude Bash의 복합 명령으로 시험했으며 Codex의 원자적 apply_patch와 도구 형태는 다름. |
| 15--claude--powershell_write | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--claude--mcp_patch | 시험자료·격리환경 | blocked | 이전 Claude kordoc 연결 시간 초과. 이번 Claude 훅 시험은 MCP를 격리해 실행했으므로 해당 두 도구의 실호출 인수는 미완료. Codex MCP 결과로 대체하지 않음. |
| 15--claude--mcp_fill | 시험자료·격리환경 | blocked | 이전 Claude kordoc 연결 시간 초과. 이번 Claude 훅 시험은 MCP를 격리해 실행했으므로 해당 두 도구의 실호출 인수는 미완료. Codex MCP 결과로 대체하지 않음. |
| 15--claude--junction_escape | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--codex--edit | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--codex--delete | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--codex--move | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--codex--mixed | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--codex--powershell_write | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 15--codex--mcp_patch | 시험자료·격리환경 | partial | 현재 Codex Desktop 구현 세션에서 실제 kordoc patch_document/fill_form이 PreToolUse로 차단되고 원본 불변. 독립 설치 세션의 MCP 접두어/전체 설정 인수는 미완료. |
| 15--codex--mcp_fill | 시험자료·격리환경 | partial | 현재 Codex Desktop 구현 세션에서 실제 kordoc patch_document/fill_form이 PreToolUse로 차단되고 원본 불변. 독립 설치 세션의 MCP 접두어/전체 설정 인수는 미완료. |
| 15--codex--junction_escape | 해소 | behavior_verified | 실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인. |
| 16--claude--read | 해소 | behavior_verified | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. |
| 16--claude--copy_new | 해소 | behavior_verified | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. 앱 설명에서 정상 복사를 보호 공백으로 잘못 해석했으나 실제 동작은 명세대로 허용됨. 후속 시험 입력에서 허용 범위를 명확히 했고 보고에 이 한계를 보존함. |
| 16--claude--new_output | 해소 | behavior_verified | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. |
| 16--claude--outside_docs | 해소 | behavior_verified | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. |
| 16--claude--no_marker | 시험자료·격리환경 | blocked | 앱 cwd 자체가 무표시 폴더인 독립 훅 등록/신뢰 조건은 미실행. 표시된 workspace 내부 plain-project는 무표시 시험이 아니므로 성공·실패로 승격하지 않음. |
| 16--codex--read | 해소 | behavior_verified | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. |
| 16--codex--copy_new | 해소 | behavior_verified | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. |
| 16--codex--new_output | 해소 | behavior_verified | 실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨. |
| 16--codex--outside_docs | 시험자료·격리환경 | partial | 올바른 형제 fixture로 재실행했으나 Codex workspace-write 자체 경계에서 거절. hwpdoc 오차단으로 판정하지 않음. 폐기용 비공문 경로를 포함한 앱 샌드박스 인수 환경 필요. |
| 16--codex--no_marker | 시험자료·격리환경 | blocked | 앱 cwd 자체가 무표시 폴더인 독립 훅 등록/신뢰 조건은 미실행. 표시된 workspace 내부 plain-project는 무표시 시험이 아니므로 성공·실패로 승격하지 않음. |
| 17--claude--untrusted | 시험자료·격리환경 | partial | Codex의 정상 /hooks 검토·신뢰 후 실제 차단은 관측함. 미신뢰 상태의 실제 쓰기/진단까지 포함한 독립 variant는 수행하지 않음. 전역 보안/신뢰 우회는 사용하지 않음. |
| 17--claude--python_missing | 해소 | behavior_verified | 프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음. |
| 17--claude--hook_error | 해소 | behavior_verified | 프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음. |
| 17--claude--utf8_path | 해소 | behavior_verified | 실제 한글 경로 보호 이벤트 정상. 추가로 PowerShell의 한국어 오류 깨짐을 수정하고 두 앱 셸 회귀 + 실제 Claude 오류 출력 재확인. |
| 17--codex--untrusted | 시험자료·격리환경 | partial | Codex의 정상 /hooks 검토·신뢰 후 실제 차단은 관측함. 미신뢰 상태의 실제 쓰기/진단까지 포함한 독립 variant는 수행하지 않음. 전역 보안/신뢰 우회는 사용하지 않음. |
| 17--codex--python_missing | 해소 | behavior_verified | 프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음. |
| 17--codex--hook_error | 해소 | behavior_verified | 프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음. |
| 17--codex--utf8_path | 해소 | behavior_verified | 실제 한글 경로 보호 이벤트 정상. 추가로 PowerShell의 한국어 오류 깨짐을 수정하고 두 앱 셸 회귀 + 실제 Claude 오류 출력 재확인. |
| 18--claude--unchanged | 해소 | behavior_verified | 깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음. |
| 18--claude--invalid_output | 해소 | behavior_verified | 깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음. |
| 18--claude--twice_failed | 시험자료·격리환경 | partial | 2회 한도 단위시험 통과. 실제 앱은 파일 미변경 후 재검사를 생략했으므로 동일 단계가 2회 실패하는 별도 실앱 variant 완료로 보지 않음. |
| 18--codex--unchanged | 해소 | behavior_verified | 깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음. |
| 18--codex--invalid_output | 해소 | behavior_verified | 깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음. |
| 18--codex--twice_failed | 시험자료·격리환경 | partial | 2회 한도 단위시험 통과. 실제 앱은 파일 미변경 후 재검사를 생략했으므로 동일 단계가 2회 실패하는 별도 실앱 variant 완료로 보지 않음. |
| 20--cli--default | 라이선스 | blocked | 현재 해시에서 권리 70, 개인정보 70, 의존성 조건 8건 미확인. 배포 금지. |
| 21--claude--base_only | 이번 범위 제외 | excluded | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. |
| 21--claude--kordoc_enabled | 이번 범위 제외 | excluded | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. |
| 21--claude--no_hancom | 이번 범위 제외 | excluded | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. |
| 21--claude--security_module_missing | 이번 범위 제외 | excluded | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. |
| 21--codex--base_only | 이번 범위 제외 | excluded | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. |
| 21--codex--kordoc_enabled | 이번 범위 제외 | excluded | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. |
| 21--codex--no_hancom | 이번 범위 제외 | excluded | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. |
| 21--codex--security_module_missing | 이번 범위 제외 | excluded | 새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과. |
| 22--claude--update | 라이선스 | blocked | 권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님. |
| 22--claude--uninstall | 라이선스 | blocked | 권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님. |
| 22--codex--update | 라이선스 | blocked | 권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님. |
| 22--codex--uninstall | 라이선스 | blocked | 권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님. |
| 23--claude--default | 시험자료·격리환경 | blocked | school_alpha·가상 업무 근거는 있으나 native_notice 원본·판독·실제 초안/최종 응답 미확보. |
| 23--codex--default | 시험자료·격리환경 | blocked | school_alpha·가상 업무 근거는 있으나 native_notice 원본·판독·실제 초안/최종 응답 미확보. |
| 24--claude--default | 시험자료·격리환경 | blocked | 학교·가상 근거는 있으나 native_reply 5행/서명/명의 배치의 원본·판독 미확보. |
| 24--codex--default | 시험자료·격리환경 | blocked | 학교·가상 근거는 있으나 native_reply 5행/서명/명의 배치의 원본·판독 미확보. |
| 25--claude--no_structure_approval | 시험자료·격리환경 | blocked | capacity_six 원문은 있으나 5행 native_reply 원본과 구조 대조 미준비. |
| 25--claude--approved_structure | 시험자료·격리환경 | blocked | capacity_six 원문은 있으나 5행 native_reply 원본과 구조 대조 미준비. |
| 25--codex--no_structure_approval | 시험자료·격리환경 | blocked | capacity_six 원문은 있으나 5행 native_reply 원본과 구조 대조 미준비. |
| 25--codex--approved_structure | 시험자료·격리환경 | blocked | capacity_six 원문은 있으나 5행 native_reply 원본과 구조 대조 미준비. |
| 26--claude--no_visual | 시험자료·격리환경 | blocked | native_reply 및 실제 슬롯 예산을 넘는 long_text·렌더/해시 연결 자료 미준비. |
| 26--claude--stale_visual | 시험자료·격리환경 | blocked | native_reply 및 실제 슬롯 예산을 넘는 long_text·렌더/해시 연결 자료 미준비. |
| 26--claude--current_visual | 시험자료·격리환경 | blocked | native_reply 및 실제 슬롯 예산을 넘는 long_text·렌더/해시 연결 자료 미준비. |
| 26--codex--no_visual | 시험자료·격리환경 | blocked | native_reply 및 실제 슬롯 예산을 넘는 long_text·렌더/해시 연결 자료 미준비. |
| 26--codex--stale_visual | 시험자료·격리환경 | blocked | native_reply 및 실제 슬롯 예산을 넘는 long_text·렌더/해시 연결 자료 미준비. |
| 26--codex--current_visual | 시험자료·격리환경 | blocked | native_reply 및 실제 슬롯 예산을 넘는 long_text·렌더/해시 연결 자료 미준비. |
| 27--claude--official_reply | 사람 확인 | blocked | w2_sources·school_alpha·task_evidence 기본 자료는 있으나 실제 앱 초안과 그에 대한 사용자 확인 미확보. |
| 27--claude--system | 사람 확인 | blocked | w2_sources·school_alpha·task_evidence 기본 자료는 있으나 실제 앱 초안과 그에 대한 사용자 확인 미확보. |
| 27--claude--email | 사람 확인 | blocked | w2_sources·school_alpha·task_evidence 기본 자료는 있으나 실제 앱 초안과 그에 대한 사용자 확인 미확보. |
| 27--claude--unknown | 해소 | behavior_verified | 실제 앱에서 제출 방법을 질문하고 변형 A/B·승인·발송을 임의 확정하지 않음. 실제 완성된 W2 문서 실적은 아님. Claude는 이미 제공한 가상 학교 값도 재확인했으며, 불필요한 질문이라는 사용성 관측을 보존함. |
| 27--codex--official_reply | 사람 확인 | blocked | w2_sources·school_alpha·task_evidence 기본 자료는 있으나 실제 앱 초안과 그에 대한 사용자 확인 미확보. |
| 27--codex--system | 사람 확인 | blocked | w2_sources·school_alpha·task_evidence 기본 자료는 있으나 실제 앱 초안과 그에 대한 사용자 확인 미확보. |
| 27--codex--email | 사람 확인 | blocked | w2_sources·school_alpha·task_evidence 기본 자료는 있으나 실제 앱 초안과 그에 대한 사용자 확인 미확보. |
| 27--codex--unknown | 해소 | behavior_verified | 실제 앱에서 제출 방법을 질문하고 변형 A/B·승인·발송을 임의 확정하지 않음. 실제 완성된 W2 문서 실적은 아님. |
| 28--cli--com_unavailable | 시험자료·격리환경 | blocked | 현재 PC의 실제 COM·렌더는 작동함. 부재 상태는 운영 환경을 제거하지 않고 모의 오류 회귀로만 확인했으므로 실환경 부재 variant는 미검증. |
| 28--cli--render_unavailable | 시험자료·격리환경 | blocked | 현재 PC의 실제 COM·렌더는 작동함. 부재 상태는 운영 환경을 제거하지 않고 모의 오류 회귀로만 확인했으므로 실환경 부재 variant는 미검증. |
| 29--claude--copy_off | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--claude--copy_success | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--claude--copy_partial | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--claude--copy_collision | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--claude--copy_twice_failed | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--claude--draft_only | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--claude--human_reject | 사람 확인 | blocked | 실제 교사가 검토본을 보고 거절한 응답 없음. CLI 합성 응답은 대체 불가. |
| 29--codex--copy_off | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--codex--copy_success | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--codex--copy_partial | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--codex--copy_collision | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--codex--copy_twice_failed | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--codex--draft_only | 사람 확인 | blocked | delivery_seed 파일은 있으나 CLI 합성 승인·검증 기록을 실제 앱 승인 실적으로 전용할 수 없음. |
| 29--codex--human_reject | 사람 확인 | blocked | 실제 교사가 검토본을 보고 거절한 응답 없음. CLI 합성 응답은 대체 불가. |
| 30--teacher_selected--default | 사람 확인 | blocked | 실제 동료 교사·그 교사의 PC/양식/설치·검토 응답 미확보. |
| 32--claude--hwp_input | 시험자료·격리환경 | blocked | 사용 허용 .hwp 및 출처가 확인된 COM 변환/재패키징 비교 사본 미결합. |
| 32--claude--repackaged | 시험자료·격리환경 | blocked | 사용 허용 .hwp 및 출처가 확인된 COM 변환/재패키징 비교 사본 미결합. |
| 32--claude--fallback_absent | 시험자료·격리환경 | blocked | 사용 허용 .hwp 및 출처가 확인된 COM 변환/재패키징 비교 사본 미결합. |
| 32--codex--hwp_input | 시험자료·격리환경 | blocked | 사용 허용 .hwp 및 출처가 확인된 COM 변환/재패키징 비교 사본 미결합. |
| 32--codex--repackaged | 시험자료·격리환경 | blocked | 사용 허용 .hwp 및 출처가 확인된 COM 변환/재패키징 비교 사본 미결합. |
| 32--codex--fallback_absent | 시험자료·격리환경 | blocked | 사용 허용 .hwp 및 출처가 확인된 COM 변환/재패키징 비교 사본 미결합. |
