from pathlib import Path
import hashlib, json, sys, zipfile
from datetime import datetime
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OLD = ROOT / 'output/2026_2학기_1회고사_가정통신문.hwpx'
NS = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
      'hh': 'http://www.hancom.co.kr/hwpml/2011/head'}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def inspect(p):
    with zipfile.ZipFile(p) as z:
        s = E.fromstring(z.read('Contents/section0.xml'))
        h = E.fromstring(z.read('Contents/header.xml'))
    styles = {x.get('id'): x for x in h.findall('.//hh:charPr', NS)}
    titles = []
    for run in s.findall('.//hp:run', NS):
        txt = ''.join(''.join(t.itertext()) for t in run.findall('hp:t', NS))
        if '2026학년도 2학기 1회고사 실시 안내' in txt:
            cp = styles.get(run.get('charPrIDRef'))
            titles.append({'text': txt, 'height': cp.get('height') if cp is not None else None})
    tables = []
    for i, table in enumerate(s.findall('.//hp:tbl', NS)):
        cells = []
        for tr in table.findall('hp:tr', NS):
            for cell in tr.findall('hp:tc', NS):
                item = {k: dict(cell.find('hp:' + k, NS).attrib)
                        for k in ('cellAddr', 'cellSpan', 'cellSz', 'cellMargin')
                        if cell.find('hp:' + k, NS) is not None}
                item['text'] = ' '.join(''.join(t.itertext()) for t in cell.findall('.//hp:t', NS))
                cells.append(item)
        tables.append({'index': i, 'rows': table.get('rowCnt'), 'cols': table.get('colCnt'), 'cells': cells})
    return {'path': str(p), 'sha256': sha(p), 'titles': titles, 'tables': tables}

def snapshot():
    paths = [OLD, ROOT / 'CLAUDE.md', ROOT / '.claude/skills/hwpx/SKILL.md',
             ROOT / '.claude/skills/hwpx/references/editing-details.md']
    paths += list((ROOT / 'knowledge/templates/가정통신문-고사안내').glob('*'))
    paths += list((ROOT / '.claude/skills/hwpx/scripts').rglob('*.py'))
    d = {'at': datetime.now().astimezone().isoformat(),
         'files': {str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()},
         'baseline': inspect(OLD), 'test_kind': 'fresh_context_reproduction',
         'prior_result_visible_to_writer': False,
         'user_review_score': None}
    (WORK / 'before.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('baseline saved', len(d['files']), 'files')

def compare(candidate):
    before = json.loads((WORK / 'before.json').read_text(encoding='utf-8'))
    old = before['baseline']; new = inspect(candidate)
    differences = []
    for a, b in zip(old['tables'], new['tables']):
        shape_a = {k: v for k, v in a.items() if k != 'cells'}
        shape_b = {k: v for k, v in b.items() if k != 'cells'}
        if shape_a != shape_b:
            differences.append({'table': a['index'], 'shape_before': shape_a, 'shape_after': shape_b})
        ma = {json.dumps(c.get('cellAddr'), sort_keys=True): c for c in a['cells']}
        mb = {json.dumps(c.get('cellAddr'), sort_keys=True): c for c in b['cells']}
        for address in sorted(set(ma) | set(mb)):
            ca, cb = ma.get(address), mb.get(address)
            if ca != cb:
                differences.append({'table': a['index'], 'address': address, 'before': ca, 'after': cb})
    d = {'at': datetime.now().astimezone().isoformat(), 'baseline': old['path'],
         'candidate': new['path'], 'candidate_sha256': new['sha256'],
         'source_changes': [p for p, digest in before['files'].items()
                            if not (ROOT / p).is_file() or sha(ROOT / p) != digest],
         'table_counts': [len(old['tables']), len(new['tables'])],
         'titles': [old['titles'], new['titles']], 'cell_differences': differences,
         'interpretation': 'Text/geometry differences require reviewer interpretation; this is not an automatic quality score.'}
    (WORK / 'comparison.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(d, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    if len(sys.argv) == 1:
        snapshot()
    else:
        compare(Path(sys.argv[1]).resolve())
