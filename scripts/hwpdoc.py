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
import tempfile
import time
import copy
from zipfile import BadZipFile
# Inspection commands must not create bytecode alongside the installed tools.
sys.dont_write_bytecode = True
from hwpdoc_config import load_context, Context
from hwpdoc_runtime import snapshot as runtime_snapshot, diagnostics as runtime_diagnostics
sys.modules.setdefault('hwpdoc', sys.modules[__name__])

CODE_ROOT = Path(__file__).resolve().parent.parent
# The CLI can initialize a workspace before one exists.
try:
    CONTEXT = load_context()
except ValueError:
    CONTEXT = None
ROOT = CONTEXT.workspace if CONTEXT else CODE_ROOT
PYTHON = CONTEXT.python if CONTEXT else Path(sys.executable)
SKILL = CONTEXT.skill if CONTEXT else CODE_ROOT / 'skills/hwpx/scripts'
JOBS = ROOT / '.hwpdoc/jobs'
ONEDRIVE = CONTEXT.external_copy if CONTEXT else None
STAGES = ('structure', 'namespaces', 'finalize', 'layout', 'shading', 'page_guard', 'hancom',
          'render', 'visual_review', 'content', 'values', 'gonmun', 'budget_names', 'related',
          'timetable', 'attachments', 'compare')
NOTICE = '발송 전 한글로 열어 확인해주세요'


def configure(workspace=None):
    global CONTEXT, ROOT, PYTHON, SKILL, JOBS, ONEDRIVE
    CONTEXT = load_context(workspace)
    ROOT, PYTHON, SKILL = CONTEXT.workspace, CONTEXT.python, CONTEXT.skill
    JOBS, ONEDRIVE = ROOT / '.hwpdoc/jobs', CONTEXT.external_copy


def path_context():
    return Context(CODE_ROOT, ROOT, CONTEXT.pc_data if CONTEXT else ROOT, {}, PYTHON)


def workspace_path(relative):
    return path_context().local(relative)


def template_file(m):
    """편집 베이스는 prepare --base가 보존한 미등록 일회성 사본뿐이다 (양식 등록부는 0.2.0에서 폐지)."""
    base = m.get('base')
    if not base:
        raise ValueError('미등록 일회성 베이스(--base)가 필요합니다')
    if base.get('kind') != 'unregistered_one_off':
        raise ValueError('지원하지 않는 베이스 종류')
    path = workspace_path(base['path'])
    if path.suffix.lower() != '.hwpx' or not path.is_file() or base.get('sha256') != sha(path):
        raise ValueError('일회성 베이스 사본 없음/해시 불일치')
    return path


def report_record(report, *, decode=False):
    """Only path fields are translated; manifests and approval hashes are untouched."""
    result = copy.deepcopy(report)
    if decode and result.get('path_format') != 2:
        return result
    convert = (lambda p: str(path_context().decode(p))) if decode else path_context().encode
    for key in ('work_file', 'manifest_file'):
        result[key] = convert(result[key])
    result['dependencies'] = {convert(p): digest for p, digest in result['dependencies'].items()}
    if 'visual_review_dependencies' in result:
        result['visual_review_dependencies'] = [convert(p) for p in result['visual_review_dependencies']]
    if 'tool_dependencies' in result:
        result['tool_dependencies'] = {convert(p): digest for p, digest in result['tool_dependencies'].items()}
    for name in ('delivery', 'copy'):
        for key in ('local', 'directory'):
            if result.get(name, {}).get(key):
                result[name][key] = convert(result[name][key])
    for entry in [*result.get('stages', {}).values(), *result.get('history', [])]:
        if entry.get('command'):
            entry['command'] = [convert(v) if v.startswith(('workspace:', 'plugin:')) or Path(v).is_absolute() else v for v in entry['command']]
    result['path_format'] = 2
    return result


def load_report(path):
    return report_record(read_json(path), decode=True)


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
    try:
        os.replace(temp, path)
    except PermissionError:
        # Observed Windows transient file lock. Retry I/O once, not a validation stage.
        time.sleep(0.05)
        os.replace(temp, path)


def input_path(value):
    p = Path(value)
    return (ROOT / p).resolve() if not p.is_absolute() else p.resolve()


def original_input_path(value):
    path = input_path(value)
    if path.is_relative_to((ROOT / '.hwpdoc').resolve()):
        raise ValueError('원본은 .hwpdoc 밖에 두세요: ' + str(value))
    return path


def validate_job_id(job):
    if not isinstance(job, str) or not re.fullmatch(r'[A-Za-z0-9가-힣][A-Za-z0-9가-힣_.-]{0,90}', job):
        raise ValueError('job_id는 경로 없는 1~91자 식별자여야 합니다')


def job_dir(job):
    validate_job_id(job)
    p = (JOBS / job).resolve()
    if not JOBS.resolve().is_relative_to(ROOT.resolve()) or not p.is_relative_to(JOBS.resolve()):
        raise ValueError('작업 경로 이탈')
    return p


def audit(action, target, result, detail):
    p = workspace_path('logs/audit.jsonl')
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
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1', HWPDOC_WORKSPACE=str(ROOT), PYTHONDONTWRITEBYTECODE='1')
    def invoke():
        try:
            r = subprocess.run([str(PYTHON), '-X', 'utf8', *map(str, argv)], cwd=ROOT,
                               capture_output=True, text=True, encoding='utf-8', errors='replace',
                               timeout=timeout, env=env)
            return r.returncode, r.stdout + r.stderr
        except subprocess.TimeoutExpired as exc:
            def decode(value):
                return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else (value or '')
            return 124, decode(exc.stdout) + decode(exc.stderr) + '\n시간 초과. COM 잔존 프로세스 여부를 확인해야 합니다; 자동 강제 종료하지 않음.'
        except OSError as exc:
            return 125, str(exc)
    if com:
        with lock(workspace_path('.hwpdoc/hancom.lock')):
            return invoke()
    return invoke()


def approval_payload(m):
    return {k: v for k, v in m.items() if k != 'draft_approval'}


MANIFEST_GUIDANCE = {
    'record': '준비 기록은 record --job <이름> --file <UTF-8 JSON>으로 등록합니다. 임시 Python으로 manifest를 고치지 않습니다. 파일 해시는 실행기가 계산합니다. 승인 기록은 approve, 편집값·유지 목록·확인표는 checklist --apply로만 기록합니다. 실제 미확인 사항 추가는 unresolved_add이며, 승인 뒤 입력 변경은 revise로 새 작업을 만듭니다.',
    'version': '입력 계약 버전 정수 2. 경로는 작업 폴더 기준 상대경로로 기록합니다.',
    'job_id': 'prepare에서 지정한 경로 없는 작업 ID 문자열을 유지합니다. 기존 보고서가 있는 작업은 덮어쓰지 않으므로 새 작업ID를 사용합니다.',
    'workflow': '신규는 W1, 회신은 W2 문자열입니다.',
    'document_type': '요청한 문서 유형 문자열입니다.',
    'shared_values': '본문·붙임에 함께 넣을 의미→문자열 JSON 객체입니다. 없으면 {}입니다.',
    'shared_values_file': '선택 사항: shared_values 대신 읽을 의미→문자열 JSON 파일 상대경로입니다.',
    'sources': '확인한 유사/수신 원문 목록 [{"path":"상대경로","sha256":"그 원문 파일 바이트의 SHA256"}]입니다. 최소 1건입니다.',
    'attachments': '실제 붙임 목록 [{"path":"상대경로","title":"본문 붙임 제목","sha256":"그 붙임 파일 바이트의 SHA256"}]입니다. 없으면 []입니다.',
    'attachment_mentions': '본문에서 확인한 붙임 제목 문자열 배열입니다. attachments의 title 순서와 맞추며, 붙임이 없음을 확인했으면 []입니다. 미확인은 null로 둡니다.',
    'draft.path': '교사에게 보여줄 초안 파일의 상대경로입니다.',
    'draft.sha256': 'draft.path가 가리키는 초안 파일 바이트의 SHA256(소문자 64자리)입니다.',
    'draft.created_at': '초안을 작성한 실제 시각을 ISO 8601(시간대 포함) 문자열로 기록합니다.',
    'draft_approval.confirmed': '교사 확인 후: 제시한 초안의 파일 생성을 실제 확인받았을 때만 true로 기록합니다.',
    'draft_approval.by': '교사 확인 후: 실제 확인한 사람을 문자열로 기록합니다.',
    'draft_approval.at': '교사 확인 후: 실제 확인 시각을 ISO 8601(시간대 포함)로 기록합니다. draft.created_at 이전일 수 없습니다. 동일 내용 이월이면 이월 처리 시각이고, 원래 교사 확인 시각은 draft_approval.carried_forward_from.approval.at에 보존합니다.',
    'draft_approval.carried_forward_from': 'approve --carry-forward-from이 동일 내용을 대조한 뒤 기록하는 이전 job_id·manifest_sha256·approval(by/at/record/input_sha256)·teacher_content_sha256입니다. 새 교사 확인을 만들지 않습니다.',
    'draft_approval.record': '교사 확인 후: 제시한 문안에 대한 실제 사용자 응답을 문자열로 기록합니다. 승인 문구를 만들어 넣지 않습니다.',
    'draft_approval.input_sha256': '교사 확인 후: hwpdoc.json_hash(hwpdoc.approval_payload(manifest)) 값입니다. draft_approval을 제외한 manifest를 ensure_ascii=False, sort_keys=True, separators=(",",":")로 JSON 직렬화한 UTF-8 바이트의 SHA256입니다. 파일 자체의 해시가 아닙니다. 입력 변경 시 초안을 다시 확인받으며 해시만 보완해 승인을 유지하지 않습니다.',
    'exploration.record': 'W1: 읽은 유사 공문·양식 경로, 선택 이유와 보존할 배치를 문자열로 기록합니다.',
    'content_rules.forbid': '재사용 원문에서 확인한 고유 명칭·옛 날짜 문자열 배열입니다. reuse_review.names/dates의 모든 항목을 포함합니다. 더미 금지어를 쓰지 않습니다.',
    'reuse_review.record': '재사용 원문에서 고유 명칭·옛 날짜를 실제 검토한 내용을 문자열로 기록합니다.',
    'reuse_review.names': '원문에서 확인한 이전 고유 명칭 문자열 배열입니다. 없음을 확인했으면 []입니다.',
    'reuse_review.dates': '원문에서 확인한 교체 대상 옛 날짜 문자열 배열입니다. 없음을 확인했으면 []입니다.',
    'reuse_review.names_empty_reason': 'names가 []일 때 고유 명칭이 없는 실제 이유 문자열입니다.',
    'reuse_review.dates_empty_reason': 'dates가 []일 때 옛 날짜가 없는 실제 이유 문자열입니다.',
    'checks': '조회별 적용 여부·입력을 기록합니다. 틀의 reference_setting은 필요한 .hwpdoc/workspace.json 설정 키를 안내하며 실제 자료 경로는 그 설정에 기록합니다. 적용 대상만 필요합니다.',
    'checks.budget_names.applicable': '예산명 조회 적용 여부 true/false입니다. 미확인은 null입니다. true이면 names 문자열 배열과 .hwpdoc/workspace.json의 references.budget(예산 자료 JSON 상대경로) 설정이 필요합니다.',
    'checks.related.applicable': '관련번호 조회 적용 여부 true/false입니다. 미확인은 null입니다. true이면 원문에서 확인한 numbers 배열과 .hwpdoc/workspace.json의 references.related(공문 MD 폴더 상대경로) 설정이 필요합니다.',
    'checks.timetable.applicable': '시간표 조회 적용 여부 true/false입니다. 미확인은 null입니다. true이면 dates(ISO 날짜 배열), periods("1-4" 등), 필요 시 grades("1,2" 등)와 .hwpdoc/workspace.json의 references.timetable(시간표 JSON 상대경로) 설정이 필요합니다.',
    'checks.budget_names.reason': 'budget_names.applicable=false이면 업무와 무관한 실제 이유 문자열입니다.',
    'checks.related.reason': 'related.applicable=false이면 업무와 무관한 실제 이유 문자열입니다.',
    'checks.timetable.reason': 'timetable.applicable=false이면 업무와 무관한 실제 이유 문자열입니다.',
    'environment': '실제 app·python·kordoc 상태 JSON 객체입니다. 미확인은 unconfirmed로 보존합니다.',
    'preparation_tasks': 'prepare가 만든 작업 안내 {kind,text,slot(슬롯 조회일 때)} 배열입니다. 완료 여부는 현재 확인표·승인·입력 검증으로 계산하고 보고서에 근거와 이력을 보존합니다. 안내를 실제 미확인 사항으로 옮기거나 완료 상태를 손으로 쓰지 않습니다.',
    'unresolved': '실제 값·업무 판단 미확인 사항 배열입니다. 모두 해결했으면 []이며 남은 항목은 정상 전달을 막습니다. 렌더·판독 대기는 {"kind":"validation","text":"대기 사유","stages":["render","visual_review"]}로 해당 단계에 연결할 수 있습니다. pass와 현재 파일 해시가 일치해야 해소됩니다.',
    'base': 'prepare --base가 보존한 kind=unregistered_one_off, path·sha256·origin·imported_at 객체입니다. path 사본의 SHA256을 유지합니다. 원본을 덮어쓰지 않습니다.',
    'reference': '신구대조 기준 HWPX 상대경로입니다. --base에서는 준비된 base.path를 유지합니다.',
    'reference_sha256': 'reference가 가리키는 기준 HWPX 파일 바이트의 SHA256입니다.',
    'base_provenance': '확인된 유래 native/converted/repackaged 또는 unconfirmed입니다. 미등록 베이스는 unconfirmed를 유지하고 렌더로 대조합니다.',
    'slots.template_sha256': '실제 base.path가 가리키는 편집 베이스 HWPX 파일 바이트의 SHA256입니다.',
    'slots.values': '추출 슬롯 키(p:12, cell:0:2:1 등)→문자열 또는 {"shared":"공유값 키"} 객체입니다. 추출 주소·max_chars를 지키며 임의 축약/병합으로 맞추지 않습니다.',
    'kept_slots': '교사가 유지를 확인한 실제 추출 슬롯 키 배열입니다. 편집값과 유지 슬롯 중 하나 이상이 필요합니다.',
    'cell_fills': '선택 사항: {"cell:표:행:열":"cell:같은표:원본행:원본열"}. 베이스 원본 칸의 borderFillIDRef 전체(테두리 등 포함)를 복사합니다. 승인 전에 기록하며 입력 해시에 포함됩니다.',
    'shading_ack': '선택 사항: 현재 음영 유지를 교사가 명시한 베이스 칸 키 목록입니다. 해당 칸의 의미상 음영 불일치를 수용하며 승인 입력 해시에 포함됩니다.',
    'visual_review_record': '선택 사항: 생성 후 표 칸·문단 판독 JSON 경로를 승인 전에 선언합니다. 기본값은 .hwpdoc/jobs/<job_id>/visual-review.json입니다. build → validate → review --job <ID> → PDF·전 페이지 PNG 실제 판독 → review --job <ID> --confirm --by <판독자> --record <판독 내용> → validate 순서입니다. manifest는 생성 후 수정하지 않습니다.',
    'checklist.path': '--apply가 기록한 확인표.md 상대경로입니다. 확인표를 고쳤으면 다시 --apply 후 초안을 확인받습니다.',
    'checklist.sha256': '--apply가 기록한 checklist.path 파일 바이트의 SHA256입니다. 수동 보완으로 기존 승인을 유지하지 않습니다.',
    'activities': '선택 사항: [{"location":"위치","items":["활동명"],"slot_keys":["실제 추출 키"]}]입니다. 활동별 행과 값을 보존합니다.',
    'structure_change': '구조 변경이 필요하면 대상·변경 전후·이유·실제 승인 근거를 남기고 기존 재생성·렌더 경로로 진행합니다. 슬롯 build로 우회하지 않습니다.',
    'source': '슬롯 build 외 기존 생성 경로의 HWPX 상대경로입니다. validate --manifest로 전체 검증합니다.',
    'source_sha256': 'source가 가리키는 생성 HWPX 파일 바이트의 SHA256입니다.',
    'expected_values': '기존 생성 경로의 원문에서 확인한 필수값 문자열 배열입니다. 슬롯 경로는 slots.values를 대조합니다.',
    'received.submission_method': 'W2: 수신 원문에서 확인한 official_reply/system/email 중 하나입니다. 없으면 확인이 필요합니다.',
    'received': 'W2: summary·requirements·deadline·document_number·issue_date·source_quote를 수신 원문에서 확인해 기록합니다. 번호·시행일·제출 방법을 추측하지 않습니다.',
}


