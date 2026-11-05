"""Generate reviewable app hook registration without trusting hooks implicitly."""
from pathlib import Path
import json
import subprocess
import sys
import copy
import uuid
import base64
import os
import re
import tomllib
from urllib.parse import urlsplit

import hwpdoc as h


DEFAULT_MCP_URL = 'https://teacher-doc-mcp.vercel.app/api/mcp'


def validate_mcp_url(url):
    """Validate endpoints locally; credentials belong to the remote server."""
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 for c in url) or '\\' in url:
        raise ValueError('MCP URL은 공백 없는 HTTPS URL이어야 합니다')
    parsed = urlsplit(url)
    if (not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.fragment
            or parsed.port == 0 or not (parsed.scheme == 'https' or
                parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost'))):
        raise ValueError('HTTPS만 허용합니다 (개발용 http://127.0.0.1 및 http://localhost 예외). URL 인증정보는 지원하지 않습니다')
    return url


def _json_add_member(text, key, value):
    """Insert one member without rewriting existing JSON members/formatting."""
    end = text.rfind('}')
    existing = json.loads(text)
    newline = '\r\n' if '\r\n' in text else '\n'
    entry = json.dumps(key) + ': ' + json.dumps(value, ensure_ascii=False)
    return text[:end].rstrip() + (',' if existing else '') + newline + '  ' + entry + newline + text[end:]


def _claude_mcp_text(text, url):
    existing = json.loads(text)
    if not isinstance(existing, dict):
        raise ValueError('Claude MCP 설정은 JSON 객체여야 합니다')
    servers = existing.get('mcpServers', {})
    if not isinstance(servers, dict):
        raise ValueError('mcpServers는 JSON 객체여야 합니다')
    entry = servers.get('teacher_doc_mcp')
    if 'teacher_doc_mcp' in servers:
        if not isinstance(entry, dict) or entry.get('url') != url or entry.get('type') != 'http' or 'command' in entry:
            raise ValueError('teacher_doc_mcp 앱 설정 충돌: 기존 항목을 보존했습니다')
        return text
    value = {'type': 'http', 'url': url}
    if 'mcpServers' not in existing:
        return _json_add_member(text, 'mcpServers', {'teacher_doc_mcp': value})
    # Find the actual top-level member, not a string/comment/nested lookalike.
    decoder, pos = json.JSONDecoder(), text.index('{') + 1
    while True:
        pos = len(text) - len(text[pos:].lstrip())
        key, pos = decoder.raw_decode(text, pos)
        pos = text.index(':', pos) + 1
        pos = len(text) - len(text[pos:].lstrip())
        _, end = decoder.raw_decode(text, pos)
        if key == 'mcpServers':
            return text[:pos] + _json_add_member(text[pos:end], 'teacher_doc_mcp', value) + text[end:]
        pos = text.index(',', end) + 1


def _codex_inline_mcp_text(text, url, servers):
    """Insert into the root inline table, retaining all existing source text.

    Called only when appending a subtable fails: a root inline table is sealed
    in TOML. Skip strings/comments so nested braces and sample settings in
    multiline strings cannot be mistaken for the table's closing brace.
    """
    basic = r'"(?:\\[\s\S]|[^"\\])*"'
    literal = r"'[^']*'"
    tokens = re.compile(
        r'(?P<assignment>^[ \t]*(?P<key>[A-Za-z0-9_-]+|' + basic + '|' + literal + r')[ \t]*=[ \t]*\{)'
        r'|"""(?:\\[\s\S]|(?!""")[\s\S])*""""{0,2}'
        r"|'''[\s\S]*?''''{0,2}"
        + '|' + basic + '|' + literal + r'|#[^\r\n]*|(?P<brace>[{}])', re.MULTILINE)
    depth = None
    for token in tokens.finditer(text):
        if depth is None:
            if token.group('assignment') and 'mcp_servers' in tomllib.loads(token.group('key') + ' = {}'):
                depth = 1
        elif token.group('brace'):
            depth += 1 if token.group('brace') == '{' else -1
            if depth == 0:
                entry = (', ' if servers else '') + 'teacher_doc_mcp = { url = ' + json.dumps(url, ensure_ascii=False) + ' }'
                return text[:token.start()] + entry + text[token.start():]
    return None


def _codex_mcp_text(text, url):
    existing = tomllib.loads(text)
    servers = existing.get('mcp_servers', {})
    if not isinstance(servers, dict):
        raise ValueError('mcp_servers는 TOML 테이블이어야 합니다')
    entry = servers.get('teacher_doc_mcp')
    if 'teacher_doc_mcp' in servers:
        if not isinstance(entry, dict) or entry.get('url') != url or 'command' in entry:
            raise ValueError('teacher_doc_mcp 앱 설정 충돌: 기존 항목을 보존했습니다')
        return text
    newline = '\r\n' if '\r\n' in text else '\n'
    updated = text + (newline if text and not text.endswith('\n') else '') + newline
    updated += '[mcp_servers.teacher_doc_mcp]' + newline + 'url = ' + json.dumps(url, ensure_ascii=False) + newline
    try:
        tomllib.loads(updated)
    except tomllib.TOMLDecodeError:
        updated = _codex_inline_mcp_text(text, url, servers)
        if updated is None:
            raise
        tomllib.loads(updated)  # Validate the insertion before any writes.
    return updated


def setup_mcp(args):
    from hwpdoc_workspace import workspace_settings
    url = validate_mcp_url(args.url)
    if h.ROOT == h.CODE_ROOT:
        raise ValueError('개발 체크아웃의 MCP 설정은 변경하지 않습니다. 별도 --workspace를 지정하세요')
    with h.lock(h.workspace_path('.hwpdoc/settings.lock')):
        marker, settings = workspace_settings()
        app = args.app or settings.get('app')
        if app not in ('claude', 'codex'):
            raise ValueError('--app codex|claude를 지정하세요')
        connection = settings.get('connections', {}).get('teacher_doc_mcp')
        if connection is None or connection == 'unconfirmed':
            connection = {}
        if not isinstance(connection, dict) or connection.get('url', url) != url:
            raise ValueError('connections.teacher_doc_mcp URL 충돌: 기존 설정을 보존했습니다')
        apps = connection.get('registered_apps', [])
        if not isinstance(apps, list) or any(a not in ('codex', 'claude') for a in apps):
            raise ValueError('registered_apps는 앱 이름 목록이어야 합니다')
        path = h.workspace_path('.mcp.json' if app == 'claude' else '.codex/config.toml')
        raw = path.read_bytes() if path.exists() else b''
        text = raw.decode('utf-8-sig') if raw else ('{}' if app == 'claude' else '')
        updated = (_claude_mcp_text if app == 'claude' else _codex_mcp_text)(text, url)
        encoded = (b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + updated.encode('utf-8')
        value = dict(connection, url=url, registered_apps=apps if app in apps else [*apps, app])
        changed = encoded != raw or connection != value
        if encoded != raw:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                temporary.write_bytes(encoded)
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        if connection != value:
            settings.setdefault('connections', {})['teacher_doc_mcp'] = value
            h.write_json(marker, settings)
            h.configure(h.ROOT)
        if changed:
            h.audit('setup_mcp', path, 'pass', {'url': url, 'app': app, 'actual_calls': 'unverified'})
    return {'status': 'configured' if changed else 'unchanged', 'path': str(path),
            **value, 'actual_calls': 'unverified'}


def mcp_diagnostics():
    connection = h.CONTEXT.settings.get('connections', {}).get('teacher_doc_mcp')
    connection = connection if isinstance(connection, dict) else {}
    url = connection.get('url')
    school = h.CONTEXT.settings.get('school', {}).get('neis')
    return {'configured': bool(url), 'url': url, 'registered_apps': connection.get('registered_apps', []),
            'school_identification_stored': bool(isinstance(school, dict) and school.get('candidateId')),
            'actual_calls': 'unverified'}


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
    if not (h.CODE_ROOT / 'scripts/hook.ps1').is_file():
        raise ValueError('이 배포본에는 훅이 포함되지 않습니다. 훅은 개발 저장소에서만 지원합니다')
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
    executable = Path(os.path.abspath(Path(args.python).expanduser()))
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
    p = commands.add_parser('setup-mcp', help='작업 폴더 앱 설정에 원격 teacher_doc_mcp 등록 (네트워크 호출 없음)')
    p.add_argument('--url', default=DEFAULT_MCP_URL, help='원격 학교 정보 MCP URL (생략하면 기본 서버 사용)')
    p.add_argument('--app', choices=['claude', 'codex'], help='생략하면 workspace.json의 app 사용')
    p = commands.add_parser('setup-hooks')
    p.add_argument('--app', choices=['claude', 'codex'], required=True)
    p.add_argument('--tool', action='append', help='실제 관측한 도구명의 matcher 정규식')
    p.add_argument('--apply', action='store_true', help='기존 설정을 보존하여 항목 병합; 신뢰는 자동 설정하지 않음')
    p.add_argument('--remove', action='store_true', help='소유 기록과 일치하는 hwpdoc 훅만 제거 제안; --apply로 적용')
    p = commands.add_parser('setup-runtime')
    p.add_argument('--python', required=True); p.add_argument('--data-dir')
