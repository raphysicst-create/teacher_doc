"""Initialization and mechanical preparation for the shared workflow CLI."""
from __future__ import annotations

import argparse
import copy
import hashlib
from datetime import date, datetime, timezone
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zlib

import hwpdoc as h
from hwpdoc_config import MARKER, reject_broken_text


WORKSPACE_DIRS = ('.hwpdoc/jobs', '.hwpdoc/templates', 'knowledge/reference',
                  'knowledge/examples/md', 'output', 'logs', 'tmp')

NEIS_CANDIDATE = re.compile(r'neis:([A-Za-z0-9_-]{1,40}):([A-Za-z0-9_-]{1,40})')
SCHOOL_LEVELS = ('elementary', 'middle', 'high', 'special')


def validate_cli_text(args):
    # Run before dispatch/configuration/locks, including commands that audit failures.
    fields = {
        'approve': ('by', 'record'),
        'review': ('by', 'record'),
        'checklist': ('value',),
        'init': ('school', 'prefix', 'skill_name'),
        'school': ('region',),
        'prepare': ('document_type',),
        'resume': ('record',),
    }
    for field in fields.get(args.command, ()):
        value = getattr(args, field, None)
        for text in value if isinstance(value, list) else (value,):
            reject_broken_text(text, f'{args.command} --{field.replace("_", "-")}')


def workspace_settings():
    """Read current settings under the caller's lock, never write legacy defaults."""
    marker = h.workspace_path(MARKER)
    settings = h.read_json(marker)
    if not isinstance(settings, dict) or settings.get('kind') != 'hwpdoc-workspace' or settings.get('version') != 1:
        raise ValueError('유효한 .hwpdoc/workspace.json이 필요합니다. init을 먼저 실행하세요')
    for key in ('school', 'connections'):
        if key in settings and not isinstance(settings[key], dict):
            raise ValueError('작업 설정은 JSON 객체여야 합니다: ' + key)
    return marker, settings


def school(args):
    if args.set_neis is not None:
        match = NEIS_CANDIDATE.fullmatch(args.set_neis)
        if not match:
            raise ValueError('candidateId 형식: neis:<교육청코드>:<학교코드> (각 1~40자 영숫자/_/-)')
        if args.level not in SCHOOL_LEVELS:
            raise ValueError('--set-neis에는 --level이 필요합니다')
        if args.region is not None and (not args.region.strip() or len(args.region) > 200):
            raise ValueError('--region은 공백이 아닌 1~200자 문자열이어야 합니다')
    elif args.level or args.region is not None:
        raise ValueError('--level/--region은 --set-neis와 함께만 사용하세요')
    with h.lock(h.workspace_path('.hwpdoc/settings.lock')):
        marker, settings = workspace_settings()
        saved = settings.get('school', {}).get('neis')
        status = 'stored' if saved else 'not_configured'
        if args.set_neis is not None:
            value = dict(candidateId=args.set_neis, educationOfficeCode=match[1], schoolCode=match[2],
                         schoolLevel=args.level, region=args.region)
            if isinstance(saved, dict) and all(saved.get(k) == v for k, v in value.items()):
                status = 'unchanged'
            else:
                saved = dict(value, confirmed_at=h.now())
                settings.setdefault('school', {})['neis'] = saved
                h.write_json(marker, settings)
                h.configure(h.ROOT)
                h.audit('school', marker, 'pass', {'candidateId': args.set_neis})
                status = 'stored'
    selection = ({'method': 'stored_setting', 'candidateId': saved['candidateId'],
                  'settingRef': '.hwpdoc/workspace.json#school.neis'} if saved else None)
    return {'status': status, 'neis': saved, 'selection': selection}


def check_init_paths(root):
    """Diagnose classic Windows path limits before any workspace writes.

    Python long-path support does not establish support in Hancom or other hosts.
    Keep initialization within the classic directory (248) / file (260) limits.
    """
    if os.name != 'nt':
        return
    paths = [(root / p, 248) for p in WORKSPACE_DIRS]
    paths += [(root / p, 260) for p in (MARKER, 'CLAUDE.md', 'AGENTS.md',
                                      '.hwpdoc/instructions-to-merge.md', 'logs/audit.jsonl')]
    for path, limit in paths:
        length = len(str(path).encode('utf-16-le')) // 2
        if length >= limit or any(len(p.encode('utf-16-le')) // 2 > 255 for p in path.parts):
            raise ValueError(f'작업 경로가 Windows 지원 범위를 초과합니다: {length}자, '
                             f'초기화 대상은 {limit}자 미만이어야 합니다. 더 짧은 상위 경로/폴더명을 '
                             f'선택하세요. 파일 생성 전 중단했습니다: {path}')


def instruction_text(app, skill):
    return (f'# 공문 작업 폴더 ({app})\n\n'
            f'공문 작업을 시작할 때 이 앱에서 확인한 `{skill}` 스킬의 SKILL.md 본문을 읽고, '
            '연결된 `references/workflow.md` 업무 절차를 읽는다. 목록 노출만으로 읽었다고 하지 않는다.\n\n'
            '학교 설정은 `.hwpdoc/workspace.json`이다. 새 대화에서는 `.hwpdoc/onboarding.json`의 실제 '
            '`pc_data`와 `python`을 먼저 읽고, 해당 `runtime.json`과 실행 파일의 존재·일치를 확인한다. '
            '기록이 없거나 경로가 이동/소실됐으면 진단하고 기본 경로로 바꾸거나 재설치하지 않는다. '
            '그 Python과 실제 로드된 플러그인의 `scripts/teacher_doc.py`에 이 작업 폴더를 '
            '`--workspace`로 전달한다. 환경변수 없이도 실행기는 설치 기록을 복원한다.\n\n'
            '원본은 보존하고 새 파일을 만든다. 미확인 값·승인·육안 판독을 만들어 넣지 않는다. '
            '실제 사용자 확인 후 생성하고, 결과와 보고서는 output에 저장한다. 검증 실패를 통과로 바꾸지 않는다. '
            '최종 사람 검토와 사람 발송을 유지한다. 발송 전 한글로 열어 확인해주세요.\n')


def init_workspace(args):
    root = Path(args.path).resolve()
    if root in (h.CODE_ROOT, h.CODE_ROOT.parent):
        raise ValueError('기존 프로젝트/부모 fallback 지침에 새 안내문을 만들지 않습니다. 별도 작업 폴더를 선택하세요')
    check_init_paths(root)
    marker = root / MARKER
    if marker.exists():
        raise ValueError('기존 작업 설정을 덮어쓰지 않습니다')
    instruction = root / ('CLAUDE.md' if args.app == 'claude' else 'AGENTS.md')
    target = root / '.hwpdoc/instructions-to-merge.md' if instruction.exists() else instruction
    if target.exists():
        raise ValueError('이전 안내 제안을 덮어쓰지 않습니다: ' + str(target))
    for relative in WORKSPACE_DIRS:
        (root / relative).mkdir(parents=True, exist_ok=True)
    settings = dict(kind='hwpdoc-workspace', version=1, app=args.app, skill_name=args.skill_name,
                    school={'name': args.school, 'document_prefix': args.prefix, 'academic_year': args.year},
                    delivery={'external_copy': str(Path(args.copy_to).resolve()) if args.copy_to else None},
                    references={}, timetable_mapping={}, preferences={},
                    connections={'kordoc': 'unconfirmed'})
    h.write_json(marker, settings)
    text = instruction_text(args.app, args.skill_name)
    if instruction.exists():
        target = root / '.hwpdoc/instructions-to-merge.md'
        mode = 'existing_instructions_preserved'
    else:
        target, mode = instruction, 'created'
    with target.open('x', encoding='utf-8') as stream:
        stream.write(text)
    h.configure(root)
    h.audit('init', marker, 'pass', {'app': args.app, 'instructions': mode, 'actual_skill_loaded': 'unverified'})
    return {'status': 'initialized', 'workspace': str(root), 'instructions': str(target), 'mode': mode,
            'hooks': 'unregistered', 'actual_skill_loaded': 'unverified',
            'next_action': 'doctor 실행; 앱 스킬 본문 실제 로딩 및 훅 등록·신뢰·차단을 별도 확인하세요'}


# Only preparation records belong here. Workflow receipts and editing decisions
# must continue through their existing commands, including nested/dotted attempts.
EVIDENCE_RETIRED = ('업무 근거 기록은 2026. 11. 4. 폐지됐습니다. '
                    '값·판단 미확인이면 kind: facts로 기록하세요')
RECORD_FORBIDDEN = {
    'evidence': EVIDENCE_RETIRED,
    'draft_approval': 'approve --job <이름>',
    'slots': 'checklist --job <이름> --apply',
    'kept_slots': 'checklist --job <이름> --apply',
    'checklist': 'checklist --job <이름> --apply',
    'preparation_tasks': 'prepare가 생성하고 check가 완료 근거를 계산합니다',
    'base': 'prepare --base',
    'job_id': 'prepare --job 또는 revise --job … --new-job …',
    'version': 'prepare',
    'unresolved': '추가는 unresolved_add, 기존 항목은 원문/교사 답을 확인한 뒤 revise로 검토하세요',
}
RECORD_SCHEMA = {
    'sources': [{'path': str, 'sha256': str}],
    'draft': {'path': str, 'sha256': str, 'created_at': str},
    'exploration': {'record': str},
    'reuse_review': {'record': str, 'names': [str], 'dates': [str],
                     'names_empty_reason': str, 'dates_empty_reason': str},
    'content_rules': {key: [str] for key in ('require', 'forbid', 'require_regex', 'forbid_regex', 'placeholder_regex')},
    'checks': {key: {'applicable': bool, 'reason': str, 'reference_setting': str, **fields}
               for key, fields in (
                   ('budget_names', {'names': [str]}), ('related', {'numbers': [str]}),
                   ('timetable', {'dates': [str], 'periods': str, 'grades': str}))},
    'attachments': [{'path': str, 'title': str, 'sha256': str}],
    'attachment_mentions': [str],
    'received': {key: str for key in ('summary', 'requirements', 'deadline', 'submission_method',
                                     'document_number', 'issue_date', 'source_quote')},
    'reference': str, 'reference_sha256': str,
    'activities': [{'location': str, 'items': [str], 'slot_keys': [str]}],
    'over_budget_cells': [str], 'visual_review_record': str,
    'unresolved_add': None,  # Explicit fact/validation records validated below.
}


def record_shape(value, schema, field=''):
    if isinstance(schema, dict):
        if not isinstance(value, dict):
            raise ValueError(f'{field or "record"}: JSON 객체가 필요합니다')
        for key, item in value.items():
            name = f'{field}.{key}' if field else key
            if not field and key.split('.')[0] in RECORD_FORBIDDEN:
                raise ValueError(f'{name}: record 등록 금지. ' + RECORD_FORBIDDEN[key.split('.')[0]])
            if key not in schema:
                raise ValueError('모르는 등록 키: ' + name)
            record_shape(item, schema[key], name)
    elif isinstance(schema, list):
        if not isinstance(value, list):
            raise ValueError(field + ': 배열이 필요합니다')
        for index, item in enumerate(value):
            record_shape(item, schema[0], f'{field}[{index}]')
    elif schema is not None and type(value) is not schema:
        raise ValueError(field + ': 형식 오류 (' + schema.__name__ + ')')


def record_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('중복 JSON 키: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('JSON에서 허용하지 않는 값: ' + value)
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)


def record_path(value, field, *, existing=True):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ': 파일 경로가 필요합니다')
    raw = Path(value)
    # Drive-relative paths (C:foo) depend on a per-drive cwd; never accept them.
    if raw.drive and not raw.is_absolute():
        raise ValueError(field + ': 드라이브 상대경로는 사용할 수 없습니다')
    path = h.input_path(value)
    if not path.is_relative_to(h.ROOT.resolve()):
        raise ValueError(field + ': 작업 폴더 밖 경로는 등록할 수 없습니다')
    relative = path.relative_to(h.ROOT.resolve()).as_posix()
    path = h.workspace_path(relative)  # Also enforce the existing junction/path contract.
    if existing and not path.is_file():
        raise ValueError(field + ': 파일 없음: ' + relative)
    return relative, path


