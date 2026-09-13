"""Allowlist packaging. Missing rights/privacy reviews block any distributable copy."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def check_release(manifest, rights):
    issues, entries = [], []
    if manifest.get('version') != 1 or not isinstance(manifest.get('files'), list) or not manifest['files']:
        raise ValueError('배포 manifest 형식 오류')
    names = set()
    for item in manifest['files']:
        source, destination = Path(item['source']), Path(item['destination'])
        path = (ROOT / source).resolve()
        if not source.parts or not destination.parts or source.drive or destination.drive or source.is_absolute() or destination.is_absolute() or '..' in source.parts or '..' in destination.parts or not path.is_relative_to(ROOT):
            raise ValueError('배포 파일 경로 이탈')
        if source.parts[0] in ('knowledge', 'logs', 'output', 'tmp', '.hwpdoc', 'evals', 'config') or 'scratchpad' in source.parts:
            raise ValueError('운영/평가 자료는 배포할 수 없습니다: ' + str(source))
        name = destination.as_posix().casefold()
        if name in names or any(name.startswith(existing + '/') or existing.startswith(name + '/') for existing in names):
            raise ValueError('중복 배포 경로')
        names.add(name)
        if not path.is_file():
            issues.append({'file': str(source), 'reason': 'missing'}); continue
        sha = digest(path)
        review = rights.get('files', {}).get(source.as_posix(), {})
        if not (review.get('sha256') == sha and all(review.get(k) for k in ('license', 'source', 'permission_record', 'reviewed_by', 'reviewed_at'))):
            issues.append({'file': str(source), 'reason': 'rights_unconfirmed'})
        if not (review.get('privacy_review') and review.get('privacy_sha256') == sha):
            issues.append({'file': str(source), 'reason': 'privacy_unconfirmed'})
        if path.suffix.lower() in ('.py', '.ps1', '.md', '.json', '.xml', '.hpf', '.txt'):
            text = path.read_text(encoding='utf-8-sig')
            if re.search(r'(?i)[a-z]:[/\\]Users[/\\]|화동중|Desktop[/\\]maintain', text):
                issues.append({'file': str(source), 'reason': 'local_identity_or_path'})
            if path.suffix.lower() == '.hpf':
                try:
                    root = ElementTree.fromstring(text)
                    private = [element.get('name') for element in root.iter()
                               if element.tag.endswith('}meta') and element.get('name') in ('creator', 'lastsaveby', 'CreatedDate', 'ModifiedDate', 'date')
                               and (element.text or '').strip()]
                    if private:
                        issues.append({'file': str(source), 'reason': 'document_identity_metadata', 'fields': private})
                except ElementTree.ParseError:
                    issues.append({'file': str(source), 'reason': 'invalid_asset_xml'})
        entries.append({'source': source.as_posix(), 'destination': destination.as_posix(), 'sha256': sha})
    for name in manifest.get('dependency_reviews', []):
        review = rights.get('dependencies', {}).get(name, {})
        if not all(review.get(k) for k in ('license', 'source', 'conditions_review', 'reviewed_by')):
            issues.append({'dependency': name, 'reason': 'dependency_license_unconfirmed'})
    return {'status': 'blocked' if issues else 'ready_to_package', 'issues': issues, 'files': entries,
            'release_ready': False, 'note': '포장 가능 여부만 검사합니다. 앱 인수·동료 교사 시범 사용은 별도 평가입니다.'}


def build(manifest, rights, output=None):
    result = check_release(manifest, rights)
    if output is None or result['issues']:
        return result
    output = Path(output).resolve()
    if output.name != 'hwpdoc' or output.exists() or not output.is_relative_to(ROOT):
        raise ValueError('배포 출력은 프로젝트 안의 존재하지 않는 hwpdoc 폴더여야 합니다')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.hwpdoc-building-', dir=output.parent))
    for entry in result['files']:
        destination = staging / entry['destination']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / entry['source'], destination)
        if digest(destination) != entry['sha256']:
            raise ValueError('배포 복사 해시 불일치: ' + str(destination))
    (staging / 'release-inventory.json').write_text(json.dumps(dict(result, status='packaged'), ensure_ascii=False, indent=2), encoding='utf-8')
    # A failed copy never leaves a half-built plugin at the installation target.
    staging.rename(output)
    result.update(status='packaged', directory=str(output))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, default=ROOT / 'distribution/release-files.json')
    ap.add_argument('--rights', type=Path, required=True)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    try:
        result = build(read(args.manifest), read(args.rights), args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result['issues'] else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc), 'release_ready': False}, ensure_ascii=False))
        return 2


if __name__ == '__main__': raise SystemExit(main())
