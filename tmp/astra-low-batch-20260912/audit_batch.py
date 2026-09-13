from pathlib import Path
import json, zipfile, hashlib, subprocess, sys
from lxml import etree as E
import fitz
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
NS={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph','hh':'http://www.hancom.co.kr/hwpml/2011/head'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def inspect(path):
    with zipfile.ZipFile(path) as z:
        h=E.fromstring(z.read('Contents/header.xml'))
        sections=[E.fromstring(z.read(n)) for n in sorted(z.namelist()) if n.startswith('Contents/section') and n.endswith('.xml')]
    styles={x.get('id'):x for x in h.findall('.//hh:charPr',NS)}
    fonts={f.get('lang'):{x.get('id'):x.get('face') for x in f.findall('hh:font',NS)} for f in h.findall('.//hh:fontface',NS)}
    paragraphs=[]; tables=[]
    for s in sections:
        for p in s.findall('.//hp:p',NS):
            runs=[]
            for r in p.findall('hp:run',NS):
                text=''.join(''.join(t.itertext()) for t in r.findall('hp:t',NS))
                if not text.strip():continue
                cp=styles.get(r.get('charPrIDRef')); fr=cp.find('hh:fontRef',NS) if cp is not None else None
                runs.append({'text':text,'height':cp.get('height') if cp is not None else None,
                  'bold':cp.find('hh:bold',NS) is not None if cp is not None else None,
                  'hangul_font':fonts.get('HANGUL',{}).get(fr.get('hangul')) if fr is not None else None})
            if runs:paragraphs.append({'runs':runs,'text':''.join(r['text'] for r in runs)})
        for t in s.findall('.//hp:tbl',NS):
            cells=[]
            for row in t.findall('hp:tr',NS):
                for c in row.findall('hp:tc',NS):
                    cell={k:dict(c.find('hp:'+k,NS).attrib) for k in ('cellAddr','cellSpan','cellSz','cellMargin') if c.find('hp:'+k,NS) is not None}
                    cell['text']=' '.join(''.join(x.itertext()) for x in c.findall('.//hp:t',NS))
                    cells.append(cell)
            tables.append({'rows':t.get('rowCnt'),'cols':t.get('colCnt'),'cells':cells})
    return {'path':str(path),'sha256':sha(path),'paragraphs':paragraphs,'tables':tables}

def baselines():
    selection=json.loads((WORK/'selection.json').read_text(encoding='utf-8'))
    results=[]
    for case in selection['cases']:
        name=case['case']; source=ROOT/case['baseline']
        profile=inspect(source)
        (WORK/(name+'-baseline-profile.json')).write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
        pdf=WORK/(name+'-baseline.pdf')
        r=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/render_check.py'),str(source),'--keep-pdf',str(pdf),'--json'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        (WORK/(name+'-baseline-render.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
        item={'case':name,'exit_code':r.returncode,'original_unchanged':sha(source)==case['sha256']}
        if pdf.exists():
            d=fitz.open(pdf); item['pages']=len(d)
            for i,p in enumerate(d):p.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(WORK/(name+f'-baseline-{i+1}.png'))
            d.close()
        results.append(item)
        (WORK/'baseline-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(item,flush=True)

if __name__=='__main__':
    if sys.argv[1]=='baselines':baselines()
    else:
        path=Path(sys.argv[2]).resolve(); result=inspect(path)
        (WORK/(sys.argv[1]+'-candidate-profile.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'case':sys.argv[1],'path':str(path),'sha256':result['sha256'],'tables':len(result['tables']),'paragraphs':len(result['paragraphs'])},ensure_ascii=False))
