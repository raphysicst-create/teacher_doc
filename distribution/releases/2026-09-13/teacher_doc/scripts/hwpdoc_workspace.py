"""Initialization and mechanical preparation for the shared workflow CLI."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

import hwpdoc as h
from hwpdoc_config import MARKER


WORKSPACE_DIRS = ('.hwpdoc/jobs', '.hwpdoc/templates', 'knowledge/reference',
                  'knowledge/examples/md', 'output', 'logs', 'tmp')


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
            '학교 설정은 `.hwpdoc/workspace.json`, PC 설정은 `%LOCALAPPDATA%/hwpdoc/runtime.json`이다. '
            '스킬에서 안내하는 teacher_doc 실행기에 이 작업 폴더를 `--workspace`로 전달한다.\n\n'
            '원본은 보존하고 새 파일을 만든다. 미확인 값·업무 근거·승인·육안 판독을 만들어 넣지 않는다. '
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
                    connections={'school_task_guide': 'unconfirmed', 'kordoc': 'unconfirmed'})
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


def prepare(args):
    from hwpdoc_templates import extracted, folder_for, resolve_template
    h.job_dir(args.job)  # identifier validation, no file creation
    folder = h.workspace_path(Path('.hwpdoc/prepared') / args.job)
    if folder.exists():
        raise ValueError('기존 준비 입력을 덮어쓰지 않습니다. 새 job 식별자를 사용하세요')
    template = args.template
    mapping = None
    if args.version:
        p = folder_for(template, args.version) / 'template.hwpx'
        template = {'id': template, 'version': args.version, 'sha256': h.sha(p)}
        resolved = resolve_template(template)
        mapping = resolved['mapping']
    base = h.template_file({'template': template, 'document_type': args.document_type}) if template else None
    source_files = [h.input_path(s) for s in args.source]
    if any(not p.is_file() for p in source_files):
        raise ValueError('원문 경로를 확인하세요')
    supplied = h.read_json(h.input_path(args.values)) if args.values else {}
    if not isinstance(supplied, dict) or any(not isinstance(v, str) for v in supplied.values()):
        raise ValueError('--values는 의미/슬롯→문자열 JSON이어야 합니다')
    if mapping:
        unknown = set(supplied) - set(mapping)
        if unknown:
            raise ValueError('등록 의미에 없는 값: ' + ', '.join(sorted(unknown)))
        values = {mapping[k]: v for k, v in supplied.items()}
    else:
        values = supplied
    slots = extracted(base) if base else None
    if slots and set(values) - {s['key'] for s in slots['slots']}:
        raise ValueError('추출되지 않은 슬롯 주소')
    folder.mkdir(parents=True)
    sources = []
    for src in source_files:
        digest = h.sha(src)
        dest = folder / 'sources' / (digest[:12] + '-' + src.name)
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(src, dest)
        if h.sha(dest) != digest:
            raise ValueError('원문 가져오기 해시 불일치')
        sources.append({'path': dest.relative_to(h.ROOT).as_posix(), 'sha256': digest,
                        'origin': str(src), 'imported_at': h.now()})
    if slots:
        h.write_json(folder / 'slots.extracted.json', slots)
    missing = ['유사/수신 원문과 양식 선택 근거', '초안 전 업무 근거 조건·예외·최신판 확인',
               '초안 문안과 실제 사용자 확인 기록', '예산명·관련번호·시간표 적용 여부',
               '복사 잔재 이름·날짜와 forbid', '붙임 목록·미확인 사항 검토']
    if mapping:
        missing += ['값 미입력: ' + k for k in mapping if k not in supplied]
    elif slots:
        # Explicit empty strings can mean intentional blanks; only absent keys
        # need a decision. Legacy templates have addresses, not approved meanings.
        missing += ['값 미입력: ' + s['key'] + ' (의미 확인 필요; 기존 문구: '
                    + str(s.get('text', s.get('preview', '')))[:100] + ')'
                    for s in slots['slots'] if s['key'] not in values]
    m = dict(version=2, job_id=args.job, workflow=args.workflow, document_type=args.document_type,
             shared_values={}, sources=sources, evidence={'record': ''}, attachments=[],
             draft={'path': '', 'sha256': '', 'created_at': ''}, draft_approval={'confirmed': False},
             content_rules={'forbid': []},
             checks={k: {'applicable': None} for k in ('budget_names', 'related', 'timetable')},
             environment={'app': h.CONTEXT.settings.get('app', 'unconfirmed'), 'python': sys.version.split()[0],
                          'kordoc': 'unconfirmed', 'school_task_guide': 'unconfirmed'},
             unresolved=missing, base_provenance='unconfirmed', exploration={'record': ''})
    if template:
        m.update(template=template, slots={'template_sha256': h.sha(base), 'values': values})
        if mapping:
            m['base_provenance'] = resolved['registration']['provenance']
    else:
        m.update(source='', expected_values=[])
    if args.workflow == 'W2':
        m['received'] = {'submission_method': None}
        m['unresolved'].append('수신 원문의 제출 방법·기한·문서번호·시행일 확인')
    h.write_json(folder / 'manifest.json', m)
    (folder / '확인할사항.md').write_text('# 작성 전 확인할 사항\n\n' + '\n'.join('- ' + x for x in missing)
        + '\n\n기계적으로 수집한 준비 입력입니다. 승인·업무 근거 해석·육안 판독을 자동 작성하지 않았습니다.\n', encoding='utf-8')
    h.audit('prepare', folder, 'unconfirmed', missing)
    return {'status': 'unconfirmed', 'manifest': str(folder / 'manifest.json'), 'missing': missing,
            'next_action': '미확인 항목을 묶어 확인하고 문안 제시 후 실제 사용자 확인을 기록하세요'}


def add_commands(commands):
    init = commands.add_parser('init')
    init.add_argument('path'); init.add_argument('--app', choices=['claude', 'codex'], required=True)
    init.add_argument('--skill-name', required=True, help='선택한 앱에서 실제 노출을 확인한 스킬 이름')
    init.add_argument('--school'); init.add_argument('--prefix'); init.add_argument('--year', type=int); init.add_argument('--copy-to')
    template = commands.add_parser('add-template')
    template.add_argument('--id', required=True); template.add_argument('--version', required=True)
    phase = template.add_mutually_exclusive_group()
    phase.add_argument('--source'); phase.add_argument('--mapping'); phase.add_argument('--review')
    phase.add_argument('--review-draft', action='store_true', help='필요한 PDF/PNG와 미승인 검토 기록 초안 준비')
    template.add_argument('--purpose', action='append')
    template.add_argument('--provenance', choices=['native', 'converted', 'repackaged', 'unconfirmed'], default='unconfirmed')
    commands.add_parser('list-templates'); commands.add_parser('migrate-templates')
    p = commands.add_parser('prepare')
    p.add_argument('--job', required=True); p.add_argument('--template'); p.add_argument('--version')
    p.add_argument('--source', action='append', default=[]); p.add_argument('--values')
    p.add_argument('--workflow', choices=['W1', 'W2'], default='W1'); p.add_argument('--document-type', required=True)


def dispatch(args):
    from hwpdoc_templates import add_template, list_templates, migrate_legacy
    return {'init': init_workspace, 'add-template': add_template, 'prepare': prepare,
            'list-templates': lambda _: list_templates(), 'migrate-templates': lambda _: migrate_legacy()}[args.command](args)
