import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import hwpdoc as h

results = []
for name, argv in [
    ('probe', [ROOT / 'scripts/hwpdoc_com_probe.py']),
    ('open', [h.SKILL / 'finalize_hwpx.py', RUN / 'w1-copy.hwpx', '--hancom']),
    ('render', [ROOT / 'scripts/render_check.py', RUN / 'w1-copy.hwpx', '--keep-pdf', RUN / 'restricted-never-created.pdf']),
]:
    start = time.monotonic()
    code, detail = h.run(argv, com=True, timeout=15)
    seconds = time.monotonic()-start
    assert code not in (0, 124, 125) and 'HANCOM_RESTRICTED_CONTEXT' in detail, (name, code, detail)
    assert seconds < 10, (name, seconds)
    results.append({'name': name, 'code': code, 'seconds': seconds, 'detail': detail})
assert not (RUN / 'restricted-never-created.pdf').exists()
print(json.dumps(results, ensure_ascii=False, indent=2))
