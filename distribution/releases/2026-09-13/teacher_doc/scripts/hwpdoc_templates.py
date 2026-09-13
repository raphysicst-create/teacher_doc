"""Workspace-owned, hash-bound template registration; no implicit human approval."""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys
from zipfile import BadZipFile
from types import SimpleNamespace

import hwpdoc as h

REGISTRY_VERSION = 1
FILES = ('original.hwpx', 'template.hwpx', 'slots.json', 'mapping.json', 'budget.json', 'structure.json')


def folder_for(identifier, version):
    for value in (identifier, version):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9가-힣][A-Za-z0-9가-힣_.-]{0,90}', value):
            raise ValueError('양식 id/version은 경로 없는 식별자여야 합니다')
    root = h.workspace_path('.hwpdoc/templates')
    folder = (root / identifier / version).resolve()
    if not folder.is_relative_to(root.resolve()):
        raise ValueError('양식 경로 이탈')
    return folder


def extracted(path):
    from lxml.etree import XMLSyntaxError
    sys.path.insert(0, str(h.SKILL))
    from hwpx_slots import collect_slots
    try:
        result = collect_slots(path, preview_len=1000000)
    except (BadZipFile, XMLSyntaxError, KeyError) as exc:
        raise ValueError('읽을 수 없는 HWPX 패키지: ' + str(exc)) from exc
    result['source'] = path.name
    return result


def file_hashes(folder):
    return {name: h.sha(folder / name) for name in FILES if (folder / name).is_file()}


def review_errors(r, review):
    errors = []
    if not isinstance(review, dict):
        return ['등록 확인 기록은 JSON 객체여야 합니다']
    if not (review.get('confirmed') is True and all(isinstance(review.get(k), str) and review[k].strip() for k in ('by', 'at', 'record'))):
        errors.append('실제 사용자 확인 기록 누락')
    if review.get('purposes') != r.get('purposes') or review.get('provenance') != r.get('provenance'):
        errors.append('확인 후 지원 용도/원본 종류 변경')
    if review.get('hashes') != r.get('hashes'):
        errors.append('확인 기록과 등록 파일 해시 불일치')
    for name in ('review_render', 'review_images'):
        if name in r.get('stages', {}) and r['stages'][name].get('status') != 'pass':
            errors.append('검토 자료 준비 단계 미통과: ' + name)
    if r.get('provenance') != 'native':
        visual = review.get('visual', {})
        if not isinstance(visual, dict) or not visual.get('record') or visual.get('document_sha256') != r.get('hashes', {}).get('template.hwpx'):
            errors.append('현재 문서 해시의 육안 판독 기록 누락')
        else:
            images = visual.get('images')
            if not isinstance(images, list) or not images:
                errors.append('육안 판독 이미지 누락')
            else:
                for artifact in [visual.get('pdf'), *images]:
                    try:
                        if not isinstance(artifact, dict) or not artifact.get('path'):
                            raise ValueError('PDF/이미지 경로 누락')
                        path = h.workspace_path(artifact['path'])
                        if not path.is_file() or artifact.get('sha256') != h.sha(path):
                            raise ValueError('PDF/이미지 누락 또는 해시 변경: ' + artifact['path'])
                    except (ValueError, OSError, TypeError) as exc:
                        errors.append(str(exc))
    return errors


def inspect_registration(folder):
    r = h.read_json(folder / 'registration.json')
    if not isinstance(r, dict):
        raise ValueError('등록 기록은 JSON 객체여야 합니다')
    issues = []
    if r.get('version') != REGISTRY_VERSION:
        issues.append('등록 형식 버전 미지원')
    if r.get('status') == 'registered':
        for name in FILES:
            if not (folder / name).is_file() or r.get('hashes', {}).get(name) != h.sha(folder / name):
                issues.append('필수 파일 누락/변경: ' + name)
        receipt = folder / 'review.json'
        if not receipt.is_file() or r.get('review_sha256') != h.sha(receipt):
            issues.append('등록 확인 기록 누락/변경')
        else:
            review = h.read_json(receipt)
            issues.extend(review_errors(r, review))
        if r.get('source', {}).get('sha256') != r.get('hashes', {}).get('original.hwpx'):
            issues.append('원본 가져오기 해시 불일치')
        if not all(r.get('stages', {}).get(name, {}).get('status') == 'pass' for name in ('structure', 'namespaces', 'finalize', 'layout', 'profiles', 'hancom')):
            issues.append('필수 등록 검증 미통과')
    return r, issues


