"""Render receipts must not excuse changed files, cells or unrelated paragraphs."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.claude/skills/hwpx/scripts'))
import page_guard as g

class ParagraphRenderTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / '.claude/scratchpad/tests'; scratch.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.ref = self.root / 'reference.hwpx'; self.out = self.root / 'output.hwpx'
        shutil.copy2(ROOT / 'knowledge/templates/성립전예산요구/양식.hwpx', self.ref)
        shutil.copy2(self.ref, self.out)
        for name in ('view.pdf', 'view.png'): (self.root / name).write_bytes(b'SYNTHETIC RECEIPT TEST')
        self.receipt = self.root / 'review.json'
        self.data = dict(confirmed=True, observer='SYNTHETIC', at='2026-09-13', record='Not real visual evidence', paragraphs=['p:7'],
                         reference_sha256=self.sha(self.ref), document_sha256=self.sha(self.out),
                         pdf={'path': 'view.pdf', 'sha256': self.sha(self.root / 'view.pdf')},
                         images=[{'path': 'view.png', 'sha256': self.sha(self.root / 'view.png')}])
        self.write()
    def sha(self, path): return hashlib.sha256(path.read_bytes()).hexdigest()
    def write(self): self.receipt.write_text(json.dumps(self.data), encoding='utf-8')
    def test_current_receipt_and_stale_artifact(self):
        self.assertEqual(g.paragraph_render_keys(self.receipt, self.ref, self.out), ('p:7',))
        (self.root / 'view.png').write_bytes(b'CHANGED')
        with self.assertRaises(ValueError): g.paragraph_render_keys(self.receipt, self.ref, self.out)
    def test_stale_document_and_reference(self):
        for key in ('document_sha256', 'reference_sha256'):
            old=self.data[key]; self.data[key]='STALE'; self.write()
            with self.assertRaises(ValueError): g.paragraph_render_keys(self.receipt, self.ref, self.out)
            self.data[key]=old
    def test_cell_or_missing_paragraph_not_accepted(self):
        for key in ('cell:0:1:1', 'p:999999'):
            self.data['paragraphs']=[key]; self.write()
            with self.assertRaises(ValueError): g.paragraph_render_keys(self.receipt, self.ref, self.out)
    def test_only_named_paragraph_budget_is_excused(self):
        slots=[dict(key=k, kind='cell' if k.startswith('cell') else 'paragraph', max_chars=5, text_len_nospace=5) for k in ('p:7','p:9','cell:0:0:0')]
        output=[dict(s, text_len_nospace=6) for s in slots]
        errors=g.compare_text_budget_profile({'slots':slots},{'slots':output},False,('p:7','cell:0:0:0'))
        self.assertEqual(len(errors),2)
        self.assertTrue(any('p:9' in error for error in errors))
        self.assertTrue(any('cell:0:0:0' in error for error in errors))

if __name__=='__main__': unittest.main()
