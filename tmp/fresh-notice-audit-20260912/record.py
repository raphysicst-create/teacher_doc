from pathlib import Path
from datetime import datetime
import hashlib, json

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
evidence = json.loads((WORK / 'hook-fix-evidence.json').read_text(encoding='utf-8'))
evidence['recorded_at'] = datetime.now().astimezone().isoformat()
evidence['modified_file_hashes'] = {
    p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
    for p in evidence['modified_files']
}
(WORK / 'hook-fix-evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
with (ROOT / 'logs/audit.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps({
        'ts': evidence['recorded_at'], 'agent': 'codex-parent',
        'action': 'fresh_reproduction_hook_false_positive_fix',
        'target': evidence['modified_files'], 'result': 'pass_narrow_case',
        'detail': {'evidence': str(WORK / 'hook-fix-evidence.json'),
                   'first_run': 'blocked_before_generation',
                   'regression': '27 tests OK', 'live_copy': 'exit 0',
                   'limit': '첫 독립 실행 통과 또는 동적 셸 전체 보호 완료를 뜻하지 않음'}
    }, ensure_ascii=False) + '\n')
print('Recorded observed hook failure, fix and verification.')
