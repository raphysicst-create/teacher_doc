from pathlib import Path
import hashlib, json, re, sys, subprocess, zipfile
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'inputs/local-materials'
OUT = ROOT / 'output'
PY = 'C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe'
SCRIPT = Path('C:/Users/22/Desktop/maintain/Hwp_doc/.claude/skills/hwpx/scripts/edit_hwpx.py')
ns = {'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph', 'hh':'http://www.hancom.co.kr/hwpml/2011/head'}
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
before = {str(p.relative_to(BASE)):sha(p) for p in BASE.rglob('*') if p.is_file()}
sources = read(BASE/'sources.json')
baseprofile = read(BASE/'profiles/gianmun.json')
rows = []
for key in ['gianmun'] + [f'lineage-{n:02}' for n in range(1,9)]:
    source = next(s for s in sources if s['key']==key)
    profile = read(BASE/f'profiles/{key}.json')
    p = BASE/source['copy']
    with zipfile.ZipFile(p) as z:
        hb = z.read('Contents/header.xml'); header = E.fromstring(hb)
        section = E.fromstring(z.read('Contents/section0.xml'))
    titles = []
    for para in section.findall('.//hp:p',ns):
        txt = ''.join(para.xpath('./hp:run/hp:t//text()',namespaces=ns))
        if not txt.startswith('제목'): continue
        runs=[]
        for run in para.findall('hp:run',ns):
            rt=''.join(run.xpath('./hp:t//text()',namespaces=ns))
            if not rt: continue
            cid=run.get('charPrIDRef')
            cp=header.find(f'.//hh:charPr[@id="{cid}"]',ns)
            fr=cp.find('hh:fontRef',ns)
            fonts={}
            for lang,fid in fr.attrib.items():
                f=header.find(f'.//hh:fontface[@lang="{lang.upper()}"]/hh:font[@id="{fid}"]',ns)
                fonts[lang]=f.get('face') if f is not None else None
            runs.append({'text':rt,'charPrIDRef':cid,'height':cp.get('height'),'bold':cp.find('hh:bold',ns) is not None,'fonts':fonts,'profile_style_matches':E.tostring(cp,method='c14n')==E.tostring(E.fromstring(profile['titles'][len(titles)]['runs'][len(runs)]['style'].encode()),method='c14n')})
        titles.append({'text':txt,'paraPrIDRef':para.get('paraPrIDRef'),'runs':runs})
    margins=[dict(m.attrib) for m in section.findall('.//hp:pagePr/hp:margin',ns)]
    rows.append({'key':key,'source':source['source'],'sha256':sha(p),'hash_matches':sha(p)==source['sha256']==profile['sha256'],'header_matches_profile':hashlib.sha256(hb).hexdigest()==profile['header_sha256'],'header_matches_base':profile['header_sha256']==baseprofile['header_sha256'],'title':titles,'profile_title_matches': [t['text'] for t in titles]==[t['text'] for t in profile['titles']], 'profile_styles_equal_base':[[r['style'] for r in t['runs']] for t in profile['titles']]==[[r['style'] for r in t['runs']] for t in baseprofile['titles']], 'margins':margins,'profile_page_equal_base':profile['page_properties']==baseprofile['page_properties'],'margin_matches_profile':margins==[dict(E.fromstring(x.encode()).find('hp:margin',ns).attrib) for x in profile['page_properties']], 'approval_record':source['approval_record']})
reply = BASE/'sources/reply.hwpx'
with zipfile.ZipFile(reply) as z:
    root=E.fromstring(z.read('Contents/section0.xml'))
tables=[]
for ti,tbl in enumerate(root.findall('.//hp:tbl',ns)):
    cells=[]
    for tc in tbl.findall('./hp:tr/hp:tc',ns):
        cells.append({'addr':dict(tc.find('hp:cellAddr',ns).attrib),'span':dict(tc.find('hp:cellSpan',ns).attrib),'size':dict(tc.find('hp:cellSz',ns).attrib),'text':''.join(tc.xpath('.//hp:t//text()',namespaces=ns))})
    tables.append({'table':ti,'rowCnt':tbl.get('rowCnt'),'colCnt':tbl.get('colCnt'),'cells':cells})
sys.path.insert(0,str(SCRIPT.parent))
from page_guard import collect_text_budget_profile
budget = collect_text_budget_profile(reply)
slots=read(BASE/'sources/reply/slots.json')['slots']
target='cell:1:2:2'
actualslot=next(s for s in budget['slots'] if s['key']==target+':0')
storedslot=next(s for s in slots if s['key']==target)
long=(BASE/'long_text.txt').read_text(encoding='utf-8')
values=OUT/'local-materials-long-values.json'
candidate=OUT/'local-materials-long-attempt.hwpx'
log=OUT/'local-materials-long-attempt.json'
if log.exists() or candidate.exists() or values.exists():
    raise SystemExit('Existing trial evidence found; refusing another edit attempt or overwrite.')
values.write_text(json.dumps({target:long},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
cmd=[PY,'-B','-X','utf8',str(SCRIPT),str(reply),'-o',str(candidate),'--slot-json',str(values)]
count=len(re.sub(r'\s+','',long))
assert count>actualslot['max_chars']
result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
trial={'command':cmd,'executions':1,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'output_exists':candidate.exists(),'raw_chars':len(long),'sentence_chars':len(long.rstrip('\r\n')),'nospace_chars':count,'target':target,'stored_slot':storedslot,'actual_budget':actualslot,'long_text':long}
log.write_text(json.dumps(trial,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
after={str(p.relative_to(BASE)):sha(p) for p in BASE.rglob('*') if p.is_file()}
audit={'lineage':rows,'reply_tables':tables,'reply_paragraphs':[''.join(p.xpath('./hp:run/hp:t//text()',namespaces=ns)) for p in root.findall('.//hp:p',ns)],'source_hashes_match':all(sha(BASE/s['copy'])==s['sha256'] for s in sources),'inputs_unchanged':before==after,'input_hashes':before,'trial':trial}
(OUT/'local-materials-evidence.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'lineage':rows,'tables':[{'table':t['table'],'rows':t['rowCnt'],'cols':t['colCnt']} for t in tables],'trial':trial,'inputs_unchanged':before==after},ensure_ascii=False,indent=2))
