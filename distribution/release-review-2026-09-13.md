# 배포 파일·의존성 검토 — 2026. 9. 13.

teacher_doc 0.1.0 배포 허용 목록 **101개 파일의 권리·개인정보 검토를 완료**했다. 의존성은 **8종 중 7종의 현재 범위 조건을 확인**, **xlrd 2.0.2 한 종은 AGPL 결합 조건 미해결로 차단**한다. 이 기록은 배포 검토 결과이며 전체 앱 인수 또는 공개 릴리스 승인이 아니다. 패키지를 생성하거나 게시하지 않았다.

## 권리와 출처

- Canine89/hwpxskill: 사용자가 저작자에게 받은 개인 MIT 허락을 [기존 확인 기록](canine89-mit-permission-2026-09-13.json)으로 적용했다. 허락 원문·수신 날짜·대상 버전을 새로 만들어 기록하지 않았다.
- 스킬·템플릿은 기존 Git 이력과 상류 고정 트리 `cb5f25b6557b47b0339398d3b5d45a57bdcb4b28`의 경로·Git blob을 대조했다. 수정된 파일은 같은 파일이라고 주장하지 않고 원출처와 로컬 변경을 구분했다. 상류와 동일한 파일도 실제 배포 바이트의 SHA256을 별도로 기록했다.
- 프로젝트 자체 실행기·훅·업무 도구·배포 안내는 저장소의 추가 이력과 현재 내용을 확인했다. 사용자가 선택하고 준비를 지시한 무료 AGPL 경로 및 기존 `legal/NOTICE.md`에 따라 AGPL-3.0-only를 적용했다. 새로운 라이선스 예외나 제3자의 허락을 만들지 않았다.
- `editing-details.md`·`xml-authoring.md`는 기존 스킬 지침을 재구성한 프로젝트 수정본으로, 상류 MIT 고지를 함께 유지한다. 익명화 XML 사본은 [준비 기록](assets/preparation.json)의 원본·후보 해시와 연결한다.
- 루트 LICENSE, MIT 및 구성요소별 원래 고지, 변경 고지, 대응 소스·설치 설명을 유지했다. 소스 압축본 2개는 기존 고정 해시와 일치하고 수정하지 않았다. NOTICE에 xlrd가 요구하는 저작자 표시도 명시했다.

## 개인정보·자산 확인

[파일별 검토 목록](review-2026-09-13/files.json)에 101개 파일의 출처·해시·확인 범위를 남겼다. 아래는 자동 검사 결과를 실제 자산 내용과 대조한 범위다.

- 학교 이름·사용자 절대경로·OneDrive 계정 경로, 휴대전화·주민번호 형태, 비밀키·토큰 형태를 검사했다. 로컬 운영 식별정보에 해당하는 탐지는 없었다. 이 정규식 검사가 모든 형태의 개인정보 부재를 자동 보증한다고 해석하지 않는다.
- XML 14개·RDF 1개·HPF 1개의 텍스트 노드와 속성을 파싱해 확인했다. 문서 내용은 빈 값·슬롯·일반 양식 라벨이며 제안서 과거 사업 문구는 후보 사본에서 placeholder로 대체돼 있다. content.hpf의 작성자·날짜 값은 비어 있고 언어 `ko`만 남는다.
- header의 한글 값은 서체 이름과 스타일 이름이다. 서체 파일이나 한글 실행 파일·보안모듈은 포함하지 않는다.
- PrvText.txt는 비어 있다. PrvImage.png는 전체 이미지를 직접 열어 빈 흰 페이지임을 확인했다. PNG에는 IHDR/sRGB/gAMA/pHYs/IDAT/IEND만 있고 텍스트·EXIF 청크는 없다. 눈에 보이는 내용과 메타데이터를 각각 확인했다.
- 최초 고지 4개 파일과 이번에 저작자 표시를 보완한 NOTICE에서 발견한 이메일은 상류 저작권자 표시 또는 공개 제품 문의 주소다. 운영 교사·학생 정보가 아니며 고지 보존을 위해 유지한다.
- 운영 knowledge/output/logs/config, 평가 자료, 승인된 학교 5종 양식은 배포 허용 목록에 없다. 두 대형 소스 압축본은 공개 상류 원본과 동일한 해시이며 로컬 자료를 추가하지 않았다. 소스 내부의 모든 이미지·시험 문서를 새로 육안 판독한 것은 아니다.

## 의존성별 적용 조건

Python 3.12에 설치된 고정 버전의 원래 라이선스·NOTICE 사본을 다시 대조했다. 현재 패키지는 의존성 wheel·DLL·EXE를 포함하지 않으며 설치기는 PyPI의 고정 버전을 받는다. 별도 다운로드라는 이유만으로 프로그램의 결합 조건을 면제하지 않는다. 기본 전이 의존성은 python-hwpx→lxml, openpyxl→et-xmlfile이며 둘 다 현재 목록에 있다. extra 패키지와 Python 3.11 미만 조건의 typing_extensions는 이 Python 3.12 설치 범위에 없다.

