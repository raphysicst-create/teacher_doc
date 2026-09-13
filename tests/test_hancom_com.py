"""COM lifecycle and fail-fast tests; actual Hancom acceptance is recorded separately."""
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.claude/skills/hwpx/scripts'))
sys.path.insert(0, str(ROOT / 'scripts'))
import hancom_com as com
import hwpdoc


class HancomTests(unittest.TestCase):
    def setUp(self):
        self.token = MagicMock()
        self.api = SimpleNamespace(GetCurrentProcess=lambda: 1, GetCurrentThreadId=lambda: 2, GetUserName=lambda: 'test-user')
        self.security = SimpleNamespace(TOKEN_QUERY=8, OpenProcessToken=lambda *a: self.token, IsTokenRestricted=lambda t: False)
        self.service = SimpleNamespace(GetThreadDesktop=lambda t: 1, GetUserObjectInformation=lambda *a: 'Default')
        self.registry = MagicMock()
        self.registry.QueryValueEx.return_value = (str(Path(__file__).resolve()), 1)
        self.client = MagicMock()
        self.app = self.client.DispatchEx.return_value
        self.app.RegisterModule.return_value = True
        self.modules = patch.dict(sys.modules, {'win32api': self.api, 'win32security': self.security,
            'win32service': self.service, 'winreg': self.registry, 'win32com': SimpleNamespace(client=self.client),
            'win32com.client': self.client})
        self.modules.start(); self.addCleanup(self.modules.stop)
        p = patch.object(com, 'os', SimpleNamespace(name='nt'))
        p.start(); self.addCleanup(p.stop)

    def test_restricted_token_stops_before_com_and_closes_token(self):
        self.security.IsTokenRestricted = lambda t: True
        with self.assertRaisesRegex(RuntimeError, 'HANCOM_RESTRICTED_CONTEXT'):
            with com.session():
                self.fail('restricted context yielded COM')
        self.client.DispatchEx.assert_not_called()
        self.token.Close.assert_called_once()

    def test_private_desktop_stops_before_com(self):
        self.service.GetUserObjectInformation = lambda *a: 'CodexSandboxDesktop-test'
        with self.assertRaisesRegex(RuntimeError, 'HANCOM_RESTRICTED_CONTEXT'):
            com.preflight()
        self.client.DispatchEx.assert_not_called()

    def test_missing_module_stops_before_com(self):
        self.registry.OpenKey.side_effect = FileNotFoundError('missing')
        with self.assertRaisesRegex(RuntimeError, 'HANCOM_MODULE_MISSING'):
            with com.session():
                self.fail('missing module yielded COM')
        self.client.DispatchEx.assert_not_called()

    def test_missing_dll_stops_before_com(self):
        self.registry.QueryValueEx.return_value = (str(ROOT / 'tmp/nonexistent-module-test.dll'), 1)
        with self.assertRaisesRegex(RuntimeError, 'HANCOM_MODULE_MISSING'):
            com.preflight()

    def test_module_rejection_never_opens_and_quits_owned_instance(self):
        self.app.RegisterModule.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'HANCOM_MODULE_REJECTED'):
            with com.session() as (app, _):
                app.Open('must-not-open')
        self.app.Open.assert_not_called()
        self.app.Quit.assert_called_once()
        self.client.Dispatch.assert_not_called()

    def test_body_failure_still_quits(self):
        with self.assertRaisesRegex(RuntimeError, 'open failed'):
            with com.session():
                raise RuntimeError('open failed')
        self.app.Quit.assert_called_once()

    def test_quit_failure_does_not_report_success(self):
        self.app.Quit.side_effect = RuntimeError('quit failed')
        with self.assertRaisesRegex(RuntimeError, 'quit failed'):
            with com.session():
                pass

    def test_success_owns_new_instance(self):
        with com.session() as (app, context):
            self.assertIs(app, self.app)
            self.assertFalse(context['restricted'])
        self.client.DispatchEx.assert_called_once_with('HWPFrame.HwpObject')
        self.app.Quit.assert_called_once()

    def test_timeout_keeps_partial_diagnostics_bytes_and_text(self):
        for stdout in (b'Dispatch-start', 'Dispatch-start'):
            with patch.object(hwpdoc.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['probe'], 1, output=stdout, stderr=b'detail')):
                code, detail = hwpdoc.run(['probe'])
            self.assertEqual(code, 124)
            self.assertIn('Dispatch-startdetail', detail)
            self.assertIn('시간 초과', detail)


if __name__ == '__main__':
    unittest.main()
