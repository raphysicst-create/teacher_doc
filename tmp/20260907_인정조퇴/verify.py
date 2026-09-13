from pathlib import Path
import subprocess,sys,json,shutil
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
SKILL=ROOT/'.claude/skills/hwpx/scripts'
OUT=ROOT/'output/20260907_과학그리기대회_출석인정조퇴.hwpx'

def audit(action,result,detail):
    with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps(dict(ts=datetime.now().astimezone().isoformat(),agent='Codex',action=action,target=str(OUT),result=result,detail=detail),ensure_ascii=False)+'\n')

def run(label,script,*args):
    p=subprocess.run([sys.executable,'-X','utf8',str(script),*map(str,args)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8')
    (WORK/(label+'.log')).write_text(p.stdout,encoding='utf-8')
    print(label+': '+p.stdout,flush=True)
    audit('validate', 'pass' if p.returncode==0 else 'fail',label+': '+p.stdout[:1500])
    if p.returncode: raise SystemExit(p.returncode)

audit('generate','ok','ユーザー confirmed: 1학년 1반 2명, 번호·성명 빈칸, 장소 예미랩. 신규 생성, 전체 굴림·본문12pt. 준비 스크립트 최초 들여쓰기 XML namespace 오류 후 hc:left로 교정하여 재시도 성공.')
run('01_validate',SKILL/'validate.py',OUT)
run('02_namespaces',SKILL/'fix_namespaces.py',OUT)
run('03_finalize',SKILL/'finalize_hwpx.py',OUT,'--strip-linesegarray','--layout')
run('04_layout',SKILL/'validate.py',OUT,'--layout')
baseline=WORK/'신규생성_기준.hwpx'
shutil.copy2(OUT,baseline)
run('05_profiles',SKILL/'page_guard.py','--reference',baseline,'--write-budget',WORK/'budget.json','--write-structure',WORK/'structure.json')
run('06_page_guard',SKILL/'page_guard.py','--reference',baseline,'--output',OUT,'--budget-profile',WORK/'budget.json','--structure-profile',WORK/'structure.json')
run('07_hancom',SKILL/'finalize_hwpx.py',OUT,'--hancom')
run('08_lint',SKILL/'gonmun_lint.py','--hwpx',OUT,'--format','text')
run('09_content',SKILL/'content_guard.py',OUT,'--rules',WORK/'content.rules.json')
run('10_render',ROOT/'scripts/render_check.py',OUT,'--keep-pdf',WORK/'검증.pdf','--json')
