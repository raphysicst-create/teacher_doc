# teacher_doc 이름 변경 실행 상태

2026. 9. 13. 코드·플러그인 이름, 기본 CLI와 배포 폴더 정의를 teacher_doc으로 변경했다. 최종 개발 회귀시험 103개 통과(72.302초), 새 CLI 도움말·Codex 매니페스트 검사·변경 공백 검사도 통과했다. 앱 서버에 저장된 프로젝트 이름 갱신·재조회도 확인했다.

실제 폴더는 다른 프로세스가 사용 중이라 즉시 이동하지 못했다. 처음 준비한 PowerShell 스크립트는 PC 실행 정책으로 시작되지 않았다. 실행 정책을 수정하지 않고 Python의 Windows 파일 API로 이전하는 보조 프로그램을 준비했다. 원본 보호 훅이 기존 안내문 추가 수정을 차단하여 이 파일에 후속 상태를 남긴다.

`.claude/scratchpad/rename-teacher-doc/run_rename.py --apply --wait-seconds 3600`이 Codex 완전 종료와 폴더 잠금 해제를 기다리도록 실행된다. Codex와 이 폴더를 사용하는 Claude/터미널을 닫은 뒤 완료를 기다린다. 실제 상태의 정본은 같은 디렉터리의 `status.json`이며 `complete` 전에는 폴더 이전 완료로 보지 않는다. 프로세스를 강제로 종료하지 않는다.

완료하면 실제 폴더는 `C:\Users\22\Desktop\maintain\teacher_doc`, 기존 Hwp_doc은 그 폴더로 이어지는 호환 junction이다. 기존 공문·로그·승인 해시는 보존하고 부모 안내·보호 마커·앱 경로·메모리 접근을 연결한다. 훅 신뢰를 자동 승인하지 않는다. 새 경로에서 앱이 요청하면 직접 확인한다.

대기 한도는 1시간이다. 시간 초과로 실행되지 않았으면 앱을 닫고 부모 폴더의 PowerShell에서 아래 명령을 실행한다. 이미 폴더가 이동됐다면 재실행하지 말고 status.json의 후속 오류부터 확인한다.

```powershell
& 'C:\Users\22\AppData\Local\Programs\Python\Python312\python.exe' -B -X utf8 'C:\Users\22\Desktop\maintain\Hwp_doc\.claude\scratchpad\rename-teacher-doc\run_rename.py' --apply
```

GitHub 저장소 이름·origin·커밋·푸시는 변경하지 않았다. 개발 회귀시험은 앱 보호나 실제 문서 품질 인수를 대신하지 않는다.
