"""Python-free launcher tests. Network/unsafe execution are replaced, not bypassed."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DownloadManifest(unittest.TestCase):
    def test_pinned_official_metadata(self):
        rows = [r.split('\t') for r in (ROOT / 'distribution/runtime-downloads.tsv').read_text().splitlines() if not r.startswith('#')]
        self.assertEqual(len(rows), 6)
        for target, url, digest in rows:
            self.assertTrue(url.startswith('https://github.com/astral-sh/uv/releases/download/0.12.22/uv-' + target))
            self.assertRegex(digest, r'^[a-f0-9]{64}$')
        data = json.loads((ROOT / 'distribution/python-downloads.json').read_text())
        self.assertEqual(len(data), 6)
        for key, value in data.items():
            self.assertTrue(key.startswith('cpython-3.12.15-'))
            self.assertTrue(value['url'].startswith('https://github.com/astral-sh/python-build-standalone/releases/download/20261001/'))
            self.assertRegex(value['sha256'], r'^[a-f0-9]{64}$')


@unittest.skipIf(os.name == 'nt', 'Unix entry point; Windows uses its own real no-Python CI')
class ShellEntryPoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='teacher bootstrap 한글 ')
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        for name in ['bash', 'dirname', 'awk', 'uname', 'cat', 'mkdir', 'mktemp', 'sha256sum', 'tar', 'rm', 'gzip', 'env']:
            path = shutil.which(name)
            if path:
                (self.bin / name).symlink_to(path)
        self.env = dict(os.environ, PATH=str(self.bin), HOME=str(self.base / 'home'), HWPDOC_PC_DATA='')
        self.work = self.base / '교사 작업'
        self.data = self.base / 'PC 데이터'
        self.args = ['/bin/bash', str(ROOT / 'scripts/bootstrap.sh'), '--workspace', str(self.work), '--data-dir', str(self.data)]

    def tearDown(self):
        self.tmp.cleanup()

    def run_entry(self, *extra):
        return subprocess.run([*self.args, *extra], env=self.env, capture_output=True, text=True, timeout=60)

    def fake_curl(self, body):
        target = self.bin / 'curl'
        target.write_text('#!/bin/bash\n' + body)
        target.chmod(0o755)

    def test_consent_required_without_files_or_network(self):
        self.fake_curl('exit 99\n')
        result = self.run_entry()
        self.assertEqual(result.returncode, 2)
        self.assertIn('PYTHON_INSTALL_CONSENT_REQUIRED', result.stderr)
        self.assertFalse(self.data.exists())
        self.assertFalse(self.work.exists())

    def test_download_hash_mismatch_never_extracts(self):
        self.fake_curl('while (($#)); do if [[ $1 == --output ]]; then printf "not an archive" > "$2"; exit 0; fi; shift; done\nexit 99\n')
        result = self.run_entry('--allow-python-install')
        self.assertEqual(result.returncode, 2)
        self.assertIn('UV_HASH_MISMATCH', result.stderr)
        self.assertFalse((self.data / 'runtime.json').exists())
        self.assertFalse((self.data / 'managed-python/python').exists())
        self.assertEqual(list((self.data / 'managed-python').glob('download-*')), [])
        # Retrying remains fail-closed and does not remove unrelated files.
        sentinel = self.data / 'keep.txt'
        sentinel.write_text('user')
        self.assertEqual(self.run_entry('--allow-python-install').returncode, 2)
        self.assertEqual(sentinel.read_text(), 'user')

    def test_network_failure_preserves_existing_data(self):
        self.data.mkdir()
        (self.data / 'keep.txt').write_text('user')
        self.fake_curl('printf "network denied fixture\\n" >&2; exit 7\n')
        result = self.run_entry('--allow-python-install')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('network denied fixture', result.stderr)
        self.assertFalse((self.data / 'runtime.json').exists())
        self.assertEqual((self.data / 'keep.txt').read_text(), 'user')

    def test_existing_config_without_python_is_not_replaced(self):
        self.data.mkdir()
        config = self.data / 'runtime.json'
        config.write_text('{"version":1,"python":"/missing/user/python"}')
        before = config.read_bytes()
        result = self.run_entry('--allow-python-install')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Existing runtime.json preserved', result.stderr)
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse((self.data / 'managed-python').exists())

    def test_foreign_managed_folder_is_preserved(self):
        managed = self.data / 'managed-python'
        managed.mkdir(parents=True)
        (managed / 'keep').write_text('user')
        result = self.run_entry('--allow-python-install')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Existing unmanaged', result.stderr)
        self.assertEqual((managed / 'keep').read_text(), 'user')

    def test_managed_symlink_does_not_write_outside_data(self):
        foreign = self.base / 'foreign'
        foreign.mkdir()
        (foreign / '.teacher-doc-owner').write_text('teacher-doc-python-v1')
        self.data.mkdir()
        (self.data / 'managed-python').symlink_to(foreign, target_is_directory=True)
        result = self.run_entry('--allow-python-install')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Symlink', result.stderr)
        self.assertEqual(sorted(p.name for p in foreign.iterdir()), ['.teacher-doc-owner'])

    def test_code_overlap_fails_before_download(self):
        self.args[-1] = str(ROOT / 'forbidden-data')
        result = self.run_entry('--allow-python-install')
        self.assertEqual(result.returncode, 2)
        self.assertIn('must not overlap', result.stderr)
        self.assertFalse((ROOT / 'forbidden-data').exists())

    def test_explicit_wrong_python_does_not_trigger_download(self):
        result = self.run_entry('--allow-python-install', '--python', '/missing/python')
        self.assertEqual(result.returncode, 2)
        self.assertIn('absolute Python 3.12', result.stderr)
        self.assertFalse(self.data.exists())


if __name__ == '__main__':
    unittest.main()