def resolve_template(ref):
    folder = folder_for(ref.get('id'), ref.get('version'))
    if not (folder / 'registration.json').is_file():
        raise ValueError('등록 양식 없음')
    r, issues = inspect_registration(folder)
    if r.get('status') != 'registered' or issues:
        raise ValueError('사용 불가 양식: ' + '; '.join(issues or ['등록 검토 대기']))
    path = folder / 'template.hwpx'
    if ref.get('sha256') != h.sha(path):
        raise ValueError('양식 참조 해시 불일치')
    return {'file': path, 'registration': r, 'mapping': h.read_json(folder / 'mapping.json')}


def registration_dependencies(ref):
    resolved = resolve_template(ref)
    folder = resolved['file'].parent
    paths = [p for p in folder.iterdir() if p.is_file() and p.name != '.lock']
    if resolved['registration']['provenance'] != 'native':
        visual = h.read_json(folder / 'review.json')['visual']
        paths += [h.workspace_path(a['path']) for a in [visual['pdf'], *visual['images']]]
    return paths


def list_templates():
    entries = []
    for name in h.TEMPLATES:
        folder = h.ROOT / 'knowledge/templates' / name
        if (folder / '양식.hwpx').is_file():
            entries.append({'id': name, 'version': 'legacy', 'status': 'legacy_available',
                            'purposes': [name], 'sha256': h.sha(folder / '양식.hwpx'),
                            'note': '기존 선택 경로 유지; 새 등록의 사람 확인을 대체하지 않음'})
    for p in sorted((h.ROOT / '.hwpdoc/templates').glob('*/*/registration.json')):
        try:
            r, issues = inspect_registration(p.parent)
            entries.append({'id': r['id'], 'version': r['template_version'],
                            'status': 'changed' if issues else r['status'], 'issues': issues,
                            'purposes': r['purposes'], 'sha256': r.get('hashes', {}).get('template.hwpx')})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            entries.append({'id': p.parent.parent.name, 'status': 'invalid', 'issues': [str(exc)]})
    return entries


def add_template(args):
    folder = folder_for(args.id, args.version)
    folder.mkdir(parents=True, exist_ok=True)
    with h.lock(folder / '.lock'):
        return _add_template(args, folder)


def prepare_review(folder, r):
    if r['status'] != 'awaiting_review' or r['hashes'] != file_hashes(folder):
        raise ValueError('등록 검증을 마친 현재 파일만 검토 자료로 준비할 수 있습니다')
    target = folder / 'review.draft.json'
    if target.exists():
        return dict(r, review_draft=str(target), next_action='기존 검토 초안을 보존했습니다. 실제 확인 후 --review로 제출하세요')
    review = dict(confirmed=False, by='', at='', record='', hashes=r['hashes'],
                  purposes=r['purposes'], provenance=r['provenance'], prepared_at=h.now())
    if r['provenance'] != 'native':
        pdf = folder / 'review.pdf'
        preview = folder / 'preview'
        sequence = [('review_render', [h.CODE_ROOT / 'scripts/render_check.py', folder / 'template.hwpx',
                                      '--reference', folder / 'original.hwpx', '--keep-pdf', pdf]),
                    ('review_images', [h.CODE_ROOT / 'scripts/hwpdoc_preview.py', '--pdf', pdf, '--output-dir', preview])]
        for name, argv in sequence:
            previous = r['stages'].get(name, {})
            if previous.get('failures', 0) >= 2:
                raise ValueError(name + ': 동일 단계 2회 실패. 자동 시도 중단')
            code, output = h.run(argv, com=name == 'review_render')
            r['stages'][name] = dict(status='pass' if code == 0 else ('unconfirmed' if code in (3, 124, 125) else 'fail'),
                                     exit_code=code, reason=output, at=h.now(), failures=previous.get('failures', 0) + bool(code))
            h.write_json(folder / 'registration.json', r)
            h.audit('template_' + name, folder, r['stages'][name]['status'], output[:1000])
            if code:
                return r
        artifacts = h.read_json(preview / 'preview.json')
        review['visual'] = {'record': '', 'document_sha256': r['hashes']['template.hwpx'],
                            'pdf': artifacts['pdf'], 'images': artifacts['images']}
    h.write_json(target, review)
    return dict(r, review_draft=str(target), next_action='양식·매핑·용도와 필요한 PNG를 실제 확인한 후 기록을 완성하여 --review로 제출하세요')


