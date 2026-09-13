from pathlib import Path
import sys,zipfile
from lxml import etree as E
w=Path(__file__).resolve().parent
sys.path.insert(0,str(w.parents[1]/'.claude/skills/hwpx/scripts'))
from edit_hwpx import write_raw_preserving_zip
src=w/'notice-native.hwpx'
with zipfile.ZipFile(src) as z:r=E.fromstring(z.read('Contents/section0.xml'))
n={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph'}
for tbl in r.findall('.//hp:tbl',n)[1:]:
 p=tbl.find('hp:pos',n)
 p.set('treatAsChar','1');p.set('affectLSpacing','0');p.set('flowWithText','1')
write_raw_preserving_zip(src,w/'notice-flow.hwpx',{'Contents/section0.xml':E.tostring(r,xml_declaration=True,encoding='UTF-8')})
