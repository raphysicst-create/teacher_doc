from pathlib import Path
import ast, collections, hashlib, json, re, struct, subprocess
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/release-review-20260913'
OUT.mkdir(exist_ok=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest=json.loads((ROOT/'distribution/release-files.json').read_text(encoding='utf-8'))
tree=json.loads((ROOT/'tmp/remaining-20260913/evidence/github-tree.json').read_text(encoding='utf-8'))
upstream={e['path']:e for e in tree['tree'] if e['type']=='blob'}
rules={
 'local_identity':r'(?i)[a-z]:[/\\]Users[/\\]|화동중|Desktop[/\\]maintain|OneDrive\s*-',
 'personal_number':r'(?<!\d)\d{6}\s*-\s*[1-4]\d{6}(?!\d)',
 'phone':r'(?<!\d)(?:010|011|016|017|018|019)[ -]?\d{3,4}[ -]?\d{4}(?!\d)',
 'email':r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
 'credential':r'(?i)-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,})',
 'external_url':r'https?://[^\s<>"\)]+',
 'attribution':r'(?i)copyright|all rights reserved|licensed under|SPDX|Canine89|jkf87|Anthropic|OpenAI',
}
records=[]
for item in manifest['files']:
 p=ROOT/item['source']; data=p.read_bytes()
 r={**item,'bytes':len(data),'sha256':sha(p),'suffix':p.suffix,'matches':{}}
 short=item['source'].removeprefix('.claude/skills/hwpx/')
 if item['source'].startswith('distribution/assets/templates/'):
  short=item['source'].removeprefix('distribution/assets/')
 u=upstream.get(short) if item['source'].startswith(('.claude/skills/hwpx/','distribution/assets/')) else None
 if u:
  normalized=data.replace(b'\r\n',b'\n')
  blob=hashlib.sha1(b'blob '+str(len(normalized)).encode()+b'\0'+normalized).hexdigest()
  r['upstream']={'tree':tree['sha'],'path':short,'blob_sha1':u['sha'],'same_lf_blob':blob==u['sha']}
 if len(data)<300000:
  try: text=data.decode('utf-8-sig')
  except UnicodeDecodeError: text=None
  if text is not None:
   r['text_scanned']=True
   for key,pat in rules.items():
    hits=[{'line':i,'text':line[:450]} for i,line in enumerate(text.splitlines(),1) if re.search(pat,line)]
    if hits:r['matches'][key]=hits
   if p.suffix in ('.xml','.hpf','.rdf'):
    node=ET.fromstring(text)
    r['xml_text']=[x.strip() for x in node.itertext() if x.strip()]
    r['xml_attributes']=sorted(set(f'{k}={v}' for n in node.iter() for k,v in n.attrib.items() if re.search(r'[가-힣]|https?://|[a-z]:',v,re.I)))
   if p.suffix=='.py':
    node=ast.parse(text)
    r['imports']=sorted(set(n.names[0].name if isinstance(n,ast.Import) else n.module or '' for n in ast.walk(node) if isinstance(n,(ast.Import,ast.ImportFrom))))
    r['docstring']=(ast.get_docstring(node) or '')[:800]
  elif p.suffix=='.png':
   chunks=[];offset=8
   while offset<len(data):
    size=struct.unpack('>I',data[offset:offset+4])[0];kind=data[offset+4:offset+8].decode('ascii');chunks.append(kind);offset+=12+size
   r['png_chunks']=chunks
 if item['source'].startswith(('scripts/','.claude/')):
  proc=subprocess.run(['git','log','--diff-filter=A','--format=%H %s','--',item['source']],cwd=ROOT,capture_output=True,encoding='utf-8')
  r['git_additions']=proc.stdout.strip().splitlines()
 records.append(r)
save('inventory.json',records)
save('baseline-hashes.json',{i['source']:i['sha256'] for i in records})
save('rights-before.json',json.loads((ROOT/'distribution/rights.pending.json').read_text(encoding='utf-8')))
print('FILES',len(records),'BY EXTENSION',dict(collections.Counter(r['suffix'] for r in records)))
for r in records:
 if r['source'].startswith('distribution/legal/') or r['source'].endswith('.tar.gz'):continue
 print('\nFILE',r['source'],'UPSTREAM',r.get('upstream'),'GIT',r.get('git_additions'))
 if 'xml_text' in r:print('XML TEXT',r['xml_text'],'ATTR',r['xml_attributes'])
 for key,hits in r['matches'].items():
  if key!='external_url':print(key,hits)
 if r.get('png_chunks'):print('PNG CHUNKS',r['png_chunks'])