def preflight_issue(field, problem, how_to_fix=None):
    guidance_key = re.sub(r'\[\d+\](?:\.(?:path|sha256))?', '', field)
    children = [f'{key}: {value}' for key, value in MANIFEST_GUIDANCE.items() if key.startswith(field + '.')]
    return dict(field=field, problem=problem,
                how_to_fix=how_to_fix or MANIFEST_GUIDANCE.get(field) or MANIFEST_GUIDANCE.get(guidance_key)
                or ('JSON 객체에 다음 항목을 채우세요. ' + ' '.join(children) if children else '')
                or ('manifest의 ' + field + ' 항목을 올바른 형식으로 채우세요.'),
                phase='after_teacher_confirmation' if field.startswith('draft_approval') else 'before_approval')


def blocking_issues(issues):
    return [issue for issue in issues if issue.get('blocking', True)]


def zoned_time(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError('ISO 8601 시간대가 필요합니다')
    return parsed


def prerequisite_issues(m, *, build=False):
    """Read-only diagnostics; field addresses are supplied by the rules themselves."""
    issues = []
    def add(field, problem, fix=None):
        issues.append(preflight_issue(field, problem, fix))
    if not isinstance(m, dict):
        return [preflight_issue('$', 'manifest는 JSON 객체여야 합니다', 'prepare의 manifest.json 객체 형식을 유지하세요.')]
    required = dict(job_id=str, workflow=str, document_type=str, shared_values=dict, sources=list,
                    attachments=list, draft=dict, draft_approval=dict, content_rules=dict,
                    checks=dict, environment=dict, unresolved=list)
    for key, kind in required.items():
        if key not in m:
            add(key, '필수 입력 누락: ' + key)
        elif not isinstance(m[key], kind):
            add(key, '필수 입력 형식 오류: ' + key)
    def obj(key):
        return m.get(key) if isinstance(m.get(key), dict) else {}
    def items(key):
        return m.get(key) if isinstance(m.get(key), list) else []
    version = m.get('version', 1)
    if type(version) is not int:
        add('version', 'version은 정수여야 합니다')
        version = 2
    if isinstance(m.get('job_id'), str):
        try:
            validate_job_id(m['job_id'])
        except ValueError as exc:
            add('job_id', str(exc))
    if m.get('workflow') not in ('W1', 'W2'):
        add('workflow', 'workflow는 W1 또는 W2')
    if not m.get('document_type'):
        add('document_type', '문서 유형 누락')
    if not items('sources'):
        add('sources', '유사 문서/수신 원문 기록 누락')

    def file(field, value, hash_field=None, digest=None, *, local=False):
        path = None
        label = '확인표 ' if field.startswith('checklist.') else ''
        if not isinstance(value, str) or not value:
            add(field, label + '파일 경로 누락/형식 오류')
        else:
            try:
                path = workspace_path(value) if version >= 2 or local else input_path(value)
                if not path.is_file():
                    add(field, label + '파일 없음: ' + value)
                    path = None
            except (ValueError, OSError) as exc:
                add(field, str(exc))
        if hash_field:
            fix = MANIFEST_GUIDANCE.get(hash_field) or (
                f'{field}가 가리키는 파일 바이트의 SHA256(소문자 64자리)을 {hash_field}에 기록하세요.')
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
                add(hash_field, label + '파일 SHA256 누락/형식 오류', fix)
            elif path and digest != sha(path):
                add(hash_field, label + '파일 해시 불일치: ' + field, fix)
        return path

    draft, approval = obj('draft'), obj('draft_approval')
    file('draft.path', draft.get('path'), 'draft.sha256', draft.get('sha256'))
    draft_time = None
    try:
        draft_time = zoned_time(draft['created_at'])
    except (KeyError, ValueError, TypeError):
        add('draft.created_at', '초안 작성 시각이 올바르지 않습니다')
    for key in ('confirmed', 'by', 'at', 'record'):
        missing = approval.get(key) is not True if key == 'confirmed' else not approval.get(key)
        if missing:
            add('draft_approval.' + key, '사용자 초안 확인 기록이 필요합니다: ' + key)
    if approval.get('input_sha256') != json_hash(approval_payload(m)):
        add('draft_approval.input_sha256', '초안 확인 후 입력이 달라졌습니다: input_sha256 불일치')
    if approval.get('at'):
        try:
            approved = zoned_time(approval['at'])
            if draft_time and approved < draft_time:
                add('draft_approval.at', '초안 작성 이전 승인 기록')
        except (ValueError, KeyError, TypeError):
            add('draft_approval.at', '초안 승인 시각이 올바르지 않습니다')
    if m.get('checklist'):
        checklist = obj('checklist')
        file('checklist.path', checklist.get('path'), 'checklist.sha256', checklist.get('sha256'), local=True)
        if checklist.get('applied') is False or 'proposals' in checklist and checklist.get('applied') is not True:
            add('checklist.applied', '확인표가 아직 적용되지 않았습니다',
                '모든 행의 확정 값을 교사 답으로 채운 뒤 checklist --job <ID> --apply를 실행하세요.')
        if 'proposals' in checklist:
            proposals = checklist['proposals'] if isinstance(checklist['proposals'], dict) else {}
            file('checklist.proposals.path', proposals.get('path'), 'checklist.proposals.sha256', proposals.get('sha256'), local=True)
    for key in ('sources', 'attachments'):
        for index, item in enumerate(items(key)):
            field = f'{key}[{index}]'
            if not isinstance(item, dict):
                add(field, '원문/첨부는 path·sha256 객체여야 합니다')
                continue
            file(field + '.path', item.get('path'), field + '.sha256' if version >= 2 or item.get('sha256') else None, item.get('sha256'))
    if version >= 2 and not isinstance(m.get('attachment_mentions'), list):
        add('attachment_mentions', '본문 붙임 언급 목록 확인 기록 누락/형식 오류')
    for key in ('source', 'reference'):
        if m.get(key):
            file(key, m[key], key + '_sha256' if version >= 2 else None, m.get(key + '_sha256'))
    if m.get('shared_values_file'):
        file('shared_values_file', m['shared_values_file'])
    if m.get('workflow') == 'W1' and not obj('exploration').get('record'):
        add('exploration.record', 'W1 유사 공문·양식 탐색 기록 누락')
    if m.get('workflow') == 'W2':
        received = obj('received')
        if received.get('submission_method') not in ('official_reply', 'system', 'email'):
            add('received.submission_method', 'W2 제출 방법 미확인: 사용자 확인 필요')
        for key in ('summary', 'requirements', 'deadline', 'document_number', 'issue_date', 'source_quote'):
            if not received.get(key):
                add('received.' + key, 'W2 수신 원문에서 확인할 값: ' + key, MANIFEST_GUIDANCE['received'])
    for key in ('budget_names', 'related', 'timetable'):
        check = obj('checks').get(key)
        if not isinstance(check, dict) or not isinstance(check.get('applicable'), bool):
            add('checks.' + key + '.applicable', '조회 도구 적용 여부 누락: ' + key)
        elif check['applicable'] is False and not check.get('reason'):
            add('checks.' + key + '.reason', '해당 없음 이유 누락: ' + key)
    if build and m.get('structure_change'):
        add('structure_change', '구조 변경 필요: 기존 승인·재생성·렌더 경로로 진행하세요')
    if m.get('reference') or m.get('base'):
        rules, review = obj('content_rules'), obj('reuse_review')
        forbid = rules.get('forbid')
        if not isinstance(forbid, list) or any(not isinstance(x, str) or not x.strip() for x in forbid):
            add('content_rules.forbid', 'content_rules.forbid는 확인한 문자열 목록이어야 합니다')
        checked_forbid = forbid if isinstance(forbid, list) else []
        if not isinstance(review.get('record'), str) or not review['record'].strip():
            add('reuse_review.record', '재사용 문서의 고유 명칭·옛 날짜 검토 기록 필요')
        for key in ('names', 'dates'):
            if not isinstance(review.get(key), list):
                add('reuse_review.' + key, '복사 잔재 점검 목록 누락: reuse_review.' + key)
            elif not review[key] and (not isinstance(review.get(key + '_empty_reason'), str) or not review[key + '_empty_reason'].strip()):
                add('reuse_review.' + key + '_empty_reason', '복사 잔재 목록이 빈 이유 필요: ' + key)
            elif any(not isinstance(x, str) or not x.strip() or x not in checked_forbid for x in review[key]):
                add('reuse_review.' + key, '복사 잔재 점검 목록은 모두 content_rules.forbid에 포함해야 합니다: ' + key)
    return issues


def prerequisite_errors(m, *, build=False):
    # Preserve the public string-list interface for existing callers.
    return [issue['problem'] for issue in blocking_issues(preflight_issues(m, build=build))]


def value_inputs(m):
    issues = []
    shared = m.get('shared_values', {})
    if m.get('shared_values_file'):
        try:
            shared = read_json(input_path(m['shared_values_file']))
        except (ValueError, OSError, TypeError) as exc:
            issues.append(preflight_issue('shared_values_file', '공유값 JSON 오류: ' + str(exc)))
            shared = {}
    if not isinstance(shared, dict):
        issues.append(preflight_issue('shared_values_file' if m.get('shared_values_file') else 'shared_values', '공유값은 JSON 객체여야 합니다'))
        shared = {}
    supplied = m.get('slots', {})
    supplied = supplied.get('values') if isinstance(supplied, dict) else None
    if not isinstance(supplied, dict):
        return issues + [preflight_issue('slots.values', '슬롯 값은 JSON 객체여야 합니다')], {}
    values = {}
    for key, value in supplied.items():
        field = 'slots.values[' + json.dumps(key, ensure_ascii=False) + ']'
        if isinstance(value, dict) and set(value) == {'shared'}:
            if not isinstance(value['shared'], str) or value['shared'] not in shared:
                issues.append(preflight_issue(field, '공유값 누락: ' + str(value['shared']), MANIFEST_GUIDANCE['shared_values']))
                continue
            value = shared[value['shared']]
        if not isinstance(value, str):
            issues.append(preflight_issue(field, '문자열 아닌 슬롯 값: ' + key, MANIFEST_GUIDANCE['slots.values']))
            continue
        values[key] = value
    return issues, values


def resolved_values(m):
    issues, values = value_inputs(m)
    if issues:
        raise ValueError('\n'.join(x['problem'] for x in issues))
    return values


def editor_command(template, output, values_file, *, draft_over_budget=False, cell_fills_file=None):
    command = [SKILL / 'edit_hwpx.py', template, '-o', output, '--slot-json', values_file]
    if cell_fills_file is not None:
        command += ['--cell-fills', cell_fills_file]
    return command + (['--draft-over-budget'] if draft_over_budget else [])


def shading_inputs(m, template, values, *, output=None):
    """Blocking diagnostics before approval and the identical actual-file check."""
    sys.path.insert(0, str(SKILL))
    from hwpx_slots import shading_report
    try:
        result = shading_report(template, values, m.get('cell_fills', {}), m.get('shading_ack', []), output=output)
    except (ValueError, OSError, KeyError, TypeError, BadZipFile, SyntaxError, SystemExit) as exc:
        issue = preflight_issue('shading', '표 음영 검사 실패: ' + str(exc),
                                MANIFEST_GUIDANCE['cell_fills'] + ' ' + MANIFEST_GUIDANCE['shading_ack'])
        if not (m.get('cell_fills') or m.get('shading_ack')):
            issue.update(blocking=False, phase='review_note')  # 입력 오류가 아니면 막지 않는다
        return [issue], None
    # A shading mismatch is a note for the teacher, not a gate: on 11. 3. the
    # teacher called a forced decision over-optimization ("과최적화").
    issues = []
    for item in result['issues']:
        if not item['acknowledged']:
            issue = preflight_issue('shading', item['problem'], item['how_to_fix'])
            issue.update(blocking=False, phase='review_note')
            issues.append(issue)
    return issues, result


def checklist_input_issues(m, extracted, aliases):
    """Compare final raw inputs to the applied table; legacy slot jobs have none."""
    record = m.get('checklist')
    # Legacy tables must still be reconciled even if a handwritten applied flag
    # is false. Unapplied proposal tables are blocked by prerequisite_issues.
    if (not isinstance(record, dict) or not record
            or record.get('applied') is False and 'proposals' in record):
        return [], {}
    from hwpdoc_workspace import applied_checklist_values, ChecklistProposalError
    try:
        expected, kept = applied_checklist_values(m, extracted, aliases)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        detail = '; '.join(exc.problems) if isinstance(exc, ChecklistProposalError) else str(exc)
        return [preflight_issue('checklist.path', '확인표 재대조 실패: ' + detail,
                '확인표와 제안 근거를 확인하고 checklist --apply로 다시 적용한 뒤 초안을 확인받으세요.')], {}
    slots = m.get('slots')
    supplied = slots.get('values', {}) if isinstance(slots, dict) else {}
    supplied = supplied if isinstance(supplied, dict) else {}
    issues, labels = [], {}
    fix = '확인표 행으로 올려 교사 확인을 받거나 지우세요. 예산 초과 신고는 over_budget_cells에 확인표 키로 하세요.'
    for key in supplied:
        if key not in expected:
            issues.append(preflight_issue('slots.values[' + json.dumps(key, ensure_ascii=False) + ']',
                                         '확인표에 없는 편집값', fix))
    for key, value in expected.items():
        field = 'slots.values[' + json.dumps(key, ensure_ascii=False) + ']'
        if key not in supplied:
            issues.append(preflight_issue(field, '확인표 편집값 누락', '확인표를 다시 --apply하고 초안을 확인받으세요.'))
        elif supplied[key] != value:
            issues.append(preflight_issue(field, '확인표 확정 값과 편집값 불일치', '확인표를 다시 --apply하고 초안을 확인받으세요.'))
        if key in aliases:
            labels.setdefault(aliases[key], []).append(key)
    if m.get('kept_slots', []) != kept:
        issues.append(preflight_issue('kept_slots', '확인표 유지 슬롯 불일치', '확인표를 다시 --apply하고 초안을 확인받으세요.'))
    return issues, labels


def annotate_budget_cells(reason, labels):
    """Display checklist paragraph addresses beside cell budgets, without waivers."""
    def label(match):
        key = match[0]
        parts = key.split(':')
        # page_guard always includes occurrence, hwpx_slots omits the first 0.
        if len(parts) == 5:
            if parts[-1] != '0':
                return key
            key = ':'.join(parts[:4])
        return match[0] + (' (확인표 ' + ', '.join(labels[key]) + ')' if key in labels else '')
    return '\n'.join(re.sub(r'\bcell:\d+:\d+:\d+(?::\d+)?\b', label, line)
                     if '초과' in line and ('예산' in line or '글자 수' in line) else line
                     for line in reason.split('\n'))


def editor_issues(template, values, *, draft_over_budget=False, checklist_labels=None, inspect=None, cell_fills=None):
    """Exercise the build editor unchanged, keeping all output outside the workspace."""
    try:
        temp_root = Path(tempfile.gettempdir()).resolve()
        if temp_root.is_relative_to(ROOT.resolve()):
            raise ValueError('임시 폴더가 작업 폴더 안에 있습니다. 작업 폴더 밖의 TEMP/TMP를 설정하세요.')
        with tempfile.TemporaryDirectory(prefix='hwpdoc-check-', dir=temp_root) as name:
            folder = Path(name)
            write_json(folder / 'values.json', values)
            output_file = folder / ('work-미검증.hwpx' if draft_over_budget else 'work.hwpx')
            fills = folder / 'cell_fills.json' if cell_fills else None
            if fills:
                write_json(fills, cell_fills)
            if values or fills:
                code, output = run(editor_command(template, output_file, folder / 'values.json',
                                   draft_over_budget=draft_over_budget, cell_fills_file=fills))
            else:
                shutil.copy2(template, output_file)
                code, output = 0, ''
            if not code:
                if inspect:
                    inspect(output_file, folder)
                return []
            output = output.replace(str(folder), '<임시 폴더>')
    except (ValueError, OSError) as exc:
        return [preflight_issue('slots.values', '편집기 사전 점검 실패: ' + str(exc))]
    problems = [line.strip()[2:] for line in output.splitlines() if line.strip().startswith('- ')]
    issues = []
    for problem in problems or [output.strip() or f'편집기 종료 코드: {code}']:
        cell = re.search(r'table=(\d+), row=(\d+), col=(\d+)', problem)
        paragraph = re.search(r'(?:--paragraph |index=)(\d+)', problem)
        key = 'cell:' + ':'.join(cell.groups()) if cell else 'p:' + paragraph[1] if paragraph else None
        field = 'slots.values[' + json.dumps(key, ensure_ascii=False) + ']' if key in values else 'slots.values'
        fix = MANIFEST_GUIDANCE['slots.values']
        if '글자 수 초과' in problem:
            if key in (checklist_labels or {}):
                problem += ' — ' + key
            problem = annotate_budget_cells(problem, checklist_labels or {})
            fix += ' 뜻을 보존한 짧은 문구(추천)로 바꾸거나, 교사가 문구 유지를 택하면 over_budget_cells에 넣고 생성 후 렌더 확인을 진행하세요. 구조 변경·렌더 확인 경로는 기존 절차를 따릅니다.'
        elif '띄어쓰기 없는 한글' in problem:
            fix += ' 띄어쓰기 없는 한글 연속 문자열은 24자 이내여야 합니다. 의미를 보존해 띄어쓰기를 바로잡으세요.'
        issues.append(preflight_issue(field, problem, fix))
    return issues


def build_inputs(m, *, content_detail=None, inspect=None):
    """All slot/value checks, without writing profiles, work files or reports."""
    if not isinstance(m, dict):
        return [], None, {}
    issues, values = value_inputs(m)
    template, extracted, slots = None, None, None
    aliases, checklist_labels = {}, {}
    base_field = 'base'
    try:
        template = template_file(m)
        if template.suffix.lower() != '.hwpx' or not template.is_file():
            raise ValueError('편집 베이스 HWPX 파일 없음')
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        issues.append(preflight_issue(base_field, str(exc)))
        template = None
    supplied = m.get('slots') if isinstance(m.get('slots'), dict) else {}
    digest = supplied.get('template_sha256')
    if (not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)
            or template and digest != sha(template)):
        issues.append(preflight_issue('slots.template_sha256', '추출 슬롯의 템플릿 해시 누락/불일치'))
    if not (supplied.get('values') or m.get('kept_slots')):
        issues.append(preflight_issue('slots.values', '슬롯 편집값 또는 유지 슬롯 누락', MANIFEST_GUIDANCE['slots.values'] + ' ' + MANIFEST_GUIDANCE['kept_slots']))
    if template:
        sys.path.insert(0, str(SKILL))
        from hwpx_slots import collect_slots
        try:
            extracted = collect_slots(template, preview_len=1000000)
            slots = {x['key']: x for x in extracted['slots']}
            from hwpdoc_workspace import checklist_aliases
            aliases = checklist_aliases(m, extracted)
        except (ValueError, OSError, KeyError, TypeError, BadZipFile, SyntaxError) as exc:
            issues.append(preflight_issue(base_field, '베이스 슬롯 추출 실패: ' + str(exc)))
    if extracted is not None:
        checklist_issues, checklist_labels = checklist_input_issues(m, extracted, aliases)
        issues += checklist_issues
    for paragraph, cell in aliases.items():
        if paragraph in values and cell in values:
            issues.append(preflight_issue('slots.values[' + json.dumps(cell, ensure_ascii=False) + ']',
                f'셀·소유 문단 동시 편집: {cell}, {paragraph}',
                '같은 위치를 덮어쓰는 셀 키와 문단 키 중 하나만 편집하세요.'))
    if template and slots is not None and not blocking_issues(issues):
        issues += shading_inputs(m, template, values)[0]
    kept = m.get('kept_slots', [])
    if not isinstance(kept, list) or any(not isinstance(key, str) or slots is not None and key not in slots for key in kept):
        issues.append(preflight_issue('kept_slots', '추출되지 않은 유지 슬롯 또는 목록 형식 오류'))
    declared = m.get('over_budget_cells', [])
    if not isinstance(declared, list) or any(not isinstance(key, str) for key in declared):
        issues.append(preflight_issue('over_budget_cells', '예산 초과 신고는 슬롯 키 문자열 목록이어야 합니다'))
        declared = []
    for index, key in enumerate(declared):
        field = f'over_budget_cells[{index}]'
        if slots is not None and key not in slots:
            issues.append(preflight_issue(field, '추출되지 않은 예산 초과 신고 슬롯: ' + key))
        elif key not in values:
            issues.append(preflight_issue(field, '예산 초과 신고 슬롯의 편집값 누락: ' + key))
        elif slots is not None and len(''.join(values[key].split())) <= slots[key]['max_chars']:
            issues.append(preflight_issue(field, '신고했지만 실제로 예산을 넘지 않는 슬롯: ' + key))
    budget_issues = []
    for key, value in (values.items() if slots is not None else []):
        field = 'slots.values[' + json.dumps(key, ensure_ascii=False) + ']'
        if key not in slots:
            issues.append(preflight_issue(field, '추출되지 않은 슬롯: ' + key, MANIFEST_GUIDANCE['slots.values']))
            continue
        limit = slots[key]['max_chars']
        if (limit or key in declared) and len(''.join(value.split())) > limit:
            issue = preflight_issue(field,
                annotate_budget_cells(f'{key}: {len("".join(value.split()))}>{limit}자, 예산 초과 — 내용 보존·구조 변경·렌더 확인 필요', checklist_labels),
                MANIFEST_GUIDANCE['slots.values'] + ' 뜻을 보존한 짧은 문구(추천)로 바꾸거나, 교사가 문구 유지를 택하면 over_budget_cells에 넣고 생성 후 렌더 확인을 진행하세요. 구조 변경·렌더 확인 경로는 기존 절차를 따릅니다.')
            if key in declared:
                issue.update(blocking=False, phase='after_build_render_review',
                             how_to_fix='생성 후 렌더·육안 확인 필요. ' + MANIFEST_GUIDANCE['visual_review_record'])
            issues.append(issue)
            budget_issues.append(issue)
    # Budget failures must not hide content failures in other slots. A disposable
    # draft can be inspected but is discarded; build still honors every gate.
    can_inspect = slots is not None and not blocking_issues([i for i in issues if i not in budget_issues])
    if can_inspect:
        # The draft flag is global: first retain the editor's normal checks for
        # every undeclared value, including its estimated empty-cell budgets.
        undeclared = {key: value for key, value in values.items() if key not in declared}
        if isinstance(m.get('content_rules'), dict):
            from hwpdoc_content_check import inspect_inputs, issues_for
            try:
                editor_findings, detail = inspect_inputs(m, template, extracted, values, aliases,
                    draft_over_budget=bool(declared or budget_issues), checklist_labels=checklist_labels,
                    undeclared=undeclared if declared else None, inspect=inspect)
                issues += editor_findings
                issues += issues_for(detail)
                if content_detail is not None:
                    content_detail.update(detail)
            except (ValueError, OSError, KeyError, TypeError, SyntaxError, BadZipFile) as exc:
                issues.append(preflight_issue('content_check', '내용 사전 검사 실패: ' + str(exc)))
        else:
            if declared and undeclared:
                issues += editor_issues(template, undeclared, checklist_labels=checklist_labels)
            if not blocking_issues(issues) and (values or inspect):
                issues += editor_issues(template, values, draft_over_budget=bool(declared), checklist_labels=checklist_labels,
                                        cell_fills=m.get('cell_fills'), inspect=inspect)
    activities = m.get('activities', [])
    if not isinstance(activities, list):
        issues.append(preflight_issue('activities', '활동은 items·slot_keys 객체 목록이어야 합니다'))
        activities = []
    for index, group in enumerate(activities):
        field = f'activities[{index}]'
        if not isinstance(group, dict) or not isinstance(group.get('items', []), list) or not isinstance(group.get('slot_keys', []), list):
            issues.append(preflight_issue(field, '활동 items·slot_keys는 배열이어야 합니다', MANIFEST_GUIDANCE['activities']))
            continue
        if len(group.get('items', [])) > len(group.get('slot_keys', [])):
            issues.append(preflight_issue(field + '.slot_keys', '활동 행 부족: ' + str(group.get('location')) + ' — 병합하지 말고 구조 변경 경로로 진행하세요', MANIFEST_GUIDANCE['activities']))
        for item, key in zip(group.get('items', []), group.get('slot_keys', [])):
            if not isinstance(key, str) or values.get(key) != item:
                issues.append(preflight_issue(field + '.slot_keys', '활동명 훼손/매핑 불일치: ' + str(key), MANIFEST_GUIDANCE['activities']))
    return issues, extracted, values


