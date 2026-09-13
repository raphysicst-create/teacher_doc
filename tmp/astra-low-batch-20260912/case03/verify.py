from pathlib import Path
import subprocess,json,datetime
W=Path(__file__).parent; R=W.resolve().parents[2]; S=R/'.claude/skills/hwpx/scripts'; PY=r'C:\Users\22\AppData\Local\Programs\Python\Python312\python.exe'; F=str(W/'result.hwpx')
steps=[('validate',S/'validate.py',[F]),('fix_namespaces',S/'fix_namespaces.py',[F]),('finalize',S/'finalize_hwpx.py',[F,'--strip-linesegarray']),('layout',S/'validate.py',[F,'--layout']),('page_guard',S/'page_guard.py',['--reference',F,'--output',F,'--json']),('content_guard',S/'content_guard.py',[F,'--forbid','3205','--forbid','7341','--forbid','2025학년도','--forbid','2026. 4. 16.','--forbid','2025. 10. 13.','--require','2026학년도 2학기 1회고사','--json']),('gonmun_lint',S/'gonmun_lint.py',[F])]
out=[]
for name,script,args in steps:
 p=subprocess.run([PY,'-X','utf8',str(script),*args],capture_output=True,text=True,encoding='utf-8'); (W/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');out.append({'step':name,'exit':p.returncode}); print(name,p.returncode,p.stdout[-250:])
 with (R/'logs/audit.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(dict(ts=datetime.datetime.now().isoformat(),agent='astra-low-case03',action='validate',target=F,result=str(p.returncode),detail=name),ensure_ascii=False)+'\n')
(W/'validation.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
