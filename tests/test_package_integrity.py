"""Shipped bytes and version identities must match the published inventories."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackageIntegrity(unittest.TestCase):
    def test_inventory_and_source_bundle(self):
        inventory = json.loads((ROOT / 'release-inventory.json').read_text(encoding='utf-8'))
        destinations = [entry['destination'] for entry in inventory['files']]
        self.assertEqual(len(destinations), len(set(destinations)))
        for entry in inventory['files']:
            self.assertEqual(hashlib.sha256((ROOT / entry['destination']).read_bytes()).hexdigest(), entry['sha256'], entry['destination'])
        bundle = json.loads((ROOT / 'SOURCE-BUNDLE.json').read_text(encoding='utf-8'))
        for entry in bundle['documents'] + bundle['archives']:
            path = ROOT / entry['destination']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['sha256'], str(path))
        for manifest in ('.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
            self.assertEqual(json.loads((ROOT / manifest).read_text(encoding='utf-8'))['version'], bundle['plugin_version'])
        for required in ('tests/test_beginner_workflow.py', 'scripts/runtime.ps1', 'skills/hwpx/references/resume.md'):
            self.assertIn(required, destinations)


if __name__ == '__main__':
    unittest.main()
