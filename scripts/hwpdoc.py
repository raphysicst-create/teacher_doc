"""Ordered, hash-bound HWPX workflow. Existing tool CLIs remain authoritative.

No document prose, approvals or evidence are invented here. An unfinished job
can be delivered only with --draft, visibly marked as unverified.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PYTHON = Path('C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe')
SKILL = ROOT / '.claude/skills/hwpx/scripts'
JOBS = ROOT / '.hwpdoc/jobs'
ONEDRIVE = Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용')
TEMPLATES = ('가정통신문', '가정통신문-회신형', '가정통신문-고사안내', '성립전예산요구', '회의록-교과협의회')
STAGES = ('structure', 'namespaces', 'finalize', 'layout', 'page_guard', 'hancom',
          'render', 'visual_review', 'content', 'values', 'gonmun', 'budget_names', 'related',
          'timetable', 'attachments', 'compare')
NOTICE = '발송 전 한글로 열어 확인해주세요'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def input_path(value):
    p = Path(value)
    return (ROOT / p).resolve() if not p.is_absolute() else p.resolve()


def job_dir(job):
    if not re.fullmatch(r'[A-Za-z0-9가-힣][A-Za-z0-9가-힣_.-]{0,90}', job):
        raise ValueError('job_id는 경로 없는 1~91자 식별자여야 합니다')
    p = (JOBS / job).resolve()
    if not p.is_relative_to(JOBS.resolve()):
        raise ValueError('작업 경로 이탈')
    return p


def audit(action, target, result, detail):
    p = ROOT / 'logs/audit.jsonl'
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(ts=now(), agent='hwpdoc', action=action,
                                    target=str(target), result=result, detail=detail), ensure_ascii=False) + '\n')


@contextmanager
def lock(path):
    """OS file lock releases on crash; serializes COM and each job across processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                stream.write(b'0'); stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError('다른 작업이 실행 중입니다: ' + str(path)) from exc
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        stream.close()


def run(argv, *, timeout=90, com=False):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    def invoke():
        try:
            r = subprocess.run([str(PYTHON), '-X', 'utf8', *map(str, argv)], cwd=ROOT,
                               capture_output=True, text=True, encoding='utf-8', errors='replace',
                               timeout=timeout, env=env)
            return r.returncode, r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            return 124, '시간 초과. COM 잔존 프로세스 여부를 확인해야 합니다; 자동 강제 종료하지 않음.'
        except OSError as exc:
            return 125, str(exc)
    if com:
        with lock(ROOT / '.hwpdoc/hancom.lock'):
            return invoke()
    return invoke()


def approval_payload(m):
    return {k: v for k, v in m.items() if k != 'draft_approval'}


