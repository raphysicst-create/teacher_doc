"""Claude/Codex event decoding. No shell evaluation; malformed patches fail closed.

This is a tool policy adapter, not a filesystem security boundary.
"""
from __future__ import annotations

import json
import ntpath
import os
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from hwpdoc_config import owned_workspace


def normalize_path(raw: str, cwd: str) -> str:
    if not isinstance(raw, str) or not raw.strip() or any(c in raw for c in '\x00\r\n'):
        raise ValueError('파일 경로가 없거나 해석할 수 없습니다')
    raw = raw.replace('/', '\\')
    if raw.startswith('\\\\?\\UNC\\'):
        raw = '\\\\' + raw[8:]
    elif raw.startswith('\\\\?\\'):
        raw = raw[4:]
    # Drive-relative paths depend on hidden per-drive cwd; never guess.
    drive, tail = ntpath.splitdrive(raw)
    if drive and not tail.startswith('\\'):
        raise ValueError('드라이브 상대 경로는 지원하지 않습니다: ' + raw)
    if not drive:
        raw = ntpath.join(cwd, raw)
    result = ntpath.normpath(raw)
    if not ntpath.isabs(result):
        raise ValueError('절대 작업 디렉터리가 필요합니다')
    if ':' in ntpath.splitdrive(result)[1]:
        raise ValueError('대체 데이터 스트림 경로는 지원하지 않습니다')
    if any(part.endswith((' ', '.')) for part in result.split('\\') if part):
        raise ValueError('후행 공백/온점 경로는 지원하지 않습니다')
    if os.name == 'nt':
        result = str(Path(result).resolve())
    return ntpath.normcase(result)


def patch_targets(command: str) -> list[tuple[str, str]]:
    if not isinstance(command, str):
        raise ValueError('패치 command는 문자열이어야 합니다')
    lines = command.splitlines()
    if len(lines) < 3 or lines[0] != '*** Begin Patch' or lines[-1] != '*** End Patch':
        raise ValueError('패치 시작/종료 표식을 해석할 수 없습니다')
    targets = []
    operation = None
    body = 0
    moved = False
    for line in lines[1:-1]:
        match = re.fullmatch(r'\*\*\* (Add|Update|Delete) File: (.+)', line)
        if match:
            if operation in ('Add', 'Update') and body == 0:
                raise ValueError('본문 없는 패치')
            operation, path = match.groups()
            targets.append((operation.lower(), path))
            body = 0
            moved = False
        elif line.startswith('*** Move to: '):
            if operation != 'Update' or moved or body:
                raise ValueError('잘못된 이동 패치')
            targets.append(('move_destination', line[len('*** Move to: '):]))
            moved = True
        elif operation == 'Add' and line.startswith('+'):
            body += 1
        elif operation == 'Update' and (line.startswith((' ', '+', '-', '@@')) or line in ('', '*** End of File')):
            if not line.startswith('@@') and line != '*** End of File':
                body += 1
        else:
            raise ValueError('해석 불가 패치 행: ' + line[:120])
    if not targets or (operation in ('Add', 'Update') and body == 0):
        raise ValueError('빈 패치 또는 본문 누락')
    return targets


def targets_for_event(data: dict) -> list[tuple[str, str]]:
    tool = data.get('tool_name', '')
    inp = data.get('tool_input')
    if not isinstance(inp, dict):
        raise ValueError('tool_input 객체 누락')
    if tool == 'apply_patch':
        return patch_targets(inp.get('command'))
    if tool in ('Edit', 'Write'):
        return [('write', inp.get('file_path'))]
    if tool.endswith(('__patch_document', '__fill_form')):
        # Verified kordoc 4.12 schema: file_path is READ-only; output_path is the
        # sole write target. Rejecting the source would break ordinary copy edits.
        if inp.get('output_path'):
            return [('mcp_write', inp['output_path'])]
        if tool.endswith('__fill_form'):
            return []  # documented text-return mode, no output file
        raise ValueError('patch_document output_path 누락')
    if tool.startswith('mcp__') and re.search(r'(patch_document|fill_form|write_file|edit_file|delete_file|move_file)$', tool):
        keys = ('file_path', 'path', 'input_path', 'output_path', 'source', 'destination')
        found = [('mcp_write', inp[k]) for k in keys if isinstance(inp.get(k), str)]
        if not found:
            raise ValueError('MCP 수정 대상 경로 스키마 미확인: ' + tool)
        return found
    return []


