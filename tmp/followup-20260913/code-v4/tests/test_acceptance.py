import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from hwpdoc_acceptance import new_matrix, summary, record


class AcceptanceTests(unittest.TestCase):
    def test_empty_matrix_never_counts_as_pass(self):
        s = summary(new_matrix())
        self.assertEqual(s['total'], 36); self.assertEqual(s['passed'], 0)
        self.assertFalse(s['complete'])

    def test_claim_without_evidence_rejected(self):
        with self.assertRaises(ValueError):
            record(new_matrix(), dict(environment='codex_sol_high', case='general_notice', repeat=1, status='pass'))

    def test_different_inputs_not_comparable(self):
        m = new_matrix(); m['runs'][0]['input_sha256'] = 'a'
        with self.assertRaisesRegex(ValueError, 'identical input'):
            record(m, dict(environment='codex_sol_high', case='general_notice', repeat=1, input_sha256='b'))


if __name__ == '__main__': unittest.main()
