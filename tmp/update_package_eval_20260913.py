from package_lifecycle_20260913 import *
from collections import Counter
import re

PREV=ROOT/'tmp/eval-integrated-20260913-v4';OUT=ROOT/'tmp/eval-integrated-20260913-v5'
REPORT=ROOT/'docs/플러그인-보급-평가통합표-2026-09-13.md'
assert not OUT.exists();trial=read(RUN/'summary.json');assert trial['package_cli_lifecycle']=='pass'
OUT.mkdir();previous=REPORT.read_bytes();(OUT/'previous-report.md').write_bytes(previous)
rows=read(PREV/'rows.json');old_summary=read(PREV/'summary.json');index=read(PREV/'evidence-index.json')
labels={'historical_pass':'과거 합격','fixed_verified':'수정 후 확인','behavior_verified':'동작 확인','partial':'부분 확인','material_ready':'자료 확보·후속 대기','blocked':'선행 조건 대기','pending':'미실행','excluded':'범위 제외'}
changes=[]
for row in rows:
    state=None
    if row['id']=='20--cli--default':
        state='behavior_verified';note='XLS 판독기를 MIT python-calamine 0.7.0으로 교체. 318셀·파생 JSON 동일 및 회귀시험 133개 통과. 103파일의 현재 게이트 차단 0, 실제 패키지 생성. 기존 MIT·AGPL 결정과 xlrd 표시 약속 보존.';action='현재 패키지의 권리·출처 조건 확인 완료. 변경 시 새 해시로 재검토.';remaining='';scope='current_package_license_gate_and_regression'
    elif row['id']=='19--cli--clean':
        state='behavior_verified';note='실제 ZIP: 허용 103파일+생성 목록 1개, 초과 파일 0. CRC·모든 파일 SHA256 일치. 텍스트 87개 식별정보 검사 및 단일 PNG 직접 열람(빈 이미지) 완료. 5위치 고장 주입 시험은 별도 행 미실행.';action='현재 clean 후보 확인 완료. 변조 표식 탐지는 sentinel_leak 행에서 별도 확인.';remaining='';scope='actual_clean_archive_inventory_text_and_image_review'
    elif row['id'].startswith('22--'):
        state='partial';note='Codex·Claude 실제 plugin CLI로 허가된 패키지 설치·업데이트·제거 완료. 설치 코드 W1 전체 검증·전달, 코드 변경 시 재검증 요구, 승인 입력·자료 42개 및 사용자 훅 보존 확인. 새 앱/LLM 문맥 로딩 인수는 미실행.';action='새 앱 문맥의 스킬·훅 로딩 인수를 보완. CLI 패키지 수명주기 시험은 반복할 필요 없음.';remaining='새 앱 문맥 인수';scope='actual_plugin_manager_and_installed_code_not_fresh_app_context'
    if state:
        before=row['current_status'];row.update(current_status=state,current_label=labels[state],observation=note,next_action=action,remaining_condition=remaining,evidence_scope=scope)
        row['history'].append({'source':'package_lifecycle_v5','state':state,'note':note})
        paths=['docs/실제-배포-패키지-검증-2026-09-13.md','tmp/package-lifecycle-20260913/summary.json','tmp/package-lifecycle-20260913/evidence-index.json']
        if row['case']=='20':paths+=['distribution/calamine-review-2026-09-13.md','tmp/package-lifecycle-20260913/lifecycle-evidence/final-release-gate.json']
        elif row['case']=='19':paths+=['tmp/package-lifecycle-20260913/clean-candidate-scan.json','tmp/package-lifecycle-20260913/archive-verification.json']
        else:paths+=[f"tmp/package-lifecycle-20260913/{row['target']}-{row['variant']}-verification.json"]
        for p in paths:
            h=sha(ROOT/p);row['evidence'].append({'path':p,'sha256':h});index[p]=h
        changes.append({'id':row['id'],'from':before,'to':state,'note':note})
counts=Counter(r['current_status'] for r in rows);prior=Counter(r['current_status'] for r in read(PREV/'rows.json'))
active=[r for r in rows if r['current_status'] in ('partial','material_ready','blocked','pending')]
assert len(rows)==len({r['id'] for r in rows})==176
assert Counter(r['initial_verdict'] for r in rows)=={'pass':56,'fail':3,'blocked':115,'pending':2}
assert len(active)==55 and counts['partial']==32 and counts['behavior_verified']==53
source_changes=[];sources={}
for p,h in old_summary['source_hashes'].items():
    current=sha(ROOT/p);sources[p]=current
    if current!=h:source_changes.append({'path':p,'previous_sha256':h,'current_sha256':current,'reason':'Authorized current-package dependency migration/review or report update; historical snapshots preserved'})
