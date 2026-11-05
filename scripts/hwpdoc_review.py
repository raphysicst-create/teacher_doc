"""Command-bound visual receipts; actual human observation cannot be proven.

The report records explicit render/confirm operations. It is local workflow
state, not tamper-proof storage against someone able to rewrite the report too.
"""
import copy
from pathlib import Path
import tempfile

import hwpdoc as h

OBSERVATION_LIMIT = '명시적 확정 명령을 거쳤다는 기록만 확인하며, 사람이 실제로 이미지를 보았는지는 기계가 증명할 수 없습니다.'


def record_path(m):
    value = m.get('visual_review_record', f'.hwpdoc/jobs/{m["job_id"]}/visual-review.json')
    if not isinstance(value, str) or not value.strip():
        raise ValueError('visual_review_record는 작업 폴더 상대경로여야 합니다')
    path = h.workspace_path(value)
    if path.suffix.lower() != '.json':
        raise ValueError('visual_review_record는 JSON 경로여야 합니다')
    # Generated receipts must never overwrite source inputs or workflow state.
    protected = ('knowledge', 'docs', 'logs', '.hwpdoc/prepared', '.hwpdoc/templates')
    if any(path.is_relative_to(h.workspace_path(name)) for name in protected):
        raise ValueError('판독 기록은 원본·준비 입력 폴더 밖에 선언하세요. 기본값: .hwpdoc/jobs/<job_id>/visual-review.json')
    if path.is_relative_to(h.workspace_path('.hwpdoc')) and not path.is_relative_to(h.job_dir(m['job_id'])):
        raise ValueError('.hwpdoc 안의 판독 기록은 현재 작업의 jobs/<job_id>/ 안에 선언하세요')
    if path.name.lower() in ('report.json', 'budget.json', 'structure.json', 'visual-review-slots.json'):
        raise ValueError('검증 상태 파일을 판독 기록으로 사용할 수 없습니다')
    inputs = [m.get(k) for k in ('source', 'reference', 'shared_values_file')]
    for key in ('draft', 'checklist', 'base'):
        item = m.get(key)
        if isinstance(item, dict):
            inputs.append(item.get('path') or item.get('record'))
    for key in ('sources', 'attachments'):
        inputs += [item.get('path') for item in m.get(key, []) if isinstance(item, dict)]
    if any(isinstance(value, str) and value and h.input_path(value) == path for value in inputs):
        raise ValueError('판독 기록으로 준비 입력을 덮어쓸 수 없습니다')
    # Protect an old reference file when its path is usable; malformed optional
    # notes must not prevent an otherwise valid visual review.
    evidence = m.get('evidence')
    if isinstance(evidence, dict) and isinstance(evidence.get('record'), str) and evidence['record']:
        try:
            evidence_path = h.input_path(evidence['record'])
        except (ValueError, OSError):
            evidence_path = None
        if evidence_path == path:
            raise ValueError('판독 기록으로 준비 입력을 덮어쓸 수 없습니다')
    return path


def review_inputs(m, report=None):
    from hwpdoc_templates import extracted
    from hwpdoc_workspace import checklist_aliases
    inputs = dict(declared=m.get('over_budget_cells', []), aliases=checklist_aliases(m, extracted(h.template_file(m))))
    if report is not None:
        inputs.update(job_id=m['job_id'], render_record=report.get('visual_review_render'),
                      confirmation_record=report.get('visual_review_confirmation'))
    return inputs


def consume(m, work, reference, report=None):
    """One verifier used both by validate and the explicit confirmation command."""
    from page_guard import visual_render_keys
    path = record_path(m)
    if report is None:
        report = h.load_report(h.job_dir(m['job_id']) / 'report.json')
    if report.get('job_id') != m['job_id']:
        raise ValueError('판독 보고서 job_id 불일치')
    inputs = review_inputs(m, report)
    keys = visual_render_keys(path, reference, work, **inputs)
    proof = h.read_json(path)
    artifacts = [path, *[(path.parent / a['path']).resolve() for a in [proof['pdf'], *proof['images']]]]
    return keys, artifacts