def prerequisite_errors(m, *, build=False):
    errors = []
    required = ('job_id', 'workflow', 'document_type', 'shared_values', 'sources', 'evidence',
                'attachments', 'draft', 'draft_approval', 'content_rules', 'checks', 'environment', 'unresolved')
    for key in required:
        if key not in m:
            errors.append('필수 입력 누락: ' + key)
    if errors:
        return errors
    if m['workflow'] not in ('W1', 'W2'):
        errors.append('workflow는 W1 또는 W2')
    if not m['sources']:
        errors.append('유사 문서/수신 원문 기록 누락')
    evidence = m['evidence']
    if not isinstance(evidence, dict) or not evidence.get('record'):
        errors.append('초안 전 업무 근거 조회 기록 누락')
    else:
        p = input_path(evidence['record'])
        if not p.is_file():
            errors.append('업무 근거 기록 파일 없음: ' + str(p))
        else:
            record = read_json(p)
            if not all(k in record for k in ('status', 'steps', 'conditions', 'exceptions', 'pending_items', 'reviewed_at', 'freshness')):
                errors.append('근거 기록에 조회 단계/조건/예외/미확인/시점/최신판 확인이 필요합니다')
            if record.get('status') not in ('ok', 'partial', 'needs_context', 'unsupported', 'connection_error'):
                errors.append('근거 기록 status 미지원')
            if record.get('status') == 'ok' and record.get('steps') != ['find_tasks', 'get_task_guide', 'search_task_evidence', 'read_evidence']:
                errors.append('업무지침 원문까지 조회한 단계 기록 필요')
            if record.get('status') != 'ok' and not record.get('fallback_sources'):
                errors.append('부분 지원/연결 실패 시 확인한 원문 fallback_sources 필요')
            try:
                if datetime.fromisoformat(record['reviewed_at']) > datetime.fromisoformat(m['draft']['created_at']):
                    errors.append('업무 근거 검토가 초안 작성보다 늦습니다')
            except (KeyError, ValueError, TypeError):
                errors.append('근거 검토/초안 시각이 올바르지 않습니다')
    approval = m['draft_approval']
    draft = m['draft']
    if approval.get('confirmed') is not True or not approval.get('by') or not approval.get('at') or not approval.get('record'):
        errors.append('사용자 초안 확인 기록이 필요합니다')
    if not input_path(draft.get('path', '')).is_file():
        errors.append('초안 파일 없음')
    elif draft.get('sha256') != sha(input_path(draft['path'])):
        errors.append('확인 대상 초안 해시 불일치')
    if approval.get('input_sha256') != json_hash(approval_payload(m)):
        errors.append('초안 확인 후 입력이 달라졌습니다: input_sha256 불일치')
    try:
        if datetime.fromisoformat(approval['at']) < datetime.fromisoformat(draft['created_at']):
            errors.append('초안 작성 이전 승인 기록')
    except (ValueError, KeyError, TypeError):
        errors.append('초안 승인 시각이 올바르지 않습니다')
    for item in m['sources'] + m['attachments']:
        if not isinstance(item, dict) or not item.get('path') or not input_path(item['path']).is_file():
            errors.append('원문/첨부 파일 없음: ' + str(item))
    if m['workflow'] == 'W1' and not m.get('exploration', {}).get('record'):
        errors.append('W1 유사 공문·양식 탐색 기록 누락')
    if m['workflow'] == 'W2':
        received = m.get('received', {})
        if received.get('submission_method') not in ('official_reply', 'system', 'email'):
            errors.append('W2 제출 방법 미확인: 사용자 확인 필요')
        for key in ('summary', 'requirements', 'deadline', 'document_number', 'issue_date', 'source_quote'):
            if not received.get(key):
                errors.append('W2 수신 원문에서 확인할 값: ' + key)
    for key in ('budget_names', 'related', 'timetable'):
        check = m['checks'].get(key)
        if not isinstance(check, dict) or not isinstance(check.get('applicable'), bool):
            errors.append('조회 도구 적용 여부 누락: ' + key)
        elif check['applicable'] is False and not check.get('reason'):
            errors.append('해당 없음 이유 누락: ' + key)
    if build:
        if m.get('template') not in TEMPLATES:
            errors.append('자동 생성은 슬롯 템플릿 5종만 지원합니다')
        if m.get('structure_change'):
            errors.append('구조 변경 필요: 기존 승인·재생성·렌더 경로로 진행하세요')
        for group in m.get('activities', []):
            if len(group.get('items', [])) > len(group.get('slot_keys', [])):
                errors.append('활동 행 부족: ' + str(group.get('location')) + ' — 병합하지 말고 구조 변경 경로로 진행하세요')
    if m.get('reference') or m.get('template'):
        rules = m['content_rules']
        if not rules.get('forbid') or not m.get('reuse_review', {}).get('record'):
            errors.append('재사용 문서의 고유 명칭·옛 날짜 forbid와 검토 기록 필요')
        review = m.get('reuse_review', {})
        for key in ('names', 'dates'):
            if not isinstance(review.get(key), list):
                errors.append('복사 잔재 점검 목록 누락: reuse_review.' + key)
            elif not review[key] and not review.get(key + '_empty_reason'):
                errors.append('복사 잔재 목록이 빈 이유 필요: ' + key)
            elif any(x not in rules.get('forbid', []) for x in review[key]):
                errors.append('복사 잔재 점검 목록은 모두 content_rules.forbid에 포함해야 합니다: ' + key)
    if m.get('shared_values_file') and not input_path(m['shared_values_file']).is_file():
        errors.append('공유값 단일 소스 파일 없음')
    return errors


