"""Synthetic ledger tests only: no HWPX/product/COM/app/human evaluation."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import evaluate as e


class LedgerTests(unittest.TestCase):
    def setUp(self):
        e.SCRATCH.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='ledger-selftest-', dir=e.SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.suite = e.read(e.HERE / 'suite.json')
        self.rubric = e.read(e.HERE / 'rubric.json')
        self.case = next(c for c in self.suite['cases'] if c['id'] == '23')
        self.record = e.blank_record(self.case, 'codex', 'default', self.rubric)
        self.raw = self.run / 'synthetic.txt'
        self.raw.write_text('SYNTHETIC LEDGER TEST. No real run or human approval.\n', encoding='utf-8')

    def ref(self, kind):
        return {'path': 'synthetic.txt', 'sha256': e.digest(self.raw), 'kind': kind, 'locator': 'line 1 (synthetic)'}

    def ready(self):
        # Fabricated metadata is confined to a ledger unit test, never acceptance.
        self.record['execution'].update(started_at='2026-09-13T01:00:00+09:00',
            finished_at='2026-09-13T01:01:00+09:00', actor_thread='synthetic-third-session',
            mode='actual_app', app='codex', os='Windows synthetic', synthetic=False,
            app_version='synthetic-v1', engine_version='synthetic-python',
            model='synthetic-model', effort='synthetic-effort', actual_tool_names=['synthetic-tool'],
            evidence=[self.ref(k) for k in ('environment', 'inputs', 'observation')])
        self.record['assessment'].update(evaluator_thread='synthetic-third-session',
            attested_at='2026-09-13T01:02:00+09:00', raw_evidence_reviewed=True)
        for c in e.checks_for(self.case, self.rubric):
            self.record['checks'][c['id']].update(status='pass', reason='synthetic parser exercise',
                evidence=[self.ref(k) for k in c['evidence_kinds']])

    def grade(self, **kwargs):
        return e.grade_record(self.record, self.case, 'codex', 'default', self.rubric,
                              self.run, 'synthetic-third-session', **kwargs)

    def test_package_has_32_cases_176_unique_rows(self):
        self.assertEqual(e.validate_suite()['instances'], 176)
        self.assertEqual(len({r[0] for r in e.expected_rows(self.suite)}), 176)

    def test_empty_record_never_passes(self):
        self.assertEqual(self.grade()['status'], 'pending')

    def test_pass_without_evidence_is_pending(self):
        for c in self.record['checks'].values():
            c.update(status='pass', reason='unsupported')
        self.assertEqual(self.grade()['status'], 'pending')

    def test_synthetic_parser_positive_control(self):
        self.ready()
        self.assertEqual(self.grade()['status'], 'pass')
        self.assertEqual(self.grade()['outcomes']['document'], 'not_observed')

    def test_wrong_app_cannot_fill_other_app(self):
        self.ready(); self.record['execution']['app'] = 'claude'
        self.assertEqual(self.grade()['status'], 'pending')

    def test_actual_app_requires_execution_metadata(self):
        for field in ('app_version', 'engine_version', 'model', 'effort', 'actual_tool_names'):
            with self.subTest(field=field):
                self.ready()
                self.record['execution'][field] = [] if field == 'actual_tool_names' else ''
                self.assertEqual(self.grade()['status'], 'pending')

    def test_cli_cannot_be_actual_app(self):
        self.ready(); self.record['execution']['mode'] = 'cli'
        self.assertEqual(self.grade()['status'], 'pending')

    def test_mock_cannot_be_actual_app(self):
        self.ready(); self.record['execution']['synthetic'] = True
        self.assertEqual(self.grade()['status'], 'pending')

    def test_evaluator_attestation_required(self):
        self.ready(); self.record['assessment']['raw_evidence_reviewed'] = False
        self.assertEqual(self.grade()['status'], 'pending')

    def test_wrong_evaluator_rejected(self):
        self.ready(); self.record['assessment']['evaluator_thread'] = 'other'
        self.assertEqual(self.grade()['status'], 'pending')

    def test_forbidden_actor_cannot_self_evaluate(self):
        self.ready()
        self.assertEqual(self.grade(forbidden_threads=('synthetic-third-session',))['status'], 'pending')

    def test_variant_identity_not_interchangeable(self):
        self.ready(); self.record['variant'] = 'unknown'
        self.assertEqual(self.grade()['status'], 'pending')

    def test_missing_check_is_pending(self):
        self.ready(); del self.record['checks']['C1']
        self.assertEqual(self.grade()['status'], 'pending')

    def test_unknown_state_not_success(self):
        self.ready(); self.record['checks']['C1']['status'] = 'not_applicable'
        self.assertEqual(self.grade()['status'], 'pending')

    def test_malformed_check_preserves_other_failure(self):
        self.ready()
        self.record['checks']['G2']['status'] = 'fail'
        self.record['checks']['C1'] = None
        result = self.grade()
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['checks']['C1'], 'pending')

    def test_critical_failure_cannot_average_out(self):
        self.ready(); self.record['checks']['G2']['status'] = 'fail'
        result = self.grade()
        self.assertEqual(result['status'], 'fail')
        self.assertIn('G2', result['critical_failures'])

    def test_environment_block_stays_block(self):
        for check in self.record['checks'].values():
            check.update(status='blocked', reason='no isolated host', blocked_reason='environment')
        self.assertEqual(self.grade()['status'], 'blocked')

    def test_undocumented_block_is_pending(self):
        for check in self.record['checks'].values():
            check.update(status='blocked', reason='')
        self.assertEqual(self.grade()['status'], 'pending')

    def test_tampered_evidence_invalidates_pass(self):
        self.ready(); self.raw.write_text('changed', encoding='utf-8')
        self.assertEqual(self.grade()['status'], 'pending')

    def test_mixed_stale_evidence_rejected(self):
        self.ready()
        self.record['checks']['C1']['evidence'].append({'path': 'missing', 'kind': 'extra', 'locator': '1', 'sha256': '0'*64})
        self.assertEqual(self.grade()['status'], 'pending')

    def test_stale_subject_invalidates_pass(self):
        self.ready(); self.assertEqual(self.grade(stale=True)['status'], 'pending')

    def test_path_traversal_and_absolute_rejected(self):
        for p in ('../escape', str(self.run / 'synthetic.txt')):
            with self.assertRaises(ValueError):
                e.within(self.run, p)

    def test_no_document_outcome_from_unsupported_claim(self):
        self.ready(); self.record['outcomes']['document']['status'] = 'verified'
        self.assertEqual(self.grade()['outcomes']['document'], 'unconfirmed')

    def test_outcome_requires_reason_and_all_current_evidence(self):
        self.ready()
        outcome = self.record['outcomes']['document']
        outcome.update(status='verified', reason='', evidence=[self.ref('pipeline'), self.ref('artifacts')])
        self.assertEqual(self.grade()['outcomes']['document'], 'unconfirmed')
        outcome['reason'] = 'synthetic parser exercise only'
        self.assertEqual(self.grade()['outcomes']['document'], 'verified')
        outcome['evidence'].append({'path': 'missing', 'kind': 'extra', 'locator': '1', 'sha256': '0'*64})
        self.assertEqual(self.grade()['outcomes']['document'], 'unconfirmed')

    def init_run(self):
        subject = self.run / 'subject'; subject.mkdir()
        (subject / 'code.py').write_text('# synthetic subject, not product\n', encoding='utf-8')
        listing = self.run / 'files.json'; e.write_new(listing, ['code.py'])
        args = SimpleNamespace(run_dir=str(self.run / 'run'), subject_root=str(subject),
                               subject_files=str(listing), evaluator_thread='synthetic-third-session')
        with patch.object(e, 'git_info', return_value={'synthetic': True}):
            e.initialize(args)
        return args, subject

    def test_init_creates_only_pending_rows(self):
        args, _ = self.init_run()
        result = e.score(args)
        self.assertEqual(result['counts'], {'pending': 176})
        self.assertFalse(result['release_ready'])
        self.assertEqual(result['outcomes']['document'], 0)

    def test_init_refuses_overwrite(self):
        args, _ = self.init_run()
        with self.assertRaises(ValueError):
            e.initialize(args)

    def test_init_rejects_author_session(self):
        args, _ = self.init_run(); args.run_dir += '-other'
        args.evaluator_thread = self.suite['author_thread']
        with self.assertRaises(ValueError):
            e.initialize(args)

    def test_subject_change_is_stale(self):
        args, subject = self.init_run()
        (subject / 'code.py').write_text('# changed\n', encoding='utf-8')
        self.assertIn('subject_changed', e.score(args)['stale'])

    def test_missing_record_and_unknown_record_not_skipped(self):
        args, _ = self.init_run(); run = Path(args.run_dir)
        next((run / 'records').glob('*.json')).unlink()
        e.write_new(run / 'records' / 'fake-extra.json', {})
        result = e.score(args)
        self.assertEqual(result['expected_instances'], 176)
        self.assertFalse(result['release_ready'])
        self.assertEqual(result['unexpected_records'], ['fake-extra.json'])

    def test_fixture_seal_and_tamper_detection(self):
        args, _ = self.init_run(); run = Path(args.run_dir)
        fixture = run / 'input.txt'; fixture.write_text('synthetic', encoding='utf-8')
        manifest = {'fixtures': {'sample': {'status': 'ready', 'provenance': 'synthetic unit test',
                    'files': [{'path': 'input.txt', 'sha256': e.digest(fixture)}]}}}
        (run / 'fixtures.json').write_text(__import__('json').dumps(manifest), encoding='utf-8')
        e.seal_fixtures(args)
        fixture.write_text('changed', encoding='utf-8')
        self.assertIn('fixture_changed:input.txt', e.score(args)['stale'])


if __name__ == '__main__':
    unittest.main()
