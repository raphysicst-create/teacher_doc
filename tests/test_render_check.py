"""Regression: a circle already rendered by the reference is not newly introduced."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_check as rc


class RenderResidueTests(unittest.TestCase):
    def test_no_reference_preserves_failure(self):
        self.assertIn('◯', rc.check_object_residue('본문', '본문◯')['unexpected'])

    def test_reference_circle_is_warning_candidate(self):
        result = rc.check_object_residue('본문', '본문◯◯', '이전본문◯◯')
        self.assertEqual(result['inherited']['◯'], {'output': 2, 'reference': 2})
        self.assertFalse(result['unexpected'])

    def test_increased_circle_still_fails(self):
        self.assertIn('◯', rc.check_object_residue('본문', '본문◯◯', '이전◯')['unexpected'])

    def test_new_character_not_hidden_by_other_baseline_character(self):
        result = rc.check_object_residue('본문', '본문◯①', '이전◯◯')
        self.assertIn('①', result['unexpected'])
        self.assertIn('◯', result['inherited'])

    def test_intentional_logical_character(self):
        self.assertFalse(rc.check_object_residue('본문①', '본문①')['unexpected'])

    def run_cli(self, reference_text, reference_pages=1):
        scratch = ROOT / 'tmp'; scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            out = Path(folder) / 'out.hwpx'; out.write_bytes(b'synthetic')
            ref = Path(folder) / 'ref.hwp'; ref.write_bytes(b'synthetic')
            pdf = Path(folder) / 'out.pdf'
            lines = ['충분히긴고유문단번호' + str(i) for i in range(20)]
            stream = io.StringIO()
            with patch.object(sys, 'argv', ['render_check', str(out), '--reference', str(ref), '--keep-pdf', str(pdf), '--json']), \
                 patch.object(rc, 'hancom_pages_and_pdf', side_effect=[1, reference_pages]) as com, \
                 patch.object(rc, 'extract_pdf_text', side_effect=[reference_text, ''.join(lines) + '◯']), \
                 patch.object(rc, 'extract_logical_lines', return_value=lines), \
                 contextlib.redirect_stdout(stream):
                result = rc.main()
            self.assertNotEqual(com.call_args_list[1].args[1], pdf)
            self.assertEqual(out.read_bytes(), b'synthetic')
            self.assertEqual(ref.read_bytes(), b'synthetic')
            return result, stream.getvalue()

    def test_cli_inherited_circle_passes_with_explicit_warning(self):
        result, output = self.run_cli('원본문장' * 30 + '◯')
        report = json.loads(output)
        self.assertEqual(result, 0)
        self.assertTrue(report['warnings'])
        self.assertEqual(report['result'], 'PASS')

    def test_reference_extraction_failure_is_not_pass(self):
        result, output = self.run_cli('◯')
        self.assertEqual(result, 3)
        self.assertIn('원본 대조 불가', output)

    def test_page_failure_not_suppressed_by_inherited_circle(self):
        result, output = self.run_cli('원본문장' * 30 + '◯', reference_pages=2)
        self.assertEqual(result, 1)
        self.assertIn('쪽수 불일치', json.loads(output)['fails'][0])


if __name__ == '__main__':
    unittest.main()
