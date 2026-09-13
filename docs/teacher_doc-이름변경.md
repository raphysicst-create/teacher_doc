# teacher_doc 이름 변경

2026. 9. 13. 사용자 요청: 전체 프로젝트와 폴더 이름을 `teacher_doc`으로 변경.

프로젝트·두 앱의 플러그인 식별자·배포 폴더·새 CLI는 `teacher_doc`으로 맞춘다. 기존 `hwpdoc` Python 모듈/CLI, `.hwpdoc` 데이터, `%LOCALAPPDATA%/hwpdoc`, `HWPDOC_*` 환경변수와 `hwpx` 형식/스킬 이름은 호환용으로 유지한다. 실제 공문·양식·검토 결과·평가 원증거의 본문과 해시를 이름 변경 목적으로 수정하지 않는다.

## 폴더 이전

- 이전: `C:\Users\22\Desktop\maintain\Hwp_doc`
- 새 경로: `C:\Users\22\Desktop\maintain\teacher_doc`
- 기존 폴더가 실행 중인 프로세스에 잠겨 직접 Rename-Item이 실패했다. 파일은 이동되지 않았다.
- `.claude/scratchpad/rename-teacher-doc/finish-rename.ps1`이 Codex 완전 종료와 폴더 잠금 해제를 기다린 뒤 이동하도록 준비됐다. 실제 완료 여부는 같은 폴더의 `status.json`에서 확인한다.
- 이전 경로에는 새 폴더를 가리키는 junction을 남겨 기존 세션·절대경로 자료가 계속 접근하게 한다. 데이터 복제본이 아니다. 기존 경로 연결이 필요한 동안 삭제하지 않는다.
- 이후 프로젝트 훅 경로·부모 안내·전역 보호 마커·Claude 프로젝트 메모리·Codex 프로젝트 경로/표시 이름을 갱신한다. 다른 프로젝트 설정은 보존한다. 외부 설정의 변경 전 사본은 같은 scratchpad의 backups에 보관한다.

수동 재실행이 필요한 경우 Codex/Claude와 이 폴더를 사용하는 터미널을 닫고, 부모 폴더에서 실행한다.

```powershell
powershell.exe -NoProfile -File 'C:\Users\22\Desktop\maintain\Hwp_doc\.claude\scratchpad\rename-teacher-doc\finish-rename.ps1' -Apply
```

Codex의 훅 신뢰 해시는 복사하거나 자동 승인하지 않는다. 새 경로에서 신뢰 확인이 요청되면 앱에서 확인한다. 코드/경로 변경으로 이전 검증이 미확인이 될 수 있으며 기존 사람 승인이나 평가 lock을 고쳐 통과시키지 않는다.

GitHub 저장소 이름과 origin은 이 로컬 이름 변경으로 갱신하지 않았다. 커밋·푸시·공개 배포도 수행하지 않는다. 배포 허용 목록은 새 CLI 2개가 추가되어 72개이며 파일별 현재 해시 검토가 필요하다.