def record_write(path, value):
    """Validate/serialize before touching disk; failed writes preserve old bytes."""
    serialized = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    json.loads(serialized)
    record_bytes(path, serialized.encode('utf-8'))


def record_bytes(path, content):
    """Atomically replace one registered file, including UTF-8 draft bytes."""
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent,
                                         prefix=path.stem + '.', suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def record_summary(value):
    # Never echo draft text, evidence prose, teacher names or long array contents.
    if isinstance(value, dict):
        return f'객체 {len(value)}개 키 ({h.json_hash(value)[:12]})'
    if isinstance(value, list):
        return f'배열 {len(value)}건 ({h.json_hash(value)[:12]})'
    if isinstance(value, str):
        return f'문자열 {len(value)}자'
    return '없음' if value is None else str(value)


def record_changes(before, after, job):
    """Shared registration boundary; call before writing any proposed file."""
    changed = [key for key in after if before.get(key) != after[key] or key not in before]
    approval = before.get('draft_approval')
    if (isinstance(approval, dict) and any(approval.values())
            and h.json_hash(h.approval_payload(before)) != h.json_hash(h.approval_payload(after))):
        raise ValueError('승인 입력 해시가 바뀌므로 등록을 거부합니다. revise --job ' + job
                         + ' --new-job <새 이름>으로 준비한 뒤 초안을 다시 확인받으세요')
    if changed and (h.job_dir(job) / 'report.json').exists():
        raise ValueError('보고서가 있는 작업은 변경하지 않습니다. revise --job ' + job + ' --new-job <새 이름>을 사용하세요')
    changes = {key: dict(before=record_summary(before.get(key)), after=record_summary(after[key])) for key in changed}
    return dict(changed_fields=changed, changes=changes,
                before_sha256=h.json_hash(before), after_sha256=h.json_hash(after))


def record(args):
    h.job_dir(args.job)
    manifest = h.workspace_path(Path('.hwpdoc/prepared') / args.job / 'manifest.json')
    try:
        _, input_file = record_path(args.file, '--file')
        update = record_json(input_file)
        record_shape(update, RECORD_SCHEMA)
        # An ANSI-saved file turns Hangul into '?'; three in a row is not prose.
        def strings(value, field):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield from strings(item, f'{field}.{key}' if field else key)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    yield from strings(item, f'{field}[{index}]')
            elif isinstance(value, str):
                yield field, value
        for field, text in strings(update, ''):
            reject_broken_text(text, field, guidance=(
                '등록 파일을 UTF-8로 다시 저장하세요 '
                '(PowerShell 5.1의 Set-Content·> 기본 인코딩은 한글을 ?로 바꿉니다)'))
        with h.lock(h.job_dir(args.job) / '.lock'):
            before = record_json(manifest)
            if not isinstance(before, dict) or before.get('job_id') != args.job:
                raise ValueError('manifest 객체/job_id 불일치')
            after = copy.deepcopy(before)

            def merge(target, patch):
                for key, value in patch.items():
                    if isinstance(value, dict):
                        if not isinstance(target.get(key), dict):
                            target[key] = {}
                        merge(target[key], value)
                    else:
                        target[key] = copy.deepcopy(value)
            merge(after, {k: v for k, v in update.items() if k != 'unresolved_add'})

            def file_hash(item, patch, path_key, hash_key, field):
                relative, path = record_path(item.get(path_key), field + path_key)
                digest = h.sha(path)
                if hash_key in patch and patch[hash_key] != digest:
                    raise ValueError(field + hash_key + ': 실제 파일 SHA256 불일치')
                item.update({path_key: relative, hash_key: digest})

            for key in ('sources', 'attachments'):
                if key in update:
                    for index, item in enumerate(after[key]):
                        file_hash(item, update[key][index], 'path', 'sha256', f'{key}[{index}].')
            if 'draft' in update:
                file_hash(after['draft'], update['draft'], 'path', 'sha256', 'draft.')
                if 'created_at' not in update['draft']:
                    after['draft']['created_at'] = h.now()
                h.zoned_time(after['draft']['created_at'])
            if 'reference' in update or 'reference_sha256' in update:
                file_hash(after, update, 'reference', 'reference_sha256', '')
            if 'visual_review_record' in update:
                after['visual_review_record'], _ = record_path(update['visual_review_record'], 'visual_review_record', existing=False)
            if 'unresolved_add' in update:
                items = update['unresolved_add']
                if not isinstance(items, list):
                    raise ValueError('unresolved_add: 실제 미확인 사항 배열이 필요합니다')
                from hwpdoc_pending import TASK_FIELDS, APPROVAL, DECISIONS, SLOT_PREFIX
                for item in items:
                    if isinstance(item, dict):
                        record_shape(item, {'kind': str, 'text': str, 'stages': [str]}, 'unresolved_add[]')
                        text = item.get('text')
                        kind = item.get('kind')
                        if kind == 'evidence':
                            raise ValueError('unresolved_add: ' + EVIDENCE_RETIRED)
                        if kind not in ('facts', 'validation'):
                            raise ValueError('unresolved_add: kind는 facts/validation만 허용합니다')
                        if kind == 'validation' and (not item.get('stages') or any(s not in h.STAGES for s in item['stages'])):
                            raise ValueError('unresolved_add: 실제 검증 단계 stages가 필요합니다')
                        if kind != 'validation' and 'stages' in item:
                            raise ValueError('unresolved_add: stages는 validation에서만 허용합니다')
                    else:
                        text = item
                    if (not isinstance(text, str) or not text.strip() or text in (*TASK_FIELDS, APPROVAL, DECISIONS)
                            or text.startswith(SLOT_PREFIX)):
                        raise ValueError('unresolved_add: 준비 안내 대신 실제 미확인 사항만 추가하세요')
                if not isinstance(after.get('unresolved'), list):
                    raise ValueError('manifest.unresolved는 배열이어야 합니다')
                after['unresolved'].extend(copy.deepcopy(items))
            detail = record_changes(before, after, args.job)
            changed, changes = detail['changed_fields'], detail['changes']
            if changed:
                record_write(manifest, after)
            h.audit('record', manifest, 'pass', detail)
        return dict(status='recorded' if changed else 'unchanged', job_id=args.job, manifest=str(manifest),
                    changed_fields=changed, changes=changes, next_action=f'다음: check --job {args.job}')
    except (ValueError, OSError, TypeError, RuntimeError) as exc:
        h.audit('record', manifest, 'fail', {'error': str(exc)})
        raise


def draft(args):
    """Register text from the disposable preapproval edit; never a build input."""
    h.job_dir(args.job)
    manifest = h.workspace_path(Path('.hwpdoc/prepared') / args.job / 'manifest.json')
    try:
        with h.lock(h.job_dir(args.job) / '.lock'):
            before = record_json(manifest)
            if not isinstance(before, dict) or before.get('job_id') != args.job:
                raise ValueError('manifest 객체/job_id 불일치')
            checklist = before.get('checklist')
            slots = before.get('slots')
            if (not isinstance(checklist, dict) or not checklist
                    or checklist.get('applied', True) is not True
                    or not isinstance(slots, dict)
                    or not (slots.get('values') or before.get('kept_slots'))):
                raise ValueError(f'적용된 확인표의 확정 값이 필요합니다. checklist --job {args.job} --apply로 먼저 적용하세요')
            detail, texts = {}, []
            def extract(path, folder):
                from text_extract import extract_markdown
                texts.append(extract_markdown(path))
            issues, _, _ = h.build_inputs(before, content_detail=detail, inspect=extract)
            # Content findings are review material, never an approval waiver.
            blocked = h.blocking_issues([i for i in issues if not i.get('content_check')])
            if blocked or not texts:
                raise ValueError('초안 임시 편집 실패. check --job ' + args.job + '로 확인하세요. '
                                 + '; '.join(i['field'] + ': ' + i['problem'] for i in blocked))
            text = '확인용 초안 — 승인 전, 실제 파일 생성 아님\n\n' + texts[0] + '\n'
            content = text.encode('utf-8')
            digest = hashlib.sha256(content).hexdigest()
            relative, path = record_path(str(manifest.with_name('초안.md')), 'draft.path', existing=False)
            previous = path.read_bytes() if path.exists() else None
            old = before.get('draft')
            old = old if isinstance(old, dict) else {}
            receipt = dict(path=relative, sha256=digest, created_at=old.get('created_at'))
            if old.get('path') != relative or old.get('sha256') != digest or not receipt['created_at']:
                receipt['created_at'] = h.now()
            h.zoned_time(receipt['created_at'])
            after = copy.deepcopy(before)
            after['draft'] = receipt
            changes = record_changes(before, after, args.job)
            changed = bool(changes['changed_fields']) or previous != content
            if changed and (h.job_dir(args.job) / 'report.json').exists():
                raise ValueError(f'보고서가 있는 작업은 변경하지 않습니다. revise --job {args.job} --new-job <새 이름>을 사용하세요')
            if changed:
                if previous != content:
                    record_bytes(path, content)
                try:
                    if changes['changed_fields']:
                        record_write(manifest, after)
                except OSError:
                    if previous != content:
                        if previous is None:
                            path.unlink()
                        else:
                            record_bytes(path, previous)
                    raise
            from hwpdoc_content_check import summary
            counts = summary(detail)
            h.audit('draft', manifest, 'pass', dict(changes, draft=receipt, characters=len(text),
                                                   content_check=counts, unchanged=not changed))
        return dict(status='drafted' if changed else 'unchanged', job_id=args.job,
                    draft_path=str(path), characters=len(text), content_check=counts,
                    next_action=f'다음: check --job {args.job}. 교사에게 초안을 보여주고 답을 approve로 기록하세요.')
    except (ValueError, OSError, TypeError, RuntimeError, KeyError) as exc:
        h.audit('draft', manifest, 'fail', {'error': str(exc)})
        raise


