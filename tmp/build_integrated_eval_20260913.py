"""Consolidate immutable evaluation history and later observations; never rescore it."""
from pathlib import Path
from collections import Counter
import datetime, hashlib, json, re

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'.claude/scratchpad/plugin-distribution/run-01a097f3-20260913'
FOLLOW=ROOT/'tmp/followup-20260913'
MAT=ROOT/'tmp/materials-followup-20260913'
OUT=ROOT/'tmp/eval-integrated-20260913'
REPORT=ROOT/'docs/플러그인-보급-평가통합표-2026-09-13.md'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def relative(p):return p.relative_to(ROOT).as_posix()
sources=[OLD/'matrix.json',FOLLOW/'classification/rows.json',FOLLOW/'classification/summary.json',
    ROOT/'docs/플러그인-보급-미충족분류-정정-2026-09-13.md',MAT/'34-row-material-correction.json',
    MAT/'summary.json',MAT/'fixtures-local.json',MAT/'evidence/lineage-comparison.json',
    MAT/'evidence/codex-local-finish.json',MAT/'evidence/claude-local-trial.json',
    MAT/'app-artifacts/codex/local-materials-trial.md',MAT/'app-artifacts/claude/local-materials-trial.md',
    MAT/'evidence/conversion-native-render.json',MAT/'evidence/conversion-pixel-comparison.json',
    FOLLOW/'evidence/release-gate-final.json']
before={relative(p):sha(p) for p in sources}
base=read(OLD/'matrix.json'); follow={x['id']:x for x in read(FOLLOW/'classification/rows.json')}
materials={x['id']:x for x in read(MAT/'34-row-material-correction.json')}
labels={'historical_pass':'과거 합격','fixed_verified':'수정 후 확인','behavior_verified':'동작 확인',
        'partial':'부분 확인','material_ready':'자료 확보·후속 대기','blocked':'선행 조건 대기','pending':'미실행','excluded':'범위 제외'}
descriptions={
 'historical_pass':'최초 독립 평가의 합격 기록. 최신 수정본 전체 재평가와 구분.',
 'fixed_verified':'최초 실패를 수정하고 재현 시험으로 확인. 독립 점수는 보존.',
 'behavior_verified':'후속 실제 동작/원본 보존 근거 확인. 전체 독립 인수 pass는 아님.',
 'partial':'일부 실제 근거가 있으나 해당 행의 인수 조건이 남음.',
 'material_ready':'기존 실물 사본 확보. 후속 앱 실행·해당 분기 확인이 남음.',
 'blocked':'환경·실제 사람 응답·권리·패키지 등 선행 조건이 필요.',
 'pending':'실행하지 않았음. 선행 조건과 별도로 미실행 사실을 표시.',
 'excluded':'외부 PC/새 환경 제외 요청과 운영 환경 보존 범위 적용.'}
evidence_index={}; mismatches=[]
def evidence(p,expected=None):
    p=Path(p);assert p.is_file(),p
    item={'path':relative(p),'sha256':sha(p)}
    if expected is not None and expected!=item['sha256']:
        mismatches.append({'path':relative(p),'recorded_sha256':expected,'actual_sha256':item['sha256']})
    evidence_index[item['path']]=item['sha256'];return item

def next_for(case,variant):
    return {
      '09':'실물·매핑으로 실제 앱 등록을 진행하고 새 등록 검토가 필요한 부분을 제시.',
      '11':'동일 베이스에 내부결재/가통 발송 두 용도를 연결한 앱 등록·선택 결과 확인.',
      '13':'격리 설치의 새 문맥에서 스킬/업무 지침 본문 로딩 근거 확인.',
      '14':'새 앱 문맥에서 빈 셀·학년·메타데이터·선례 정책을 각각 실행.',
      '15':'해당 앱 MCP 도구 연결·실호출·사전 차단을 같은 인수 환경에서 확인.',
      '16':'폐기용 무표시 cwd/비공문 경로를 포함한 앱 권한 조건으로 실행.',
      '17':'미신뢰 상태의 실제 도구 호출·진단을 정상 신뢰 절차와 구분해 관측.',
      '18':'동일 단계 2회 실패 후 자동 중단을 실제 앱에서 관측.',
      '19':'허가된 릴리스 사본에서 clean 또는 5위치 시험 표식 탐지를 실행.',
      '20':'파일별 권리·개인정보 및 의존성 라이선스 조건 확인.',
      '22':'허가된 구·신 패키지로 실제 앱 업데이트/제거와 자료 보존 확인.',
      '23':'기존 일반 가통으로 앱 초안을 제시하고 문안 확인→전체 검증→전달 진행.',
      '24':'기존 회신형으로 앱 초안을 제시하고 문안 확인→전체 검증→전달 진행.',
      '25':'구체적인 데이터 1행 추가 범위의 확인 후 구조·쪽수·렌더 검증.',
      '26':'오래된 판독 또는 현재 판독 조건을 각각 구성하고 최종 해시와 대조.',
      '27':'제출 방법별 앱 초안을 제시하고 실제 문안 확인 후 흐름 완주.',
      '28':'운영 설치를 제거하지 않는 COM/렌더 부재 환경에서 미확인 보존 확인.',
      '29':'검토할 앱 산출물을 준비하고 해당 복사/검토 분기를 실행.',
      '30':'외부 PC 시험 제외 유지.',
      '32':'출처 있는 사본으로 앱별 변환·재패키징·폴백 부재 흐름 실행. 변환 경고는 별도 대조.'
    }.get(case,'원래 판정과 근거를 보존. 새 소스 독립 인수 시 재확인.')