| 의존성 | 현재 범위 확인 | 결과 |
|---|---|---|
| lxml 5.4.0 | etree 사용, BSD 고지와 예외 목록 보존. isoschematron의 라이선스 미지정 변환 자산은 포함·호출하지 않는다. 전체 lxml 소스/wheel의 재배포 허가로 확대하지 않는다. | 조건 확인 |
| python-hwpx 2.23.0 | Apache-2.0 LICENSE·NOTICE·원저작자/비공식 구현 표시 보존. 의존성 소스를 수정하거나 패키지에 복제하지 않는다. | 조건 확인 |
| pypdf 6.14.2 | BSD-3-Clause 저작권·조건·면책 보존. 저작자의 추천·보증으로 표시하지 않는다. | 조건 확인 |
| pywin32 312 | 실제 사용은 win32com/client·win32api/security/service 등 Windows API/COM 모듈이다. 혼합 라이선스 고지들을 유지하며 사용하지 않는 adodbapi/MAPI/Scintilla 소스·바이너리는 이 패키지에 묶지 않는다. | 조건 확인 |
| openpyxl 3.1.5 | MIT 허가문·저작권 보존. 패키지 자체는 별도 설치한다. | 조건 확인 |
| et-xmlfile 2.0.0 | MIT뿐 아니라 포함 Python 유래 코드의 LICENCE.python도 보존한다. | 조건 확인 |
| PyMuPDF 1.28.0 / MuPDF 1.28.0 | 사용자 AGPL 결정 유지, 완전한 원본 소스 압축본·고지·설치/빌드 설명과 현재 해시 대조. C++ 재빌드·바이너리 동일성 시험은 별도 범위다. | 소스·고지 조건 재확인 |
| xlrd 2.0.2 | 과거 코드에 광고 자료의 저작자 표시를 요구하는 추가 조건이 남아 있다. 아래 AGPL 결합 문제를 해소하지 못했다. | **차단** |

근거: [lxml 고정 버전의 예외 목록](https://raw.githubusercontent.com/lxml/lxml/lxml-5.4.0/LICENSES.txt), [python-hwpx 원문](https://github.com/airmang/python-hwpx/blob/main/LICENSE), [pypdf 고정 버전 원문](https://raw.githubusercontent.com/py-pdf/pypdf/6.14.2/LICENSE), [pywin32 고정 버전 원문](https://raw.githubusercontent.com/mhammond/pywin32/b312/win32/License.txt), [openpyxl 3.1.5](https://pypi.org/project/openpyxl/3.1.5/), [et-xmlfile 2.0.0](https://pypi.org/project/et-xmlfile/2.0.0/). 고정 설치본 고지의 해시는 [의존성 검토 JSON](review-2026-09-13/dependencies.json)에 있다.

## 남은 차단: xlrd와 AGPL 결합

[xlrd 2.0.2의 LICENSE](https://raw.githubusercontent.com/python-excel/xlrd/2.0.2/LICENSE)는 주 코드의 BSD형 조건 외에 David Giffin의 과거 코드에 적용되는 광고 표시 조건을 포함한다. 일부 모듈만 Giffin 코드에서 파생되지 않았다고 명시한다. 그 선언을 패키지 전체로 확대할 근거는 확인하지 못했다. [GNU의 BSD 광고 조항 설명](https://www.gnu.org/philosophy/bsd.html)은 광고 조항을 포함한 원래 BSD 조건의 GPL 비호환 문제를 설명한다.

teacher_doc은 `refresh_reference.py`에서 xlrd를 직접 import하고, `hwpdoc_runtime.py`의 doctor도 xlrd를 import한다. 따라서 단순히 외부 프로그램과 파일만 주고받는 독립 도구라고 기록할 수 없다. AGPL §7·§10의 추가 조건 제한과 위 라이선스를 대조한 결과, 현재 증거만으로 결합 배포 조건 충족을 확인할 수 없어 **보류**한다. 이는 법원의 위법 판단이 아니라 이 후보의 검토 게이트 판정이다.

권리 기록에는 xlrd의 원문·검토 결과를 남기되, 충족하지 못한 `conditions_review` 필드를 완료 근거로 채우지 않는다. 따라서 실제 패키지 검사도 계속 차단된다. 광고 표시를 NOTICE에 넣은 것은 고지 보존이며 호환성 해결이 아니다. MIT 허락이나 PyMuPDF의 무료 AGPL 선택을 다시 물을 사안도 아니다.

다음 기술적 해결안은 AGPL과 호환되는 XLS 읽기 라이브러리로 교체하고, 기존 사업관리카드와 가상학교 시험 자료에서 셀 값·파생 JSON의 동일성을 확인하는 것이다. 기존 라이브러리 제거, 운영 자료 변환, 라이선스 예외 부여는 이번 검토에서 실행하지 않았다. 교체한 경우 파일 해시·의존성 고지·회귀시험을 갱신한 뒤 게이트를 다시 실행해야 한다.

## 결과와 추적

실제 `build_distribution.py --rights distribution/rights.pending.json`은 종료 코드 2로 xlrd 의존성 조건 1건만 반환했다. 권리/개인정보/소스 고지 오류는 0건이다. 배포 관련 회귀시험 `test_distribution_*.py` **48개 통과**를 확인했다. 소스 해시·현재 검토 입력·고지 대응을 다시 대조했다.

- [파일별 검토](review-2026-09-13/files.json)
- [의존성별 검토](review-2026-09-13/dependencies.json)
- [현재 검토 입력](rights.pending.json)
- [실제 게이트와 검증 결과](review-2026-09-13/validation.json)

기존 73개 파일의 권리/개인정보 미확인과 의존성 7건 미확인을, 완료한 파일 검토와 **xlrd 한 종의 구체적 결합 조건 차단**으로 정리했다. 앱 인수·패키지 수명주기 시험·최종 배포 판단은 별도로 남는다.
