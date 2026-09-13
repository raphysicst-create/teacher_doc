from pathlib import Path
from collections import Counter
import datetime,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
PREV=ROOT/'tmp/eval-integrated-20260913-v2'
OUT=ROOT/'tmp/eval-integrated-20260913-v3'
REPORT=ROOT/'docs/플러그인-보급-평가통합표-2026-09-13.md'
assert not OUT.exists()
OUT.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
previous=REPORT.read_bytes();(OUT/'previous-report.md').write_bytes(previous)
rows=read(PREV/'rows.json'); summary=read(PREV/'summary.json'); index=read(PREV/'evidence-index.json')
r=next(r for r in rows if r['id']=='20--cli--default')
note='101개 파일의 현재 해시 권리·개인정보 검토 완료. MIT 허락·무료 AGPL·소스 고지 준비 완료. 의존성 8종 중 7종 조건 확인, xlrd 2.0.2의 과거 광고 조항과 AGPL 결합 조건 1건 차단. 정식 패키지 미생성.'
action='xlrd 결합 조건을 해결한 뒤 변경 파일·의존성을 재검토하고 패키지 게이트 재실행. 기존 MIT/AGPL 선택 재질문 없음.'
r.update(observation=note,next_action=action,remaining_condition='xlrd AGPL 결합 조건 미해결')
r['history'].append({'source':'release_review_v3','state':'blocked','note':note})
for path in ['distribution/release-review-2026-09-13.md','distribution/review-2026-09-13/files.json',
             'distribution/review-2026-09-13/dependencies.json','distribution/review-2026-09-13/actual-cli-gate.json']:
    e={'path':path,'sha256':sha(ROOT/path)};r['evidence'].append(e);index[path]=e['sha256']
old_sources=summary['source_hashes'];changes=[]
current={}
for path,old in old_sources.items():
    h=sha(ROOT/path);current[path]=h
    if h!=old:changes.append({'path':path,'previous_sha256':old,'current_sha256':h,'reason':'authorized distribution review updates; prior snapshot preserved'})
for e in r['evidence'][-4:]:current[e['path']]=e['sha256']
summary.update(revision=3,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               previous_active_followup_rows=57,status_transitions=[],source_hashes=current,
               authorized_source_updates_since_v2=changes,release_issue_counts={'dependency_license_unconfirmed':1},
               previous_report_sha256=hashlib.sha256(previous).hexdigest(),
               release_file_reviews_completed=101,release_dependency_conditions_checked=7,
               release_blocking_dependency='xlrd==2.0.2')
save(OUT/'rows.json',rows);save(OUT/'summary.json',summary);save(OUT/'evidence-index.json',index)
text=previous.decode('utf-8').replace('\r\n','\n').replace('(2차 갱신)','(3차: 배포 검토 반영)')
text=text.replace('tmp/eval-integrated-20260913-v2/','tmp/eval-integrated-20260913-v3/')
# The old v2 release snapshot link is replaced with the actual reviewed CLI gate.
text=text.replace('../tmp/eval-integrated-20260913-v3/release-gate.json','../distribution/review-2026-09-13/actual-cli-gate.json')
start=text.index('## 배포 검토');end=text.index('## 남은 실행 목록')
text=text[:start]+'''## 배포 검토

**101개 파일의 권리·개인정보 검토 완료.** 기존 권리 미확인 73건과 개인정보 미확인 73건은 각각 0건이다. 의존성은 8종 중 7종의 조건을 확인했으며, **xlrd 2.0.2 과거 코드의 광고 조항과 AGPL 결합 조건 1건**이 남았다. MIT 허락과 무료 AGPL 선택은 완료 상태를 유지한다.

실제 패키지 CLI도 xlrd 1건만 차단하는 것을 확인했다. 파일 검토 완료를 앱 인수·최종 배포 승인으로 바꾸지 않으며 패키지는 아직 생성하지 않았다. 평가 행 20은 계속 선행 조건 대기이므로 후속 행 수 **57개는 동일**하다.

[배포 검토 보고서](../distribution/release-review-2026-09-13.md) · [파일별 근거](../distribution/review-2026-09-13/files.json) · [의존성별 근거](../distribution/review-2026-09-13/dependencies.json) · [실제 게이트](../distribution/review-2026-09-13/actual-cli-gate.json)

'''+text[end:]
text=re.sub(r'^\| 20 라이선스·출처·버전 고정 \|.*$',f'| 20 라이선스·출처·버전 고정 | 1 | {action} |',text,flags=re.M)
line='| '+' | '.join([r['id'],r['title'],r['initial_verdict'],r['current_label'],note,action,'[근거](../distribution/review-2026-09-13/actual-cli-gate.json)'])+' |'
text=re.sub(r'^\| 20--cli--default \|.*$',line,text,flags=re.M)
REPORT.write_text(text,encoding='utf-8',newline='\n')
save(OUT/'validation.json',{'unique_rows':176,'active_followup_rows':57,'current_count_sum':176,
 'initial_verdicts_unchanged':True,'previous_snapshot_preserved':True,'source_updates_documented':changes,
 'new_app_tests_run':False,'release_gate_rechecked':True,'report_sha256':sha(REPORT)})
assert all((REPORT.parent/p).is_file() for p in re.findall(r'\]\(([^)]+)\)',text))
assert Counter(r['initial_verdict'] for r in rows)=={'pass':56,'fail':3,'pending':2,'blocked':115}
assert sum(r['current_status'] in ('partial','material_ready','blocked','pending') for r in rows)==57
assert all(sha(ROOT/p)==h for p,h in current.items())
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps({'ts':summary['created_at'],'agent':'codex','action':'refresh_evaluation_release_gate',
                       'target':'docs/플러그인-보급-평가통합표-2026-09-13.md','result':'complete',
                       'detail':{'revision':3,'remaining_rows':57,'release_dependency_blockers':1}},ensure_ascii=False)+'\n')
print('PASS: evaluation row 20 and release section refreshed; 176 original verdicts preserved; 57 follow-up rows remain')