def preflight_issues(m, *, build=False, content_detail=None):
    issues = prerequisite_issues(m, build=build)
    if isinstance(m, dict) and 'visual_review_record' in m:
        from hwpdoc_review import record_path
        try:
            record_path(m)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            issues.append(preflight_issue('visual_review_record', str(exc)))
    if build:
        issues += build_inputs(m, content_detail=content_detail)[0]
    elif isinstance(m, dict) and ('cell_fills' in m or 'shading_ack' in m):
        try:
            issues += shading_inputs(m, template_file(m), resolved_values(m) if m.get('slots') else {})[0]
        except (ValueError, OSError, KeyError, TypeError) as exc:
            issues.append(preflight_issue('shading', '음영 입력의 편집 베이스 확인 실패: ' + str(exc)))
    if (isinstance(m, dict) and isinstance(m.get('checks'), dict)
            and type(m.get('version', 1)) is int and m.get('version', 1) >= 2 and CONTEXT):
        for check, reference in (('budget_names', 'budget'), ('related', 'related'), ('timetable', 'timetable')):
            entry = m['checks'].get(check)
            if isinstance(entry, dict) and entry.get('applicable') is True:
                try:
                    CONTEXT.reference(reference)
                except (ValueError, OSError, TypeError) as exc:
                    issues.append(preflight_issue('references.' + reference, str(exc),
                        MANIFEST_GUIDANCE['checks.' + check + '.applicable']))
    return issues


