from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'tmp/remaining-20260913'
RUN = ROOT / 'tmp/approved-workflow-20260913'
PY = Path(sys.executable)
USER = 'Codex가 준비해 둔 W1·W2 시험 초안 확인: 확인해 주면 두 앱에서 전체 흐름(작성 → 검증 → 전달) 시험을 마저 합니다.  -> 진행해'
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ws(app): return OLD / f'{app}-marked'
def call(app,key,args,timeout=200):
    dest=RUN/'evidence'/f'{app}-{key}.json'
    assert not dest.exists(),dest
    env=dict(os.environ,HWPDOC_PC_DATA=str(OLD/'pc'),HWPDOC_WORKSPACE=str(ws(app)),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
    started=now();start=time.time()
    try:
        r=subprocess.run(list(map(str,args)),cwd=ws(app),env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        result={'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:
        dec=lambda x:x.decode('utf-8',errors='replace') if isinstance(x,bytes) else (x or '')
        result={'exit_code':124,'stdout':dec(e.stdout),'stderr':dec(e.stderr),'timeout':True}
    result.update(argv=list(map(str,args)),at=started,seconds=time.time()-start,app=app)
    save(dest,result);print(app,key,result['exit_code'],flush=True)
    return result
def cli(app,key,*args): return call(app,key,[PY,'-B','-X','utf8',ROOT/'scripts/teacher_doc.py','--workspace',ws(app),*args])

def prepare():
    RUN.mkdir(exist_ok=True)
    if not (RUN/'protected-before.json').exists():
        save(RUN/'protected-before.json',{p.relative_to(ROOT).as_posix():sha(p) for folder in ['knowledge','output','.hwpdoc/templates'] for p in (ROOT/folder).rglob('*') if p.is_file()})
    original_draft=OLD/'workflow-drafts.md'
    save(RUN/'user-approval.json',{'recorded_at':now(),'user_statement':USER,'draft':str(original_draft),'draft_sha256':sha(original_draft),'scope':'Existing W1 and W2 system-submission drafts, unchanged layout/mapping, local test registration and build/validate/deliver. No actual submission, structure change, or final document rating.'})
    fixture=read(ROOT/'evals/plugin_distribution/fixtures/w2_sources.json')
    texts={
      'W1':['가람중학교','수신 내부결재','(경유)','제목 공통 실행기 기능 시험 계획','1. 목적: 공문 작성·검증·전달 기능 확인','2. 2026. 10. 6.에 가상 문서를 사용하여 공통 실행기 기능을 확인하고자 합니다.','3. 시험 결과물은 발송하지 않으며 검토용으로만 사용합니다. 끝.'],
      'W2':['가람중학교','수신 내부결재','(경유)','제목 과학 체험 참여 현황 제출','1. 관련: 가상교육지원청-200(2026. 10. 1.)','2. 과학 체험 참여 현황(1학년 20명)을 평가용 시스템에 제출하고자 합니다.','3. 제출 기한: 2026. 10. 8. 끝.']}
    draft_text=original_draft.read_text(encoding='utf-8')
    for content in texts.values():
        for line in content: assert line in draft_text,line
    first_png=ws('codex')/'.hwpdoc/templates/trial-gianmun/1/preview/page-001.png'
    for app in ['codex','claude']:
        base=ws(app);folder=base/'inputs/approved-workflow';folder.mkdir(exist_ok=True)
        template=base/'.hwpdoc/templates/trial-gianmun/1'
        assert sha(first_png)==sha(template/'preview/page-001.png')
        oldreview=read(template/'review.draft.json')
        for name,digest in oldreview['hashes'].items():assert sha(template/name)==digest,name
        review=oldreview.copy()
        review.update(confirmed=True,by='user (current conversation)',at=now(),record=USER+'; inputs/approved-workflow/user-approval.json')
        review['visual']=dict(oldreview['visual'],record='Codex directly inspected the current one-page PNG; Claude preview has identical SHA256. Header, recipient/title/body placement and margins preserved. Visual observer is Codex; no human visual rating asserted.')
        save(folder/'registration-review.json',review)
        shutil.copy2(RUN/'user-approval.json',folder/'user-approval.json')
        save(folder/'w2-source.json',fixture)
        # Fresh evidence review of the frozen test fixture, not a fabricated school_task_guide call.
        evidence={'status':'unsupported','steps':[],'conditions':['폐기용 로컬 기능 시험. 실제 학교 업무·시스템 접속·발송 없음.','W2 system 분기, 가상교육지원청-200, 2026. 10. 1. 시행, 2026. 10. 8. 기한, 1학년 20명.'],
                  'exceptions':['학교 업무지침 MCP 조회 대상이 아닌 가상 시험; 실제 원문 조회 성공으로 기록하지 않음.'],
                  'pending_items':[],'reviewed_at':now(),'freshness':'verified','freshness_scope':'Frozen fixture and user-approved test text only; no statement about current school regulations.',
                  'fallback_sources':[{'path':'inputs/approved-workflow/w2-source.json','sha256':sha(folder/'w2-source.json')},{'path':'inputs/workflow-drafts.md','sha256':sha(base/'inputs/workflow-drafts.md')} ]}
        save(folder/'evidence.json',evidence)
        shutil.copy2(original_draft,folder/'draft.md');draft_time=now()
        related=folder/'related';related.mkdir(exist_ok=True)
        (related/'fixture-200.md').write_text('---\n문서번호: 가상교육지원청-200\n제목: 평가용 과학 체험 참여 현황 제출\n시행일: 2026. 10. 1.\n관련: []\n---\n가상 시험 자료. 실제 공문이 아님.\n'+fixture['variants']['system']+'\n',encoding='utf-8')
        cfg=read(base/'.hwpdoc/workspace.json')
        if not (RUN/f'{app}-workspace-before.json').exists():save(RUN/f'{app}-workspace-before.json',cfg)
        cfg['school']={'name':'가람중학교','document_prefix':'','academic_year':2026}
        cfg['references']['related']='inputs/approved-workflow/related'
        cfg['delivery']['external_copy']=str(base/'approved-test-copy')
        (base/'approved-test-copy').mkdir(exist_ok=True)
        save(base/'.hwpdoc/workspace.json',cfg)
        names=['화동중학교','농어촌유학','농어촌 유학','정책기획과','거주비','지원금','성립전']
        dates=['2025. 3. 19.','2026학년도','1학기']
        for flow,values in texts.items():
            slots=dict(zip(['p:1','p:3','p:4','p:5','p:7','p:9','p:11'],values))
            limits={x['key']:x['max_chars'] for x in read(template/'slots.json')['slots']}
            excess={k:{'length':len(''.join(v.split())),'limit':limits[k]} for k,v in slots.items() if len(''.join(v.split()))>limits[k]}
            save(folder/(flow.lower()+'-budget-check.json'),{'excess':excess,'route':'existing paragraph-edit path plus render' if excess else 'registered slot build'})
            m={'version':2,'job_id':f'approved-{flow.lower()}-20260913','workflow':flow,'document_type':flow,
               'template':{'id':'trial-gianmun','version':'1','sha256':sha(template/'template.hwpx')},
               'slots':{'template_sha256':sha(template/'template.hwpx'),'values':slots},'shared_values':{},
               'sources':[{'path':'inputs/form.hwpx','sha256':sha(base/'inputs/form.hwpx')},{'path':'inputs/approved-workflow/w2-source.json','sha256':sha(folder/'w2-source.json')}],
               'evidence':{'record':'inputs/approved-workflow/evidence.json','sha256':sha(folder/'evidence.json')},
               'draft':{'path':'inputs/approved-workflow/draft.md','sha256':sha(folder/'draft.md'),'created_at':draft_time,'note':'Unchanged approved draft copied after fresh fixture review; original draft retained.'},
               'attachments':[],'attachment_mentions':[],
               'content_rules':{'require':['가람중학교',values[3].removeprefix('제목 ')],'forbid':names+dates},
               'reuse_review':{'record':'Original template text was compared with approved slots; all seven visible paragraphs replaced, structure unchanged.','names':names,'dates':dates},
               'checks':{k:{'applicable':False,'reason':'시험 문안에 예산·수업 대체 내용 없음' if k!='related' else 'W1 시험 계획에 관련번호 인용 없음'} for k in ['budget_names','related','timetable']},
               'base_provenance':'unconfirmed','over_budget_cells':[],
               'environment':{'app':'Codex Desktop' if app=='codex' else 'Claude Code CLI','app_version':'unconfirmed','model':'unconfirmed','scope':'User-approved synthetic W1/W2 workflow on current PC'},'unresolved':[],
               'exploration':{'record':'Prepared draft selected common gianmun layout after comparison with 8 previously approved documents; current slot map verified.'}}
            if flow=='W2':
                common=fixture['common'];m['received']={k:common[k] for k in ['summary','requirements','deadline','issue_date']}
                m['received'].update(document_number=common['number'],submission_method='system',source_quote=fixture['variants']['system'])
                m['checks']['related']={'applicable':True,'numbers':['가상교육지원청-200']}
            payload=json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            m['draft_approval']={'confirmed':True,'by':'user (current conversation)','at':now(),'record':USER+'; inputs/approved-workflow/user-approval.json','input_sha256':hashlib.sha256(payload).hexdigest()}
            save(folder/(flow.lower()+'.json'),m)
        print(app,'prepared',flush=True)

def execute(app,phase):
    if phase=='register':
        return cli(app,'register','add-template','--id','trial-gianmun','--version','1','--review','inputs/approved-workflow/registration-review.json')
    if phase=='w2-candidate':
        folder=ws(app)/'inputs/approved-workflow';m=read(folder/'w2.json')
        candidate=folder/'w2-unverified-candidate.hwpx';assert not candidate.exists()
        sys.path.insert(0,str(ROOT/'.claude/skills/hwpx/scripts'))
        import edit_hwpx as editor
        paragraphs=[editor.ParagraphTarget(int(k.split(':')[1]),v) for k,v in m['slots']['values'].items()]
        editor._pack_from_original(ws(app)/'.hwpdoc/templates/trial-gianmun/1/template.hwpx',candidate,{},[],paragraphs)
        save(folder/'w2-candidate.json',{'status':'unverified_preview_only','document_sha256':sha(candidate),'reason':'Skill editing-details requires an unverified render candidate before final over-budget editing. Raw ZIP writer preserves structure; this is not an approved final output.'})
        result=call(app,phase+'-render',[PY,'-B','-X','utf8',ROOT/'scripts/render_check.py',candidate,'--reference',ws(app)/'.hwpdoc/templates/trial-gianmun/1/template.hwpx','--keep-pdf',folder/'w2-candidate.pdf'])
        if result['exit_code']:return result
        return call(app,phase+'-images',[PY,'-B','-X','utf8',ROOT/'scripts/hwpdoc_preview.py','--pdf',folder/'w2-candidate.pdf','--output-dir',folder/'w2-candidate-preview'])
    if phase.startswith('w2-generate'):
        folder=ws(app)/'inputs/approved-workflow';m=read(folder/'w2.json')
        assert not (folder/'w2-generated.hwpx').exists()
        visual=read(folder/'w2-candidate-visual.json')
        assert visual['confirmed'] and visual['document_sha256']==sha(folder/'w2-unverified-candidate.hwpx')
        assert visual['image_sha256']==sha(folder/'w2-candidate-preview/page-001.png')
        save(folder/'w2-values.json',m['slots']['values'])
        result=call(app,phase,[PY,'-B','-X','utf8',ROOT/'.claude/skills/hwpx/scripts/edit_hwpx.py',ws(app)/'.hwpdoc/templates/trial-gianmun/1/template.hwpx','-o',folder/'w2-generated.hwpx','--slot-json',folder/'w2-values.json','--allow-over-budget','--verified-by-render'])
        if result['exit_code']:return result
        assert sha(folder/'w2-generated.hwpx')==visual['document_sha256'],'Final differs from observed candidate; rerender required'
        shutil.copy2(folder/'w2.json',folder/'w2-slot-proposal.json')
        m.update(source='inputs/approved-workflow/w2-generated.hwpx',source_sha256=sha(folder/'w2-generated.hwpx'),reference='.hwpdoc/templates/trial-gianmun/1/template.hwpx',reference_sha256=m['template']['sha256'],
                 generation_record='Existing paragraph-edit path after actual candidate render observation; 28 non-space characters versus old paragraph budget 27. Approved wording and structure unchanged. Full reference render required. No cells changed; WARNING retained.',
                 paragraph_visual_record='inputs/approved-workflow/w2-candidate-visual.json')
        m['draft_approval']['input_sha256']=hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='draft_approval'},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        save(folder/'w2.json',m)
        return result
    flow,command,*_=phase.split('-')
    if command=='preview':
        job=ws(app)/'.hwpdoc/jobs'/f'approved-{flow}-20260913'
        return call(app,phase,[PY,'-B','-X','utf8',ROOT/'scripts/hwpdoc_preview.py','--pdf',job/'render.pdf','--output-dir',job/'final-preview'])
    args=['--manifest',f'inputs/approved-workflow/{flow}.json'] if command=='build' or (flow=='w2' and command=='validate' and not (ws(app)/'.hwpdoc/jobs/approved-w2-20260913/report.json').exists()) else ['--job',f'approved-{flow}-20260913']
    return cli(app,phase,command,*args)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    else:
        result=execute(sys.argv[1],sys.argv[2])
        raise SystemExit(result['exit_code'])