def _add_template(args, folder):
    record = folder / 'registration.json'
    if args.source:
        if record.exists() or (folder / 'original.hwpx').exists():
            raise ValueError('기존 등록을 덮어쓰지 않습니다. 새 version을 사용하세요')
        source = h.input_path(args.source)
        if source.suffix.lower() != '.hwpx' or not source.is_file():
            raise ValueError('양식 등록은 HWPX만 지원합니다. HWP는 원본 보존 후 한글에서 HWPX 사본으로 저장하세요')
        slots = extracted(source)  # Invalid packages leave no orphaned original copy.
        digest = h.sha(source)
        shutil.copy2(source, folder / 'original.hwpx')
        if h.sha(folder / 'original.hwpx') != digest:
            raise ValueError('원본 사본 해시 불일치')
        slots['source'] = 'original.hwpx'
        h.write_json(folder / 'slots.raw.json', slots)
        r = dict(version=REGISTRY_VERSION, id=args.id, template_version=args.version,
                 status='draft', purposes=args.purpose or [], provenance=args.provenance,
                 source={'origin': str(source), 'sha256': digest, 'imported_at': h.now()},
                 stages={}, created_at=h.now(), next_action='slots.raw.json의 주소를 확인하고 의미→슬롯 mapping.json을 제출하세요')
        h.write_json(record, r)
        h.audit('template_draft', record, 'unconfirmed', '원본 사본/슬롯 추출; 의미와 승인은 자동 생성하지 않음')
        return r
    if not record.is_file():
        raise ValueError('--source로 등록 초안을 먼저 만드세요')
    r = h.read_json(record)
    if r['status'] == 'registered':
        raise ValueError('등록 완료 양식은 새 version으로 수정하세요')
    if h.sha(folder / 'original.hwpx') != r['source']['sha256']:
        raise ValueError('원본 사본이 변경됐습니다. 새 등록이 필요합니다')
    if getattr(args, 'review_draft', False):
        return prepare_review(folder, r)
    if args.mapping:
        if r['status'] == 'awaiting_review':
            raise ValueError('검토 대상 변경은 새 version으로 등록하세요')
        mapping = h.read_json(h.input_path(args.mapping))
        keys = {s['key'] for s in extracted(folder / 'original.hwpx')['slots']}
        if not isinstance(mapping, dict) or not mapping or any(not k or not isinstance(v, str) or v not in keys for k, v in mapping.items()):
            raise ValueError('의미→슬롯 매핑은 실제 추출 주소를 가리켜야 합니다')
        if len(set(mapping.values())) != len(mapping):
            raise ValueError('하나의 슬롯에 중복 의미를 매핑할 수 없습니다')
        if not r['purposes']:
            raise ValueError('지원 용도 누락: 새 등록 초안에 --purpose를 지정하세요')
        h.write_json(folder / 'mapping.json', mapping)
        work = folder / 'template.hwpx'
        shutil.copy2(folder / 'original.hwpx', work)
        sequence = [('structure', [h.SKILL / 'validate.py', work]),
                    ('namespaces', [h.SKILL / 'fix_namespaces.py', work]),
                    ('finalize', [h.SKILL / 'finalize_hwpx.py', work, '--strip-linesegarray']),
                    ('layout', [h.SKILL / 'validate.py', work, '--layout']),
                    ('profiles', [h.SKILL / 'page_guard.py', '--reference', work, '--write-budget', folder / 'budget.json', '--write-structure', folder / 'structure.json']),
                    ('hancom', [h.SKILL / 'finalize_hwpx.py', work, '--hancom'])]
        for name, argv in sequence:
            previous = r['stages'].get(name, {})
            if previous.get('failures', 0) >= 2:
                raise ValueError(name + ': 동일 단계 2회 실패. 자동 시도 중단; 사람 확인 필요')
            code, output = h.run(argv, com=name == 'hancom')
            r['stages'][name] = dict(status='pass' if code == 0 else ('unconfirmed' if code in (3, 124, 125) else 'fail'),
                                     exit_code=code, reason=output, at=h.now(), failures=previous.get('failures', 0) + bool(code))
            h.write_json(record, r)
            h.audit('template_' + name, work, r['stages'][name]['status'], output[:1000])
            if code:
                return r
        h.write_json(folder / 'slots.json', extracted(work))
        r.update(status='awaiting_review', hashes=file_hashes(folder),
                 next_action='양식·의미·용도 확인 후 현재 해시에 연결된 review.json 제출; 필요한 PDF/PNG 판독 기록 포함')
        h.write_json(record, r)
        return r
    if args.review:
        if r['status'] != 'awaiting_review' or r['hashes'] != file_hashes(folder):
            raise ValueError('검토 대상이 준비되지 않았거나 변경됐습니다')
        review = h.read_json(h.input_path(args.review))
        issues = review_errors(r, review)
        if issues:
            raise ValueError('; '.join(issues))
        h.write_json(folder / 'review.json', review)
        r.update(status='registered', review_sha256=h.sha(folder / 'review.json'), registered_at=h.now(), next_action='prepare로 문서 작업 시작')
        h.write_json(record, r)
        h.audit('template_register', record, 'pass', '제공된 사람 확인 기록 수리; 실제 확인 행위의 진위는 자동 보증하지 않음')
        return r
    return r


