"""Synthetic grader regression tests. These are NOT the five model evaluations."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import evaluate as e


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.suite = e.read(e.HERE / 'suite.json')
        self.rubric = e.read(e.HERE / 'rubric.json')
        self.case = self.suite['cases'][0]
        self.record = e.init_record(self.case, self.suite, self.rubric)
        scratch = e.ROOT / '.claude/scratchpad/workflow-eval-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.log = self.base / 'synthetic.txt'
        self.log.write_text('SOFTWARE TEST ONLY. No model run or user approval.', encoding='utf-8')
        self.ref = {'path': str(self.log), 'sha256': e.digest(self.log), 'locator': 'line 1'}

    def grade(self):
        return e.grade(self.record, self.case, self.suite, self.rubric, self.base)

    def simulated_checkpoint(self):
        self.record['started_at'] = '2026-09-11T00:00:00+09:00'
        self.record['transcript'] = self.ref
        self.record['environment'].update(app='ChatGPT Work', local=True, evidence=self.ref)
        self.record['outcome'] = self.case['expected_checkpoint']
        for row in self.record['checks'].values():
            row.update(status='pass', reason='synthetic grader fixture', evidence=[self.ref])

    def test_empty_is_not_five_successes(self):
        result = self.grade()
        self.assertFalse(result['real_work_started'])
        self.assertFalse(result['checkpoint_pass'])
        self.assertEqual(result['checks']['pass'], 0)
        self.assertFalse(result['accepted_document'])

    def test_unsupported_pass_claim_is_unverified(self):
        for row in self.record['checks'].values():
            row['status'] = 'pass'
        self.assertEqual(self.grade()['checks']['pass'], 0)

    def test_checkpoint_does_not_count_as_document(self):
        self.simulated_checkpoint()
        result = self.grade()
        self.assertTrue(result['checkpoint_pass'])
        self.assertFalse(result['document_verified'])
        self.assertFalse(result['accepted_document'])

    def test_critical_failure_survives_other_passes(self):
        self.simulated_checkpoint()
        self.record['checks']['honest_values']['status'] = 'fail'
        result = self.grade()
        self.assertFalse(result['checkpoint_pass'])
        self.assertEqual(result['critical_failures'], ['honest_values'])

    def test_changed_evidence_invalidates_claim(self):
        self.simulated_checkpoint()
        self.log.write_text('changed', encoding='utf-8')
        self.assertFalse(self.grade()['real_work_started'])
        self.assertEqual(self.grade()['checks']['pass'], 0)

    def test_non_work_run_not_counted(self):
        self.simulated_checkpoint()
        self.record['environment']['app'] = 'Codex'
        self.assertFalse(self.grade()['real_work_started'])

    def test_cloud_run_not_counted_as_local(self):
        self.simulated_checkpoint()
        self.record['environment']['local'] = False
        self.assertFalse(self.grade()['checkpoint_pass'])

    def test_changed_prompt_has_diagnostic(self):
        self.simulated_checkpoint()
        self.record['input_sha256'] = '0' * 64
        self.assertIn('INPUT_CHANGED', [x['code'] for x in self.grade()['diagnostics']])
        self.assertFalse(self.grade()['checkpoint_pass'])

    def test_not_applicable_cannot_skip_rubric(self):
        self.record['checks']['approval']['status'] = 'not_applicable'
        with self.assertRaises(ValueError):
            self.grade()

    def test_typo_not_silently_ignored(self):
        self.record['checks']['wrong_field'] = {'status': 'pass'}
        with self.assertRaises(ValueError):
            self.grade()

    def test_wrong_case_rejected(self):
        self.record['case'] = '05_w2'
        with self.assertRaises(ValueError):
            self.grade()

    def test_manual_review_requires_real_file_reference(self):
        self.record['human_review'] = {'approved': True, 'score': 5, 'evidence': None}
        self.assertFalse(self.grade()['human_reviewed'])

    def test_stale_runner_report_is_unverified(self):
        self.record['runner_report'] = dict(self.ref, sha256='0' * 64)
        self.assertIn('STALE_REPORT', [x['code'] for x in self.grade()['diagnostics']])

    def test_com_failure_classified_separately(self):
        report = {'stages': {s: {'status': 'pass'} for s in e.h.STAGES}, 'dependencies': {'fixture': 'hash'}}
        report['stages']['hancom'] = {'status': 'fail', 'reason': 'synthetic COM failure'}
        with patch.object(e, 'read', return_value=report), patch.object(e.h, 'freshness', return_value=[]), patch.object(e.h, 'result_state', return_value='fail'):
            verified, delivered, issues = e.runner_diagnostics(self.ref, self.base)
        self.assertFalse(verified)
        self.assertFalse(delivered)
        self.assertEqual([x['code'] for x in issues], ['COM'])

    def test_required_stage_cannot_be_not_applicable(self):
        report = {'stages': {s: {'status': 'pass'} for s in e.h.STAGES}, 'dependencies': {'fixture': 'hash'}}
        report['stages']['hancom'] = {'status': 'not_applicable', 'reason': 'synthetic bypass'}
        with patch.object(e, 'read', return_value=report), patch.object(e.h, 'freshness', return_value=[]), patch.object(e.h, 'result_state', return_value='pass'):
            verified, _, issues = e.runner_diagnostics(self.ref, self.base)
        self.assertFalse(verified)
        self.assertEqual(issues[0]['code'], 'COM')

    def test_suite_has_exactly_five_distinct_prompts(self):
        cases = self.suite['cases']
        self.assertEqual(len(cases), 5)
        self.assertEqual(len({x['id'] for x in cases}), 5)
        for case in cases:
            self.assertTrue((e.HERE / case['prompt']).is_file())
            e.definitions(case, self.rubric)

    def test_all_pending_summary_stays_zero(self):
        rows = [e.grade(e.init_record(c, self.suite, self.rubric), c, self.suite, self.rubric, self.base)
                for c in self.suite['cases']]
        summary = e.summarize(rows)
        self.assertEqual(summary['planned'], 5)
        for key in ('work_runs_started', 'checkpoint_passed', 'documents_verified', 'documents_delivered', 'documents_human_accepted'):
            self.assertEqual(summary[key], 0)

    def test_verified_copy_requires_both_matching_files(self):
        local, remote_dir = self.base / 'local.hwpx', self.base / 'remote'
        remote_dir.mkdir()
        local.write_bytes(b'synthetic-document')
        remote = remote_dir / local.name
        remote.write_bytes(local.read_bytes())
        report = {'stages': {s: {'status': 'pass'} for s in e.h.STAGES}, 'dependencies': {'fixture': 'hash'},
                  'validated_sha256': e.digest(local), 'delivery': {'local': str(local), 'sent': False},
                  'copy': {'status': 'pass', 'directory': str(remote_dir)}}
        with patch.object(e, 'read', return_value=report), patch.object(e.h, 'freshness', return_value=[]), patch.object(e.h, 'result_state', return_value='pass'):
            verified, delivered, _ = e.runner_diagnostics(self.ref, self.base)
            self.assertTrue(verified)
            self.assertTrue(delivered)
            remote.write_bytes(b'changed')
            verified, delivered, issues = e.runner_diagnostics(self.ref, self.base)
            self.assertTrue(verified)
            self.assertFalse(delivered)
            self.assertEqual(issues[0]['code'], 'DELIVERY')

    def test_changed_runner_dependencies_invalidates_document(self):
        report = {'stages': {s: {'status': 'pass'} for s in e.h.STAGES}, 'dependencies': {'fixture': 'hash'}}
        with patch.object(e, 'read', return_value=report), patch.object(e.h, 'freshness', return_value=['changed-source']), patch.object(e.h, 'result_state', return_value='unconfirmed'):
            verified, _, issues = e.runner_diagnostics(self.ref, self.base)
        self.assertFalse(verified)
        self.assertEqual(issues[0]['code'], 'STALE_ARTIFACT')

    def test_acceptance_needs_review_and_delivery(self):
        self.simulated_checkpoint()
        with patch.object(e, 'runner_diagnostics', return_value=(True, True, [])):
            self.assertFalse(self.grade()['accepted_document'])
            self.record['human_review'] = {'approved': True, 'score': 5, 'evidence': self.ref}
            self.assertTrue(self.grade()['accepted_document'])
            self.record['human_review']['approved'] = False
            self.assertFalse(self.grade()['accepted_document'])


if __name__ == '__main__':
    unittest.main()
