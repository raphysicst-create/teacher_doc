"""Refresh the follow-up ledger; preserve independent verdicts and prior snapshots."""
from pathlib import Path
from collections import Counter
import copy, datetime, hashlib, importlib.util, json, re

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / 'tmp/eval-integrated-20260913'
OUT = ROOT / 'tmp/eval-integrated-20260913-v2'
REPORT = ROOT / 'docs/플러그인-보급-평가통합표-2026-09-13.md'
assert not OUT.exists(), 'Do not overwrite an existing revision'
OUT.mkdir()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p, v): p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def rel(p): return p.relative_to(ROOT).as_posix()
previous_report = REPORT.read_bytes()
(OUT / 'previous-report.md').write_bytes(previous_report)
old_rows = read(PREV / 'rows.json')
rows = copy.deepcopy(old_rows)
by_id = {r['id']: r for r in rows}
labels = {'historical_pass':'과거 합격', 'fixed_verified':'수정 후 확인', 'behavior_verified':'동작 확인',
          'partial':'부분 확인', 'material_ready':'자료 확보·후속 대기', 'blocked':'선행 조건 대기', 'pending':'미실행', 'excluded':'범위 제외'}
active = {'partial','material_ready','blocked','pending'}
sources = {rel(p): sha(p) for p in PREV.glob('*.json')}
evidence_index = {}
historical_drift = []
for r in rows:
    for e in r['evidence']:
        p = ROOT / e['path']
        assert p.is_file(), p
        actual = sha(p)
        if actual != e['sha256']:
            historical_drift.append({'id':r['id'], **e, 'current_sha256':actual})
        sources[e['path']] = actual
        evidence_index[e['path']] = actual

def ev(path):
    p = ROOT / path
    assert p.is_file(), p
    h = sha(p)
    sources[path] = h
    evidence_index[path] = h
    return {'path':path, 'sha256':h}

R = 'tmp/remaining-20260913/'
W = 'tmp/approved-workflow-20260913/'
C = 'tmp/com-timeout-20260913/'
remaining_report = 'docs/플러그인-남은시험-실행결과-2026-09-13.md'
workflow_report = 'docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md'
com_report = 'docs/Codex-CLI-COM-시간초과-수정-2026-09-13.md'
cowork_report = 'docs/Claude-데스크톱-Cowork-확인-2026-09-13.md'
for path in [remaining_report, workflow_report, com_report, cowork_report,
             R+'summary.json', W+'summary.json', W+'user-approval.json',
             C+'acceptance.json', C+'actual-cli.json', C+'restricted-acceptance.json',
             'tmp/claude-desktop-check-20260913/cowork-result.json',
             'distribution/agpl-review-2026-09-13.md',
             'distribution/canine89-mit-permission-2026-09-13.json',
             'distribution/pymupdf-agpl-decision-2026-09-13.json']:
    ev(path)

changes = []
def update(id, state, note, action, paths, scope='current_pc_followup', gate=''):
    r = by_id[id]
    prior = r['current_status']
    r.update(current_status=state, current_label=labels[state], observation=note,
             next_action=action, remaining_condition=gate, evidence_scope=scope)
    r['history'].append({'source':'integration_v2', 'state':state, 'note':note})
    r['evidence'] += [ev(p) for p in paths]
    r['evidence'] = list({e['path']:e for e in r['evidence']}.values())
    changes.append({'id':id, 'from':prior, 'to':state, 'note':note})