for p in index:
    if p.startswith('tmp/package-lifecycle-20260913/') or p in ('docs/실제-배포-패키지-검증-2026-09-13.md','distribution/calamine-review-2026-09-13.md'):sources[p]=sha(ROOT/p)
summary=dict(old_summary,revision=5,created_at=now(),current_counts=dict(counts),active_followup_rows=len(active),previous_active_followup_rows=57,status_transitions=changes,initial_blocked_115_current_counts=dict(Counter(r['current_status'] for r in rows if r['initial_verdict']=='blocked')),new_independent_pass_promotions=0,new_app_tests_run=False,new_package_cli_trials_run=True,release_gate_rechecked=True,release_issue_counts={},release_decision='hold',package_cli_lifecycle='pass',source_hashes=sources,authorized_source_updates_since_v4=source_changes,previous_report_sha256=hashlib.sha256(previous).hexdigest(),new_full_workflows_completed=0,installed_code_W1_trials_completed=2)
save(OUT/'rows.json',rows);save(OUT/'summary.json',summary);save(OUT/'evidence-index.json',index)
body='''# 플러그인 보급 평가 통합표 — 2026. 9. 13. (5차: 실제 패키지 시험)

**실제 패키지의 Codex·Claude CLI 설치·업데이트·제거와 자료 보존은 통과했다. 공개 배포는 보류한다.** 최초 독립 판정은 합격 56 / 실패 3 / 미실행 2 / 차단 115를 그대로 유지한다. 후속 동작 확인을 독립 인수 합격으로 승격하지 않는다.

| 현재 상태 | 4차 | 5차 |
|---|---:|---:|
'''
body+=''.join(f'| {label} | {prior[state]} | {counts[state]} |\n' for state,label in labels.items())
body+='''| 합계 | 176 | 176 |

**후속 작업이 남은 행은 57개에서 55개로 감소했다.** 이는 부분 확인·자료 확보·선행 조건 대기·미실행의 합계이며 결함 수나 승인 요청 횟수가 아니다. 라이선스 1행과 정상 패키지 검사 1행을 동작 확인으로 바꿨다. 업데이트·제거 4행은 CLI 시험을 완료했지만 새 앱 문맥 요건이 남아 부분 확인으로 기록한다.

## 이번 결과

- [실제 패키지 검증 보고서](실제-배포-패키지-검증-2026-09-13.md): 허용 103파일, ZIP 전체 CRC·해시 일치, 양 CLI 실제 설치·업데이트·제거, 승인 입력·자료 각 42개와 사용자 훅 보존. 원본 460개·전역 설정 4개 불변.
- 설치된 코드로 기존 승인 W1 작성→전체 검증→시험 전달 및 업데이트 후 재검증을 수행했다. 새 LLM/앱 문맥의 생성 시험이나 새 문안 승인으로 기록하지 않았다.
- [XLS 의존성 교체](../distribution/calamine-review-2026-09-13.md): xlrd 대신 MIT python-calamine 0.7.0. 실제 사용 셀 318개와 파생 JSON 동일, 회귀시험 133개 통과. 기존 MIT·무료 AGPL 결정과 README 저작자 표시 약속 보존.
- [현재 게이트](../tmp/package-lifecycle-20260913/lifecycle-evidence/final-release-gate.json)는 차단 0건. [과거 배포 검토](../distribution/release-review-2026-09-13.md)의 xlrd 차단은 당시 결과로 보존하며 현재 차단 사유로 사용하지 않는다.
- 5위치 표식 삽입 시험은 미실행이다. 정상 ZIP 검사만으로 탐지 능력을 확인했다고 표시하지 않았다.

## 환경별 범위

| 환경 | 확인한 범위 | 남은 범위 |
|---|---|---|
| Codex Desktop | 이전 승인 W1·W2 생성·전체 검증·시험 전달 | 새 패키지의 새 앱 문맥 인수·나머지 업무 분기 |
| Codex CLI 0.147.0 기본 사용자 권한 | 이번 격리 패키지 설치·업데이트·제거, 설치 코드 W1 전체 흐름·COM·렌더·재검증 | 새 LLM 문맥의 스킬·훅 로딩과 구분 |
| Claude Code CLI 2.1.270 | 이전 승인 W1·W2 흐름 및 이번 실제 패키지 관리·설치 코드 검증 | 새 앱 문맥 인수, Claude Desktop과 구분 |
| Codex CLI workspace-write | COM 제한을 빠르게 실패·미확인으로 반환 | 제한 모드 COM 지원 미완료 |
| Claude Desktop Cowork | 실제 앱 연결 상태 확인 | Windows COM 연결 없음, W1/W2 미실행 |
| VS Code Claude 확장 | 지침·스킬·절차·W2 원문 실제 Read 4회 | 전체 작성·검증·전달 미완료 |
| 외부 PC | 사용자 요청으로 제외 | 이번 작업에서 시험하지 않음 |

[이전 승인 흐름](W1-W2-승인후-두앱-흐름시험-2026-09-13.md) · [남은 업무 분기](미검증-분기-시험-2026-09-13.md) · [CLI COM](Codex-CLI-COM-시간초과-수정-2026-09-13.md) · [Claude Desktop](Claude-데스크톱-Cowork-확인-2026-09-13.md)

## 남은 실행 목록

| 사례 | 남은 행 | 다음 처리 |
|---|---:|---|
'''
for case in sorted({r['case'] for r in active}):
    group=[r for r in active if r['case']==case];actions=list(dict.fromkeys(r['next_action'] for r in group))
    body+=f"| {case} {group[0]['title']} | {len(group)} | {' / '.join(actions)} |\n"
