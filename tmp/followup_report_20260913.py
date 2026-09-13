"""Produce a new implementation follow-up classification; original evals are immutable."""
import collections, copy, datetime, json, re
from pathlib import Path
import followup_20260913 as f

ROOT, RUN = f.ROOT, f.RUN
E = RUN / 'evidence'
OUT = RUN / 'classification'
OLD_CLASS = ROOT / '.claude/scratchpad/plugin-distribution/current-classification-20260913/rows.json'
rows = f.read(OLD_CLASS)
codex = 'codex-events-01a098b3-ef41-7713-8b40-6a4ae7071849.json'

def evidence(names):
    result=[]
    for name in names:
        path=E/name
        assert path.is_file(), path
        result.append({'path':path.relative_to(ROOT).as_posix(),'sha256':f.sha(path)})
    return result

new=[]
for old in rows:
    row=copy.deepcopy(old)
    case, app, variant = row['case'],row['target'],row['variant']
    category='시험자료·격리환경'; outcome='blocked'; note=row['remaining_condition']; names=[]
    if row['current_category'] in ('human','approval_flow','delivery_seed'):
        category='사람 확인'
    if row['current_category']=='release_pair':
        category='라이선스'; note='권리 게이트가 미통과여서 허가된 구·신 배포 패키지 쌍이 없음. 개발 설치 경로 변경·소유 훅 제거 시험은 통과했으나 앱의 정식 패키지 업데이트/제거 실적은 아님.'
        names=['relocation-observation.json','release-gate-final.json']
    if case=='20':
        category='라이선스'; note='현재 해시에서 권리 70, 개인정보 70, 의존성 조건 8건 미확인. 배포 금지.';names=['release-gate-final.json']
    if case=='21':
        category='이번 범위 제외';outcome='excluded';note='새 PC·새 계정·한글/보안모듈 부재의 새 설치 조건. 외부 PC 시험은 제외하며 현재 운영 PC의 Python·한글·보안모듈을 제거하지 않음. 현재 계정의 설치 경로 변경은 별도 통과.'
        names=['relocation-observation.json']
    if case=='28':
        note='현재 PC의 실제 COM·렌더는 작동함. 부재 상태는 운영 환경을 제거하지 않고 모의 오류 회귀로만 확인했으므로 실환경 부재 variant는 미검증.'
        names=['workflow-0-validate.json','final-test_hook_lifecycle.py.json']
    if case=='08':
        category='해소';outcome='behavior_verified';note='사용자의 기존양식 5종 승인 기록과 현재 등록 해시 확인. 5종 목록/등록 버전 prepare 및 원본 보존 대조 완료.'
        names=['08-approval-integrity.json','08-list.json']+[f'08-prepare-{i}.json' for i in range(5)]
    if case=='13':
        outcome='partial';note='앱의 새 시험 세션에서 로컬 지침/스킬 읽기 확인. 전역 메모리가 없는 정식 설치 패키지 조건을 충족한 독립 인수는 아님.';names=[codex,'claude-final-normal.json']
    if case=='15':
        if variant.startswith('mcp_'):
            if app=='codex':
                outcome='partial';note='현재 Codex Desktop 구현 세션에서 실제 kordoc patch_document/fill_form이 PreToolUse로 차단되고 원본 불변. 독립 설치 세션의 MCP 접두어/전체 설정 인수는 미완료.'
                names=['mcp-protection-current.json','mcp-read-current.json']
            else:
                note='이전 Claude kordoc 연결 시간 초과. 이번 Claude 훅 시험은 MCP를 격리해 실행했으므로 해당 두 도구의 실호출 인수는 미완료. Codex MCP 결과로 대체하지 않음.'
        else:
            category='해소';outcome='behavior_verified';note='실제 앱 도구의 사전 차단과 폐기용 원본/이동 대상 불변 확인.'
            if app=='codex': names=[codex,'codex-host-after-v4.json','extra-hook-before-v4.json']
            elif variant=='mixed': names=['claude-mixed.json','claude-mixed-after.json']
            elif variant in ('delete','move','junction_escape'):names=['claude-extra-run.json','claude-extra-after.json','extra-hook-before.json']
            else: names=['claude-final-normal.json','claude-final-normal-after.json']
            if app=='claude' and variant=='mixed': note+=' Claude Bash의 복합 명령으로 시험했으며 Codex의 원자적 apply_patch와 도구 형태는 다름.'
    if case=='16':
        if variant in ('read','copy_new','new_output') or (app=='claude' and variant=='outside_docs'):
            category='해소';outcome='behavior_verified';note='실제 도구의 정상 읽기·새 출력·복사 또는 별도 무표시 폴더 수정 성공. 원본은 유지됨.'
            names=[codex,'codex-host-after-v4.json'] if app=='codex' else ['claude-final-normal.json','claude-final-normal-after.json']
            if app=='claude' and variant=='copy_new': note+=' 앱 설명에서 정상 복사를 보호 공백으로 잘못 해석했으나 실제 동작은 명세대로 허용됨. 후속 시험 입력에서 허용 범위를 명확히 했고 보고에 이 한계를 보존함.'
        elif variant=='outside_docs':
            outcome='partial';note='올바른 형제 fixture로 재실행했으나 Codex workspace-write 자체 경계에서 거절. hwpdoc 오차단으로 판정하지 않음. 폐기용 비공문 경로를 포함한 앱 샌드박스 인수 환경 필요.';names=['codex-outside-unchanged.json','codex-outside-after.json']
        else:
            note='앱 cwd 자체가 무표시 폴더인 독립 훅 등록/신뢰 조건은 미실행. 표시된 workspace 내부 plain-project는 무표시 시험이 아니므로 성공·실패로 승격하지 않음.'
    if case=='17':
        if variant in ('python_missing','hook_error','utf8_path'):
            category='해소';outcome='behavior_verified'
            if variant=='utf8_path':
                note='실제 한글 경로 보호 이벤트 정상. 추가로 PowerShell의 한국어 오류 깨짐을 수정하고 두 앱 셸 회귀 + 실제 Claude 오류 출력 재확인.'
                names=[codex,'claude-extra-run.json','final-utf8-runtime-tests.json','claude-utf8-error.json','claude-utf8-after.json']
            else:
                note='프로세스별 runtime fixture에서 실제 앱 호출이 차단되고 보호 미검증으로 보고됨. PC의 Python은 제거하지 않음.'
                names=[f'bootstrap-{app}-{variant}.json',f'bootstrap-{app}-{variant}-after.json']
                if app=='claude' and variant=='hook_error':names+=['claude-utf8-error.json','claude-utf8-after.json']
        else:
            outcome='partial';note='Codex의 정상 /hooks 검토·신뢰 후 실제 차단은 관측함. 미신뢰 상태의 실제 쓰기/진단까지 포함한 독립 variant는 수행하지 않음. 전역 보안/신뢰 우회는 사용하지 않음.'
    if case=='18':
        if variant in ('invalid_output','unchanged'):
            category='해소';outcome='behavior_verified';note='깨진 HWPX의 실제 Stop 실패 및 이후 동일 파일 미변경 시 재검사 생략을 관측. 저장 상태 ok=false 유지, 전체 COM/내용/렌더 통과로 승격하지 않음.'
            names=[codex,'codex-outside-after.json'] if app=='codex' else ['claude-final-normal.json','claude-mixed.json']
        else:
            outcome='partial';note='2회 한도 단위시험 통과. 실제 앱은 파일 미변경 후 재검사를 생략했으므로 동일 단계가 2회 실패하는 별도 실앱 variant 완료로 보지 않음.'
            names=['final-test_hook_lifecycle.py.json','claude-final-normal.json',codex]
    if case=='27' and variant=='unknown':
        category='해소';outcome='behavior_verified';note='실제 앱에서 제출 방법을 질문하고 변형 A/B·승인·발송을 임의 확정하지 않음. 실제 완성된 W2 문서 실적은 아님.'
        names=[codex] if app=='codex' else ['claude-final-normal.json']
        if app=='claude':note+=' Claude는 이미 제공한 가상 학교 값도 재확인했으며, 불필요한 질문이라는 사용성 관측을 보존함.'
    row.update(followup_category=category,followup_outcome=outcome,followup_note=note,
               followup_evidence=evidence(names),formal_case_verdict='not_independently_reassessed')
    # Historical fields above remain as originally captured, not current approval status.
    new.append(row)