def resolved_values(m):
    shared = read_json(input_path(m['shared_values_file'])) if m.get('shared_values_file') else m['shared_values']
    values = {}
    for key, value in m.get('slots', {}).get('values', {}).items():
        if isinstance(value, dict) and set(value) == {'shared'}:
            if value['shared'] not in shared:
                raise ValueError('공유값 누락: ' + value['shared'])
            value = shared[value['shared']]
        values[key] = value
    return values


def dependencies(m):
    paths = [input_path(m['draft']['path']), input_path(m['evidence']['record'])]
    paths += [input_path(x['path']) for x in m['sources'] + m['attachments']]
    if m.get('template'):
        paths += list((ROOT / 'knowledge/templates' / m['template']).glob('*'))
    for key in ('source', 'reference'):
        if m.get(key):
            paths.append(input_path(m[key]))
    if m.get('shared_values_file'):
        paths.append(input_path(m['shared_values_file']))
    visual = m.get('visual_review', {})
    if visual.get('pdf'):
        paths.append(input_path(visual['pdf']['path']))
    paths += [input_path(x['path']) for x in visual.get('images', [])]
    paths += list(SKILL.glob('*.py')) + [ROOT / 'CLAUDE.md', Path(__file__).resolve(), ROOT / 'scripts/render_check.py']
    paths += [ROOT / 'scripts' / n for n in ('budget_name_check.py', 'related_lookup.py', 'fusion_timetable.py')]
    paths += list((ROOT / 'knowledge/reference').glob('*'))
    if m['checks']['related'].get('applicable'):
        paths += list((ROOT / 'knowledge/examples/md').glob('*.md'))
    return {str(p.resolve()): sha(p) for p in paths if p.is_file()}


def freshness(report):
    changed = []
    for name, digest in report.get('dependencies', {}).items():
        if not Path(name).is_file() or sha(name) != digest:
            changed.append(name)
    work = Path(report['work_file'])
    if report.get('validated_sha256') and (not work.is_file() or sha(work) != report['validated_sha256']):
        changed.append(str(work))
    manifest = Path(report['manifest_file'])
    if not manifest.is_file() or sha(manifest) != report['manifest_sha256']:
        changed.append(str(manifest))
    return changed


def result_state(report):
    if freshness(report):
        return 'unconfirmed'
    states = [report.get('stages', {}).get(s, {}).get('status', 'unconfirmed') for s in STAGES]
    if 'fail' in states:
        return 'fail'
    if report.get('unresolved') or 'unconfirmed' in states or not report.get('validated_sha256'):
        return 'unconfirmed'
    return 'pass'


def save_report(report):
    report['updated_at'] = now()
    report['status'] = result_state(report)
    report['next_action'] = ('사람 최종 검토; ' + NOTICE if report['status'] == 'pass'
                             else '실패/미확인 단계와 변경 파일 확인; 값을 지어내지 말고 질문 또는 기존 수동 경로 사용')
    write_json(job_dir(report['job_id']) / 'report.json', report)


def stage(report, name, argv=None, *, status=None, reason='', com=False):
    previous = report['stages'].get(name, {})
    failures = previous.get('failures', 0)
    before = sha(report['work_file']) if Path(report['work_file']).is_file() else None
    if argv is None:
        code, output = None, reason
        state = status or 'unconfirmed'
    elif failures >= 2:
        code, output, state = None, '동일 단계 2회 실패: 자동 시도 중단. 사람 확인 필요.', 'fail'
    else:
        code, output = run(argv, com=com)
        unavailable = code in (124, 125) or (com and re.search('검사 불가|not installed|only available|COM .*failed', output, re.I))
        state = 'pass' if code == 0 else ('unconfirmed' if unavailable else 'fail')
        if code:
            failures += 1
    entry = dict(status=state, reason=output, failures=failures, exit_code=code,
                 before_sha256=before, after_sha256=sha(report['work_file']) if Path(report['work_file']).is_file() else None,
                 at=now(), command=list(map(str, argv)) if argv else None,
                 warnings=[line for line in output.splitlines() if re.search('warning|경고', line, re.I)])
    report['stages'][name] = entry
    report['history'].append(dict(stage=name, **entry))
    save_report(report)
    audit(name, report['work_file'], state, output[:1500])
    return state in ('pass', 'not_applicable')


