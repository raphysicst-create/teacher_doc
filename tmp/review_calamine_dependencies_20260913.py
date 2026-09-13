from pathlib import Path
import concurrent.futures,hashlib,json,tomllib,urllib.request
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'tmp/package-lifecycle-20260913'
lock=tomllib.loads((RUN/'calamine-source-review/Cargo.lock').read_text(encoding='utf-8'))
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'teacher_doc-local-license-review/0.1'})
    return urllib.request.urlopen(req,timeout=40).read()
def review(p):
    name,version=p['name'],p['version'];source=p.get('source','')
    if source.startswith('registry+'):
        url=f'https://crates.io/api/v1/crates/{name}/{version}'
        data=json.loads(get(url));v=data['version']
        assert v['checksum']==p['checksum'],name
        return {'name':name,'version':version,'license':v['license'],'url':url,'checksum':v['checksum']}
    if source.startswith('git+'):
        base='https://raw.githubusercontent.com/omerbenamram/pyo3-file/e88695f375ea3db95d96efc53707f4e8eb1def00/'
        cargo=get(base+'Cargo.toml');(RUN/'calamine-source-review/pyo3-file-Cargo.toml').write_bytes(cargo)
        return {'name':name,'version':version,'license':tomllib.loads(cargo.decode())['package']['license'],'url':base+'Cargo.toml','source':source}
    return {'name':name,'version':version,'license':'MIT','source':'Reviewed python-calamine source distribution LICENSE'}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(review,lock['package']))
out={'count':len(results),'licenses':sorted({r['license'] for r in results}),'scope':'Pinned Cargo.lock checksum and publisher-declared license metadata review. No Rust wheel/source redistribution added; pip installs upstream wheel. Not a full C++/Rust rebuild audit.','packages':results}
(RUN/'calamine-dependency-license-review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'count':out['count'],'licenses':out['licenses']},ensure_ascii=False))
