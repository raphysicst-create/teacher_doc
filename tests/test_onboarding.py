"""Cross-platform local onboarding checks (no Hancom, Codex login, or real data)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]


class Onboarding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='teacher-doc-qc-')
        cls.root = Path(cls.temp.name)
        cls.home = cls.root / 'clean home 한글'
        cls.home.mkdir()
        cls.workspace = cls.root / '교사 작업'
        cls.data = cls.root / 'PC 데이터'
        cls.env = dict(os.environ, HOME=str(cls.home), USERPROFILE=str(cls.home),
                       CODEX_HOME=str(cls.home / '.codex'), LOCALAPPDATA=str(cls.home / 'AppData/Local'),
                       HWPDOC_PC_DATA=str(cls.data), HWPDOC_WORKSPACE=str(cls.workspace),
                       PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
        cls.args = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/bootstrap.py'),
                    '--workspace', str(cls.workspace), '--data-dir', str(cls.data)]
        result = cls.run_process(cls.args)
        if result.returncode:
            raise AssertionError(result.stderr + result.stdout)
        cls.result = json.loads(result.stdout)
        cls.python = cls.result['python']
        cls.cli = [cls.python, '-B', '-X', 'utf8', str(ROOT / 'scripts/teacher_doc.py'),
                   '--workspace', str(cls.workspace)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def run_process(cls, args, env=None):
        return subprocess.run([str(a) for a in args], env=env or cls.env, cwd=cls.home,
                              capture_output=True, text=True, encoding='utf-8', timeout=600)

    def test_00_pip_target_cannot_escape_venv(self):
        # Existing user pip configuration must never redirect this installation.
        target = self.root / 'forbidden external pip target'
        data = self.root / 'isolated pip data'
        work = self.root / 'isolated pip workspace'
        config = self.root / 'user pip.ini'
        config.write_text('[global]\ntarget = ' + str(target) + '\n', encoding='utf-8')
        env = dict(self.env, PIP_TARGET=str(target), PIP_CONFIG_FILE=str(config), PIP_USER='1')
        args = [sys.executable, '-B', '-X', 'utf8', ROOT / 'scripts/bootstrap.py',
                '--workspace', work, '--data-dir', data]
        result = self.run_process(args, env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(target.exists())
        self.assertTrue(Path(json.loads(result.stdout)['python']).resolve().is_relative_to(data.resolve()))

    def test_01_first_document(self):
        self.assertEqual(self.result['status'], 'ready_xml')
        self.assertEqual(self.result['practice']['status'], 'xml_pass')
        self.assertFalse(self.result['practice']['human_approval'])
        self.assertEqual(self.result['practice']['checks']['hancom_open'], 'not_run')
        folder = self.workspace / 'output/teacher-doc-practice'
        for name, digest in self.result['practice']['files'].items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest)

    def test_02_repeat_preserves_user_files(self):
        sentinel = self.workspace / 'knowledge/keep me.txt'
        sentinel.write_text('사용자 원문', encoding='utf-8')
        before = (self.workspace / '.hwpdoc/workspace.json').read_bytes()
        result = self.run_process(self.args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['practice']['reused'])
        self.assertEqual(before, (self.workspace / '.hwpdoc/workspace.json').read_bytes())
        self.assertEqual(sentinel.read_text(encoding='utf-8'), '사용자 원문')

    def test_03_child_stays_in_venv(self):
        code = (f'import sys;sys.path.insert(0,{str(ROOT / "scripts")!r});import hwpdoc;'
                'hwpdoc.configure();'
                'code,out=hwpdoc.run(["-c", "import sys,lxml.etree; print(sys.executable); print(lxml.etree.LXML_VERSION)"]);'
                'print(out);raise SystemExit(code)')
        result = self.run_process([self.python, '-B', '-X', 'utf8', '-c', code])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.python, result.stdout)
        self.assertIn('(5, 4, 0, 0)', result.stdout)

    def test_04_doctor_exit_codes(self):
        result = self.run_process([*self.cli, 'doctor', '--mode', 'xml'])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        if os.name != 'nt':
            result = self.run_process([*self.cli, 'doctor', '--mode', 'full'])
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['checks']['hancom']['status'], 'unconfirmed')
        # Missing dependencies and a different selected runtime must not exit 0.
        empty = self.root / 'empty venv'
        venv.EnvBuilder(with_pip=False).create(empty)
        python = empty / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        result = self.run_process([python, '-B', '-X', 'utf8', ROOT / 'scripts/teacher_doc.py',
                                   '--workspace', self.workspace, 'doctor', '--mode', 'xml'])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['status'], 'fail')
        self.assertEqual(data['checks']['lxml']['status'], 'fail')
        self.assertEqual(data['checks']['python']['status'], 'fail')

    def test_05_modified_practice_preserved(self):
        path = self.workspace / 'output/teacher-doc-practice/first-document.hwpx'
        original = path.read_bytes()
        try:
            path.write_bytes(b'user-modified')
            result = self.run_process([*self.cli, 'first-doc'])
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(path.read_bytes(), b'user-modified')
        finally:
            path.write_bytes(original)

    def test_06_existing_runtime_preserved(self):
        config = self.data / 'runtime.json'
        original = config.read_bytes()
        try:
            config.write_text('{"version":1,"python":"/missing/python"}', encoding='utf-8')
            result = self.run_process(self.args)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn('/missing/python', config.read_text(encoding='utf-8'))
            self.assertEqual(json.loads((self.workspace / '.hwpdoc/onboarding-attempt.json').read_text())['status'], 'failed')
            self.assertEqual(json.loads((self.workspace / '.hwpdoc/onboarding.json').read_text())['status'], 'ready_xml')
        finally:
            config.write_bytes(original)

    def test_07_corrupt_workspace_preserved(self):
        marker = self.workspace / '.hwpdoc/workspace.json'
        original = marker.read_bytes()
        try:
            marker.write_text('{"kind":"someone-else"}', encoding='utf-8')
            result = self.run_process(self.args)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(marker.read_text(), '{"kind":"someone-else"}')
        finally:
            marker.write_bytes(original)

    def test_08_no_workspace_in_plugin(self):
        result = self.run_process([sys.executable, ROOT / 'scripts/bootstrap.py',
                                   '--workspace', ROOT / 'output/unsafe', '--data-dir', self.data])
        self.assertEqual(result.returncode, 2)
        self.assertFalse((ROOT / 'output/unsafe').exists())

    def test_09_no_implicit_hooks(self):
        self.assertFalse((self.workspace / '.codex/hooks.json').exists())
        self.assertFalse((self.workspace / '.claude/settings.json').exists())

    def test_10_non_object_settings(self):
        config = self.data / 'runtime.json'
        original = config.read_bytes()
        try:
            for value in ('[]', '{"version":1,"python":[]}'):
                config.write_text(value, encoding='utf-8')
                result = self.run_process(self.args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stderr)['status'], 'failed')
                self.assertEqual(config.read_text(encoding='utf-8'), value)
        finally:
            config.write_bytes(original)

    def test_11_new_session_restores_recorded_runtime(self):
        env = {k: v for k, v in self.env.items() if k not in ('HWPDOC_PC_DATA', 'HWPDOC_WORKSPACE')}
        tracked = [self.workspace / '.hwpdoc/workspace.json', self.workspace / 'AGENTS.md',
                   *list((self.workspace / 'output/teacher-doc-practice').glob('*'))]
        before = {str(p): p.read_bytes() for p in tracked}
        result = self.run_process([*self.cli, 'doctor', '--mode', 'xml'], env)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        record = json.loads(result.stdout)
        self.assertEqual(record['pc_data'], str(self.data))
        self.assertEqual(record['checks']['python']['selected_path'], self.python)
        if os.name == 'nt':
            result = self.run_process(['powershell.exe', '-NoProfile', '-File', ROOT / 'scripts/teacher_doc.ps1',
                                       '--workspace', self.workspace, 'doctor', '--mode', 'xml'], env)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(json.loads(result.stdout)['checks']['python']['path'], self.python)
        self.assertEqual(before, {str(p): p.read_bytes() for p in tracked})

    def test_11_package_layout(self):
        catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        entry = next(e for e in catalog['plugins'] if e['name'] == 'teacher_doc')
        self.assertEqual(entry['source'], {'source': 'local', 'path': './'})
        self.assertEqual(entry['policy']['installation'], 'AVAILABLE')
        self.assertTrue((ROOT / 'skills/teacher-doc-setup/SKILL.md').is_file())


if __name__ == '__main__':
    unittest.main()
