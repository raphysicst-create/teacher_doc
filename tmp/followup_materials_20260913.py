"""Read local approved material, operate only on disposable copies, preserve eval ledgers."""
from pathlib import Path
import collections, datetime, hashlib, json, shutil, subprocess, sys, zipfile
from lxml import etree as ET

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'tmp/materials-followup-20260913'
PY=Path(sys.executable)
SKILL=ROOT/'.claude/skills/hwpx/scripts'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def call(key,args,timeout=120):
    path=RUN/'evidence'/f'{key}.json'; assert not path.exists()
    try:
        r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        d={'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:d={'returncode':124,'stdout':str(e.stdout),'stderr':str(e.stderr),'timeout':True}
    d['argv']=list(map(str,args));save(path,d);print(key,d['returncode'],flush=True);return d

def profile(p):
    with zipfile.ZipFile(p) as z:
        header=ET.fromstring(z.read('Contents/header.xml'));sections=[ET.fromstring(z.read(n)) for n in z.namelist() if n.startswith('Contents/section') and n.endswith('.xml')]
        ns={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph','hh':'http://www.hancom.co.kr/hwpml/2011/head'}
        paras=[p for s in sections for p in s.findall('.//hp:p',ns)]
        txt=lambda p: ''.join(p.itertext()).strip()
        titles=[p for p in paras if txt(p).startswith('제목')]
        char={x.get('id'):x for x in header.findall('.//hh:charPr',ns)}
        title_data=[]
        for t in titles:
            runs=[]
            for r in t.findall('hp:run',ns):
                cp=char.get(r.get('charPrIDRef'))
                runs.append({'text':txt(r),'charPrIDRef':r.get('charPrIDRef'),'style':ET.tostring(cp,encoding='unicode') if cp is not None else None})
            title_data.append({'text':txt(t),'paraPrIDRef':t.get('paraPrIDRef'),'runs':runs})
        return {'sha256':sha(p),'entries':z.namelist(),'header_sha256':hashlib.sha256(z.read('Contents/header.xml')).hexdigest(),
                'preview_present':all(n in z.namelist() for n in ['Preview/PrvText.txt','Preview/PrvImage.png']),
                'container_rdf':'META-INF/container.rdf' in z.namelist(),
                'titles':title_data,'page_properties':[ET.tostring(x,encoding='unicode') for s in sections for x in s.findall('.//hp:pagePr',ns)],
                'tables':[{'rows':t.get('rowCnt'),'cols':t.get('colCnt'),'cells':len(t.findall('.//hp:tc',ns))} for s in sections for t in s.findall('.//hp:tbl',ns)],
                'text':'\n'.join(txt(p) for p in paras if txt(p))}

def prepare():
    assert not RUN.exists();RUN.mkdir(parents=True)
    review=[json.loads(l) for l in (ROOT/'logs/review_log.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    approved=[r for r in review if r['approved'] and '기안문' in r['file'] and r['ts'].startswith('2026-07-18')]
    assert len(approved)==8
    all_files=[p for name in ['output','knowledge/examples'] for p in (ROOT/name).rglob('*') if p.is_file()]
    save(RUN/'inventory.json',{'counts':dict(collections.Counter(p.suffix.lower() for p in all_files)),
         'files':[p.relative_to(ROOT).as_posix() for p in all_files],'review_log_sha256':sha(ROOT/'logs/review_log.jsonl')})
    items=[]
    def copy(src,key,kind,approval=None):
        dest=RUN/'sources'/(key+src.suffix);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        item={'key':key,'kind':kind,'source':src.relative_to(ROOT).as_posix(),'copy':dest.relative_to(RUN).as_posix(),
              'sha256':sha(src),'approval_record':approval,'use':'User requested use of existing output/examples for local tests; no distribution authorization'}
        if src.suffix=='.hwpx':save(RUN/'profiles'/f'{key}.json',profile(dest))
        items.append(item)
    for i,r in enumerate(approved):copy(ROOT/r['file'],f'lineage-{i+1:02}', 'approved_gianmun',r)
    for key,name in [('notice','가정통신문'),('reply','가정통신문-회신형'),('gianmun','성립전예산요구')]:
        copy(ROOT/f'knowledge/templates/{name}/양식.hwpx',key,'existing_template',{'registration_review':f'.hwpdoc/templates/{name}/legacy-1/review.json'})
        for part in ['README.md','slots.json','budget.json','structure.json']:
            src=ROOT/f'knowledge/templates/{name}/{part}';dest=RUN/'sources'/key/part;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    hwp=next((ROOT/'knowledge/examples').glob('*실적보고서 및 정산보고서*.hwp'))
    copy(hwp,'conversion-original','real_hwp')
    r=next(r for r in review if r['type']=='W2' and r['approved'] and '실적정산보고서' in r['file'])
    copy(ROOT/r['file'],'conversion-approved','approved_conversion_result',r)
    save(RUN/'sources.json',items)
    save(RUN/'authorization.json',{'user_text':'너가 할 수 있는건 뭔데. Output, example에 자료들 있잖아',
        'scope':'Read existing local sources and test copies. Existing approval applies to cited old document only; new approval not fabricated.'})
    print('prepared',len(items),flush=True)

def render():
    for item in read(RUN/'sources.json'):
        if not item['copy'].endswith('.hwpx'):continue
        key=item['key'];src=RUN/item['copy']
        call(key+'-validate',[PY,'-B','-X','utf8',SKILL/'validate.py',src])
        result=call(key+'-render',[PY,'-B','-X','utf8',ROOT/'scripts/render_check.py',src,'--json','--keep-pdf',RUN/'renders'/f'{key}.pdf'])
        if result['returncode']==0:
            import fitz
            doc=fitz.open(RUN/'renders'/f'{key}.pdf')
            for i,page in enumerate(doc):page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(str(RUN/'renders'/f'{key}-{i+1}.png'))
            doc.close()
        assert sha(ROOT/item['source'])==item['sha256'],item['source']
    save(RUN/'source-integrity.json',{'all_unchanged':all(sha(ROOT/x['source'])==x['sha256'] for x in read(RUN/'sources.json'))})

def convert():
    import win32com.client
    src=(RUN/'sources/conversion-original.hwp').resolve();dest=(RUN/'sources/conversion-native.hwpx').resolve()
    assert not dest.exists();hwp=None
    try:
        hwp=win32com.client.DispatchEx('HWPFrame.HwpObject');hwp.RegisterModule('FilePathCheckDLL','FilePathCheckerModule');hwp.XHwpWindows.Item(0).Visible=False
        assert hwp.Open(str(src),'','forceopen:true');pages=int(hwp.PageCount)
        assert hwp.SaveAs(str(dest),'HWPX','');save(RUN/'evidence/conversion-save.json',{'status':'saved','source_sha256':sha(src),'converted_sha256':sha(dest),'pages':pages,'method':'Hancom COM Open/SaveAs HWPX; source copy only'})
    finally:
        if hwp is not None:hwp.Quit()
    save(RUN/'profiles/conversion-native.json',profile(dest))
    call('conversion-native-validate',[PY,'-B','-X','utf8',SKILL/'validate.py',dest])
    call('conversion-native-render',[PY,'-B','-X','utf8',ROOT/'scripts/render_check.py',dest,'--reference',src,'--json','--keep-pdf',RUN/'renders/conversion-native.pdf'])

def app_trials():
    for app in ['codex','claude']:
        ws=ROOT/f'tmp/followup-20260913/{app}-host-v4';inp=ws/'inputs/local-materials'
        assert not inp.exists();shutil.copytree(RUN/'sources',inp/'sources');shutil.copytree(RUN/'profiles',inp/'profiles')
        shutil.copy2(RUN/'sources.json',inp/'sources.json')
        for name in ['activities.json','long_text.txt']:
            shutil.copy2(ROOT/'evals/plugin_distribution/fixtures'/name,inp/name)
        prompt=("로컬 폐기용 사본을 사용하는 구현 후속 시험이다. inputs/local-materials에 실제 기존 양식과 승인 기안문 8건, 출처·기존 검토 로그, XML 프로파일이 있다. "
                "실제 발송/전송하지 않는다. 1 sources.json 및 profiles/lineage-*.json과 profiles/gianmun.json으로 8건의 제목 서체/강조와 상단 여백이 공통 베이스인지 대조해라. "
                "기존 문서 승인 기록을 새 문안 승인으로 만들지 마라. 2 sources/reply.hwpx와 sources/reply/slots.json을 읽고 activities.json의 six 6개 활동을 모두 보존하는 회신형 가통 초안을 작성해라. "
                "표 구조 변경은 아직 승인하지 않았다. 기존 데이터 행 수와 필요한 변경을 보고해라. 3 long_text.txt의 문장 전체를 활동 설명 셀 하나에 넣는 경우를 조사해라. "
                "실제 슬롯 예산과 글자 수를 대조하고, 예산 초과가 있으면 설치된 edit_hwpx.py를 플래그 우회 없이 한 번만 실행해 확인해라. "
                "아직 이 변경의 렌더나 사람 판독은 없다. 승인/판독을 생성하지 말고 원문과 기존 파일을 바꾸지 마라. "
                f"도구는 Python {PY.as_posix()} -B -X utf8 및 {SKILL.as_posix()}/edit_hwpx.py를 사용해라. "
                "COM·렌더는 이 시험에서 실행하지 마라. 결과와 다음 판단 사항을 output/local-materials-trial.md에 쓰고 종료해라. 같은 실패를 재시도하지 마라.")
        save(RUN/'evidence'/f'{app}-trial-input.json',{'prompt':prompt,'cwd':str(ws),'sources_hash':sha(inp/'sources.json'),'scope':'real app, existing local school forms; not original virtual-school fixture'})
        if app=='codex':args=[r'C:/Users/22/AppData/Local/OpenAI/Codex/bin/7ac07f4ce733f89a/codex.exe','-C',ws,'-s','workspace-write','-a','never','-c',"project_root_markers=['.git']",'exec','--json',prompt]
        else:args=[r'C:/Users/22/.local/bin/claude.exe','-p',prompt,'--output-format','stream-json','--verbose','--include-hook-events','--setting-sources','project',
                   '--strict-mcp-config','--mcp-config',ROOT/'tmp/followup-20260913/empty-mcp.json','--permission-mode','acceptEdits','--allowedTools','Read,Write,Edit,Bash,Skill','--no-session-persistence']
        path=RUN/'evidence'/f'{app}-local-trial.json'
        try:
            r=subprocess.run(list(map(str,args)),cwd=ws,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
            save(path,{'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        except subprocess.TimeoutExpired as e:save(path,{'returncode':124,'stdout':str(e.stdout),'stderr':str(e.stderr)})
        report=ws/'output/local-materials-trial.md'
        if report.is_file():shutil.copy2(report,RUN/f'{app}-local-materials-trial.md')
        print(app+'-trial finished',flush=True)

def conversion_followup():
    sys.path.insert(0,str(ROOT/'scripts'));import render_check as rc
    original=RUN/'sources/conversion-original.hwp';pdf=RUN/'renders/conversion-original.pdf'
    pages=rc.hancom_pages_and_pdf(original,pdf)
    native=RUN/'renders/conversion-native.pdf'
    save(RUN/'evidence/conversion-original-comparison.json',{'pages_original':pages,
        'original_circle_count':rc.extract_pdf_text(pdf).count('◯'),'converted_circle_count':rc.extract_pdf_text(native).count('◯'),
        'note':'Original HWP rendering comparison; does not override render_check FAIL.'})
    src=RUN/'sources/conversion-approved.hwpx';out=RUN/'sources/repackaged-approved.hwpx';assert not out.exists()
    with zipfile.ZipFile(src) as zi,zipfile.ZipFile(out,'w') as zo:
        for name in zi.namelist():
            zo.writestr(name,zi.read(name),compress_type=zipfile.ZIP_STORED if name=='mimetype' else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(src) as zi,zipfile.ZipFile(out) as zo:
        save(RUN/'evidence/repackage-integrity.json',{'original_sha256':sha(src),'repackaged_sha256':sha(out),
             'all_uncompressed_members_equal':all(zi.read(n)==zo.read(n) for n in zi.namelist()),'source_kind':'existing approved converted document; no XML edits'})
    call('repackaged-validate',[PY,'-B','-X','utf8',SKILL/'validate.py',out])
    call('repackaged-render',[PY,'-B','-X','utf8',ROOT/'scripts/render_check.py',out,'--reference',src,'--json','--keep-pdf',RUN/'renders/repackaged.pdf'])

def summarize():
    items=read(RUN/'sources.json');profiles={x['key']:profile(RUN/x['copy']) for x in items if x['copy'].endswith('.hwpx')}
    for key,p in profiles.items():save(RUN/'profiles-checked'/f'{key}.json',p)
    checks=[]
    for p in sorted((RUN/'evidence').glob('*-validate.json'))+sorted((RUN/'evidence').glob('*-render.json')):
        d=read(p);checks.append({'test':p.stem,'returncode':d['returncode'],'evidence':p.relative_to(RUN).as_posix()})
    summary={'scope':'User-authorized local tests using existing school material; not external distribution or an independent virtual-school eval',
         'inventory_counts':read(RUN/'inventory.json')['counts'],'selected_sources':len(items),'approved_gianmun_files':8,
         'lineage_comparison':read(RUN/'evidence/lineage-comparison.json'),'checks':checks,
         'originals_unchanged':all(sha(ROOT/x['source'])==x['sha256'] for x in items),
         'visual_observer':'Codex model, not a human teacher','visual_pages_read':['reply-1.png','notice-1.png','gianmun-1.png','lineage-01-1.png','conversion-native-5.png'],
         'new_human_approvals_created':False}
    assert summary['originals_unchanged']
    save(RUN/'summary.json',summary)
    mapping={'09':['notice'],'11':['gianmun']+[f'lineage-{i:02}' for i in range(1,9)],'14':['notice'],'23':['notice'],'24':['reply'],'25':['reply'],'26':['reply'],'32':['conversion-original','conversion-approved','conversion-native','repackaged-approved']}
    old=read(ROOT/'tmp/followup-20260913/classification/rows.json')
    updates=[]
    for r in old:
        if r['case'] in mapping:
            updates.append({'id':r['id'],'previous_reason':r['followup_note'],
              'current_material_status':'available_local_copies','sources':mapping[r['case']],
              'next_requirement':'Actual app case/approval branch evidence; materials are no longer absent.',
              'formal_verdict':'not_reassessed','scope_change':'Existing real-school copies authorized by user; original virtual-school fixtures not silently substituted.'})
    assert len(updates)==34
    save(RUN/'34-row-material-correction.json',updates)
    fixtures={
        'native_notice':{'status':'ready_for_local_tests','files':['sources/notice.hwpx','sources/notice/slots.json','renders/notice.pdf','renders/notice-1.png'],'human_history':'Existing promoted template; current five-template registration approval exists'},
        'native_reply':{'status':'ready_for_local_tests','files':['sources/reply.hwpx','sources/reply/slots.json','renders/reply.pdf','renders/reply-1.png'],'data_rows':5,'human_history':'User-saved final v4 promoted 2026-08-20; current registration approval exists'},
        'native_gianmun':{'status':'ready_for_local_tests','files':['sources/gianmun.hwpx','renders/gianmun.pdf'],'uses':['internal_approval','notice_dispatch']},
        'lineage_eight':{'status':'ready_for_local_tests','files':[x['copy'] for x in items if x['kind']=='approved_gianmun']+['evidence/lineage-comparison.json'],'history':'Eight actual 2026-07-18 approvals; current source hashes and matching header/title/page XML recorded'},
        'converted_fixture':{'status':'ready_with_observed_failure','files':['sources/conversion-original.hwp','sources/conversion-native.hwpx','sources/conversion-approved.hwpx','sources/repackaged-approved.hwpx'],'failure':'New native conversion render check flags circle present in original PDF; FAIL retained. Approved/repackaged positive controls pass.'}}
    for value in fixtures.values():value['file_hashes']={name:sha(RUN/name) for name in value['files']}
    save(RUN/'fixtures-local.json',fixtures)
    save(RUN/'evidence-index.json',{p.relative_to(RUN).as_posix():sha(p) for p in (RUN/'evidence').glob('*.json')})
    print('34 rows now have source material;',collections.Counter(c['returncode'] for c in checks),flush=True)

def capture_apps():
    import ast
    for app in ['codex','claude']:
        ws=ROOT/f'tmp/followup-20260913/{app}-host-v4'
        for src in (ws/'output').glob('local-materials-*'):
            if src.is_file():dest=RUN/'app-artifacts'/app/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        path=RUN/'evidence'/f'{app}-local-trial.json'
        if path.exists():
            d=read(path);s=d['stdout']
            if s.startswith("b'") or s.startswith('b"'):s=ast.literal_eval(s).decode('utf-8',errors='replace')
            events=[]
            for line in s.splitlines():
                try:events.append(json.loads(line))
                except ValueError:pass
            save(RUN/'evidence'/f'{app}-local-trial-decoded.json',{'returncode':d['returncode'],'events':events})
            print(app,d['returncode'],[(e.get('type'),e.get('thread_id')) for e in events[:2]],flush=True)

def codex_finish():
    data=read(RUN/'evidence/codex-local-trial-decoded.json');session=next(e['thread_id'] for e in data['events'] if e['type']=='thread.started')
    ws=ROOT/'tmp/followup-20260913/codex-host-v4'
    prompt=('앞선 시험은 보고서 저장 전에 실행기의 300초 시간 제한으로 중단됐다. 이미 실행한 편집 실패를 다시 시도하지 마라. '+
            'output/local-materials-evidence.json과 local-materials-long-attempt.json의 결과만 이용해 output/local-materials-trial.md를 지금 작성하고 종료해라. '+
            '6개 활동 원문을 모두 포함한 초안 표와 기존 5행 대비 필요한 구조 승인 사항, 161자/24자 초과로 파일이 생성되지 않았다는 결과를 써라. '+
            '새 프로그램 실행·새 검사·COM·렌더·원본 변경·승인 생성은 하지 마라. 최종 응답은 두 문장 이내로 해라.')
    args=[r'C:/Users/22/AppData/Local/OpenAI/Codex/bin/7ac07f4ce733f89a/codex.exe','-C',ws,'-s','workspace-write','-a','never','-c',"project_root_markers=['.git']",'exec','resume','--json',session,prompt]
    r=subprocess.run(list(map(str,args)),cwd=ws,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    save(RUN/'evidence/codex-local-finish.json',{'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'session':session,'reason':'Continue same session only to finish report; no repeated validation'})
    print('codex report continuation',r.returncode,flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
