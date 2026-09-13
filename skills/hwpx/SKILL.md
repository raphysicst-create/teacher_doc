---
name: hwpx
description: "HWPX 문서 읽기·슬롯/셀 편집·양식 보존·구조 및 레이아웃 검증. 기존 양식은 슬롯 편집 우선. .hwp 바이너리 결과물 생성은 지원하지 않는다."
---

# HWPX — 슬롯 편집과 원본 양식 보존

개발 정본은 `<프로젝트>/.claude/skills/hwpx/SKILL.md`이고 배포본은 패키지의 `skills/hwpx/SKILL.md`다. 발견 경로가 링크이면 실제 대상을 확인한다.
공문 작업을 시작하면 [업무 절차](references/workflow.md)를 실제로 읽는다. 학교별 설정은 작업 폴더의 `.hwpdoc/workspace.json`에 있고, 기존 운영 프로젝트의 `CLAUDE.md`에 명시된 사용자 결정은 유지한다. W1·W2 별도 스킬은 사용하지 않는다.

## 경로 선택

1. 기존 슬롯 템플릿 또는 HWPX 양식의 내용 교체: **초안 작성 전에** 텍스트와 구조를 읽고 `hwpx_slots.py`로 편집할 슬롯을 확인한다. 원본 제목 서식·상자·표 순서/병합·명의 위치를 유지한 초안을 `edit_hwpx.py --slot-json`으로 새 파일에 채운다. Markdown 초안을 근거로 원본 본문을 지우고 재조립하지 않는다.
2. 특정 문단·셀 수정: 프로젝트의 Reader/패치 도구를 우선하며 연결 불가 시 추출된 슬롯·셀 주소로 `edit_hwpx.py`를 사용한다. 마크다운 표를 보고 행/열 번호를 추정하지 않는다.
3. 행·열·병합 등 구조 변경: 프로젝트 지침에 따라 변경 전후와 구체적인 사용자 요청·승인 범위를 확인한 뒤 기존 재생성 경로로 처리한다. 문안 생성 승인만으로 구조 변경을 승인된 것으로 기록하지 않는다. 필요한 경우에만 [XML 작성 참고](references/xml-authoring.md)를 읽는다. 자동 슬롯 실행기에 맡기지 않는다.
4. 양식 없는 신규 문서: [XML 작성 참고](references/xml-authoring.md)의 `build_hwpx.py` 경로를 사용한다. 상세 요소는 [HWPX 형식](references/hwpx-format.md)을 필요한 부분만 읽는다.
5. `.hwp` 원본 읽기·변환과 `hwpx-fallback` 진입 조건은 프로젝트 지침을 따른다. `.hwp` 결과물을 생성하거나 원본을 덮어쓰지 않는다. 폴백 비교가 필요한 경우에만 [기능 비교](references/jkf87-hwpx-skill-comparison.md)를 읽는다.

## 기본 편집

설치 폴더와 교사의 작업 폴더를 구분한다. 개발 저장소에서는 `.claude/skills/hwpx/`, 배포본에서는 `skills/hwpx/`가 스킬 폴더다. 실제 로드한 스킬 폴더에서 위로 탐색하여 `scripts/runtime.ps1`이 있는 코드 루트를 확인한다. 작업 파일은 작업 폴더에만 저장한다. Python은 코드 루트의 `scripts/runtime.ps1`이 PC 설정과 설치 위치에서 찾는다. PATH의 임의 python으로 대체하지 않는다.

```powershell
# taskPlugin은 이 스킬이 속한 코드 루트, taskWorkspace는 교사의 작업 폴더다.
. "$taskPlugin/scripts/runtime.ps1"
$taskPython = Get-HwpdocPython
# taskSkill은 실제 로드한 SKILL.md의 상위 폴더다.
& $taskPython -X utf8 "$taskSkill/scripts/hwpx_slots.py" reference.hwpx -o slots.json
& $taskPython -X utf8 "$taskSkill/scripts/edit_hwpx.py" reference.hwpx -o result.hwpx --slot-json values.json
```

`values.json`은 추출된 슬롯 키(`p:12`, `cell:0:2:1`)와 새 문자열의 매핑이다. 기존 슬롯 프로파일은 현재 양식에서 추출한 주소와 해시를 확인한다. 작업 파일은 프로젝트 안의 작업용 디렉터리에만 둔다.