def prepare(args):
    from hwpdoc_pending import preparation_task
    from hwpdoc_templates import extracted
    h.job_dir(args.job)  # identifier validation, no file creation
    folder = h.workspace_path(Path('.hwpdoc/prepared') / args.job)
    if folder.exists():
        raise ValueError('기존 준비 입력을 덮어쓰지 않습니다. 새 job 식별자를 사용하세요')
    if not getattr(args, 'base', None):
        raise ValueError('--base <작년.hwpx>가 필요합니다')
    base_source = h.original_input_path(args.base)
    if base_source.suffix.lower() != '.hwpx' or not base_source.is_file():
        raise ValueError('베이스는 HWPX만 받습니다. .hwp는 먼저 한글 COM(Windows + 한글) 또는 kordoc으로 HWPX 사본을 만든 뒤 그 사본을 --base로 주세요. 원본은 보존합니다')
    source_files = [h.original_input_path(s) for s in args.source]
    if any(not p.is_file() for p in source_files):
        raise ValueError('원문 경로를 확인하세요')
    supplied = h.read_json(h.input_path(args.values)) if args.values else {}
    if not isinstance(supplied, dict) or any(not isinstance(v, str) for v in supplied.values()):
        raise ValueError('--values는 의미/슬롯→문자열 JSON이어야 합니다')
    values = supplied
    folder.mkdir(parents=True)
    base = folder / 'base.hwpx'
    digest = h.sha(base_source)
    shutil.copy2(base_source, base)
    if h.sha(base) != digest:
        raise ValueError('원본 사본 해시 불일치')
    base_record = dict(path=base.relative_to(h.ROOT).as_posix(), sha256=digest,
                       origin=str(base_source), imported_at=h.now())
    slots = extracted(base)
    if set(values) - {s['key'] for s in slots['slots']}:
        raise ValueError('추출되지 않은 슬롯 주소')
    sources = [base_record]
    for src in source_files:
        digest = h.sha(src)
        dest = folder / 'sources' / (digest[:12] + '-' + src.name)
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(src, dest)
        if h.sha(dest) != digest:
            raise ValueError('원문 가져오기 해시 불일치')
        sources.append({'path': dest.relative_to(h.ROOT).as_posix(), 'sha256': digest,
                        'origin': str(src), 'imported_at': h.now()})
    h.write_json(folder / 'slots.extracted.json', slots)
    # 레퍼런스 자료(예산·관련번호·시간표)가 작업 설정에 없으면 해당 조회는 적용 불가로 미리 채운다.
    references = h.CONTEXT.settings.get('references', {}) or {}
    checks = {}
    for key, reference in (('budget_names', 'budget'), ('related', 'related'), ('timetable', 'timetable')):
        if references.get(reference):
            checks[key] = {'applicable': None, 'reason': '', 'reference_setting': 'references.' + reference}
        else:
            checks[key] = {'applicable': False, 'reason': f'작업 설정에 references.{reference} 자료 없음',
                           'reference_setting': 'references.' + reference}
    agent_tasks = ['받은 원문에서 확실한 날짜·장소·업무 사실 추출 및 초안 문안 준비']
    if any(check['applicable'] is None for check in checks.values()):
        agent_tasks.append('예산명·관련번호·시간표 적용 여부(무관하면 이유 기록)')
    agent_tasks += ['복사 잔재 이름·날짜와 forbid', '붙임 목록·미확인 사항 검토']
    if slots:
        # Explicit empty strings can mean intentional blanks; only absent keys
        # need a decision. Base slots have addresses, not approved meanings.
        agent_tasks += ['원문/설정에서 먼저 찾을 값: ' + s['key'] + ' (의미 확인 필요; 기존 문구: '
                    + str(s.get('text', s.get('preview', '')))[:100] + ')'
                    for s in slots['slots'] if s['key'] not in values]
    user_decisions = ['제시한 초안 문안의 파일 생성 확인', '원문/설정에서 찾지 못하거나 서로 충돌하는 사실·선택만 질문']
    missing = agent_tasks + user_decisions
    m = dict(version=2, job_id=args.job, workflow=args.workflow, document_type=args.document_type,
             shared_values={}, sources=sources,
             attachments=[], attachment_mentions=None,
             draft={'path': '', 'sha256': '', 'created_at': ''},
             draft_approval={'confirmed': False, 'by': '', 'at': '', 'record': '', 'input_sha256': ''},
             content_rules={'forbid': []},
             reuse_review={'record': '', 'names': None, 'dates': None, 'names_empty_reason': '', 'dates_empty_reason': ''},
             checks=checks,
             environment={'app': h.CONTEXT.settings.get('app', 'unconfirmed'), 'python': sys.version.split()[0],
                          'kordoc': 'unconfirmed'},
             unresolved=[], base_provenance='unconfirmed',
             exploration={'record': f'미등록 일회성 베이스 {base_source} (sha256 {base_record["sha256"][:12]})'})
    m['slots'] = {'template_sha256': h.sha(base), 'values': values}
    m['kept_slots'] = []
    m.update(base=dict(base_record, kind='unregistered_one_off'),
             reference=base_record['path'], reference_sha256=base_record['sha256'])
    if args.workflow == 'W2':
        m['received'] = dict(submission_method=None, summary='', requirements='', deadline='',
                             document_number='', issue_date='', source_quote='')
        agent_tasks.append('수신 원문에서 제출 방법·기한·문서번호·시행일을 먼저 추출; 제출 방법이 없을 때만 질문')
    m['preparation_tasks'] = []
    for text in agent_tasks + user_decisions:
        slot = None
        if text.startswith('원문/설정에서 먼저 찾을 값: '):
            slot = text[len('원문/설정에서 먼저 찾을 값: '):].split(' ', 1)[0]
        m['preparation_tasks'].append(preparation_task(text, slot))
    h.write_json(folder / 'manifest.json', m)
    base_notice = '미등록 일회성 베이스입니다. 재사용 양식 등록·사람 양식 검토를 수행한 기록이 아닙니다.'
    (folder / '확인할사항.md').write_text(base_notice + '\n\n'
        + '# 에이전트 작업 목록 (교사에게 그대로 질문하지 않음)\n\n' + '\n'.join('- ' + x for x in agent_tasks)
        + '\n\n## 사용자 결정\n\n' + '\n'.join('- ' + x for x in user_decisions)
        + '\n\n## build 입력 계약 (manifest 경로·의미·형식·해시 대상)\n\n'
        + '빈 값·null은 미확인입니다. 실제 근거·확인 없이 채우지 마세요.\n'
        + '교사 확인 후 항목은 초안을 제시하고 실제 확인받은 뒤 기록합니다. '
          '나머지 입력을 먼저 완성한 뒤 승인하며, 승인 후 입력이 바뀌면 다시 확인받습니다.\n\n'
        + '\n'.join(f'- `{field}`: {description}' for field, description in h.MANIFEST_GUIDANCE.items())
        + f'\n\n다음: `check --job {args.job}`로 남은 항목 확인. ready는 build 사전 점검만 뜻하며 전체 검증·전달 승인이 아닙니다.\n'
        + '\n\n기계적으로 수집한 준비 입력입니다. 승인·육안 판독을 자동 작성하지 않았습니다.\n', encoding='utf-8')
    h.audit('prepare', folder, 'unconfirmed', missing)
    result = {'status': 'unconfirmed', 'manifest': str(folder / 'manifest.json'), 'missing': agent_tasks + user_decisions,
            'missing_by_owner': {'agent_review': agent_tasks, 'user_decisions': user_decisions},
            'next_action': f'다음: check --job {args.job}로 남은 항목 확인. 원문·설정에서 확인 가능한 사실은 먼저 읽으세요. 남은 결정만 질문하고 문안 제시 후 실제 파일 생성 확인을 기록하세요'}
    result.update(base=m['base'], base_notice=base_notice)
    result['details_path'] = str(folder / 'prepare-details.json')
    h.write_json(result['details_path'], result)
    return result


YEAR = re.compile(r'(?<![\d,])(?:19|20)\d{2}(?![\d,]|\s*(?:원|명|회|시간))')
CONTEXT_YEAR = re.compile(r'(?<![\w.-])(?P<year>(?:19|20)\d{2})\s*(?P<kind>학년도|년)')
ISO_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
CHECKLIST_HEADER = ['번호', '위치', '작년 값', '제안', '제안 근거', '확정 값']


def checklist_date(text):
    from value_guard import DATE
    return re.search(r'\d{4}([/-])\d{1,2}\1\d{1,2}(?!\d)|' + DATE.pattern, text)


DATE_MENTION = re.compile(r'(?<!\d)(?:(?P<year>\d{4})\s*[./년-]\s*)?'
                          r'(?P<month>\d{1,2})\s*[./월-]\s*(?P<day>\d{1,2})(?!\d)\s*[.일]?')
