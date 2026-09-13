from branch_acceptance_20260913 import *
from collections import Counter
import re
PREV=ROOT/'tmp/eval-integrated-20260913-v3'
OUT=ROOT/'tmp/eval-integrated-20260913-v4'
REPORT=ROOT/'docs/플러그인-보급-평가통합표-2026-09-13.md'
assert not OUT.exists()
trial=read(RUN/'summary.json');assert trial['full_workflow_complete'] is False
OUT.mkdir();before=REPORT.read_bytes();(OUT/'previous-report.md').write_bytes(before)
rows=read(PREV/'rows.json');summary=read(PREV/'summary.json');index=read(PREV/'evidence-index.json')
changes=[]
for app in ['codex','claude']:
    for case,variant in [('23','default'),('24','default'),('27','official_reply'),('27','email')]:
        row=next(r for r in rows if r['id']==f'{case}--{app}--{variant}')
        prev=row['current_status']
        note='새 분기 문안 제시·원본 슬롯/예산 대조와 실제 미승인 build 차단(exit 2, HWPX 미생성) 확인. 해당 문안 승인·정상 생성·COM·렌더·전달은 아직 미완료.'
        action='제시한 문안 확인 후 미확인 값을 보존해 사본 생성·전체 검증·필요한 실제 렌더·시험 전달 진행.'
        row.update(current_status='partial',current_label='부분 확인',observation=note,next_action=action,remaining_condition='새 문안 확인 및 정상 전체 흐름 미완료',evidence_scope='actual_host_unapproved_input_preflight_only')
        row['history'].append({'source':'branch_preflight_v4','state':'partial','note':note})
        paths=['docs/미검증-분기-시험-2026-09-13.md','tmp/branch-acceptance-20260913/summary.json',f'tmp/branch-acceptance-20260913/evidence/{app}-preflight-summary.json']
        for p in paths:
            e={'path':p,'sha256':sha(ROOT/p)};row['evidence'].append(e);index[p]=e['sha256']
        changes.append({'id':row['id'],'from':prev,'to':'partial','note':note})
counts=dict(Counter(r['current_status'] for r in rows));active=sum(r['current_status'] in ('partial','material_ready','blocked','pending') for r in rows)
assert len(rows)==176 and len({r['id'] for r in rows})==176 and active==57
assert Counter(r['initial_verdict'] for r in rows)=={'pass':56,'fail':3,'pending':2,'blocked':115}
text=before.decode('utf-8').replace('\r\n','\n').replace('(3차: 배포 검토 반영)','(4차: 미검증 분기 시험 착수)')
text=text.replace('이번에는 새 앱 시험이나 독립 재채점을 하지 않았다.','이번에는 VS Code의 실제 읽기와 두 호스트의 미승인 입력 차단을 확인했다. 새 분기의 전체 흐름 완료나 독립 재채점은 아니다.')
text=text.replace('tmp/eval-integrated-20260913-v3/','tmp/eval-integrated-20260913-v4/')
labels={'historical_pass':'과거 합격','fixed_verified':'수정 후 확인','behavior_verified':'동작 확인','partial':'부분 확인','material_ready':'자료 확보·후속 대기','blocked':'선행 조건 대기','pending':'미실행','excluded':'범위 제외'}
prior=Counter(r['current_status'] for r in read(PREV/'rows.json'))
for state,label in labels.items():text=re.sub(r'^\| '+re.escape(label)+r' \|.*$',f'| {label} | {prior[state]} | {counts[state]} |',text,flags=re.M)
text=re.sub(r'\*\*후속 작업이 남은 행: .*?\*\*','**후속 작업이 남은 행: 57개(동일).**',text,count=1)
start=text.index('## 이번에 반영한 결과')
text=text[:start]+text[start:].replace('## 이번에 반영한 결과','''## 이번에 반영한 결과

- 새 4종 초안과 원본 슬롯·예산을 대조하고 Codex Desktop·Claude Code CLI에서 미승인 입력 5건씩이 생성 전에 차단되는 것을 실제 확인했다. 사례 23·24·27의 8행은 자료 확보에서 부분 확인으로 변경했으며 새 전체 흐름 합격은 없다.
- VS Code Claude 확장에서 프로젝트 지침·스킬·업무 절차·W2 원문을 실제 Read 4회로 확인했다. 전체 흐름은 사용자 실행 시작 대기다. 화면 조작 도구의 명령 실행 제한을 앱 결함으로 표시하지 않는다.
- [이번 분기 시험 보고서](../docs/미검증-분기-시험-2026-09-13.md) · [새 문안](../tmp/branch-acceptance-20260913/drafts.md) · [VS Code 실행 요청문](../tmp/branch-acceptance-20260913/vscode-run-request.md)

이전 차수에서 확인한 결과:
''',1)
text=text.replace('| VS Code | 이번 최신 전체 흐름 근거 없음 | 현재 소스로 별도 인수 필요 |','| VS Code Claude 확장 | 실제 지침·스킬·업무 절차·W2 원문 Read 4회 확인 | 준비한 실행 요청문 사용자 시작, 생성·COM·렌더·전달 미완료 |')
for case in ['23','24','27']:
    text=re.sub(r'^(\| '+case+r' [^|]+ \| \d+ \|).*$',r'\1 새 문안 제시와 미승인 차단 확인 완료. 문안 확인 후 생성·전체 검증·시험 전달 진행. |',text,flags=re.M)
