from pathlib import Path
import hashlib,json,shutil,datetime,subprocess
R=Path.cwd(); T=R/'tmp/astra-low-batch-20260912/case04'; O=R/'output/astra-low-batch-20260912/case04'; D=Path(r'C:\Users\22\OneDrive - 화동중학교\작업 보고용\astra-low-batch-20260912\case04'); O.mkdir(parents=True,exist_ok=True);D.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='2026학년도 2학기 2회고사 교과협의회 회의록_기안문.hwpx'
report='''# case04 검증보고서

모델 설정: gpt-6-astra / low. Hwp_doc 독립 재작성. 실제 요청과 생성 승인 해석·초안/입력/지침 해시는 작업 폴더 approval.json에 기록했다. 새 승인 발언·검토 점수·발송 기록은 만들지 않았다.

본문-내부결재.md 변형 C 및 knowledge/examples/md/4505_2회고사교과협의회회의록.md와 본문 PDF를 확인했다. 동일 본체의 편집 가능한 HWPX는 발견되지 않아 스킬 gonmun 템플릿의 build_hwpx.py로 신규 생성했다. 첨부 회의록 양식은 본체로 사용하지 않았다. 기관명·수신·제목·관련·보고문·붙임 순서를 따른다. 원본 PDF의 슬로건·기결재선·도장은 재현하지 않았다. 새 본문의 전체 글꼴은 굴림, 본문 12pt, 기관명 22pt다.

업무지침: find_tasks는 not_found로 후보 없음. get_task_guide는 선택할 task_id가 없어 미실행. 원문 검색은 partial(127건 중 관련 근거 선택); 강원 중학교 학업성적관리시행지침 PDF 7쪽 및 계속 8쪽을 read_evidence로 확인했다. 교과(학년)협의회 구성·운영, 교과협의회 운영 불가 학교의 학년협의회 예외를 확인했다. 학교별 세부 운영/설립구분, 이후 별도 공문 전수 확인 및 원문 추출 의미 검토는 미확정이다. 해당 조건을 새로운 본문 의무로 추가하지 않았다. 근거 원문은 evidence.json이다.

| 검사 | 결과 |
|---|---|
| 최초 구조 validate / 11개 최소 패키지 | PASS |
| fix_namespaces | PASS, 변경 0 |
| finalize --strip-linesegarray | PASS |
| validate --layout | PASS, 본문 들여쓰기 휴리스틱 WARNING 1건 |
| page_guard 예산/구조 대조 | 미실행: 신규 작성이며 동일 본체 HWPX 기준 없음. 결과물로 기준을 재설정하여 통과 처리하지 않음 |
| 한글 COM 실열림 | PASS |
| PDF render_check | PASS: 1쪽, 앵커 발견율 100%, 순서 100%, 역순/잔재 없음 |
| PDF→PNG 육안 확인 | 1쪽, 제목/본문/붙임 잘림·겹침 없음. 긴 본문의 양쪽정렬 자간은 보임 |
| gonmun_lint | 최초 CLI 인자 오류 1회, --hwpx로 재시도 PASS, 지적 0 |
| content_guard | PASS: 필수 제목/결재 후 기재 안내 존재, 1학기·2861·옛 날짜 잔재 없음 |
| 관련번호 대조 | 미확정: 사용자가 번호 미제공 및 계획 결재 후 기재를 지정. 번호/날짜를 생성하지 않음 |
| 붙임 수 | 표기 1부 / 첨부 파일 0개: 사용자 지정 시험 범위, 추후 실제 첨부 필요 |
| kordoc 신구대조 | 수행, diff.json. PDF 블록과 HWPX 문단 차이로 추가7·삭제2로 표시 |
| 시간표·예산명 | 해당 없음 |

탐색 과정에서 존재하지 않는 본문-교과협의회.md와 gonmun/Contents 경로 조회가 실패하여 실제 본문-내부결재.md와 gonmun 루트 파일로 바로잡았다. 문서 검증 실패와 구분한다. COM은 부모 허가 후 직렬 실행했고 종료 후 잔존 Hwp 프로세스가 없었다. 기존 git 미완료 변경은 보존했다.

전체 파이프라인 완전 통과로 보고하지 않는다. page_guard 기준 대조 미실행, 업무지침 partial, 관련번호 미확정 및 실제 첨부 미포함을 보존한 검토용 기안문이다. 관련 표기는 “2026학년도 2학기 교과별 평가계획 수립(계획 결재 후 문서번호·시행일 기재)”이다. 계획 결재 후 실제 문서번호·시행일과 첨부를 확인해야 한다.

발송 전 한글로 열어 확인해주세요.
'''
report+='\n최종 HWPX SHA-256: '+sha(T/'result.hwpx')+'\n'
for p in [R/'CLAUDE.md',R/'.claude/skills/hwpx/SKILL.md',T/'request.md',T/'draft.md']:report+='\n'+str(p)+' SHA-256: '+sha(p)+'\n'
(O/'검증보고서.md').write_text(report,encoding='utf-8');shutil.copy2(T/'result.hwpx',O/name)
for p in [O/name,O/'검증보고서.md']:shutil.copy2(p,D/p.name)
assert sha(O/name)==sha(D/name)==sha(T/'result.hwpx')
with (R/'logs/audit.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'ts':datetime.datetime.now().astimezone().isoformat(),'agent':'astra-low-case04','action':'validate-deliver','target':str(O/name),'result':'review-draft','detail':{'sha256':sha(O/name),'com':'PASS','render':'PASS 1 page','lint_retry':'PASS','page_guard':'not run no HWPX reference','related':'pending per request','OneDrive':'copy hash match'}},ensure_ascii=False)+'\n')
print(O/name);print(sha(O/name))
