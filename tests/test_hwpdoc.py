"""Runner contract tests. Synthetic approval is test data, never an acceptance result."""
from pathlib import Path
import copy
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import hwpdoc as h


class RunnerTests(unittest.TestCase):
    def setUp(self):
        scratch = REPO / '.claude/scratchpad/tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.tmp.name)
        self.root_patch = patch.object(h, 'ROOT', self.root)
        self.jobs_patch = patch.object(h, 'JOBS', self.root / '.hwpdoc/jobs')
        self.root_patch.start(); self.jobs_patch.start()
        self.addCleanup(self.tmp.cleanup); self.addCleanup(self.root_patch.stop); self.addCleanup(self.jobs_patch.stop)
        self.draft = self.root / 'draft.md'; self.draft.write_text('software test only', encoding='utf-8')
        self.source = self.root / 'input.hwpx'
        shutil.copy2(REPO / 'knowledge/templates/가정통신문/양식.hwpx', self.source)
        h.write_json(self.root / 'evidence.json', dict(status='ok', steps=['find_tasks', 'get_task_guide', 'search_task_evidence', 'read_evidence'],
                     conditions=[], exceptions=[], pending_items=[], reviewed_at='2026-09-10T01:00:00+00:00', freshness='verified'))
        self.m = dict(job_id='test', workflow='W1', document_type='software-test', shared_values={}, sources=[{'path': str(self.source)}],
                      evidence={'record': str(self.root / 'evidence.json')}, attachments=[], attachment_mentions=[],
                      draft={'path': str(self.draft), 'sha256': h.sha(self.draft), 'created_at': '2026-09-10T02:00:00+00:00'},
                      content_rules={'forbid': ['SYNTHETIC_OLD_TOKEN']}, checks={x: {'applicable': False, 'reason': 'software fixture'} for x in ('budget_names', 'related', 'timetable')},
                      environment={'app': 'unit-test', 'model': 'none'}, unresolved=[], source=str(self.source), reference=str(self.source),
                      exploration={'record': 'software fixture'}, reuse_review={'record': 'software fixture', 'names': ['SYNTHETIC_OLD_TOKEN'], 'dates': [], 'dates_empty_reason': 'software fixture'}, base_provenance='native',
                      expected_values=['화동중학교'])
        self.approve()

    def approve(self):
        self.m['draft_approval'] = dict(confirmed=True, by='SYNTHETIC_TEST_NOT_USER', at='2026-09-10T03:00:00+00:00',
                                       record='unit test fixture', input_sha256=h.json_hash(h.approval_payload(self.m)))
        self.manifest = self.root / 'manifest.json'; h.write_json(self.manifest, self.m)

    def report(self):
        return h.initialize(self.manifest, build=False)[1]

    def test_missing_approval_is_not_generated(self):
        self.m['draft_approval']['confirmed'] = False
        self.assertTrue(any('확인 기록' in x for x in h.prerequisite_errors(self.m)))

    def test_reviewed_unknown_origin_requires_real_render_and_preserves_origin(self):
        for render_exit in (0, 1):
            with self.subTest(render_exit=render_exit):
                self.m['job_id'] = 'unknown-' + str(render_exit)
                self.m['base_provenance'] = 'unconfirmed'
                self.m['template'] = {'id': 'reviewed-fixture', 'version': '1', 'sha256': h.sha(self.source)}
                self.approve()
                with patch.object(h, 'template_file', return_value=self.source), \
                     patch('hwpdoc_templates.registration_dependencies', return_value=[self.source]):
                    r = self.report()
                    def run(argv, **kwargs):
                        return (render_exit, 'render fixture') if 'render_check.py' in str(argv[0]) else (0, 'PASS')
                    with patch.object(h, 'run', side_effect=run) as calls:
                        h.validate_document(r)
                    self.assertTrue(any('render_check.py' in str(c.args[0][0]) for c in calls.call_args_list))
                    self.assertEqual(r['stages']['render']['status'], 'pass' if render_exit == 0 else 'fail')
                    self.assertEqual(h.read_json(self.manifest)['base_provenance'], 'unconfirmed')

    def test_unknown_origin_without_reviewed_registration_stays_unconfirmed(self):
        self.m['base_provenance'] = 'unconfirmed'; self.approve()
        r = self.report()
        with patch.object(h, 'run', return_value=(0, 'PASS')):
            h.validate_document(r)
        self.assertEqual(r['stages']['render']['status'], 'unconfirmed')

    def test_consumed_paragraph_observation_artifacts_invalidate_status_when_changed(self):
        for name in ('proof.pdf', 'proof.png'):
            (self.root / name).write_bytes(b'SYNTHETIC OBSERVATION FIXTURE')
        receipt = self.root / 'paragraph-review.json'
        h.write_json(receipt, {'pdf': {'path': 'proof.pdf'}, 'images': [{'path': 'proof.png'}]})
        self.m['paragraph_visual_record'] = 'paragraph-review.json'; self.approve()
        r = self.report()
        # Successful external validation is simulated; this verifies receipt freshness tracking.
        with patch.object(h, 'run', return_value=(0, 'PASS')):
            h.validate_document(r)
        (self.root / 'proof.png').write_bytes(b'CHANGED')
        self.assertIn(str((self.root / 'proof.png').resolve()), h.freshness(r))

    def test_changed_approved_value_rejected(self):
        self.m['shared_values']['date'] = 'invented'
        self.assertTrue(any('input_sha256' in x for x in h.prerequisite_errors(self.m)))

    def test_w2_unknown_submission_stays_unknown(self):
        self.m['workflow'] = 'W2'; self.m['received'] = {}; self.approve()
        self.assertTrue(any('제출 방법 미확인' in x for x in h.prerequisite_errors(self.m)))

    def test_insufficient_activity_rows(self):
        self.m['template'] = '가정통신문-회신형'
        self.m['activities'] = [dict(location='일정표', items=['a', 'b'], slot_keys=['p:1'])]; self.approve()
        self.assertTrue(any('활동 행 부족' in x for x in h.prerequisite_errors(self.m, build=True)))

    def test_evidence_must_precede_draft(self):
        p = self.root / 'evidence.json'; e = h.read_json(p); e['reviewed_at'] = '2026-09-11T01:00:00+00:00'; h.write_json(p, e)
        self.assertTrue(any('초안 작성보다 늦' in x for x in h.prerequisite_errors(self.m)))

    def test_pending_evidence_never_passes(self):
        p = self.root / 'evidence.json'; e = h.read_json(p); e['pending_items'] = ['latest source unknown']; h.write_json(p, e)
        r = self.report(); r['stages'] = {s: {'status': 'pass'} for s in h.STAGES}; r['validated_sha256'] = h.sha(r['work_file'])
        self.assertEqual(h.result_state(r), 'unconfirmed')

    def test_hash_change_invalidates_all_passes(self):
        r = self.report(); r['stages'] = {s: {'status': 'pass'} for s in h.STAGES}; r['validated_sha256'] = h.sha(r['work_file'])
        self.assertEqual(h.result_state(r), 'pass')
        with Path(r['work_file']).open('ab') as f: f.write(b'changed')
        self.assertEqual(h.result_state(r), 'unconfirmed')
        with self.assertRaises(ValueError): h.delivery(r)

    def test_reference_change_invalidates(self):
        r = self.report(); self.source.write_bytes(b'changed')
        self.assertIn(str(self.source), h.freshness(r))

    def test_two_failures_stop_invocation(self):
        r = self.report()
        with patch.object(h, 'run', return_value=(1, 'FAIL')) as run:
            for _ in range(3): h.stage(r, 'structure', ['validator'])
            self.assertEqual(run.call_count, 2)
        self.assertEqual(r['stages']['structure']['failures'], 2)

    def test_timeout_is_unconfirmed(self):
        r = self.report()
        with patch.object(h, 'run', return_value=(124, 'timeout')):
            h.stage(r, 'hancom', ['validator'], com=True)
        self.assertEqual(r['stages']['hancom']['status'], 'unconfirmed')

    def test_visual_claim_without_files_stays_unconfirmed(self):
        self.m['over_budget_cells'] = ['p:3']
        self.m['visual_review'] = {'confirmed': True, 'document_sha256': h.sha(self.source)}
        self.approve(); r = self.report()
        with patch.object(h, 'run', return_value=(0, 'PASS')): h.validate_document(r)
        self.assertEqual(r['stages']['visual_review']['status'], 'unconfirmed')

    def test_visual_receipt_bound_to_file_and_artifacts(self):
        pdf = self.root / 'synthetic.pdf'; pdf.write_bytes(b'UNIT TEST ARTIFACT')
        png = self.root / 'synthetic.png'; png.write_bytes(b'UNIT TEST ARTIFACT')
        self.m['over_budget_cells'] = ['p:3']
        self.m['visual_review'] = dict(confirmed=True, by='SYNTHETIC_TEST', at='2026-09-10', record='not actual visual QA',
                                      document_sha256=h.sha(self.source), cells=['p:3'],
                                      pdf={'path': str(pdf), 'sha256': h.sha(pdf)}, images=[{'path': str(png), 'sha256': h.sha(png)}])
        self.approve(); r = self.report()
        with patch.object(h, 'run', return_value=(0, 'PASS')): h.validate_document(r)
        self.assertEqual(r['stages']['visual_review']['status'], 'pass')
        png.write_bytes(b'changed')
        self.assertEqual(h.result_state(r), 'unconfirmed')

    def test_validation_order_and_no_fast_hook(self):
        r = self.report()
        with patch.object(h, 'run', return_value=(0, 'PASS')) as run:
            h.validate_document(r)
        names = [x['stage'] for x in r['history']]
        self.assertEqual(names[:4], ['structure', 'namespaces', 'finalize', 'layout'])
        self.assertLess(names.index('reference_finalize'), names.index('reference_profiles'))
        self.assertLess(names.index('page_guard'), names.index('hancom'))
        self.assertLess(names.index('hancom'), names.index('content'))
        self.assertEqual(names[-1], 'compare')
        self.assertNotIn('validate_pipeline.py', str(run.call_args_list))
        self.assertNotIn('--allow-over-budget', str(run.call_args_list))

    def test_budget_cli_repeats_check_for_every_name(self):
        self.m['checks']['budget_names'] = {'applicable': True, 'names': ['A', 'B']}; self.approve(); r = self.report()
        with patch.object(h, 'run', return_value=(0, 'PASS')) as run: h.validate_document(r)
        args = next(x.args[0] for x in run.call_args_list if 'budget_name_check.py' in str(x))
        self.assertEqual(args[-4:], ['--check', 'A', '--check', 'B'])

    def test_copy_retry_does_not_revalidate(self):
        r = self.report()
        missing = self.root / 'onedrive'
        with patch.object(h, 'run', side_effect=AssertionError('must not validate')):
            h.delivery(r, draft=True, destination=missing)
            self.assertEqual(r['copy']['status'], 'fail')
            missing.mkdir()
            h.delivery(r, draft=True, destination=missing)
            self.assertEqual(r['copy']['status'], 'pass')
        self.assertFalse(r['delivery']['sent'])
        self.assertIn('미확인', r['delivery']['local'])

    def test_original_template_never_overwritten(self):
        before = h.sha(self.source); r = self.report()
        self.assertNotEqual(r['work_file'], str(self.source))
        Path(r['work_file']).write_bytes(b'edit')
        self.assertEqual(before, h.sha(self.source))

    def test_job_path_traversal(self):
        for value in ('../other', '..', 'C:\\other', 'a/b'):
            with self.subTest(value=value), self.assertRaises(ValueError): h.job_dir(value)


if __name__ == '__main__':
    unittest.main()
