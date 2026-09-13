from pathlib import Path
import json, subprocess, sys, hashlib
from datetime import datetime
WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[1]
OUT=ROOT/'output/fresh-notice-reproduction-20260912'
OUT.mkdir(parents=True,exist_ok=True)
FINAL=OUT/'2026학년도_2학기_1회고사_안내_검토초안.hwpx'
PY=Path('C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe')
SKILL=ROOT/'.claude/skills/hwpx/scripts'
results=[]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def run(name,args):
    before=sha(FINAL)
    p=subprocess.run([str(PY),'-X','utf8',*map(str,args)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    text=p.stdout+p.stderr
    (WORK/(name+'.log')).write_text(text,encoding='utf-8')
    r={'step':name,'returncode':p.returncode,'command':list(map(str,args)),'document_sha256_before':before,'document_sha256_after':sha(FINAL),'result':'pass' if p.returncode==0 else 'fail','output':text,'at':datetime.now().astimezone().isoformat()}
    results.append(r)
    (WORK/'validation-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(name,p.returncode,flush=True)
    return p.returncode
if FINAL.exists(): raise SystemExit('Refuse overwrite final')
run('01_edit',[SKILL/'edit_hwpx.py',WORK/'reference.hwpx','-o',FINAL,'--slot-json',WORK/'edit-values.json','--replace-json',WORK/'replacements.json','--allow-over-budget','--verified-by-render'])
if not FINAL.exists(): raise SystemExit('Edit failed')
run('02_validate',[SKILL/'validate.py',FINAL])
run('03_namespaces',[SKILL/'fix_namespaces.py',FINAL])
run('04_finalize',[SKILL/'finalize_hwpx.py',FINAL,'--strip-linesegarray','--layout'])
run('05_layout',[SKILL/'validate.py',FINAL,'--layout'])
run('06_page_guard',[SKILL/'page_guard.py','--reference',WORK/'reference.hwpx','--output',FINAL,'--budget-profile',WORK/'budget.json','--structure-profile',WORK/'structure.json','--no-strict-paragraph-budget','--skip-text-drift','--allow-empty-fill'])
run('07_hancom',[SKILL/'finalize_hwpx.py',FINAL,'--hancom','--json',WORK/'hancom.json'])
run('08_render',[ROOT/'scripts/render_check.py',FINAL,'--reference',WORK/'reference.hwpx','--keep-pdf',WORK/'final.pdf','--json'])
run('09_content',[SKILL/'content_guard.py',FINAL,'--rules',WORK/'content-rules.json','--json'])
run('10_gonmun',[SKILL/'gonmun_lint.py',FINAL])
run('11_final_extract',[SKILL/'text_extract.py',FINAL,'--format','markdown'])
run('12_reference_extract',[SKILL/'text_extract.py',WORK/'reference.hwpx','--format','markdown'])
(WORK/'final-hashes.json').write_text(json.dumps({'final':str(FINAL),'sha256':sha(FINAL),'visual_preview_sha256':sha(WORK/'미검증_렌더용_v2.hwpx'),'same_as_visual_preview':sha(FINAL)==sha(WORK/'미검증_렌더용_v2.hwpx'),'pdf_sha256':sha(WORK/'final.pdf')},ensure_ascii=False,indent=2),encoding='utf-8')
print('COM finished. Full pipeline remains FAIL if any mandatory step failed.',flush=True)
