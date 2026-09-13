"""Finish the same v4 snapshot after correcting validation self-link ordering."""
from branch_acceptance_20260913 import *
from collections import Counter
import re
OUT=ROOT/'tmp/eval-integrated-20260913-v4'
REPORT=ROOT/'docs/플러그인-보급-평가통합표-2026-09-13.md'
assert (OUT/'rows.json').is_file() and not (OUT/'validation.json').exists()
save(OUT/'generation-error.json',{'at':now(),'error':'Validation self-link was checked before validation.json was written','effect':'Rows/report written correctly; final validation/audit completion not yet written','recovery':'Preserve previous-report and rows; correct derived counters, then create and verify validation receipt.'})
rows=read(OUT/'rows.json');old=read(ROOT/'tmp/eval-integrated-20260913-v3/rows.json');summary=read(OUT/'summary.json')
save(OUT/'summary-before-final-check.json',summary)
summary.update(initial_blocked_115_current_counts=dict(Counter(r['current_status'] for r in rows if r['initial_verdict']=='blocked')),new_app_tests_run=True,release_gate_rechecked=False)
save(OUT/'summary.json',summary)
assert len(rows)==176 and len({r['id'] for r in rows})==176
assert {r['id']:r['initial_verdict'] for r in rows}=={r['id']:r['initial_verdict'] for r in old}
assert Counter(r['current_status'] for r in rows)==summary['current_counts']
assert sum(r['current_status'] in ('partial','material_ready','blocked','pending') for r in rows)==57
links=re.findall(r'\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8'))
assert all((REPORT.parent/p).is_file() for p in links if (REPORT.parent/p).resolve()!=(OUT/'validation.json').resolve())
save(OUT/'validation.json',{'at':now(),'unique_rows':176,'active_followup_rows':57,'current_count_sum':176,'initial_verdicts_unchanged':True,'previous_snapshot_preserved':True,'new_full_workflows_completed':0,'all_report_links_exist':True,'report_sha256':sha(REPORT),'recovered_generation_error':'generation-error.json','vscode_read_calls':4,'actual_preflight_rejections':10})
assert all((REPORT.parent/p).is_file() for p in links)
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps({'ts':now(),'agent':'codex','action':'refresh_branch_evaluation','target':str(REPORT),'result':'partial','detail':{'revision':4,'changed_rows':8,'active_rows':57,'full_workflows_completed':0,'report_generator_self_link_fixed':True}},ensure_ascii=False)+'\n')
print('PASS: 176 initial verdicts preserved; 10 actual rejection checks; 8 rows partial; 57 follow-ups remain; links verified.')
