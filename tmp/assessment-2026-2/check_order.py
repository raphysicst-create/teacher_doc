import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from render_check import *
w=Path(__file__).resolve().parent
lines=extract_logical_lines(w/'notice-native.hwpx'); a=pick_anchors(lines); t=norm(extract_pdf_text(w/'notice.pdf'))
for i,s in enumerate(a):print(i,t.find(s),s[:100])
