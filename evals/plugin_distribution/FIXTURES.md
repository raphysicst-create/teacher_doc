# 평가 자료 준비 계약

배포 패키지에는 실무 공문이나 학교 원본을 포함하지 않는다. 모든 준비·고장 주입·산출물은 평가 실행 폴더 아래 사본에서 한다. 이 문서는 준비 절차이며 자료가 이미 존재하거나 검증됐다는 뜻이 아니다.

## 결합 방식

run-dir/fixtures.json의 fixtures 객체에 아래 이름별 status=ready|pending|blocked, provenance(원문 출처/준비자/버전), files([{path,sha256}])를 채운다. path는 run-dir 기준 상대경로다. ready는 실제 파일과 확인 가능한 출처가 있어야 한다. 미확보 native/교사 환경/릴리스는 blocked 사유를 기록한다. 환경 fixture는 실제 환경 관측 JSON/문서 파일을 증거로 결합한다.

seal-fixtures는 manifest와 원문 파일을 고정하며, 변조 variant는 fixtures 원본이 아닌 lab 사본에 적용한다. 기준·후보 소스의 허용 파일 목록은 subject-files JSON에 별도로 둔다. 동결은 HEAD·diff·미추적 목록과 파일 해시를 함께 기록한다.

## 원문/환경 fixture 목록

