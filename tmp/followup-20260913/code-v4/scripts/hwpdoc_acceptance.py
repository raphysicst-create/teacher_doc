"""36-run acceptance ledger. Only evidence-backed, reviewed model runs count."""
import argparse
from pathlib import Path
from hwpdoc import ROOT, sha, read_json, write_json, now

CASES = ('general_notice', 'reply_notice', 'budget_names', 'extra_activities', 'w2_unknowns', 'residue_package_com')
ENVS = ('work_local', 'codex_sol_high')
COUNTERS = ('missing_required_steps', 'fabricated_values', 'content_damage', 'false_pass_reports')


def new_matrix():
    return dict(version=1, created_at=now(), user_simulation={'environment': 'Linux temporary',
                'source': 'user-provided result; not reproduced here', 'claude': 'blocked', 'codex': 'allowed',
                'windows_integration': False}, runs=[dict(environment=e, case=c, repeat=r, status='unverified')
                for e in ENVS for c in CASES for r in range(1, 4)],
                skill_only_comparison={'status': 'unverified', 'required': 'same input, model, tools; old vs skill-only configuration; exclude runner effect'})


def record(matrix, result):
    key = (result.get('environment'), result.get('case'), result.get('repeat'))
    row = next((r for r in matrix['runs'] if (r['environment'], r['case'], r['repeat']) == key), None)
    if row is None: raise ValueError('Unknown environment/case/repeat')
    for other in matrix['runs']:
        if other['case'] == result.get('case') and other.get('input_sha256') and other['input_sha256'] != result.get('input_sha256'):
            raise ValueError('Same representative case must use identical input across both environments and all repeats')
    for field in ('model', 'reasoning_effort', 'app_version', 'engine_version', 'input_sha256', 'started_at', 'finished_at',
                  'transcript', 'instructions', 'skill', 'review', 'counters', 'outcome'):
        if not result.get(field): raise ValueError('Evidence field required: ' + field)
    if result['environment'] == 'codex_sol_high' and (result['model'] != 'gpt-5.6-sol' or result['reasoning_effort'] != 'high'):
        raise ValueError('Codex acceptance requires the requested gpt-5.6-sol high')
    if result['outcome'] not in ('verified_review_copy', 'appropriate_question', 'appropriate_hold'):
        raise ValueError('Unknown outcome')
    if result['review'].get('confirmed') is not True or not result['review'].get('by') or not result['review'].get('record'):
        raise ValueError('Human review evidence required')
    for counter in COUNTERS:
        value = result['counters'].get(counter)
        if type(value) is not int or value < 0: raise ValueError('Invalid failure counter: ' + counter)
    evidence_paths = [result['transcript'], *result['instructions'], result['skill']]
    for entry in evidence_paths:
        p = Path(entry['path'])
        if not p.is_file() or sha(p) != entry['sha256']: raise ValueError('Missing or changed evidence: ' + str(p))
    # Captured skill body, not merely a skill selector listing.
    if result['skill'].get('body_loaded') is not True or not result['skill'].get('canonical_path'):
        raise ValueError('Actual canonical skill body loading evidence required')
    if any(x.get('body_loaded') is not True for x in result['instructions']):
        raise ValueError('Actual instruction body loading evidence required')
    row.update(result, status='pass' if not any(result['counters'].values()) else 'fail', recorded_at=now())


def summary(matrix):
    runs = matrix['runs']
    return dict(total=len(runs), passed=sum(r['status'] == 'pass' for r in runs),
                failed=sum(r['status'] == 'fail' for r in runs), unverified=sum(r['status'] == 'unverified' for r in runs),
                complete=all(r['status'] == 'pass' for r in runs) and matrix['skill_only_comparison']['status'] == 'pass')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'record', 'status'))
    parser.add_argument('--result')
    args = parser.parse_args()
    path = ROOT / '.hwpdoc/acceptance.json'
    if args.command == 'init':
        if not path.exists(): write_json(path, new_matrix())
    elif args.command == 'record':
        if not args.result: parser.error('--result required')
        matrix = read_json(path); record(matrix, read_json(args.result)); write_json(path, matrix)
    import json
    print(json.dumps(summary(read_json(path)), ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
