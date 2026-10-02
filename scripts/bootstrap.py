#!/usr/bin/env python3
"""Install an isolated runtime, initialize a workspace, and make a practice HWPX.

Run only after the user requests installation. The shell/PowerShell entry points
can prepare app-local Python after consent. This Python stage never installs Hancom,
changes security settings, registers hooks, or edits Codex configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import venv

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'teacher-doc-bootstrap-v1'


def read(path):
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('설정은 JSON 객체여야 합니다: ' + str(path))
    return value


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def run(argv, *, env=None, timeout=600):
    result = subprocess.run([str(x) for x in argv], env=env, capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'명령 실패 (exit {result.returncode}): {argv[0]}\n'
                           + (result.stdout + result.stderr)[-12000:])
    return result.stdout


def interpreter(folder):
    return folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def requirements(args):
    files = ['requirements-base.txt']
    if os.name == 'nt':
        files.append('requirements-windows.txt')
    if args.school_data:
        files.append('requirements-school-data.txt')
    if args.visual:
        files.append('requirements-visual.txt')
    return [ROOT / 'distribution' / name for name in files]


def verify_python(python, reqs, env):
    code = "import sys; assert sys.version_info[:2] == (3,12), 'Python 3.12 required'"
    run([python, '-B', '-X', 'utf8', '-c', code], env=env)
    # pip check alone accepts an empty environment; verify exact pins and imports.
    code = ("import importlib,importlib.metadata as m,json; "
            "pairs=json.loads(__import__('sys').argv[1]); "
            "[(importlib.import_module(mod), "
            "(_ for _ in ()).throw(AssertionError(name+' version mismatch')) "
            "if m.version(name)!=ver else None) for name,ver,mod in pairs]")
    modules = {'python-hwpx': 'hwpx', 'pywin32': 'win32com', 'PyMuPDF': 'fitz',
               'python-calamine': 'python_calamine', 'et-xmlfile': 'et_xmlfile'}
    pins = []
    for path in reqs:
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            name, version = line.split(';')[0].strip().split('==')
            pins.append((name, version, modules.get(name, name)))
    run([python, '-B', '-X', 'utf8', '-c', code, json.dumps(pins)], env=env)
    run([python, '-B', '-X', 'utf8', '-m', 'pip', 'check'], env=env)


def install(args):
    if sys.version_info[:2] != (3, 12):
        raise ValueError('Python 3.12가 필요합니다. 기존 3.12 실행 파일을 선택하세요. '
                         '없으면 scripts/bootstrap.ps1 또는 bootstrap.sh에서 앱 전용 Python 설치 승인을 받아 이어서 진행하세요.')
    for relative in ('skills/hwpx/SKILL.md', 'scripts/teacher_doc.py',
                     '.codex-plugin/plugin.json', 'distribution/requirements-base.txt'):
        if not (ROOT / relative).is_file():
            raise ValueError('불완전한 설치입니다. hwpx 스킬만 설치하지 말고 저장소 전체를 설치하세요: ' + relative)
    workspace = Path(args.workspace).expanduser().resolve()
    data = Path(args.data_dir or os.environ.get('HWPDOC_PC_DATA') or
                (Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'hwpdoc')).expanduser().resolve()
    if workspace.is_relative_to(ROOT) or ROOT.is_relative_to(workspace):
        raise ValueError('설치 코드와 겹치지 않는 별도 작업 폴더를 선택하세요')
    if data.is_relative_to(ROOT) or ROOT.is_relative_to(data):
        raise ValueError('PC 데이터 폴더는 설치 코드 밖에 두세요')
    # Reject bad or foreign workspaces before creating/installing the runtime.
    marker = workspace / '.hwpdoc/workspace.json'
    if marker.exists():
        settings = read(marker)
        if settings.get('kind') != 'hwpdoc-workspace' or settings.get('version') != 1:
            raise ValueError('기존 작업 설정이 손상됐거나 다른 형식입니다. 자동 덮어쓰기하지 않습니다')
        if settings.get('app') != args.app:
            raise ValueError('기존 작업 폴더의 앱 설정을 자동 변경하지 않습니다. 별도 폴더를 선택하세요')
    # Installation must not inherit PIP_TARGET/PREFIX/USER or a config that
    # redirects packages outside this application's venv. Keep proxy/CA settings.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('PIP_') and key not in ('PYTHONPATH', 'PYTHONHOME')}
    env.update(HWPDOC_PC_DATA=str(data), PYTHONUTF8='1',
               PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
               PYTHONNOUSERSITE='1', PIP_CONFIG_FILE=os.devnull)
    reqs = requirements(args)
    digest = hashlib.sha256(b'python3.12\n' + sys.platform.encode() +
                            b''.join(p.name.encode() + p.read_bytes() for p in reqs)).hexdigest()
    config = data / 'runtime.json'
    if config.exists():
        record = read(config)
        if not isinstance(record.get('python'), str):
            raise ValueError('기존 runtime.json의 python은 실행 파일 경로 문자열이어야 합니다')
        python = Path(record['python'])
        if record.get('version') != 1 or not python.is_absolute() or not python.is_file():
            raise ValueError('기존 runtime.json이 유효하지 않습니다. 보존했습니다. --data-dir로 별도 경로를 선택하세요')
        try:
            verify_python(python, reqs, env)
        except (RuntimeError, OSError) as exc:
            raise ValueError('기존 실행 환경을 변경하지 않았습니다. --data-dir로 새 격리 경로를 선택하세요. ' + str(exc)) from exc
        runtime_state = 'reused_existing'
    else:
        folder = data / 'runtimes' / ('onboarding-' + digest[:16])
        receipt = folder / '.teacher-doc-runtime.json'
        if folder.exists():
            if not receipt.is_file() or read(receipt).get('owner') != OWNER or read(receipt).get('requirements_sha256') != digest:
                raise ValueError('소유 기록 없는 기존 환경을 덮어쓰지 않습니다: ' + str(folder))
        else:
            folder.mkdir(parents=True)
            write(receipt, {'owner': OWNER, 'requirements_sha256': digest, 'status': 'creating'})
        python = interpreter(folder)
        record = read(receipt)
        if record.get('status') != 'ready':
            # Retain this final path: venv launchers are not safely relocatable.
            venv.EnvBuilder(with_pip=True, clear=False).create(folder)
            for req in reqs:
                run([python, '-X', 'utf8', '-m', 'pip', 'install', '--require-virtualenv', '--disable-pip-version-check', '-r', req], env=env)
            verify_python(python, reqs, env)
            write(receipt, {'owner': OWNER, 'requirements_sha256': digest, 'status': 'ready'})
        else:
            verify_python(python, reqs, env)
        # Never replace an unrelated runtime selection made during installation.
        config.parent.mkdir(parents=True, exist_ok=True)
        with config.open('x', encoding='utf-8') as stream:
            json.dump({'version': 1, 'python': str(python)}, stream, indent=2)
        runtime_state = 'installed'
    command = [python, '-B', '-X', 'utf8', ROOT / 'scripts/teacher_doc.py']
    if not marker.exists():
        run([*command, 'init', workspace, '--app', args.app, '--skill-name', args.skill_name], env=env)
    # Always prove the XML path even if the separately requested COM check blocks.
    xml = json.loads(run([*command, '--workspace', workspace, 'doctor', '--mode', 'xml'], env=env))
    practice = json.loads(run([*command, '--workspace', workspace, 'first-doc'], env=env))
    full = None
    exit_code = 0
    if args.mode == 'full':
        result = subprocess.run([str(x) for x in [*command, '--workspace', workspace, 'doctor', '--mode', 'full']],
                                env=env, capture_output=True, text=True, encoding='utf-8', timeout=180)
        exit_code = result.returncode
        try:
            full = json.loads(result.stdout)
        except json.JSONDecodeError:
            full = {'status': 'unconfirmed', 'detail': (result.stdout + result.stderr)[-4000:]}
            exit_code = exit_code or 2
    summary = {'status': 'ready_xml' if exit_code == 0 else 'full_verification_incomplete',
               'runtime': runtime_state, 'python': str(python), 'source_python': sys.executable,
               'source_python_version': sys.version.split()[0], 'pc_data': str(data),
               'workspace': str(workspace), 'xml_doctor': xml['status'], 'practice': practice,
               'full_doctor': full, 'plugin_loaded_in_chat': 'unverified',
               'next_action': '새 대화에서 실제 설치 스킬을 읽으세요. 실제 공문은 기존 승인·한글 열기·렌더 검증 절차가 필요합니다.'}
    write(workspace / '.hwpdoc/onboarding.json', summary)
    return summary, exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--data-dir')
    parser.add_argument('--mode', choices=['xml', 'full'], default='xml')
    parser.add_argument('--app', choices=['codex', 'claude'], default='codex')
    parser.add_argument('--skill-name', default='hwpx')
    parser.add_argument('--school-data', action='store_true')
    parser.add_argument('--visual', action='store_true')
    args = parser.parse_args()
    try:
        result, code = install(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc), 'next_action':
                          '설치된 파일과 기존 자료는 보존했습니다. 원인을 해결한 뒤 같은 명령으로 재개하세요.'}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