def initialize(manifest_file, *, build):
    manifest_file = input_path(manifest_file)
    m = read_json(manifest_file)
    folder = job_dir(m['job_id'])
    if (folder / 'report.json').exists():
        raise ValueError('기존 작업은 덮어쓰지 않습니다. status/validate 또는 새 job_id를 사용하세요')
    errors = prerequisite_errors(m, build=build)
    if errors:
        # Record rejected attempts too, without overwriting an earlier job.
        audit('preflight', manifest_file, 'unconfirmed', errors)
        folder.mkdir(parents=True, exist_ok=True)
        write_json(folder / 'preflight.json', {'status': 'unconfirmed', 'errors': errors, 'at': now()})
        raise ValueError('\n'.join(errors))
    folder.mkdir(parents=True, exist_ok=True)
    source = (ROOT / 'knowledge/templates' / m['template'] / '양식.hwpx') if build else input_path(m['source'])
    if source.suffix.lower() != '.hwpx' or not source.is_file():
        raise ValueError('기존 경로에서 생성된 HWPX만 입력할 수 있습니다')
    work = folder / 'work.hwpx'
    shutil.copy2(source, work)
    report = dict(version=1, job_id=m['job_id'], workflow=m['workflow'], manifest_file=str(manifest_file),
                  manifest_sha256=sha(manifest_file), work_file=str(work), dependencies=dependencies(m),
                  stages={}, history=[], unresolved=list(m['unresolved']), environment=m['environment'],
                  created_at=now(), notice=NOTICE, semantic_evidence_assurance=False)
    er = read_json(input_path(m['evidence']['record']))
    report['evidence'] = er
    report['unresolved'] += er.get('pending_items', [])
    if er.get('freshness') != 'verified':
        report['unresolved'].append('업무 근거 적용기간/최신판 미확인')
    save_report(report)
    return m, report


def build_document(manifest_file):
    m, report = initialize(manifest_file, build=True)
    folder = job_dir(m['job_id'])
    template = ROOT / 'knowledge/templates' / m['template'] / '양식.hwpx'
    sys.path.insert(0, str(SKILL))
    from hwpx_slots import collect_slots
    extracted = collect_slots(template)
    slots = {x['key']: x for x in extracted['slots']}
    values = {}
    errors = []
    supplied = m.get('slots', {})
    if supplied.get('template_sha256') != sha(template) or not supplied.get('values'):
        errors.append('추출 슬롯의 템플릿 해시 또는 values 누락')
    for key, value in resolved_values(m).items():
        if key not in slots or not isinstance(value, str):
            errors.append('추출되지 않은 슬롯 또는 문자열 아닌 값: ' + key); continue
        limit = slots[key]['max_chars']
        if limit and len(''.join(value.split())) > limit:
            errors.append(f'{key}: {len("".join(value.split()))}>{limit}자, 예산 초과 — 내용 보존·구조 변경·렌더 확인 필요')
        values[key] = value
    for group in m.get('activities', []):
        for item, key in zip(group.get('items', []), group.get('slot_keys', [])):
            if values.get(key) != item:
                errors.append('활동명 훼손/매핑 불일치: ' + key)
    if errors:
        stage(report, 'build', status='unconfirmed', reason='\n'.join(errors))
        return report
    write_json(folder / 'slots.extracted.json', extracted)
    write_json(folder / 'values.json', values)
    stage(report, 'build', [SKILL / 'edit_hwpx.py', template, '-o', report['work_file'], '--slot-json', folder / 'values.json'])
    return report


