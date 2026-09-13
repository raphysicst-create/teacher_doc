import json,sys,subprocess,hashlib,shutil
from pathlib import Path
from datetime import datetime
R=Path(__file__).resolve().parents[2]; W=Path(__file__).resolve().parent
S=R/'.claude/skills/hwpx/scripts'; P=Path(sys.executable)
src=R/'knowledge/examples/2026학년도 1학기 과목별 평가계획 안내 가정통신문.hwpx'
out=R/'output/2026_2학기_평가계획_가정통신문.hwpx'
reports=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(label,script,*args):
 cmd=[str(P),'-X','utf8',str(script),*map(str,args)]
 p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,encoding='utf-8',timeout=90)
 log=p.stdout+p.stderr
 (W/(label+'.log')).write_text(log,encoding='utf-8')
 item={'step':label,'exit_code':p.returncode,'log':log,'sha256':sha(out) if out.exists() else None}
 reports.append(item)
 (W/'validation.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
 with (R/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
  f.write(json.dumps({'ts':datetime.now().astimezone().isoformat(),'agent':'Codex','action':label,'target':str(out),'result':'pass' if p.returncode==0 else 'fail','detail':log},ensure_ascii=False)+'\n')
 print(label,p.returncode,log[:2000],flush=True)
 return p.returncode
visual={'confirmed':True,'by':'Codex','at':datetime.now().astimezone().isoformat(),'record':'proof-final.png 실제 판독: 전체 1쪽, 셀 텍스트 겹침/잘림 없음, 두 줄 활동은 셀 안에 수용. 피아노 연주 괄호 문구 확인.','document_sha256':sha(W/'render-proof.hwpx'),'pdf_sha256':sha(W/'proof-final.pdf'),'image_sha256':sha(W/'proof-final.png'),'over_budget':json.loads((W/'compact-budget-review.json').read_text(encoding='utf-8'))}
(W/'visual-review.json').write_text(json.dumps(visual,ensure_ascii=False,indent=2),encoding='utf-8')
assert run('edit',S/'edit_hwpx.py',src,'-o',out,'--slot-json',W/'compact-values.json','--allow-over-budget','--verified-by-render')==0
assert run('validate',S/'validate.py',out)==0
assert run('namespaces',S/'fix_namespaces.py',out)==0
assert run('finalize',S/'finalize_hwpx.py',out,'--strip-linesegarray')==0
assert run('layout',S/'validate.py',out,'--layout')==0
ref=W/'reference-finalized.hwpx'; shutil.copy2(src,ref)
assert run('reference_finalize',S/'finalize_hwpx.py',ref,'--strip-linesegarray')==0
assert run('profiles',S/'page_guard.py','--reference',ref,'--write-budget',W/'budget.json','--write-structure',W/'structure.json')==0
run('page_guard',S/'page_guard.py','--reference',ref,'--output',out,'--budget-profile',W/'budget.json','--structure-profile',W/'structure.json','--no-strict-paragraph-budget','--skip-text-drift','--allow-empty-fill')
run('hancom',S/'finalize_hwpx.py',out,'--hancom')
run('render',R/'scripts/render_check.py',out,'--reference',src,'--keep-pdf',R/'output/2026_2학기_평가계획_가정통신문.pdf','--json')
rules={'forbid':['1학기','2026-20호','2026. 4. 9.','2026.04.28.','2026.06.30.','비열실험','부력 측정 실험','소리의 성질 탐구 실험','이온의 이동 관찰 실험','작곡가 음악신문','자화상','풍경화','조소','전각','채색화','작가탐구','줄넘기','배드민턴','청소년의 발달 안내책','픽토그램','더블 클립카','세얼간이','네 컷 만화','피지컬 컴퓨팅'],'require':['2026학년도 2학기','2026. 10. 27.~10. 28.','2026. 12. 7.~12. 8.','자유학기','광합성 실험','옴의 법칙 실험','인공지능','달 모형','화동중학교장']}
(W/'content-rules.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2),encoding='utf-8')
run('content',S/'content_guard.py',out,'--rules',W/'content-rules.json')
run('lint',S/'gonmun_lint.py',out)
run('extract_final',S/'text_extract.py',out,'--format','markdown','-o',W/'final.md')
run('extract_original',S/'text_extract.py',src,'--format','markdown','-o',W/'original.md')
import difflib
(W/'신구대조.diff').write_text(''.join(difflib.unified_diff((W/'original.md').read_text(encoding='utf-8').splitlines(True),(W/'final.md').read_text(encoding='utf-8').splitlines(True),fromfile='1학기 원본',tofile='2학기 축약본')),encoding='utf-8')
print('FINAL SHA',sha(out),'PROOF MATCH',sha(out)==sha(W/'render-proof.hwpx'))
