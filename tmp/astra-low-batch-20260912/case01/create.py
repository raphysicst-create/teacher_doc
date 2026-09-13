from pathlib import Path
from lxml import etree as E
import json,hashlib,datetime,subprocess
r=Path.cwd(); w=r/'tmp/astra-low-batch-20260912/case01'; w.mkdir(parents=True,exist_ok=True)
s=r/'.claude/skills/hwpx'; ns={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph','hh':'http://www.hancom.co.kr/hwpml/2011/head'}
root=E.parse(str(s/'templates/gonmun/section0.xml')).getroot()
for x in list(root)[1:]:root.remove(x)
lines=['화동중학교','','수신 내부결재','(경유)','제목  2026학년도 2학기 1회고사 출제 관련 연수','','1. 관련: 화동중학교-2058(2026. 3. 17.)','','2. 2026학년도 2학기 1회고사 출제 관련 연수를 다음과 같이 실시하고자 합니다.','  가. 일시: 2026. 10. 8. 13:00','  나. 장소: 교무실','  다. 대상: 전 교원','','붙임  2026학년도 2학기 시험출제 관련 연수 자료 1부.  끝.']
for i,t in enumerate(lines,2):
 p=E.SubElement(root,'{'+ns['hp']+'}p',id=str(1000000000+i),paraPrIDRef='20' if i==2 else '0',styleIDRef='0',pageBreak='0',columnBreak='0',merged='0')
 run=E.SubElement(p,'{'+ns['hp']+'}run',charPrIDRef='7' if i==2 else '0'); E.SubElement(run,'{'+ns['hp']+'}t').text=t
E.ElementTree(root).write(str(w/'section.xml'),encoding='utf-8',xml_declaration=True)
h=E.parse(str(s/'templates/gonmun/header.xml'))
for x in h.findall('.//hh:font',ns):x.set('face','굴림')
for x in h.findall('.//hh:charPr',ns):
 if x.get('id')!='7':x.set('height','1200')
h.write(str(w/'header.xml'),encoding='utf-8',xml_declaration=True)
(w/'draft.md').write_text('\n'.join(lines),encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(w/'provenance.json').write_text(json.dumps({'model':'gpt-6-astra','reasoning':'low','approval_quote':'이 실험 astra-light 수준으로 5건 정도 랜덤 배치로 돌려서 기존 ouput 폴더의 최종 산출물들처럼 나오는지 확인해줘','approval_scope':'독립 재작성 실험의 기안문 본체 생성. 새 검토 점수나 발송 승인 없음','draft_sha256':sha(w/'draft.md'),'request_sha256':sha(w/'request.md'),'instructions':{str(p):sha(p) for p in [r/'CLAUDE.md',s/'SKILL.md']},'base':'유사 본문 PDF 3206 + 본문-내부결재.md 실시형. 편집 가능한 동일 HWPX 없음, gonmun XML 신규 생성'},ensure_ascii=False,indent=2),encoding='utf-8')
(w/'rules.json').write_text(json.dumps({'forbid':['1학기','2025. 4. 17.','2026. 4. 16.','농어촌유학','정책기획과-3100'],'require':['2026학년도 2학기 1회고사 출제 관련 연수','화동중학교-2058(2026. 3. 17.)','2026. 10. 8. 13:00','교무실','전 교원','2026학년도 2학기 시험출제 관련 연수 자료 1부.']},ensure_ascii=False),encoding='utf-8')