def legacy_evidence(m):
    """Read an optional historical record for reporting, never for readiness."""
    if 'evidence' not in m:
        return {}, []
    notes = ['기존 업무 근거 기록은 참고 메모로 보존하며 정상 전달을 막지 않습니다.']
    try:
        entry = m['evidence']
        if not isinstance(entry, dict) or not isinstance(entry.get('record'), str) or not entry['record']:
            raise ValueError('evidence.record 경로 없음/형식 오류')
        path = input_path(entry['record'])
        record = read_json(path)
        if not isinstance(record, dict):
            raise ValueError('기록이 JSON 객체가 아닙니다')
        return record, notes
    except (ValueError, OSError, TypeError) as exc:
        notes.append('기존 업무 근거 기록을 읽을 수 없거나 형식이 올바르지 않습니다: ' + str(exc))
        return {}, notes


def initialization_inputs(manifest_file, *, build, job=None):
    """The complete read-only initialization path shared by check and build.

    Resolve dependencies before any work/report writes,
    so their input errors cannot first appear after preflight has passed.
    """
    prepared, m = {}, None
    try:
        m = read_json(input_path(manifest_file))
    except FileNotFoundError:
        return m, [preflight_issue('$', 'prepared manifest 파일이 없습니다: ' + str(manifest_file))], prepared
    except (ValueError, OSError, TypeError) as exc:
        return m, [preflight_issue('$', 'manifest JSON 오류: ' + str(exc))], prepared
    detail = {}
    issues = preflight_issues(m, build=build, content_detail=detail)
    if detail:
        prepared['content_check'] = detail
    if not isinstance(m, dict):
        return m, issues, prepared
    try:
        folder = job_dir(m.get('job_id'))
        prepared['folder'] = folder
        if job is not None and m.get('job_id') != job:
            issues.append(preflight_issue('job_id', '요청한 작업ID와 manifest의 job_id가 다릅니다'))
        if (folder / 'report.json').exists():
            issues.append(preflight_issue('job_id', '기존 작업은 덮어쓰지 않습니다 — 새 작업ID 사용'))
    except (ValueError, OSError, TypeError) as exc:
        if not any(i['field'] == 'job_id' for i in issues):
            issues.append(preflight_issue('job_id', str(exc)))
    if not blocking_issues(issues):
        try:
            source = template_file(m) if build else input_path(m.get('source'))
            if source.suffix.lower() != '.hwpx' or not source.is_file():
                raise ValueError('기존 경로에서 생성된 HWPX만 입력할 수 있습니다')
            prepared['source'] = source
        except (ValueError, OSError, KeyError, TypeError) as exc:
            issues.append(preflight_issue('base' if build else 'source', str(exc)))
    if not blocking_issues(issues):
        try:
            er, notes = legacy_evidence(m)
            prepared.update(dependencies=dependencies(m), tool_dependencies=tool_dependencies(),
                            runtime=runtime_snapshot(), evidence=er, evidence_notes=notes,
                            unresolved=list(m['unresolved']))
        except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
            issues.append(preflight_issue('$', '초기화 입력/의존 파일 오류: ' + str(exc),
                'manifest의 의존 파일 경로·JSON 형식과 작업 폴더 설정을 확인한 뒤 check를 다시 실행하세요.'))
    return m, issues, prepared


def check_result(job, issues):
    blocked = blocking_issues(issues)
    return dict(job_id=job, ready=not blocked, issues=issues,
                ready_for_approval=not any(i['phase'] == 'before_approval' for i in blocked),
                next_action=('교사 확인 후 항목은 실제 초안 확인을 받아 기록하세요. ' if blocked else '')
                + (f'다음: check --job {job}로 남은 항목 확인 후 build' if blocked else 'build 사전 점검 통과. 확인받은 입력으로 build 후 validate를 실행하세요.')
                + (' 생성 후 렌더·육안 확인 필요.' if any(i['phase'] == 'after_build_render_review' for i in issues) else ''))


def check_job(job):
    job_dir(job)  # Validate without acquiring a lock or creating its parent.
    manifest = workspace_path(Path('.hwpdoc/prepared') / job / 'manifest.json')
    m, issues, prepared = initialization_inputs(manifest, build=True, job=job)
    result = check_result(job, issues)
    detail = prepared.get('content_check')
    if detail:
        from hwpdoc_content_check import summary
        result['content_check'] = summary(detail)
        # Only diagnostics are persisted, never the temporary edited document.
        path = manifest.parent / 'content-check.json'
        detail['input_sha256'] = json_hash(approval_payload(m))
        detail['tool_dependencies'] = tool_dependencies()
        try:
            current_detail = read_json(path)
        except (OSError, ValueError):
            current_detail = None
        if current_detail != detail:
            write_json(path, detail)
        result['content_check']['details_path'] = str(path)
        result['content_check']['examples'] = [dict(slot=key, findings=items[:3])
                                             for key, items in list(detail['groups'].items())[:5]]
        result['content_check']['date_normalizations'] = detail['date_normalizations'][:5]
        result['content_check']['final_content_policy'] = detail['final_content_policy']
        # Keep all issues for gating, but never print a full document's findings.
        content_issues = [i for i in issues if i.get('content_check')]
        result['issues'] = [i for i in issues if not i.get('content_check')] + content_issues[:5]
    if isinstance(m, dict) and isinstance(m.get('unresolved'), list):
        from hwpdoc_pending import pending_view, pending_summary
        report_file = job_dir(job) / 'report.json'
        report = load_report(report_file) if report_file.is_file() else None
        view = pending_view(m, report=report)
        result['pending_summary'] = pending_summary(view, report.get('stages') if report else None,
                                                    freshness(report) if report else None)
        result['preparation_counts'] = {
            'completed': sum(t['status'] == 'completed' for t in view['preparation_tasks']),
            'pending': sum(t['status'] == 'pending' for t in view['preparation_tasks'])}
    from hwpdoc_workspace import checklist_warning_notes
    warnings = checklist_warning_notes(manifest.parent)
    if warnings:
        result['date_warnings'] = warnings
    return result


def approve_job(job, by=None, record=None, *, carry_forward_from=None):
    if carry_forward_from and (by is not None or record is not None):
        raise ValueError('--carry-forward-from과 새 --by/--record를 함께 쓰지 마세요')
    if not carry_forward_from and (not by or not by.strip() or not record or not record.strip()):
        raise ValueError('--by와 --record는 비어 있을 수 없습니다. 교사의 실제 응답 원문을 기록하세요.')
    job_dir(job)
    manifest = workspace_path(Path('.hwpdoc/prepared') / job / 'manifest.json')
    m, issues, _ = initialization_inputs(manifest, build=True, job=job)
    before = [i for i in issues if i['phase'] == 'before_approval']
    if before:
        result = check_result(job, before)
        result['next_action'] = '승인 전 항목을 먼저 채운 뒤 초안을 다시 보여주고 확인받으세요'
        return result
    carried = None
    if carry_forward_from:
        from hwpdoc_revisions import carry_approval
        carried = carry_approval(m, carry_forward_from)
    previous = m.get('draft_approval')
    if isinstance(previous, dict) and previous.get('input_sha256') == json_hash(approval_payload(m)):
        result = check_result(job, issues)
        result['message'] = '이미 확인됨'
        return result
    if previous is not None:
        history = m.setdefault('approval_history', [])
        if not isinstance(history, list):
            raise ValueError('approval_history는 이전 확인 기록의 목록이어야 합니다')
        history.append(previous)
    m['draft_approval'] = carried or dict(confirmed=True, by=by, at=now(), record=record)
    m['draft_approval']['input_sha256'] = json_hash(approval_payload(m))
    write_json(manifest, m)
    result = check_job(job)
    result['message'] = ('기존 확인은 입력 해시가 달라 무효입니다. 새 확인을 기록했습니다.'
                         if previous is not None else '교사 확인을 기록했습니다.')
    if carried:
        result['message'] = '교사 확인 이월: ' + carry_forward_from + ' (교사가 보는 내용 동일)'
    if result['ready']:
        result['next_action'] = f'다음: build --manifest "{manifest}"'
    audit('approve', manifest, 'pass' if result['ready'] else 'unconfirmed', result)
    return result


def tool_dependencies():
    paths = list(SKILL.glob('*.py'))
    paths += [CODE_ROOT / 'scripts' / name for name in (
        'teacher_doc.py', 'teacher_doc.ps1', 'hwpdoc.py', 'hwpdoc_config.py', 'hwpdoc_templates.py', 'hwpdoc_workspace.py',
        'hwpdoc_review.py', 'hwpdoc_revisions.py', 'hwpdoc_preview.py', 'hwpdoc_pending.py', 'hwpdoc_content_check.py', 'render_check.py',
        'budget_name_check.py', 'related_lookup.py', 'fusion_timetable.py', 'hwpdoc_runtime.py')]
    paths += [SKILL.parent / 'SKILL.md', SKILL.parent / 'references/workflow.md']
    paths += list((CODE_ROOT / 'distribution').glob('requirements-*.txt'))
    return {str(p.resolve()): sha(p) for p in paths if p.is_file()}


def dependencies(m):
    paths = [input_path(m['draft']['path'])]
    if m.get('checklist'):
        paths.append(workspace_path(m['checklist']['path']))
        if m['checklist'].get('proposals'):
            paths.append(workspace_path(m['checklist']['proposals']['path']))
    paths += [input_path(x['path']) for x in m['sources'] + m['attachments']]
    if m.get('base'):
        paths.append(template_file(m))
    for key in ('source', 'reference'):
        if m.get(key):
            paths.append(input_path(m[key]))
    if m.get('shared_values_file'):
        paths.append(input_path(m['shared_values_file']))
    visual = m.get('visual_review', {})
    if visual.get('pdf'):
        paths.append(input_path(visual['pdf']['path']))
    paths += [input_path(x['path']) for x in visual.get('images', [])]
    paths += [ROOT / 'CLAUDE.md', ROOT / 'AGENTS.md', ROOT / '.hwpdoc/workspace.json', CODE_ROOT / 'config/legacy-workspace.json']
    if m.get('version', 1) < 2:
        paths += list((ROOT / 'knowledge/reference').glob('*'))
    elif CONTEXT:
        # Only selected inputs; unrelated school assets do not invalidate new jobs.
        for check, keys in {'budget_names': ('budget',), 'timetable': ('timetable',)}.items():
            if m['checks'][check].get('applicable'):
                paths += [CONTEXT.reference(k) for k in keys]
    if m['checks']['related'].get('applicable'):
        related = CONTEXT.reference('related') if m.get('version', 1) >= 2 and CONTEXT else ROOT / 'knowledge/examples/md'
        paths += list(related.glob('*.md'))
    return {**tool_dependencies(), **{str(p.resolve()): sha(p) for p in paths if p.is_file()}}


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
    if 'tool_dependencies' in report:
        current = tool_dependencies()
        changed += [p for p in set(current) | set(report['tool_dependencies'])
                    if current.get(p) != report['tool_dependencies'].get(p)]
    if report.get('runtime') != runtime_snapshot():
        changed.append('@runtime')
    return sorted(set(changed))


