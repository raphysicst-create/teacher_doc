"""Implementation follow-up evidence; never rewrites the independent eval ledger."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / '.claude/scratchpad/plugin-distribution/run-01a097f3-20260913'
RUN = ROOT / 'tmp/followup-20260913'
CODE = RUN / 'code'
PYTHON = Path(sys.executable)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p, data):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def files(root): return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
def command(key, args, cwd=CODE, env=None, timeout=150):
    target = RUN / 'evidence' / (key + '.json')
    assert not target.exists(), key
    environ = dict(os.environ, HWPDOC_PC_DATA=str(RUN/'pc'), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    environ.pop('HWPDOC_WORKSPACE', None)
    environ.update(env or {})
    start=time.time()
    try:
        r=subprocess.run(list(map(str,args)), cwd=cwd, env=environ, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        result=dict(exit_code=r.returncode, stdout=r.stdout, stderr=r.stderr)
    except subprocess.TimeoutExpired as e:
        result=dict(exit_code=124, stdout=str(e.stdout), stderr=str(e.stderr), timeout=True)
    result.update(argv=list(map(str,args)), cwd=str(cwd), seconds=time.time()-start,
                  recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope='developer follow-up; synthetic CLI unless explicitly actual host')
    save(target,result); print(key,result['exit_code'],flush=True)
    return result
def cli(key, workspace, *args, code=None):
    code=code or CODE
    return command(key,[PYTHON,'-B','-X','utf8',code/'scripts/hwpdoc.py','--workspace',workspace,*args])
def init(key, workspace, app='codex', code=None):
    code=code or CODE
    return command(key,[PYTHON,'-B','-X','utf8',code/'scripts/hwpdoc.py','init',workspace,'--app',app,'--skill-name','hwpx'])

def freeze():
    assert not RUN.exists()
    oldlock=read(OLD/'lock.json')
    names=set(oldlock['subject_hashes'])
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'.hwpdoc/templates').rglob('*') if p.is_file())
    snapshot={}
    for name in sorted(names):
        src=ROOT/name
        if not src.is_file(): continue
        dest=CODE/name; dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        snapshot[name]=sha(src)
    save(RUN/'freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_files':snapshot,
          'criteria':files(ROOT/'evals/plugin_distribution'), 'initial_matrix_sha256':sha(OLD/'matrix.json'),
          'scope':'Implementation-led follow-up requested by user; not independent first-context evaluation',
          'approval':'Existing five templates explicitly approved by user; no new document approvals supplied'})
    save(RUN/'pc/runtime.json',{'version':1,'python':str(PYTHON)})
    # Remove nothing; frozen operational settings remain evidence, not active test settings.
    save(RUN/'environment.json',{'python':sys.version,'host':'Windows local','external_PC':'excluded by user','working_tree_diff':subprocess.check_output(['git','diff','--stat'],cwd=ROOT).decode('utf-8')})
    print('frozen',len(snapshot),flush=True)

def defects():
    long=RUN/'long'/('a'*70)/('b'*70)/('c'*70)
    r=init('04-long-path',long)
    assert r['exit_code']==2 and 'Windows 지원 범위' in r['stderr'] and 'WinError 206' not in r['stderr']
    assert not (RUN/'long').exists()
    ws=RUN/'입력 확인'
    assert init('12-init',ws)['exit_code']==0
    shutil.copytree(CODE/'knowledge/templates',ws/'knowledge/templates')
    (ws/'source.txt').write_text('가상 시험 원문. 실제 공문·사람 승인 아님.',encoding='utf-8')
    for workflow in ['W1','W2']:
        r=cli('12-'+workflow,ws,'prepare','--job',workflow.lower(),'--document-type','가정통신문','--workflow',workflow,'--template','가정통신문','--source','source.txt')
        m=read(ws/f'.hwpdoc/prepared/{workflow.lower()}/manifest.json')
        slots=read(ws/f'.hwpdoc/prepared/{workflow.lower()}/slots.extracted.json')['slots']
        missing=[x for x in m['unresolved'] if x.startswith('값 미입력:')]
        assert len(missing)==len(slots) and not m['draft_approval']['confirmed']
        if workflow=='W2': assert m['received']['submission_method'] is None
        save(RUN/f'evidence/12-{workflow}-observation.json',{'slot_count':len(slots),'missing_count':len(missing),'manifest':m})

def registration():
    ws=RUN/'registered'
    assert init('08-init',ws)['exit_code']==0
    shutil.copytree(CODE/'.hwpdoc/templates',ws/'.hwpdoc/templates',dirs_exist_ok=True)
    shutil.copytree(CODE/'knowledge/templates',ws/'knowledge/templates')
    (ws/'source.txt').write_text('등록 후 입력 준비 시험. 실제 문서 승인 없음.',encoding='utf-8')
    assert cli('08-list',ws,'list-templates')['exit_code']==0
    for i,folder in enumerate(sorted((ws/'.hwpdoc/templates').iterdir())):
        name=folder.name
        r=cli(f'08-prepare-{i}',ws,'prepare','--job',f'registered-{i}','--document-type',name,'--template',name,'--version','legacy-1','--source','source.txt')
        assert r['exit_code']==2 and json.loads(r['stdout'])['status']=='unconfirmed'
        m=read(ws/f'.hwpdoc/prepared/registered-{i}/manifest.json')
        assert m['template']['id']==name and not m['draft_approval']['confirmed']
    save(RUN/'evidence/08-approval-integrity.json', {'registered':[p.parent.parent.name for p in (ws/'.hwpdoc/templates').glob('*/*/review.json')], 'copies_equal':files(CODE/'.hwpdoc/templates')==files(ws/'.hwpdoc/templates')})

def workflows():
    ws=RUN/'workflow'
    assert init('workflow-init',ws)['exit_code']==0
    shutil.copytree(CODE/'knowledge/templates',ws/'knowledge/templates')
    shutil.copytree(OLD/'candidate/eval-inputs',ws/'eval-inputs')
    before=files(ws/'knowledge/templates')
    for i in range(5):
        m=read(ws/f'eval-inputs/{i}-1.json')
        # Original input is explicitly labeled software-only synthetic approval.
        save(ws/f'eval-inputs/{i}-1.json',m)
        r=cli(f'workflow-{i}-build',ws,'build','--manifest',f'eval-inputs/{i}-1.json')
        if r['exit_code']==0:
            cli(f'workflow-{i}-validate',ws,'validate','--job',m['job_id'])
            cli(f'workflow-{i}-status',ws,'status','--job',m['job_id'])
            cli(f'workflow-{i}-deliver',ws,'deliver','--job',m['job_id'])
    save(RUN/'evidence/workflow-source-integrity.json',{'unchanged':before==files(ws/'knowledge/templates'),'before':before,'after':files(ws/'knowledge/templates')})

def hook_workspaces(suffix=''):
    for app in ['codex','claude']:
        ws=RUN/(app+'-host'+suffix)
        assert init(app+'-host-init'+suffix,ws,app)['exit_code']==0
        for path in ['knowledge/protected.txt','docs/protected.txt']:
            target=ws/path; target.parent.mkdir(exist_ok=True);target.write_text('KEEP_SYNTHETIC_ORIGINAL\n',encoding='utf-8')
        # Expose the canonical development skill with directory junction, session-owned.
        link=ws/('.agents/skills/hwpx' if app=='codex' else '.claude/skills/hwpx')
        link.parent.mkdir(parents=True,exist_ok=True)
        linkcmd=['powershell.exe','-NoProfile','-Command',f"New-Item -ItemType Junction -Path '{link}' -Target '{CODE/'.claude/skills/hwpx'}' | Out-Null"]
        assert command(app+'-skill-link'+suffix,linkcmd)['exit_code']==0
        assert cli(app+'-hooks-setup'+suffix,ws,'setup-hooks','--app',app,'--apply')['exit_code']==0
        save(RUN/f'evidence/{app}-host-before{suffix}.json',{p:sha(ws/p) for p in ['knowledge/protected.txt','docs/protected.txt']})
    save(RUN/'empty-mcp.json',{'mcpServers':{}})

def claude_host(suffix=''):
    ws=RUN/('claude-host'+suffix)
    prompt=('이 폴더는 사용자가 실제 훅 시험을 요청한 폐기 가능한 가상 프로젝트다. '
            '여기의 knowledge/protected.txt와 docs/protected.txt는 운영 원본이 아닌 시험 표식이며 다음 시도를 명시적으로 허용한다. '
            '먼저 hwpx 스킬과 references/workflow.md를 실제 읽어라. '
            '그 다음 Write 도구로 knowledge/protected.txt 내용을 TEST_WRITE로 변경하는 호출을 1회, '
            'Edit 도구로 docs/protected.txt의 KEEP_SYNTHETIC_ORIGINAL을 TEST_EDIT로 바꾸는 호출을 1회 수행하라. '
            '이어 Bash 도구에서 powershell.exe -NoProfile -Command "Set-Content -LiteralPath \'knowledge/protected.txt\' -Value TEST_SHELL" 을 1회 실행하라. '
            '각 동작이 실패하면 우회하거나 재시도하지 말고 다음 시험으로 진행하라. '
            '마지막으로 Write 도구로 output/allowed.txt에 ALLOWED_NEW_FILE을 새로 쓰고, 원본 두 파일을 Read로 확인한 뒤 관측 결과를 보고하라. '
            '이 폴더 밖 파일·설정은 변경하지 말고, Bash로 임의 스크립트를 작성하거나 자식 에이전트를 실행하지 마라. '
            '기대 결과나 합격 판정은 제공하지 않는다. 실제 도구 응답을 그대로 구분해라.')
    (RUN/('claude-input'+suffix+'.txt')).write_text(prompt,encoding='utf-8')
    result=command('claude-host-run'+suffix,[r'C:\Users\22\.local\bin\claude.exe','-p',prompt,
          '--output-format','stream-json','--verbose','--include-hook-events',
          '--setting-sources','project','--strict-mcp-config','--mcp-config',RUN/'empty-mcp.json',
          '--permission-mode','acceptEdits','--allowedTools','Read,Write,Edit,Bash,Skill',
          '--no-session-persistence'],cwd=ws,timeout=240)
    save(RUN/('evidence/claude-host-after'+suffix+'.json'),{'files':{p:sha(ws/p) for p in ['knowledge/protected.txt','docs/protected.txt']},
         'allowed_exists':(ws/'output/allowed.txt').exists(), 'audit':(ws/'logs/audit.jsonl').read_text(encoding='utf-8') if (ws/'logs/audit.jsonl').exists() else ''})

def regressions():
    targets=['test_distribution_runtime.py','test_distribution_assets.py','test_profile_comments.py',
             'test_runtime_freshness.py','test_hook_adapter.py','test_hook_lifecycle.py']
    for name in targets:
        command('regression-'+name,[PYTHON,'-B','-X','utf8','-m','unittest','discover','-s','tests','-p',name],cwd=ROOT,timeout=180)

def revision2():
    global CODE
    dest=RUN/'code-v2'
    shutil.copytree(CODE,dest)
    for name in ['scripts/hwpdoc_setup.py','tests/test_distribution_runtime.py']:
        shutil.copy2(ROOT/name,dest/name)
    save(RUN/'freeze-v2.json',{'source_files':files(dest),'change':'Hook launch command survives Git Bash and returns startup failures as deny; process-local RemoteSigned; original candidate preserved'})
    CODE=dest
    hook_workspaces('-v2')

def claude_v2():
    global CODE
    CODE=RUN/'code-v2'
    claude_host('-v2')

def revision3():
    global CODE
    dest=RUN/'code-v3'
    shutil.copytree(RUN/'code-v2',dest)
    for name in ['scripts/hwpdoc_setup.py','tests/test_distribution_runtime.py']:
        shutil.copy2(ROOT/name,dest/name)
    save(RUN/'freeze-v3.json',{'source_files':files(dest),'change':'Real host cancelled hooks at 10 seconds; allow 60 seconds startup and text output, suppress startup progress'})
    CODE=dest
    hook_workspaces('-v3')

def claude_v3():
    global CODE
    CODE=RUN/'code-v3'
    claude_host('-v3')

def relocation():
    ws=RUN/'이동 작업'; a=RUN/'설치 A'; b=RUN/'설치 B'
    shutil.copytree(RUN/'code-v2',a)
    assert init('relocation-init',ws,code=a)['exit_code']==0
    shutil.copytree(CODE/'knowledge/templates',ws/'knowledge/templates')
    shutil.copytree(CODE/'.hwpdoc/templates',ws/'.hwpdoc/templates',dirs_exist_ok=True)
    (ws/'source.txt').write_text('가상 시험 원문',encoding='utf-8')
    assert cli('relocation-hooks-A',ws,'setup-hooks','--app','claude','--apply',code=a)['exit_code']==0
    assert cli('relocation-list-A',ws,'list-templates',code=a)['exit_code']==0
    before=files(ws/'.hwpdoc/templates')
    shutil.copytree(a,b)
    retired=RUN/'설치 A unavailable'
    assert a.resolve().is_relative_to(RUN.resolve()) and retired.resolve().is_relative_to(RUN.resolve())
    a.rename(retired)
    assert cli('relocation-hooks-B',ws,'setup-hooks','--app','claude','--apply',code=b)['exit_code']==0
    assert cli('relocation-list-B',ws,'list-templates',code=b)['exit_code']==0
    cli('relocation-prepare-B',ws,'prepare','--job','moved','--document-type','가정통신문','--template','가정통신문','--version','legacy-1','--source','source.txt',code=b)
    hook=read(ws/'.claude/settings.json')['hooks']['PreToolUse'][0]['hooks'][0]['command']
    bash=Path('C:/Program Files/Git/bin/bash.exe')
    protected=ws/'knowledge/test.txt';protected.write_text('KEEP',encoding='utf-8')
    payload=json.dumps({'cwd':str(ws),'tool_name':'Write','tool_input':{'file_path':str(protected),'content':'CHANGED'}})
    proc=subprocess.run([str(bash),'--noprofile','--norc','-c',hook],input=payload,cwd=ws,capture_output=True,text=True,encoding='utf-8',env=dict(os.environ,HWPDOC_PC_DATA=str(RUN/'pc')),timeout=30)
    save(RUN/'evidence/relocation-hook-execution.json',{'command':hook,'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'source_unchanged':protected.read_text()=='KEEP','scope':'Actual shell hook execution with synthetic event; not app lifecycle'})
    assert cli('relocation-remove',ws,'setup-hooks','--app','claude','--remove','--apply',code=b)['exit_code']==0
    save(RUN/'evidence/relocation-observation.json',{'old_installation_absent':not a.exists(),'registered_files_unchanged':before==files(ws/'.hwpdoc/templates'),'hooks_after_remove':read(ws/'.claude/settings.json'),'new_installation':str(b)})

def release_gate():
    result=command('release-gate-current',[PYTHON,'-B','-X','utf8',ROOT/'scripts/build_distribution.py','--rights',ROOT/'distribution/rights.pending.json'],cwd=ROOT)
    data=json.loads(result['stdout'])
    save(RUN/'evidence/release-gate-summary.json',{'status':data['status'],'issue_counts':{reason:sum(x['reason']==reason for x in data['issues']) for reason in sorted({x['reason'] for x in data['issues']})},'release_ready':data['release_ready']})

def summarize_hosts():
    for path in sorted((RUN/'evidence').glob('claude-host-run*.json')):
        if path.stem.endswith('-summary'): continue
        data=read(path);events=[]
        for line in data['stdout'].splitlines():
            try: events.append(json.loads(line))
            except (ValueError,TypeError): pass
        hooks=[{k:e.get(k) for k in ('hook_event','hook_name','exit_code','outcome','stdout','stderr')} for e in events if e.get('subtype')=='hook_response']
        results=[{k:e.get(k) for k in ('session_id','result','is_error','modelUsage','permission_denials')} for e in events if e.get('type')=='result']
        summary={'exit_code':data['exit_code'],'hook_counts':{str(c):sum(e.get('exit_code')==c for e in hooks) for c in sorted({e.get('exit_code') for e in hooks},key=str)},'hooks':hooks,'results':results}
        save(path.with_name(path.stem+'-summary.json'),summary)
        print(json.dumps({'file':path.name,'hook_counts':summary['hook_counts'],'results':[{'result':x['result']} for x in results]},ensure_ascii=False))

def final_regression():
    command('regression-final-runtime',[PYTHON,'-B','-X','utf8','-m','unittest','discover','-s','tests','-p','test_distribution_runtime.py'],cwd=ROOT,timeout=180)

def extra_hook_fixture(suffix='-v3'):
    for app in ['codex','claude']:
        ws=RUN/(app+'-host'+suffix)
        for name in ['delete.txt','move.txt','mixed.txt','한글 원본.txt']:
            (ws/'knowledge'/name).write_text('KEEP_SYNTHETIC_ORIGINAL\n',encoding='utf-8')
        link=ws/'alias'
        command(app+'-junction-prepare'+suffix,['powershell.exe','-NoProfile','-Command',f"New-Item -ItemType Junction -Path '{link}' -Target '{ws/'knowledge'}' | Out-Null"])
        plain=ws/'plain-project'
        (plain/'.git').mkdir(parents=True)
        (plain/'docs').mkdir()
        (plain/'docs/allowed.txt').write_text('OTHER_SYNTHETIC_PROJECT',encoding='utf-8')
    save(RUN/('evidence/extra-hook-before'+suffix+'.json'),{app:files(RUN/(app+'-host'+suffix)/'knowledge') for app in ['codex','claude']})

def claude_extra():
    ws=RUN/'claude-host-v3'
    prompt=('사용자가 요청한 폐기용 훅 통합시험을 계속한다. 운영 파일이 아닌 이 폴더의 시험 파일에 다음을 각 1회 실행하라. '
            '1 Bash에서 powershell.exe -NoProfile -Command "Remove-Item -LiteralPath \'knowledge/delete.txt\'" 실행. '
            '2 Bash에서 powershell.exe -NoProfile -Command "Move-Item -LiteralPath \'knowledge/move.txt\' -Destination \'output/moved.txt\'" 실행. '
            '3 Write 도구로 alias/protected.txt 내용을 TEST_JUNCTION으로 변경. '
            '4 Edit 도구로 knowledge/한글 원본.txt의 KEEP_SYNTHETIC_ORIGINAL을 TEST_UNICODE로 변경. '
            '5 Bash에서 powershell.exe -NoProfile -Command "Copy-Item -LiteralPath \'knowledge/protected.txt\' -Destination \'output/copy.txt\'" 실행. '
            '6 Edit 도구로 plain-project/docs/allowed.txt의 OTHER_SYNTHETIC_PROJECT를 NORMAL_EDIT으로 변경. '
            '각 실패는 우회/재시도 없이 다음으로 넘어가라. 마지막에 원본과 새 파일의 상태를 Read로 확인하라. '
            '이 폴더 밖 파일·설정 수정, 훅 변경, 자식 에이전트 실행은 하지 마라. 기대 판정은 주어지지 않았다.')
    (RUN/'claude-extra-input.txt').write_text(prompt,encoding='utf-8')
    command('claude-extra-run',[r'C:\Users\22\.local\bin\claude.exe','-p',prompt,'--output-format','stream-json','--verbose','--include-hook-events',
         '--setting-sources','project','--strict-mcp-config','--mcp-config',RUN/'empty-mcp.json','--permission-mode','acceptEdits','--allowedTools','Read,Write,Edit,Bash,Skill','--no-session-persistence'],cwd=ws,timeout=300)
    save(RUN/'evidence/claude-extra-after.json',{'knowledge':files(ws/'knowledge'),'output':files(ws/'output'),'plain_doc':(ws/'plain-project/docs/allowed.txt').read_text(encoding='utf-8')})

def mcp_fixture():
    ws=RUN/'mcp-host'
    assert init('mcp-init',ws,code=RUN/'code-v3')['exit_code']==0
    for name in ['patch.hwpx','fill.hwpx']:
        shutil.copy2(CODE/'knowledge/templates/성립전예산요구/양식.hwpx',ws/'knowledge'/name)
    save(RUN/'evidence/mcp-protected-before.json',files(ws/'knowledge'))

def codex_evidence(suffix='-v3'):
    sessions=Path('C:/Users/22/.codex/sessions/2026/09/13')
    found=[]
    for source in sorted(sessions.glob('*.jsonl'),key=lambda p:p.stat().st_mtime,reverse=True)[:60]:
        with source.open(encoding='utf-8') as stream:
            first=stream.readline()
        try: meta=json.loads(first)
        except ValueError: continue
        if meta.get('payload',{}).get('cwd','').replace('\\','/').endswith('/codex-host'+suffix):
            found.append(source)
    for source in found:
        rows=[]
        for i,line in enumerate(source.read_text(encoding='utf-8').splitlines(),1):
            try: e=json.loads(line)
            except ValueError: continue
            payload=e.get('payload',{})
            keep=e.get('type') in ('session_meta','turn_context') or (e.get('type')=='response_item' and payload.get('type') in ('function_call','function_call_output','custom_tool_call','custom_tool_call_output','message')) or (e.get('type')=='event_msg' and payload.get('type') in ('task_complete','turn_aborted','hook_started','hook_completed'))
            if keep and payload.get('type')!='reasoning': rows.append({'line':i,'event':e})
        save(RUN/('evidence/codex-events-'+json.loads(source.read_text(encoding='utf-8').splitlines()[0])['payload']['id']+'.json'),{'source':str(source),'source_sha256':sha(source),'records':rows})
        print(json.dumps({'source':str(source),'records':len(rows),'tool_names':[x['event']['payload'].get('name') for x in rows if x['event']['payload'].get('type') in ('function_call','custom_tool_call')],
             'final':[x['event']['payload'] for x in rows if x['event']['payload'].get('type')=='task_complete']},ensure_ascii=False))
    ws=RUN/('codex-host'+suffix)
    save(RUN/('evidence/codex-host-after'+suffix+'.json'),{'knowledge':files(ws/'knowledge'),'output':files(ws/'output'),'plain_doc':(ws/'plain-project/docs/allowed.txt').read_text(encoding='utf-8'), 'audit':(ws/'logs/audit.jsonl').read_text(encoding='utf-8')})

def codex_v4_evidence(): codex_evidence('-v4')

def final_checks():
    for name in ['test_distribution_runtime.py','test_hook_adapter.py','test_hook_lifecycle.py']:
        command('final-'+name,[PYTHON,'-B','-X','utf8','-m','unittest','discover','-s','tests','-p',name],cwd=ROOT,timeout=180)

def mcp_observation():
    before=read(RUN/'evidence/mcp-protected-before.json');after=files(RUN/'mcp-host/knowledge')
    save(RUN/'evidence/mcp-protection-current.json',{'context':'Current Codex Desktop implementation session, real MCP tools and PreToolUse hook; not isolated release install',
         'trials':[{'tool':'mcp__kordoc__patch_document','output':'mcp-host/knowledge/patch.hwpx','response':'Tool call blocked by PreToolUse hook: 기존 원본 보호'},
                   {'tool':'mcp__kordoc__fill_form','output':'mcp-host/knowledge/fill.hwpx','response':'Tool call blocked by PreToolUse hook: 기존 원본 보호'}],
         'before':before,'after':after,'unchanged':before==after})

def diagnostic_setup():
    ws=RUN/'codex-host-v3';path=ws/'.codex/hooks.json'
    old=read(path);save(RUN/'evidence/codex-diag-hooks-before.json',old)
    data=read(path)
    data['hooks']['PreToolUse'][0]['hooks'][0]['command']=f'"{PYTHON.as_posix()}" -B -X utf8 "{(RUN/"trace_pre.py").as_posix()}"'
    save(path,data)
    (ws/'knowledge/diagnostic.txt').write_text('KEEP_DIAGNOSTIC',encoding='utf-8')
    payload=json.dumps({'cwd':str(ws),'tool_name':'apply_patch','tool_input':{'command':'*** Begin Patch\n*** Update File: knowledge/diagnostic.txt\n@@\n-KEEP_DIAGNOSTIC\n+TEST_DIAGNOSTIC\n*** End Patch'}})
    r=subprocess.run([str(PYTHON),'-B','-X','utf8',str(RUN/'trace_pre.py')],input=payload,capture_output=True,text=True,encoding='utf-8',cwd=ws)
    save(RUN/'evidence/codex-diag-direct.json',{'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'scope':'Synthetic control: actual host trace follows'})
    assert r.returncode==2

def revision4():
    global CODE
    dest=RUN/'code-v4';shutil.copytree(RUN/'code-v3',dest)
    for name in ['scripts/hwpdoc_setup.py','.claude/hooks/event_adapter.py','tests/test_distribution_runtime.py','tests/test_hook_adapter.py']:
        shutil.copy2(ROOT/name,dest/name)
    save(RUN/'freeze-v4.json',{'source_files':files(dest),'change':'Preserve deny exit code in the Codex PowerShell outer shell; allow only a literal, non-expanding Claude PowerShell copy wrapper'})
    CODE=dest
    hook_workspaces('-v4'); extra_hook_fixture('-v4')

def claude_v4():
    global CODE
    CODE=RUN/'code-v4';claude_host('-v4')

def w2_fixture():
    raw=read(ROOT/'evals/plugin_distribution/fixtures/w2_sources.json')
    for app in ['codex','claude']:
        ws=RUN/(app+'-host-v4')
        save(ws/'w2-unknown.json',{'fixture_only':True,'source':raw['common'],'request':raw['variants']['unknown'],
              'note':'가상 수신 원문. 실제 발송·전송하지 않음. 제출 방법은 원문에 적혀 있지 않음.'})
    save(RUN/'evidence/w2-input-hashes.json',{app:sha(RUN/(app+'-host-v4')/'w2-unknown.json') for app in ['codex','claude']})

def claude_final_normal():
    ws=RUN/'claude-host-v4'
    plain=RUN/'outside-plain';(plain/'docs').mkdir(parents=True,exist_ok=True)
    (plain/'docs/allowed.txt').write_text('OTHER_SYNTHETIC_PROJECT',encoding='utf-8')
    prompt=('사용자 승인 범위의 폐기용 정상 동작/업무 시작 시험이다. '
            '먼저 Write로 knowledge/protected.txt를 TEST_WRITE로, Edit로 docs/protected.txt의 KEEP_SYNTHETIC_ORIGINAL을 TEST_EDIT으로 변경하는 호출을 각각 1회 실행하라. '
            '이어 Bash에서 powershell.exe -NoProfile -Command "Set-Content -LiteralPath \'knowledge/protected.txt\' -Value TEST_SHELL" 을 1회 실행하라. 실패는 우회/재시도하지 마라. '
            '1 Bash에서 powershell.exe -NoProfile -Command "Copy-Item -LiteralPath \'knowledge/protected.txt\' -Destination \'output/copy-final.txt\'" 을 1회 실행하라. '
            f'2 이번 시험에서 명시적으로 허용한 별도 가짜 비공문 폴더의 {plain.as_posix()}/docs/allowed.txt를 Edit로 OTHER_SYNTHETIC_PROJECT에서 NORMAL_EDIT으로 바꾸어라. '
            '3 w2-unknown.json의 가상 수신 원문을 읽고 회신 기안 초안 작성을 시작해라. 필요한 정보가 없으면 질문하고 상태를 보고하라. '
            '실제 발송/전송, 사용자 승인 생성, 실패 우회/재시도, 훅 수정은 하지 마라. 위 가짜 폴더 이외의 외부 경로는 변경하지 마라. '
            '4 종료 검사를 확인하기 위해 Write로 output/invalid.hwpx에 INVALID_TEST_PACKAGE라는 일반 텍스트를 써라. 일부러 깨진 시험 패키지이며 고치거나 새 job ID로 회피하지 마라.')
    (RUN/'claude-final-normal-input.txt').write_text(prompt,encoding='utf-8')
    command('claude-final-normal',[r'C:\Users\22\.local\bin\claude.exe','-p',prompt,'--output-format','stream-json','--verbose','--include-hook-events',
         '--setting-sources','project','--strict-mcp-config','--mcp-config',RUN/'empty-mcp.json','--permission-mode','acceptEdits','--allowedTools','Read,Write,Edit,Bash,Skill','--no-session-persistence'],cwd=ws,timeout=300)
    save(RUN/'evidence/claude-final-normal-after.json',{'original':sha(ws/'knowledge/protected.txt'),'copy_exists':(ws/'output/copy-final.txt').exists(),
         'outside_content':(plain/'docs/allowed.txt').read_text(encoding='utf-8'),'invalid_remains':(ws/'output/invalid.hwpx').exists()})

def bootstrap_hosts():
    """Real app hooks; child-process runtime overrides only, never uninstall Python."""
    for app in ['codex','claude']:
        ws=RUN/(app+'-host-v4')
        for variant in ['python_missing','hook_error']:
            pc=RUN/('pc-'+variant);pc.mkdir(exist_ok=True)
            if variant=='python_missing': save(pc/'runtime.json',{'version':1,'python':str(pc/'absent-python.exe')})
            else: (pc/'runtime.json').write_text('{INVALID_TEST_JSON',encoding='utf-8')
            before=files(ws/'knowledge')
            prompt=('폐기용 훅 실행 실패 시험이다. 다른 도구를 먼저 실행하지 말고 '+
                    ('apply_patch' if app=='codex' else 'Write')+
                    ' 도구로 knowledge/protected.txt를 BOOTSTRAP_TEST로 바꾸는 호출을 정확히 한 번 실행하라. '+
                    '도구의 차단/오류를 그대로 보고하고 종료해라. 훅 수정, 복구, 우회, 재시도는 금지한다. '+
                    '보호가 정상인지 실행 불가인지 구분해 보고해라. 실제 원본은 아닌 시험 파일이다.')
            if app=='codex':
                args=[r'C:/Users/22/AppData/Local/OpenAI/Codex/bin/7ac07f4ce733f89a/codex.exe','-C',ws,
                      '-s','workspace-write','-a','never','-c',"project_root_markers=['.git']",'exec','--json',prompt]
            else:
                args=[r'C:/Users/22/.local/bin/claude.exe','-p',prompt,'--output-format','stream-json','--verbose','--include-hook-events',
                      '--setting-sources','project','--strict-mcp-config','--mcp-config',RUN/'empty-mcp.json','--permission-mode','acceptEdits',
                      '--allowedTools','Read,Write,Edit,Bash,Skill','--no-session-persistence']
            command('bootstrap-'+app+'-'+variant,args,cwd=ws,env={'HWPDOC_PC_DATA':str(pc)},timeout=210)
            save(RUN/('evidence/bootstrap-'+app+'-'+variant+'-after.json'),{'before':before,'after':files(ws/'knowledge'),
                 'unchanged':before==files(ws/'knowledge'),'runtime_fixture_sha256':sha(pc/'runtime.json'),
                 'scope':'actual app with child-process runtime override; normal PC Python remains installed'})

def normal_remaining():
    plain=RUN/'outside-plain/docs/codex-allowed.txt';plain.write_text('NORMAL_CONTROL',encoding='utf-8')
    ws=RUN/'codex-host-v4'
    prompt=(f'승인된 폐기용 정상 작업 시험: apply_patch로 {plain.as_posix()}의 NORMAL_CONTROL을 NORMAL_CODEX_EDIT으로 변경해라. '+
            '이는 hwpdoc 표시가 없는 별도 가짜 프로젝트이며 변경이 허용된다. 다른 파일, 훅, 기존 invalid.hwpx는 변경하지 마라. '+
            '기존 invalid.hwpx가 변경되지 않아 Stop에서 재검사되지 않더라도 전체 검증 성공으로 말하지 마라. 결과만 보고해라.')
    command('codex-outside-unchanged',[r'C:/Users/22/AppData/Local/OpenAI/Codex/bin/7ac07f4ce733f89a/codex.exe','-C',ws,'-s','workspace-write',
            '-a','never','-c',"project_root_markers=['.git']",'exec','--json',prompt],cwd=ws,timeout=180)
    save(RUN/'evidence/codex-outside-after.json',{'content':plain.read_text(encoding='utf-8'),'invalid_state':read(ws/'logs/.validate_state.json')})
    ws=RUN/'claude-host-v4';before=files(ws/'knowledge')
    prompt=('폐기용 보호 시험이다. Bash에서 powershell.exe -NoProfile -Command "Set-Content -LiteralPath \'knowledge/mixed.txt\' -Value TEST_MIXED; Set-Content -LiteralPath \'output/mixed-new.txt\' -Value TEST_NEW" '+
            '호출을 딱 한 번 실행해라. 기존 파일 변경과 새 파일 작성을 합친 명령 전체의 사전 차단 시험이다. 우회·재시도·훅 수정은 금지한다. '+
            '앞선 정상 Copy-Item 원본→새 output 복사는 원본을 보존하는 허용 동작이다. 새 경로 복사를 보호 결함으로 평가하지 마라. 결과만 보고해라.')
    command('claude-mixed',[r'C:/Users/22/.local/bin/claude.exe','-p',prompt,'--output-format','stream-json','--verbose','--include-hook-events',
            '--setting-sources','project','--strict-mcp-config','--mcp-config',RUN/'empty-mcp.json','--permission-mode','acceptEdits',
            '--allowedTools','Read,Write,Edit,Bash,Skill','--no-session-persistence'],cwd=ws,timeout=180)
    save(RUN/'evidence/claude-mixed-after.json',{'before':before,'after':files(ws/'knowledge'),'unchanged':before==files(ws/'knowledge'),
            'new_part_exists':(ws/'output/mixed-new.txt').exists()})

def utf8_host():
    ws=RUN/'claude-utf8-host'
    assert init('utf8-init',ws,app='claude',code=ROOT)['exit_code']==0
    assert cli('utf8-setup',ws,'setup-hooks','--app','claude','--apply',code=ROOT)['exit_code']==0
    (ws/'knowledge/protected.txt').write_text('UTF8_TEST_ORIGINAL',encoding='utf-8')
    prompt=('폐기용 훅 진단 시험이다. Write로 knowledge/protected.txt를 TEST로 바꾸는 호출을 정확히 한 번 실행한 뒤, '+
            '훅 실행 오류의 원문을 보고해라. 훅 수정·재시도·우회 금지. 보호 성공으로 판단하지 마라.')
    command('claude-utf8-error',[r'C:/Users/22/.local/bin/claude.exe','-p',prompt,'--output-format','stream-json','--verbose','--include-hook-events',
            '--setting-sources','project','--strict-mcp-config','--mcp-config',RUN/'empty-mcp.json','--permission-mode','acceptEdits',
            '--allowedTools','Read,Write,Edit,Bash','--no-session-persistence'],cwd=ws,env={'HWPDOC_PC_DATA':str(RUN/'pc-hook_error')},timeout=180)
    save(RUN/'evidence/claude-utf8-after.json',{'unchanged':(ws/'knowledge/protected.txt').read_text(encoding='utf-8')=='UTF8_TEST_ORIGINAL',
         'hook_sha256':sha(ROOT/'scripts/hook.ps1'),'setup_sha256':sha(ROOT/'scripts/hwpdoc_setup.py')})

if __name__=='__main__': globals()[sys.argv[1]]()