rows=[]
for old in base:
    id=old['id'];case=id.split('--')[0];variant=old['variant'];app=old['target']
    state='historical_pass' if old['status']=='pass' else 'pending'
    note=old['reason'];action=next_for(case,variant);gate='';scope='original_independent_eval'
    ev=[evidence(OLD/old['record'])]
    history=[{'source':'initial','state':old['status'],'note':old['reason']}]
    if id in follow:
        f=follow[id];state=f['followup_outcome'];note=f['followup_note'];gate=f['followup_category'];scope='implementation_followup'
        ev += [evidence(ROOT/e['path'],e.get('sha256')) for e in f['followup_evidence']]
        history.append({'source':'followup','state':state,'note':note})
    if old['status']=='fail':
        state='fixed_verified';gate='';scope='developer_reproduction'
        key='04-long-path' if case=='04' else ('12-W1-observation' if variant=='missing_values' else '12-W2-observation')
        ev.append(evidence(FOLLOW/'evidence'/f'{key}.json'))
        note='긴 경로를 mkdir 전에 거절하고 지원 범위 안내; 부분 폴더 생성 없음.' if case=='04' else 'W1/W2 미제공 슬롯 목록을 표시하고 승인/제출 방법 미확인을 유지.'
        action='수정 재현 확인 완료. 정식 독립 평가 때 원래 행으로 재확인.'
        history.append({'source':'defect_reproduction','state':state,'note':note})
    if id in ('16--claude--no_marker','16--codex--no_marker'):
        state='pending';gate='실행 대기';note='별도 무표시 cwd 앱 시험 미실행. 실행 불가능한 선행 조건이 입증된 것으로 보지 않음.'
        ev.append(evidence(sources[3]));history.append({'source':'classification_correction','state':state,'note':note})
    if case=='30':
        state='excluded';gate='범위 제외';note='동료 교사 PC 최초 사용은 사용자의 외부 PC 제외 대상.'
        ev.append(evidence(sources[3]));history.append({'source':'classification_correction','state':state,'note':note})
    if id in materials:
        state='material_ready';gate='자료 확보, 개별 후속 확인';scope='authorized_local_school_materials'
        note='기존 output/examples/승인 템플릿 실물과 출처·해시·검증 자료 확보. 자료 부재 사유 해소.'
        ev += [evidence(MAT/'34-row-material-correction.json'),evidence(MAT/'fixtures-local.json')]
        if case=='11':
            state='partial';note='승인 기안문 8건의 실제 파일·header·제목·여백·COM 대조 완료. 두 용도의 앱 등록/선택까지 완료한 것은 아님.'
            ev.append(evidence(MAT/'evidence/lineage-comparison.json'))
        if (case=='25' and variant=='no_structure_approval') or (case=='26' and variant=='no_visual'):
            state='behavior_verified';gate=''
            note=('두 앱에서 데이터 5행과 6개 활동을 대조, 모든 활동을 초안에 보존하고 1행 추가 승인 전 보류.' if case=='25' else
                  '두 앱이 같은 실제 셀에 161자 입력을 1회 실행. 현재 예산 24자 초과로 거절, 출력 없음. 판독/우회 승인 생성 없음.')
            action='해당 로컬 동작 확인 완료. 승인된 구조 변경/현재 판독은 다른 행에서 진행.'
        if case in ('11','25','26'):
            ev.append(evidence(MAT/f'app-artifacts/{app}/local-materials-trial.md'))
            ev.append(evidence(MAT/'evidence'/f'{app}-local-trial.json'))
            if app=='codex':ev.append(evidence(MAT/'evidence/codex-local-finish.json'))
        if case=='32':
            note+=' 새 COM 변환본은 원문자 경고 FAIL 유지; 원본과 7쪽 픽셀 동일. 승인본 재패키징은 렌더 통과. 앱별 전체 경로는 후속 대기.'
            ev += [evidence(MAT/'evidence/conversion-native-render.json'),evidence(MAT/'evidence/conversion-pixel-comparison.json'),evidence(MAT/'evidence/repackaged-render.json')]
        history.append({'source':'local_materials_trials','state':state,'note':note})
    if case=='19':gate='권리 확인 후 릴리스 사본 필요';note+=' 이번에도 실제 패키지 시험 미실행, 최초 stale 표시 보존.'
    if state in ('behavior_verified','fixed_verified') and id not in materials:
        action='후속 동작 근거 확인 완료. 정식 독립 평가 점수는 변경하지 않음.'
    if state=='historical_pass':action='최초 합격 기록 보존. 최신 소스 전체 재시험으로 해석하지 않음.'
    if state=='excluded':action='현재 작업 범위에서 실행하지 않음.'
    assert state in labels,(id,state)
    rows.append({'id':id,'stage':old['stage'],'case':case,'title':old['case_title'],'target':app,'variant':variant,
                 'initial_verdict':old['status'],'initial_reason':old['reason'],'initial_scorer_problems':old['scorer_problems'],
                 'current_status':state,'current_label':labels[state],'observation':note,'remaining_condition':gate,
                 'next_action':action,'evidence_scope':scope,'new_independent_verdict':None,
                 'source_ids':materials.get(id,{}).get('sources',[]),'evidence':list({e['path']:e for e in ev}.values()),'history':history})

