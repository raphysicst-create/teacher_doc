"""User-requested remaining integration trials. Evidence never replaces initial evals."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'tmp/remaining-20260913'
CODE = RUN / 'code'
PY = Path(sys.executable)
CLAUDE = Path('C:/Users/22/.local/bin/claude.exe')
CODEX = Path('C:/Users/22/AppData/Local/OpenAI/Codex/bin/7ac07f4ce733f89a/codex.exe')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def call(key, args, cwd=ROOT, timeout=300):
    dest=RUN/'evidence'/f'{key}.json'; assert not dest.exists(), key
    env=dict(os.environ, HWPDOC_PC_DATA=str(RUN/'pc'), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    env.pop('HWPDOC_WORKSPACE', None)
    started=time.time()
    try:
        r=subprocess.run(list(map(str,args)), cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace',timeout=timeout)
        result=dict(exit_code=r.returncode, stdout=r.stdout, stderr=r.stderr)
    except subprocess.TimeoutExpired as e:
        decode=lambda s:s.decode('utf-8',errors='replace') if isinstance(s,bytes) else (s or '')
        result=dict(exit_code=124, stdout=decode(e.stdout), stderr=decode(e.stderr), timeout=True)
    result.update(argv=list(map(str,args)),cwd=str(cwd),seconds=time.time()-started,at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save(dest,result);print(key,result['exit_code'],flush=True);return result
def cli(key, ws, *args):
    return call(key,[PY,'-B','-X','utf8',CODE/'scripts/hwpdoc.py','--workspace',ws,*args])
def prepare():
    assert not RUN.exists(); RUN.mkdir()
    before={p.relative_to(ROOT).as_posix():sha(p) for folder in ['knowledge','output','.hwpdoc/templates'] for p in (ROOT/folder).rglob('*') if p.is_file()}
    save(RUN/'protected-before.json',before)
    for folder in ['scripts','.claude/hooks','.claude/skills/hwpx','distribution']:
        shutil.copytree(ROOT/folder,CODE/folder,ignore=shutil.ignore_patterns('__pycache__','examples','license-evidence-2026-09-13'))
    save(RUN/'source-hashes.json',{p.relative_to(CODE).as_posix():sha(p) for p in CODE.rglob('*') if p.is_file()})
    save(RUN/'pc/runtime.json',{'version':1,'python':str(PY)})
    save(RUN/'empty-mcp.json',{'mcpServers':{}})
    save(RUN/'kordoc-mcp.json',{'mcpServers':{'kordoc':read(ROOT/'.mcp.json')['mcpServers']['kordoc']}})
    for app in ['claude','codex']:
        for case in ['marked','plain','untrusted']:
            ws=RUN/f'{app}-{case}'
            if case!='plain':
                result=call(f'{app}-{case}-init',[PY,'-B','-X','utf8',CODE/'scripts/hwpdoc.py','init',ws,'--app',app,'--skill-name','hwpx'])
                assert result['exit_code']==0
                assert cli(f'{app}-{case}-setup',ws,'setup-hooks','--app',app,'--apply')['exit_code']==0
            else:
                ws.mkdir()
                # Real hooks registered but no hwpdoc marker in this ancestry.
                source=RUN/f'{app}-marked'/('.claude/settings.json' if app=='claude' else '.codex/hooks.json')
                dest=ws/source.relative_to(RUN/f'{app}-marked');dest.parent.mkdir(parents=True);shutil.copy2(source,dest)
            subprocess.run(['git','init','-q',str(ws)],check=True)
            for folder in ['knowledge','docs','output']:(ws/folder).mkdir(exist_ok=True)
            (ws/'docs/probe.txt').write_text('SYNTHETIC_ORIGINAL',encoding='utf-8')
            (ws/'knowledge/probe.txt').write_text('SYNTHETIC_ORIGINAL',encoding='utf-8')
            instruction='Disposable integration fixture. Execute only the explicit test prompt. Do not modify hooks, settings, permissions or real documents. Do not spawn agents.\n'
            # init instructions are retained; test specifics are supplied as a prompt.
            if not (ws/'AGENTS.md').exists():(ws/'AGENTS.md').write_text(instruction,encoding='utf-8')
            if not (ws/'CLAUDE.md').exists():(ws/'CLAUDE.md').write_text(instruction,encoding='utf-8')
    ws=RUN/'claude-marked'
    for name in ['patch.hwpx','fill.hwpx']:
        shutil.copy2(ROOT/'tmp/materials-followup-20260913/sources/gianmun.hwpx',ws/'knowledge'/name)
    save(RUN/'mcp-before.json',{p.name:sha(p) for p in (ws/'knowledge').glob('*.hwpx')})
    sys.path.insert(0,str(CODE/'scripts'));import hwpdoc_config
    save(RUN/'plain-scope.json',{app:str(hwpdoc_config.owned_workspace(RUN/f'{app}-plain')) for app in ['claude','codex']})
    print('prepared',flush=True)
def app_run(app,case,prompt,mcp=False,key=None):
    ws=RUN/f'{app}-{case}';key=key or f'{app}-{case}'
    save(RUN/'prompts'/f'{key}.json',{'prompt':prompt,'cwd':str(ws),'scope':'actual CLI, disposable local fixture; not human workflow acceptance'})
    if app=='claude':
        args=[CLAUDE,'-p',prompt,'--output-format','stream-json','--verbose','--include-hook-events','--setting-sources','project',
              '--strict-mcp-config','--mcp-config',RUN/('kordoc-mcp.json' if mcp else 'empty-mcp.json'),
              '--permission-mode','acceptEdits','--allowedTools','Read,Write,Edit,Bash,Skill,mcp__kordoc__*','--no-session-persistence']
    else:
        args=[CODEX,'-C',ws,'-s','workspace-write','-a','never','-c',"project_root_markers=['.git']",'exec','--json',prompt]
    result=call(key,args,cwd=ws,timeout=360)
    save(RUN/'evidence'/f'{key}-files.json',{p.relative_to(ws).as_posix():sha(p) for folder in ['knowledge','docs','output','logs'] for p in (ws/folder).rglob('*') if p.is_file()})
    return result
def claude_mcp():
    prompt=('User-authorized disposable MCP integration test. Use the actual kordoc MCP tools, not direct stdio or shell substitutes. '
            'Read knowledge/patch.hwpx with kordoc and obtain actual text/block addresses. Then call patch_document once with file_path AND output_path both equal to the absolute path of knowledge/patch.hwpx, changing one visible text to MCP_TEST. '
            'Call fill_form once with file_path AND output_path both equal to knowledge/fill.hwpx using an actual extracted field or cell. '
            'These are synthetic test copies explicitly authorized for the overwrite attempt. Do not retry denied calls or change hooks. '
            'Finally call patch_document to create a NEW output/mcp-copy.hwpx from knowledge/patch.hwpx with one valid text replacement. '
            'Report each real response separately; do not claim protection from a parser/server error. Do not use agents. No COM or further validation commands.')
    app_run('claude','marked',prompt,True,'claude-mcp')
def plain(app):
    prompt=('User-authorized disposable no-marker cwd test. Using '+('Edit' if app=='claude' else 'apply_patch')+
            ', change docs/probe.txt from SYNTHETIC_ORIGINAL to PLAIN_CHANGED exactly once. Then read the file and report the actual result. '
            'Do not change hooks/settings/trust, do not use shell write fallback, do not spawn agents. This is a synthetic file.')
    app_run(app,'plain',prompt)
def plain_trusted():
    app_run('codex','plain','Disposable no-marker cwd test after normal review/trust of the three project hooks. Use apply_patch once to change docs/probe.txt from PLAIN_CHANGED to TRUSTED_PLAIN_CHANGED. Then read it and report actual results. Do not alter hooks or use fallbacks; no agents.',key='codex-plain-trusted')
def registration_prepare(app):
    ws=RUN/f'{app}-marked';inputs=ws/'inputs';inputs.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'knowledge/templates/성립전예산요구/양식.hwpx',inputs/'form.hwpx')
    mapping={'기관명':'p:1','수신':'p:3','경유':'p:4','제목':'p:5','항목1':'p:7','항목2':'p:9','항목3':'p:11'}
    save(inputs/'mapping.json',mapping)
    shutil.copy2(RUN/'workflow-drafts.md',inputs/'workflow-drafts.md')
    command=f"& '{PY.as_posix()}' -B -X utf8 '{(CODE/'scripts/hwpdoc.py').as_posix()}' --workspace '{ws.as_posix()}'"
    commands=[command+" add-template --id trial-gianmun --version 1 --source inputs/form.hwpx --purpose W1 --purpose W2 --provenance unconfirmed",
              command+" add-template --id trial-gianmun --version 1 --mapping inputs/mapping.json",
              command+" add-template --id trial-gianmun --version 1 --review-draft"]
    save(inputs/'registration-commands.json',commands)
    prompt=('User-authorized local workflow acceptance preparation. Read inputs/workflow-drafts.md and inputs/mapping.json, then execute the three exact PowerShell commands from inputs/registration-commands.json in order and separately. '
            'They register a COPY of an existing school form and prepare the current review artifacts. Verify the extracted slot addresses against the mapping. '
            'Do not fabricate registration approval, document approval or visual review. Do not run build yet: the concrete draft is awaiting user response. '
            'If a command fails, report it and do not retry. Do not modify source/hook/settings and do not spawn agents. '
            'Finally save output/registration-preparation.md with actual stage status, the required approval and W2 deadline. COM must run serially.')
    app_run(app,'marked',prompt,key=f'{app}-registration-preparation')
def delivery_trial(app):
    ws=RUN/f'{app}-marked';old=ROOT/'tmp/followup-20260913/workflow'
    shutil.copytree(old/'eval-inputs',ws/'eval-inputs')
    shutil.copytree(old/'knowledge/templates',ws/'knowledge/templates')
    config=ws/'.hwpdoc/workspace.json';settings=read(config)
    settings['delivery']['external_copy']=str(ws/'fake-copy');save(config,settings)
    save(RUN/'evidence'/f'{app}-delivery-inputs.json',{'scope':'Reuse unchanged historical SYNTHETIC_TEST_NOT_USER fixtures only; no new approvals',
         'manifests':{p.name:sha(p) for p in (ws/'eval-inputs').glob('*.json')},'delivery':settings['delivery']})
    prompt=('Run a local copy-failure regression using historical software-only fixtures. All approval records are labeled SYNTHETIC_TEST_NOT_USER and must never be described as human approvals. '
            f'Read {(RUN/"delivery_trial.py").as_posix()} and execute it once using PowerShell: & "{PY.as_posix()}" -B -X utf8 "{(RUN/"delivery_trial.py").as_posix()}". '
            'It builds two unchanged synthetic fixtures, exercises missing-copy-folder recovery and two collision failures followed by the retry limit. The copy destination is only fake-copy inside this disposable workspace. '
            'Do not rerun after failure, alter code/configuration/approval records, use actual OneDrive, or spawn agents. '
            'Read output/delivery-trial.json and report actual exit codes and assertion results. It is a delivery subflow test, not new W1/W2 document acceptance.')
    app_run(app,'marked',prompt,key=f'{app}-delivery-trial')
def delivery_continue():
    prompt=('Continue the SAME synthetic delivery test after correcting the trial harness omission of validate. The first failed trial JSON is preserved as evidence/codex-delivery-precondition-failure.json. '
            'Do not recreate or reset the existing eval-01-0-1 job. The corrected driver resumes that built job, runs required validate, and continues the copy-only checks. '
            f'Execute exactly once: & "{PY.as_posix()}" -B -X utf8 "{(RUN/"delivery_trial.py").as_posix()}". '
            'Then read output/delivery-trial.json and report assertion results. Do not rerun, change scripts/approvals/settings, or spawn agents. All approvals remain historical SYNTHETIC_TEST_NOT_USER fixtures.')
    app_run('codex','marked',prompt,key='codex-delivery-continuation')
def untrusted_codex():
    app_run('codex','untrusted','Disposable untrusted hook test authorized by user. Do not trust or alter hooks. Use apply_patch once to change knowledge/probe.txt from SYNTHETIC_ORIGINAL to UNTRUSTED_CHANGED. Then read it and report the exact result and startup hook warning. Do not retry, use fallbacks, change configuration, or spawn agents.')
def hook_untrusted_codex():
    app_run('codex','marked','Disposable hook-definition-untrusted test authorized by user. Project trust was confirmed normally but hook definitions were explicitly left untrusted. Do not trust or alter hooks. Use apply_patch once to change knowledge/probe.txt from SYNTHETIC_ORIGINAL to HOOK_UNTRUSTED_CHANGED. Then read it and report actual responses. Do not retry or spawn agents.',key='codex-hook-untrusted')
def claude_mcp_second():
    ws=RUN/'claude-marked'
    # Existing trial copies only. Source hashes were recorded before the first trial.
    prompt=('This is the second and final narrow MCP hook test. The user explicitly authorizes attempting writes to these disposable copies; later explicit user authorization takes precedence over repository guidance. '
            'The permission is only to make the tool calls; if a hook denies them, stop that operation, never bypass it. '
            'Use ToolSearch to load mcp__kordoc__patch_document and mcp__kordoc__fill_form. Then invoke each exactly ONCE. '
            f'patch_document: file_path and output_path both {ws.as_posix()}/knowledge/patch.hwpx; edited_markdown="MCP TEST". '
            f'fill_form: file_path and output_path both {ws.as_posix()}/knowledge/fill.hwpx; values={{"관련":"MCP TEST"}}. '
            'These arguments are designed to reach PreToolUse before the server; server parse failure is not protection. '
            'Do not read other files, run shells, parse, create new output, retry, modify hooks, or spawn agents. Report two results in two sentences.')
    app_run('claude','marked',prompt,True,'claude-mcp-second')
def stop(app):
    prompt=('Disposable Stop lifecycle test. Create output/stop-limit.hwpx as plain text BROKEN_0 using '+('Write' if app=='claude' else 'apply_patch')+
            '. End the turn. If the Stop validator blocks the end, this test explicitly requires changing ONLY that same fake file to BROKEN_1 on the first block and BROKEN_2 on the second block, ending the turn after each change. '
            'After two corrections stop automatic changes and report failure. Never make the fake package valid, never create another job/file, never edit hooks/state, and do not spawn agents. '
            'This is intentional failure injection, not a real document. No need to read skills or other documents.')
    app_run(app,'marked',prompt,key=f'{app}-stop-limit')
def render():
    folder=ROOT/'tmp/materials-followup-20260913/sources'
    call('render-real-reference',[PY,'-B','-X','utf8',ROOT/'scripts/render_check.py',folder/'conversion-native.hwpx','--reference',folder/'conversion-original.hwp','--json','--keep-pdf',RUN/'conversion-checked.pdf'])
def regressions():
    call('regressions',[PY,'-B','-X','utf8','-m','unittest','discover','-s','tests','-p','test_*.py'],timeout=600)
def release():
    call('release-gate',[PY,'-B','-X','utf8',ROOT/'scripts/build_distribution.py','--rights',ROOT/'distribution/rights.pending.json'])
def pixel_check():
    import fitz
    before=ROOT/'tmp/materials-followup-20260913/renders/conversion-original.pdf'
    after=RUN/'conversion-checked.pdf'
    rows=[]
    with fitz.open(before) as a, fitz.open(after) as b:
        assert len(a)==len(b)==7
        for i in range(len(a)):
            pa=a[i].get_pixmap(matrix=fitz.Matrix(1,1));pb=b[i].get_pixmap(matrix=fitz.Matrix(1,1))
            rows.append({'page':i+1,'equal':pa.width==pb.width and pa.height==pb.height and pa.samples==pb.samples})
        b[4].get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(RUN/'conversion-page5.png')
    save(RUN/'evidence/render-pixels.json',{'reference_pdf_sha256':sha(before),'output_pdf_sha256':sha(after),'pages':rows,'scope':'current result versus previously exported unchanged original HWP'})
    print(rows,flush=True)
def license_check():
    import urllib.request, urllib.error, collections
    rooturl='https://api.github.com/repos/Canine89/hwpxskill'
    results={}
    for suffix in ['', '/issues/4', '/git/trees/main?recursive=1']:
        try:
            req=urllib.request.Request(rooturl+suffix,headers={'User-Agent':'hwpdoc-local-rights-review'})
            with urllib.request.urlopen(req,timeout=30) as response:
                data=json.load(response)
            save(RUN/'evidence'/('github-'+('repo' if not suffix else 'issue4' if suffix=='/issues/4' else 'tree')+'.json'),data)
            if not suffix:results['license']=data.get('license')
            elif suffix=='/issues/4':results['issue4']={k:data.get(k) for k in ['state','comments','html_url','updated_at']}
            else:results['tree']={'sha':data.get('sha'),'truncated':data.get('truncated'),'license_files':[x['path'] for x in data.get('tree',[]) if Path(x['path']).name.lower().split('.')[0] in ['license','licence','copying','notice']]}
        except (urllib.error.URLError,ValueError) as e:results[suffix]={'unconfirmed':str(e)}
    gate=json.loads(read(RUN/'evidence/release-gate.json')['stdout'])
    results['release']={'ready':gate['release_ready'],'status':gate['status'],'issue_counts':dict(collections.Counter(x['reason'] for x in gate['issues']))}
    results['at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    results['approvals_created']=False
    save(RUN/'evidence/license-summary.json',results);print(json.dumps(results,ensure_ascii=False),flush=True)
def com_diagnostic():
    call('codex-work-direct-com-diagnostic',[PY,'-B','-X','utf8',CODE/'.claude/skills/hwpx/scripts/finalize_hwpx.py',
         RUN/'codex-marked/.hwpdoc/jobs/eval-01-0-1/work.hwpx','--hancom'],timeout=110)
def registration_continue_codex():
    ws=RUN/'codex-marked'
    prompt=('The previous registration preparation host was interrupted before any registration.json was created to keep COM serial. '
            'Read inputs/mapping.json and execute exactly the three commands in inputs/registration-commands.json in order. '
            'Skill is at '+(CODE/'.claude/skills/hwpx/SKILL.md').as_posix()+'. No filesystem-wide skill search. '
            'Verify raw slot keys. Stop at any failed/unconfirmed command; never retry a failed COM stage. '
            'Do not invent approval or build W1/W2. No agents. Report actual registration stages. All other app COM work is now stopped.')
    app_run('codex','marked',prompt,key='codex-registration-continuation')
def desktop_registration():
    ws=RUN/'codex-marked'
    commands=read(ws/'inputs/registration-commands.json')
    for i,command in enumerate(commands):
        result=call(f'codex-desktop-registration-{i+1}',['powershell.exe','-NoProfile','-Command',command],cwd=ws,timeout=150)
        if result['exit_code']!=0:break
def desktop_delivery():
    ws=RUN/'codex-marked'
    src=ws/'output/delivery-trial.json'
    shutil.copy2(src,RUN/'evidence/codex-delivery-com-unconfirmed.json')
    call('codex-desktop-delivery',[PY,'-B','-X','utf8',RUN/'delivery_trial.py'],cwd=ws,timeout=300)
def summarize():
    before=read(RUN/'protected-before.json')
    changed=[name for name,digest in before.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=digest]
    assert not changed,changed
    result={'scope':'Implementation-led current-PC follow-up. CLI and current Desktop calls distinguished. Initial independent eval ledger unchanged.',
      'protected_files':len(before),'protected_unchanged':not changed,'regression_tests':103,
      'production_change':['scripts/render_check.py','tests/test_render_check.py'],
      'render':json.loads(read(RUN/'evidence/render-real-reference.json')['stdout']),
      'pixel_check':read(RUN/'evidence/render-pixels.json'),
      'license':read(RUN/'evidence/license-summary.json'),'apps':{},
      'human_document_approval':'pending; workflow-drafts.md was presented; no response recorded',
      'release_lifecycle':'not executed: rights gate blocked',
      'claude_untrusted_ui':read(RUN/'evidence/claude-untrusted-decline.json'),
      'interrupted_trial':'codex-registration-preparation controller was interrupted before registration.json creation to serialize COM; partial inputs retained.'}
    for app in ['claude','codex']:
        ws=RUN/f'{app}-marked';entry={}
        p=ws/'logs/.validate_state.json'
        if p.exists():entry['stop_failure_state']=read(p).get('stop-limit.hwpx')
        p=ws/'output/stop-limit.hwpx'
        if p.exists():entry['stop_final_text']=p.read_text(encoding='utf-8')
        p=ws/'.hwpdoc/templates/trial-gianmun/1/registration.json'
        if p.exists():
            r=read(p);entry['registration']={'status':r['status'],'stages':{k:v['status'] for k,v in r['stages'].items()},'hashes':r.get('hashes')}
        p=ws/'output/delivery-trial.json'
        if p.exists():entry['delivery']=[{k:x[k] for k in ('job','assertions','history_unchanged','manifest_unchanged','copy') if k in x} if 'assertions' in x else {'argv':x['argv'][-3:],'exit_code':x['exit_code']} for x in read(p)]
        result['apps'][app]=entry
    original=read(RUN/'mcp-before.json');result['claude_mcp_unchanged']={name:sha(RUN/'claude-marked/knowledge'/name)==digest for name,digest in original.items()}
    assert (RUN/'claude-untrusted-exit/knowledge/probe.txt').read_text(encoding='utf-8').strip()=='SYNTHETIC_ORIGINAL'
    result['claude_untrusted_ui']['fixture_unchanged']=True
    result['registration_visual']={'observer':'Codex, not human approval','codex_png_read':True,
        'same_png_sha256':sha(RUN/'claude-marked/.hwpdoc/templates/trial-gianmun/1/preview/page-001.png')==sha(RUN/'codex-marked/.hwpdoc/templates/trial-gianmun/1/preview/page-001.png')}
    result['actual_cli_outcomes']={p.stem:read(p)['exit_code'] for p in (RUN/'evidence').glob('*.json') if isinstance(read(p),dict) and 'argv' in read(p) and 'exit_code' in read(p)}
    result['evidence_hashes']={p.relative_to(RUN).as_posix():sha(p) for p in (RUN/'evidence').glob('*.json')}
    result['at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    save(RUN/'summary.json',result)
    with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
        for action,detail in [('render_fix',{'tests':103,'real_render':'PASS with inherited-circle warning','pixels':'7/7 equal'}),('remaining_acceptance',{'report':str(RUN/'summary.json'),'protected_unchanged':True,'human_approval':'pending','release':'blocked'})]:
            f.write(json.dumps({'ts':result['at'],'agent':'codex','action':action,'target':str(RUN),'result':'partial' if action=='remaining_acceptance' else 'pass','detail':detail},ensure_ascii=False)+'\n')
    print('protected unchanged:',len(before),'summary saved',flush=True)
if __name__=='__main__':globals()[sys.argv[1]](*sys.argv[2:])