DATE_RANGE_END = re.compile(r'\s*(?:\([월화수목금토일]\))?\s*[~～∼]\s*(\d{1,2})(?!\d|\s*[./월-]\s*\d)\s*[.일]?')
FIXED_HOLIDAYS = {(1, 1): '신정', (3, 1): '삼일절', (5, 5): '어린이날', (6, 6): '현충일',
                  (8, 15): '광복절', (10, 3): '개천절', (10, 9): '한글날', (12, 25): '성탄절'}
FIXED_HOLIDAY_NOTICE = '공휴일 검사는 고정 공휴일만 확인(설날·추석·대체·임시공휴일은 학사일정 확인 필요)'
CALENDAR_HOLIDAY = re.compile(r'휴업|휴일|설날|추석|부처님\s*오신\s*날|석가탄신일')


def checklist_dates(text, year=None):
    """Normalize date spellings; short dates inherit only the preceding year/context."""
    found, end, academic = [], 0, False
    for match in DATE_MENTION.finditer(text):
        if match.start() < end:
            continue
        context = text[end:match.start()]
        for preceding in CONTEXT_YEAR.finditer(context):
            year = int(preceding['year'])
            academic = preceding['kind'] == '학년도'
        if match['year']:
            year = int(match['year'])
            academic = False
        month, day = int(match['month']), int(match['day'])
        resolved_year = int(year) if year else None
        if resolved_year and academic:
            sys.path.insert(0, str(h.SKILL))
            from gonmun_lint import _school_year
            resolved_year = _school_year(resolved_year, month)
        found.append((resolved_year, month, day))
        end = match.end()
        tail = DATE_RANGE_END.match(text, end)
        if tail:
            found.append((resolved_year, month, int(tail[1])))
            end = tail.end()
    return found


def checklist_date_warnings(text, year=None, events=()):
    warnings = []
    for y, month, day in checklist_dates(text, year):
        try:
            value = date(y or 2000, month, day)
        except ValueError:
            continue  # Date validity/format remains the content validator's responsibility.
        label = f'{y}. {month}. {day}.' if y else f'{month}. {day}.'
        if y and value.weekday() >= 5:
            warnings.append(f'⚠ {"토요일" if value.weekday() == 5 else "일요일"} ({label})')
        if (month, day) in FIXED_HOLIDAYS:
            warnings.append(f'⚠ 공휴일: {FIXED_HOLIDAYS[month, day]} ({label})')
        for event in events:
            if y and event['date'] == value.isoformat() and CALENDAR_HOLIDAY.search(event['title']):
                warnings.append(f'⚠ 휴업일·공휴일: {event["title"]} ({label})')
    return list(dict.fromkeys(warnings))


def with_date_warnings(reason, warnings):
    return '; '.join([reason] + [warning for warning in dict.fromkeys(warnings) if warning not in reason])


def date_source_text(path):
    """Extract HWPX or read known text formats; never decode binary originals."""
    if path.suffix.lower() == '.hwpx':
        from lxml.etree import XMLSyntaxError
        from zipfile import BadZipFile
        sys.path.insert(0, str(h.SKILL))
        from text_extract import extract_markdown
        try:
            return extract_markdown(path)
        except (OSError, ValueError, KeyError, BadZipFile, XMLSyntaxError,
                zlib.error, EOFError, RuntimeError, NotImplementedError, SystemExit):
            return None
    if path.suffix.lower() not in ('.json', '.md', '.txt', '.csv', '.tsv', '.rst', '.text', '.xml', '.yaml', '.yml'):
        return None
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            text = path.read_text(encoding=encoding)
            return text if '\0' not in text else None
        except UnicodeError:
            continue
        except OSError:
            return None
    return None


def proposal_date_review(item, text, events=(), *, calendar_valid=False):
    academic_year = h.CONTEXT.settings.get('school', {}).get('academic_year')
    proposed = checklist_dates(item['proposed'], academic_year)
    if not proposed:
        return item
    available = checklist_dates(text) if text is not None else []
    review = 'unreadable' if text is None else 'matched'
    if item['source']['kind'] == 'calendar' and text is not None and not calendar_valid:
        return dict(item, _date_review='unknown_year',
                    _date_warnings=checklist_date_warnings(item['proposed'], academic_year, events))
    for y, month, day in proposed if text is not None else ():
        same_day = [sy for sy, m, d in available if (month, day) == (m, d)]
        if any(sy is not None and (y is None or y == sy) for sy in same_day):
            continue
        if None in same_day:
            # A validated calendar can establish a short date's year only from
            # the school's academic year. Explicit source years always prevail.
            if (item['source']['kind'] == 'calendar' and calendar_valid
                    and type(academic_year) is int and all(sy is None for sy in same_day)):
                sys.path.insert(0, str(h.SKILL))
                from gonmun_lint import _school_year
                if y == _school_year(academic_year, month):
                    continue
            review = 'unknown_year'
        else:
            review = 'missing'
            break
    return dict(item, _date_review=review,
                _date_warnings=checklist_date_warnings(item['proposed'],
                    h.CONTEXT.settings.get('school', {}).get('academic_year'), events))


def checklist_aliases(m, extracted):
    """Resolve paragraph aliases from actual cell ownership, never equal text."""
    cells = {s['key'] for s in extracted['slots'] if s['key'].startswith('cell:')}
    if not cells or not m.get('base'):
        return {}
    sys.path.insert(0, str(h.SKILL))
    from hwpx_slots import NS, _parse_section, owned_cells
    root = _parse_section(h.template_file(m))
    paragraphs = {p: f'p:{i}' for i, p in enumerate(root.xpath('.//hp:p', namespaces=NS))}
    aliases = {}
    for i, table in enumerate(root.xpath('.//hp:tbl', namespaces=NS)):
        for cell in owned_cells(table):
            addr = cell.find('hp:cellAddr', namespaces=NS)
            if addr is None:
                continue
            key = f"cell:{i}:{addr.get('rowAddr', '0')}:{addr.get('colAddr', '0')}"
            if key in cells:
                aliases.update((paragraphs[p], key) for p in cell.xpath('.//hp:p', namespaces=NS))
    return aliases


def checklist_code_columns(extracted, *, labeled=False):
    """Existing related-cell classification; serial-number columns stay excluded."""
    columns = {}
    for slot in extracted['slots']:
        parts = slot['key'].split(':')
        if parts[0] == 'cell' and len(parts) == 4:
            columns.setdefault((parts[1], parts[3]), []).append(
                (int(parts[2]), ''.join(slot.get('text', slot.get('preview', '')).split())))
    code_columns = set()
    for column, cells in columns.items():
        codes = [int(text) for _, text in sorted(cells) if re.fullmatch(r'\d{1,4}', text)]
        if codes and not (len(codes) >= 3 and all(b == a + 1 for a, b in zip(codes, codes[1:]))):
            code_columns.add(column)
        # A code list can itself run 01..13. Its explicit code header separates
        # it from 순번 without changing checklist_rows' selection/apply contract.
        if labeled and any('코드' in text for _, text in cells):
            code_columns.add(column)
    return code_columns


def subject_code_map(extracted):
    """Only unambiguous subject/code pairs in the base document's actual rows."""
    columns = checklist_code_columns(extracted, labeled=True)
    rows = {}
    for slot in extracted['slots']:
        parts = slot['key'].split(':')
        if parts[0] != 'cell' or len(parts) != 4:
            continue
        text = ''.join(slot.get('text', slot.get('preview', '')).split())
        rows.setdefault(tuple(parts[1:3]), []).append((parts[3], text))
    by_subject, by_code = {}, {}
    for (table, _), cells in rows.items():
        subjects = {text for col, text in cells if (table, col) not in columns
                    and re.fullmatch(r'[가-힣]+(?:[·∙ㆍ/･・()-][가-힣]+)*', text)}
        codes = {text for col, text in cells if (table, col) in columns
                 and re.fullmatch(r'\d{1,4}', text)}
        for subject in subjects:
            for code in codes:
                by_subject.setdefault(subject, set()).add(code)
                by_code.setdefault(code, set()).add(subject)
    return {subject: next(iter(codes)) for subject, codes in by_subject.items()
            if len(codes) == 1 and len(by_code[next(iter(codes))]) == 1}


def checklist_code_suggestions(rows, extracted, aliases, proposals):
    mapping = subject_code_map(extracted)
    columns = checklist_code_columns(extracted, labeled=True)
    subjects = {}
    for key, item in proposals.items():
        value = item['proposed']
        cell = aliases.get(key, key).split(':')
        if (len(cell) == 4 and cell[0] == 'cell' and isinstance(value, str)
                and (cell[1], cell[3]) not in columns
                and value.strip() and not re.search(r'\d', value)):
            subjects.setdefault(tuple(cell[1:3]), set()).add(''.join(value.split()))
    suggestions = {}
    for row in rows:
        cell = aliases.get(row['key'], row['key']).split(':')
        if (len(cell) != 4 or cell[0] != 'cell' or (cell[1], cell[3]) not in columns
                or (row.get('text', '').strip() and not re.fullmatch(r'\d{1,4}', ''.join(row['text'].split())))):
            continue
        # An explicitly selected confirmation-only code is still related to
        # the proposed subject. Keep its existing snapshot/tamper-check path.
        if row['key'] in proposals and proposals[row['key']]['proposed'] is not None:
            continue
        candidates = subjects.get(tuple(cell[1:3]), set())
        matched = candidates & mapping.keys()
        if len(matched) == 1:
            subject = next(iter(matched))
            code = mapping[subject]
            suggestions[row['key']] = (code, f'같은 문서 코드표: {subject}→{code}')
        elif matched:
            suggestions[row['key']] = ('', '확인 필요 — 같은 행 과목 제안이 모호함')
        elif candidates:
            suggestions[row['key']] = ('', '확인 필요 — 코드표에 없는 과목')
    return suggestions


