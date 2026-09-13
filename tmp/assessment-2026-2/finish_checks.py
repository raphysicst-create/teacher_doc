from pathlib import Path
import sys,subprocess,json,hashlib,datetime,re,zipfile
from lxml import etree as E
w=Path(__file__).resolve().parent;root=w.parents[1]; skill=root/'.claude/skills/hwpx/scripts'
sys.path.insert(0,str(skill))
from edit_hwpx import write_raw_preserving_zip
base=root/'knowledge/examples/(화동중학교-2956 (첨부)) 2026학년도 1학기 과목별 평가계획 안내 가정통신문.hwp.hwpx'
write_raw_preserving_zip(base,w/'base-copy.hwpx',{})
records=[]
def run(name,script,*args):
 p=subprocess.run([sys.executable,'-X','utf8',str(skill/script),*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=90)
 (w/(name+'.txt')).write_text(p.stdout+p.stderr,encoding='utf-8');records.append({'stage':name,'exit_code':p.returncode,'output':p.stdout+p.stderr});print(name,p.returncode,flush=True)
run('base-finalize','finalize_hwpx.py',w/'base-copy.hwpx','--strip-linesegarray')
run('base-profiles','page_guard.py','--reference',w/'base-copy.hwpx','--write-budget',w/'base-budget.json','--write-structure',w/'base-structure.json')
run('original-structure-diff','page_guard.py','--reference',w/'base-copy.hwpx','--output',w/'final.hwpx','--budget-profile',w/'base-budget.json','--structure-profile',w/'base-structure.json','--no-strict-paragraph-budget','--skip-text-drift','--json')
run('approved-profiles','page_guard.py','--reference',w/'final.hwpx','--write-budget',w/'final-budget.json','--write-structure',w/'final-structure.json')
run('approved-page-guard','page_guard.py','--reference',w/'final.hwpx','--output',w/'final.hwpx','--budget-profile',w/'final-budget.json','--structure-profile',w/'final-structure.json','--no-strict-paragraph-budget','--skip-text-drift')
run('hancom','finalize_hwpx.py',w/'final.hwpx','--hancom')
run('gonmun','gonmun_lint.py','--hwpx',w/'final.hwpx','--format','text')
run('content','content_guard.py',w/'final.hwpx','--forbid','2026-20호','--forbid','2026. 4. 9.','--forbid','1학기','--forbid','세얼간이','--forbid','더블 클립카','--forbid','소리의 성질','--forbid','이온의 이동','--forbid','기출문제','--require','2026학년도 2학기','--require','2026. 10. 27.','--require','2026. 12. 8.','--json')
md=(root/'output/2026학년도_2학기_평가계획_가정통신문_초안.md').read_text(encoding='utf-8')
with zipfile.ZipFile(w/'final.hwpx') as z:tree=E.fromstring(z.read('Contents/section0.xml'))
norm=lambda s:re.sub(r'\s+','',s)
text=norm(''.join(tree.itertext()))
cells=[c.strip() for l in md.splitlines() if l.startswith('|') and '---' not in l for c in l.strip('|').split('|')]
missing=[c for c in cells if norm(c) not in text]
records.append({'stage':'approved-table-values','count':len(cells),'missing':missing})
assert not missing,missing
(w/'verification.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
for rec in records:
 with (root/'logs/audit.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'ts':datetime.datetime.now().astimezone().isoformat(),'agent':'codex','action':'validation','target':str(w/'final.hwpx'),'result':rec.get('exit_code',0),'detail':rec['stage']},ensure_ascii=False)+'\n')
print('table values',len(cells),'matched')