assert len(rows)==176 and len({r['id'] for r in rows})==176
assert len(follow)==115 and len(materials)==34
assert not mismatches, mismatches
counts=Counter(r['current_status'] for r in rows)
assert counts==Counter(historical_pass=56,fixed_verified=3,behavior_verified=36,partial=13,material_ready=26,blocked=29,pending=4,excluded=9),counts
assert Counter(r['initial_verdict'] for r in rows)=={'pass':56,'fail':3,'pending':2,'blocked':115}
source_unchanged=all(sha(ROOT/p)==digest for p,digest in before.items());assert source_unchanged
summary={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Integrated follow-up table; original independent verdicts unchanged; no tests newly run by this consolidation',
 'total_rows':176,'initial_verdict_counts':dict(Counter(r['initial_verdict'] for r in rows)),
 'current_counts':{k:counts[k] for k in labels},'initial_blocked_115_current_counts':dict(Counter(r['current_status'] for r in rows if r['initial_verdict']=='blocked')),
 'material_34_current_counts':dict(Counter(r['current_status'] for r in rows if r['id'] in materials)),
 'active_followup_rows':sum(r['current_status'] in ('partial','material_ready','blocked','pending') for r in rows),
 'new_independent_pass_promotions':0,'source_hashes':before,'source_documents_unchanged':source_unchanged,
 'evidence_hash_mismatches':mismatches,'additional_observations':{'conversion_render_fail_retained':True,'conversion_original_pixels_identical_pages':7,
 'codex_material_trial_timeout_retained':True,'codex_same_session_report_continuation':True},'release_decision':'hold'}
