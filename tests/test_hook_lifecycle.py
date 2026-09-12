"""Real Python hook processes with synthetic events, isolated project copies."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HookLifecycleTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / '.claude/scratchpad/tests'; folder.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=folder); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        dest = self.root / '.claude/hooks'; dest.mkdir(parents=True)
        for name in ('audit_log.py', 'event_adapter.py', 'protect_files.py', 'stop_validator.py'):
            shutil.copy2(ROOT / '.claude/hooks' / name, dest / name)
        (self.root / 'scripts').mkdir()

    def call(self, hook, data):
        return subprocess.run([sys.executable, '-X', 'utf8', str(self.root / '.claude/hooks' / hook)],
                              input=json.dumps(data), capture_output=True, text=True, encoding='utf-8')

    def test_post_failed_response_and_all_paths(self):
        event = dict(cwd=str(self.root), hook_event_name='PostToolUse', tool_name='apply_patch', tool_use_id='synthetic',
                     tool_input={'command': '*** Begin Patch\n*** Add File: output/a\n+a\n*** Add File: output/b\n+b\n*** End Patch'},
                     tool_response={'isError': True})
        r = self.call('audit_log.py', event)
        self.assertEqual(r.returncode, 0); self.assertEqual(json.loads(r.stdout), {})
        entry = json.loads((self.root / 'logs/audit.jsonl').read_text(encoding='utf-8').splitlines()[-1])
        self.assertEqual(entry['result'], 'fail'); self.assertEqual(len(entry['target']), 2)

    def test_registered_powershell_preserves_block_exit(self):
        original = self.root / 'knowledge/test.txt'; original.parent.mkdir(); original.write_text('UNCHANGED')
        command = json.loads((ROOT / '.codex/hooks.json').read_text(encoding='utf-8'))['hooks']['PreToolUse'][0]['hooks'][0]['command']
        event = dict(cwd=str(self.root), tool_name='apply_patch', tool_input={'command': '*** Begin Patch\n*** Delete File: knowledge/test.txt\n*** End Patch'})
        result = subprocess.run(command, input=json.dumps(event), capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertEqual(original.read_text(), 'UNCHANGED')

    def test_stop_two_blocks_then_report_and_json_success(self):
        validator = self.root / 'scripts/validate_pipeline.py'
        validator.write_text("print('synthetic fail'); raise SystemExit(1)", encoding='utf-8')
        event = dict(cwd=str(self.root / 'scripts'), session_id='test', hook_event_name='Stop', stop_hook_active=False)
        first = json.loads(self.call('stop_validator.py', event).stdout)
        event['stop_hook_active'] = True
        second = json.loads(self.call('stop_validator.py', event).stdout)
        third = json.loads(self.call('stop_validator.py', event).stdout)
        self.assertEqual(first['decision'], 'block'); self.assertEqual(second['decision'], 'block')
        self.assertNotIn('decision', third); self.assertIn('systemMessage', third)
        validator.write_text("raise SystemExit(0)", encoding='utf-8')
        self.assertEqual(json.loads(self.call('stop_validator.py', event).stdout), {})


if __name__ == '__main__': unittest.main()
