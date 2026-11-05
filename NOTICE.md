# teacher_doc 0.2.0 — 라이선스 및 출처

이 배포의 teacher_doc 결합 프로그램은 GNU Affero General Public License version 3 (AGPL-3.0-only)로 제공한다. 전문은 루트 `LICENSE`에 있다. 소프트웨어는 어떠한 보증도 없이 제공된다. 수정·재배포 시 적용되는 소스 제공, 라이선스·저작권·변경 고지 의무를 따른다. 원래 구성요소의 고지와 추가로 허용된 권리는 아래와 같이 보존한다.

## Canine89/hwpxskill

- 저작자: Canine89. 출처: https://github.com/Canine89/hwpxskill
- MIT 허락: 배포자가 저작자에게 직접 연락해 허락을 받았다고 2026. 9. 13. 확인했다. `licenses/Canine89-MIT.txt`는 이 허락에 따라 배포자가 붙인 표준 MIT 고지이며, 개인 허락 원문을 재현한 문서가 아니다.
- 배포의 `skills/hwpx/`는 이 프로젝트를 기반으로 한 운영 수정본이다. 비교에 사용한 상류 트리는 `cb5f25b6557b47b0339398d3b5d45a57bdcb4b28`이다. 현재 파일의 식별 해시는 `release-inventory.json`에 있다.
- 변경과 추가 사항은 `CHANGES.md`를 참고한다. MIT 부분의 고지는 AGPL 결합 배포에서도 유지한다.

## jkf87/hwpx-skill

- 저작자: jkf87 및 기여자 phdgil. 출처: https://github.com/jkf87/hwpx-skill
- 라이선스: MIT. 상류 README의 「라이선스」 절이 MIT를 밝힌다(대조 기준 커밋 `389dd7b`, 2026. 11. 5. 기준 main도 같다). 상류에는 상류 자체 코드에 대한 LICENSE 파일과 저작권 문구가 없다. `licenses/jkf87-hwpx-skill-MIT.txt`는 이 선언에 따라 배포자가 붙인 표준 MIT 고지이며, 상류 원문을 재현한 문서가 아니다. phdgil의 기여는 이 선언이 있는 저장소에 PR #1로 제출·병합됐다(기여 직전 커밋 `8b64fdf`에도 같은 선언이 있다).
- 이 코드는 위 Canine89/hwpxskill 상류 트리의 `cb5f25b` 커밋("Add HWPX finalization guards")을 거쳐 들어왔다. 그 커밋이 jkf87/hwpx-skill을 참고해 추가·수정한 `skills/hwpx/scripts/finalize_hwpx.py`·`fix_namespaces.py`·`gonmun_lint.py`와 `validate.py`의 레이아웃 경고(`--layout`) 부분에 상류의 같은 이름 스크립트에서 온 코드가 남아 있다. 상류에서 `fix_namespaces.py`·`gonmun_lint.py`는 jkf87이, `finalize_hwpx.py`와 `validate.py`의 레이아웃 경고 부분은 phdgil이 PR #1(커밋 `1d7b5b3`)로 작성했다. `finalize_hwpx.py`는 대부분이 상류 코드다.
- Canine89에게서 받은 MIT 허락은 jkf87·phdgil 저작 부분을 대신하지 않으므로 두 고지를 함께 둔다. 두 저장소의 비교 메모는 `skills/hwpx/references/jkf87-hwpx-skill-comparison.md`에 있다.

## PyMuPDF 1.28.0 / MuPDF 1.28.0

- PyMuPDF: https://github.com/pymupdf/PyMuPDF — Artifex Software, Inc. 및 원래 기여자.
- MuPDF: Copyright (c) 2006-2026 Artifex Software, Inc. 원래 고지는 `licenses/MuPDF-README.txt`에 있다.
- 이 배포는 무료 AGPL v3 경로를 사용한다. 별도 상용 계약을 전제로 하지 않는다.
- PyMuPDF 배포의 `COPYING`과 일부 소스 파일의 GPL-3.0-only 표기를 그대로 보존했다. 해당 파일 고지도 보존하기 위해 `licenses/GPL-3.0-only.txt`를 함께 제공한다. MuPDF 원본의 AGPL v3-or-later 표기도 원본 그대로 남긴다.
- 두 소스 압축본은 수정하지 않았다. MuPDF `thirdparty/`의 개별 저작권과 라이선스도 원본 소스 안에 포함돼 있다. 소스 위치와 검증법은 `SOURCE.md` 및 `SOURCE-BUNDLE.json`에 있다.

## 그 밖의 Python 의존성

| 구성요소 | 고정 버전 | 상류 라이선스 및 고지 위치 |
|---|---|---|
| lxml | 5.4.0 | BSD 및 포함 구성요소 고지: `licenses/dependencies/lxml/` |
| python-hwpx | 2.23.0 | Apache-2.0, NOTICE: `licenses/dependencies/python-hwpx/` |
| pypdf | 6.14.2 | BSD-3-Clause: `licenses/dependencies/pypdf/` |
| pywin32 | 312 | 구성요소별 고지: `licenses/dependencies/pywin32/` |
| openpyxl | 3.1.5 | MIT: `licenses/dependencies/openpyxl/` |
| et-xmlfile | 2.0.0 | MIT 및 Python 고지: `licenses/dependencies/et-xmlfile/` |
| python-calamine | 0.7.0 | MIT: `licenses/dependencies/python-calamine/` |

설치기는 고정 버전의 의존성을 PyPI에서 별도로 받는다. 이 패키지는 Python, 한글 프로그램, 보안모듈 또는 의존성 바이너리를 포함하지 않는다. 각 제품의 기존 권리는 해당 권리자에게 있다.

이전 시험 버전의 xlrd 고지는 기록으로 보존한다: “This product includes software developed by David Giffin <david@giffin.org>.” 배포자는 해당 버전을 소개하는 광고 자료에도 표시를 유지하기로 했다. 현재 후보는 xlrd를 import하거나 설치하지 않으며 XLS 읽기를 python-calamine으로 교체했다. 과거 고지의 보존을 xlrd와 AGPL의 결합 허락으로 해석하지 않는다. 기존 xlrd LICENSE는 `licenses/dependencies/xlrd/`에 남긴다.

## 선택적 앱 전용 Python 다운로드

Python이 없는 PC에서 사용자 동의 후 Astral uv와 python-build-standalone CPython 배포본을 공식 공급원에서 다운로드할 수 있다. 바이너리는 이 저장소에 포함하지 않으며 각 배포본의 MIT/Apache-2.0, PSF 및 포함 라이브러리 고지를 따른다. 버전·해시·출처·라이선스와 변경 없는 전역 설정 범위는 [docs/PYTHON-RUNTIME.md](docs/PYTHON-RUNTIME.md)를 참조한다.