def migrate_legacy(version='legacy-1'):
    """Import immutable registration drafts; activation still requires real review."""
    results = []
    for name in h.TEMPLATES:
        source = h.ROOT / 'knowledge/templates' / name
        if not (source / '양식.hwpx').is_file():
            results.append({'id': name, 'status': 'missing'}); continue
        folder = h.workspace_path(Path('.hwpdoc/migration') / name)
        files = {p.name: h.sha(p) for p in source.iterdir() if p.is_file()}
        if (folder / 'inventory.json').exists():
            record = h.read_json(folder / 'inventory.json')
            if record['files'] != files:
                results.append({'id': name, 'status': 'source_changed', 'next_action': '이관 조사 후 원본 변경. 기존 기록을 덮어쓰지 않고 새 등록 version으로 확인하세요'})
                continue
        else:
            folder.mkdir(parents=True, exist_ok=True)
            h.write_json(folder / 'slots.extracted.json', extracted(source / '양식.hwpx'))
            record = dict(id=name, status='human_review_pending', existing_path=source.relative_to(h.ROOT).as_posix(),
                          files=files, purposes_proposed=[name], source_readme=(source / 'README.md').read_text(encoding='utf-8'),
                          at=h.now(), next_action='실제 파일·출처·의미 매핑·용도 확인 후 add-template으로 이관; 기존 선택 경로 유지')
            h.write_json(folder / 'inventory.json', record)
        registration = folder_for(name, version)
        if not (registration / 'registration.json').exists():
            args = SimpleNamespace(id=name, version=version, source=str(source / '양식.hwpx'), purpose=[name], provenance='unconfirmed')
            add_template(args)
            # Preserve historical profiles as evidence, never as freshly validated profiles.
            archive = registration / 'legacy'; archive.mkdir(exist_ok=True)
            for filename in ('slots.json', 'budget.json', 'structure.json', 'README.md'):
                if (source / filename).is_file():
                    target = archive / filename
                    shutil.copy2(source / filename, target)
                    if h.sha(target) != files[filename]:
                        raise ValueError('이관 사본 해시 불일치: ' + filename)
            raw = h.read_json(registration / 'slots.raw.json')
            h.write_json(registration / 'mapping.proposed.json', {slot['key']: slot['key'] for slot in raw['slots']})
            h.write_json(registration / 'legacy-import.json', {'version': 1, 'inventory': h.path_context().encode(folder / 'inventory.json'),
                                                            'inventory_sha256': h.sha(folder / 'inventory.json'), 'files': files})
        existing = h.read_json(registration / 'registration.json')
        if existing.get('source', {}).get('sha256') != files['양식.hwpx']:
            raise ValueError('해당 이관 version은 다른 원본을 가리킵니다: ' + name)
        record = dict(record, registration=registration.relative_to(h.ROOT).as_posix(), registration_status=existing['status'])
        results.append(record)
    h.audit('template_migration_inventory', h.ROOT / '.hwpdoc/migration', 'unconfirmed', '기존 5종 등록 초안 수집; 사람 등록 확인 미완료')
    return [{key: x[key] for key in ('id', 'status', 'registration', 'registration_status', 'next_action') if key in x} for x in results]