def refresh_validation_tools(report):
    """Revalidate after code updates without manufacturing another draft approval."""
    current = tool_dependencies()
    previous = report.get('tool_dependencies', {p: digest for p, digest in report['dependencies'].items() if p in current})
    changed = freshness(report)
    generated = report.get('visual_review_dependencies', [])
    inputs = [p for p in changed if p not in (report['work_file'], '@runtime') and p not in current and p not in previous and p not in generated]
    if inputs:
        raise ValueError('승인 입력/근거 변경: 새 확인과 새 job_id 필요\n' + '\n'.join(inputs))
    updates = {path_context().encode(p): {'before': previous.get(p), 'after': current.get(p)}
               for p in set(previous) | set(current) if previous.get(p) != current.get(p)}
    if updates:
        report.pop('validated_sha256', None)
        report.setdefault('tool_updates', []).append({'at': now(), 'files': updates, 'approval_preserved': True})
    runtime = runtime_snapshot()
    if report.get('runtime') != runtime:
        report.pop('validated_sha256', None)
        report.setdefault('runtime_updates', []).append({'at': now(), 'before': report.get('runtime'),
                                                        'after': runtime, 'approval_preserved': True})
    report['runtime'] = runtime
    for p in previous:
        report['dependencies'].pop(p, None)
    report['dependencies'].update(current)
    report['tool_dependencies'] = current


def result_state(report, *, pending=None):
    from hwpdoc_pending import report_view, blockers
    view = report_view(report) if pending is None else pending
    if any(item['id'] == 'manifest:read' for item in view['unresolved']):
        return 'unconfirmed'
    if freshness(report):
        return 'unconfirmed'
    states = [report.get('stages', {}).get(s, {}).get('status', 'unconfirmed') for s in STAGES]
    if 'fail' in states:
        return 'fail'
    if blockers(view) or any(s not in ('pass', 'not_applicable') for s in states) or not report.get('validated_sha256'):
        return 'unconfirmed'
    return 'pass'


def stage_challenge(entry):
    canonical = copy.deepcopy(entry)
    if canonical.get('command'):
        canonical['command'] = [path_context().encode(p) if Path(p).is_absolute() else p for p in canonical['command']]
    return json_hash(canonical)


def resume_challenges(report):
    return {name: {'stage_sha256': stage_challenge(entry),
                   'document_sha256': sha(report['work_file']) if Path(report['work_file']).is_file() else None,
                   'input_sha256': report['manifest_sha256']}
            for name, entry in report.get('stages', {}).items()
            if entry.get('failures', 0) - entry.get('retry_baseline', 0) >= 2 and name != 'build'}


def save_report(report):
    from hwpdoc_pending import sync_report
    view = sync_report(report)
    report['resume_challenges'] = resume_challenges(report)
    report['updated_at'] = now()
    report['status'] = result_state(report, pending=view)
    report['next_action'] = ('사람 최종 검토; ' + NOTICE if report['status'] == 'pass'
                             else '실패/미확인 단계와 변경 파일 확인; 값을 지어내지 말고 질문 또는 기존 수동 경로 사용')
    write_json(job_dir(report['job_id']) / 'report.json', report_record(report))


def retry_basis(work):
    return {'document_sha256': sha(work) if Path(work).is_file() else None,
            'tools_sha256': json_hash(tool_dependencies()), 'runtime': runtime_snapshot()}


def stage(report, name, argv=None, *, status=None, reason='', com=False):
    started = time.monotonic()
    previous = report['stages'].get(name, {})
    failures = previous.get('failures', 0)
    retry_baseline = previous.get('retry_baseline', 0)
    before = sha(report['work_file']) if Path(report['work_file']).is_file() else None
    if argv is None:
        code, output = None, reason
        state = status or 'unconfirmed'
    elif failures - retry_baseline >= 2:
        code, output, state = None, '동일 단계 2회 실패: 자동 시도 중단. 원인 해결·실제 사용자 확인 후 resume --job --stage --record 필요.', 'fail'
    else:
        code, output = run(argv, com=com)
        unavailable = code in (124, 125) or (com and re.search('검사 불가|not installed|only available|COM .*failed', output, re.I))
        state = 'pass' if code == 0 else ('unconfirmed' if unavailable else 'fail')
        if code:
            failures += 1
    if name == 'page_guard' and report.get('manifest_file'):
        # Decorate the report/history/audit together, after the status decision.
        # Missing or invalid table inputs must never alter page_guard's verdict.
        try:
            m = read_json(report['manifest_file'])
            if m.get('checklist'):
                from hwpdoc_templates import extracted
                from hwpdoc_workspace import checklist_aliases
                slots = extracted(template_file(m))
                _, labels = checklist_input_issues(m, slots, checklist_aliases(m, slots))
                output = annotate_budget_cells(output, labels)
        except (ValueError, OSError, KeyError, TypeError, AttributeError):
            pass
    entry = dict(status=state, reason=output, failures=failures, retry_baseline=retry_baseline, exit_code=code,
                 before_sha256=before, after_sha256=sha(report['work_file']) if Path(report['work_file']).is_file() else None,
                 at=now(), elapsed_seconds=round(time.monotonic() - started, 4), command=list(map(str, argv)) if argv else None,
                 warnings=[line for line in output.splitlines() if re.search(r'warning|\[warn\]|경고', line, re.I)])
    entry['failure_basis'] = retry_basis(report['work_file']) if code else previous.get('failure_basis')
    report['stages'][name] = entry
    report['history'].append(dict(stage=name, **entry))
    save_report(report)
    audit(name, report['work_file'], state, output[:1500])
    return state in ('pass', 'not_applicable')


def resume_stage(record, name, proof_file, work, input_sha256, folder):
    """One explicit retry window, without deleting failures or claiming a pass.

    A human's recorded confirmation and current-hash resolution evidence are
    required. This checks the evidence linkage, not the truth of their statement.
    """
    from datetime import datetime
    previous = record.get('stages', {}).get(name)
    if not previous or previous.get('failures', 0) - previous.get('retry_baseline', 0) < 2:
        raise ValueError('2회 실패로 중단된 해당 단계만 명시적으로 재개할 수 있습니다')
    proof_path = workspace_path(proof_file)
    proof = read_json(proof_path)
    if not isinstance(proof, dict) or proof.get('confirmed') is not True:
        raise ValueError('재개에는 원인 해결 후 실제 사용자 확인이 필요합니다')
    if any(not isinstance(proof.get(k), str) or not proof[k].strip()
           for k in ('by', 'at', 'record', 'cause', 'resolution')):
        raise ValueError('재개 확인·원인·해결 내용 누락')
    if (proof.get('stage') != name or proof.get('stage_sha256') != stage_challenge(previous)
            or proof.get('document_sha256') != sha(work) or proof.get('input_sha256') != input_sha256):
        raise ValueError('재개 확인 대상 단계/현재 문서/승인 입력 해시 불일치')
    try:
        at = datetime.fromisoformat(proof['at'])
        stopped = datetime.fromisoformat(previous['at'])
        if at <= stopped or at > datetime.now(timezone.utc):
            raise ValueError('중단 이후 현재 시점까지의 실제 확인 기록이 필요합니다')
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('재개 확인 시각이 올바르지 않습니다: ' + str(exc)) from exc
    evidence = proof.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        raise ValueError('원인 해결을 확인한 진단/수정 증거 파일과 SHA256이 필요합니다')
    sources = []
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError('재개 증거 형식 오류')
        path = workspace_path(item['path'])
        if not path.is_file() or item.get('sha256') != sha(path):
            raise ValueError('재개 증거 누락/해시 변경')
        sources.append(path)
    # A renamed evidence file or a different explanation cannot reset the same
    # failed conditions. External repairs require their own explicit human record.
    if previous.get('failure_basis') == retry_basis(work) or not previous.get('failure_basis'):
        if name not in ('hancom', 'render', 'review_render'):
            raise ValueError('실패 조건이 그대로입니다. 이 단계는 실제 문서/도구/runtime 수정이 필요합니다')
        external = proof.get('external_environment', {})
        if (not isinstance(external, dict) or external.get('confirmed') is not True
                or any(not isinstance(external.get(k), str) or not external[k].strip()
                       for k in ('by', 'at', 'change', 'verification'))):
            raise ValueError('실패 조건이 그대로입니다. 실제 문서/도구/runtime 수정 또는 외부 환경 복구의 구체적인 사람 확인이 필요합니다')
        try:
            verified = datetime.fromisoformat(external['at'])
            if not stopped < verified <= at:
                raise ValueError('복구 확인 시각 범위 오류')
        except (TypeError, ValueError) as exc:
            raise ValueError('외부 환경 복구 확인 시각 오류') from exc
    digest = sha(proof_path)
    if any(entry.get('record_sha256') == digest for entry in record.get('resumes', [])):
        raise ValueError('이미 사용한 재개 확인 기록은 다시 사용할 수 없습니다')
    evidence_folder = folder / 'resumes' / digest
    if evidence_folder.exists():
        raise ValueError('기존 재개 증거 폴더를 덮어쓰지 않습니다')
    evidence_folder.mkdir(parents=True)
    shutil.copy2(proof_path, evidence_folder / 'confirmation.json')
    for index, source in enumerate(sources):
        shutil.copy2(source, evidence_folder / (str(index) + '-' + source.name))
    entry = {'at': now(), 'stage': name, 'record_sha256': digest, 'previous': copy.deepcopy(previous),
             'document_sha256': sha(work), 'input_sha256': input_sha256,
             'evidence_directory': path_context().encode(evidence_folder), 'approval_preserved': True}
    record.setdefault('resumes', []).append(entry)
    record.setdefault('history', []).append({'stage': name, 'action': 'explicit_resume', **entry})
    record['stages'][name] = dict(previous, status='unconfirmed', retry_baseline=previous['failures'],
                                 reason='원인 해결 증거와 실제 사용자 재개 확인 수리; 전체 재검증 대기', at=now())
    record.pop('validated_sha256', None)
    audit('resume_' + name, work, 'unconfirmed', {'record_sha256': digest, 'failures_preserved': previous['failures']})
    return record


def resume_document(report, name, proof_file):
    if name in ('build', 'copy'):
        raise ValueError('이 재개 명령은 문서 검증 단계용입니다. 생성/외부 복사 상태를 우회하지 않습니다')
    # Original approval-bearing input files must still match. Work/tool/runtime
    # repairs are the permitted changes, followed by the normal full validator.
    refresh_validation_tools(report)
    resume_stage(report, name, proof_file, Path(report['work_file']), report['manifest_sha256'], job_dir(report['job_id']))
    save_report(report)
    return report


class PreflightRejected(ValueError):
    def __init__(self, result):
        self.result = result
        super().__init__('\n'.join(result['errors']))


def initialize(manifest_file, *, build):
    manifest_file = input_path(manifest_file)
    m, issues, prepared = initialization_inputs(manifest_file, build=build)
    folder = prepared.get('folder')
    if blocking_issues(issues):
        errors = [issue['problem'] for issue in blocking_issues(issues)]
        result = dict(status='unconfirmed', ready=False, error='\n'.join(errors), errors=errors, issues=issues, at=now())
        # Keep refusal reasons even when an earlier report exists; never replace it.
        audit('preflight', manifest_file, 'unconfirmed', errors)
        if folder:
            result.update(job_id=m['job_id'], next_action=f"다음: check --job {m['job_id']} 후 build")
            write_json(folder / 'preflight.json', result)
        raise PreflightRejected(result)
    folder.mkdir(parents=True, exist_ok=True)
    work = folder / ('work-미검증.hwpx' if build and m.get('over_budget_cells') else 'work.hwpx')
    shutil.copy2(prepared['source'], work)
    report = dict(version=1, job_id=m['job_id'], workflow=m['workflow'], manifest_file=str(manifest_file),
                  manifest_sha256=sha(manifest_file), work_file=str(work), dependencies=prepared['dependencies'],
                  tool_dependencies=prepared['tool_dependencies'],
                  runtime=prepared['runtime'], evidence=prepared['evidence'], evidence_notes=prepared['evidence_notes'],
                  stages={}, history=[], unresolved=prepared['unresolved'], environment=m['environment'],
                  created_at=now(), notice=NOTICE, semantic_evidence_assurance=False)
    save_report(report)
    (folder / 'preflight.json').unlink(missing_ok=True)
    return m, report


def build_document(manifest_file):
    m, report = initialize(manifest_file, build=True)
    folder = job_dir(m['job_id'])
    # Re-read through the same rules before editing in case inputs changed.
    issues, extracted, values = build_inputs(m)
    if blocking_issues(issues):
        stage(report, 'build', status='unconfirmed', reason='\n'.join(x['problem'] for x in issues))
        return report
    template = template_file(m)
    write_json(folder / 'slots.extracted.json', extracted)
    write_json(folder / 'values.json', values)
    fills_file = None
    if m.get('cell_fills'):
        fills_file = folder / 'cell_fills.json'
        write_json(fills_file, m['cell_fills'])
    if values or fills_file:
        stage(report, 'build', editor_command(template, report['work_file'], folder / 'values.json',
                                             draft_over_budget=bool(m.get('over_budget_cells')), cell_fills_file=fills_file))
    else:
        stage(report, 'build', status='pass', reason='모든 확인표 칸 유지: 원본 사본 보존')
    return report


