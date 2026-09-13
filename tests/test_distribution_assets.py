"""Release candidate data must not retain original author or example facts."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / '.claude/skills/hwpx/scripts'))
import prepare_distribution_assets as assets
import build_distribution as packaging
from page_guard import _xml_structure_hash


class AssetTests(unittest.TestCase):
    def test_redacted_proposal_preserves_structure_and_replaces_example_facts(self):
        original = (assets.SOURCE / 'proposal/section0.xml').read_bytes()
        candidate = assets.proposal_candidate(original)
        self.assertEqual(_xml_structure_hash(original), _xml_structure_hash(candidate))
        for residue in ('서울특별시교육청', '7,354,948', '2021.', '교육혁신과-14927'):
            self.assertNotIn(residue.encode(), candidate)
        self.assertIn('{{사업기간}}'.encode(), candidate)

    def test_redacted_metadata_has_no_original_author_or_dates(self):
        original = (assets.SOURCE / 'base/Contents/content.hpf').read_bytes()
        candidate = assets.metadata_candidate(original)
        self.assertNotIn(b'kokyu', candidate)
        self.assertNotIn(b'2025-09-17', candidate)
        self.assertIn(b'Contents/header.xml', candidate)

    def test_failed_copy_leaves_no_installable_target(self):
        scratch = REPO / '.claude/scratchpad/release-tests'; scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as name:
            root = Path(name); (root / 'code.py').write_text('print(1)')
            manifest = {'version': 1, 'files': [{'source': 'code.py', 'destination': 'scripts/code.py'}]}
            grant = {k: 'SYNTHETIC TEST RECORD' for k in ('license', 'source', 'permission_record', 'reviewed_by', 'reviewed_at', 'privacy_review')}
            grant.update(sha256=packaging.digest(root / 'code.py'), privacy_sha256=packaging.digest(root / 'code.py'))
            output = root / 'release/teacher_doc'
            with patch.object(packaging, 'ROOT', root), patch.object(packaging.shutil, 'copy2', side_effect=OSError('synthetic copy failure')):
                with self.assertRaises(OSError): packaging.build(manifest, {'files': {'code.py': grant}}, output)
            self.assertFalse(output.exists())

    def test_populated_metadata_is_blocked_even_with_review_record(self):
        scratch = REPO / '.claude/scratchpad/release-tests'; scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as name:
            root = Path(name); source = root / 'content.hpf'
            source.write_text('<package xmlns="urn:opf"><meta name="creator">Example person</meta></package>')
            manifest = {'version': 1, 'files': [{'source': 'content.hpf', 'destination': 'content.hpf'}]}
            grant = {k: 'SYNTHETIC TEST RECORD' for k in ('license', 'source', 'permission_record', 'reviewed_by', 'reviewed_at', 'privacy_review')}
            grant.update(sha256=packaging.digest(source), privacy_sha256=packaging.digest(source))
            with patch.object(packaging, 'ROOT', root):
                reasons = [issue['reason'] for issue in packaging.check_release(manifest, {'files': {'content.hpf': grant}})['issues']]
            self.assertEqual(['document_identity_metadata'], reasons)


if __name__ == '__main__': unittest.main()