assert not OUT.exists() and not REPORT.exists(),'Use a new version instead of overwriting a published integration.'
save(OUT/'rows.json',rows);save(OUT/'summary.json',summary);save(OUT/'evidence-index.json',evidence_index)
def esc(s):return str(s).replace('|','/').replace('\n','<br>')
def link(e,label='근거'):return f"[{label}](../{e['path']})"
lines=['# 플러그인 보급 평가 통합표 — 2026. 9. 13.','','최초 독립 평가 176행에 결함 수정, 115행 후속 분류, 분류 정정, 기존 자료 활용 시험을 합쳤다. 이번 작업은 표 통합이며 새 시험 실행이나 독립 점수 재채점이 아니다. **이 표의 현재 상태를 최신 통합 기준으로 사용한다.** 이전 표/점수/원시 기록은 보존했다.','','## 현재 집계','','| 현재 상태 | 행 수 | 해석 |','|---|---:|---|']
for state in labels:lines.append(f'| {labels[state]} | {counts[state]} | {descriptions[state]} |')
lines+=['| 합계 | **176** | |','','최초 독립 점수는 **합격 56 / 실패 3 / 미실행 2 / 차단 115** 그대로다. 최초 실패 3행은 두 결함을 수정해 후속 확인했으며, 원래 실패 기록을 삭제하지 않았다. 과거 합격 56행은 최신 수정본 전체 재검증을 뜻하지 않는다.','','**후속 작업이 남은 행은 72개**(부분 확인 13 + 자료 확보·후속 대기 26 + 선행 조건 대기 29 + 미실행 4)다. 각 앱/조건별 시험 행의 수이며 서로 다른 결함 72개나 사람 승인 72회를 의미하지 않는다. 배포는 계속 보류다.','','## 변경이 반영된 방식','','- 최초 차단 115행 → 동작 확인 36, 부분 확인 13, 자료 확보·후속 대기 26, 선행 조건 대기 29, 미실행 2, 제외 9. 합계 115.','- 기존 66건 중 무표시 cwd 시험 2건은 미실행으로, 동료 교사 PC 1건은 제외로 정정했다.','- 자료 부족 34행 → 자료 확보·후속 대기 26, 기안문 계보 부분 확인 4, 행 부족/판독 없는 예산 초과의 실제 동작 확인 4로 반영했다. 34개를 일괄 합격시키지 않았다.','- `19 clean/sentinel_leak`은 최초부터 남았던 미실행 2행이다. 실제 릴리스 ZIP 및 시험이 없고 당시 stale 표시도 유지한다.','- 기존 학교 자료를 사용하는 로컬 후속 시험과 최초 가상학교/격리 설치 조건을 구분한다. 새 승인이나 사람 판독을 만들지 않았다.','- HWP 변환 원문자 경고 FAIL과 원본·변환본 7쪽 픽셀 동일 관측을 함께 보존했다. Codex 묶음 시험 300초 종료 및 같은 세션의 보고서 완성 이력도 보존했다.','','## 남은 실행 목록','','| 사례 | 대상·조건 | 다음 작업 |','|---|---|---|']
for case in sorted({r['case'] for r in rows}):
    pending=[r for r in rows if r['case']==case and r['current_status'] in ('partial','material_ready','blocked','pending')]
    if pending:lines.append('| '+case+' '+esc(pending[0]['title'])+' | '+str(len(pending))+'행 · '+esc(', '.join(sorted({r['variant'] for r in pending})))+' | '+esc(pending[0]['next_action'])+' |')
lines+=['','## 176행 상세','','“최초”는 원래 독립 판정, “현재”는 후속 근거/준비 상태다. 근거 링크는 최신 관측을 우선하며 전체 경로·SHA256·상태 이력은 JSON에 보관했다.','','| ID | 시험 | 최초 | 현재 | 최신 관측 | 다음 처리 | 근거 |','|---|---|---|---|---|---|---|']
for r in rows:
    e=r['evidence'][-1]
    lines.append('| '+r['id']+' | '+esc(r['title'])+' | '+r['initial_verdict']+' | '+r['current_label']+' | '+esc(r['observation'])+' | '+esc(r['next_action'])+' | '+link(e)+' |')
lines+=['','## 기계 판독·추적','','- [176행 JSON](../tmp/eval-integrated-20260913/rows.json)','- [집계·원본 보존 해시](../tmp/eval-integrated-20260913/summary.json)','- [근거 색인](../tmp/eval-integrated-20260913/evidence-index.json)','','Hwp_doc에서 평가표 176행을 통합 갱신했다. 코드·실무 원본·기존 평가 판정은 변경하지 않았다.']
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
assert all((REPORT.parent/s).is_file() for s in re.findall(r'\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8')))
assert all(sha(ROOT/p)==digest for p,digest in before.items())
save(OUT/'validation.json',{'unique_rows':176,'initial_blocked_rows':115,'material_rows':34,'total_current_counts':sum(counts.values()),
 'all_report_links_exist':True,'all_evidence_hashes_match':True,'source_documents_unchanged':True,'report_sha256':sha(REPORT)})
audit={'ts':summary['created_at'],'agent':'codex','action':'consolidate_evaluation_table','target':relative(REPORT),'result':'complete',
       'detail':{'rows':176,'current_counts':summary['current_counts'],'original_verdicts_preserved':True,'new_tests_run':False}}
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(audit,ensure_ascii=False)+'\n')
print(json.dumps({'report':relative(REPORT),'current_counts':summary['current_counts'],'remaining_rows':summary['active_followup_rows']},ensure_ascii=False,indent=2))