body+='\n## 이번 상태 변경\n\n| ID | 이전 | 현재 |\n|---|---|---|\n'
body+=''.join(f"| {c['id']} | {labels[c['from']]} | {labels[c['to']]} |\n" for c in changes)
body+='\n## 176행 상세\n\n최초 판정·해시·변경 이력은 JSON과 과거 스냅샷에 보존한다.\n\n| ID | 시험 | 최초 | 현재 | 최신 관측 | 다음 처리 | 근거 |\n|---|---|---|---|---|---|---|\n'
def cell(v):return str(v).replace('|','\\|').replace('\n',' ')
for row in rows:
    path=row['evidence'][-1]['path']
    body+='| '+' | '.join(map(cell,[row['id'],row['title'],row['initial_verdict'],row['current_label'],row['observation'],row['next_action']]))+f' | [근거](../{path}) |\n'
body+='''
## 근거와 검증

[행별 JSON](../tmp/eval-integrated-20260913-v5/rows.json) · [집계](../tmp/eval-integrated-20260913-v5/summary.json) · [해시 목록](../tmp/eval-integrated-20260913-v5/evidence-index.json) · [검증](../tmp/eval-integrated-20260913-v5/validation.json) · [이전 보고서 보존본](../tmp/eval-integrated-20260913-v5/previous-report.md)

평가표 변경은 신규 독립 채점이 아니다. 공개 배포 판단은 보류하며, 새 앱 문맥 인수·미검증 업무 분기·표식 고장 주입·동료 시범 사용을 남은 조건으로 유지한다.
'''
REPORT.write_text(body,encoding='utf-8',newline='\n')
links=re.findall(r'\]\(([^)]+)\)',body)
missing=[p for p in links if not (REPORT.parent/p).is_file() and (REPORT.parent/p).resolve()!=(OUT/'validation.json').resolve()]
assert not missing,missing
save(OUT/'validation.json',{'unique_rows':176,'initial_verdicts_unchanged':True,'current_count_sum':sum(counts.values()),'active_followup_rows':55,'status_changes':len(changes),'new_independent_pass_promotions':0,'all_report_links_exist':True,'previous_snapshot_preserved':True,'source_changes_documented':source_changes,'report_sha256':sha(REPORT)})
assert all((REPORT.parent/p).is_file() for p in links)
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'ts':now(),'agent':'codex','action':'refresh_package_evaluation','target':str(REPORT),'result':'updated','detail':{'revision':5,'active_rows':55,'cli_lifecycle_pass':True,'fresh_app_acceptance_pending':True}},ensure_ascii=False)+'\n')
print(json.dumps({'revision':5,'counts':dict(counts),'active':55,'changed_rows':len(changes)},ensure_ascii=False))
