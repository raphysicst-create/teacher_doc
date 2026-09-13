from pathlib import Path
import json, sys, hashlib, difflib
from audit_batch import inspect
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
case=sys.argv[1]; candidate=Path(sys.argv[2]).resolve()
old=json.loads((WORK/(case+'-baseline-profile.json')).read_text(encoding='utf-8'))
new=inspect(candidate)
text=lambda d:'\n'.join(p['text'] for p in d['paragraphs'])
shape=lambda d:[{'rows':t['rows'],'cols':t['cols'],'cells':[{k:v for k,v in c.items() if k!='text'} for c in t['cells']]} for t in d['tables']]
styles=lambda d:sorted({(r['height'] or '',r['hangul_font'] or '',str(r['bold'])) for p in d['paragraphs'] for r in p['runs']})
data={'case':case,'baseline':old['path'],'candidate':str(candidate),'candidate_sha256':new['sha256'],
      'table_geometry_equal':shape(old)==shape(new),'table_counts':[len(old['tables']),len(new['tables'])],
      'paragraph_counts':[len(old['paragraphs']),len(new['paragraphs'])],
      'styles_before':styles(old),'styles_after':styles(new),
      'text_diff':list(difflib.unified_diff(text(old).splitlines(),text(new).splitlines(),fromfile='baseline',tofile='candidate',lineterm='')),
      'candidate_profile':new,
      'meaning':'Exact differences, not an automatic quality verdict; placeholder and wording changes need human/model review.'}
(WORK/(case+'-comparison.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in data.items() if k!='candidate_profile'},ensure_ascii=False,indent=2))
