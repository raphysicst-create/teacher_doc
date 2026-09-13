from branch_acceptance_20260913 import *
import copy
OLD=ROOT/'tmp/remaining-20260913'
def invoke(app,key,args,timeout=300):
    dest=RUN/'evidence'/f'{app}-{key}.json'
    assert not dest.exists(),dest
    ws=RUN/app
    env=dict(os.environ,HWPDOC_PC_DATA=str(OLD/'pc'),HWPDOC_WORKSPACE=str(ws),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
    begin=now();start=time.monotonic()
    try:
        r=subprocess.run(list(map(str,args)),cwd=ws,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        result={'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:
        dec=lambda x:x.decode('utf-8',errors='replace') if isinstance(x,bytes) else (x or '')
        result={'exit_code':124,'stdout':dec(e.stdout),'stderr':dec(e.stderr),'timeout':True}
    result.update(at=begin,seconds=time.monotonic()-start,argv=list(map(str,args)),cwd=str(ws),host=app)
    save(dest,result);print(app,key,result['exit_code'],flush=True);return result
def cli(app,key,*args):return invoke(app,key,[PY,'-B','-X','utf8',ROOT/'scripts/teacher_doc.py','--workspace',RUN/app,*args])
def payload(m):return hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='draft_approval'},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def prepare_workspaces():
    values=read(RUN/'proposed-values.json');w2=read(RUN/'sources/w2_sources.json')
    for app in ['codex','claude','vscode']:
        ws=RUN/app;assert not ws.exists();ws.mkdir()
        (ws/'.hwpdoc').mkdir();(ws/'inputs').mkdir();(ws/'test-copy').mkdir()
        save(ws/'.hwpdoc/workspace.json',{'kind':'hwpdoc-workspace','version':1,'app':'claude' if app!='codex' else 'codex','school':{'name':'가람중학교','academic_year':2026},'delivery':{'external_copy':str(ws/'test-copy')},'references':{'related':'inputs/approved-workflow/related'},'preferences':read(RUN/'sources/policy.json')['preferences']})
        shutil.copytree(OLD/'codex-marked/inputs/approved-workflow',ws/'inputs/approved-workflow')
        shutil.copy2(OLD/'codex-marked/inputs/form.hwpx',ws/'inputs/form.hwpx')
        shutil.copy2(OLD/'workflow-drafts.md',ws/'inputs/workflow-drafts.md')
        shutil.copytree(OLD/'codex-marked/.hwpdoc/templates/trial-gianmun',ws/'.hwpdoc/templates/trial-gianmun')
        for name in ['가정통신문','가정통신문-회신형']:
            shutil.copytree(ROOT/'.hwpdoc/templates'/name,ws/'.hwpdoc/templates'/name)
        shutil.copytree(RUN/'sources',ws/'inputs/branch-sources')
        evidence={'status':'unsupported','steps':[],'conditions':['가상 시험 전용 자료. 실제 학교 업무·외부 전송 없음.'],'exceptions':['업무지침 MCP 원문 조회 성공을 주장하지 않음.'],'pending_items':[],'reviewed_at':now(),'freshness':'verified','freshness_scope':'Frozen fixture only','fallback_sources':[{'path':'inputs/branch-sources/w2_sources.json','sha256':sha(ws/'inputs/branch-sources/w2_sources.json')}]}
        save(ws/'inputs/branch-evidence.json',evidence)
        shutil.copy2(RUN/'drafts.md',ws/'inputs/branch-drafts.md');draft_time=now()
        for name,slots in values.items():
            m=read(ws/'inputs/approved-workflow'/('w1.json' if name in ('notice','reply') else 'w2.json'))
            for k in ['source','source_sha256','reference','reference_sha256','generation_record','paragraph_visual_record']:m.pop(k,None)
            kind=name if name in ('notice','reply') else 'gianmun'
            if kind in ('notice','reply'):
                tid='가정통신문' if kind=='notice' else '가정통신문-회신형'
                reg=read(ws/'.hwpdoc/templates'/tid/'legacy-1/registration.json')
                m.update(document_type=reg['purposes'][0],template={'id':tid,'version':'legacy-1','sha256':sha(ws/'.hwpdoc/templates'/tid/'legacy-1/template.hwpx')},base_provenance=reg['provenance'])
            m.update(job_id=f'branch-{name}-20260913',slots={'template_sha256':m['template']['sha256'],'values':slots},sources=[{'path':f'inputs/branch-sources/{kind}.hwpx','sha256':sha(ws/f'inputs/branch-sources/{kind}.hwpx')},{'path':'inputs/branch-sources/w2_sources.json','sha256':sha(ws/'inputs/branch-sources/w2_sources.json')}],evidence={'record':'inputs/branch-evidence.json','sha256':sha(ws/'inputs/branch-evidence.json')},draft={'path':'inputs/branch-drafts.md','sha256':sha(ws/'inputs/branch-drafts.md'),'created_at':draft_time},environment={'app':{'codex':'Codex Desktop','claude':'Claude Code CLI','vscode':'VS Code Claude Code extension'}[app],'scope':'Synthetic branch acceptance; execution host must be verified separately'},draft_approval={'confirmed':False,'by':None,'at':None,'record':'New branch drafts awaiting actual user confirmation','input_sha256':None})
            if name in ('notice','reply'):
                olddates=['2025. 3. 25.'] if name=='notice' else ['2026. 8. 28.','2026. 8. 20.']
                names=['화동','기출문제','사교육비','저작권'] if name=='notice' else ['화동','농어촌','수리과학체험','동해','항해사']
                m['reuse_review']={'record':'Frozen native template slots read before drafting; visible old names/dates replaced, structure retained.','names':names,'dates':olddates}
                m['content_rules']={'require':['가람중학교' if name=='notice' else '가람과학관','과학 독서 나눔 안내' if name=='notice' else '보호자'],'forbid':names+olddates}
                m['unresolved']=['문서번호','교무실 연락처','행정실 연락처','누리집','주소']+(['배부일','대상','인솔 인원','회신 제출처'] if name=='reply' else [])
                m['exploration']={'record':'Current native five-template original and extracted slot addresses read; repeated layout, five separate activity rows and signature/date position retained.'}
                if name=='reply':m['activities']=[{'location':'일정표 활동내용','items':[a[1] for a in read(RUN/'sources/activities.json')['five']],'slot_keys':[f'p:{26+3*i}' for i in range(5)]}]
            else:
                m['received']['submission_method']=name;m['received']['source_quote']=w2['variants'][name]
                m['unresolved']=['실제 이메일 주소 미확인'] if name=='email' else []
            save(ws/'inputs'/f'branch-{name}.json',m)
        m=copy.deepcopy(read(ws/'inputs/branch-official_reply.json'))
        m['job_id']='branch-unknown-20260913';m['received']['submission_method']='unknown';m['received']['source_quote']=w2['variants']['unknown']
        save(ws/'inputs/branch-unknown.json',m)
        # Only the exact historically approved wording is reusable for a new host.
        for flow in ['w1','w2']:
            m=read(ws/'inputs/approved-workflow'/f'{flow}.json')
            m['job_id']=f'vscode-approved-{flow}-20260913'
            m['environment']={'app':'VS Code Claude Code extension','scope':'Unchanged user-approved W1 / W2 system wording; fresh host run. No new semantic or layout approval.'}
            m['draft_approval']['record']+='; same approved content reused on VS Code under the current explicit test request'
            m['draft_approval']['input_sha256']=payload(m)
            save(ws/'inputs'/f'vscode-approved-{flow}.json',m)
    save(RUN/'preparation-correction.json',{'at':now(),'draft_sha256':sha(RUN/'drafts.md'),'correction':'General notice title is 8 non-space characters, not 9. Proposed text unchanged. Approval remains pending.'})
    print('workspaces ready')
def preflight(app):
    results=[]
    for name in ['notice','reply','official_reply','email','unknown']:
        r=cli(app,'preflight-'+name,'build','--manifest',f'inputs/branch-{name}.json')
        folder=RUN/app/'.hwpdoc/jobs'/f'branch-{name}-20260913'
        p=read(folder/'preflight.json')
        assert r['exit_code']==2 and any('사용자 초안 확인 기록' in s for s in p['errors'])
        if name=='unknown':assert any('W2 제출 방법 미확인' in s for s in p['errors'])
        assert not (folder/'work.hwpx').exists() and not (folder/'report.json').exists()
        results.append({'case':name,'exit_code':r['exit_code'],'errors':p['errors'],'generated':False})
    save(RUN/'evidence'/f'{app}-preflight-summary.json',{'at':now(),'scope':'Actual unapproved-input rejection, not full workflow acceptance','results':results})
def parent_processes():
    import ctypes
    from ctypes import wintypes
    class ProcessEntry(ctypes.Structure):
        _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),('th32ProcessID',wintypes.DWORD),('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),('dwFlags',wintypes.DWORD),('szExeFile',wintypes.WCHAR*260)]
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];k.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    k.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(ProcessEntry)];k.Process32NextW.argtypes=k.Process32FirstW.argtypes
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=k.CreateToolhelp32Snapshot(2,0)
    if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    rows={}
    try:
        entry=ProcessEntry();entry.dwSize=ctypes.sizeof(entry);more=k.Process32FirstW(handle,ctypes.byref(entry))
        while more:
            rows[entry.th32ProcessID]={'pid':entry.th32ProcessID,'parent_pid':entry.th32ParentProcessID,'name':entry.szExeFile}
            more=k.Process32NextW(handle,ctypes.byref(entry))
    finally:k.CloseHandle(handle)
    found=[];pid=os.getpid();seen=set()
    while pid in rows and pid not in seen:
        seen.add(pid);found.append(rows[pid]);pid=rows[pid]['parent_pid']
    return found
