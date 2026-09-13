from pathlib import Path
from lxml import etree as E
from copy import deepcopy
import json

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
SKILL = ROOT / '.claude/skills/hwpx'
NS = {'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph', 'hh':'http://www.hancom.co.kr/hwpml/2011/head'}
header = E.parse(str(SKILL/'templates/gonmun/header.xml'))
for font in header.findall('.//hh:font', NS):
    font.set('face', '굴림')
for cp in header.findall('.//hh:charPr', NS):
    if cp.get('id') != '7':
        cp.set('height', '1200')
paras = header.find('.//hh:paraProperties', NS)
for ident, left in [('23',1200),('24',2400)]:
    p = deepcopy(paras.find('hh:paraPr[@id="0"]', NS))
    p.set('id',ident)
    for margin in p.findall('.//hh:margin',NS):
        margin.find('{http://www.hancom.co.kr/hwpml/2011/core}left').set('value',str(left))
    paras.append(p)
paras.set('itemCnt',str(len(paras)))
header.write(str(WORK/'header.xml'),encoding='UTF-8',xml_declaration=True)

template = E.parse(str(SKILL/'templates/gonmun/section0.xml'))
root = E.Element(template.getroot().tag,nsmap=template.getroot().nsmap)
first = deepcopy(template.getroot().find('hp:p',NS))
for cache in first.findall('hp:linesegarray',NS): first.remove(cache)
root.append(first)
rows = [
 ('화동중학교','20','7'),
 ('','0','0'),
 ('수신  내부결재','0','0'),
 ('(경유)','0','0'),
 ('제목  2026년 과학 그리기 대회 참가 학생 출석인정 조퇴 처리','0','0'),
 ('','0','0'),
 ('1. 관련: 강원특별자치도정선교육지원청 교육과-6882(2026. 3. 30.)','0','0'),
 ('2. 2026년 예미랩과 함께하는 과학 그리기 대회에 참가하는 학생의 출결을 다음과 같이 처리하고자 합니다.','0','0'),
 ('가. 일시: 2026. 9. 7.(월) 12:00~16:50','23','0'),
 ('나. 대상: 1학년 1반 학생 2명','23','0'),
 ('1) 1학년 1반  번호:              성명:','24','0'),
 ('2) 1학년 1반  번호:              성명:','24','0'),
 ('다. 장소: 예미랩','23','0'),
 ('라. 사유: 과학 그리기 대회 참가','23','0'),
 ('마. 출결 처리: 출석인정 조퇴. 끝.','23','0'),
]
for i,(text,para,char) in enumerate(rows,2):
    p=E.SubElement(root,'{'+NS['hp']+'}p',id=str(1000000000+i),paraPrIDRef=para,styleIDRef='0',pageBreak='0',columnBreak='0',merged='0')
    run=E.SubElement(p,'{'+NS['hp']+'}run',charPrIDRef=char)
    E.SubElement(run,'{'+NS['hp']+'}t').text=text or None
E.ElementTree(root).write(str(WORK/'section0.xml'),encoding='UTF-8',xml_declaration=True)
(WORK/'확정문안.md').write_text('\n'.join(row[0] for row in rows)+'\n',encoding='utf-8')
(WORK/'content.rules.json').write_text(json.dumps({'require':['2026. 9. 7.(월) 12:00~16:50','1학년 1반 학생 2명','예미랩','출석인정 조퇴','교육과-6882(2026. 3. 30.)'], 'forbid':['[[','{{','대회 장소','학생1','학생2']},ensure_ascii=False,indent=2),encoding='utf-8')
print('XML and confirmed draft prepared')