def unbuilt_job(job):
    folder = job_dir(job)
    preflight = folder / 'preflight.json'
    if not preflight.is_file() and (folder / 'report.json').is_file():
        return None
    manifest = workspace_path(Path('.hwpdoc/prepared') / job / 'manifest.json')
    if not (folder / 'report.json').is_file() and (manifest.is_file() or not preflight.is_file()):
        result = check_job(job)
        result['errors'] = [issue['problem'] for issue in result['issues']]
    else:
        result = read_json(preflight)
    return dict(result, job_id=job, status='unconfirmed', ready=False,
                next_action=f'다음: check --job {job} 후 build. 기존 작업은 새 작업ID를 사용하세요.'
                if (folder / 'report.json').is_file() else f'다음: 고친 뒤 check --job {job} 후 build. 아직 생성하지 않았습니다.'
                + ('' if manifest.is_file() else ' prepared manifest 파일이 없습니다.'))


def structure_recovery():
    if (SKILL.parent.parent / 'hwpx-fallback/SKILL.md').is_file():
        return 'validate 2회 실패: hwpx-fallback F(양식 있음)/A(없음), strict 검사 후 주력 전체 검증'
    return ('validate 2회 실패: 이 설치에는 hwpx-fallback이 없습니다. 원본을 보존하고 한글에서 '
            '새 HWPX 사본으로 저장하거나 지원 양식으로 재생성한 뒤 전체 검증을 다시 수행하세요.')


def validate_document(report):
    sys.path.insert(0, str(SKILL))
    m = read_json(report['manifest_file'])
    refresh_validation_tools(report)
    for path in report.pop('visual_review_dependencies', []):
        report['dependencies'].pop(path, None)
    report.pop('validated_sha256', None)
    for name in STAGES:
        old = report['stages'].get(name, {})
        report['stages'][name] = {'status': 'unconfirmed', 'reason': '이번 파일 전체 검증 대기', 'failures': old.get('failures', 0), 'retry_baseline': old.get('retry_baseline', 0),
                                  'failure_basis': old.get('failure_basis'), 'at': old.get('at', now())}
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
            if name == 'structure' and report['stages'][name]['failures'] - report['stages'][name].get('retry_baseline', 0) < 2:
                if stage(report, name, argv):
                    continue
            report['fallback_next'] = structure_recovery() if name == 'structure' else '현재 단계 수정 후 재검증'
            save_report(report)
            return report
    reference = input_path(m['reference']) if m.get('reference') else (template_file(m) if m.get('base') else None)
    visual_status, visual_reason = 'unconfirmed', '예산 초과 PDF·전 페이지 PNG 판독 필요: review --job ' + m['job_id']
    if m.get('base'):
        shade_issues, shade_result = shading_inputs(m, template_file(m), resolved_values(m) if m.get('slots') else {}, output=f)
        report['shading'] = shade_result
        accepted = [item['key'] + ': ' + item['problem'] for item in (shade_result or {}).get('issues', []) if item['acknowledged']]
        reason = ('\n'.join(item['problem'] + '\n' + item['how_to_fix'] for item in shade_issues)
                  if shade_issues else '베이스 글자→배경 대조 통과')
        if accepted:
            reason += '\n교사의 현재 음영 유지 명시(shading_ack): ' + '; '.join(accepted)
        if shade_result and shade_result['notice']:
            reason += '\n' + shade_result['notice']
        status = 'pass'
        if shade_issues:
            if any(issue.get('blocking', True) for issue in shade_issues):
                status = 'fail'
            else:
                reason = '[WARN] 음영 확인 필요 — 막지 않음, 검토 때 한글에서 확인:\n' + reason
        if shade_result is not None and not shade_result['checked_tables'] and not shade_issues:
            status = 'not_applicable'
            reason = '음영 검사 제외: ' + json.dumps(shade_result['skipped_tables'], ensure_ascii=False)
        stage(report, 'shading', status=status, reason=reason)
    else:
        stage(report, 'shading', status='not_applicable', reason='슬롯 편집 베이스가 없는 기존 생성 경로')
    if reference:
        ref = folder / 'reference.finalized.hwpx'
        if m.get('cell_fills'):
            # Expected structure comes only from the reference plus hash-bound,
            # approved fill copies, never from the generated output.
            fills_file = folder / 'cell_fills.json'
            write_json(fills_file, m['cell_fills'])
            if not stage(report, 'reference_fills', [SKILL / 'edit_hwpx.py', reference, '-o', ref, '--cell-fills', fills_file]):
                return report
        else:
            shutil.copy2(reference, ref)
        # Profiles are generated only from the finalized reference COPY.
        for name, argv in [('reference_namespaces', [SKILL / 'fix_namespaces.py', ref]),
                           ('reference_finalize', [SKILL / 'finalize_hwpx.py', ref, '--strip-linesegarray']),
                           ('reference_profiles', [SKILL / 'page_guard.py', '--reference', ref,
                                                  '--write-budget', folder / 'budget.json', '--write-structure', folder / 'structure.json'])]:
            if not stage(report, name, argv):
                return report
        page_command = [SKILL / 'page_guard.py', '--reference', ref, '--output', f,
                  '--budget-profile', folder / 'budget.json', '--structure-profile', folder / 'structure.json',
                  '--no-strict-paragraph-budget', '--skip-text-drift', '--allow-empty-fill']
        if m.get('over_budget_cells'):
            from hwpdoc_review import record_path, consume, review_inputs, OBSERVATION_LIMIT
            receipt = record_path(m)
            if receipt.is_file() or m.get('visual_review_record'):
                try:
                    _, artifacts = consume(m, f, ref, report)
                    slots_file = folder / 'visual-review-slots.json'
                    write_json(slots_file, review_inputs(m, report))
                    page_command += ['--visual-render-review', receipt, '--visual-review-slots', slots_file]
                    report['visual_review_dependencies'] = [str(p.resolve()) for p in artifacts]
                    report['dependencies'].update({str(p.resolve()): sha(p) for p in artifacts})
                    visual_status, visual_reason = 'pass', '명시 확정 명령·현재 문서·원본·렌더 PDF·전 페이지 PNG·쪽수·신고 슬롯 대조 통과. ' + OBSERVATION_LIMIT
                except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
                    visual_reason = '판독 기록 미확인: ' + str(exc)
                report['visual_review_notice'] = OBSERVATION_LIMIT
        if m.get('paragraph_visual_record'):
            receipt = workspace_path(m['paragraph_visual_record'])
            page_command += ['--paragraph-render-review', receipt]
        page_ok = stage(report, 'page_guard', page_command)
        if page_ok and m.get('paragraph_visual_record'):
            proof = read_json(receipt)
            artifacts = [receipt, *[(receipt.parent / a['path']).resolve() for a in [proof['pdf'], *proof['images']]]]
            report['dependencies'].update({str(p.resolve()): sha(p) for p in artifacts})
        if not page_ok:
            report['structure_next'] = '실패 위치를 검토하세요. 활동 병합·내용 축약·구조 프로파일 재승인·검증 플래그 우회는 자동 수행하지 않습니다.'
    else:
        stage(report, 'page_guard', reason='기준 문서/승인된 구조 프로파일 없음: 기존 경로로 기준 확인 필요')
    stage(report, 'hancom', [SKILL / 'finalize_hwpx.py', f, '--hancom'], com=True)
    provenance = m.get('base_provenance')
    if m.get('base'):
        report['base_provenance_notice'] = '미등록 일회성 베이스; 원본 유래 미확인 유지, 베이스 사본과 결과물 렌더 대조 필요'
    if provenance in ('converted', 'repackaged') or m.get('over_budget_cells') or m.get('base'):
        if not reference:
            stage(report, 'render', reason='조건부 렌더 기준 파일 누락')
        else:
            stage(report, 'render', [CODE_ROOT / 'scripts/render_check.py', f, '--reference', reference, '--keep-pdf', folder / 'render.pdf'], com=True)
    elif provenance == 'native':
        stage(report, 'render', status='not_applicable', reason='네이티브 HWPX 일반 편집, 예산 초과 없음')
    else:
        stage(report, 'render', reason='base_provenance 미확인')
    if m.get('over_budget_cells'):
        # Existing inline evidence remains readable. A declared/existing external
        # receipt takes precedence, so stale receipts cannot fall back silently.
        from hwpdoc_review import record_path
        if not m.get('visual_review_record') and not record_path(m).exists():
            review = m.get('visual_review', {})
            artifacts = [review.get('pdf', {}), *review.get('images', [])]
            reviewed = (review.get('confirmed') is True and review.get('by') and review.get('at') and review.get('record')
                        and review.get('document_sha256') == sha(f) and review.get('images')
                        and all(x in review.get('cells', []) for x in m['over_budget_cells'])
                        and all(x.get('path') and input_path(x['path']).is_file() and x.get('sha256') == sha(input_path(x['path'])) for x in artifacts))
            if reviewed:
                visual_status, visual_reason = 'pass', '현재 문서 해시와 연결된 기존 인라인 PDF·PNG 판독 기록 확인'
        stage(report, 'visual_review', status=visual_status, reason=visual_reason)
    else:
        stage(report, 'visual_review', status='not_applicable', reason='신고된/자동 편집 예산 초과 없음')
    content_rules = dict(m['content_rules'])
    content_rules['forbid_regex'] = [*content_rules.get('forbid_regex', []), r'\[\[[^\]]+\]\]']
    write_json(folder / 'content.rules.json', content_rules)
    stage(report, 'content', [SKILL / 'content_guard.py', f, '--rules', folder / 'content.rules.json'])
    if m.get('slots', {}).get('values') or m.get('kept_slots'):
        from hwpx_slots import NS, _direct_text, _parse_section, collect_slots
        actual = {x['key']: x['preview'] for x in collect_slots(f, preview_len=1000000)['slots']}
        # collect_slots omits empty paragraphs. Read explicit blank decisions by
        # their actual address so a missing slot cannot count as a matched blank.
        values = resolved_values(m)
        if any(key.startswith('p:') and value == '' for key, value in values.items()):
            for index, paragraph in enumerate(_parse_section(f).xpath('.//hp:p', namespaces=NS)):
                key = f'p:{index}'
                if key in values and values[key] == '' and not paragraph.xpath('.//hp:p', namespaces=NS):
                    actual[key] = ' '.join(_direct_text(paragraph).split())
        mismatches = [key for key, value in values.items()
                      if actual.get(key) != ' '.join(value.split())]
        if m.get('kept_slots'):
            original = {x['key']: x['preview'] for x in collect_slots(reference, preview_len=1000000)['slots']}
            mismatches += [key for key in m['kept_slots'] if key not in original or actual.get(key) != original[key]]
        stage(report, 'values', status='fail' if mismatches else 'pass', reason='승인 슬롯값 대조: ' + str(mismatches or '일치'))
    elif m.get('expected_values'):
        from value_guard import (MIN_VALUE_CHARS, SHORT_KOREAN, check_values,
                                 erased_table_cells, extract_value_text, normalize)
        visible = extract_value_text(f)
        values_report = check_values(m['expected_values'], visible)
        missing = values_report['missing'] + [v for v in m['expected_values']
                   if len(normalize(v)) < MIN_VALUE_CHARS and not SHORT_KOREAN.fullmatch(v) and v not in visible]
        short_missing = values_report['short_missing']
        short_shortfall = values_report['short_shortfall']
        reason = '기존 경로의 필수값 대조'
        if missing:
            reason += ': ' + str(missing)
        elif not (short_missing or short_shortfall):
            reason += ': 일치'
        if short_missing:
            reason += '\nshort_missing: ' + json.dumps(short_missing, ensure_ascii=False)
        if short_shortfall:
            reason += '\n[WARN] short_shortfall (확인 필요): ' + json.dumps(short_shortfall, ensure_ascii=False)
        if reference:
            for cell in erased_table_cells(f, reference):
                reason += '\n[WARN] erased_cells: ' + cell['slot'] + ' (베이스 값 소거 검토)'
        stage(report, 'values', status='fail' if missing or short_missing else 'pass', reason=reason)
    else:
        stage(report, 'values', reason='기존 경로 검증에 expected_values(원문에서 확인한 필수값)가 필요합니다')
    gonmun = [SKILL / 'gonmun_lint.py', '--hwpx', f, '--format', 'json']
    year = (CONTEXT.settings.get('school') or {}).get('academic_year') if CONTEXT else None
    if isinstance(year, int) and not isinstance(year, bool):
        gonmun += ['--academic-year', str(year)]  # 본문 'NNNN학년도'가 없을 때의 기준
    stage(report, 'gonmun', gonmun)
    for name in ('budget_names', 'related', 'timetable'):
        check = m['checks'][name]
        if not check['applicable']:
            stage(report, name, status='not_applicable', reason=check['reason']); continue
        if name == 'budget_names' and check.get('names'):
            stage(report, name, [CODE_ROOT / 'scripts/budget_name_check.py', *[arg for value in check['names'] for arg in ('--check', value)]])
        elif name == 'related' and check.get('numbers'):
            failures = []
            for number in check['numbers']:
                sub = 'related:' + str(number)
                if not stage(report, sub, [CODE_ROOT / 'scripts/related_lookup.py', '--doc', str(number)]):
                    failures.append(number)
            stage(report, name, status='fail' if failures else 'pass', reason='관련번호 조회 실패: ' + str(failures) if failures else '모든 관련번호 조회 통과; 시행일·원문 인용은 근거 기록과 사람 검토 필요')
        elif name == 'timetable' and check.get('dates') and check.get('periods'):
            argv = [CODE_ROOT / 'scripts/fusion_timetable.py', *check['dates'], '--periods', check['periods'], '--json']
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


