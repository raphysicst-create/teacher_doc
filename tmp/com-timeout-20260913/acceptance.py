"""Read-only COM acceptance on copies of the user-approved W1/W2 test documents."""
import datetime
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import hwpdoc as h

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

result = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'steps': [],
          'permission_note': 'Existing user configuration inherited. No sandbox/approval/trust overrides.',
          'python': sys.executable, 'source_hashes': {}}
receipt = RUN / 'acceptance.json'
if receipt.exists():
    result = json.loads(receipt.read_text(encoding='utf-8'))
    if result.get('status') == 'pass' or result.get('interruptions'):
        raise SystemExit('No more resumes allowed.')
    result['interruptions'] = [{'stage': 'w1 Hancom Open', 'reason': 'Independent CLI shell tool terminated at its 10-second limit.',
                                'evidence': 'cli-shell-timeout.stdout.jsonl', 'resume': 'same copies; shell timeout explicitly configured'}]

def save():
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

def step(name, argv):
    if any(s['name'] == name and s['code'] == 0 for s in result['steps']):
        return
    started = time.monotonic()
    code, output = h.run(argv, com=True, timeout=60)
    result['steps'].append({'name': name, 'argv': list(map(str, argv)), 'code': code,
                            'seconds': round(time.monotonic()-started, 3), 'output': output})
    save()
    print(name, code, flush=True)
    if code:
        raise SystemExit(code)

step('COM environment', [ROOT / 'scripts/hwpdoc_com_probe.py'])
for workflow in ('w1', 'w2'):
    source = ROOT / f'tmp/remaining-20260913/codex-marked/.hwpdoc/jobs/approved-{workflow}-20260913/work.hwpx'
    target = RUN / f'{workflow}-copy.hwpx'
    result['source_hashes'][str(source)] = sha(source)
    if target.exists():
        assert sha(target) == sha(source), 'Existing copy changed'
    else:
        shutil.copy2(source, target)
    step(f'{workflow} Hancom Open', [h.SKILL / 'finalize_hwpx.py', target, '--hancom'])
    step(f'{workflow} PDF render', [ROOT / 'scripts/render_check.py', target, '--reference', source,
                                   '--keep-pdf', RUN / f'{workflow}.pdf', '--json'])
    assert sha(target) == sha(source), 'COM changed the HWPX bytes'
result['originals_unchanged'] = all(sha(Path(p)) == digest for p, digest in result['source_hashes'].items())
assert result['originals_unchanged']
result['status'] = 'pass'
save()
print(json.dumps(result, ensure_ascii=False, indent=2))
