"""Observe the active interpreter and installed distributions without installing."""
import importlib
from importlib import metadata
from pathlib import Path
import platform
import re
import sys

PACKAGES = {
    'lxml': ('lxml', False), 'hwpx': ('python-hwpx', False),
    'win32com': ('pywin32', False), 'pypdf': ('pypdf', False),
    'fitz': ('PyMuPDF', True), 'openpyxl': ('openpyxl', True),
    'et_xmlfile': ('et-xmlfile', True), 'python_calamine': ('python-calamine', True),
}


def installed_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def snapshot():
    return {'python': str(Path(sys.executable).resolve()), 'version': platform.python_version(),
            'implementation': platform.python_implementation(), 'machine': platform.machine(),
            'packages': {distribution: installed_version(distribution) for distribution, _ in PACKAGES.values()}}


def diagnostics(code_root):
    expected = {}
    for path in sorted((Path(code_root) / 'distribution').glob('requirements-*.txt')):
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match = re.match(r'^([A-Za-z0-9_.-]+)==([^ ;]+)', line.strip())
            if match:
                expected[match[1].replace('_', '-').lower()] = match[2]
    results = {}
    for module, (distribution, optional) in PACKAGES.items():
        version = installed_version(distribution)
        required = expected.get(distribution.lower())
        error = None
        if version is not None:
            try:
                importlib.import_module(module)
            except Exception as exc:
                error = str(exc)
        status = 'pass' if version is not None and version == required and error is None else 'unconfirmed'
        if not optional and (version is None or error):
            status = 'fail'
        results[module] = {'status': status, 'distribution': distribution, 'installed_version': version,
                           'expected_version': required, 'optional': optional,
                           'import_error': error,
                           'note': '개발에서 고정한 버전과 실제 import를 대조합니다. 문서 검증/앱 인수와 별개입니다.'}
    return results
