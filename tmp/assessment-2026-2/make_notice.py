from pathlib import Path
from copy import deepcopy
import sys,json,hashlib,datetime,re
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'.claude/skills/hwpx/scripts'))
from edit_hwpx import write_raw_preserving_zip
W=ROOT/'tmp/assessment-2026-2'
ns={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph'}
hp='{'+ns['hp']+'}'
base=ROOT/'knowledge/examples/(화동중학교-2956 (첨부)) 2026학년도 1학기 과목별 평가계획 안내 가정통신문.hwp.hwpx'
draft=ROOT/'output/2026학년도_2학기_평가계획_가정통신문_초안.md'
md=draft.read_text(encoding='utf-8')
tables=[]
for block in md.split('## ')[2:4]:
 rows=[[c.strip() for c in line.strip('|').split('|')] for line in block.splitlines() if line.startswith('|') and '---' not in line]
 tables.append(rows)
assert [len(x) for x in tables]==[12,12]
root=E.parse(str(W/'section.xml')).getroot()
old=list(root)
def plain(text,pi=18,ci=23):
 p=E.Element(hp+'p',id='0',paraPrIDRef=str(pi),styleIDRef='0',pageBreak='0',columnBreak='0',merged='0')
 run=E.SubElement(p,hp+'run',charPrIDRef=str(ci)); E.SubElement(run,hp+'t').text=text
 return p
header=deepcopy(old[0])
for t in header.findall('.//hp:t',ns):
 if t.text and '화동중 제2026-20호' in t.text:t.text=t.text.replace('화동중 제2026-20호','화동중 제2026-[[번호]]호')
origtable=old[8].find('.//hp:tbl',ns)
assert origtable is not None
cell=origtable.find('hp:tr/hp:tc',ns)
def table(rows,widths):
 tbl=deepcopy(origtable)
 for tr in tbl.findall('hp:tr',ns):tbl.remove(tr)
 tbl.set('rowCnt',str(len(rows)));tbl.set('colCnt',str(len(widths)));tbl.set('repeatHeader','1')
 tbl.set('pageBreak','CELL')
 total=0
 for ri,row in enumerate(rows):
  # Original 10pt text, full-width grade-one descriptions; enough height for wraps.
  lines=max(max(1,__import__('math').ceil(sum(1 if ord(c)>255 else .55 for c in text)/(widths[ci]/1000-1.1))) for ci,text in enumerate(row))
  height=max(1450,lines*1050+350);total+=height
  tr=E.SubElement(tbl,hp+'tr')
  for ci,text in enumerate(row):
   tc=deepcopy(cell);tr.append(tc)
   tc.set('header','1' if ri==0 else '0');tc.set('borderFillIDRef','11')
   sl=tc.find('hp:subList',ns)
   for ch in list(sl):sl.remove(ch)
   sl.append(plain(text))
   tc.find('hp:cellAddr',ns).attrib.update({'rowAddr':str(ri),'colAddr':str(ci)})
   tc.find('hp:cellSpan',ns).attrib.update({'rowSpan':'1','colSpan':'1'})
   tc.find('hp:cellSz',ns).attrib.update({'width':str(widths[ci]),'height':str(height)})
  
 tbl.find('hp:sz',ns).attrib.update({'width':str(sum(widths)),'height':str(total)})
 p=plain('');p.find('hp:run',ns).insert(0,tbl)
 return p
for ch in list(root):root.remove(ch)
root.append(header)
root.append(plain('2026학년도 2학기 과목별 평가계획 안내',14,21))
root.append(plain('학부모님, 안녕하십니까? 항상 본교의 교육활동에 관심과 성원을 보내주셔서 감사합니다. 2026학년도 2학기 고사 일정과 과목별 평가계획을 다음과 같이 안내드립니다. 학생들이 평가 내용을 확인하고 자기주도적으로 학습할 수 있도록 가정에서도 관심과 격려를 부탁드립니다.',15,17))
root.append(plain('1. 고사 일정',17,22))
root.append(plain('2학기 1회고사: 2026. 10. 27. ~ 2026. 10. 28. / 2학기 2회고사: 2026. 12. 7. ~ 2026. 12. 8.',18,23))
root.append(plain('※ 1학년은 자유학기로 지필고사를 실시하지 않으며, 학습 과정과 성장을 중심으로 평가합니다.',19,26))
root.append(plain('2. 1학년 과목별 평가계획',17,22))
root.append(table(tables[0],[6300,40885]))
root.append(plain('※ 자유학기 평가 결과는 학생의 학습 과정과 성장 정도를 중심으로 기록합니다.',19,26))
root.append(plain('3. 2학년 과목별 평가 반영 비율',17,22))
root.append(table(tables[1],[5500,4300,4300,4300,28785]))
root.append(plain('※ 평가계획이 변경될 경우 평가 실시 전에 학생과 학부모님께 안내하겠습니다.',19,26))
root.append(plain('[[배부일]]',20,28))
root.append(deepcopy(old[13]))
for node in root.findall('.//hp:linesegarray',ns):node.getparent().remove(node)
for i,p in enumerate(root.findall('.//hp:p',ns)):p.set('id',str(1000000000+i))
for i,tbl in enumerate(root.findall('.//hp:tbl',ns)):tbl.set('id',str(1100000000+i))
out=W/'notice.hwpx'
write_raw_preserving_zip(base,out,{'Contents/section0.xml':E.tostring(root,xml_declaration=True,encoding='UTF-8')})
record={'confirmed':True,'by':'user','record':'사용자: 작성해줘','at':datetime.datetime.now().astimezone().isoformat(),'draft_sha256':hashlib.sha256(draft.read_bytes()).hexdigest(),'layout':'승인 초안의 학년별 2개 표로 재구성. 원본 서체·머리말·용지 크기 유지. 원본 1쪽 유지 목표.'}
(W/'approval.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(out)