def validate_document(report):
    sys.path.insert(0, str(SKILL))
    m = read_json(report['manifest_file'])
    changed = freshness(report)
    if changed:
        # A work-file-only edit can be revalidated; approved input/reference changes cannot.
        other = [x for x in changed if x != report['work_file']]
        if other:
            raise ValueError('승인 입력/근거/검증 도구 변경: 새 확인과 새 job_id 필요\n' + '\n'.join(other))
    report.pop('validated_sha256', None)
    for name in STAGES:
        old = report['stages'].get(name, {})
        report['stages'][name] = {'status': 'unconfirmed', 'reason': '이번 파일 전체 검증 대기', 'failures': old.get('failures', 0)}
    save_report(report)
    if 'build' in report['stages'] and report['stages']['build']['status'] != 'pass':
        raise ValueError('build 미통과: work 사본을 생성 완료본으로 검증할 수 없습니다')
    f = Path(report['work_file']); folder = f.parent
    sequence = [('structure', [SKILL / 'validate.py', f]),
                ('namespaces', [SKILL / 'fix_namespaces.py', f]),
                ('finalize', [SKILL / 'finalize_hwpx.py', f, '--strip-linesegarray', '--layout']),
                ('layout', [SKILL / 'validate.py', f, '--layout'])]
    for name, argv in sequence:
        if not stage(report, name, argv):
            if name == 'structure' and report['stages'][name]['failures'] < 2:
                if stage(report, name, argv):
                    continue
            report['fallback_next'] = ('validate 2회 실패: hwpx-fallback F(양식 있음)/A(없음), strict 검사 후 주력 전체 검증' if name == 'structure' else '현재 단계 수정 후 재검증')
            save_report(report)
            return report
    reference = input_path(m['reference']) if m.get('reference') else ((ROOT / 'knowledge/templates' / m['template'] / '양식.hwpx') if m.get('template') else None)
    if reference:
        ref = folder / 'reference.finalized.hwpx'
        shutil.copy2(reference, ref)
        # Profiles are generated only from the finalized reference COPY.
        for name, argv in [('reference_namespaces', [SKILL / 'fix_namespaces.py', ref]),
                           ('reference_finalize', [SKILL / 'finalize_hwpx.py', ref, '--strip-linesegarray']),
                           ('reference_profiles', [SKILL / 'page_guard.py', '--reference', ref,
                                                  '--write-budget', folder / 'budget.json', '--write-structure', folder / 'structure.json'])]:
            if not stage(report, name, argv):
                return report
        page_ok = stage(report, 'page_guard', [SKILL / 'page_guard.py', '--reference', ref, '--output', f,
                  '--budget-profile', folder / 'budget.json', '--structure-profile', folder / 'structure.json',
                  '--no-strict-paragraph-budget', '--skip-text-drift', '--allow-empty-fill'])
        if not page_ok:
            report['structure_next'] = '실패 위치를 검토하세요. 활동 병합·내용 축약·구조 프로파일 재승인·검증 플래그 우회는 자동 수행하지 않습니다.'
    else:
        stage(report, 'page_guard', reason='기준 문서/승인된 구조 프로파일 없음: 기존 경로로 기준 확인 필요')
    stage(report, 'hancom', [SKILL / 'finalize_hwpx.py', f, '--hancom'], com=True)
    provenance = m.get('base_provenance')
    if provenance in ('converted', 'repackaged') or m.get('over_budget_cells'):
        if not reference:
            stage(report, 'render', reason='조건부 렌더 기준 파일 누락')
        else:
            stage(report, 'render', [ROOT / 'scripts/render_check.py', f, '--reference', reference, '--keep-pdf', folder / 'render.pdf'], com=True)
    elif provenance == 'native':
        stage(report, 'render', status='not_applicable', reason='네이티브 HWPX 일반 편집, 예산 초과 없음')
    else:
        stage(report, 'render', reason='base_provenance 미확인')
    if m.get('over_budget_cells'):
        review = m.get('visual_review', {})
        artifacts = [review.get('pdf', {}), *review.get('images', [])]
        reviewed = (review.get('confirmed') is True and review.get('by') and review.get('at') and review.get('record')
                    and review.get('document_sha256') == sha(f) and review.get('images')
                    and all(x in review.get('cells', []) for x in m['over_budget_cells'])
                    and all(x.get('path') and input_path(x['path']).is_file() and x.get('sha256') == sha(input_path(x['path'])) for x in artifacts))
        stage(report, 'visual_review', status='pass' if reviewed else 'unconfirmed',
              reason='현재 문서 해시와 연결된 PDF·PNG 육안 판독 기록 확인' if reviewed else '예산 초과 셀 PDF→PNG 육안 판독 증거 필요. 자동 우회하지 않습니다.')
    else:
        stage(report, 'visual_review', status='not_applicable', reason='신고된/자동 편집 예산 초과 없음')
    content_rules = dict(m['content_rules'])
    content_rules['forbid_regex'] = [*content_rules.get('forbid_regex', []), r'\[\[[^\]]+\]\]']
    write_json(folder / 'content.rules.json', content_rules)
    stage(report, 'content', [SKILL / 'content_guard.py', f, '--rules', folder / 'content.rules.json'])
    if m.get('slots', {}).get('values'):
        from hwpx_slots import collect_slots
        actual = {x['key']: x['preview'] for x in collect_slots(f, preview_len=1000000)['slots']}
        mismatches = [key for key, value in resolved_values(m).items()
                      if actual.get(key, '') != ' '.join(value.split())]
        stage(report, 'values', status='fail' if mismatches else 'pass', reason='승인 슬롯값 대조: ' + str(mismatches or '일치'))
    elif m.get('expected_values'):
        from text_extract import extract_plain
        visible = extract_plain(f, include_tables=True)
        missing = [v for v in m['expected_values'] if v not in visible]
        stage(report, 'values', status='fail' if missing else 'pass', reason='기존 경로의 필수값 대조: ' + str(missing or '일치'))
    else:
        stage(report, 'values', reason='기존 경로 검증에 expected_values(원문에서 확인한 필수값)가 필요합니다')
    stage(report, 'gonmun', [SKILL / 'gonmun_lint.py', '--hwpx', f, '--format', 'json'])
    for name in ('budget_names', 'related', 'timetable'):
        check = m['checks'][name]
        if not check['applicable']:
            stage(report, name, status='not_applicable', reason=check['reason']); continue
        if name == 'budget_names' and check.get('names'):
            stage(report, name, [ROOT / 'scripts/budget_name_check.py', *[arg for value in check['names'] for arg in ('--check', value)]])
        elif name == 'related' and check.get('numbers'):
            failures = []
            for number in check['numbers']:
                sub = 'related:' + str(number)
                if not stage(report, sub, [ROOT / 'scripts/related_lookup.py', '--doc', str(number)]):
                    failures.append(number)
            stage(report, name, status='fail' if failures else 'pass', reason='관련번호 조회 실패: ' + str(failures) if failures else '모든 관련번호 조회 통과; 시행일·원문 인용은 근거 기록과 사람 검토 필요')
        elif name == 'timetable' and check.get('dates') and check.get('periods'):
            argv = [ROOT / 'scripts/fusion_timetable.py', *check['dates'], '--periods', check['periods'], '--json']
            if check.get('grades'):
                argv += ['--grades', check['grades']]
            stage(report, name, argv)
        else:
            stage(report, name, reason='필수 조회 입력 누락: ' + name)
    # Compare only visible text; no inferred nth row/column addressing.
    sys.path.insert(0, str(SKILL))
    from text_extract import extract_plain
    text = extract_plain(f, include_tables=True)
    mentions = m.get('attachment_mentions')
    if mentions is None:
        stage(report, 'attachments', reason='본문 붙임 언급 목록 확인 기록 누락')
    else:
        titles = [x.get('title') for x in m['attachments']]
        ok = mentions == titles and all(isinstance(x, str) and x in text for x in mentions)
        if not mentions and '붙임' in text:
            ok = False
        stage(report, 'attachments', status='pass' if ok else 'fail', reason='본문 붙임 제목·실제 첨부 목록 대조 ' + ('통과' if ok else '불일치'))
    if reference:
        original = extract_plain(reference, include_tables=True)
        diff = '\n'.join(difflib.unified_diff(original.splitlines(), text.splitlines(), fromfile=str(reference), tofile=str(f), lineterm=''))
        (folder / 'compare.diff').write_text(diff, encoding='utf-8')
        stage(report, 'compare', status='pass', reason='kordoc 미사용(실행기 프로세스에 MCP 세션 미연결): text_extract 신구대조 compare.diff 생성')
    else:
        stage(report, 'compare', status='not_applicable', reason='비교할 원본 없음')
    report['validated_sha256'] = sha(f)
    save_report(report)
    return report


