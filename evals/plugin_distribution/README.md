# 플러그인 보급 전체 과정 독립 평가

개선 계획의 7단계를 **32개 상위 사례, 176개 개별 평가 행**으로 분해했다. 앱·양식·실패 variant마다 입력과 증거, 판정을 따로 남긴다. 평가자는 설계 세션과 구현 세션 모두와 달라야 한다.

**현재는 평가 패키지 작성 단계다. 제품 평가나 실제 앱·교사 인수를 수행한 결과가 아니다.** 구현 세션은 이후 사용자의 별도 “구현 시작해” 지시로 제품 구현을 재개했다고 확인했다. 이 evals 합의 자체가 재개 승인은 아니다. 평가 전 실제 후보를 새로 확인하고 동결한다.

- [START.md](START.md): 다른 평가 세션에 전달할 시작 지시
- [OPERATOR.md](OPERATOR.md): 순서·판정·후속 사람 입력·고장 주입 안내
- [FIXTURES.md](FIXTURES.md): 독립 시험 자료 준비와 원본 보호
- [CONTRACT.md](CONTRACT.md): 구현 세션이 확인한 미검증 CLI·상태 계약
- [AGREEMENT.md](AGREEMENT.md): 구현 세션과 합의 및 현재 미완료 범위
- [suite.json](suite.json): 사례/variant/앱 전수 목록
- [rubric.json](rubric.json): 공통·개별 판정 기준
- cases/: 평가 대상에게 전달하는 개별 입력
- rubrics/: 최초 결과 고정 뒤 사용하는 개별 판정 안내
- evaluate.py / test_evaluate.py: 증거 장부·집계와 집계기 자체 회귀시험
- [SELFTEST.md](SELFTEST.md): 평가 도구 자체시험 30개 통과 기록; 제품 평가와 구분

## 평가 범위

| 단계 | 상위 사례 | 핵심 |
|---|---|---|
| 1 | 01–02 | 5종 반복 생성·서식, 기준 변경·배포 전 검수 |
| 2 | 03–07 | init, 경로·이동, Python·복사, 학교 자료, 구형 작업 기록 |
| 3 | 08–12 | 5종 이관, 등록·변조, 복수 용도/계보, prepare |
| 4 | 13–14 | 실제 스킬 본문·업무 절차 로딩, 메모리 없는 정책 적용 |
| 5 | 15–18 | 실제 앱 훅 차단/정상 허용, PowerShell/MCP, 오류/신뢰, Stop |
| 6 | 19–22 | 배포 파일·식별정보, 라이선스·버전, 의존성, 업데이트/제거 |
| 7 | 23–32 | W1/W2, 구조·예산, 실패/오보고, 전달·교사 검토, 새 PC, 캐시, 변환 |

case 01의 5종 생성·필수 검증·서식 증거와 case 08의 이관 증거를 재사용해 연결할 수 있지만, 하나의 pass로 다른 양식의 미실행 행을 채우지 않는다. W2 제출방법 4분기와 근거 partial/connection_error는 독립 행이다.

## 빠른 시작

평가자는 먼저 START.md와 OPERATOR.md를 읽고 평가 대상의 버전을 동결한다. 아래 ID와 경로는 실제 평가 환경으로 바꾼다.

```powershell
$taskPython = 'C:\Users\22\AppData\Local\Programs\Python\Python312\python.exe'
& $taskPython -X utf8 evals/plugin_distribution/evaluate.py check
& $taskPython -X utf8 evals/plugin_distribution/evaluate.py init --run-dir .claude/scratchpad/plugin-distribution/run-001 --subject-root . --subject-files evals/plugin_distribution/subject-files.example.json --evaluator-thread 실제평가세션ID
# fixtures.json 결합과 원문 사본 준비 후 한 번만 동결
& $taskPython -X utf8 evals/plugin_distribution/evaluate.py seal-fixtures --run-dir .claude/scratchpad/plugin-distribution/run-001
& $taskPython -X utf8 evals/plugin_distribution/evaluate.py score --run-dir .claude/scratchpad/plugin-distribution/run-001
```

Python 경로는 이 운영 PC의 실행 예다. 새 평가 PC에서는 doctor로 확인한 인터프리터를 사용한다. subject-files.example.json은 **현재 소스 평가 예시**이며, 실제 배포 후보의 파일 목록도 반드시 추가한다. 예시 목록만 동결하고 패키지 전체를 검증했다고 주장하지 않는다.

집계 명령은 제품·COM·앱을 실행하지 않으며 결과 JSON을 stdout에 출력한다. score 종료코드 0은 모든 필수 평가 행 충족, 2는 미충족/미확인, 1은 장부 읽기 오류다. check/init/seal/evidence의 0은 평가 도구 동작 성공일 뿐 제품 통과가 아니다.

## 판정과 완료

pass=필수 관측·증거 충족, fail=명세 위반 관측, pending=미실행·미구현, blocked=환경·fixture·사람 입력 등 필요조건 부재. 현재 범위에 모든 행이 필수이므로 N/A로 삭제하지 않는다. 사례 안에서 외부 복사 선택 해제 등의 **제품 not_applicable**은 올바른 행동으로 평가할 수 있다.

안전한 실패 보고가 음성 사례 pass여도 검증 완료 HWPX는 아니다. document/delivery/human_review를 분리하고 합성 승인은 사람 확인으로 세지 않는다. 결과 숫자는 독립 평가 행 수이며 고유 문서 수가 아니다. 모든 행의 pass와 동결된 증거가 있어야 release_ready가 된다. 집계기는 원시 증거와 평가자 확인의 진위·법적 해석·시각 품질을 자동 보증하지 않는다.

기존 workflow_5와 36회 인수 장부, 실무 review_log에는 이 패키지 결과를 합산하지 않는다. 결과·민감 자료·배포 후보는 .claude/scratchpad/plugin-distribution/의 격리 실행 폴더에만 둔다.
