from pathlib import Path
import hashlib,json,shutil,sys,datetime,urllib.request,tarfile,io
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'tmp/package-lifecycle-20260913'
sys.path.insert(0,str(RUN/'calamine-runtime'));sys.path.insert(0,str(ROOT/'scripts'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if not (RUN/'before').exists():
    for name in ['scripts/refresh_reference.py','scripts/hwpdoc_runtime.py','distribution/README.md','distribution/requirements-school-data.txt','distribution/rights.pending.json','distribution/release-files.json','distribution/source-bundle.json','distribution/pymupdf-agpl-decision-2026-09-13.json','distribution/legal/NOTICE.md','distribution/legal/CHANGES.md']:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
    save(RUN/'protected-before.json',{p.relative_to(ROOT).as_posix():sha(p) for d in ['knowledge','output','.hwpdoc/templates'] for p in (ROOT/d).rglob('*') if p.is_file()})
import xlrd
from python_calamine import CalamineWorkbook
source=ROOT/'knowledge/reference/사업관리카드-예산-2026.xls'
copy=RUN/'probe-input'/source.name;copy.parent.mkdir(exist_ok=True);shutil.copy2(source,copy)
with CalamineWorkbook.from_path(str(copy)) as b:rows=b.get_sheet_by_index(0).to_python(skip_empty_area=False)
old=xlrd.open_workbook(str(copy));sheet=old.sheet_by_index(0)
diff=[];types={}
for r in range(sheet.nrows):
    for c in range(min(3,sheet.ncols)):
        v=rows[r][c] if r<len(rows) and c<len(rows[r]) else ''
        a=sheet.cell_value(r,c);key=type(a).__name__+' -> '+type(v).__name__;types[key]=types.get(key,0)+1
        if a!=v:diff.append({'row':r,'col':c,'old_type':type(a).__name__,'new_type':type(v).__name__})
assert not diff,diff[:10]
save(RUN/'calamine-cell-comparison.json',{'source_sha256':sha(source),'copy_sha256':sha(copy),'source_unchanged':sha(source)==sha(copy),'rows':sheet.nrows,'compared_columns':3,'compared_cells':sheet.nrows*min(3,sheet.ncols),'value_differences':diff,'type_pairs':types})
meta=json.load(urllib.request.urlopen('https://pypi.org/pypi/python-calamine/0.7.0/json',timeout=30))
save(RUN/'python-calamine-pypi.json',meta)
s=next(x for x in meta['urls'] if x['packagetype']=='sdist');archive=RUN/s['filename']
if not archive.exists():archive.write_bytes(urllib.request.urlopen(s['url'],timeout=30).read())
assert sha(archive)==s['digests']['sha256']
with tarfile.open(archive) as tf:
    entries=[n for n in tf.getnames() if n.endswith(('LICENSE','Cargo.toml','Cargo.lock','pyproject.toml'))]
    save(RUN/'calamine-source-inspection.json',{'sdist_sha256':sha(archive),'url':s['url'],'entries':entries,'license_expression':meta['info'].get('license_expression'),'requires_dist':meta['info'].get('requires_dist')})
    for n in entries:
        target=RUN/'calamine-source-review'/Path(n).name;target.parent.mkdir(exist_ok=True);target.write_bytes(tf.extractfile(n).read())
print(json.dumps({'cell_comparison':'pass','rows':sheet.nrows,'type_pairs':types,'source_license':meta['info'].get('license_expression'),'source_entries':entries},ensure_ascii=False))
