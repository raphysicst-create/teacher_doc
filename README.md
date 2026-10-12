# teacher_doc

교사의 기존 양식을 보존하면서 공문 초안 작성, HWPX 생성, 검증과 사람 검토를 돕는다.

GitHub `0.1.3`(2026. 10. 2., `380a122`)의 실행기·HWPX 안전 편집·설치 기능을 이 개발 정본에 동기화했다. 학교 운영 자료와 설정은 유지한다. [동기화 범위와 검증 기록](docs/GitHub-동기화-20261012.md), [첫 설치 안내](docs/BEGINNER.md)를 참고한다.

```powershell
./scripts/teacher_doc.ps1 --help
./scripts/teacher_doc.ps1 --workspace 'C:/교사 작업/공문' doctor
```

- [설치·사용·배포 안내](distribution/README.md)
- [프로젝트 실행 규칙](CLAUDE.md)
- [독립 평가](evals/plugin_distribution/README.md)
- [이름 변경 및 경로 이전](docs/teacher_doc-이름변경.md)

프로젝트와 플러그인 이름은 `teacher_doc`이다. 기존 `hwpdoc.py`/`hwpdoc.ps1`, `.hwpdoc` 작업 기록, `HWPDOC_*` 환경변수와 PC 데이터 폴더는 호환성을 위해 유지한다. `hwpx`는 파일 형식과 스킬 이름이다. 이름 변경만으로 기존 승인·검증·권리 검토 기록을 갱신하지 않는다.
