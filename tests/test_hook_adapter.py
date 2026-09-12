"""Windows adapter regression: disposable files only, not host integration."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.claude/hooks'))
from event_adapter import evaluate, normalize_path, patch_targets


class AdapterTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / '.claude/scratchpad/tests'; scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / 'knowledge/original.txt'; self.original.parent.mkdir(); self.original.write_text('UNCHANGED', encoding='utf-8')
        self.before = hashlib.sha256(self.original.read_bytes()).hexdigest()

    def event(self, command):
        return {'cwd': str(self.root), 'tool_name': 'apply_patch', 'hook_event_name': 'PreToolUse', 'tool_input': {'command': command}}

    def check(self, patch_text, decision):
        self.assertEqual(evaluate(self.event('*** Begin Patch\n' + patch_text + '\n*** End Patch'))['decision'], decision)
        self.assertEqual(hashlib.sha256(self.original.read_bytes()).hexdigest(), self.before)

    def test_update(self): self.check('*** Update File: knowledge/original.txt\n@@\n-UNCHANGED\n+changed', 'deny')
    def test_delete(self): self.check('*** Delete File: knowledge/original.txt', 'deny')
    def test_move_source(self): self.check('*** Update File: knowledge/original.txt\n*** Move to: output/new.txt\n@@\n-UNCHANGED\n+changed', 'deny')
    def test_move_destination(self): self.check('*** Update File: output/new.txt\n*** Move to: knowledge/original.txt\n@@\n-old\n+new', 'deny')
    def test_mixed_patch(self): self.check('*** Add File: output/new.txt\n+new\n*** Delete File: knowledge/original.txt', 'deny')
    def test_multiple_allowed(self): self.check('*** Add File: output/a.txt\n+a\n*** Add File: output/b.txt\n+b', 'allow')
    def test_new_protected_file(self): self.check('*** Add File: knowledge/new.txt\n+new', 'allow')
    def test_add_cannot_overwrite(self): self.check('*** Add File: knowledge/original.txt\n+new', 'deny')
    def test_output_substring_no_bypass(self):
        p = self.root / 'knowledge/output/original.txt'; p.parent.mkdir(); p.write_text('x')
        self.check('*** Delete File: knowledge/output/original.txt', 'deny')
    def test_whitelist_md_only(self):
        p = self.root / 'knowledge/examples/md'; p.mkdir(parents=True)
        (p / 'a.md').write_text('x'); (p / 'a.hwpx').write_text('x')
        self.check('*** Delete File: knowledge/examples/md/a.md', 'allow')
        self.check('*** Delete File: knowledge/examples/md/a.hwpx', 'deny')
    def test_absolute_windows_case(self): self.check('*** Delete File: ' + str(self.original).upper(), 'deny')
    def test_relative_parent_segments(self): self.check('*** Delete File: output/../knowledge/original.txt', 'deny')
    def test_malformed(self):
        for p in ('garbage', '*** Begin Patch\n*** Unknown File: x\n*** End Patch', '*** Begin Patch\n*** Update File: x\n*** End Patch'):
            with self.subTest(p=p): self.assertEqual(evaluate(self.event(p))['decision'], 'deny')
    def test_missing_cwd(self):
        e = self.event('x'); del e['cwd']; self.assertEqual(evaluate(e)['decision'], 'deny')
    def test_drive_relative_and_ads(self):
        for p in ('C:original.txt', 'C:\\x.txt:stream', 'C:\\knowledge\\original.txt.'):
            with self.subTest(p=p), self.assertRaises(ValueError): normalize_path(p, str(self.root))
    def test_claude_input(self):
        e = {'cwd': str(self.root), 'tool_name': 'Write', 'tool_input': {'file_path': str(self.original)}}
        self.assertEqual(evaluate(e)['decision'], 'deny')
    def test_direct_powershell_python_and_mcp_classified(self):
        for command in ("Set-Content knowledge/original.txt changed", "python -c \"open('knowledge/original.txt','w').write('x')\""):
            e = {'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}
            self.assertEqual(evaluate(e)['decision'], 'deny')
        e = {'cwd': str(self.root), 'tool_name': 'mcp__kordoc__patch_document', 'tool_input': {'output_path': str(self.original)}}
        self.assertEqual(evaluate(e)['decision'], 'deny')
        e['tool_input'] = {'document_id': 'unknown'}
        self.assertEqual(evaluate(e)['decision'], 'deny')
    def test_mcp_read_source_new_output_allowed(self):
        e = {'cwd': str(self.root), 'tool_name': 'mcp__kordoc__patch_document',
             'tool_input': {'file_path': str(self.original), 'output_path': str(self.root / 'output/new.hwpx')}}
        self.assertEqual(evaluate(e)['decision'], 'allow')
    def test_non_object_input_denied(self):
        self.assertEqual(evaluate([])['decision'], 'deny')
    def test_dynamic_shell_explicitly_partial(self):
        e = {'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': 'python arbitrary.py'}}
        self.assertEqual(evaluate(e)['coverage'], 'partial')
    def copy_event(self, source, destination):
        return {'cwd': str(self.root), 'tool_name': 'exec_command', 'tool_input': {
            'cmd': f"Copy-Item -LiteralPath '{source}' -Destination '{destination}'"}}

    def test_literal_copy_read_original_to_new_work_file(self):
        (self.root / 'tmp').mkdir()
        e = self.copy_event(self.original, self.root / 'tmp/copy.txt')
        result = evaluate(e)
        self.assertEqual(result['decision'], 'allow')
        self.assertEqual(result['coverage'], 'literal_copy')
        self.assertEqual(result['targets'][0][0], 'copy_read')
        e['tool_name'] = 'Bash'
        e['tool_input']['command'] = e['tool_input'].pop('cmd')
        self.assertEqual(evaluate(e)['coverage'], 'literal_copy')
        e['tool_input']['shell'] = 'bash.exe'
        self.assertEqual(evaluate(e)['decision'], 'deny')
        self.assertEqual(hashlib.sha256(self.original.read_bytes()).hexdigest(), self.before)

    def test_literal_copy_rejects_overwrite_escape_and_compound_command(self):
        (self.root / 'tmp').mkdir()
        existing = self.root / 'tmp/existing.txt'; existing.write_text('keep')
        for destination in (self.original, existing, self.root / 'tmp/../knowledge/new.txt', self.root / 'elsewhere.txt'):
            with self.subTest(destination=destination):
                self.assertEqual(evaluate(self.copy_event(self.original, destination))['decision'], 'deny')
        for suffix in ('; Set-Content knowledge/original.txt x', ' -Recurse', ' -Force'):
            e = self.copy_event(self.original, self.root / 'tmp/new.txt')
            e['tool_input']['cmd'] += suffix
            self.assertEqual(evaluate(e)['decision'], 'deny')
        e = self.copy_event(self.original.parent, self.root / 'tmp/newdir')
        self.assertEqual(evaluate(e)['decision'], 'deny')
        self.assertEqual(existing.read_text(), 'keep')

    def test_literal_copy_rejects_resolved_destination_escape(self):
        (self.root / 'tmp').mkdir()
        e = self.copy_event(self.original, self.root / 'tmp/new.txt')
        actual_normalize = normalize_path
        def resolve_redirect(raw, cwd):
            if raw.endswith('new.txt'):
                return actual_normalize(str(self.root / 'knowledge/new.txt'), cwd)
            return actual_normalize(raw, cwd)
        with patch('event_adapter.normalize_path', side_effect=resolve_redirect):
            self.assertEqual(evaluate(e)['decision'], 'deny')
    def test_process_exit_and_json_contract(self):
        p = '*** Begin Patch\n*** Delete File: knowledge/original.txt\n*** End Patch'
        r = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / '.claude/hooks/protect_files.py')], input=json.dumps(self.event(p)), capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertEqual(self.original.read_text(), 'UNCHANGED')


if __name__ == '__main__': unittest.main()
