# teacher_doc

학교 양식을 보존하면서 HWPX 문서의 내용을 바꾸고 검증하는 교사용 플러그인입니다. **처음에는 학교 자료 없이 연습 문서부터 만들어 볼 수 있습니다.**

## 가장 쉬운 시작

파일을 다룰 수 있는 Codex 대화에 다음을 붙여 넣으세요. 명령어를 직접 입력할 필요는 없습니다.

> https://github.com/raphysicst-create/teacher_doc
>
> 이 플러그인을 Python 포함 설치해줘. Python 3.12가 없으면 공식 Astral uv와 CPython 배포본을 teacher_doc 전용 폴더에 받아도 돼. 저장소 전체와 설치 안내를 읽고, 내 문서와 분리된 작업 폴더에서 기본 XML 점검과 첫 연습 문서 생성까지 해줘. 결과 파일과 미확인 항목도 알려줘.

에이전트가 기존 Python 3.12를 확인하고, 없으면 위 문장의 동의에 따라 teacher_doc 전용 Python을 준비합니다. 고정 의존성 설치, XML 환경 점검, 개인정보 없는 첫 연습 HWPX 생성까지 이어집니다. 전역 PATH·레지스트리·보안 정책은 바꾸지 않습니다. 한글 구매/설치는 포함되지 않습니다. [Python 공급원·검증·라이선스](docs/PYTHON-RUNTIME.md)를 확인할 수 있습니다.

- **처음 보는 분:** [따라 하기와 문제 해결](docs/BEGINNER.md)
- **설치를 진행하는 에이전트:** [AGENTS.md](AGENTS.md) → [설치 스킬](skills/teacher-doc-setup/SKILL.md)
- **검증과 재현:** [자동 시험·Windows 확인 절차](docs/VERIFICATION.md)
- **실제 학교 공문 작업:** [HWPX 스킬](skills/hwpx/SKILL.md) → [업무 절차](skills/hwpx/references/workflow.md)

설치 뒤 새 대화에서는 **“(실제 작업 폴더)에서 문서 작업 이어줘”**라고 요청하면 됩니다. 기존 설치 기록의 실행 환경을 복원하며, 결과는 HWPX와 실제 본문 발췌·주요 변경·남은 검사를 함께 받습니다.

## 무엇이 확인되나요?

- **설치·앱 인식:** 플러그인 파일 설치, 앱 목록 노출, 실제 스킬 로딩은 각각 확인해야 합니다
- **XML 모드:** Windows·macOS·Linux에서 Python 의존성, HWPX 구조와 슬롯 편집 경로를 점검합니다. 한글이 없어도 시작할 수 있습니다
- **전체 모드:** Windows의 설치된 한글과 COM 자동화 환경이 필요합니다. 실제 문서 열기와 필요한 PDF/PNG 검사를 별도로 진행합니다
- **연습 문서:** 합성 양식과 채워진 HWPX, 기계 검사 보고서를 작업 폴더의 `output/teacher-doc-practice/`에 만듭니다. 학교 양식 등록·사람 승인·최종 발송 검증을 대신하지 않습니다

XML 검사 성공만으로 한글에서의 실제 열림, 쪽수, 줄바꿈, 인쇄 모양이 확인되지는 않습니다. 실제 공문은 원본 보존, 초안 확인, 전체 검증, 사람 검토 절차를 거쳐야 합니다. 발송 전 한글로 열어 확인해주세요.

## 설치 경로에 관해

이 저장소는 `.codex-plugin/plugin.json`과 `.agents/plugins/marketplace.json`을 포함합니다. 마켓플레이스 이름은 `teacher-doc-local`, 플러그인 이름은 기존의 `teacher_doc`입니다. 저장소 루트 전체가 설치 단위이며 **`skills/hwpx`만 복사하면 안 됩니다.** 상위 `scripts`, 의존성 목록, 라이선스와 소스 파일도 필요합니다.

지원되는 Codex CLI에서는 에이전트가 다음 경로를 사용할 수 있습니다. 먼저 설치된 CLI의 도움말로 지원 여부를 확인합니다.

```sh
codex plugin marketplace add https://github.com/raphysicst-create/teacher_doc.git
codex plugin add teacher_doc@teacher-doc-local --json
codex plugin list --json
```

설치 응답의 실제 설치 경로에서 `skills/teacher-doc-setup/SKILL.md`를 읽고 런타임 설정을 이어갑니다. 플러그인 추가만으로 Python 환경이나 작업 폴더가 준비되지는 않습니다.

일반 대화에 링크를 붙여 설치를 부탁하는 것, CLI에 마켓플레이스 원본을 추가하는 것, 앱의 가져오기 화면에 링크를 넣는 것은 서로 다른 경로입니다. **모든 계정·앱 버전의 Plugins Directory 검색창이 GitHub 주소를 설치 입력으로 받는다고 보장하지 않습니다.** 앱의 실제 가져오기 기능과 조직 정책을 확인하고, 지원하지 않으면 전체 저장소를 지속 보관할 폴더에 받아 에이전트 안내로 진행합니다. 앱 자동 발견은 별도 확인합니다.

## 자주 막히는 곳

- **Python 3.12가 없음:** 위 “Python 포함 설치” 문장으로 전용 런타임까지 준비합니다. 단순 설치 요청이라면 다운로드 전에 한 번 동의를 구합니다. 거절하면 설치하지 않고 멈춥니다
- **한글이 없거나 macOS/Linux임:** 기본 XML 모드로 설치와 연습을 진행합니다. Windows COM·인쇄 모양 확인은 미확인으로 남습니다
- **플러그인은 보이는데 실행이 안 됨:** 실제 설치 경로의 설치 스킬과 `scripts/bootstrap.ps1` 또는 `scripts/bootstrap.sh`가 있는지 확인합니다. 스킬 폴더만 설치했다면 전체 패키지가 필요합니다
- **권한·네트워크·조직 정책에 막힘:** 오류 단계와 필요한 조치를 안내합니다. 보안 제한을 낮추거나 무시하지 않습니다
- **기존 작업 폴더가 있음:** 같은 폴더와 PC 데이터 경로로 재실행하여 기존 설정을 보존합니다. 새 학교 값으로 덮어쓰지 않습니다

더 자세한 안내는 [초보자 안내](docs/BEGINNER.md)에 있습니다. [distribution/README.md](distribution/README.md)는 과거 배포 준비·운영 검토 기록입니다. 공개 패키지에 없는 개발 전용 명령도 포함하므로 최초 설치 순서는 이 README와 설치 스킬을 따릅니다.

## 라이선스와 검증 범위

[LICENSE](LICENSE), [NOTICE.md](NOTICE.md), [SOURCE.md](SOURCE.md), `licenses/`, `sources/`를 함께 보존합니다. 설치가 성공해도 앱별 배포 인수, Windows 한글 COM, 실제 학교 양식의 육안 검토가 모두 끝났다는 뜻은 아닙니다. 결과 보고에는 실제 수행한 검사를 구분해 표시합니다.

설치 형식 참고: [OpenAI 공식 플러그인 패키징 안내](https://developers.openai.com/plugins/build/plugins). 안내 확인일: **2026-10-02**. 클라이언트 기능과 조직 정책은 사용 환경에서 다시 확인합니다.
