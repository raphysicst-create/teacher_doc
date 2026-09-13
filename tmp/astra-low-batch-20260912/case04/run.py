from pathlib import Path
from lxml import etree as E
import subprocess,json,hashlib,datetime
R=Path.cwd(); T=R/'tmp/astra-low-batch-20260912/case04'; S=R/'.claude/skills/hwpx'; P=r'C:\Users\22\AppData\Local\Programs\Python\Python312\python.exe'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,*args):
 r=subprocess.run([P,'-X','utf8',*map(str,args)],capture_output=True,text=True,encoding='utf-8'); (T/(name+'.txt')).write_text(r.stdout+r.stderr,encoding='utf-8'); print(name,r.returncode,r.stdout[-400:],r.stderr[-400:]);
 with (R/'logs/audit.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(dict(ts=datetime.datetime.now().astimezone().isoformat(),agent='astra-low-case04',action=name,target=str(T),result=r.returncode,detail=(r.stdout+r.stderr)[-1500:]),ensure_ascii=False)+'\n')
 return r
title='2026학년도 2학기 2회고사 교과협의회 회의록'
lines=['화동중학교','수신 내부결재','(경유)','제목 '+title,'','1. 관련: 2026학년도 2학기 교과별 평가계획 수립(계획 결재 후 문서번호·시행일 기재)','','2. 2026학년도 2학기 2회고사 교과협의회를 붙임과 같이 실시하여 보고하고자 합니다.','','붙임  '+title+' 1부.  끝.']
(T/'draft.md').write_text('# 작성 근거\n본문-내부결재.md 변형 C, 4505 본문 PDF/MD 선례. 편집 가능한 동일 본체 HWPX가 없어 gonmun 신규 생성. 기관명·수신·제목·관련·보고문·붙임 순서 보존.\n\n'+'\n\n'.join(lines),encoding='utf-8')
(T/'approval.json').write_text(json.dumps({'model':'gpt-6-astra','reasoning':'low','authorization':'이 실험 astra-light 수준으로 5건 정도 랜덤 배치로 돌려서 기존 ouput 폴더의 최종 산출물들처럼 나오는지 확인해줘','interpretation':'부모가 전달한 실제 요청에 근거한 동일 입력 재작성 승인; 새 발언·평가 생성 없음','request_sha256':sha(T/'request.md'),'draft_sha256':sha(T/'draft.md'),'instructions':{str(p):sha(p) for p in [R/'CLAUDE.md',S/'SKILL.md']}},ensure_ascii=False,indent=2),encoding='utf-8')
hp='http://www.hancom.co.kr/hwpml/2011/paragraph'; hh='http://www.hancom.co.kr/hwpml/2011/head'
sec=E.parse(str(S/'templates/gonmun/section0.xml')).getroot(); first=sec.find('{'+hp+'}p')
for c in list(sec):
 if c is not first: sec.remove(c)
for ls in sec.findall('.//{'+hp+'}linesegarray'): ls.getparent().remove(ls)
for i,text in enumerate(lines):
 p=E.SubElement(sec,'{'+hp+'}p',id=str(1100000000+i),paraPrIDRef='20' if i==0 else '0',styleIDRef='0',pageBreak='0',columnBreak='0',merged='0'); runel=E.SubElement(p,'{'+hp+'}run',charPrIDRef='7' if i==0 else '0'); E.SubElement(runel,'{'+hp+'}t').text=text
E.ElementTree(sec).write(str(T/'section.xml'),xml_declaration=True,encoding='UTF-8')
header=E.parse(str(S/'templates/gonmun/header.xml'))
for font in header.findall('.//{'+hh+'}font'): font.set('face','굴림')
for cp in header.findall('.//{'+hh+'}charPr'):
 if cp.get('id')!='7': cp.set('height','1200')
header.write(str(T/'header.xml'),xml_declaration=True,encoding='UTF-8')
run('build',S/'scripts/build_hwpx.py','--template','gonmun','--header',T/'header.xml','--section',T/'section.xml','--output',T/'result.hwpx')
run('validate',S/'scripts/validate.py',T/'result.hwpx')
run('namespace',S/'scripts/fix_namespaces.py',T/'result.hwpx')
run('finalize',S/'scripts/finalize_hwpx.py',T/'result.hwpx','--strip-linesegarray')
run('layout',S/'scripts/validate.py',T/'result.hwpx','--layout')
run('lint',S/'scripts/gonmun_lint.py',T/'result.hwpx')
run('content',S/'scripts/content_guard.py',T/'result.hwpx','--forbid','1학기','--forbid','2861','--forbid','2026. 4. 7.','--forbid','2026. 6. 5.','--require',title,'--require','계획 결재 후 문서번호·시행일 기재')
run('text',S/'scripts/text_extract.py',T/'result.hwpx','--format','markdown')