def checklist_rows(m, extracted, aliases, proposals=None):
    sys.path.insert(0, str(h.SKILL))
    from value_guard import VALUE_SHAPE
    supplied = set(m.get('slots', {}).get('values', {})) | set(m.get('kept_slots', []))
    supplied |= {aliases[key] for key in supplied if key in aliases}
    supplied |= set(proposals or {})
    paragraph_cells = {aliases[key] for key in (proposals or {}) if key in aliases}
    blocked = {s['key'] for s in extracted.get('blocked_slots', [])}
    rows = []
    seen = set()
    previous = None
    for slot in extracted['slots']:
        key, text = slot['key'], slot.get('text', slot.get('preview', ''))
        if (key in aliases and aliases[key] not in paragraph_cells) or key in paragraph_cells or key in seen:
            continue
        seen.add(key)
        before = ''
        if previous:
            old_key = previous['key']
            if (key.startswith('p:') and old_key == 'p:' + str(int(key[2:]) - 1)
                    or key.startswith('cell:') and old_key.split(':')[:2] == key.split(':')[:2]):
                before = previous.get('text', previous.get('preview', ''))
        if key not in blocked and (key in supplied or VALUE_SHAPE.search(text) or checklist_date(text)
                                  or YEAR.search(text) or re.search('학년도|연도|학기', text)):
            rows.append({'key': key, 'text': text, 'before': before})
        previous = slot
    # Rows already selected for confirmation seed their row's code/blank cells.
    # Include safety-net rows too: they become input/keep decisions on apply,
    # and must yield the same row set during later reconstruction.
    related_rows = {tuple(aliases.get(key, key).split(':')[1:3]) for key in {row['key'] for row in rows}
                    if aliases.get(key, key).startswith('cell:')}
    # Only code columns: short numeric codes that are not a 1, 2, 3… sequence
    # (순번). Blank form fields and serial numbers are not related cells; on
    # 11. 3. they added 23 noise rows to a 61-row checklist.
    code_columns = checklist_code_columns(extracted)
    selected = {row['key']: row for row in rows}
    for slot in extracted['slots']:
        key = slot['key']
        text = slot.get('text', slot.get('preview', ''))
        if (key.startswith('cell:') and len(key.split(':')) == 4
                and tuple(key.split(':')[1:3]) in related_rows
                and (key.split(':')[1], key.split(':')[3]) in code_columns
                and key not in selected and key not in blocked and key not in paragraph_cells
                and (not text.strip() or re.fullmatch(r'\d{1,4}', ''.join(text.split())))):
            selected[key] = {'key': key, 'text': text, 'before': '', 'related': True}
    # Extraction order is also the apply/reconciliation contract.
    rows, seen = [], set()
    for slot in extracted['slots']:
        key = slot['key']
        if key in selected and key not in seen:
            rows.append(selected[key])
            seen.add(key)
    return rows


class ChecklistProposalError(ValueError):
    def __init__(self, problems):
        super().__init__('확인표 제안 검증 실패')
        self.problems = problems


def checklist_input_path(value):
    path = h.input_path(value)
    if not path.is_relative_to(h.ROOT):
        raise ValueError('작업 폴더 밖 파일은 제안 근거로 사용할 수 없습니다: ' + str(value))
    return h.workspace_path(path.relative_to(h.ROOT))


def checklist_proposals(path, folder, extracted, aliases, digest=None):
    """Validate every proposal before creating a checklist or changing its inputs."""
    try:
        path = checklist_input_path(path)
        actual = h.sha(path)
        if digest is not None and digest != actual:
            raise ValueError('제안 파일 해시 불일치')
        raw = h.read_json(path)
        if not isinstance(raw, list):
            raise ValueError('제안 JSON은 목록이어야 합니다')
    except (ValueError, OSError, TypeError) as exc:
        raise ChecklistProposalError([str(exc)]) from exc
    slots = {s['key'] for s in extracted['slots']}
    blocked = {s['key'] for s in extracted.get('blocked_slots', [])}
    proposals, sources, problems, seen = {}, {}, [], set()
    for i, item in enumerate(raw, 1):
        try:
            if not isinstance(item, dict):
                raise ValueError('제안은 객체여야 합니다')
            key = item.get('slot')
            if not isinstance(key, str) or key not in slots:
                raise ValueError('추출되지 않은 슬롯: ' + str(key))
            if key in blocked or aliases.get(key) in blocked:
                raise ValueError('blocked 슬롯: ' + key)
            if (key in seen or aliases.get(key) in seen
                    or any(aliases.get(previous) == key for previous in seen)):
                raise ValueError('중복 슬롯: ' + key)
            seen.add(key)
            if not isinstance(item.get('reason'), str) or not item['reason'].strip():
                raise ValueError('reason에 변경 이유가 필요합니다')
            if 'proposed' in item and 'source' in item and item['proposed'] is None and item['source'] is None:
                proposals[key] = item
                continue
            if not isinstance(item.get('proposed'), str):
                raise ValueError('proposed는 문자열이어야 합니다')
            # A file saved in the ANSI code page turns Hangul into '?'. On 11. 4.
            # such proposals ("2024???2??1???") reached the teacher as suggestions.
            original = next((str(s.get('text', s.get('preview', ''))) for s in extracted['slots'] if s['key'] == key), '')
            for field, text in (('proposed', item['proposed']), ('reason', item['reason'])):
                if '�' in text or (re.search(r'\?{2,}', text) and '??' not in original):
                    raise ValueError(f'{field}에 깨진 문자(?)가 있습니다. 제안 파일을 UTF-8로 다시 저장하세요 '
                                     '(PowerShell 5.1의 Set-Content·> 기본 인코딩은 한글을 ?로 바꿉니다)')
            source = item.get('source')
            if not isinstance(source, dict) or source.get('kind') not in ('calendar', 'document', 'setting', 'prior_document', 'teacher'):
                raise ValueError('source.kind 미지원')
            kind, ref, detail = source['kind'], source.get('ref'), source.get('detail', '')
            if not isinstance(ref, str) or not ref.strip():
                raise ValueError('source.ref가 필요합니다')
            if not isinstance(detail, str):
                raise ValueError('source.detail은 문자열이어야 합니다')
            source_text, source_events, calendar_valid = None, [], False
            if kind in ('calendar', 'document', 'prior_document'):
                # Imported originals in this job's sources/ are the sole managed-area exception.
                original = checklist_input_path(ref)
                imported = (folder.is_relative_to(h.ROOT / '.hwpdoc/prepared')
                            and original.is_relative_to(folder / 'sources'))
                if not imported:
                    original = h.original_input_path(ref)
                expected = source.get('sha256')
                if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
                    raise ValueError('source.sha256이 필요합니다 (소문자 64자리)')
                if h.sha(original) != expected:
                    raise ValueError('근거 파일 해시 불일치: ' + ref)
                sources[original.relative_to(h.ROOT).as_posix()] = expected
                if checklist_dates(item['proposed']):
                    source_text = date_source_text(original)
                    if kind == 'calendar' and source_text is not None:
                        try:
                            source_events, _ = calendar_events(json.loads(source_text))
                            calendar_valid = True
                        except (ValueError, TypeError):
                            pass  # Invalid calendar responses cannot establish date evidence.
            elif kind == 'setting':
                value = h.CONTEXT.settings
                for part in ref.split('.'):
                    if not isinstance(value, dict) or part not in value:
                        raise ValueError('없는 설정 키: ' + ref)
                    value = value[part]
                source_text = str(value)
            elif not detail.strip():
                raise ValueError('teacher 근거는 detail에 교사 원문이 필요합니다')
            else:
                source_text = detail
            # Internal review fields always come from the verified source, never the proposal JSON.
            item = {k: v for k, v in item.items() if not k.startswith('_date_')}
            proposals[key] = proposal_date_review(item, source_text, source_events, calendar_valid=calendar_valid)
        except (ValueError, OSError, TypeError) as exc:
            problems.append(f'제안 {i}: {exc}')
    if problems:
        raise ChecklistProposalError(problems)
    return proposals, [{'path': p, 'sha256': sha} for p, sha in sources.items()], {
        'path': path.relative_to(h.ROOT).as_posix(), 'sha256': actual}


def proposal_suggestion(item, fallback=('', ''), warnings=()):
    if item['proposed'] is None:
        proposed, reason = fallback
        return proposed, f"확인 필요 — {item['reason']}" + ('; ' + reason if reason else '')
    source = item['source']
    reason = f"{source['kind']}: {source['ref']} — {source.get('detail') or item['reason']}"
    proposal = item['proposed']
    review = item.get('_date_review')
    if review in ('missing', 'unreadable', 'unknown_year'):
        proposal = ''
        detail = {'missing': '제안 날짜가 근거 원문에 없음',
                  'unreadable': '날짜 근거 원문 대조 미실시 (텍스트를 읽을 수 없음)',
                  'unknown_year': '근거 날짜의 연도 불명'}[review]
        reason = f'확인 필요 — {detail}; 참고 제안: {item["proposed"]}; ' + reason
    return proposal, with_date_warnings(reason, list(item.get('_date_warnings', [])) + list(warnings))


def calendar_events(raw):
    """Read both retrieval responses and prepare_document_context envelopes."""
    if not isinstance(raw, dict) or type(raw.get('contextVersion')) is not int or raw['contextVersion'] != 1:
        raise ValueError('학사일정 contextVersion은 1이어야 합니다')
    if raw.get('outcome') == 'document_context':
        results = raw.get('results')
        if not isinstance(results, list):
            raise ValueError('학사일정 results 배열이 필요합니다')
        calendars = [r.get('response') for r in results if isinstance(r, dict) and r.get('kind') == 'calendar']
        if not calendars:
            raise ValueError('calendar 조회 결과가 없습니다')
        events, partial = [], bool(raw.get('unresolved') or raw.get('errors'))
        for response in calendars:
            items, incomplete = calendar_events(response)
            events.extend(items); partial |= incomplete
        return sorted(events, key=lambda e: e['date']), partial
    if raw.get('outcome') != 'result' or not isinstance(raw.get('data'), list):
        raise ValueError('학사일정 outcome=result와 data 배열이 필요합니다')
    def provided(value):
        return value.get('value') if isinstance(value, dict) and value.get('state') == 'provided' else value
    events = []
    for item in raw['data']:
        try:
            span = provided(item['scope']['dateRange'])
            day, title = span['start'], provided(item['title'])
            if (not isinstance(day, str) or not ISO_DATE.fullmatch(day) or span.get('end') != day
                    or not isinstance(title, str) or not title.strip()):
                raise ValueError('ISO 하루 날짜와 title이 필요합니다')
            date.fromisoformat(day)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('학사일정의 ISO 하루 날짜 또는 title이 올바르지 않습니다') from exc
        if 'fetchedAt' in item and not isinstance(item['fetchedAt'], str):
            raise ValueError('학사일정 fetchedAt은 문자열이어야 합니다')
        events.append({'date': day, 'title': title, 'fetched_at': item.get('fetchedAt') or '조회시각 미확인'})
    return sorted(events, key=lambda e: e['date']), bool(raw.get('status') == 'partial' or raw.get('unresolved') or raw.get('errors'))


