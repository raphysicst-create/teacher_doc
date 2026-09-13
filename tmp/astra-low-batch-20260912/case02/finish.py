from pathlib import Path
import subprocess,sys,json,hashlib,datetime,shutil
r=Path(__file__).resolve().parents[3];t=Path(__file__).resolve().parent;s=r/'.claude/skills/hwpx/scripts'; f=t/'result.hwpx'; logs=[]
def run(script,*args):
 p=subprocess.run([sys.executable,'-X','utf8',str(script),*map(str,args)],capture_output=True,text=True,encoding='utf-8'); logs.append({'script':str(script),'args':list(map(str,args)),'exit':p.returncode,'output':p.stdout+p.stderr}); print(p.stdout+p.stderr);return p
run(s/'edit_hwpx.py',r/'knowledge/templates/성립전예산요구/양식.hwpx','-o',f,'--slot-json',t/'values.json','--allow-over-budget','--verified-by-render')
for script,args in [('validate.py',[]),('fix_namespaces.py',[]),('finalize_hwpx.py',['--strip-linesegarray']),('validate.py',['--layout'])]:run(s/script,f,*args)
run(s/'page_guard.py','--reference',r/'knowledge/templates/성립전예산요구/양식.hwpx','--output',f,'--budget-profile',r/'knowledge/templates/성립전예산요구/budget.json','--structure-profile',r/'knowledge/templates/성립전예산요구/structure.json','--no-strict-paragraph-budget','--skip-text-drift')
run(s/'finalize_hwpx.py',f,'--hancom')
run(r/'scripts/render_check.py',f,'--reference',r/'knowledge/templates/성립전예산요구/양식.hwpx','--keep-pdf',t/'final.pdf')
run(s/'content_guard.py',f,'--forbid','농어촌유학 거주비 지원금','--forbid','정책기획과-3100','--forbid','2025. 3. 19.','--forbid','1학기','--require','화동중학교-2058(2026. 3. 17.)','--require','2학기 교과별 교수학습 및 평가계획','--require','1학년','--require','2학년')
run(s/'gonmun_lint.py','--hwpx',f,'--format','text')
(t/'validation.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2),encoding='utf-8')
print('HASH',hashlib.sha256(f.read_bytes()).hexdigest(),'PREVIEW_HASH',hashlib.sha256((t/'unverified.hwpx').read_bytes()).hexdigest())
