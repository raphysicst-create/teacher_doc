"""Generate reviewable app hook registration without trusting hooks implicitly."""
from pathlib import Path
import json
import subprocess
import sys
import copy
import uuid
import base64

import hwpdoc as h


def hook_command(script, mode, app='claude'):
    # Hosts may execute hook commands through Git Bash, cmd or PowerShell.
    # Encode the PowerShell invocation so Windows backslashes and shell-special
    # characters in installation paths never pass through the outer shell.
    literal = str(script).replace("'", "''")
    invocation = ("$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue'; try { "
                  f"& '{literal}' -Event '{mode}'; exit $LASTEXITCODE"
                  " } catch { [Console]::Error.WriteLine('hwpdoc hook unavailable; protection unverified: ' + $_.Exception.Message); exit 2 }")
    encoded = base64.b64encode(invocation.encode('utf-16-le')).decode('ascii')
    # Process-only policy permits local scripts without changing registry policy;
    # centrally managed execution policy still takes precedence.
    command = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -OutputFormat Text -EncodedCommand ' + encoded
    # Codex's Windows host wraps commands in PowerShell -Command, which otherwise
    # changes a native exit 2 (deny) into exit 1 (non-blocking hook error).
    # Claude's Git Bash already preserves the native status; keep its syntax separate.
    return command + ('; exit $LASTEXITCODE' if app == 'codex' else '')


def setup_hooks(args):
    with h.lock(h.workspace_path('.hwpdoc/setup-hooks.lock')):
        return _setup_hooks(args)


