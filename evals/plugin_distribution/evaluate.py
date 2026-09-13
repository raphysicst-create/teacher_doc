"""Evidence ledger only. Never runs the product, apps, COM, or approvals.

Self-tests validate this ledger, not product acceptance. Standard library only.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRATCH = ROOT / '.claude/scratchpad/plugin-distribution'
STATES = {'pending', 'blocked', 'fail', 'pass'}
ARTIFACT_STATES = {'not_observed', 'not_produced', 'unconfirmed', 'verified'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def within(root, value):
    root = Path(root).resolve()
    raw = Path(value)
    path = (root / raw).resolve()
    if raw.is_absolute() or not path.is_relative_to(root):
        raise ValueError('상대경로 이탈: ' + str(value))
    return path


def run_folder(value):
    path = Path(value).resolve()
    if path == SCRATCH.resolve() or not path.is_relative_to(SCRATCH.resolve()):
        raise ValueError('run-dir은 .claude/scratchpad/plugin-distribution/ 아래 새 폴더여야 합니다')
    return path


def suite_files():
    return [p for p in HERE.rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix != '.pyc']


def hash_files(root, files):
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(files)}


def subject_files(root, includes):
    root = Path(root).resolve()
    found = set()
    for name in includes:
        p = within(root, name)
        if not p.exists():
            raise ValueError('평가 대상 경로 없음: ' + name)
        candidates = p.rglob('*') if p.is_dir() else [p]
        for child in candidates:
            if child.is_symlink():
                raise ValueError('대상 링크는 실제 포함 파일 목록으로 풀어 기록하세요: ' + str(child))
            resolved = child.resolve()
            if not resolved.is_relative_to(root):
                raise ValueError('대상 junction/경로 이탈: ' + str(child))
            if child.is_file() and '__pycache__' not in child.parts and child.suffix != '.pyc':
                found.add(child)
    if not found:
        raise ValueError('평가 대상 파일 목록이 비었습니다')
    return found


def git_info(root):
    results = {}
    for key, argv in [('head', ['rev-parse', 'HEAD']), ('status', ['status', '--short']),
                      ('diff', ['diff', '--no-ext-diff', 'HEAD', '--']),
                      ('untracked', ['ls-files', '--others', '--exclude-standard'])]:
        try:
            r = subprocess.run(['git', '-C', str(root), *argv], capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=30)
            results[key] = {'exit_code': r.returncode, 'output': r.stdout, 'error': r.stderr}
        except (OSError, subprocess.TimeoutExpired) as exc:
            results[key] = {'unconfirmed': str(exc)}
    return results


def expected_rows(suite):
    for case in suite['cases']:
        for target in case['targets']:
            for variant in case['variants']:
                yield f"{case['id']}--{target}--{variant}", case, target, variant


def checks_for(case, rubric):
    return rubric['common'] + rubric['cases'][case['id']]


def blank_record(case, target, variant, rubric):
    return {
        'case_id': case['id'], 'target': target, 'variant': variant,
        'execution': {'started_at': '', 'finished_at': '', 'actor_thread': '',
                      'mode': '', 'app': '', 'app_version': '', 'engine_version': '',
                      'model': '', 'effort': '', 'os': '', 'synthetic': None,
                      'actual_tool_names': [], 'evidence': []},
        'assessment': {'evaluator_thread': '', 'attested_at': '',
                       'raw_evidence_reviewed': False},
        'checks': {c['id']: {'status': 'pending', 'reason': '미실행',
                              'blocked_reason': '', 'evidence': []}
                   for c in checks_for(case, rubric)},
        'outcomes': {k: {'status': 'not_observed', 'reason': '', 'evidence': []}
                     for k in ('document', 'delivery', 'human_review')},
        'notes': '', 'cleanup': {'performed': False, 'paths': []}
    }


def validate_suite():
    suite, rubric = read(HERE / 'suite.json'), read(HERE / 'rubric.json')
    ids = [c['id'] for c in suite['cases']]
    assert len(ids) == 32 and len(set(ids)) == 32
    assert {c['stage'] for c in suite['cases']} == set(range(1, 8))
    for c in suite['cases']:
        assert c['variants'] and len(c['variants']) == len(set(c['variants']))
        assert set(c['targets']) <= {'cli', 'claude', 'codex', 'teacher_selected'}
        assert within(HERE, c['prompt']).is_file()
        assert within(HERE, c['rubric']).is_file()
        assert c['check_ids'] == [x['id'] for x in rubric['cases'][c['id']]]
        for check in checks_for(c, rubric):
            assert check['text'] and check['evidence_kinds']
    agreement = read(HERE / 'agreement.json')
    assert agreement['status'] == 'agreed'
    assert agreement['implementation_thread'] == suite['implementation_thread']
    return {'cases': len(ids), 'instances': sum(1 for _ in expected_rows(suite)),
            'schema': 'pass', 'product_evaluated': False}


def initialize(args):
    validate_suite()
    run = run_folder(args.run_dir)
    if run.exists():
        raise ValueError('기존 실행 폴더를 덮어쓰지 않습니다')
    suite, rubric = read(HERE / 'suite.json'), read(HERE / 'rubric.json')
    if not args.evaluator_thread or args.evaluator_thread in (suite['author_thread'], suite['implementation_thread']):
        raise ValueError('설계/구현 세션과 다른 실제 평가 세션 ID가 필요합니다')
    subject_root = Path(args.subject_root).resolve()
    includes = read(args.subject_files)
    if not isinstance(includes, list) or not all(isinstance(s, str) for s in includes):
        raise ValueError('subject-files는 상대경로 목록 JSON이어야 합니다')
    hashes = hash_files(subject_root, subject_files(subject_root, includes))
    run.mkdir(parents=True)
    lock = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
            'evaluator_thread': args.evaluator_thread, 'subject_root': str(subject_root),
            'subject_includes': includes, 'subject_hashes': hashes,
            'suite_hashes': hash_files(HERE, suite_files()),
            'scope': suite['scope'], 'synthetic_run': False}
    write_new(run / 'lock.json', lock)
    write_new(run / 'git-snapshot.json', git_info(subject_root))
    write_new(run / 'fixtures.json', {'status': 'pending', 'fixtures': {},
              'note': 'FIXTURES.md에 따라 실제 평가 자료를 결합하세요. 승인/호스트/네이티브 파일을 생성했다고 가정하지 마세요.'})
    for key, case, target, variant in expected_rows(suite):
        write_new(run / 'records' / (key + '.json'), blank_record(case, target, variant, rubric))
    return {'run_dir': str(run), 'instances': sum(1 for _ in expected_rows(suite)),
            'status': 'pending', 'product_evaluated': False}


def evidence_ok(item, run):
    try:
        p = within(run, item['path'])
        return (p.is_file() and bool(item.get('locator')) and bool(item.get('kind'))
                and re.fullmatch(r'[0-9a-f]{64}', item.get('sha256', '')) is not None
                and digest(p) == item['sha256'])
    except (KeyError, TypeError, ValueError, OSError):
        return False


def evidence_kinds(items, run):
    if not isinstance(items, list):
        return set()
    return {i['kind'] for i in items if isinstance(i, dict) and evidence_ok(i, run)}


def seal_fixtures(args):
    run = run_folder(args.run_dir)
    manifest = read(run / 'fixtures.json')
    entries = manifest.get('fixtures', {})
    if not isinstance(entries, dict) or not entries:
        raise ValueError('실제 fixture 결합이 필요합니다')
    hashes = {}
    for name, entry in entries.items():
        if not isinstance(entry, dict) or entry.get('status') not in ('ready', 'pending', 'blocked'):
            raise ValueError('fixture 상태 오류: ' + name)
        for item in entry.get('files', []):
            p = within(run, item['path'])
            if not p.is_file() or digest(p) != item.get('sha256'):
                raise ValueError('fixture 파일 누락/해시 불일치: ' + name)
            hashes[item['path']] = item['sha256']
        if entry['status'] == 'ready' and (not entry.get('files') or not entry.get('provenance')):
            raise ValueError('ready fixture에는 원문 파일과 출처가 필요합니다: ' + name)
    write_new(run / 'fixture-lock.json', {'manifest_sha256': digest(run / 'fixtures.json'), 'files': hashes})
    return {'sealed': True, 'files': len(hashes), 'product_evaluated': False}


def grade_record(record, case, target, variant, rubric, run, evaluator_thread, stale=False, forbidden_threads=()):
    problems = []
    if (record.get('case_id'), record.get('target'), record.get('variant')) != (case['id'], target, variant):
        problems.append('record_identity_mismatch')
    assessment = record.get('assessment', {})
    attested = (assessment.get('evaluator_thread') == evaluator_thread
                and bool(assessment.get('attested_at')) and assessment.get('raw_evidence_reviewed') is True)
    execution = record.get('execution', {})
    identity = (bool(execution.get('actor_thread')) and execution.get('actor_thread') not in forbidden_threads
                and bool(execution.get('started_at')) and bool(execution.get('finished_at')))
    mode = execution.get('mode')
    if target == 'cli':
        environment = mode == 'cli'
    elif target == 'teacher_selected':
        environment = mode == 'human_pilot' and execution.get('app') in ('claude', 'codex') and execution.get('synthetic') is False
    else:
        environment = mode == 'actual_app' and execution.get('app') == target and execution.get('synthetic') is False
    environment = environment and execution.get('os', '').lower().startswith('windows')
    def recorded(value):
        return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {'unknown', 'unconfirmed', 'n/a', 'none'}
    metadata = recorded(execution.get('engine_version'))
    if target != 'cli':
        metadata = metadata and all(recorded(execution.get(k)) for k in ('app_version', 'model', 'effort'))
        names = execution.get('actual_tool_names')
        metadata = metadata and isinstance(names, list) and bool(names) and all(recorded(n) for n in names)
        if case['stage'] == 5 and isinstance(names, list):
            metadata = metadata and not any(str(n).startswith('not_used:') for n in names)
    if not metadata:
        problems.append('execution_metadata_missing')
    execution_refs = execution.get('evidence', [])
    execution_proof = ({'environment', 'inputs', 'observation'} <= evidence_kinds(execution_refs, run)
                       and all(evidence_ok(i, run) for i in execution_refs))
    can_pass = attested and identity and environment and metadata and execution_proof and not problems and not stale
    if not can_pass:
        problems.append('stale' if stale else 'execution_or_attestation_unconfirmed')
    expected_checks = checks_for(case, rubric)
    supplied = record.get('checks', {})
    if not isinstance(supplied, dict):
        supplied = {}
        problems.append('invalid_checks')
    if set(supplied) - {x['id'] for x in expected_checks}:
        problems.append('unknown_checks')
        can_pass = False
    results = {}
    for spec in expected_checks:
        check = supplied.get(spec['id'], {})
        if not isinstance(check, dict):
            problems.append('invalid_check:' + spec['id'])
            check = {}
        state = check.get('status', 'pending')
        if state not in STATES:
            problems.append('invalid_state:' + spec['id'])
            state = 'pending'
        kinds = evidence_kinds(check.get('evidence', []), run) if isinstance(check, dict) else set()
        refs = check.get('evidence', [])
        supported = (bool(check.get('reason')) and set(spec['evidence_kinds']) <= kinds
                     and isinstance(refs, list) and all(evidence_ok(i, run) for i in refs))
        if state == 'pass' and (not can_pass or not supported):
            problems.append('unsupported_pass:' + spec['id'])
            state = 'pending'
        if state == 'fail' and not supported:
            problems.append('unverified_failure:' + spec['id'])
        if state == 'blocked' and (not check.get('reason') or check.get('blocked_reason') not in rubric['blocked_reasons']):
            problems.append('unsupported_block:' + spec['id'])
            state = 'pending'
        results[spec['id']] = state
    states = set(results.values())
    overall = 'fail' if 'fail' in states else 'pending' if 'pending' in states else 'blocked' if 'blocked' in states else 'pass'
    outcomes = {}
    for name, required in [('document', {'pipeline', 'artifacts'}), ('delivery', {'delivery', 'artifacts'}),
                            ('human_review', {'human_review'})]:
        outcome = record.get('outcomes', {}).get(name, {})
        status = outcome.get('status', 'not_observed')
        if status not in ARTIFACT_STATES:
            status = 'unconfirmed'
        outcome_refs = outcome.get('evidence', [])
        outcome_supported = (bool(outcome.get('reason')) and isinstance(outcome_refs, list)
                             and required <= evidence_kinds(outcome_refs, run)
                             and all(evidence_ok(i, run) for i in outcome_refs))
        if status == 'verified' and (not can_pass or target == 'cli' or overall != 'pass'
                                    or not outcome_supported):
            status = 'unconfirmed'
        outcomes[name] = status
    return {'status': overall, 'checks': results, 'problems': problems, 'outcomes': outcomes,
            'critical_failures': [x['id'] for x in expected_checks if x['critical'] and results[x['id']] == 'fail']}


def score(args):
    run = run_folder(args.run_dir)
    lock, suite, rubric = read(run / 'lock.json'), read(HERE / 'suite.json'), read(HERE / 'rubric.json')
    stale = []
    if lock['suite_hashes'] != hash_files(HERE, suite_files()):
        stale.append('suite_changed')
    try:
        now = hash_files(Path(lock['subject_root']), subject_files(lock['subject_root'], lock['subject_includes']))
        if lock['subject_hashes'] != now:
            stale.append('subject_changed')
    except (ValueError, OSError):
        stale.append('subject_unavailable')
    fixture_entries = {}
    try:
        fixture_lock = read(run / 'fixture-lock.json')
        if fixture_lock['manifest_sha256'] != digest(run / 'fixtures.json'):
            stale.append('fixture_manifest_changed')
        for path, expected_hash in fixture_lock['files'].items():
            p = within(run, path)
            if not p.is_file() or digest(p) != expected_hash:
                stale.append('fixture_changed:' + path)
        fixture_entries = read(run / 'fixtures.json')['fixtures']
    except (OSError, ValueError, KeyError, TypeError):
        stale.append('fixtures_unsealed_or_invalid')
    rows = {}
    expected = set()
    for key, case, target, variant in expected_rows(suite):
        expected.add(key + '.json')
        try:
            record = read(run / 'records' / (key + '.json'))
            if not isinstance(record, dict):
                raise ValueError('record must be an object')
            missing_fixtures = [f for f in case['fixtures'] if fixture_entries.get(f, {}).get('status') != 'ready']
            rows[key] = grade_record(record, case, target, variant, rubric, run,
                                      lock['evaluator_thread'], bool(stale) or bool(missing_fixtures),
                                      (suite['author_thread'], suite['implementation_thread']))
            rows[key]['missing_fixtures'] = missing_fixtures
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            rows[key] = {'status': 'pending', 'problems': ['missing_or_invalid_record:' + str(exc)],
                         'critical_failures': [], 'outcomes': {}}
    unexpected = sorted(p.name for p in (run / 'records').glob('*.json') if p.name not in expected)
    counts = Counter(row['status'] for row in rows.values())
    by_stage = {str(stage): dict(Counter(rows[key]['status'] for key, case, _, _ in expected_rows(suite)
                                       if case['stage'] == stage)) for stage in range(1, 8)}
    by_target = {target: dict(Counter(rows[key]['status'] for key, _, t, _ in expected_rows(suite) if t == target))
                 for target in ('cli', 'claude', 'codex', 'teacher_selected')}
    return {'counts': dict(counts), 'expected_instances': len(rows), 'by_stage': by_stage, 'by_target': by_target,
            'release_ready': not stale and not unexpected and counts['pass'] == len(rows),
            'stale': stale, 'unexpected_records': unexpected, 'rows': rows,
            'outcomes': {name: sum(r.get('outcomes', {}).get(name) == 'verified' for r in rows.values())
                         for name in ('document', 'delivery', 'human_review')},
            'notice': '집계기는 증거 파일 무결성과 평가자 판정 기록을 확인할 뿐, 실제 앱·사람 승인·시각 품질의 진위를 보증하지 않습니다. outcomes는 독립 평가 행 수이며 고유 문서 수가 아닙니다.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    init = sub.add_parser('init')
    init.add_argument('--run-dir', required=True)
    init.add_argument('--subject-root', required=True)
    init.add_argument('--subject-files', required=True)
    init.add_argument('--evaluator-thread', required=True)
    scoring = sub.add_parser('score'); scoring.add_argument('--run-dir', required=True)
    sealing = sub.add_parser('seal-fixtures'); sealing.add_argument('--run-dir', required=True)
    ev = sub.add_parser('evidence'); ev.add_argument('--run-dir', required=True)
    ev.add_argument('--path', required=True); ev.add_argument('--kind', required=True); ev.add_argument('--locator', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'check':
            result = validate_suite()
        elif args.command == 'init':
            result = initialize(args)
        elif args.command == 'score':
            result = score(args)
        elif args.command == 'seal-fixtures':
            result = seal_fixtures(args)
        else:
            path = within(run_folder(args.run_dir), args.path)
            result = {'path': args.path, 'sha256': digest(path), 'kind': args.kind, 'locator': args.locator}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.command != 'score' or result['release_ready'] else 2
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print(json.dumps({'error': str(exc), 'product_evaluated': False}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