- 표·그림·텍스트상자를 감싼 컨테이너 문단을 직접 편집하지 않는다. 추출기는 이 문단을 제외한다.
- 원본의 주 런 서체·강조를 보존한다. 표 셀·본문을 다시 쪼개거나 띄어쓰기를 제거해 길이에 맞추지 않는다.
- `hp:t`의 `hp:fwSpace`, `hp:lineBreak` 등 자식 컨트롤은 보존한다. 본문 변경 시 줄 배치 캐시(`hp:linesegarray`)를 제거한다.
- `edit_hwpx.py`의 원시 ZIP 복사 방식을 유지한다. 변경하지 않은 엔트리·Preview·BinData·header·메타데이터를 일반 ZIP 재압축으로 바꾸지 않는다.
- 서체·런·빈 셀·예산·fingerprint 문제를 해결할 때만 [편집 세부](references/editing-details.md)를 읽는다.

## 구조·레이아웃

문단 순서, 표의 행·열·병합·셀 폭/높이·여백, 페이지/섹션, 스타일 ID 참조를 보존한다. 사용자 요청 없는 문단/표 추가·삭제·분할·병합을 하지 않는다. 레퍼런스 쪽수를 유지하며 쪽수 증가가 필요하면 프로젝트의 승인된 구조 변경 절차를 따른다.

**행 부족과 긴 문구를 구분한다.** 서로 다른 활동에 필요한 행이 부족하면 위치·필요 행 수를 보고하고 구조 변경 경로로 간다. 행은 충분하고 문구만 길면 대상·행동·조건·수치/비율을 보존해 먼저 간결하게 다듬고 [편집 세부](references/editing-details.md)의 예산·렌더 절차로 확인한다. 의미 보존이 불확실하거나 여전히 수용되지 않을 때 원문/축약안·위치·예산·실제 렌더 상태를 제시해 판단을 요청한다. 활동 누락·행 병합·글자 크기 임의 축소로 해결하지 않는다.

`--allow-over-budget`은 셀 폭을 넓히지 않는다. `--verified-by-render`는 미검증 사본을 실제 PDF→PNG로 판독한 **뒤에만** 붙인다. 최종 파일이 판독한 사본과 같은 해시인지 확인하고, 다르면 최종 파일을 다시 렌더한다. 원본과 나란히 제목 강조·상자·표 구성·줄바꿈/여백·명의 위치를 확인하며, 1쪽·잘림 없음만으로 양식 보존을 판정하지 않는다. 초과 WARNING은 보고에 남기고 자동 실행기는 이 플래그를 주입하지 않는다.

## 검증 도구

전체 순서와 조건은 [업무 절차](references/workflow.md)의 검증 절과 기존 운영 프로젝트 지침을 따른다. 순서는 구조 검사 → 네임스페이스 보정 → finalize → layout → page_guard → COM·조건부 렌더 → 내용·공문 규칙 → 신구대조다. 실행기의 build/validate/deliver/status를 우선 사용한다.

- `validate.py`: ZIP/11개 최소 패키지/XML 검사. 스키마 통과가 한글 실열림을 뜻하지 않는다.
- `fix_namespaces.py`: 프리픽스·header itemCnt 보정.
- `finalize_hwpx.py --strip-linesegarray --layout`: 캐시 제거와 밀도 경고. `--hancom`: 실제 COM 열기 검사.
- `page_guard.py --budget-profile ... --structure-profile ...`: 텍스트 예산과 전체 패키지 구조 비교. 프로파일은 **finalize 완료 후 사본**에서 만든다. 승인되지 않은 출력으로 기준을 재설정하지 않는다.
- `content_guard.py`: placeholder/원문 잔재/필수 값 검사. `gonmun_lint.py`: 날짜·요일 등 공문 규칙 검사. 주력 사본을 사용한다.
- 프로젝트 `scripts/render_check.py`: COM 쪽수·PDF 텍스트 순서/역순·개체 잔재 검사. 예산 초과 셀의 육안 판독은 별도다.
- `text_extract.py --format markdown`: Reader 연결 불가 시 텍스트 추출. 원본이 있으면 신구대조를 남긴다.

실패를 고치거나 방어선의 근거가 필요하면 운영 프로젝트에 보관된 실패 이력을 확인한다. 실패/미실행을 통과로 바꾸지 않는다. 재시도 한도와 폴백 재생성 후 검증은 업무 절차와 프로젝트 지침을 따른다.

## XML 작업 시 최소 불변 조건

첫 문단 첫 run의 `secPr`·`colPr`, 첫 ZIP 엔트리의 `mimetype`/ZIP_STORED, 표준 네임스페이스, header itemCnt, charPr/paraPr 참조 정합을 지킨다. 빈 텍스트는 `<hp:t/>`를 쓴다. `unpack --pretty` 결과는 검사 전용이며 pack 입력으로 사용하지 않는다.

`.claude/skills/hwpx/examples/*`는 읽기·복사에 사용하지 않는다. 프로젝트 `knowledge/examples/`는 프로젝트 지침에 따라 사용한다.