def review_job(report, *, confirm=False, refresh=False, by=None, record=None):
    m = h.read_json(report['manifest_file'])
    if report.get('job_id') != m['job_id']:
        raise ValueError('판독 보고서 job_id 불일치')
    path = record_path(m)
    if not m.get('over_budget_cells'):
        raise ValueError('승인 입력에 over_budget_cells 신고가 없습니다')
    if refresh and confirm:
        raise ValueError('--refresh와 --confirm은 함께 쓸 수 없습니다. 새 이미지는 실제 판독 후 확정하세요')
    if (by or record) and not confirm:
        raise ValueError('--by/--record는 --confirm과 함께만 사용하세요')
    if confirm and (not isinstance(by, str) or not by.strip() or not isinstance(record, str) or not record.strip()):
        raise ValueError('--confirm에는 실제 판독자의 --by와 --record가 필요합니다')
    h.refresh_validation_tools(report)
    work = Path(report['work_file'])
    reference = work.parent / 'reference.finalized.hwpx'
    if (not reference.is_file() or any(report['stages'].get(s, {}).get('status') != 'pass'
                                     for s in ('structure', 'namespaces', 'finalize', 'layout', 'reference_profiles'))
            or report['stages']['finalize'].get('after_sha256') != h.sha(work)):
        raise ValueError('먼저 현재 work 파일로 validate를 실행해 정리·기준 프로파일을 확인하세요')
    inputs = review_inputs(m)
    if confirm:
        # Do not render here: the explicit confirmation refers to the exact
        # draft images that the observer has already seen.
        proof = h.read_json(path)
        candidate = dict(proof, confirmed=True, by=by, at=h.now(), record=record)
        # Validate without temporarily writing a confirmed receipt to disk.
        from page_guard import visual_render_evidence
        visual_render_evidence(path, reference, work, inputs['declared'], inputs['aliases'], review=candidate,
                               job_id=m['job_id'], render_record=report.get('visual_review_render'))
        if proof.get('confirmed') is True:
            raise ValueError('이미 확정된 판독 기록입니다. validate로 소비하세요')
        proof = candidate
    else:
        if path.exists():
            existing = h.read_json(path)
            if not (isinstance(existing, dict) and existing.get('kind') == 'hwpdoc-visual-review'
                    and existing.get('job_id') == m['job_id']):
                raise ValueError('기존 파일은 이 작업의 판독 기록이 아닙니다. 덮어쓰지 않습니다')
            if not refresh and existing.get('document_sha256') == h.sha(work):
                raise ValueError('미확정 기록은 실제 판독 후 --confirm, 확정 기록은 validate 하세요. 다시 렌더하려면 review --refresh를 쓰세요')
            # A changed current work file requires new images and observation,
            # while the old receipt and its assets remain available for audit.
            history = path.parent / (path.stem + '-history')
            history.mkdir(exist_ok=True)
            archived = history / (h.sha(path) + '.json')
            archived.write_bytes(path.read_bytes())
        path.parent.mkdir(parents=True, exist_ok=True)
        assets = Path(tempfile.mkdtemp(prefix=path.stem + '-assets-', dir=path.parent))
        pdf = assets / 'render.pdf'
        original_reference = h.input_path(m['reference']) if m.get('reference') else h.template_file(m)
        before = h.sha(work)
        if not h.stage(report, 'review_render', [h.CODE_ROOT / 'scripts/render_check.py', work,
                       '--reference', original_reference, '--keep-pdf', pdf], com=True):
            return dict(status='unconfirmed', confirmed=False, reason=report['stages']['review_render']['reason'])
        from hwpdoc_preview import render
        preview = render(pdf, assets / 'png', h.path_context())
        if h.sha(work) != before:
            raise ValueError('렌더 도중 문서 변경: 판독 기록을 만들지 않습니다')
        def artifact(item):
            p = h.workspace_path(item['path'])
            return dict(item, path=p.relative_to(path.parent).as_posix())
        proof = dict(version=1, kind='hwpdoc-visual-review', job_id=m['job_id'],
                     confirmed=False, by='', at='', record='', created_at=h.now(),
                     document_sha256=before, reference_sha256=h.sha(reference), cells=inputs['declared'],
                     page_count=len(preview['images']), pdf=artifact(preview['pdf']),
                     images=[artifact(item) for item in preview['images']])
    h.write_json(path, proof)
    if confirm:
        report['visual_review_confirmation'] = dict(record_sha256=h.sha(path), by=proof['by'], at=proof['at'])
    else:
        report['visual_review_render'] = copy.deepcopy({key: proof[key] for key in
            ('job_id', 'kind', 'created_at', 'document_sha256', 'reference_sha256', 'page_count', 'pdf', 'images')})
        report.pop('visual_review_confirmation', None)
    report['visual_review_notice'] = OBSERVATION_LIMIT
    # A newly confirmed generated receipt is consumed on the next validate.
    # Its previous digest is not an approved preparation input.
    report.pop('validated_sha256', None)
    h.save_report(report)
    h.audit('review', path, 'pass' if confirm else 'unconfirmed',
            {'confirmed': confirm, 'render': report['visual_review_render'],
             'confirmation': report.get('visual_review_confirmation'), 'notice': OBSERVATION_LIMIT})
    return dict(status='pass' if confirm else 'unconfirmed', confirmed=confirm,
                visual_review_record=str(path), pdf=proof['pdf'], images=proof['images'], notice=OBSERVATION_LIMIT,
                next_action=f'validate --job {m["job_id"]}' if confirm else
                f'PDF와 전 페이지 PNG를 실제로 본 뒤 review --job {m["job_id"]} --confirm --by <판독자> --record <판독 내용>')