def vscode_approved():
    ancestry=parent_processes()
    if not any(p['name'].lower()=='code.exe' for p in ancestry):raise RuntimeError('VS Code ancestor absent: do not count this as VS Code acceptance')
    save(RUN/'evidence/vscode-process-ancestry.json',ancestry)
    for flow in ['w1','w2']:
        if flow=='w1':
            r=cli('vscode','approved-w1-build','build','--manifest','inputs/vscode-approved-w1.json')
            if r['exit_code']:raise RuntimeError('VS Code W1 build failed; inspect preserved evidence and do not retry automatically')
        else:
            ws=RUN/'vscode';folder=ws/'inputs/approved-workflow'
            receipt=read(folder/'w2-candidate-visual.json')
            # Existing image observation remains valid for byte-identical input/output.
            assert receipt['confirmed'] and sha(folder/'w2-generated.hwpx')==receipt['document_sha256']
            m=read(ws/'inputs/vscode-approved-w2.json')
            save(ws/'inputs/vscode-w2-values.json',m['slots']['values'])
            r=invoke('vscode','approved-w2-generate',[PY,'-B','-X','utf8',ROOT/'.claude/skills/hwpx/scripts/edit_hwpx.py',ws/'.hwpdoc/templates/trial-gianmun/1/template.hwpx','-o',ws/'inputs/vscode-w2-generated.hwpx','--slot-json',ws/'inputs/vscode-w2-values.json','--allow-over-budget','--verified-by-render'])
            if r['exit_code']:raise RuntimeError('VS Code W2 generation failed; inspect preserved evidence and do not retry automatically')
            assert sha(ws/'inputs/vscode-w2-generated.hwpx')==receipt['document_sha256']
            m['source']='inputs/vscode-w2-generated.hwpx';m['source_sha256']=sha(ws/m['source'])
            m['draft_approval']['input_sha256']=payload(m)
            save(ws/'inputs/vscode-approved-w2.json',m)
        r=cli('vscode',f'approved-{flow}-validate','validate',*(['--job',f'vscode-approved-{flow}-20260913'] if flow=='w1' else ['--manifest','inputs/vscode-approved-w2.json']))
        if r['exit_code']:raise RuntimeError(f'VS Code {flow} validation failed; inspect preserved evidence and do not retry automatically')
        r=cli('vscode',f'approved-{flow}-deliver','deliver','--job',f'vscode-approved-{flow}-20260913')
        if r['exit_code']:raise RuntimeError(f'VS Code {flow} delivery failed; inspect preserved evidence and do not retry automatically')
    print('VS Code approved W1/W2 flow finished; current rendered review still requires image observation.')
if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare_workspaces()
    elif sys.argv[1]=='preflight':preflight(sys.argv[2])
    elif sys.argv[1]=='vscode-approved':vscode_approved()
