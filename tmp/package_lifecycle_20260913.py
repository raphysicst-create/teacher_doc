"""Actual package/CLI lifecycle trials using child-process-only configuration roots."""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'tmp/package-lifecycle-20260913';PY=Path(sys.executable)
CODEX=Path('C:/Users/22/AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe')
CLAUDE=Path('C:/Users/22/.local/bin/claude.exe')
SKILL=Path('C:/Users/22/.codex/skills/.system/plugin-creator')
MARKET='teacher-doc-lifecycle-20260913'
PACKAGE=ROOT/'distribution/releases/2026-09-13/teacher_doc'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def env(app):
    result=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',HWPDOC_PC_DATA=str(RUN/f'pc-{app}'))
    # Documented per-process config locations, never assign PowerShell HOME/CODEX_HOME variables or mutate the user environment.
    result.update(CODEX_HOME=str(RUN/'codex-config'),CLAUDE_CONFIG_DIR=str(RUN/'claude-config'))
    result.pop('HWPDOC_WORKSPACE',None)
    return result
def call(key,args,app='codex',cwd=None,timeout=300):
    dest=RUN/'lifecycle-evidence'/f'{key}.json';assert not dest.exists(),dest
    started=now();t=time.monotonic()
    try:
        r=subprocess.run(list(map(str,args)),cwd=cwd or ROOT,env=env(app),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        result={'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:
        dec=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
        result={'exit_code':124,'stdout':dec(e.stdout),'stderr':dec(e.stderr),'timeout':True}
    result.update(at=started,seconds=time.monotonic()-t,argv=list(map(str,args)),cwd=str(cwd or ROOT),configuration_scope='disposable child-process config only')
    save(dest,result);print(key,result['exit_code'],flush=True)
    return result
def require(r):
    if r['exit_code']:raise RuntimeError(r['stdout'][-1800:]+r['stderr'][-1800:])
    return r
def build():
    globals=[Path('C:/Users/22/.codex/config.toml'),Path('C:/Users/22/.claude/settings.json'),Path('C:/Users/22/.claude/plugins/installed_plugins.json'),Path('C:/Users/22/.claude/plugins/known_marketplaces.json')]
    save(RUN/'global-config-before.json',{str(p):sha(p) if p.is_file() else None for p in globals})
    r=require(call('build-original',[PY,'-B','-X','utf8',ROOT/'scripts/build_distribution.py','--rights',ROOT/'distribution/rights.pending.json','--output',PACKAGE]))
    data=json.loads(r['stdout']);assert data['status']=='packaged' and len(data['files'])==103
    assert all(sha(PACKAGE/e['destination'])==e['sha256'] for e in data['files'])
    for app in ['codex','claude']:
        (RUN/f'{app}-config').mkdir(exist_ok=True)
        save(RUN/f'pc-{app}/runtime.json',{'version':1,'python':str(PY),'note':'Disposable PC data sentinel; preserve through uninstall'})
    market=RUN/'market';shutil.copytree(PACKAGE,market/'plugins/teacher_doc')
    spec=importlib.util.spec_from_file_location('plugin_scaffolder',SKILL/'scripts/create_basic_plugin.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.validate_plugin_name('teacher_doc')
    mod.update_marketplace_json(market/'.agents/plugins/marketplace.json',MARKET,'teacher_doc','AVAILABLE','ON_INSTALL','Productivity',False)
    save(market/'.claude-plugin/marketplace.json',{'name':MARKET,'owner':{'name':'teacher_doc local acceptance'},'plugins':[{'name':'teacher_doc','source':'./plugins/teacher_doc','description':'Disposable local lifecycle test','version':'0.1.0'}]})
    require(call('codex-plugin-validate',[PY,'-B','-X','utf8',SKILL/'scripts/validate_plugin.py',PACKAGE]))
    require(call('claude-plugin-validate',[CLAUDE,'plugin','validate',PACKAGE],app='claude'))
    require(call('marketplace-name',[PY,'-B','-X','utf8',SKILL/'scripts/read_marketplace_name.py','--marketplace-path',market/'.agents/plugins/marketplace.json']))
    print('Package and local marketplace prepared')
def install(app):
    market=RUN/'market';client=CODEX if app=='codex' else CLAUDE
    require(call(app+'-market-add',[client,'plugin','marketplace','add',market],app=app))
    require(call(app+'-install',[client,'plugin','add' if app=='codex' else 'install',f'teacher_doc@{MARKET}'],app=app))
    require(call(app+'-list-installed',[client,'plugin','list','--json'],app=app))
def installed_root(app,version='0.1.0'):
    p=RUN/f'{app}-config/plugins/cache'/MARKET/'teacher_doc'/version
    if app=='claude':
        receipt=RUN/'lifecycle-evidence'/('claude-list-installed.json' if version=='0.1.0' else 'claude-list-updated.json')
        if receipt.is_file():
            entries=json.loads(read(receipt)['stdout'])
            item=next(i for i in entries if i['id']==f'teacher_doc@{MARKET}' and i['version']==version)
            p=Path(item['installPath'])
            assert p.resolve().is_relative_to((RUN/'claude-config/plugins/cache').resolve())
    assert (p/'scripts/teacher_doc.py').is_file(),p
    return p
def hcli(app,key,*args,version='0.1.0'):
    return call(app+'-'+key,[PY,'-B','-X','utf8',installed_root(app,version)/'scripts/teacher_doc.py','--workspace',RUN/f'ws-{app}',*args],app=app,cwd=RUN/f'ws-{app}')
def protected(app):
    ws=RUN/f'ws-{app}'
    result={p.relative_to(ws).as_posix():sha(p) for d in ['inputs','output','.hwpdoc/templates'] for p in (ws/d).rglob('*') if p.is_file()}
    result['@pc-runtime']=sha(RUN/f'pc-{app}/runtime.json')
    return result
def baseline(app):
    code=installed_root(app);inventory=read(PACKAGE/'release-inventory.json')['files']
    assert all(sha(code/e['destination'])==e['sha256'] for e in inventory)
    ws=RUN/f'ws-{app}';assert not ws.exists()
    require(call(app+'-init',[PY,'-B','-X','utf8',code/'scripts/teacher_doc.py','init',ws,'--app',app,'--skill-name','hwpx'],app=app))
    old=ROOT/'tmp/remaining-20260913/codex-marked'
    shutil.copytree(old/'inputs/approved-workflow',ws/'inputs/approved-workflow')
    shutil.copy2(old/'inputs/form.hwpx',ws/'inputs/form.hwpx')
    shutil.copy2(old/'inputs/workflow-drafts.md',ws/'inputs/workflow-drafts.md')
    shutil.copytree(old/'.hwpdoc/templates/trial-gianmun',ws/'.hwpdoc/templates/trial-gianmun')
    (ws/'output').mkdir(exist_ok=True);shutil.copy2(old/'.hwpdoc/jobs/approved-w1-20260913/work.hwpx',ws/'output/teacher-review.hwpx')
    (ws/'output/teacher-note.txt').write_text('USER DATA MUST SURVIVE INSTALL UPDATE UNINSTALL',encoding='utf-8')
    (ws/'test-copy').mkdir()
    cfg=read(ws/'.hwpdoc/workspace.json');cfg.update(school={'name':'가람중학교','document_prefix':'','academic_year':2026},references={'related':'inputs/approved-workflow/related'},delivery={'external_copy':str(ws/'test-copy')})
    save(ws/'.hwpdoc/workspace.json',cfg)
    user_settings={'hooks':{'PreToolUse':[{'matcher':'NeverMatchesLifecycle','hooks':[{'type':'command','command':'echo USER_HOOK_SENTINEL'}]}]},'lifecycle_user_setting':'KEEP'}
    settings=ws/('.codex/hooks.json' if app=='codex' else '.claude/settings.json');save(settings,user_settings)
    save(RUN/f'{app}-user-hooks-original.json',user_settings)
    save(RUN/f'{app}-protected-seed.json',protected(app))
    require(hcli(app,'hooks-proposal-a','setup-hooks','--app',app))
    require(hcli(app,'hooks-install-a','setup-hooks','--app',app,'--apply'))
    require(hcli(app,'doctor-a','doctor'))
    assert read(ws/'.hwpdoc/doctor.json')['checks']['hancom']['status']=='pass'
    require(hcli(app,'build-a','build','--manifest','inputs/approved-workflow/w1.json'))
    require(hcli(app,'validate-a','validate','--job','approved-w1-20260913'))
    require(hcli(app,'deliver-a','deliver','--job','approved-w1-20260913'))
    save(RUN/f'{app}-protected-before-update.json',protected(app))
    shutil.copy2(ws/'.hwpdoc/jobs/approved-w1-20260913/report.json',RUN/f'{app}-report-before-update.json')
    print(app,'baseline installed-code workflow passed',flush=True)
def prepare_update():
    candidate=ROOT/'distribution/lifecycle-test-source/teacher_doc';assert not candidate.exists()
    shutil.copytree(PACKAGE,candidate)
    require(call('cachebuster-update',[PY,'-B','-X','utf8',SKILL/'scripts/update_plugin_cachebuster.py',candidate]))
    version=read(candidate/'.codex-plugin/plugin.json')['version']
    c=read(candidate/'.claude-plugin/plugin.json');c['version']=version;save(candidate/'.claude-plugin/plugin.json',c)
    # Disposable update probe: a harmless source comment changes a tracked tool hash.
    p=candidate/'scripts/hwpdoc.py';p.write_text(p.read_text(encoding='utf-8')+'\n# Local lifecycle update fixture: source replacement detection.\n',encoding='utf-8')
    manifest=read(ROOT/'distribution/release-files.json');rights=read(ROOT/'distribution/rights.pending.json')
    inventory=read(PACKAGE/'release-inventory.json')['files']
    bydest={i['destination']:i for i in inventory}
    for entry in manifest['files']:entry['source']=(candidate/entry['destination']).relative_to(ROOT).as_posix()
    manifest.update(plugin_version=version,source_bundle=(candidate/'SOURCE-BUNDLE.json').relative_to(ROOT).as_posix())
    bundle=read(candidate/'SOURCE-BUNDLE.json');bundle['plugin_version']=version;save(candidate/'SOURCE-BUNDLE.json',bundle)
    revised={'version':rights.get('version',1),'files':{},'dependencies':copy.deepcopy(rights['dependencies'])}
    for entry in manifest['files']:
        original=bydest[entry['destination']]['source'];r=copy.deepcopy(rights['files'][original]);h=sha(ROOT/entry['source'])
        r.update(sha256=h,privacy_sha256=h,reviewed_at=now(),permission_record=r['permission_record']+'; local lifecycle fixture review: only plugin versions, source-bundle version and a nonfunctional code comment differ')
        revised['files'][entry['source']]=r
    revised['dependencies']['PyMuPDF==1.28.0']['source_bundle_sha256']=sha(candidate/'SOURCE-BUNDLE.json')
    save(RUN/'update-manifest.json',manifest);save(RUN/'update-rights.json',revised)
    output=ROOT/'distribution/lifecycle-test-updated/teacher_doc'
    require(call('build-updated',[PY,'-B','-X','utf8',ROOT/'scripts/build_distribution.py','--manifest',RUN/'update-manifest.json','--rights',RUN/'update-rights.json','--output',output]))
    save(RUN/'update-package.json',{'version':version,'path':str(output),'fixture_only':True,'changes':['Codex helper cachebuster and matching Claude/source-bundle version','Nonfunctional hwpdoc.py comment to verify source freshness detection'],'public_release_candidate':str(PACKAGE)})
    print('updated package ready',version)
def publish_update_fixture():
    assert all((RUN/f'{app}-report-before-update.json').is_file() for app in ['codex','claude'])
    info=read(RUN/'update-package.json');source=Path(info['path']);dest=RUN/'market/plugins/teacher_doc'
    assert dest.resolve().is_relative_to(RUN.resolve()) and source.resolve().is_relative_to(ROOT/'distribution')
    save(RUN/'market-before-update.json',{p.relative_to(dest).as_posix():sha(p) for p in dest.rglob('*') if p.is_file()})
    shutil.copytree(source,dest,dirs_exist_ok=True)
    mp=RUN/'market/.claude-plugin/marketplace.json';data=read(mp);data['plugins'][0]['version']=info['version'];save(mp,data)

def update(app,resume=False):
    info=read(RUN/'update-package.json');version=info['version'];client=CODEX if app=='codex' else CLAUDE
    if not resume:
        if app=='claude':require(call(app+'-market-update',[client,'plugin','marketplace','update',MARKET],app=app))
        require(call(app+'-update',[client,'plugin','add' if app=='codex' else 'update',f'teacher_doc@{MARKET}'],app=app))
        require(call(app+'-list-updated',[client,'plugin','list','--json'],app=app))
    code=installed_root(app,version);inventory=read(Path(info['path'])/'release-inventory.json')['files']
    assert all(sha(code/e['destination'])==e['sha256'] for e in inventory)
    assert sha(code/'scripts/hwpdoc.py')!=sha(PACKAGE/'scripts/hwpdoc.py')
    stale=hcli(app,'status-stale-b','status','--job','approved-w1-20260913',version=version)
    assert stale['exit_code']==2 and 'hwpdoc.py' in stale['stdout'],stale
    require(hcli(app,'hooks-proposal-b','setup-hooks','--app',app,version=version))
    require(hcli(app,'hooks-update-b','setup-hooks','--app',app,'--apply',version=version))
    require(hcli(app,'validate-b','validate','--job','approved-w1-20260913',version=version))
    ws=RUN/f'ws-{app}';before=read(RUN/f'{app}-report-before-update.json');after=read(ws/'.hwpdoc/jobs/approved-w1-20260913/report.json')
    assert after['manifest_sha256']==before['manifest_sha256']
    assert after['tool_updates'][-1]['approval_preserved'] is True
    assert protected(app)==read(RUN/f'{app}-protected-before-update.json')
    shutil.copy2(ws/'.hwpdoc/jobs/approved-w1-20260913/report.json',RUN/f'{app}-report-after-update.json')
    save(RUN/f'{app}-update-verification.json',{'at':now(),'version':version,'installed_files_verified':len(inventory),'old_validation_rejected':True,'new_full_validation_passed':True,'approval_input_preserved':True,'user_files_preserved':len(protected(app))})
    print(app,'update verification passed',flush=True)

def uninstall(app):
    version=read(RUN/'update-package.json')['version'];client=CODEX if app=='codex' else CLAUDE
    require(hcli(app,'hooks-remove-proposal','setup-hooks','--app',app,'--remove',version=version))
    require(hcli(app,'hooks-remove','setup-hooks','--app',app,'--remove','--apply',version=version))
    ws=RUN/f'ws-{app}';settings=ws/('.codex/hooks.json' if app=='codex' else '.claude/settings.json')
    assert read(settings)==read(RUN/f'{app}-user-hooks-original.json')
    args=[client,'plugin','remove' if app=='codex' else 'uninstall',f'teacher_doc@{MARKET}']
    if app=='claude':args+=['--keep-data','--json']
    require(call(app+'-uninstall',args,app=app))
    listing=require(call(app+'-list-uninstalled',[client,'plugin','list','--json'],app=app))
    data=json.loads(listing['stdout']);installed=data.get('installed',[]) if isinstance(data,dict) else data
    assert not installed,installed
    assert protected(app)==read(RUN/f'{app}-protected-before-update.json')
    save(RUN/f'{app}-uninstall-verification.json',{'at':now(),'plugin_uninstalled':True,'custom_hooks_preserved':True,'user_files_preserved':len(protected(app)),'pc_runtime_preserved':True,'owned_hooks_removed_before_uninstall':True})
    print(app,'uninstall and preservation passed',flush=True)

def main():
    if sys.argv[1]=='build':build()
    elif sys.argv[1]=='install':install(sys.argv[2])
    elif sys.argv[1]=='baseline':baseline(sys.argv[2])
    elif sys.argv[1]=='prepare-update':prepare_update()
    elif sys.argv[1]=='publish-update-fixture':publish_update_fixture()
    elif sys.argv[1]=='update':update(sys.argv[2])
    elif sys.argv[1]=='resume-update':update(sys.argv[2],resume=True)
    elif sys.argv[1]=='uninstall':uninstall(sys.argv[2])
if __name__=='__main__':main()