def checklist_suggestion(row, year, events):
    text = row['text']
    proposal, reason = '', ''
    if year:
        proposed = YEAR.sub(lambda m: str(year) if int(m[0]) < int(year) else m[0], text)
        if proposed != text:
            proposal, reason = refresh_weekdays(proposed), f'작업 폴더 학년도 {year}'
    matches = []
    has_date = checklist_date(text) or checklist_dates(text)
    if has_date:
        matches = [e for e in events if any(word in text or word in row['before']
                   for word in re.findall(r'[가-힣]{2,}', e['title']))]
    if has_date and (len(matches) != 1 or len(checklist_dates(text)) != 1):
        reason = '확인 필요 — 날짜 근거 없음; 작년 ' + text
        if proposal:
            reason += ' — 연도만 바꾸면 ' + proposal
        reason = with_date_warnings(reason, checklist_date_warnings(proposal or text, year, events))
        if matches:
            reason += '; 후보: ' + '; '.join(e['date'] + ' ' + e['title'] for e in matches)
        return '', reason
    if matches:
        labels = [f"NEIS 학사일정: {e['title']} ({e['fetched_at']})" for e in matches]
        day = date.fromisoformat(matches[0]['date'])
        proposed = proposal or text
        found = checklist_date(proposed) or DATE_MENTION.search(proposed)
        old = found[0]
        numbers = re.findall(r'\d+', old)
        parts = iter([day.year, day.month, day.day] if len(numbers) == 3 else [day.month, day.day])
        padded = '/' in old or '-' in old or bool(re.match(r'\d{4}\.\d', old))
        replacement = re.sub(r'\d+', lambda m: str(next(parts)).zfill(len(m[0]))
                             if padded or m[0].startswith('0') else str(next(parts)), old)
        after = proposed[found.end():]
        # The weekday beside the date belongs to last year's date; recompute it.
        after = re.sub(r'^(\s*\(\s*)[월화수목금토일](\s*\))', lambda m: m[1] + '월화수목금토일'[day.weekday()] + m[2], after)
        proposal, reason = proposed[:found.start()] + replacement + after, labels[0]
    return proposal, with_date_warnings(reason, checklist_date_warnings(proposal, day.year if matches else year, events))


WEEKDAY_DATE = re.compile(r'(?:(\d{4})\.\s*)?(\d{1,2})\.\s*(\d{1,2})\.?\s*\(\s*([월화수목금토일])\s*\)')


def refresh_weekdays(text):
    """A year-shifted date keeps last year's weekday; recompute it (11. 3.: 2026.09.19.(목))."""
    year = None

    def fix(m):
        nonlocal year
        if m[1]:
            year = int(m[1])
        if year is None:
            return m[0]
        try:
            weekday = '월화수목금토일'[date(year, int(m[2]), int(m[3])).weekday()]
        except ValueError:
            return m[0]
        return m[0][:m.start(4) - m.start()] + weekday + m[0][m.end(4) - m.start():]
    return WEEKDAY_DATE.sub(fix, text)


def checklist_cell(text):
    text = html.escape(text).replace('|', r'\|').replace('\r', '&#13;').replace('\n', '<br>').replace('\t', '&#9;')
    return re.sub(r'^ +| +$', lambda m: '&#32;' * len(m[0]), text)


FIXED_TEXT_HEADING = '## 확인표에 넣지 않은 고정 문구(그대로 유지)'


def checklist_fixed_slots(extracted, aliases, selected):
    """List every extracted address outside the decision rows, including aliases."""
    selected = set(selected)
    fixed = {}
    for slot in extracted['slots']:
        key = slot['key']
        children = {p for p, cell in aliases.items() if cell == key}
        if key in selected or aliases.get(key) in selected or (children and children <= selected):
            continue
        text = ' '.join(slot.get('text', slot.get('preview', '')).split())
        fixed[key] = html.escape(text[:160] + ('…' if len(text) > 160 else ''))
    return fixed


def checklist_fixed_scope(content, extracted, aliases, selected):
    """Only explicit, unchanged entries in the hash-bound section give scope."""
    expected = checklist_fixed_slots(extracted, aliases, selected)
    inside, keys = False, set()
    for line in content.splitlines():
        if line == FIXED_TEXT_HEADING:
            inside = True
        elif line.startswith('## '):
            inside = False
        elif inside:
            keys.update(key for key, text in expected.items() if line == f'- {key}: {text}')
    return keys


def parse_checklist(content):
    """Read the decision table without touching a manifest or any files."""
    lines = content.splitlines()
    start = next((i for i, line in enumerate(lines) if line.lstrip().startswith('|')), len(lines))
    end = next((i for i in range(start, len(lines)) if lines[i].strip() in ('## 참고 학사일정', FIXED_TEXT_HEADING)),
               len(lines))
    stray = next((i for i in range(end, len(lines)) if lines[i].lstrip().startswith('|')), None)
    if stray is not None:
        raise ValueError(f'확인표 표 밖의 표 행 — 줄 번호: {stray + 1}. 확인할 값 표 안으로 옮기세요')
    while end > start and not lines[end - 1].strip():
        end -= 1
    table = []
    for i in range(start, end):
        line = lines[i].strip()
        if not (line.startswith('|') and line.endswith('|')):
            raise ValueError(f'확인표 표 행 형식 오류 — 줄 번호: {i + 1}')
        cells = re.split(r'(?<!\\)\|', line[1:-1])
        if len(cells) != 6:
            raise ValueError(f'확인표 열 개수 오류 — 줄 번호: {i + 1}')
        table.append([html.unescape(c.strip().replace(r'\|', '|').replace('<br>', '\n')) for c in cells])
    if (len(table) < 2 or table[0] != CHECKLIST_HEADER or len(table[1]) != 6
            or any(not re.fullmatch(r':?-+:?', c) for c in table[1])):
        raise ValueError('확인표 표 머리/열이 손상되었습니다')
    return table[2:], start


def checklist_warning_notes(folder):
    """Expose the displayed date warnings in read-only check, including safety-net rows."""
    path = folder / '확인표.md'
    if not path.is_file():
        return []
    try:
        content = path.read_text(encoding='utf-8-sig')
        rows, _ = parse_checklist(content)
    except (OSError, ValueError, UnicodeError):
        return []  # Existing checklist/input validation reports malformed or changed tables.
    notes = [{'slot': row[1], 'warning': warning.strip()} for row in rows
             for warning in re.findall(r'⚠[^;]+', row[4])]
    if '⚠ ' + FIXED_HOLIDAY_NOTICE in content:
        notes.append({'slot': None, 'warning': '⚠ ' + FIXED_HOLIDAY_NOTICE})
    return notes


def interpret_checklist(m, rows, content, aliases, proposals=None):
    """Project teacher decisions, retaining apply's alias/filter semantics."""
    entries, start = parse_checklist(content)
    row_keys = {row['key'] for row in rows}
    positions = {}
    for i, row in enumerate(entries, start + 3):
        key = aliases.get(row[1], row[1])
        if key not in row_keys:
            key = row[1]
        if key in positions:
            line, number = positions[key]
            raise ValueError(f'확인표 중복 위치 {key} — 행 번호: {number}, {row[0]} / 줄 번호: {line}, {i}')
        positions[key] = (i, row[0])
    expected = [[str(i), row['key'], row['text']] for i, row in enumerate(rows, 1)]
    if any(len(row) != 6 for row in entries) or [row[:3] for row in entries] != expected:
        raise ValueError('확인표 행/위치/작년 값이 추출 슬롯과 다릅니다')
    for row in entries:
        if row[1] in (proposals or {}):
            item = proposals[row[1]]
            if not m['checklist'].get('date_review_version'):
                # Already generated/applied tables keep their original display contract.
                item = {k: v for k, v in item.items() if not k.startswith('_date_')}
            expected = (m['checklist']['confirm_only_suggestions'][row[1]] if item['proposed'] is None
                        else list(proposal_suggestion(item, warnings=m['checklist'].get('date_warnings', {}).get(row[1], []))))
            if row[3:5] != expected:
                raise ValueError('확인표 제안/근거가 제안 파일과 다릅니다: ' + row[1])
    empty = [row[0] for row in entries if not row[5].strip()]
    if empty:
        raise ValueError('확정 값이 빈 행 번호: ' + ', '.join(empty))
    paragraph_cells = {aliases[key] for key in row_keys if key in aliases}
    values = {key: value for key, value in m['slots']['values'].items()
              if aliases.get(key) not in row_keys and key not in paragraph_cells}
    kept = []
    from hwpdoc_content_check import KEEP_RESIDUE, KEEP_DATE
    for number, key, base_text, _, _, value in entries:
        if value in ('유지', KEEP_RESIDUE, KEEP_DATE):
            values.pop(key, None)
            kept.append(key)
        else:
            values[key] = checklist_decision(value, base_text, number, key)
    return values, kept, len(entries)


def checklist_decision(value, base_text, number, key):
    """One keyword interpretation shared by apply and hash-bound reconciliation."""
    keyword = value.strip()
    from hwpdoc_content_check import NORMALIZE_PREFIX, normalize_dates
    if value.startswith(NORMALIZE_PREFIX):
        return normalize_dates(value[len(NORMALIZE_PREFIX):])
    # The first colon (including a fullwidth colon) that separates a label from
    # its value. Not a label: times and ratios written without spaces (10:00,
    # 3:2) or a URL scheme (http://). A label may end with a digit (항목1: …).
    match = next((m for m in re.finditer(r'[:：]', base_text)
                  if not (base_text[m.start() - 1:m.start()].isdigit() and base_text[m.end():m.end() + 1].isdigit())
                  and not base_text.startswith('//', m.end())), None)
    labelled = (match is not None and bool(base_text[:match.start()].strip())
                and bool(base_text[match.end():].strip()))
    if keyword == '값만 비움':
        if not labelled:
            raise ValueError(f'확인표 행 {number} ({key}): `값만 비움`은 이름: 값 꼴의 칸에만 쓸 수 있습니다')
        return base_text[:match.end()]
    if keyword == '비움' and labelled:
        raise ValueError(f'확인표 행 {number} ({key}): 이 칸은 이름과 값이 한 문단입니다. '
                         '값만 비우려면 `값만 비움`, 문단 전체를 지우려면 `문단 비움`.')
    return '' if keyword in ('비움', '문단 비움') else value