def document_excerpt(path, limit=1200):
    sys.path.insert(0, str(SKILL))
    from text_extract import extract_plain
    text = extract_plain(Path(path), include_tables=True).strip()
    return text[:limit] + ('\n… (나머지는 HWPX 원문 확인)' if len(text) > limit else '')


def delivery(report, *, draft=False, destination='configured'):
    if destination == 'configured':
        destination = ONEDRIVE
    from hwpdoc_pending import blockers, report_view, pending_summary, summary_text
    view = report_view(report)
    state = result_state(report, pending=view)
    changed = freshness(report)
    if changed:
        detail = ''
        if not draft:
            detail = '\n' + summary_text(pending_summary(view, report.get('stages'), changed))
        raise ValueError('검증 이후 파일/입력 변경. validate를 먼저 실행하세요' + detail)
    if state != 'pass' and not draft:
        summary = pending_summary(view, report.get('stages'))
        raise ValueError('전체 검증 미통과. 미확인 검토 초안은 deliver --draft로만 저장할 수 있습니다'
                         + ('\n' + summary_text(summary) if summary else '\nvalidate로 현재 파일의 전체 검증을 완료하세요.'))
    if any(item['id'] == 'manifest:read' for item in view['unresolved']):
        raise ValueError(summary_text(pending_summary(view)))
    if report['stages'].get('build', {}).get('status', 'pass') != 'pass':
        raise ValueError('build 미완료: 편집하지 않은 템플릿 사본은 배달하지 않습니다')
    if not draft:
        from hwpdoc_pending import sync_report
        sync_report(report)
    folder = workspace_path(Path('output') / report['job_id'])
    folder.mkdir(parents=True, exist_ok=True)
    label = '검증완료_검토대기' if state == 'pass' else '미확인_검토초안'
    target = folder / (label + '.hwpx')
    work = Path(report['work_file'])
    if target.exists() and sha(target) != sha(work):
        raise ValueError('기존 검토본 덮어쓰기 금지: 새 job_id를 사용하세요')
    shutil.copy2(work, target)
    snapshot = dict(report_record(report), delivery_status=state, human_review='pending', sent=False)
    write_json(folder / '검토보고서.json', snapshot)
    lines = [f'# {report["job_id"]}: {label}', '', NOTICE, '', '사람 검토 대기 · 발송은 사람이 합니다.', '',
             f'파일 SHA256: {sha(work)}', '']
    lines += [f'- {name}: {entry["status"]} — {entry.get("reason", "")[:500]}' for name, entry in report['stages'].items()]
    warnings = [warning for entry in report['stages'].values() for warning in entry.get('warnings', [])]
    lines += ['', '경고 (전체):', *['- ' + warning for warning in warnings]]
    lines += ['', '미확인: ' + json.dumps([item['text'] for item in blockers(view)], ensure_ascii=False)]
    reference_texts = [note for note in report.get('evidence_notes', []) if isinstance(note, str) and note]
    reference_texts += [item['text'] for item in view.get('reference_items', [])
                        if isinstance(item.get('text'), str) and item['text']]
    if reference_texts:
        memo = '참고 메모 (전달 차단 없음):\n' + '\n'.join(reference_texts)
        lines += ['', memo[:2000]]
    (folder / '검토보고서.md').write_text('\n'.join(lines), encoding='utf-8')
    m = read_json(report['manifest_file'])
    excerpt = document_excerpt(target)
    excerpt_file = folder / '본문발췌.txt'
    excerpt_file.write_text('최종 HWPX에서 추출한 읽기용 본문입니다. 인쇄/쪽 배치 미리보기가 아닙니다.\n\n'
                            + excerpt + '\n', encoding='utf-8')
    files = [target, folder / '검토보고서.json', folder / '검토보고서.md', excerpt_file]
    diff = work.parent / 'compare.diff'
    changes = []
    if diff.is_file():
        changes = [line[:240] for line in diff.read_text(encoding='utf-8').splitlines()
                   if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))][:4]
        target_diff = folder / 'compare.diff'
        shutil.copy2(diff, target_diff)
        files.append(target_diff)
    report['delivery_summary'] = {'file': str(target), 'text_excerpt': excerpt, 'changes': changes,
                                  'pending_checks': [name for name, entry in report['stages'].items()
                                                     if entry['status'] not in ('pass', 'not_applicable')],
                                  'warnings': warnings, 'next_action': NOTICE,
                                  'text_is_print_preview': False, 'human_review': 'pending'}
    for attachment in m['attachments']:
        src = input_path(attachment['path']); dest = folder / src.name
        if dest.exists() and sha(dest) != sha(src):
            raise ValueError('첨부 파일명 충돌: ' + src.name)
        shutil.copy2(src, dest); files.append(dest)
    failures = report.get('copy', {}).get('failures', 0)
    if destination is None:
        report['copy'] = dict(status='not_applicable', failures=failures, reason='작업 폴더에 외부 복사 위치 미설정')
        report['delivery'] = dict(local=str(target), status=state, human_review='pending', sent=False)
        save_report(report)
        write_json(folder / '검토보고서.json', dict(report_record(report), delivery_status=state, human_review='pending', sent=False))
        audit('deliver', target, 'pass', report['copy'])
        return report
    destination = Path(destination)
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
    write_json(receipt, dict(report_record(report), delivery_status=state, human_review='pending', sent=False))
    if report['copy']['status'] == 'pass':
        try:
            remote_receipt = Path(report['copy']['directory']) / receipt.name
            shutil.copy2(receipt, remote_receipt)
            if sha(receipt) != sha(remote_receipt):
                raise OSError('최종 복사 보고서 해시 불일치')
        except OSError as exc:
            report['copy'] = dict(status='fail', failures=failures + 1, reason=str(exc), at=now())
            save_report(report)
            write_json(receipt, dict(report_record(report), delivery_status=state, human_review='pending', sent=False))
    audit('deliver', target, report['copy']['status'], report['copy'])
    return report


def hwp_input_diagnostics(mode):
    """로컬 경로·모듈·COM 등록만 조회한다. 서버/한글/설치를 실행하지 않는다."""
    reader_command = shutil.which('kordoc')
    reader_errors = []
    packages = [ROOT / 'node_modules/kordoc/package.json', CODE_ROOT / 'node_modules/kordoc/package.json']
    if os.environ.get('APPDATA'):
        packages.append(Path(os.environ['APPDATA']) / 'npm/node_modules/kordoc/package.json')
    if os.environ.get('LOCALAPPDATA'):
        try:
            packages.extend((Path(os.environ['LOCALAPPDATA']) / 'npm-cache/_npx').glob('*/node_modules/kordoc/package.json'))
        except OSError as exc:
            reader_errors.append(str(exc))
    package = None
    for path in packages:
        try:
            if path.is_file():
                package = path
                break
        except OSError as exc:
            reader_errors.append(str(exc))
    reader = dict(status='unconfirmed', available=bool(reader_command or (package and shutil.which('node'))),
                  path=reader_command or (str(package) if package else None), actual_calls='unverified', errors=reader_errors,
                  note='kordoc Reader 로컬 경로만 확인. npx 존재만으로 설치/연결 성공을 판단하지 않습니다')

    com_module = importlib.util.find_spec('win32com')
    registered = False
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'HWPFrame.HwpObject\CLSID') as key:
                registered = bool(winreg.QueryValueEx(key, '')[0])
        except OSError:
            pass
    hancom = dict(status='not_run' if mode == 'xml' else 'unconfirmed',
                  available=bool(com_module and registered),
                  module_path=com_module.origin if com_module else None, registered=registered,
                  actual_calls='unverified',
                  note='한글 COM 모듈·등록만 확인. 실열림 검사는 문서 validate에서 별도 실행합니다')

    script = CODE_ROOT / '.claude/skills/hwpx-fallback/scripts/convert_hwp.py'
    location = None
    if script.is_file():
        spec = importlib.util.spec_from_file_location('_hwpdoc_converter_probe', script)
        converter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(converter)
        location = converter.converter_location()
    local_converter = dict(status='pass' if location else 'unconfirmed', available=bool(location), path=location,
                           actual_conversion='unverified',
                           note='로컬 HWP 변환기 경로만 확인. 없으면 한글에서 HWPX로 다른 이름으로 저장하거나 kordoc Reader 사용')
    return {'kordoc': reader, 'hancom': hancom, 'hwp_converter': local_converter}


def doctor(mode="full"):
    checks = {'python': {'status': 'pass' if sys.version_info[:2] == (3, 12) and PYTHON.is_file() and os.path.normcase(os.path.abspath(PYTHON)) == os.path.normcase(os.path.abspath(sys.executable)) else 'fail', 'path': sys.executable, 'selected_path': str(PYTHON), 'version': sys.version.split()[0]}}
    checks.update(runtime_diagnostics(CODE_ROOT, mode=mode))
    checks.update(hwp_input_diagnostics(mode))
    for name, path in [('output', ROOT / 'output'), ('external_copy', ONEDRIVE)]:
        if path is None:
            checks[name] = dict(status='not_applicable', note='선택 설정 없음'); continue
        checks[name] = dict(status='pass' if path.is_dir() and os.access(path, os.W_OK) else 'unconfirmed', path=str(path), note='실제 복사 성공은 deliver에서 별도 확인')
    checks['references'] = {key: ('available' if CONTEXT.local(value).exists() else 'unconfirmed') for key, value in CONTEXT.settings.get('references', {}).items()}
    checks['connections'] = {'configured': {key: value for key, value in CONTEXT.settings.get('connections', {}).items()
                                             if key != 'school_task_guide'}, 'actual_calls': 'unverified'}
    from hwpdoc_setup import mcp_diagnostics
    checks['teacher_doc_mcp'] = mcp_diagnostics()
    checks['hooks'] = {'registration': 'unverified', 'trust': 'unverified', 'actual_blocking': 'unverified'}
    required = ['python', 'lxml', 'hwpx', 'pypdf', 'output']
    if mode == 'full':
        required.append('hancom')
        if os.name == 'nt':
            required.append('win32com')
    states = [checks[name]['status'] for name in required]
    state = 'fail' if 'fail' in states else ('pass' if all(s == 'pass' for s in states) else 'unconfirmed')
    result = {'status': state, 'mode': mode, 'required_checks': required, 'at': now(), 'checks': checks, 'workspace': str(ROOT), 'pc_data': str(CONTEXT.pc_data), 'note': '자료 없음은 해당 업무에서 요청합니다. 환경 진단은 문서 검증이나 앱 통합 인수가 아닙니다'}
    write_json(workspace_path('.hwpdoc/doctor.json'), result)
    return result


def command_arg(value):
    """Quote a data argument for the documented PowerShell entry point."""
    return "'" + str(value).replace("'", "''") + "'"


def revision_command(job):
    # Suggest an unused ID; never create a job or reset failure counts here.
    for number in range(2, 10000):
        candidate = job[:85] + f'-r{number}'
        if not job_dir(candidate).exists() and not workspace_path(Path('.hwpdoc/prepared') / candidate).exists():
            return f'revise --job {job} --new-job {candidate}'
    return f'status --job {job}'


def declared_budget_review_pending(report):
    """Recognize only declared text-budget failures; never waive a guard verdict."""
    page = report.get('stages', {}).get('page_guard', {})
    if page.get('status') != 'fail':
        return False
    lines = [line.strip() for line in page.get('reason', '').splitlines() if line.strip()]
    if not lines or lines[0] != 'FAIL: page-guard' or len(lines) < 2:
        return False
    try:
        from hwpdoc_review import review_inputs
        m = read_json(report['manifest_file'])
        inputs = review_inputs(m)
        declared = {inputs['aliases'].get(key, key) for key in inputs['declared']}
        if not declared:
            return False
        for line in lines[1:]:
            match = re.match(r'- (cell:\d+:\d+:\d+:\d+|p:\d+)'
                             r'(?: \(확인표 [^)]*\))? 글자 예산 초과:', line)
            if not match:
                return False
            key = match[1]
            if key.startswith('cell:'):
                # Only occurrence zero has a checklist cell address.
                if not key.endswith(':0'):
                    return False
                key = key.rsplit(':', 1)[0]
            if key not in declared:
                return False
        return True
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        return False


