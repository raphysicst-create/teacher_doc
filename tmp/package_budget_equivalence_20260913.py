from pathlib import Path
import sys,importlib.util,json,hashlib,unittest
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'tmp/package-lifecycle-20260913'
sys.path[:0]=[str(RUN/'calamine-runtime'),str(ROOT/'scripts')]
results=[];source=RUN/'probe-input/사업관리카드-예산-2026.xls'
for i,p in enumerate([RUN/'before/scripts/refresh_reference.py',ROOT/'scripts/refresh_reference.py']):
    spec=importlib.util.spec_from_file_location('budget_probe_'+str(i),p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.BUDGET_XLS=source;m.BUDGET_JSON=RUN/f'budget-derived-{i}.json'
    results.append(m.build_budget())
a=(RUN/'budget-derived-0.json').read_bytes();b=(RUN/'budget-derived-1.json').read_bytes()
assert a==b
(RUN/'budget-json-comparison.json').write_text(json.dumps({'equal_bytes':True,'counts':results,'sha256':hashlib.sha256(a).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
print(results,'byte-identical derived JSON')
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_budget_reader.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