def applied_checklist_values(m, extracted, aliases):
    """Reconstruct inputs solely from the hash-bound table, never current edits."""
    record = m['checklist']
    path = h.workspace_path(record['path'])
    content = path.read_text(encoding='utf-8-sig')
    if h.sha(path) != record['sha256']:
        raise ValueError('확인표 파일 해시 불일치')
    from hwpdoc_content_check import residue_receipts
    if record.get('residue_decisions', {}) != residue_receipts(m, content):
        raise ValueError('잔재 유지 결정의 값/규칙 기록 불일치: 같은 잔재인지 확인하고 --apply하세요')
    entries, _ = parse_checklist(content)
    proposals = {}
    if record.get('proposals'):
        proposal_record = record['proposals']
        proposals, _, _ = checklist_proposals(proposal_record['path'], path.parent, extracted, aliases,
                                             proposal_record['sha256'])
    # Table addresses recover manually selected non-date rows as well. Seeding
    # from manifest values here would legitimize edits added after --apply.
    selection = dict(m, slots={'values': {row[1]: '' for row in entries}}, kept_slots=[])
    rows = checklist_rows(selection, extracted, aliases, proposals)
    empty = dict(m, slots={'values': {}})
    values, kept, _ = interpret_checklist(empty, rows, content, aliases, proposals)
    return values, kept


def apply_checklist(m, rows, path, manifest, aliases, proposals=None, *, normalize_dates=False):
    from hwpdoc_content_check import normalized_checklist, residue_receipts
    content = path.read_text(encoding='utf-8-sig')
    normalized_count = 0
    if normalize_dates:
        if isinstance(m.get('draft_approval'), dict) and m['draft_approval'].get('confirmed') is True:
            raise ValueError('승인 후 날짜 일괄 정리는 하지 않습니다. revise로 수정판을 준비해 다시 확인받으세요')
        content, normalized_count = normalized_checklist(content)
    values, kept, count = interpret_checklist(m, rows, content, aliases, proposals)
    # Validation precedes all mutations, including rewriting batch choices.
    if normalized_count:
        path.write_text(content, encoding='utf-8')
    m['slots']['values'], m['kept_slots'] = values, kept
    m['checklist'] = dict(m.get('checklist', {}), path=path.relative_to(h.ROOT).as_posix(), sha256=h.sha(path))
    decisions = residue_receipts(m, content)
    if decisions:
        m['checklist']['residue_decisions'] = decisions
    else:
        m['checklist'].pop('residue_decisions', None)
    if 'proposals' in m['checklist'] or 'applied' in m['checklist']:
        m['checklist']['applied'] = True
    h.write_json(manifest, m)
    h.audit('checklist_apply', manifest, 'pass', {'rows': count, 'kept_slots': kept})
    return {'status': 'applied', 'manifest': str(manifest), 'checklist': str(path), 'rows': count, 'kept_slots': kept,
            'normalized_date_slots': normalized_count, 'residue_decisions': decisions,
            'next_action': f'다음: check --job {m["job_id"]}로 남은 항목 확인. 초안을 제시하고 교사 확인 후 승인 기록을 채우세요.'}


def fill_checklist(m, rows, path, aliases, proposals, ranges, value):
    """Transcribe a teacher's batch answer; never apply it or replace an answer."""
    if m.get('checklist') and m['checklist'].get('applied', True):
        raise ValueError('이미 적용된 확인표는 --fill로 바꾸지 않습니다. --regenerate로 재생성하고 교사 재확인 후 채우세요')
    previous = path.read_bytes()
    content = previous.decode('utf-8-sig')
    entries, start = parse_checklist(content)
    if not value.strip():
        raise ValueError('--value는 비어 있을 수 없습니다. 비울 칸은 기존 `비움` 문법을 쓰세요')
    numbers = set()
    for part in ranges.split(','):
        match = re.fullmatch(r'([1-9][0-9]*)(?:-([1-9][0-9]*))?', part.strip())
        if not match:
            raise ValueError('--fill 번호 범위 오류: 37-62 또는 3,5,7-9 형식으로 쓰세요')
        first, last = int(match[1]), int(match[2] or match[1])
        if first > last or last > len(entries):
            raise ValueError('--fill 번호 범위가 확인표 밖이거나 역순입니다: ' + part)
        numbers.update(range(first, last + 1))
    lines = content.splitlines()
    filled, skipped = [], []
    for offset, row in enumerate(entries, start + 2):
        number = int(row[0])
        if number not in numbers:
            continue
        if row[5].strip():
            skipped.append(number)
            continue
        checklist_decision(value, row[2], row[0], row[1])
        row[5] = value
        filled.append(number)
        lines[offset] = '| ' + ' | '.join(map(checklist_cell, row)) + ' |'
    # The existing interpreter validates addresses, proposals and decisions.
    # Remaining unanswered rows use temporary keeps only for validation; those
    # keeps are never written, and --apply still refuses the actual empty rows.
    validation = content.splitlines()
    for offset, row in enumerate(entries, start + 2):
        validation[offset] = '| ' + ' | '.join(map(checklist_cell, [*row[:5], row[5] if row[5].strip() else '유지'])) + ' |'
    interpret_checklist(m, rows, '\n'.join(validation) + '\n', aliases, proposals)
    if filled:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix='.checklist-fill-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write('\n'.join(lines) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            if path.read_bytes() != previous:
                raise ValueError('묶음 입력 준비 중 확인표가 변경됐습니다. 최신 내용을 읽고 다시 실행하세요')
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    result = dict(status='filled', checklist=str(path), filled_rows=len(filled),
                  skipped_rows=skipped, next_action=f'다음: checklist --job {m["job_id"]} --apply')
    h.audit('checklist_fill', path, 'pass', dict(ranges=ranges, value=value, filled_rows=filled, skipped_rows=skipped))
    return result