def literal_copy_targets(command: str, cwd: str):
    """Recognize only one literal PowerShell file copy into a new work file.

    No shell parsing/evaluation, compound commands, directory copies or overwrite.
    Resolved containment also rejects junction escapes. Other syntax keeps the
    existing conservative shell policy.
    """
    wrapper = re.fullmatch(r'(?:powershell|pwsh)(?:\.exe)?\s+-NoProfile\s+-Command\s+"([^"\r\n]+)"', command, re.I)
    if wrapper:
        # Claude's Bash tool invokes PowerShell through a double-quoted command.
        # Reject outer-shell expansion before considering the single literal copy.
        if '$' in wrapper[1] or '`' in wrapper[1] or '\\' in wrapper[1]:
            return None
        command = wrapper[1]
    match = re.fullmatch(
        r"Copy-Item[ \t]+-LiteralPath[ \t]+'([^'\r\n]+)'[ \t]+-Destination[ \t]+'([^'\r\n]+)'[ \t]*",
        command, re.I)
    if not match:
        return None
    source, destination = (normalize_path(p, cwd) for p in match.groups())
    root = normalize_path(cwd, cwd)
    allowed_roots = [ntpath.join(root, name) for name in ('tmp', 'output')]
    # Compare against lexical work roots, not a potentially redirected junction.
    if not any(ntpath.commonpath([base, destination]) == base for base in allowed_roots):
        raise ValueError('복사 대상은 프로젝트 tmp/output 내부의 새 파일이어야 합니다')
    if not Path(source).is_file() or Path(destination).exists() or not Path(destination).parent.is_dir():
        raise ValueError('복사는 기존 단일 파일에서 기존 작업 폴더의 새 파일로만 허용합니다')
    return [('copy_read', source), ('copy_new', destination)]


def evaluate(data: dict) -> dict:
    from protect_files import DANGEROUS_PATTERNS, protected_reason
    if not isinstance(data, dict):
        return {'decision': 'deny', 'reason': '이벤트 JSON 객체가 필요합니다', 'targets': []}
    tool = data.get('tool_name', '')
    cwd = data.get('cwd')
    if not isinstance(cwd, str) or not ntpath.isabs(cwd):
        return {'decision': 'deny', 'reason': '이벤트 cwd 누락/상대경로', 'targets': []}
    try:
        targets = [(op, normalize_path(path, cwd)) for op, path in targets_for_event(data)]
        for operation, path in targets:
            reason = protected_reason(path)
            if reason:
                return {'decision': 'deny', 'reason': reason, 'targets': targets}
        if tool in ('Bash', 'PowerShell', 'exec_command', 'shell', 'shell_command'):
            inp = data['tool_input']
            command = inp.get('command', inp.get('cmd', ''))
            if not isinstance(command, str):
                raise ValueError('셸 command 해석 불가')
            workspace = owned_workspace(cwd)
            if workspace is None:
                return {'decision': 'allow', 'reason': '공문 작업 폴더 밖; 이 훅의 셸 보호 대상 아님', 'targets': [], 'coverage': 'out_of_scope'}
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.I):
                    return {'decision': 'deny', 'reason': '위험 명령 패턴: ' + pattern, 'targets': []}
            # Codex's Windows host reports exec_command as Bash to registered hooks.
            if tool in ('Bash', 'PowerShell', 'exec_command', 'shell', 'shell_command') and os.name == 'nt':
                shell = inp.get('shell', '')
                if not shell or ntpath.basename(shell).lower() in ('powershell', 'powershell.exe', 'pwsh', 'pwsh.exe'):
                    copy_targets = literal_copy_targets(command, cwd)
                    if copy_targets is not None:
                        return {'decision': 'allow', 'reason': '원본 읽기 → tmp/output 새 파일 복사',
                                'targets': copy_targets, 'coverage': 'literal_copy'}
            # Deliberately conservative for visible direct writes. Dynamic scripts,
            # aliases and child processes remain unsupported, documented separately.
            mutation = r'(?i)(set-content|add-content|out-file|remove-item|move-item|copy-item|write_(text|bytes)|open\s*\(|unlink\s*\(|rename\s*\(|shutil\.|\s>{1,2})'
            if re.search(mutation, command) and re.search(r'(?i)(knowledge|docs)[/\\]', command):
                # Absolute literal paths to another workspace are not protected
                # merely because a directory there is also named docs/knowledge.
                literals = re.findall(r"'([^'\r\n]+)'|\"([^\"\r\n]+)\"", command)
                absolute = [a or b for a, b in literals if ntpath.isabs(a or b)]
                if absolute and all(owned_workspace(p) is None for p in absolute) and not re.search(r"(?i)(?<![\w/\\])(knowledge|docs)[/\\]", re.sub(r"'[^']*'|\"[^\"]*\"", '', command)):
                    return {'decision': 'allow', 'reason': '공문 작업 폴더 밖 절대 경로', 'targets': [], 'coverage': 'partial'}
                return {'decision': 'deny', 'reason': '보호 폴더 직접 쓰기: 정적 명령으로 안전한 대상 구분 불가', 'targets': []}
            return {'decision': 'allow', 'reason': '위험 패턴 검사만 수행; 동적 셸 쓰기 보호 미지원', 'targets': [], 'coverage': 'partial'}
        return {'decision': 'allow', 'reason': '보호 대상 기존 파일 없음', 'targets': targets}
    except (ValueError, TypeError, KeyError) as exc:
        return {'decision': 'deny', 'reason': str(exc), 'targets': []}


def emit_pre(data: dict) -> int:
    result = evaluate(data)
    if result['decision'] == 'deny':
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
              'permissionDecision': 'deny', 'permissionDecisionReason': result['reason']}}, ensure_ascii=False))
        print('차단: ' + result['reason'], file=sys.stderr)
        return 2
    print('{}')
    return 0
