"""Interpreter/dependency transitions must invalidate only validation, not consent."""
from pathlib import Path
import copy
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import hwpdoc as h
import hwpdoc_runtime as runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        scratch = REPO / '.claude/scratchpad/runtime-tests'; scratch.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.manifest = self.root / 'manifest.json'
        h.write_json(self.manifest, {'draft_approval': {'record': 'SYNTHETIC FIXTURE'}})
        self.work = self.root / 'work.hwpx'; self.work.write_bytes(b'SYNTHETIC FIXTURE')
        self.runtime = {'python': 'fixture-python', 'version': '3.12.10', 'packages': {'lxml': '5.4.0'}}
        self.report = {'work_file': str(self.work), 'manifest_file': str(self.manifest), 'manifest_sha256': h.sha(self.manifest),
                       'dependencies': {}, 'tool_dependencies': {}, 'runtime': self.runtime,
                       'stages': {s: {'status': 'pass'} for s in h.STAGES}, 'validated_sha256': h.sha(self.work)}

    def test_dependency_version_change_requires_full_revalidation(self):
        changed = copy.deepcopy(self.runtime); changed['packages']['lxml'] = '6.0.0'
        approved = h.sha(self.manifest)
        with patch.object(h, 'runtime_snapshot', return_value=changed), patch.object(h, 'tool_dependencies', return_value={}):
            self.assertEqual(h.result_state(self.report), 'unconfirmed')
            self.assertIn('@runtime', h.freshness(self.report))
            h.refresh_validation_tools(self.report)
            self.assertNotIn('validated_sha256', self.report)
            self.assertEqual(self.report['runtime'], changed)
            self.assertTrue(self.report['runtime_updates'][0]['approval_preserved'])
            self.assertEqual(h.sha(self.manifest), approved)
            self.assertEqual(h.result_state(self.report), 'unconfirmed')

    def test_legacy_missing_runtime_is_not_assumed_current(self):
        self.report.pop('runtime')
        with patch.object(h, 'runtime_snapshot', return_value=self.runtime), patch.object(h, 'tool_dependencies', return_value={}):
            self.assertEqual(h.result_state(self.report), 'unconfirmed')
            h.refresh_validation_tools(self.report)
            self.assertIsNone(self.report['runtime_updates'][0]['before'])
            self.assertNotIn('validated_sha256', self.report)

    def test_runtime_refresh_does_not_accept_changed_manifest(self):
        self.manifest.write_text('{"changed":true}', encoding='utf-8')
        original = copy.deepcopy(self.report)
        with self.assertRaises(ValueError): h.refresh_validation_tools(self.report)
        self.assertEqual(original, self.report)

    def test_doctor_detects_wrong_version_and_broken_import(self):
        (self.root / 'distribution').mkdir()
        (self.root / 'distribution/requirements-base.txt').write_text('lxml==5.4.0\n', encoding='utf-8')
        with patch.object(runtime, 'PACKAGES', {'lxml': ('lxml', False)}), \
                patch.object(runtime, 'installed_version', return_value='6.0.0'), \
                patch.object(runtime.importlib, 'import_module'):
            result = runtime.diagnostics(self.root)['lxml']
            self.assertEqual(result['status'], 'fail')
            self.assertEqual(result['installed_version'], '6.0.0')
            self.assertEqual(result['expected_version'], '5.4.0')
        with patch.object(runtime, 'PACKAGES', {'lxml': ('lxml', False)}), \
                patch.object(runtime, 'installed_version', return_value='5.4.0'), \
                patch.object(runtime.importlib, 'import_module', side_effect=ImportError('broken binary')):
            result = runtime.diagnostics(self.root)['lxml']
            self.assertEqual(result['status'], 'fail')
            self.assertEqual(result['import_error'], 'broken binary')

    def test_recovery_only_offers_installed_fallback(self):
        skill = self.root / 'skills/hwpx/scripts'
        with patch.object(h, 'SKILL', skill):
            self.assertIn('이 설치에는 hwpx-fallback이 없습니다', h.structure_recovery())
            fallback = self.root / 'skills/hwpx-fallback/SKILL.md'
            fallback.parent.mkdir(parents=True)
            fallback.write_text('SYNTHETIC FIXTURE', encoding='utf-8')
            self.assertIn('hwpx-fallback F', h.structure_recovery())


if __name__ == '__main__': unittest.main()
