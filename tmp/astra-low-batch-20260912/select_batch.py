from pathlib import Path
from datetime import datetime
import json, hashlib, secrets, random, zipfile, sys
from lxml import etree as E

ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=WORK/'selection.json'
if manifest.exists(): raise SystemExit('Selection already fixed; do not redraw')
reviews=[json.loads(s) for s in (ROOT/'logs/review_log.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
pool={r['file']: {'review':r,'basis':'direct_review'} for r in reviews if r['approved'] and (ROOT/r['file']).exists()}
pool.pop('output/2026_농어촌유학_수리과학체험_운영계획_v2.hwpx',None)
for attach,parent in [
 ('2026_2학기_1회고사_교과협의회_회의록.hwpx','2026_2학기_1회고사_교과협의회_기안문.hwpx'),
 ('2026_2학기_2회고사_교과협의회_회의록.hwpx','2026_2학기_2회고사_교과협의회_기안문.hwpx'),
 ('2026_2학기_2회고사_가정통신문.hwpx','2026_2학기_2회고사_가통배부_기안문.hwpx')]:
    pool['output/'+attach]={'review':pool['output/'+parent]['review'],'basis':'approved_package_attachment_not_separate_score'}
seed=secrets.randbits(64)
selected=random.Random(seed).sample(sorted(pool),5)
ns={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph'}
cases=[]
for i,p in enumerate(selected,1):
    case=f'case{i:02d}'
    with zipfile.ZipFile(ROOT/p) as z:
        sections=[E.fromstring(z.read(n)) for n in sorted(z.namelist()) if n.startswith('Contents/section') and n.endswith('.xml')]
    text='\n'.join(''.join(t.itertext()) for s in sections for t in s.findall('.//hp:t',ns))
    (WORK/(case+'-baseline-text.txt')).write_text(text,encoding='utf-8')
    cases.append({'case':case,'baseline':p,'sha256':sha(ROOT/p),**pool[p]})
tracked=[ROOT/'CLAUDE.md',ROOT/'.claude/skills/hwpx/SKILL.md',ROOT/'.claude/hooks/event_adapter.py']
tracked+=list((ROOT/'.claude/skills/hwpx/scripts').glob('*.py'))+list((ROOT/'scripts').glob('*.py'))
tracked+=list((ROOT/'knowledge/templates').rglob('*.hwpx'))
data={'created_at':datetime.now().astimezone().isoformat(),'seed':seed,'method':'uniform sample without replacement from sorted approved-final pool; no redraw',
 'model':'gpt-6-astra','reasoning_effort':'low','requested_label':'astra-light','label_interpretation':'Astra with low reasoning; not a separately resolved model alias',
 'pool':pool,'excluded':'superseded v2, rejected revisions, unreviewed experiments, previous first-exam notice test',
 'cases':cases,'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in tracked}}
manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'seed':seed,'pool_size':len(pool),'cases':[{'case':x['case'],'baseline':x['baseline']} for x in cases]},ensure_ascii=False,indent=2))