done = '현재 PC의 해당 후속 동작 확인 완료. 최초 독립 점수와 격리 배포 인수는 별도.'
for app in ('claude','codex'):
    host = 'Claude Code CLI' if app == 'claude' else 'Codex Desktop'
    update(f'09--{app}--default','partial',
           f'{host}에서 trial-gianmun 매핑·8단계 준비·현재 검토 등록 후 W1/W2에 사용. 출처는 unconfirmed를 보존하고 실제 비교 렌더를 필수 실행했다. 새 네이티브 가통 등록 조건은 미완료.',
           '네이티브 출처가 확인된 가통으로 사례 09의 등록 조건을 확인.',
           [R+'summary.json', W+'summary.json', workflow_report], gate='네이티브 가통 등록 범위 미검증')
    for variant in ('internal_approval','notice_dispatch'):
        update(f'11--{app}--{variant}','partial',
               f'8건 기안문 계보 대조에 더해 {host}의 승인된 W1 기능 시험 계획/W2 시스템 제출 내부결재를 생성·검증·전달. 같은 베이스의 가통 발송 용도까지 확인한 것은 아님.',
               '같은 승인 베이스를 가통 발송 용도에도 연결하고 제목 굵기·여백·용도 선택을 확인.',
               [W+'summary.json', workflow_report], gate='복수 용도 중 가통 발송 미검증')
    update(f'16--{app}--no_marker','behavior_verified',
           ('Claude 실제 pre/post가 빈 결과를 반환하고 Edit 성공; 공문 표시 없는 cwd에서 오차단 없음.' if app=='claude' else
            'Codex 훅을 정상 신뢰한 무표시 cwd에서 실제 apply_patch 성공; 최초 미신뢰 호출과 분리해 판정.'),
           done, [R+f'evidence/{app}-'+('plain.json' if app=='claude' else 'plain-trusted.json'), remaining_report])
    update(f'18--{app}--twice_failed','behavior_verified',
           '실제 Stop에서 BROKEN_0 첫 차단→BROKEN_1 둘째 차단→BROKEN_2 자동 교정 중단 안내. 단계 실패를 유지했으며 저장된 ok=false는 통과로 바꾸지 않음.',
           done, [R+f'evidence/{app}-stop-limit.json', R+'summary.json', remaining_report])
    update(f'27--{app}--system','behavior_verified',
           f'{host}: 사용자 승인된 가상 시스템 제출 내부결재 W2를 생성→전체 검증(COM·비교 렌더 포함)→시험 폴더 전달. 복사 해시 일치, sent=false. p:7 28/27자 경고 유지. 최종 사람 평점·실제 제출은 별도.',
           done, [W+'user-approval.json', W+'summary.json', workflow_report])
    for variant in ('official_reply','email'):
        update(f'27--{app}--{variant}','material_ready',
               '가상 수신 원문과 검증된 W2 공통 경로 확보. 사용자 승인은 system 문안에 한정하며 이 제출 방식의 초안·확인·전체 흐름은 미실행.',
               '해당 제출 방식의 원문으로 초안을 제시하고 확인 후 생성·검증·시험 전달.',
               [W+'summary.json', workflow_report], gate='해당 분기 초안·실행 대기')
    update(f'29--{app}--copy_success','behavior_verified',
           f'{host}에서 승인 W1/W2 검토본 2건을 시험 폴더로 전달하고 HWPX·보고서 복사 해시 일치 확인. 실제 OneDrive 전송이나 사람 최종 평점은 아님.',
           done, [W+'summary.json', workflow_report])
    for variant in ('copy_collision','copy_twice_failed'):
        update(f'29--{app}--{variant}','behavior_verified',
               f'{host} 실제 호출: 외부 기존 HWPX 충돌로 두 번 exit 1, 세 번째 exit 2. 기존 파일·작업 문서·manifest·검증 이력 보존. 과거 SYNTHETIC_TEST_NOT_USER 입력을 재사용한 전달 처리 시험이다.',
               done, [R+f'{app}-marked/output/delivery-trial.json', remaining_report], scope='actual_host_synthetic_delivery_fixture')
    update(f'29--{app}--copy_partial','partial',
           '외부 복사 폴더 부재에서 로컬 검토본 보존, 폴더 복구 후 복사만 재시도 성공. 여러 전달 파일 중 일부만 복사된 중간 실패 조건을 따로 주입한 근거는 없음.',
           '일부 파일 복사 뒤 실패하는 조건을 구성해 복사만 재시도하고 기존 검증·파일 보존 확인.',
           [R+f'{app}-marked/output/delivery-trial.json', remaining_report], gate='일부 파일 복사 후 실패 분기 미검증')
    for variant in ('copy_off','draft_only'):
        update(f'29--{app}--{variant}','material_ready',
               '승인 W1/W2 작업과 실제 검증·전달 가능한 자료 확보. 복사 끄기 또는 미확인 초안 전달의 해당 분기는 아직 실행하지 않음.',
               '준비된 시험 작업 사본으로 해당 전달 분기를 실행하고 검증 상태·sent=false 보존 확인.',
               [W+'summary.json', workflow_report], gate='해당 분기 실행 대기')
    for variant in ('hwp_input','repackaged','fallback_absent'):
        state = 'material_ready' if variant == 'fallback_absent' else 'partial'
        update(f'32--{app}--{variant}',state,
               '후속 렌더 수정본: HWP→HWPX 7쪽 원본과 픽셀 동일, 원본 기인 ◯ 1개를 경고로 보존하며 PASS. 이전 FAIL 기록은 유지. 재패키징 사본도 비교 렌더 근거가 있으나 앱별 변환/재패키징/폴백 부재 전체 흐름은 미완료.',
               '해당 앱에서 지정한 입력·폴백 조건의 전체 흐름을 실행. 원본 기인 경고와 새 잔재 실패 구분 유지.',
               [R+'evidence/render-real-reference.json', R+'evidence/render-pixels.json', remaining_report], gate='앱별 해당 경로 미완료')

