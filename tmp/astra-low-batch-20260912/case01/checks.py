from pathlib import Path
import subprocess,json,datetime
r=Path.cwd();w=r/'tmp/astra-low-batch-20260912/case01';s=r/'.claude/skills/hwpx/scripts';py=r'C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe';f=w/'2026_2학기_1회고사_출제연수_기안문.hwpx'
commands=[['build_hwpx.py','--template','gonmun','--section',str(w/'section.xml'),'--header',str(w/'header.xml'),'--output',str(f)],['validate.py',str(f)],['fix_namespaces.py',str(f)],['finalize_hwpx.py',str(f),'--strip-linesegarray'],['validate.py',str(f),'--layout'],['gonmun_lint.py','--hwpx',str(f),'--format','text'],['content_guard.py',str(f),'--rules',str(w/'rules.json')]]
for i,c in enumerate(commands):
 p=subprocess.run([py,'-X','utf8',str(s/c[0]),*c[1:]],capture_output=True,text=True,encoding='utf8');(w/f'check_{i}_{c[0]}.txt').write_text(p.stdout+p.stderr,encoding='utf8');print(c[0],p.returncode,p.stdout[-800:],p.stderr[-300:]);
 with (r/'logs/audit.jsonl').open('a',encoding='utf8') as a:a.write(json.dumps({'ts':datetime.datetime.now().isoformat(),'agent':'astra-low-case01','action':c[0],'target':str(f),'result':p.returncode,'detail':'독립 재작성 배치 case01'},ensure_ascii=False)+'\n')