for ch in changes:
    r=next(r for r in rows if r['id']==ch['id'])
    line='| '+' | '.join([r['id'],r['title'],r['initial_verdict'],r['current_label'],r['observation'],r['next_action'],'[근거](../tmp/branch-acceptance-20260913/summary.json)'])+' |'
    # Detailed rows only; shorter historical transition rows are preserved below.
    text=re.sub(r'^\| '+re.escape(r['id'])+r' \|[^\n]*$',lambda m:line if m.group(0).count('|')>5 else m.group(0),text,flags=re.M)
text=text.replace('## 상태 변경 목록','''## 이번 차수 상태 변경

| ID | 이전 | 현재 |
|---|---|---|
'''+''.join(f"| {c['id']} | 자료 확보·후속 대기 | 부분 확인 |\n" for c in changes)+'\n## 이전 차수 상태 변경 목록',1)
REPORT.write_text(text,encoding='utf-8',newline='\n')
updates=[];sources={}
for p,h in summary['source_hashes'].items():
    current=sha(ROOT/p);sources[p]=current
    if current!=h:updates.append({'path':p,'previous_sha256':h,'current_sha256':current,'reason':'Authorized README attribution acknowledgement or current follow-up report; old snapshot preserved'})
for p in index:
    if p.startswith('tmp/branch-acceptance-20260913/') or p=='docs/미검증-분기-시험-2026-09-13.md':sources[p]=sha(ROOT/p)
summary.update(revision=4,created_at=now(),previous_active_followup_rows=57,active_followup_rows=active,current_counts=counts,initial_blocked_115_current_counts=dict(Counter(r['current_status'] for r in rows if r['initial_verdict']=='blocked')),new_app_tests_run=True,release_gate_rechecked=False,status_transitions=changes,source_hashes=sources,authorized_source_updates_since_v3=updates,previous_report_sha256=hashlib.sha256(before).hexdigest(),new_full_workflows_completed=0,vscode_actual_read_calls=4)
save(OUT/'rows.json',rows);save(OUT/'summary.json',summary);save(OUT/'evidence-index.json',index)
links=re.findall(r'\]\(([^)]+)\)',text)
assert all((REPORT.parent/p).is_file() for p in links if (REPORT.parent/p).resolve()!=(OUT/'validation.json').resolve())
save(OUT/'validation.json',{'unique_rows':176,'active_followup_rows':57,'current_count_sum':sum(counts.values()),'initial_verdicts_unchanged':True,'previous_snapshot_preserved':True,'new_full_workflows_completed':0,'source_updates_documented':updates,'report_sha256':sha(REPORT),'all_report_links_exist':True})
assert all((REPORT.parent/p).is_file() for p in links)
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'ts':now(),'agent':'codex','action':'refresh_branch_evaluation','target':str(REPORT),'result':'partial','detail':{'revision':4,'changed_rows':8,'active_rows':57,'full_workflows_completed':0}},ensure_ascii=False)+'\n')
print(json.dumps({'rows':len(rows),'counts':counts,'active':active,'changes':len(changes)},ensure_ascii=False))