def delivery(report, *, draft=False, destination=ONEDRIVE):
    state = result_state(report)
    if freshness(report):
        raise ValueError('검증 이후 파일/입력 변경. validate를 먼저 실행하세요')
    if state != 'pass' and not draft:
        raise ValueError('전체 검증 미통과. 미확인 검토 초안은 deliver --draft로만 저장할 수 있습니다')
    if report['stages'].get('build', {}).get('status', 'pass') != 'pass':
        raise ValueError('build 미완료: 편집하지 않은 템플릿 사본은 배달하지 않습니다')
    folder = ROOT / 'output' / report['job_id']
    folder.mkdir(parents=True, exist_ok=True)
    label = '검증완료_검토대기' if state == 'pass' else '미확인_검토초안'
    target = folder / (label + '.hwpx')
    work = Path(report['work_file'])
    if target.exists() and sha(target) != sha(work):
        raise ValueError('기존 검토본 덮어쓰기 금지: 새 job_id를 사용하세요')
    shutil.copy2(work, target)
    snapshot = dict(report, delivery_status=state, human_review='pending', sent=False)
    write_json(folder / '검토보고서.json', snapshot)
    lines = [f'# {report["job_id"]}: {label}', '', NOTICE, '', '사람 검토 대기 · 발송은 사람이 합니다.', '',
             '업무 근거 해석의 정확성은 실행기가 보증하지 않습니다.', '', f'파일 SHA256: {sha(work)}', '']
    lines += [f'- {name}: {entry["status"]} — {entry.get("reason", "")[:500]}' for name, entry in report['stages'].items()]
    lines += ['', '미확인: ' + json.dumps(report.get('unresolved', []), ensure_ascii=False)]
    (folder / '검토보고서.md').write_text('\n'.join(lines), encoding='utf-8')
    m = read_json(report['manifest_file'])
    files = [target, folder / '검토보고서.json', folder / '검토보고서.md']
    for attachment in m['attachments']:
        src = input_path(attachment['path']); dest = folder / src.name
        if dest.exists() and sha(dest) != sha(src):
            raise ValueError('첨부 파일명 충돌: ' + src.name)
        shutil.copy2(src, dest); files.append(dest)
    failures = report.get('copy', {}).get('failures', 0)
    if failures >= 2:
        raise ValueError('OneDrive 복사 2회 실패: 자동 시도 중단. 로컬 검토본은 보존했습니다')
    try:
        if not destination.is_dir():
            raise OSError('OneDrive 작업 보고용 폴더 없음: ' + str(destination))
        destdir = destination / report['job_id']; destdir.mkdir(exist_ok=True)
        for source in files:
            dest = destdir / source.name
            if dest.exists() and sha(dest) != sha(source) and source.suffix == '.hwpx':
                raise OSError('OneDrive 기존 검토본 보호: ' + str(dest))
            shutil.copy2(source, dest)
            if sha(dest) != sha(source):
                raise OSError('복사 해시 불일치: ' + str(dest))
        report['copy'] = dict(status='pass', failures=failures, directory=str(destdir), at=now())
    except OSError as exc:
        report['copy'] = dict(status='fail', failures=failures + 1, reason=str(exc), at=now())
    report['delivery'] = dict(local=str(target), status=state, human_review='pending', sent=False)
    save_report(report)
    # Export the final copy receipt too; never leave the previous attempt's state
    # in the local review report after a copy-only retry.
    receipt = folder / '검토보고서.json'
    write_json(receipt, dict(report, delivery_status=state, human_review='pending', sent=False))
    if report['copy']['status'] == 'pass':
        try:
            remote_receipt = Path(report['copy']['directory']) / receipt.name
            shutil.copy2(receipt, remote_receipt)
            if sha(receipt) != sha(remote_receipt):
                raise OSError('최종 복사 보고서 해시 불일치')
        except OSError as exc:
            report['copy'] = dict(status='fail', failures=failures + 1, reason=str(exc), at=now())
            save_report(report)
            write_json(receipt, dict(report, delivery_status=state, human_review='pending', sent=False))
    audit('deliver', target, report['copy']['status'], report['copy'])
    return report