def checklist(args):
    h.job_dir(args.job)
    folder = h.workspace_path(Path('.hwpdoc/prepared') / args.job)
    manifest, path = folder / 'manifest.json', folder / '확인표.md'
    fill = getattr(args, 'fill', None)
    value = getattr(args, 'value', None)
    if (fill is None) != (value is None):
        raise ValueError('--fill과 --value는 함께 쓰세요')
    if getattr(args, 'normalize_dates', False) and not args.apply:
        raise ValueError('--normalize-dates는 교사의 일괄 적용 선택 후 --apply와 함께 쓰세요')
    if getattr(args, 'show', False):
        if args.proposals or args.regenerate:
            raise ValueError('--show는 --proposals/--regenerate와 함께 쓸 수 없습니다')
        m = h.read_json(manifest)
        if m.get('job_id') != args.job:
            raise ValueError('manifest의 job_id 불일치')
        record = m.get('checklist')
        path_source = 'manifest.checklist.path'
        if not record:
            # Legacy generation does not write a manifest receipt until --apply.
            # Its one canonical path is fixed by that manifest's job directory;
            # never scan filenames or select an archived table.
            record = {'path': path.relative_to(h.ROOT).as_posix()}
            path_source = 'legacy_manifest_directory'
        path = h.workspace_path(record['path'])
        if not path.is_file():
            raise ValueError('현재 확인표가 없습니다. 먼저 checklist로 확인표를 생성하세요: ' + str(path))
        entries, _ = parse_checklist(path.read_text(encoding='utf-8-sig'))
        confirmed = sum(bool(row[5].strip()) for row in entries)
        digest = h.sha(path)
        return dict(status='shown', job_id=args.job, checklist=str(path), sha256=digest,
                    path_source=path_source,
                    recorded_sha256=record.get('sha256'),
                    matches_recorded_sha256=(digest == record['sha256'] if record.get('sha256') else None),
                    applied=bool(m.get('checklist') and record.get('applied', True)),
                    rows=len(entries), confirmed_rows=confirmed, unconfirmed_rows=len(entries) - confirmed,
                    confirmation_meaning='확정 값이 비어 있지 않은 행 수입니다. 유효성·승인 여부는 check로 확인합니다.',
                    current_checklist_notice='현재 표는 이것 하나입니다. 이전 표는 보존용이며 사용하지 않습니다.')
    try:
        m = h.read_json(manifest)
        extracted = h.read_json(folder / 'slots.extracted.json')
        aliases = checklist_aliases(m, extracted)
        proposals, sources, record = {}, [], None
        proposal_path = getattr(args, 'proposals', None)
        regenerate = getattr(args, 'regenerate', False)
        if fill is not None and (proposal_path or regenerate):
            raise ValueError('--fill은 --proposals/--regenerate와 함께 쓸 수 없습니다. 현재 표를 확인한 뒤 별도로 채우세요')
        if args.apply and regenerate:
            raise ValueError('--regenerate와 --apply는 함께 쓸 수 없습니다. 새 표를 확인한 뒤 별도로 --apply 하세요')
        if args.apply or fill is not None:
            if proposal_path:
                raise ValueError('--proposals는 확인표 생성 때만 사용하세요. --apply는 기록된 제안을 사용합니다')
            record = m.get('checklist', {}).get('proposals')
            if record:
                proposals, sources, record = checklist_proposals(record['path'], folder, extracted, aliases, record['sha256'])
        elif proposal_path:
            proposals, sources, record = checklist_proposals(proposal_path, folder, extracted, aliases)
        rows = checklist_rows(m, extracted, aliases, proposals)
        if not rows:
            raise ValueError('확인할 값 칸을 찾지 못함 — 바꿀 칸을 직접 지정해야 합니다')
        if fill is not None:
            if m.get('checklist'):
                path = h.workspace_path(m['checklist']['path'])
            return fill_checklist(m, rows, path, aliases, proposals, fill, value)
        if args.apply:
            return apply_checklist(m, rows, path, manifest, aliases, proposals,
                                   normalize_dates=getattr(args, 'normalize_dates', False))
        previous, archive, previous_bytes = {}, None, None
        if path.exists():
            if not regenerate:
                raise ValueError('기존 확인표를 덮어쓰지 않습니다: ' + str(path) + '. 보존 후 다시 만들려면 --regenerate를 사용하세요')
            previous_bytes = path.read_bytes()
            entries, _ = parse_checklist(previous_bytes.decode('utf-8-sig'))
            for entry in entries:
                position = (entry[1], entry[2])
                if position in previous:
                    raise ValueError('이전 확인표 중복 위치/작년 값: ' + entry[1])
                previous[position] = entry[5]
        events, partial = calendar_events(h.read_json(h.input_path(args.calendar))) if args.calendar else ([], False)
        lines = (['> 일부 미확인: 학사일정 조회에 미확인 사항이 있습니다.', ''] if partial else [])
        lines += ['# 확인표', '']
        lines += (['제안이 맞으면 `확정 값`에 제안을 그대로 입력하세요.',
                   '제안과 다르면 `확정 값`에 고친 값을 입력하세요.',
                   '그대로 둘 칸은 `확정 값`에 `유지`를 입력하세요. 모든 행의 확인이 필요합니다.'] if record else [
                   '모든 행의 확정 값을 직접 입력하세요. 작년 값 그대로라면 `유지`를 입력하세요. 제안은 자동 확정되지 않습니다.'])
        lines += ['칸을 비우려면 `확정 값`에 `비움`을 입력하세요.',
                  '이름: 값이 한 칸이면 `값만 비움`은 쌍점까지 이름을 남기고, `문단 비움`은 문단 전체를 비웁니다. 이 칸에는 `비움`을 쓸 수 없습니다.',
                  f'표 밖의 고정 문구는 맨 아래 `{FIXED_TEXT_HEADING[3:]}` 절에 있습니다.']
        lines += ['', '## 확인할 값', '', '| ' + ' | '.join(CHECKLIST_HEADER) + ' |',
                  '| --- | --- | --- | --- | --- | --- |']
        year = h.CONTEXT.settings.get('school', {}).get('academic_year')
        needs_confirmation = 0
        carried_forward, needs_answer = 0, []
        confirm_only_suggestions, date_warnings = {}, {}
        confirm_only_rows = 0
        code_suggestions = checklist_code_suggestions(rows, extracted, aliases, proposals)
        for i, row in enumerate(rows, 1):
            proposal, reason = checklist_suggestion(row, year, events)
            if row['key'] in code_suggestions:
                proposal, reason = code_suggestions[row['key']]
            elif row.get('related'):
                proposal, reason = '', '같은 행 연관 칸 — 과목 코드·비고를 함께 확인하세요.'
            if row['key'] in proposals:
                item = proposals[row['key']]
                if item['proposed'] is not None:
                    warnings = checklist_date_warnings(item['proposed'], year, events)
                    if warnings:
                        date_warnings[row['key']] = warnings
                proposal, reason = proposal_suggestion(item, (proposal, reason), date_warnings.get(row['key'], []))
                confirm_only_rows += item['proposed'] is None or item.get('_date_review') in ('missing', 'unreadable', 'unknown_year')
                if item['proposed'] is None:
                    # --apply has no calendar input; retain the merged display for its tamper check.
                    confirm_only_suggestions[row['key']] = [proposal, reason]
            needs_confirmation += not proposal
            if record and not reason:
                reason = '확인 필요'
            decision = previous.get((row['key'], row['text']), '')
            if decision.strip():
                carried_forward += 1
            else:
                decision = ''
                needs_answer.append({'number': i, 'slot': row['key'], 'previous_value': row['text']})
            lines.append('| ' + ' | '.join(map(checklist_cell, [str(i), row['key'], row['text'], proposal, reason, decision])) + ' |')
        has_calendar = bool(args.calendar) or any(
            (item.get('source') or {}).get('kind') == 'calendar'
            and item.get('_date_review') != 'unreadable' for item in proposals.values())
        if not has_calendar and any(checklist_dates(row['text']) or checklist_dates(
                (proposals.get(row['key']) or {}).get('proposed') or '') for row in rows):
            lines[0:0] = ['⚠ ' + FIXED_HOLIDAY_NOTICE, '']
        if args.calendar:
            lines += ['', '## 참고 학사일정', '']
            lines += ['- ' + e['date'] + ' ' + checklist_cell(e['title']) + ' (' + checklist_cell(e['fetched_at']) + ')' for e in events]
            if not events:
                lines.append('조회된 일정 0건입니다. 공개 조회 결과만으로 행사 유무를 판단할 수 없습니다.')
        # The long fixed list follows the decisions, so the teacher reads the
        # table first. parse_checklist still rejects table rows placed here.
        lines += ['', FIXED_TEXT_HEADING, '',
                  '바꿀 문구가 있으면 해당 키를 --proposals로 확인표 행에 올리고 --regenerate 후 다시 확인·apply하세요.', '']
        lines += [f'- {key}: {text}' for key, text in
                  checklist_fixed_slots(extracted, aliases, {row['key'] for row in rows}).items()]
        # Validate all inputs and compose the new table before moving anything.
        # Rename preserves the exact previous bytes; exclusive creation never
        # overwrites a checklist (or a timestamp collision).
        if previous_bytes is not None:
            if path.read_bytes() != previous_bytes:
                raise ValueError('재생성 준비 중 확인표가 변경됐습니다. 최신 내용을 읽고 다시 실행하세요')
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            archive = path.with_name(f'확인표.{stamp}.이전.md')
            if archive.exists():
                raise ValueError('확인표 보존 파일이 이미 있습니다: ' + str(archive))
            path.rename(archive)
        with path.open('x', encoding='utf-8') as stream:
            stream.write('\n'.join(lines) + '\n')
        counts = {'rows': len(rows), 'calendar_partial': partial}
        if record or regenerate:
            m['checklist'] = {'path': path.relative_to(h.ROOT).as_posix(), 'sha256': h.sha(path),
                              'applied': False}
            if record:
                m['checklist']['proposals'] = record
                m['checklist']['date_review_version'] = 1
            if regenerate:
                # Preserve a changed approval input even if the regenerated
                # table has identical bytes. No previous approval is rewritten.
                m['checklist']['generated_at'] = h.now()
            if confirm_only_suggestions:
                m['checklist']['confirm_only_suggestions'] = confirm_only_suggestions
            if date_warnings:
                m['checklist']['date_warnings'] = date_warnings
            existing = {s['path'] for s in m.get('sources', [])}
            m.setdefault('sources', []).extend(s for s in sources if s['path'] not in existing)
            h.write_json(manifest, m)
        if record:
            counts.update(proposed_rows=len(proposals) - confirm_only_rows,
                          confirm_only_rows=confirm_only_rows, safety_net_rows=len(rows) - len(proposals),
                          needs_confirmation_rows=needs_confirmation)
        if regenerate:
            counts.update(carried_forward_rows=carried_forward, needs_answer_rows=needs_answer,
                          archived_checklist=str(archive) if archive else None)
        h.audit('checklist', path, 'pass', counts)
        return {'status': 'created', 'checklist': str(path), **counts}
    except ChecklistProposalError as exc:
        h.audit('checklist_apply' if args.apply else 'checklist', path, 'unconfirmed', exc.problems)
        return {'status': 'unconfirmed', 'error': str(exc), 'problems': exc.problems}
    except (ValueError, KeyError, OSError, TypeError) as exc:
        h.audit('checklist_fill' if fill is not None else 'checklist_apply' if args.apply else 'checklist', path, 'unconfirmed', str(exc))
        raise


def add_commands(commands):
    p = commands.add_parser('school', help='사용자가 확정한 NEIS 학교 식별 저장/조회; 네트워크 조회 없음')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--set-neis', metavar='candidateId'); mode.add_argument('--show', action='store_true')
    p.add_argument('--level', choices=SCHOOL_LEVELS); p.add_argument('--region')
    init = commands.add_parser('init')
    init.add_argument('path'); init.add_argument('--app', choices=['claude', 'codex'], required=True)
    init.add_argument('--skill-name', required=True, help='선택한 앱에서 실제 노출을 확인한 스킬 이름')
    init.add_argument('--school'); init.add_argument('--prefix'); init.add_argument('--year', type=int); init.add_argument('--copy-to')
    p = commands.add_parser('prepare')
    p.add_argument('--job', required=True)
    p.add_argument('--base', required=True, help='작년 문서 HWPX(미등록 일회성 베이스); 원본 보존 후 사본 편집')
    p.add_argument('--source', action='append', default=[]); p.add_argument('--values')
    p.add_argument('--workflow', choices=['W1', 'W2'], default='W1'); p.add_argument('--document-type', required=True)
    p.add_argument('--details', action='store_true', help='중복 목록을 포함한 기존 전체 준비 출력')
    p = commands.add_parser('record', help='UTF-8 JSON의 준비 기록 등록; 파일 해시 자동 계산, 승인·확인표는 별도 명령')
    p.add_argument('--job', required=True)
    p.add_argument('--file', required=True, help='작업 폴더 안 UTF-8 JSON; 객체 부분 병합, 배열 교체, unresolved_add만 추가 기록')
    p = commands.add_parser('draft', help='적용된 확인표의 확정 값으로 확인용 초안 생성·등록; 승인 아님')
    p.add_argument('--job', required=True)
    p = commands.add_parser('checklist')
    p.add_argument('--job', required=True)
    p.add_argument('--proposals')
    p.add_argument('--value', help='교사가 답한 확정 값; --fill과 함께 사용')
    p.add_argument('--regenerate', action='store_true', help='기존 확인표를 시각별 이전 파일로 보존하고 일치하는 행의 확정 값을 이어받아 재생성')
    p.add_argument('--normalize-dates', action='store_true', help='교사의 표기 정리 전부 적용 선택: 유지 포함 확정 값의 날짜 정리; 유지(표기 확인)·유지(잔재 확인) 제외, 승인 후 거부')
    phase = p.add_mutually_exclusive_group()
    phase.add_argument('--calendar'); phase.add_argument('--apply', action='store_true')
    phase.add_argument('--show', action='store_true', help='manifest 기준 현재 확인표 경로·해시·확정 행 수 읽기; 파일 변경 없음')
    phase.add_argument('--fill', metavar='번호범위', help='교사의 묶음 답을 빈 확정 값에만 기록: 37-62 또는 3,5,7-9')


def dispatch(args):
    return {'init': init_workspace, 'school': school, 'prepare': prepare, 'record': record, 'draft': draft,
            'checklist': checklist}[args.command](args)
