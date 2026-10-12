# 앱 전용 Python 자동 준비

## 동의와 범위

“Python 포함 설치” 요청 또는 별도 승인이 있으면 bootstrap의 `-AllowPythonInstall`(Windows)/`--allow-python-install`(Unix)로 전용 런타임을 준비한다. 기존 Python 3.12가 있으면 재사용한다. 동의가 없고 Python도 없으면 다운로드 전에 exit 2와 `PYTHON_INSTALL_CONSENT_REQUIRED`로 멈춘다.

Windows x64/ARM64, macOS x64/ARM64, glibc Linux x64/ARM64용 메타데이터가 있다. 실제 검증한 OS/아키텍처는 [검증 기록](VERIFICATION.md)에 구분한다. Linux musl, 32비트 PC, 조직 정책이 설치를 차단하는 환경은 자동 설치 성공을 보장하지 않는다.

전용 PC 데이터 아래 `managed-python/`에만 Python을 두고, `runtimes/`의 venv에 패키지를 설치한다. 관리자 권한, 전역 PATH 변경, 레지스트리 등록, 셸 프로필 편집, 실행 정책 변경, 훅 등록은 하지 않는다. 작업 폴더·설치 코드·PC 데이터는 구분하고 기존 설정과 문서를 보존한다. 한글/보안모듈은 설치하지 않는다.

## 공급원·버전·무결성

2026-10-02 공식 공급원에서 확인하여 고정했다.

- uv **0.12.22**: [Astral 공식 릴리스](https://github.com/astral-sh/uv/releases/tag/0.12.22). `distribution/runtime-downloads.tsv`의 OS별 SHA-256과 다운로드 바이트가 일치해야 실행한다
- CPython **3.12.15**, 빌드 **20261001**: [Astral python-build-standalone 릴리스](https://github.com/astral-sh/python-build-standalone/releases/tag/20261001). python.org의 PSF Windows 설치기가 아니라 Astral이 만든 CPython 빌드다
- `distribution/python-downloads.json`은 [uv 0.12.22 공식 다운로드 메타데이터](https://github.com/astral-sh/uv/blob/0.12.22/crates/uv-python/download-metadata.json)의 해당 6개 항목을 그대로 가져왔다. 고정 uv는 이 로컬 JSON에 적힌 URL과 SHA-256으로 Python을 검증하며 불일치 시 설치를 중단한다
- uv의 `--install-dir`, `--no-bin`, `--no-registry`, `--no-config`를 명시한다. 외부 uv 환경 설정과 미러를 상속하지 않는다. [공식 CLI 문서](https://docs.astral.sh/uv/reference/cli/#uv-python-install)
- 설치 후 버전과 실제 실행 파일을 확인하고 `managed-python/install-receipt.json`에 공급원, 버전, 해시와 경로를 기록한다. 런타임 선택과 연습 성공은 `.hwpdoc/onboarding.json`에 별도로 남는다

고정 버전은 재현성과 무결성을 위한 것이며 최신 보안 업데이트가 자동 반영되지는 않는다. 유지보수자는 공식 릴리스와 보안 공지를 확인하여 uv·Python 버전·모든 해시를 함께 갱신한 뒤 no-Python CI와 독립 QC를 다시 수행한다. 임의 mirror/해시 우회/인증서 검증 해제 옵션은 제공하지 않는다.

## 라이선스

다운로드된 런타임은 이 저장소의 라이선스와 별개인 해당 배포본 라이선스를 따른다.

- [uv](https://github.com/astral-sh/uv/tree/0.12.22): MIT 또는 Apache-2.0
- [CPython](https://docs.python.org/3.12/license.html): PSF License 및 포함 구성요소의 고지
- [python-build-standalone 라이선스 안내](https://gregoryszorc.com/docs/python-build-standalone/main/): Python과 포함 라이브러리의 라이선스 정보는 다운로드된 배포본과 upstream 안내를 보존한다

이 저장소는 런타임 바이너리를 재배포하지 않고 공식 배포본을 검증해서 받는다. 기존 [NOTICE](../NOTICE.md), [SOURCE](../SOURCE.md), 라이선스와 소스 번들은 그대로 유지한다.

## 실패와 재시도

해시 불일치, 네트워크 오류, 쓰기 권한 거절은 실패로 종료한다. 기존 문서·설정은 보존한다. 다운로드 임시 폴더만 정리하고 소유 표시가 있는 앱 전용 폴더는 재실행에 사용한다. 실패 원인을 해결한 뒤 같은 명령으로 이어서 실행한다. 출처 없는 기존 `managed-python` 폴더, 손상된 `runtime.json`, 다른 앱의 workspace 설정은 덮어쓰지 않는다.

학교 PC에서 PowerShell/다운로드/프로그램 실행이 제한되면 담당자에게 필요한 허용을 문의한다. `-ExecutionPolicy Bypass`, 정책 변경, SmartScreen/TLS 우회로 해결하지 않는다. XML 성공은 한글 COM 실행, 앱의 실제 스킬 로딩, 문서별 렌더 확인을 대신하지 않는다.