def doctor():
    checks = {'python': {'status': 'pass' if PYTHON.is_file() and Path(sys.executable).resolve() == PYTHON.resolve() else 'fail', 'path': sys.executable}}
    for module in ('lxml', 'hwpx', 'win32com', 'fitz'):
        checks[module] = {'status': 'pass' if importlib.util.find_spec(module) else 'fail'}
    for name in TEMPLATES:
        folder = ROOT / 'knowledge/templates' / name
        missing = [x for x in ('양식.hwpx', 'slots.json', 'budget.json', 'structure.json', 'README.md') if not (folder / x).is_file()]
        checks[name] = dict(status='fail' if missing else 'pass', missing=missing)
    for name, path in [('output', ROOT / 'output'), ('onedrive', ONEDRIVE)]:
        checks[name] = dict(status='pass' if path.is_dir() and os.access(path, os.W_OK) else 'unconfirmed', path=str(path), note='실제 복사 성공은 deliver에서 별도 확인')
    with lock(ROOT / '.hwpdoc/hancom.lock'):
        code, output = run([ROOT / 'scripts/hwpdoc_com_probe.py'])
    checks['hancom'] = dict(status='pass' if code == 0 else 'unconfirmed', detail=output)
    result = {'at': now(), 'checks': checks, 'note': '환경 진단은 문서 검증이나 앱 통합 인수가 아닙니다'}
    write_json(ROOT / '.hwpdoc/doctor.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor')
    build = commands.add_parser('build'); build.add_argument('--manifest', required=True)
    validate = commands.add_parser('validate')
    group = validate.add_mutually_exclusive_group(required=True)
    group.add_argument('--job'); group.add_argument('--manifest')
    deliver = commands.add_parser('deliver'); deliver.add_argument('--job', required=True); deliver.add_argument('--draft', action='store_true')
    status = commands.add_parser('status'); status.add_argument('--job', required=True)
    args = parser.parse_args()
    try:
        if Path(sys.executable).resolve() != PYTHON.resolve():
            raise RuntimeError('고정 Python312가 필요합니다. scripts/hwpdoc.ps1을 사용하세요')
        if args.command == 'doctor':
            print(json.dumps(doctor(), ensure_ascii=False, indent=2)); return 0
        job = args.job if getattr(args, 'job', None) else read_json(input_path(args.manifest))['job_id']
        with lock(job_dir(job) / '.lock'):
            if args.command == 'build':
                report = build_document(args.manifest)
            elif args.command == 'validate':
                report = (initialize(args.manifest, build=False)[1] if args.manifest else read_json(job_dir(job) / 'report.json'))
                report = validate_document(report)
            else:
                report_file = job_dir(job) / 'report.json'
                preflight_file = job_dir(job) / 'preflight.json'
                if args.command == 'status' and not report_file.exists() and preflight_file.exists():
                    print(json.dumps(dict(job_id=job, **read_json(preflight_file), next_action='누락/미확인 입력을 사용자에게 확인하세요. 생성하지 않았습니다.'), ensure_ascii=False, indent=2))
                    return 2
                report = read_json(report_file)
                if args.command == 'deliver':
                    report = delivery(report, draft=args.draft)
                else:
                    save_report(report)
            print(json.dumps({'job_id': job, 'status': result_state(report), 'report': str(job_dir(job) / 'report.json'),
                              'changed_files': freshness(report), 'copy': report.get('copy'), 'next_action': report['next_action']}, ensure_ascii=False, indent=2))
            if args.command == 'build':
                return 0 if report['stages'].get('build', {}).get('status') == 'pass' else 2
            if args.command == 'deliver':
                return 0 if report.get('copy', {}).get('status') == 'pass' else 1
            return {'pass': 0, 'fail': 1, 'unconfirmed': 2}[result_state(report)]
    except (ValueError, KeyError, OSError, RuntimeError, TypeError) as exc:
        print(json.dumps({'status': 'unconfirmed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
