from pathlib import Path
import json,hashlib,subprocess,datetime,shutil
R=Path('C:/Users/22/Desktop/maintain/Hwp_doc'); T=R/'tmp/astra-low-batch-20260912/case05'; S=R/'.claude/skills/hwpx/scripts'; P='C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe'
B=R/'knowledge/templates/가정통신문-고사안내/양식.hwpx'; O=T/'case05.hwpx'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(name,script,*args):
 r=subprocess.run([P,'-X','utf8',str(script),*map(str,args)],capture_output=True,text=True,encoding='utf-8'); (T/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8'); print(name,r.returncode,r.stdout[-700:],r.stderr[-300:]);
 with (R/'logs/audit.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(dict(ts=datetime.datetime.now().isoformat(),agent='astra-low-case05',action=name,target=str(O),result=r.returncode,detail=str(T/(name+'.log'))),ensure_ascii=False)+'\n')
 return r.returncode
v={'p:3':'화동중 제2026-미부여호','p:12':'2026학년도 2학기 2회고사 실시 안내','p:14':'각 가정의 건강과 행복을 기원합니다. 2학기 2회고사는 2학년만 응시합니다. 1학년은 자유학기로 지필고사 없이 양일 정상수업합니다. 2학년은 12월 7일 중식 후 하교, 8일 중식 후 정상수업합니다.','p:16':'1. 2회고사 일정 2026. 12. 7.~12. 8. 2일간','p:22':'12/7(월)','p:37':'12/8(화)','p:36':'2학년 하교','p:109':'3. 이의 신청 기간: 2026. 12. 9.~12. 12.','p:113':'2026. 11. 24.'}
for i in [24,27,30,33,39,42,45,48]:v[f'p:{i}']='수업'
for i,x in zip([25,28,31,34,40,43,46,49],['국어','영어','자습','자습','수학','역사','자습','과학']):v[f'p:{i}']=x
for i in [65,66,67,69,70,72,73,74,75,76,79,80,81,82,83,84]:v[f'p:{i}']='미실시'
for i,x in {88:'3-4단원',89:'3-4과',90:'3-4(1)단원',91:'4-6단원',93:'4-5단원',95:'선택형 60%, 서·논술형 40%',96:'선택형 84%, 서·논술형 16%',97:'선택형 70%, 서·논술형 30%',98:'선택형 85%, 서·논술형 15%',99:'선택형 75%, 서·논술형 25%',102:'선택형 16, 서·논술형 6',103:'선택형 16, 서·논술형 4',104:'선택형 18,',105:'서·논술형 2',106:'선택형 20, 서·논술형 2',107:'선택형 20,',108:'서·논술형 5'}.items():v[f'p:{i}']=x
v['p:3']='통신문 번호 미부여'
(T/'values.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
(T/'draft.md').write_text('# 독립 재작성 초안\n\n베이스: '+str(B)+'\n제목 강조, 헤더, 일정 상자, 두 표의 행열·병합, 하단 날짜·명의 보존. 1학년 및 사회 열 삭제 없음.\n\n'+ '\n\n'.join(f'{k}: {x}' for k,x in v.items())+'\n\n미제공: 통신문 번호, 이의신청 방법. 사용자 재작성 시험 입력을 그대로 생성하는 권한이며 별도의 초안 승인 발언을 만들지 않음.\n',encoding='utf-8')
(T/'provenance.json').write_text(json.dumps({'model':'gpt-6-astra','reasoning_effort':'low','user_authorization':'이 실험 astra-light 수준으로 5건 정도 랜덤 배치로 돌려서 기존 ouput 폴더의 최종 산출물들처럼 나오는지 확인해줘','request_sha256':sha(T/'request.md'),'values_sha256':sha(T/'values.json'),'draft_sha256':sha(T/'draft.md'),'base':str(B),'base_sha256':sha(B),'instructions':{str(p):sha(p) for p in [R/'CLAUDE.md',R/'.claude/skills/hwpx/SKILL.md']},'structure_change':False},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
 import sys
 sys.path.insert(0,str(S))
 import edit_hwpx
 paragraphs,cells=edit_hwpx._targets_from_slots(v)
 # 날짜 11자 > 원본 10자: 검증 주장을 하지 않는 렌더 전용 사본.
 edit_hwpx._pack_from_original(B,O,{},cells,paragraphs)
 (T/'preview-status.md').write_text('미검증 렌더 전용 사본. p:113 날짜 11자/예산10자. 플래그 승인·예산 검증 통과 주장 없음. 실렌더 후 정식 edit CLI 재실행 필요.',encoding='utf-8')
 run('validate',S/'validate.py',O)
 run('fix_namespaces',S/'fix_namespaces.py',O)
 run('finalize',S/'finalize_hwpx.py',O,'--strip-linesegarray')
 run('layout',S/'validate.py',O,'--layout')
 ref=T/'reference-finalized.hwpx'; shutil.copy2(B,ref)
 run('reference-finalize',S/'finalize_hwpx.py',ref,'--strip-linesegarray')
 run('profiles',S/'page_guard.py','--reference',ref,'--write-budget',T/'budget.json','--write-structure',T/'structure.json')
 run('page_guard',S/'page_guard.py','--reference',ref,'--output',O,'--budget-profile',T/'budget.json','--structure-profile',T/'structure.json','--no-strict-paragraph-budget','--skip-text-drift','--allow-empty-fill')