def _remove_owned_hooks(existing, owned):
    """Remove exact recorded hooks while retaining all unrelated registrations."""
    result = copy.deepcopy(existing)
    hooks = result.setdefault('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('hooks는 JSON 객체여야 합니다')
    for event, entries in owned.items():
        candidates = hooks.get(event, [])
        if not isinstance(candidates, list):
            raise ValueError('훅 이벤트 목록 형식 오류: ' + event)
        for recorded in entries:
            metadata = {k: v for k, v in recorded.items() if k != 'hooks'}
            for candidate in list(candidates):
                if not isinstance(candidate, dict) or not isinstance(candidate.get('hooks'), list):
                    raise ValueError('훅 항목 형식 오류: ' + event)
                shared_commands = {x.get('command') for x in candidate['hooks'] if isinstance(x, dict)} & {x.get('command') for x in recorded['hooks']}
                if not shared_commands:
                    continue
                if {k: v for k, v in candidate.items() if k != 'hooks'} != metadata:
                    raise ValueError('사용자가 수정한 기존 hwpdoc 훅을 자동 교체하지 않습니다: ' + event)
                if any(x.get('command') in shared_commands and x not in recorded['hooks'] for x in candidate['hooks']):
                    raise ValueError('사용자가 수정한 기존 hwpdoc 명령을 자동 교체하지 않습니다: ' + event)
                candidate['hooks'] = [x for x in candidate['hooks'] if x not in recorded['hooks']]
                if not candidate['hooks']:
                    candidates.remove(candidate)
        if event in hooks:
            if candidates:
                hooks[event] = candidates
            else:
                del hooks[event]
    return result


def _setup_hooks(args):
    script = h.CODE_ROOT / 'scripts/hook.ps1'
    # Preserve stdin and deny exit codes across the host's command shell.
    registrations = {}
    matcher = '|'.join(args.tool) if args.tool else '.*'
    for event, mode in [('PreToolUse', 'pre'), ('PostToolUse', 'post'), ('Stop', 'stop')]:
        command = hook_command(script, mode, args.app)
        # A real Windows host cancelled a protected Edit at the old 10s limit.
        # Cold PowerShell/Python startup needs headroom; timeout is not a deny.
        entry = {'hooks': [{'type': 'command', 'command': command, 'timeout': 120 if mode == 'stop' else 60}]}
        if mode != 'stop':
            entry['matcher'] = matcher
        registrations[event] = [entry]
    remove = getattr(args, 'remove', False)
    receipt = h.workspace_path('.hwpdoc/hooks-' + args.app + '-owned.json')
    destination = h.workspace_path('.claude/settings.json' if args.app == 'claude' else '.codex/hooks.json')
    existing = h.read_json(destination) if destination.exists() else {}
    if not isinstance(existing, dict):
        raise ValueError('앱 설정은 JSON 객체여야 합니다')
    owned = h.read_json(receipt) if receipt.exists() else {'version': 1, 'hooks': {}}
    if not isinstance(owned, dict) or owned.get('version') != 1 or not isinstance(owned.get('hooks'), dict):
        raise ValueError('hwpdoc 훅 소유 기록 형식 오류')
    updated = _remove_owned_hooks(existing, owned['hooks'])
    if not remove:
        for event, entries in registrations.items():
            hook_list = updated['hooks'].setdefault(event, [])
            if not isinstance(hook_list, list):
                raise ValueError('훅 이벤트 목록 형식 오류: ' + event)
            for entry in entries:
                if entry not in hook_list:
                    hook_list.append(entry)
    proposal = h.workspace_path('.hwpdoc/setup-' + args.app + '-hooks.json')
    h.write_json(proposal, updated)
    backup = None
    if args.apply:
        backup = h.workspace_path('.hwpdoc/hooks-history/' + args.app + '-' + uuid.uuid4().hex + '.json')
        h.write_json(backup, {'at': h.now(), 'destination_existed': destination.exists(), 'settings': existing, 'ownership': owned})
        h.write_json(destination, updated)
        h.write_json(receipt, {'version': 1, 'hooks': {} if remove else registrations,
                              'installation': str(h.CODE_ROOT), 'at': h.now()})
        h.audit('remove_hooks' if remove else 'setup_hooks', destination, 'pass', {'backup': str(backup), 'actual_blocking': 'unverified'})
    return {'status': ('removed' if remove else 'registered') if args.apply else 'proposal', 'path': str(destination if args.apply else proposal),
            'backup': str(backup) if backup else None, 'ownership_record': str(receipt),
            'trust': 'unverified', 'actual_blocking': 'unverified', 'actual_tool_names': args.tool or [],
            'next_action': '설정/등록/신뢰/실제 차단을 각각 확인하세요. 실제 도구명과 이벤트는 설치한 앱에서 확인해야 합니다.'}


def setup_runtime(args):
    """Use a preinstalled environment. Dependency installation is a separate command."""
    executable = Path(args.python).resolve()
    probe = subprocess.run([str(executable), '-B', '-X', 'utf8', '-c',
                            'import json,sys; print(json.dumps({"version":list(sys.version_info[:2])}))'],
                           capture_output=True, text=True, encoding='utf-8', timeout=15)
    if probe.returncode != 0 or json.loads(probe.stdout).get('version') != [3, 12]:
        raise ValueError('실행 가능한 Python 3.12가 필요합니다')
    data = Path(args.data_dir).resolve() if args.data_dir else h.CONTEXT.pc_data
    config = data / 'runtime.json'
    if config.exists():
        raise ValueError('기존 PC 설정을 덮어쓰지 않습니다. 먼저 현재 설정을 확인하세요')
    h.write_json(config, {'version': 1, 'python': str(executable)})
    return {'status': 'configured', 'path': str(config), 'packages': 'unverified', 'next_action': 'doctor로 의존성과 한글을 확인하세요'}


def add_commands(commands):
    p = commands.add_parser('setup-hooks')
    p.add_argument('--app', choices=['claude', 'codex'], required=True)
    p.add_argument('--tool', action='append', help='실제 관측한 도구명의 matcher 정규식')
    p.add_argument('--apply', action='store_true', help='기존 설정을 보존하여 항목 병합; 신뢰는 자동 설정하지 않음')
    p.add_argument('--remove', action='store_true', help='소유 기록과 일치하는 hwpdoc 훅만 제거 제안; --apply로 적용')
    p = commands.add_parser('setup-runtime')
    p.add_argument('--python', required=True); p.add_argument('--data-dir')