for variant in ('mcp_patch','mcp_fill'):
    update(f'15--claude--{variant}','behavior_verified',
           'Claude Code CLI 두 번째 좁힌 시험에서 kordoc patch_document/fill_form 실제 PreToolUse exit 2·deny 확인, 두 HWPX 사본 해시 불변. 첫 호출 생략·360초 종료는 실패 이력으로 보존.',
           done, [R+'evidence/claude-mcp-second.json', R+'evidence/claude-mcp-second-files.json', remaining_report])
update('17--codex--untrusted','behavior_verified',
       '실제 Codex에서 프로젝트 미신뢰 및 프로젝트 신뢰/훅 정의 미신뢰 조건 모두 쓰기 성공. 미신뢰 상태에서는 프로젝트 훅 보호를 주장할 수 없음을 확인했으며 정상 신뢰 후 차단 결과와 구분.',
       done, [R+'evidence/codex-untrusted.json', R+'evidence/codex-hook-untrusted.json', remaining_report])
update('17--claude--untrusted','partial',
       'Claude Code 미신뢰 진입에서 No, exit 선택을 실제 확인: exit 1, 모델/도구 턴 없음, 파일 불변. 쓰기 도구에 대한 훅 차단이나 보호 가능 여부의 모델 안내까지 시험한 결과는 아님.',
       '미신뢰 진입 거부 관측을 유지하고 호스트 허용 조건·보호 가능 안내의 남은 범위를 확인.',
       [R+'evidence/claude-untrusted-decline.json', remaining_report], gate='진입 거부 외 도구/안내 범위 미관측')
for variant in ('com_unavailable','render_unavailable'):
    update(f'28--cli--{variant}','partial',
           '독립 Codex CLI 기본 사용자 환경 COM·W1/W2 PDF 검사 통과. workspace-write 실제 제한 환경은 probe/Open/render가 HANCOM_RESTRICTED_CONTEXT로 1초 이내 실패·미확인 반환. 제한 모드 지원은 미완료. 렌더 도구 자체 부재와 build/validate/status/deliver 전체 전파는 별도.',
           '실제 불가 상태가 실행기 전체 보고·전달 금지까지 유지되는지 확인; 렌더 자체 부재는 COM 불가와 별도 시험.',
           [C+'acceptance.json', C+'restricted-acceptance.json', com_report], gate='전체 상태 전파/렌더 자체 부재 미검증')

