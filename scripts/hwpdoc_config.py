"""Versioned workspace/host paths. Importing this module never writes settings."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys

CODE_ROOT = Path(__file__).resolve().parents[1]
MARKER = Path('.hwpdoc/workspace.json')
CONFIG_VERSION = 1


def read_json(path):
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('설정은 JSON 객체여야 합니다: ' + str(path))
    return value


def discover_workspace(start=None):
    candidate = Path(start or os.getcwd()).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for folder in (candidate, *candidate.parents):
        if (folder / MARKER).is_file():
            return folder
    return None


def owned_workspace(start):
    """Scope protection by a marker, or this checkout's explicit legacy config."""
    path = Path(start).resolve()
    found = discover_workspace(path)
    if found:
        config = read_json(found / MARKER)
        if config.get('kind') != 'hwpdoc-workspace' or config.get('version') != CONFIG_VERSION:
            raise ValueError('공문 작업 폴더 표시가 손상됐습니다')
        return found
    if path.is_relative_to(CODE_ROOT) and (CODE_ROOT / 'config/legacy-workspace.json').is_file():
        return CODE_ROOT
    return None


@dataclass(frozen=True)
class Context:
    code: Path
    workspace: Path
    pc_data: Path
    settings: dict
    python: Path

    @property
    def skill(self):
        native = self.code / '.claude/skills/hwpx/scripts'
        return native if native.is_dir() else self.code / 'skills/hwpx/scripts'

    @property
    def external_copy(self):
        value = self.settings.get('delivery', {}).get('external_copy')
        return Path(value).expanduser().resolve() if value else None

    def local(self, value):
        """Workspace records must not escape through '..', drives or junctions."""
        raw = Path(value)
        path = (self.workspace / raw).resolve()
        if raw.drive or raw.is_absolute() or not path.is_relative_to(self.workspace):
            raise ValueError('작업 폴더 기준 상대경로가 필요합니다: ' + str(value))
        return path

    def optional_reference(self, name):
        return self.reference(name) if self.settings.get('references', {}).get(name) else None

    def reference(self, name):
        value = self.settings.get('references', {}).get(name)
        if not value:
            raise ValueError('학교 자료 설정 없음: references.' + name + ' — 해당 업무에 필요한 원문을 등록하세요')
        return self.local(value)

    def encode(self, path):
        path = Path(path).resolve()
        # Work records always win when installation and workspace coincide.
        if path.is_relative_to(self.workspace):
            return 'workspace:' + path.relative_to(self.workspace).as_posix()
        if path.is_relative_to(self.code):
            return 'plugin:' + path.relative_to(self.code).as_posix()
        return str(path)  # Legacy external inputs remain hash-bound, never reapproved.

    def decode(self, value):
        for prefix, root in (('workspace:', self.workspace), ('plugin:', self.code)):
            if value.startswith(prefix):
                relative = Path(value[len(prefix):])
                path = (root / relative).resolve()
                if relative.drive or relative.is_absolute() or not path.is_relative_to(root):
                    raise ValueError('기록 경로 이탈: ' + value)
                return path
        return Path(value)  # Version 1 absolute reports are supported unchanged.


def recorded_runtime(workspace):
    """Read the installation receipt as data, never silently use a different PC.

    A workspace can move on the same PC; its runtime is external. A copied
    receipt from another PC must be explicitly repaired/overridden, not guessed.
    """
    receipt = Path(workspace) / '.hwpdoc/onboarding.json'
    if not receipt.is_file():
        return None
    record = read_json(receipt)
    for key in ('pc_data', 'python'):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
            raise ValueError('설치 기록의 절대경로 형식 오류: ' + key + ' — 기존 기록을 보존하고 실제 PC 경로를 확인하세요')
    data = Path(record['pc_data'])
    config = data / 'runtime.json'
    if not config.is_file():
        raise ValueError('설치 기록의 runtime.json을 찾을 수 없습니다: ' + str(config)
                         + ' — 다른 PC/이동한 경로인지 확인하세요. 재설치나 기본 경로로 자동 전환하지 않습니다')
    host = read_json(config)
    if host.get('version') != 1 or host.get('python') != record['python']:
        raise ValueError('설치 기록과 runtime.json의 Python 경로 불일치 — 실제 경로 확인 후 명시적으로 PC 데이터를 선택하세요')
    if not Path(record['python']).is_file():
        raise ValueError('설치 기록의 Python이 없습니다: ' + record['python'] + ' — 기존 파일을 보존하고 실행 환경을 복구하세요')
    return record


def load_context(workspace=None, *, code_root=None, pc_data=None):
    code = Path(code_root or CODE_ROOT).resolve()
    chosen = workspace or os.environ.get('HWPDOC_WORKSPACE')
    root = Path(chosen).resolve() if chosen else discover_workspace()
    if root is None:
        # Compatibility only for the original checkout, never a plugin cache.
        if (code / 'CLAUDE.md').is_file() and (code / '.claude/skills/hwpx').is_dir():
            root = code
        else:
            raise ValueError('공문 작업 폴더 없음: init 또는 --workspace를 사용하세요')
    marker = root / MARKER
    legacy = code / 'config/legacy-workspace.json'
    settings = read_json(marker) if marker.is_file() else (read_json(legacy) if root == code and legacy.is_file() else {})
    if settings and (settings.get('kind') != 'hwpdoc-workspace' or settings.get('version') != CONFIG_VERSION):
        raise ValueError('미지원 작업 폴더 설정 버전/표시: ' + str(marker))
    if not settings and root != code:
        raise ValueError('작업 폴더 표시 없음: init을 먼저 실행하세요')
    for key in ('school', 'delivery', 'references', 'timetable_mapping', 'preferences', 'connections'):
        if key in settings and not isinstance(settings[key], dict):
            raise ValueError('학교 설정은 JSON 객체여야 합니다: ' + key)
    if any(not isinstance(value, str) or not value for value in settings.get('references', {}).values()):
        raise ValueError('학교 자료 경로는 비어 있지 않은 문자열이어야 합니다')
    selected_data = pc_data or os.environ.get('HWPDOC_PC_DATA')
    receipt = recorded_runtime(root) if not selected_data else None
    data = Path(selected_data or (receipt['pc_data'] if receipt else None) or
                (Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'hwpdoc')).expanduser().resolve()
    if selected_data and (root / '.hwpdoc/onboarding.json').is_file() and not (data / 'runtime.json').is_file():
        raise ValueError('명시한 PC 데이터의 runtime.json이 없습니다: ' + str(data) + ' — 기존 설치 경로를 확인하세요')
    host = read_json(data / 'runtime.json') if (data / 'runtime.json').is_file() else {}
    if host and (host.get('version') != 1 or not isinstance(host.get('python'), str) or not Path(host['python']).is_absolute()
                 or not Path(host['python']).is_file()):
        raise ValueError('미지원 PC 설정 버전')
    # Keep the venv launcher path: resolving its symlink selects base Python.
    python = Path(os.path.abspath(Path(host.get('python') or sys.executable).expanduser()))
    external = settings.get('delivery', {}).get('external_copy')
    if external is not None and not isinstance(external, str):
        raise ValueError('외부 복사 경로는 문자열 또는 null이어야 합니다')
    if external and external.startswith('profile:'):
        settings['delivery']['external_copy'] = str(Path.home() / external[len('profile:'):])
    return Context(code, root, data, settings, python)


def current_context():
    return load_context()