| 이름 | 준비물과 필수 확인 |
|---|---|
| baseline_commit | 9f3baca의 코드 사본, git 식별/기준 시험 원시 출력. 기존 47건 중 보고된 오류는 통과로 바꾸지 않음 |
| legacy_five | 현재 5종 각각 양식.hwpx·slots·budget·structure·README를 허용된 읽기로 복사. 원본 5종 전후 해시와 분류. 각 생성 입력도 포함. 파일명은 일반가통→가정통신문, 회신형→가정통신문-회신형, 고사안내→가정통신문-고사안내, 성립전예산요구, 교과협의회→회의록-교과협의회 |
| native_notice | 가상학교의 한글 네이티브 일반 가통. 제목/일시/장소/대상/안내/날짜·명의 위치와 의미 매핑을 확인. 원본 Preview/header 포함 |
| native_reply | 가상학교 네이티브 회신형. 일정 데이터 5행, 참가·불참/보호자 서명, 맨 아래 날짜·명의. 원문자·셀/문단 구분을 실제 추출로 확인 |
| native_gianmun | 제목 굵기와 상단 여백이 확인된 공통 기안문 베이스, 수신/관련/붙임 슬롯. 이름이 예산양식이어도 여러 용도 테스트 가능 |
| lineage_eight | 메모리의 8건 실제 승인본 사본과 사용 허용·기준 양식·출처 대응표. 파일 없음이면 blocked. 가상 8건을 만들어 계보 입증으로 쓰지 않음 |
| workspace_empty | run-dir 아래 기존 표시가 없는 새 폴더 준비 기록. 기존지침 variant는 KEEP_EXISTING 파일 포함 |
| workspace_seed | init된 격리 workspace와 설정·fixture 원문. 코드/PC/workspace 위치 분리와 경로 길이 기록 |
| isolated_pc | run-dir/pc-data/runtime.json 사본. 실제 사용자 PC 설정 변경 없이 자식 프로세스에서 HWPDOC_PC_DATA 사용 |
| school_alpha / school_beta | fixtures/school_alpha.json, school_beta.json의 가상 값과 이를 후보의 문서화된 지원 원본 형식으로 변환한 파일·매핑/정답 대조표. 지원 어댑터가 없으면 pending이며 현재 학교 자료로 대체하지 않음 |
| job_seed | baseline/후보 각각 정상 생성·전체 검증을 확보한 작업 사본. manifest·모든 참조·승인/검증 해시·보고서·원문을 포함. CLI용 합성 승인은 분명히 표시. 실앱 사례에는 실제 응답 필요 |
| registration_seed | 정상 등록용 사본과 mapping/review/프로파일. 양성 대조군을 먼저 확보. 실제 앱 등록과 CLI 합성 확인을 구분 |
| prepare_seed | 준비 입력용 원문, 의미/슬롯 값. 초안 승인·업무 근거·시각 확인은 일부러 제공하지 않음 |
| policy_fixture | fixtures/policy.json과 선택 학교 설정으로의 명시적 매핑. 빈 셀·미응시 학년·메타데이터·선례 보존 원칙 |
| task_evidence | fixtures/task_evidence.json 및 evidence_source.md. 전부 가상 업무 조건임을 명시. 실제 법령·학교 원문을 확인했다고 주장하지 않음. 독립 partial/connection_error는 그 상태로 유지 |
| hook_lab | workspace/knowledge·docs의 폐기용 파일, output 새 파일, outsider/docs 및 junction 대상용 별도 폐기 폴더, 입력/출력/전후 해시. 운영 다른 프로젝트는 사용하지 않음 |
| installed_plugin | 실제 선택 앱의 격리 설치 패키지·매니페스트·스킬/도구 목록·본문 로딩 원증거. 목록만으로 ready 인수 주장 금지 |
| release_candidate | 실제 릴리스 후보 사본·파일 허용 목록·버전·해시. 현재 미제작이면 pending |
| release_pair | 실제 old/new 릴리스 후보와 격리 설치 환경, 작업자료 사본. 단순 폴더 복사/삭제를 앱 업데이트/제거로 가장하지 않음 |
| privacy_sentinel | 시험 표식 SCHOOL_SENTINEL_가람과 PII_SENTINEL_NOT_REAL. HWPX 본문·Preview·content.hpf·PNG 이미지·첨부에 각각 삽입한 테스트 사본과 삽입 위치. 실제 개인정보 사용 금지 |
| fresh_environment | 별도 PC 또는 새 사용자 계정의 실제 관측 증거. Windows·Python·한글·보안모듈/설치·도구 목록. 환경 미확보면 blocked이며 새 계정 자동 생성 금지 |
| native_teacher_form | 실제 교사가 제공한 사용 허용 양식의 평가용 사본과 실제 등록/검토 응답 |
| capacity_six | fixtures/activities.json의 6행 원문. native_reply에는 실제 데이터 5행이 있어야 함 |
| long_text | fixtures/long_text.txt를 실제 슬롯 예산과 비교해 초과 셀 선택. raw 길이·max_chars·의미/수치 목록. 예산보다 짧다면 의미를 유지한 시험 문장을 추가하고 고정 후 실행 |
| w2_sources | fixtures/w2_sources.json의 네 가상 수신 원문과 지원 Reader 형식 사본. 기관+번호+시행일·제출방법/기한 정답을 대응. 실제 수신으로 가장하지 않음 |
| fault_seed | 정상 job_seed + variant마다 오류 하나를 넣은 lab 사본, 자극 전후 목록. 모의 COM은 CLI 단위 동작에만 사용 가능하며 실제 환경 부재 시험과 구분 |
| delivery_seed | 정상 검증 작업/미확인 초안 각 사본과 시험 로컬·외부 복사 위치. 실제 계정 OneDrive는 사용하지 않음 |
| converted_fixture | 사용 허용 .hwp와 COM 저장 HWPX/재패키징 사본, 출처·변환 방법·쪽수·PDF/PNG 비교. 없는 바이너리를 가상 생성해 네이티브라고 하지 않음 |

## 자료 준비와 평가 분리

기존 실제 양식을 읽기·사본 준비에 사용할 수 있지만 사본의 학교 정보를 그대로 외부로 내보내지 않는다. 현재 계보 보존 검증에 필요한 원문은 로컬 격리 평가 안에서만 사용한다. 배포 익명화 기준과 운영 메타데이터 불변 기준을 혼동하지 않는다.

새 가상학교 HWPX를 준비하려면 한글에서 사람이 저장한 평가용 원본과 판독 기록을 먼저 확보한다. 이 설계 세션은 한글 문서를 생성하거나 네이티브 판독을 수행하지 않았다. baseline 5종 실물·계보·교사 첫 사용은 합성 JSON으로 대체할 수 없다.

지정 raw 원문 형식(xlsx/xls/frontmatter)이 후보에서 지원되는지 먼저 확인하고 파일 생성/수동 매핑을 준비 단계에 기록한다. 정답은 아래 가상 값 자체이며 현재 파서가 틀리면 정답을 바꾸지 않는다. unknown 단가·실제 행정 의무를 가상 근거에서 추론하지 않는다.