def next_command(command, result, job, report=None, *, workflow_status=None):
    """Presentation only: never infer approval or perform the suggested step."""
    if not job:
        return 'doctor --mode xml'
    if report is None:
        report_file = job_dir(job) / 'report.json'
        if report_file.is_file() and load_report(report_file).get('resume_challenges'):
            # check/checklist and a refused rebuild must honor the same stop
            # guidance as validate; never suggest a new ID around the limit.
            return f'status --job {job}'
    if report is not None:
        stages = report.get('stages', {})
        state = workflow_status if workflow_status is not None else result_state(report)
        if report.get('resume_challenges'):
            return f'status --job {job}'  # Read the challenge before explicit human-authorized resume.
        changed = result['changed_files'] if 'changed_files' in result else freshness(report)
        # Match refresh_validation_tools' existing input boundary, including a
        # checklist edited after build. This only chooses guidance; no retry,
        # approval, dependency hash or validation state is modified here.
        tools = set(report.get('tool_dependencies', {})) | set(tool_dependencies())
        generated = set(report.get('visual_review_dependencies', []))
        changed_inputs = [path for path in changed
                          if path not in tools and path not in generated
                          and path not in (report.get('work_file'), '@runtime')]
        if changed_inputs:
            return revision_command(job)
        if stages.get('build', {}).get('status') not in (None, 'pass'):
            return f'status --job {job}'
        if report.get('delivery') and command in ('deliver', 'status') and not changed:
            if report.get('copy', {}).get('status') == 'fail':
                if report['copy'].get('failures', 0) >= 2:
                    return f'status --job {job}'
                draft = ' --draft' if state != 'pass' else ''
                return f'deliver --job {job}{draft}'
            target = report['delivery']['local']
            opener = 'Invoke-Item' if os.name == 'nt' else ('open' if sys.platform == 'darwin' else 'xdg-open')
            return f'{opener} {command_arg(target)}'
        if command == 'build' and stages.get('build', {}).get('status') == 'pass':
            return f'validate --job {job}'
        if result.get('confirmed') is True and command == 'review':
            return f'validate --job {job}'
        if command == 'review' and result.get('visual_review_record'):
            return (f'review --job {job} --confirm --by \'<판독자>\' '
                    "--record '<PDF·전 페이지 PNG를 실제로 본 내용>'")
        review_ready = all(stages.get(name, {}).get('status') == 'pass' for name in
                           ('structure', 'namespaces', 'finalize', 'layout', 'reference_profiles'))
        review_ready = review_ready and (stages.get('page_guard', {}).get('status') == 'pass'
                                         or declared_budget_review_pending(report))
        if review_ready and stages.get('visual_review', {}).get('status') == 'unconfirmed':
            if report.get('visual_review_confirmation'):
                return f'validate --job {job}'
            if report.get('visual_review_render'):
                return (f'review --job {job} --confirm --by \'<판독자>\' '
                        "--record '<PDF·전 페이지 PNG를 실제로 본 내용>'")
            return f'review --job {job}'
        if state == 'pass':
            return f'deliver --job {job}'
        if any(entry.get('status') == 'fail' for entry in stages.values()):
            return f'status --job {job}'  # Inspect failure evidence; do not suggest a new retry identity.
        return f'validate --job {job}'
    if command == 'checklist' and result.get('status') == 'filled':
        return f'checklist --job {job} --apply'
    if command == 'checklist' and result.get('status') in ('created', 'shown'):
        if job_dir(job).joinpath('report.json').is_file():
            return (revision_command(job) if result.get('matches_recorded_sha256') is False
                    else f'status --job {job}')
        if result.get('applied') and result.get('matches_recorded_sha256'):
            return f'check --job {job}'
        return (f'checklist --job {job} --apply' if result.get('unconfirmed_rows') == 0
                else f'checklist --job {job} --show')
    if command == 'checklist' and '현재 확인표가 없습니다' in result.get('error', ''):
        return f'checklist --job {job}'
    if command in ('record', 'draft') and 'revise --job' in result.get('error', ''):
        return revision_command(job)
    if command == 'draft' and 'checklist --job' in result.get('error', ''):
        return f'checklist --job {job} --apply'
    if result.get('status') == 'applied':
        return f'draft --job {job}'
    if command in ('prepare', 'record', 'draft'):
        return f'check --job {job}'
    if command == 'revise':
        return f'check --job {result.get("job_id", job)}'
    if job_dir(job).joinpath('report.json').is_file():
        return revision_command(job)
    before = [i for i in blocking_issues(result.get('issues', [])) if i.get('phase') == 'before_approval']
    if command == 'check' and before and all(i.get('field', '').startswith('draft.') for i in before):
        return f'draft --job {job}'
    if result.get('ready'):
        manifest = workspace_path(Path('.hwpdoc/prepared') / job / 'manifest.json')
        return f'build --manifest {command_arg(manifest)}'
    if result.get('ready_for_approval'):
        return f"approve --job {job} --by '<확인자>' --record '<제시한 초안에 대한 실제 교사 응답>'"
    return f'check --job {job}'


def cli_result(command, result, *, job=None, report=None, failed=False, details=False):
    """Add command receipts without changing stored workflow results or exit codes."""
    value = dict(result)
    job = value.get('job_id', job)
    if command == 'prepare' and not details and 'missing_by_owner' in value:
        owners = value['missing_by_owner']
        value = {key: value[key] for key in ('status', 'manifest', 'details_path', 'base_notice') if key in value}
        value.update(job_path=str(Path(result['manifest']).parent),
                     item_counts=dict(total=len(result['missing']), **{key: len(items) for key, items in owners.items()}),
                     top_blockers=[item[:160] for item in result['missing'][:3]])
    if report is not None:
        state = (result['status'] if command != 'review' and not failed and 'status' in result
                 else result_state(report))
    else:
        state = result.get('status', 'unconfirmed')
        if state not in ('pass', 'fail', 'unconfirmed'):
            state = 'unconfirmed'
    success = not failed and not result.get('error')
    if command == 'approve':
        success = success and bool(result.get('ready'))
    if command == 'review':
        success = success and bool(result.get('visual_review_record'))
    if report is not None:
        if command == 'build':
            success = success and report['stages'].get('build', {}).get('status') == 'pass'
        elif command == 'validate':
            success = success and state == 'pass'
        elif command == 'deliver':
            success = success and report.get('copy', {}).get('status') in ('pass', 'not_applicable')
    value.update(operation_status='success' if success else 'failure', workflow_status=state,
                 next_command=next_command(command, result, job, report, workflow_status=state))
    if report is not None:
        value['changed_files_meaning'] = '입력·의존 파일·검증 대상의 변경 목록입니다. 새 산출물 목록이 아닙니다.'
        paths = [report.get('work_file'), str(job_dir(job) / 'report.json'), report.get('delivery', {}).get('local')]
        value['artifacts'] = [dict(path=str(path), sha256=sha(path)) for path in dict.fromkeys(paths)
                              if path and Path(path).is_file()]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', help='교사 작업 폴더; 생략 시 표시 파일로 탐색')
    commands = parser.add_subparsers(dest='command', required=True)
    from hwpdoc_workspace import add_commands, dispatch, validate_cli_text
    add_commands(commands)
    import hwpdoc_setup
    hwpdoc_setup.add_commands(commands)
    doctor_parser = commands.add_parser('doctor')
    doctor_parser.add_argument('--mode', choices=['xml', 'full'], default='full',
                               help='xml은 COM 없는 연습 경로만, full은 한글 COM 로컬 준비 상태 포함 (실열림 미실행)')
    commands.add_parser('first-doc', help='개인정보 없는 연습 양식과 첫 HWPX 생성; 실제 승인/발송 아님')
    check = commands.add_parser('check', help='준비 입력의 build 사전 점검; 입력 수정 없음(내용 진단 content-check.json만 기록)')
    check.add_argument('--job', required=True)
    approve = commands.add_parser('approve', help='승인 전 항목 점검 후 교사의 실제 초안 확인 기록')
    approve.add_argument('--job', required=True)
    approve.add_argument('--by')
    approve.add_argument('--record')
    approve.add_argument('--carry-forward-from', help='revise 이전 작업의 동일 내용 교사 확인만 이월')
    revise = commands.add_parser('revise', help='기존 준비 입력을 새 작업으로 복사; 승인·판독은 복사하지 않음')
    revise.add_argument('--job', required=True)
    revise.add_argument('--new-job', required=True)
    review = commands.add_parser('review', help='생성 후 PDF·전 페이지 PNG 판독 초안 준비 또는 실제 판독 확정')
    review.add_argument('--job', required=True)
    review.add_argument('--confirm', action='store_true')
    review.add_argument('--refresh', action='store_true', help='기존 기록·자료를 보존하고 새 미확정 렌더 준비')
    review.add_argument('--by')
    review.add_argument('--record')
    build = commands.add_parser('build'); build.add_argument('--manifest', required=True)
    validate = commands.add_parser('validate')
    group = validate.add_mutually_exclusive_group(required=True)
    group.add_argument('--job'); group.add_argument('--manifest')
    deliver = commands.add_parser('deliver'); deliver.add_argument('--job', required=True); deliver.add_argument('--draft', action='store_true')
    status = commands.add_parser('status'); status.add_argument('--job', required=True)
    resume = commands.add_parser('resume', help='실제 원인 해결·사용자 확인 기록으로 중단된 검증 단계만 재개')
    resume.add_argument('--job', required=True); resume.add_argument('--stage', required=True); resume.add_argument('--record', required=True)
    args = parser.parse_args()
    job = getattr(args, 'job', None)
    try:
        validate_cli_text(args)
        if args.command == 'init':
            print(json.dumps(dispatch(args), ensure_ascii=False, indent=2)); return 0
        configure(args.workspace)
        if sys.version_info[:2] != (3, 12):
            raise RuntimeError('검증된 Python 3.12가 필요합니다. scripts/hwpdoc.ps1을 사용하세요')
        if args.command not in ('doctor', 'setup-runtime') and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(PYTHON)):
            raise RuntimeError('PC 설정에서 선택한 Python이 필요합니다. scripts/hwpdoc.ps1을 사용하세요')
        if args.command in ('school', 'prepare', 'record', 'draft', 'checklist'):
            result = dispatch(args)
            displayed = (cli_result(args.command, result, job=args.job, details=getattr(args, 'details', False))
                         if args.command in ('prepare', 'record', 'draft', 'checklist') else result)
            print(json.dumps(displayed, ensure_ascii=False, indent=2))
            if isinstance(result, dict):
                states = [entry.get('status') for entry in result.get('stages', {}).values()]
                if 'fail' in states:
                    return 1
                if 'unconfirmed' in states or result.get('status') == 'unconfirmed':
                    return 2
            return 0
        if args.command == 'doctor':
            result = doctor(args.mode)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return {'pass': 0, 'fail': 1, 'unconfirmed': 2}[result['status']]
        if args.command == 'first-doc':
            from hwpdoc_practice import first_doc
            print(json.dumps(first_doc(), ensure_ascii=False, indent=2)); return 0
        if args.command in ('setup-hooks', 'setup-runtime', 'setup-mcp'):
            result = {'setup-hooks': hwpdoc_setup.setup_hooks, 'setup-runtime': hwpdoc_setup.setup_runtime,
                      'setup-mcp': hwpdoc_setup.setup_mcp}[args.command](args)
            print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
        if args.command in ('check', 'approve'):
            result = check_job(args.job) if args.command == 'check' else approve_job(args.job, args.by, args.record, carry_forward_from=args.carry_forward_from)
            print(json.dumps(cli_result(args.command, result, job=args.job), ensure_ascii=False, indent=2))
            return 0 if result['ready'] else 2
        if args.command == 'revise':
            from hwpdoc_revisions import revise_job
            with lock(job_dir(args.job) / '.lock'):
                result = revise_job(args.job, args.new_job)
            print(json.dumps(cli_result(args.command, result, job=args.new_job), ensure_ascii=False, indent=2))
            return 0
        job = args.job if getattr(args, 'job', None) else read_json(input_path(args.manifest))['job_id']
        with lock(job_dir(job) / '.lock'):
            if args.command != 'build' and not getattr(args, 'manifest', None):
                blocked = unbuilt_job(job)
                if blocked:
                    print(json.dumps(cli_result(args.command, blocked, job=job, failed=True), ensure_ascii=False, indent=2))
                    return 2
            if args.command == 'build':
                report = build_document(args.manifest)
            elif args.command == 'validate':
                report = (initialize(args.manifest, build=False)[1] if args.manifest else load_report(job_dir(job) / 'report.json'))
                report = validate_document(report)
            else:
                report_file = job_dir(job) / 'report.json'
                report = load_report(report_file)
                if args.command == 'review':
                    from hwpdoc_review import review_job
                    result = review_job(report, confirm=args.confirm, refresh=args.refresh, by=args.by, record=args.record)
                    print(json.dumps(cli_result(args.command, result, job=job, report=report), ensure_ascii=False, indent=2))
                    return 0 if result['confirmed'] else 2
                if args.command == 'resume':
                    report = resume_document(report, args.stage, args.record)
                if args.command == 'deliver':
                    report = delivery(report, draft=args.draft)
                else:
                    save_report(report)
            result = {'job_id': job, 'status': result_state(report), 'report': str(job_dir(job) / 'report.json'),
                              'changed_files': freshness(report), 'copy': report.get('copy'),
                              'delivery_summary': report.get('delivery_summary'), 'resume_challenges': report.get('resume_challenges'), 'next_action': report['next_action']}
            print(json.dumps(cli_result(args.command, result, job=job, report=report), ensure_ascii=False, indent=2))
            if args.command == 'build':
                return 0 if report['stages'].get('build', {}).get('status') == 'pass' else 2
            if args.command == 'deliver':
                return 0 if report.get('copy', {}).get('status') in ('pass', 'not_applicable') else 1
            return {'pass': 0, 'fail': 1, 'unconfirmed': 2}[result_state(report)]
    except PreflightRejected as exc:
        print(json.dumps(cli_result(args.command, exc.result, job=getattr(args, 'job', None), failed=True), ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except (ValueError, KeyError, OSError, RuntimeError, TypeError) as exc:
        result = {'status': 'unconfirmed', 'error': str(exc)}
        # Invalid identifiers/configuration must still produce the original error.
        try:
            report_file = job_dir(job) / 'report.json' if job else None
            report = load_report(report_file) if report_file and report_file.is_file() else None
            result = cli_result(args.command, result, job=job, report=report, failed=True)
        except (ValueError, OSError, KeyError, TypeError):
            result.update(operation_status='failure', workflow_status='unconfirmed', next_command='doctor --mode xml')
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
