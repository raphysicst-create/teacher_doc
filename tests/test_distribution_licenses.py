"""Source/notice packaging regressions; fixtures are not release approvals."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_distribution as packaging


class LicenseBundleTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / '.claude/scratchpad/dev-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.patch = patch.object(packaging, 'ROOT', self.root)
        self.patch.start(); self.addCleanup(self.patch.stop)
        destinations = ['LICENSE', 'NOTICE.md', 'SOURCE.md', 'CHANGES.md',
                        'sources/python.tar.gz', 'sources/engine.tar.gz',
                        'distribution/requirements-visual.txt']
        self.entries = []
        for destination in destinations:
            path = self.root / destination
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('PyMuPDF==1.28.0\n' if destination.endswith('.txt') else 'SYNTHETIC fixture')
            self.entries.append({'source': destination, 'destination': destination, 'sha256': packaging.digest(path)})
        self.bundle = {
            'version': 1, 'plugin_version': '0.1.0', 'program_license': 'AGPL-3.0-only',
            'documents': self.entries[:4],
            'archives': [dict(self.entries[4], id='PyMuPDF==1.28.0'),
                         dict(self.entries[5], id='MuPDF==1.28.0')],
            'dependency_sources': {'PyMuPDF==1.28.0': ['PyMuPDF==1.28.0', 'MuPDF==1.28.0']},
        }
        self.manifest = {'version': 1, 'plugin_version': '0.1.0',
                         'dependency_reviews': ['PyMuPDF==1.28.0'], 'source_bundle': 'bundle.json'}
        self.save_bundle()

    def save_bundle(self):
        path = self.root / 'bundle.json'
        path.write_text(json.dumps(self.bundle), encoding='utf-8')
        self.entries = [item for item in self.entries if item['source'] != 'bundle.json']
        self.entries.append({'source': 'bundle.json', 'destination': 'SOURCE-BUNDLE.json', 'sha256': packaging.digest(path)})
        self.manifest['files'] = [{k: item[k] for k in ('source', 'destination')} for item in self.entries]

    def test_complete_source_delivery_is_packaged_with_notices(self):
        # Only these disposable fixtures receive synthetic grants.
        rights = {'files': {}, 'dependencies': {'PyMuPDF==1.28.0':
                  {k: 'SYNTHETIC' for k in ('license', 'source', 'conditions_review', 'reviewed_by')}}}
        rights['dependencies']['PyMuPDF==1.28.0']['source_bundle_sha256'] = packaging.digest(self.root / 'bundle.json')
        for item in self.entries:
            rights['files'][item['source']] = dict(
                sha256=item['sha256'], privacy_sha256=item['sha256'],
                **{k: 'SYNTHETIC' for k in ('license', 'source', 'permission_record', 'reviewed_by', 'reviewed_at', 'privacy_review')})
        output = self.root / 'release/teacher_doc'
        self.assertEqual(packaging.build(self.manifest, rights, output)['status'], 'packaged')
        for item in self.entries:
            self.assertEqual(packaging.digest(output / item['destination']), item['sha256'])
        rights['dependencies']['PyMuPDF==1.28.0']['source_bundle_sha256'] = 'OLD'
        reasons = [item['reason'] for item in packaging.check_release(self.manifest, rights)['issues']]
        self.assertIn('dependency_source_review_stale', reasons)

    def test_removing_bundle_declaration_does_not_disable_gate(self):
        del self.manifest['source_bundle']
        self.assertEqual(packaging.check_source_bundle(self.manifest, self.entries)[0]['reason'], 'source_bundle_missing')

    def test_omitted_notice_or_engine_source_blocks(self):
        for destination in ('LICENSE', 'NOTICE.md', 'sources/engine.tar.gz'):
            with self.subTest(destination=destination):
                entries = [entry for entry in self.entries if entry['destination'] != destination]
                self.assertTrue(packaging.check_source_bundle(self.manifest, entries))

    def test_changed_archive_blocks_even_if_new_rights_hash_is_supplied(self):
        entries = copy.deepcopy(self.entries)
        entries[4]['sha256'] = 'new-file-hash'
        self.assertEqual(packaging.check_source_bundle(self.manifest, entries)[0]['reason'], 'source_bundle_file_missing_or_changed')

    def test_dependency_upgrade_requires_matching_source(self):
        self.manifest['dependency_reviews'] = ['PyMuPDF==1.29.0']
        reasons = [issue['reason'] for issue in packaging.check_source_bundle(self.manifest, self.entries)]
        self.assertIn('corresponding_source_version_missing', reasons)
        self.assertIn('source_requirements_version_mismatch', reasons)

    def test_release_version_change_requires_updated_notice_bundle(self):
        self.manifest['plugin_version'] = '0.2.0'
        self.assertEqual(packaging.check_source_bundle(self.manifest, self.entries)[0]['reason'], 'source_bundle_invalid')

    def test_missing_notice_in_lock_cannot_hide_omission(self):
        self.bundle['documents'] = self.bundle['documents'][1:]
        self.save_bundle()
        self.assertEqual(packaging.check_source_bundle(self.manifest, self.entries)[0]['reason'], 'source_bundle_invalid')

    def test_binary_cannot_be_added_to_source_only_policy(self):
        self.entries.append({'source': 'module.pyd', 'destination': 'module.pyd', 'sha256': 'fixture'})
        self.assertEqual(packaging.check_source_bundle(self.manifest, self.entries)[0]['reason'], 'binary_bundle_requires_separate_source_review')


if __name__ == '__main__':
    unittest.main()
