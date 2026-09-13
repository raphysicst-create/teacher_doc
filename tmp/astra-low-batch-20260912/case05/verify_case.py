from build_case import *
run('hancom-preview',S/'finalize_hwpx.py',O,'--hancom')
run('render-preview',R/'scripts/render_check.py',O,'--reference',B,'--keep-pdf',T/'preview.pdf')
run('render-reference',R/'scripts/render_check.py',B,'--keep-pdf',T/'reference.pdf')
import fitz
for name in ['preview','reference']:
 d=fitz.open(T/(name+'.pdf'))
 for i,p in enumerate(d):p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(T/f'{name}-{i+1}.png')
