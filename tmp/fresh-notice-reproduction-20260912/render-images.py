from pathlib import Path
import fitz
p=Path(__file__).resolve().parent
for name in ['preview','reference','final']:
    path=p/f'{name}.pdf'
    if path.exists():
        doc=fitz.open(path)
        for i,page in enumerate(doc):
            page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(p/f'{name}-{i+1}.png')
        print(name,len(doc))
