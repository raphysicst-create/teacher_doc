"""Read-only host inventory, discovery hashes, and app-server metadata probe.

Writes reports only under this project's .hwpdoc/. Does not trust hooks, modify
user settings, start model turns, or turn metadata discovery into load evidence.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import tomllib

from hwpdoc import ROOT, sha, write_json, now


def terminal_version():
    try:
        # The PowerShell npm shim is subject to the user's execution policy.
        # Use the fixed, argument-free cmd shim without changing that policy.
        result = subprocess.run(['cmd.exe', '/d', '/c', 'codex.cmd', '--version'],
                                capture_output=True, text=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else 'unverified: ' + result.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 'unverified: ' + str(exc)


def inventory():
    config = Path.home() / '.codex/config.toml'
    user = tomllib.loads(config.read_text(encoding='utf-8'))
    local = tomllib.loads((ROOT / '.codex/config.toml').read_text(encoding='utf-8'))
    fallbacks = local.get('project_doc_fallback_filenames', user.get('project_doc_fallback_filenames', []))
    names = ['AGENTS.override.md', 'AGENTS.md', *fallbacks]
    directories = [*reversed(ROOT.parents), ROOT]
    candidates = []
    selected = []
    # This is an on-disk precedence calculation, never proof of actual loading.
    for directory in [Path.home() / '.codex', *directories]:
        found = [directory / name for name in names if (directory / name).is_file()]
        candidates += [dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size) for p in found]
        nonempty = [p for p in found if p.stat().st_size]
        if nonempty:
            selected.append(str(nonempty[0]))
    canonical = ROOT / '.claude/skills/hwpx/SKILL.md'
    link = ROOT / '.agents/skills/hwpx/SKILL.md'
    same = link.is_file() and link.resolve() == canonical.resolve() and sha(link) == sha(canonical)
    mcp = json.loads((ROOT / '.mcp.json').read_text(encoding='utf-8'))['mcpServers']
    mcp_configs = {name: dict(claude_configured=name in mcp, codex_configured=name in local.get('mcp_servers', {}) or name in user.get('mcp_servers', {}),
                             exposed='unverified', actual_call='unverified') for name in ('school_task_guide', 'kordoc')}
    report = dict(at=now(), candidates=candidates, disk_precedence_only=selected,
                  configured_max_bytes=local.get('project_doc_max_bytes', user.get('project_doc_max_bytes', 32768)),
                  canonical=dict(path=str(canonical.resolve()), sha256=sha(canonical)),
                  discovery_link=dict(path=str(link), target=str(link.resolve()), same_content=same),
                  actual_loaded={'codex': 'unverified', 'work': 'unverified'},
                  mcp=mcp_configs,
                  hooks={'registration': str(ROOT / '.codex/hooks.json'), 'trusted': 'unverified', 'actual_blocking': 'unverified'},
                  source_versions={'terminal_cli': terminal_version()})
    session_id = os.environ.get('CODEX_THREAD_ID')
    if session_id:
        files = list((Path.home() / '.codex/sessions').glob('*/*/*/*' + session_id + '*.jsonl'))
        if files:
            for line in files[0].open(encoding='utf-8'):
                data = json.loads(line)
                if data['type'] == 'session_meta':
                    meta = data['payload']
                    report['source_versions']['active_session'] = {k: meta.get(k) for k in ('originator', 'cli_version', 'cwd')}
                    report['transcript'] = str(files[0])
                if data['type'] == 'turn_context':
                    report['source_versions']['active_model'] = {k: data['payload'].get(k) for k in ('model', 'effort')}
                    break
    write_json(ROOT / '.hwpdoc/environment.json', report)
    return report


def probe(binary):
    """JSON-RPC metadata only, using local generated app-server schema."""
    binary = Path(binary).resolve()
    errors = ROOT / '.hwpdoc/app-server-stderr.log'; errors.parent.mkdir(exist_ok=True)
    with errors.open('w', encoding='utf-8') as stderr:
        proc = subprocess.Popen([str(binary), 'app-server', '--stdio'], cwd=ROOT,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
                                text=True, encoding='utf-8')
        received = queue.Queue()
        def reader():
            for line in proc.stdout:
                try: received.put(json.loads(line))
                except ValueError: pass
        threading.Thread(target=reader, daemon=True).start()
        def request(number, method, params):
            proc.stdin.write(json.dumps(dict(id=number, method=method, params=params)) + '\n'); proc.stdin.flush()
            while True:
                msg = received.get(timeout=50)
                if msg.get('id') == number:
                    return msg
                if 'id' in msg and 'method' in msg:
                    # Never approve an unexpected server request in an inventory probe.
                    proc.stdin.write(json.dumps({'id': msg['id'], 'error': {'code': -32601, 'message': 'Read-only metadata probe'}}) + '\n'); proc.stdin.flush()
        results = dict(at=now(), binary=str(binary), binary_sha256=sha(binary))
        try:
            results['initialize'] = request(1, 'initialize', {'clientInfo': {'name': 'hwpdoc_environment_probe', 'version': '1.0'}, 'capabilities': {'experimentalApi': True}})
            proc.stdin.write('{"method":"initialized"}\n'); proc.stdin.flush()
            results['skills'] = request(2, 'skills/list', {'cwds': [str(ROOT)], 'forceReload': True})
            results['hooks'] = request(3, 'hooks/list', {'cwds': [str(ROOT)]})
            config = request(4, 'config/read', {'cwd': str(ROOT), 'includeLayers': True})
            # Do not persist arbitrary config fields that can contain credentials.
            effective = config.get('result', {}).get('config', {})
            results['config'] = {key: effective.get(key) for key in ('project_doc_fallback_filenames', 'project_doc_max_bytes', 'project_root_markers', 'model', 'model_reasoning_effort')}
            results['load_assurance'] = 'metadata_only; skill body and model instruction loading unverified'
        except (queue.Empty, OSError) as exc:
            results['error'] = str(exc) or 'app-server response timeout'
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    write_json(ROOT / '.hwpdoc/app-server-probe.json', results)
    # Keep outputs small and limited to this project's skill/hook records.
    return dict(at=results['at'], error=results.get('error'), config=results.get('config'),
                skills=[s for group in results.get('skills', {}).get('result', {}).get('data', []) for s in group.get('skills', []) if s['name'] == 'hwpx'],
                hooks=results.get('hooks'), report=str(ROOT / '.hwpdoc/app-server-probe.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inventory')
    p = sub.add_parser('probe'); p.add_argument('--binary', required=True)
    args = parser.parse_args()
    result = inventory() if args.command == 'inventory' else probe(args.binary)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