# Recheck current file hashes without creating a release package.
spec = importlib.util.spec_from_file_location('release_check', ROOT/'scripts/build_distribution.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
for path in ('scripts/build_distribution.py','distribution/release-files.json','distribution/rights.pending.json','distribution/source-bundle.json'):
    ev(path)
release = module.check_release(read(ROOT/'distribution/release-files.json'), read(ROOT/'distribution/rights.pending.json'))
save(OUT/'release-gate.json', release)
issue_counts = Counter(i['reason'] for i in release['issues'])
release_note = 'Canine89 개인 MIT 허락과 무료 AGPL 선택·소스/고지 준비 완료. 현재 허용 목록 '+str(len(release['files']))+'파일의 게이트: '+', '.join(f'{k} {v}' for k,v in issue_counts.items())+'. 정식 패키지 미생성.'
update('20--cli--default','blocked',release_note,
       '현재 해시별 권리·개인정보와 나머지 의존성 조건 검토를 완료. MIT/AGPL 선택을 다시 요청하지 않음.',
       ['distribution/canine89-mit-permission-2026-09-13.json','distribution/pymupdf-agpl-decision-2026-09-13.json',rel(OUT/'release-gate.json')], gate='파일별 배포 검토 미완료')

counts = Counter(r['current_status'] for r in rows)
remaining = sum(counts[s] for s in active)
transitions = [c for c in changes if c['from'] != c['to']]
assert len(rows)==176 and len(by_id)==176
assert Counter(r['initial_verdict'] for r in rows)=={'pass':56,'fail':3,'pending':2,'blocked':115}
for old, new in zip(old_rows, rows):
    assert all(old[k]==new[k] for k in ('id','initial_verdict','initial_reason','initial_scorer_problems','new_independent_verdict'))
assert all(sha(ROOT/p)==h for p,h in sources.items())
summary = {'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'revision':2,
           'total_rows':176, 'initial_verdict_counts':dict(Counter(r['initial_verdict'] for r in rows)),
           'current_counts':dict(counts), 'active_followup_rows':remaining,
           'previous_active_followup_rows':72, 'status_transitions':transitions,
           'initial_blocked_115_current_counts':dict(Counter(r['current_status'] for r in rows if r['initial_verdict']=='blocked')),
           'new_independent_pass_promotions':0, 'new_app_tests_run':False,
           'release_gate_rechecked':True, 'release_issue_counts':dict(issue_counts), 'release_decision':'hold',
           'previous_report_sha256':hashlib.sha256(previous_report).hexdigest(),
           'historical_evidence_hash_drift':historical_drift, 'source_hashes':sources,
           'additional_environment_results':{'codex_desktop':'approved W1/W2 flow passed',
             'claude_code_cli':'approved W1/W2 flow passed; not Claude Desktop',
             'codex_cli_default':'COM/Open/PDF passed; not whole CLI workflow acceptance',
             'codex_cli_workspace_write':'COM unsupported, fail-fast observed',
             'claude_desktop_cowork':'no local MCP, COM connection absent; W1/W2 not run',
             'vscode':'current full workflow unverified', 'external_pc':'excluded'}}
save(OUT/'rows.json', rows); save(OUT/'summary.json',summary); save(OUT/'evidence-index.json',evidence_index)
def esc(s): return str(s).replace('|','/').replace('\n','<br>')
def link(path, label='근거'): return f'[{label}](../{path})'
lines = ['# 플러그인 보급 평가 통합표 — 2026. 9. 13. (2차 갱신)', '',
         '이 표를 최신 통합 기준으로 사용한다. 최초 독립 평가 176행의 판정은 그대로 두고 이후 실제 시험·사용자 결정·현재 배포 게이트를 반영했다. 이번에는 새 앱 시험이나 독립 재채점을 하지 않았다. 이전 통합 JSON과 '+link(rel(OUT/'previous-report.md'),'이전 표 사본')+'을 보존했다.', '',
         '## 현재 집계', '', '| 상태 | 이전 | 현재 |', '|---|---:|---:|']
previous_counts=Counter(r['current_status'] for r in old_rows)
for s, label in labels.items(): lines.append(f'| {label} | {previous_counts[s]} | {counts[s]} |')
lines += ['| 합계 | **176** | **176** |','',
          f'**후속 작업이 남은 행: 72 → {remaining}개.** 부분 확인·자료 확보·선행 조건 대기·미실행의 합계다. 서로 다른 결함이나 사람 승인 횟수가 아니다. 동작 확인은 해당 후속 시험의 범위이며 독립 인수 합격으로 승격하지 않는다. 과거 합격도 최신 코드 전체 재시험을 뜻하지 않는다.', '',
          '최초 독립 판정은 **합격 56 / 실패 3 / 미실행 2 / 차단 115**를 유지한다. 최초 실패 3행은 두 결함의 수정 재현 근거가 있으며 원래 기록을 삭제하지 않았다. 배포 판단은 **보류**다.', '',
          '## 이번에 반영한 결과', '',
          '- Claude Code CLI MCP 사전 차단, 두 앱 무표시 cwd, Stop 2회 실패 제한, Codex 미신뢰 훅 상태를 반영했다.',
          '- 승인된 W1 기능 시험 계획과 W2 시스템 제출 내부결재는 Codex Desktop·Claude Code CLI에서 생성→전체 검증→시험 폴더 전달을 마쳤다. W2 system 2행에 반영하고 W1 기안문은 별도 실적으로 기록했다. 일반/회신형 가통(23·24)과 W2 공문·메일 제출은 통과로 바꾸지 않았다.',
          '- 전달 성공·충돌·2회 실패 한도 6행을 동작 확인으로 반영했다. 폴더 부재 복구는 일부 파일 복사 뒤 실패와 달라 copy_partial은 부분 확인이다. 실제 OneDrive 전송·사람 최종 평점은 별도다.',
          '- 새 등록은 완료했으나 양식 출처 unconfirmed와 네이티브 가통 조건 차이를 유지한다. 기안문 W2의 문단 1자 초과 판독을 사례 26의 표 셀 초과 판독으로 전용하지 않았다.',
          '- HWP 변환 렌더 오탐 수정 후 PASS와 원본 기인 경고, 7쪽 픽셀 동일 결과를 반영했다. 과거 FAIL과 앱별 전체 경로 미완료는 보존했다.', '',
          '## 환경별 범위 — 176행과 별도 표시', '',
          '| 환경 | 확인한 범위 | 남은 범위 |','|---|---|---|',
          '| Codex Desktop | 승인 W1·W2 생성·전체 검증·시험 전달 | 다른 업무 분기·배포 인수 |',
          '| Claude Code CLI 2.1.270 | 승인 W1·W2 생성·전체 검증·시험 전달 | Claude Desktop 결과와 구분 |',
          '| 독립 Codex CLI 0.147.0 기본 사용자 환경 | W1·W2 COM 열기·PDF 비교 통과 | 독립 CLI 전체 흐름 인수와 구분 |',
          '| Codex CLI workspace-write | COM 불가를 1초 이내 실패·미확인으로 반환 | 제한 모드 COM 지원 미완료 |',
          '| Claude Desktop Cowork 1.52386.3 | 실제 앱에서 localMcpServers=[] 확인 | Windows COM 연결 없음·W1/W2 미실행 |',
          '| VS Code | 이번 최신 전체 흐름 근거 없음 | 현재 소스로 별도 인수 필요 |',
          '| 외부 PC | 사용자 요청으로 제외 | 현재 작업에서 시험하지 않음 |', '',
          'Claude Desktop·VS Code 상태는 기존 target 이름에 끼워 넣어 176행의 수를 바꾸지 않았다. 후속 자료의 claude는 실제 호스트가 Claude Code CLI임을 명시한다.', '',
          link(workflow_report,'승인 후 흐름 보고서')+' · '+link(com_report,'CLI COM 보고서')+' · '+link(cowork_report,'Claude 앱 보고서'), '',
          '## 배포 검토', '', release_note, '',
          '파일별 권리/개인정보 미확인 수는 같은 파일에 대한 서로 다른 검토 항목이다. 고지 동봉이나 MIT 허락을 기존 파일 전체의 현재 해시 검토 완료로 간주하지 않는다. 실제 패키지 생성·설치·업데이트·제거 시험은 남아 있다. '+link(rel(OUT/'release-gate.json'),'현재 게이트 원시 결과'), '',
          '## 남은 실행 목록', '', '| 사례 | 남은 행 | 다음 처리 |','|---|---:|---|']
for case in sorted({r['case'] for r in rows}):
    pending=[r for r in rows if r['case']==case and r['current_status'] in active]
    if pending:
        actions=list(dict.fromkeys(r['next_action'] for r in pending))
        lines.append(f"| {case} {esc(pending[0]['title'])} | {len(pending)} | {esc(' / '.join(actions))} |")
lines += ['', '## 상태 변경 목록', '', '| ID | 이전 | 현재 |','|---|---|---|']
for c in transitions: lines.append(f"| {c['id']} | {labels[c['from']]} | {labels[c['to']]} |")
lines += ['', '## 176행 상세', '', '최초 판정과 현재 후속 상태를 분리한다. 전체 근거 해시와 변경 이력은 JSON에 보관했다.', '',
          '| ID | 시험 | 최초 | 현재 | 최신 관측 | 다음 처리 | 근거 |','|---|---|---|---|---|---|---|']
for r in rows:
    lines.append('| '+' | '.join([r['id'],esc(r['title']),r['initial_verdict'],r['current_label'],esc(r['observation']),esc(r['next_action']),link(r['evidence'][-1]['path'])])+' |')
lines += ['', '## 기계 판독·검증', '',
          '- '+link(rel(OUT/'rows.json'),'176행 JSON'), '- '+link(rel(OUT/'summary.json'),'집계·원본 해시·환경 범위'),
          '- '+link(rel(OUT/'evidence-index.json'),'근거 색인'), '- '+link(rel(OUT/'validation.json'),'무결성 검증'), '',
          'teacher_doc에서 평가표와 후속 집계를 최신화했다. 구현 코드·실무 원본·최초 평가 판정은 변경하지 않았다.']
assert not historical_drift, historical_drift
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
save(OUT/'validation.json',{'unique_rows':176,'current_count_sum':sum(counts.values()),'active_followup_rows':remaining,
                          'initial_verdicts_unchanged':True,'old_integration_json_unchanged':True,
                          'all_evidence_hashes_match':True,'historical_evidence_hash_drift':historical_drift,
                          'source_documents_unchanged':True,'previous_report_preserved':True,'new_app_tests_run':False,
                          'release_gate_rechecked':True,'report_sha256':sha(REPORT)})
links=re.findall(r'\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8'))
assert all((REPORT.parent/p).is_file() for p in links)
assert all(sha(ROOT/p)==h for p,h in sources.items())
assert (OUT/'previous-report.md').read_bytes()==previous_report
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as stream:
    stream.write(json.dumps({'ts':summary['created_at'],'agent':'codex','action':'refresh_evaluation_table',
                            'target':rel(REPORT),'result':'complete','detail':{'revision':2,'rows':176,
                            'active_followup_rows':remaining,'initial_verdicts_preserved':True,
                            'new_app_tests_run':False,'release_gate_rechecked':True}},ensure_ascii=False)+'\n')
print(json.dumps({'report':rel(REPORT),'counts':dict(counts),'remaining_rows':remaining,
                  'transitions':len(transitions),'release_issues':dict(issue_counts)},ensure_ascii=False,indent=2))
