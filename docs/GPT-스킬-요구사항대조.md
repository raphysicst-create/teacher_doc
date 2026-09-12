# 스킬 정리 요구사항 대조

변경 전 파일은 작업 시작 시 `.claude/scratchpad/gpt-migration/before/`에 바이트 그대로 보관했다. git의 기존 미완료 변경과 원본 자료를 보존했다. 이 표는 요구사항 이관 검사이며 동일 모델 비교시험 결과가 아니다.

| 기존 요구 | 정리 후 정본 |
|---|---|
| W1 §1 유사 공문 탐색·슬롯 5종·README 매핑·회신형 가통 선택 | CLAUDE.md W1 1항 |
| W1 §2 시간표·모든 예산명·관련번호 기계 조회, 미제공 값 질문/placeholder | CLAUDE.md 기계화 도구·W1 2항·실패 처리 |
| W1 §3 초안 확인 이후 생성·공유값 단일 소스 | CLAUDE.md W1 2~3항·실행기 입력 계약 |
| W1 §4 기안문 굴림 12pt·첨부 양식 서체·직책+인원수 | CLAUDE.md 공문서 작성 규정 |
| W1 §5 Validator 1~9·Python312·예산 초과 렌더 | CLAUDE.md Validator·실패 처리, hwpx 편집 방법, 실행기 |
| W1 §6 output+OneDrive | CLAUDE.md 절대 금지 2항·W1 5항, deliver |
| W1 §7 파일·검사·판단 지점·한글 안내 | CLAUDE.md 응답 스타일·Validator 9항, 검토보고서 |
| W1 §8 W1 검토 로그·최종본 MD 환류 | CLAUDE.md W1 6항·검토 환류 |
| W2 §1 수신 원문 파싱·요지·요청·기한·제출방법·개인정보·kordoc 불가 대체 | CLAUDE.md W2 1항·금지 규칙·실패 처리 |
| W2 §2 공문회신 A / 시스템·메일 B | CLAUDE.md W2 2항 |
| W2 §3 원문 번호·시행일 조회, 없으면 질문 | CLAUDE.md W2 3항·Validator 관련번호 대조 |
| W2 §4 공통 초안~환류·W2 기록·기한 보고 | CLAUDE.md W2 4항 |
| 초안 전 업무지침 조건·예외·원문 검토 | 기존 미완료 변경의 CLAUDE.md 업무 지침 근거 조회 절 보존 |
| XML-first vs 슬롯 우선 충돌 | hwpx 진입점을 슬롯 우선으로 통일, XML 재작성은 조건부 references/xml-authoring.md |
| 상세 런·예산·구조 처리 | hwpx/references/editing-details.md |
| 실패 이력 | hwpx/references/failure-history.md; CLAUDE.md 근거 링크 변경 |
| 사용자 확정 운영 예외(메타데이터·빈 셀·행/열 삭제 등) | CLAUDE.md 기존 사용자 결정 |
| 부모의 w1/w2 필수 로딩 안내 | 부모 파일 보존, 해당 프로젝트 CLAUDE.md의 명시적 우선 지침으로 대체 |

별도 w1/w2 SKILL.md는 제거했다. W1/W2 업무명과 검토 로그 값은 그대로 유지한다. fallback 정본과 기존 편집·검증 CLI는 변경하지 않았다.

## 분리 검증과 되돌리기

1. 스킬 정리: CLAUDE.md, hwpx SKILL.md·README·references 3개, w1/w2 제거. 스킬 정리만의 동일 입력·모델·도구 비교는 미검증이다.
2. 실행기: scripts/hwpdoc*와 tests. 실행기 테스트·실제 양식 COM smoke를 스킬 효과로 해석하지 않는다.
3. GPT 연결: .codex/config.toml·hooks.json, .agents/skills/hwpx 링크, setup-gpt/gpt_environment, 기존 훅 어댑터. 신뢰·실제 차단·Work 로딩은 별도 증거가 필요하다.

되돌릴 때는 `git checkout .`를 사용하지 않는다. 작업 시작 시 보관한 before와 현재 diff를 비교해 해당 단계의 변경만 되돌린다. 특히 CLAUDE.md와 .codex/config.toml에는 작업 전부터 사용자 변경이 있었다. 새 실행기는 기존 CLI를 대체하거나 지우지 않으므로 기존 명령으로 문서를 처리할 수 있다.
