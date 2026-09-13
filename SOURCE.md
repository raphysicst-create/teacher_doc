# teacher_doc 0.1.0 소스 제공

이 패키지 자체가 teacher_doc의 편집 가능한 소스 배포본이다. `scripts/`의 Python·PowerShell, `.claude/hooks/`, `skills/hwpx/`의 코드·지침·XML, 플러그인 설정, `distribution/requirements-*.txt` 및 설치 안내를 함께 제공한다. 별도 컴파일·난독화된 teacher_doc 실행 파일은 없다. 작업 폴더의 학교 문서·설정·감사 기록은 프로그램 소스가 아니며 이 배포에 넣지 않는다.

배포 버전과 각 파일의 SHA256은 `release-inventory.json`, 아래 외부 소스의 출처·버전·SHA256은 `SOURCE-BUNDLE.json`에 기록한다. 수령자는 별도 요청이나 유료 계정 없이 패키지에서 이 소스를 얻는다. 배포자가 패키지를 올릴 때 아래 소스를 떼어내지 않는다.

## 포함 소스

- `sources/pymupdf-1.28.0.tar.gz`: PyPI가 게시한 1.28.0 소스 배포본. Python/C++ 소스, `setup.py`, `pyproject.toml`, 빌드 지원 스크립트와 시험 자료 포함.
- `sources/mupdf-1.28.0-source.tar.gz`: MuPDF 공식 1.28.0 소스 배포본. C/C++ 소스, 빌드 파일, Python 바인딩 생성 스크립트와 `thirdparty/` 소스·고지 포함.
- 두 압축본은 상류 원본 그대로다. 일반 설치는 `distribution/README.md`와 `scripts/install-dependencies.ps1`을 따른다.

## 소스에서 빌드하는 방법

teacher_doc 스크립트는 Python 3.12와 Windows PowerShell에서 직접 실행한다. 고정된 의존성 목록과 한글 자동화 환경 준비는 `distribution/README.md`를 따른다. 한글 등 별도 설치 프로그램은 이 배포에 포함되지 않는다.

PyMuPDF를 직접 빌드하려면 두 소스 압축본을 별도 작업 폴더에 풀고, C/C++ 개발 도구를 준비한다. 상류 설치 안내는 https://pymupdf.readthedocs.io/en/latest/installation.html 이며 이 고정 버전의 구체적인 빌드 동작은 소스의 `setup.py`가 기준이다. 필요한 Python 빌드 의존성은 `pyproject.toml`에 있다. Windows 예시는 다음과 같다. `$taskPython`은 준비한 가상환경의 Python 실행 파일이다.

```powershell
$env:PYMUPDF_SETUP_MUPDF_BUILD = (Resolve-Path './mupdf-1.28.0-source').Path
& $taskPython -m pip wheel './pymupdf-1.28.0' --wheel-dir './built-wheels'
Remove-Item Env:PYMUPDF_SETUP_MUPDF_BUILD
```

상류 빌드에는 Visual Studio C/C++ 도구 등 플랫폼별 도구가 필요하며 Python 빌드 의존성을 받기 위한 네트워크가 필요할 수 있다. 이 작업에서 C++ 전체 재빌드나 PyPI wheel과의 바이너리 동일성 검증은 수행하지 않았다. 소스 압축본 해시, 고정 버전, 필수 소스·빌드 파일의 존재를 확인했다.

수정본을 배포하면 그 수정본의 실제 소스와 변경 고지를 함께 갱신한다. 네트워크를 통해 사용자와 상호작용하는 수정 서비스를 제공하는 경우에는 AGPL §13의 해당 소스 제공 조건도 적용한다. 현재 패키지는 교사의 로컬 실행용이다.
