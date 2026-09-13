from pathlib import Path
from lxml import etree as E
import hashlib,json,subprocess,datetime
R=Path(__file__).resolve().parents[3]; W=Path(__file__).parent
S=R/'.claude/skills/hwpx'; PY=r'C:\Users\22\AppData\Local\Programs\Python\Python312\python.exe'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def audit(action,result,detail):
 with (R/'logs/audit.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(dict(ts=datetime.datetime.now().isoformat(),agent='astra-low-case03',action=action,target=str(W),result=result,detail=detail),ensure_ascii=False)+'\n')
texts=['화동중학교','수신 내부결재','(경유)','제목 2026학년도 2학기 1회고사 가정통신문 배부','','1. 관련: 화동중학교-[[문서번호 확인 후 기재]]([[시행일 확인 후 기재]])','','2. 화동중학교 2026학년도 2학기 1회고사 안내 가정통신문을 배부하고자 합니다.','','붙임  2026학년도 2학기 1회고사 관련 가정통신문 1부. 끝.']
(W/'draft.md').write_text('# 기안문 초안\n\n베이스: knowledge/templates/본문-가정통신문배부.md. 본문 예시는 3306·7685. HWPX 원본 대신 신규 XML 생성; 기관명·수신·제목·관련·배부 본문·붙임 순서를 따른다.\n\n'+'\n\n'.join(texts)+'\n\n관련번호 미제공. 붙임 실제 파일 0건은 본체만 만드는 요청 범위.\n',encoding='utf-8')
record={'model':'gpt-6-astra','reasoning_effort':'low','authorization':'이 실험 astra-light 수준으로 5건 정도 랜덤 배치로 돌려서 기존 ouput 폴더의 최종 산출물들처럼 나오는지 확인해줘','scope':'같은 입력의 독립 재작성 시험; 별도 문안 승인 발언 또는 검토 점수 없음','request_sha256':sha(W/'request.md'),'draft_sha256':sha(W/'draft.md'),'instruction_hashes':{str(p.relative_to(R)):sha(p) for p in [R/'CLAUDE.md',S/'SKILL.md']},'guide':'find_tasks 120초 timeout; 나머지 조회 미실행','related':'related_lookup --search 2026학년도 2학기 1회고사 exit1'}
(W/'input-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8'); audit('draft','PASS',record)
hp='http://www.hancom.co.kr/hwpml/2011/paragraph'; hh='http://www.hancom.co.kr/hwpml/2011/head'
root=E.parse(str(S/'templates/gonmun/section0.xml')).getroot(); first=root[0]
for c in list(root):
 if c is not first: root.remove(c)
for n in root.findall('.//{'+hp+'}linesegarray'): n.getparent().remove(n)
for i,t in enumerate(texts):
 p=E.SubElement(root,'{'+hp+'}p',id=str(2000000000+i),paraPrIDRef='20' if i==0 else '0',styleIDRef='0',pageBreak='0',columnBreak='0',merged='0')
 run=E.SubElement(p,'{'+hp+'}run',charPrIDRef='7' if i==0 else '0'); E.SubElement(run,'{'+hp+'}t').text=t or None
E.ElementTree(root).write(str(W/'section.xml'),encoding='UTF-8',xml_declaration=True)
h=E.parse(str(S/'templates/gonmun/header.xml'))
for n in h.findall('.//{'+hh+'}font'): n.set('face','굴림')
for n in h.findall('.//{'+hh+'}charPr'):
 if n.get('id')=='0': n.set('height','1200')
h.write(str(W/'header.xml'),encoding='UTF-8',xml_declaration=True)
p=subprocess.run([PY,'-X','utf8',str(S/'scripts/build_hwpx.py'),'--template','gonmun','--section',str(W/'section.xml'),'--header',str(W/'header.xml'),'--output',str(W/'result.hwpx')],capture_output=True,text=True,encoding='utf-8')
(W/'build.log').write_text(p.stdout+p.stderr,encoding='utf-8'); print(p.stdout,p.stderr); audit('generate',str(p.returncode),'build_hwpx gonmun 신규 생성')
