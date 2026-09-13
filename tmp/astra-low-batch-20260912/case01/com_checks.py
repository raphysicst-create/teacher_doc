from pathlib import Path
import subprocess,fitz
r=Path.cwd(); w=r/'tmp/astra-low-batch-20260912/case01'; f=w/'2026_2학기_1회고사_출제연수_기안문.hwpx'; py=r'C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe'
for name,args in [('hancom',[str(r/'.claude/skills/hwpx/scripts/finalize_hwpx.py'),str(f),'--hancom']),('render',[str(r/'scripts/render_check.py'),str(f),'--keep-pdf',str(w/'result.pdf')])]:
 p=subprocess.run([py,'-X','utf8',*args],capture_output=True,text=True,encoding='utf8');(w/(name+'.txt')).write_text(p.stdout+p.stderr,encoding='utf8');print(name,p.returncode,p.stdout,p.stderr)
for name,p in [('reference',next((r/'knowledge/examples').glob('*3206*본문*pdf'))),('result',w/'result.pdf')]:
 if p.exists():
  d=fitz.open(p); print(name,len(d));d[0].get_pixmap(matrix=fitz.Matrix(1,1)).save(str(w/(name+'.png')))