assert len(new)==115 and len({r['id'] for r in new})==115
counts=dict(collections.Counter(r['followup_category'] for r in new))
outcomes=dict(collections.Counter(r['followup_outcome'] for r in new))
freeze=f.read(RUN/'freeze.json');v4=f.read(RUN/'freeze-v4.json')
changed={name:{'tested_v4':digest,'current':f.sha(ROOT/name) if (ROOT/name).exists() else None}
         for name,digest in v4['source_files'].items() if not (ROOT/name).exists() or f.sha(ROOT/name)!=digest}
integrity={'original_matrix_unchanged':f.sha(f.OLD/'matrix.json')==freeze['initial_matrix_sha256'],
           'criteria_unchanged':f.files(ROOT/'evals/plugin_distribution')==freeze['criteria'],
           'registered_files_unchanged':all(f.sha(ROOT/name)==digest for name,digest in freeze['source_files'].items() if name.startswith('.hwpdoc/templates/')),
           'operational_templates_unchanged':all(f.sha(ROOT/name)==digest for name,digest in freeze['source_files'].items() if name.startswith('knowledge/templates/')),
           'changes_after_app_v4_snapshot':changed}
assert all(integrity[k] for k in ('original_matrix_unchanged','criteria_unchanged','registered_files_unchanged','operational_templates_unchanged'))
summary={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'implementation-led follow-up, not a new independent 176-row evaluation',
         'initial_115_category_counts':counts,'followup_outcome_counts':outcomes,'formal_pass_promotions':0,
         'original_score':{'pass':56,'fail':3,'pending':2,'blocked':115},'regression_tests':75,
         'original_three_failed_rows':{'04 long path':'fixed and CLI repro passed','12 W1 missing slots':'fixed and CLI repro passed','12 W2 missing slots':'fixed and CLI repro passed'},
         'full_workflow':'Five synthetic templates: 20 build/validate/status/deliver commands passed including actual serial Hancom COM',
         'release_decision':'hold; rights/privacy/dependency approvals missing','integrity':integrity}
f.save(OUT/'rows.json',new);f.save(OUT/'summary.json',summary)
f.save(RUN/'final-source-hashes.json',{name:f.sha(ROOT/name) for name in v4['source_files'] if (ROOT/name).is_file()})
lines=['# 최초 차단 115행의 구현 후속 분류','','기존 행과 최초 판정을 보존했다. 아래 결과는 구현자가 수집한 동작 근거이며 독립 평가 pass 승격이 아니다.','','| ID | 현재 분류 | 관측 | 남은 조건/근거 |','|---|---|---|---|']
for r in new:lines.append('| '+r['id']+' | '+r['followup_category']+' | '+r['followup_outcome']+' | '+r['followup_note'].replace('|','/')+' |')
(OUT/'rows.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
f.save(OUT/'evidence-index.json',{p.relative_to(ROOT).as_posix():f.sha(p) for p in E.glob('*.json')})
print(json.dumps(summary,ensure_ascii=False,indent=2))
