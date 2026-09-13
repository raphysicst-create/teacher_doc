from zipfile import ZipFile
from lxml import etree as E
from pathlib import Path
import sys
n={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph'}
with ZipFile(sys.argv[1]) as z:
 r=E.fromstring(z.read('Contents/section0.xml'))
 for i,t in enumerate(r.findall('.//hp:tbl',n)):
  print('TABLE',i,dict(t.attrib))
  print('SIZE', dict(t.find('hp:sz',n).attrib))
  for row in t.findall('hp:tr',n)[:3]:
   for c in row.findall('hp:tc',n):
    print(dict(c.find('hp:cellAddr',n).attrib), dict(c.find('hp:cellSz',n).attrib),dict(c.find('hp:cellSpan',n).attrib))
 if len(sys.argv)>2 and 'Preview/PrvImage.png' in z.namelist():
  Path(sys.argv[2]).write_bytes(z.read('Preview/PrvImage.png'))
