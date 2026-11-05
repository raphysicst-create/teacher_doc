"""Evidence-bound preparation guidance and delivery blockers.

This is a read-only projection of the approved inputs. Legacy source lists are
never rewritten, and a cached completion is never used as evidence.
"""
from collections import Counter
import copy
from pathlib import Path

import hwpdoc as h


# Exact messages emitted by prepare, not a fuzzy classifier for user facts.
TASK_FIELDS = {
    '유사/수신 원문과 양식 선택 근거': ('exploration', ('exploration', 'sources')),
    '받은 원문에서 확실한 날짜·장소·업무 사실 추출 및 초안 문안 준비': ('draft', ('draft',)),
    '예산명·관련번호·시간표 적용 여부(무관하면 이유 기록)': ('checks', ('checks', 'references')),
    '복사 잔재 이름·날짜와 forbid': ('reuse', ('reuse_review', 'content_rules')),
    '붙임 목록·미확인 사항 검토': ('attachments', ('attachments', 'attachment_mentions')),
    '수신 원문에서 제출 방법·기한·문서번호·시행일을 먼저 추출; 제출 방법이 없을 때만 질문': ('received', ('received',)),
}
LEGACY_EVIDENCE_TASK = '초안 전 업무 근거 조건·예외·최신판 확인'
LEGACY_EVIDENCE_FRESHNESS = '업무 근거 적용기간/최신판 미확인'
APPROVAL = '제시한 초안 문안의 파일 생성 확인'
DECISIONS = '원문/설정에서 찾지 못하거나 서로 충돌하는 사실·선택만 질문'
SLOT_PREFIX = '원문/설정에서 먼저 찾을 값: '
RENDER_NOTES = {
    '생성 후 렌더 확인 필요': ('render',),
    '생성 후 렌더·육안 확인 필요': ('render', 'visual_review'),
    '생성 후 렌더·판독 확인 필요': ('render', 'visual_review'),
}


def preparation_task(text, slot=None):
    """Immutable instructions; status and receipts belong in the job report."""
    if slot:
        kind = 'slot_lookup'
    elif text == LEGACY_EVIDENCE_TASK:
        kind = 'evidence'
    elif text == APPROVAL:
        kind = 'draft_approval'
    elif text == DECISIONS:
        kind = 'decisions'
    else:
        kind = TASK_FIELDS.get(text, ('guidance', ()))[0]
    task = dict(kind=kind, text=text)
    if slot:
        task['slot'] = slot
    return task


def pending_view(m, evidence=None, report=None):
    """Recompute completion from current files, without changing any inputs."""
    issues = h.prerequisite_issues(m, build=bool(m.get('slots')))
    def fields_ok(prefixes):
        return not any(i['field'] == p or i['field'].startswith((p + '.', p + '['))
                       for i in issues for p in prefixes)

    approved = fields_ok(('draft_approval',))
    approval = m.get('draft_approval', {})
    approval_proof = dict(kind='draft_approval', approval=copy.deepcopy(approval)) if approved else None
    input_proof = dict(kind='manifest_fields', input_sha256=h.json_hash(h.approval_payload(m)))
    slots, aliases, meanings, selected, table_proof = {}, {}, {}, set(), None
    fixed_scope = set()
    table_error = None
    if m.get('slots'):
        try:
            from hwpdoc_templates import extracted, resolve_template
            from hwpdoc_workspace import checklist_aliases, applied_checklist_values, checklist_fixed_scope
            extracted_slots = extracted(h.template_file(m))
            slots = {s['key']: s for s in extracted_slots['slots']}
            if isinstance(m.get('template'), dict):
                meanings = resolve_template(m['template'])['mapping']
            aliases = checklist_aliases(m, extracted_slots)
            record = m.get('checklist', {})
            if record and record.get('applied') is not False and fields_ok(('checklist',)):
                values, kept = applied_checklist_values(m, extracted_slots, aliases)
                mismatch, _ = h.checklist_input_issues(m, extracted_slots, aliases)
                if not mismatch:
                    selected = set(values) | set(kept)
                    table_proof = dict(kind='applied_checklist', path=record['path'], sha256=record['sha256'])
                    fixed_scope = checklist_fixed_scope(h.workspace_path(record['path']).read_text(encoding='utf-8-sig'),
                                                        extracted_slots, aliases, selected)
                    if record.get('proposals'):
                        table_proof['proposals'] = copy.deepcopy(record['proposals'])
        except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
            table_error = str(exc)

    def covered(key):
        if key in selected or aliases.get(key) in selected:
            return True
        children = {p for p, cell in aliases.items() if cell == key}
        return bool(children) and children <= selected

    def legacy_task(raw):
        if raw in TASK_FIELDS or raw in (APPROVAL, DECISIONS, LEGACY_EVIDENCE_TASK):
            return preparation_task(raw)
        # Match the complete generated message against the actual base slot.
        for key, slot in slots.items():
            text = str(slot.get('text', slot.get('preview', '')))[:100]
            if raw == SLOT_PREFIX + key + ' (의미 확인 필요; 기존 문구: ' + text + ')':
                return preparation_task(raw, key)
        for meaning, key in meanings.items():
            if raw == SLOT_PREFIX + meaning:
                return preparation_task(raw, key)
        return None

    tasks, unresolved, resolved, reference_items = [], [], [], []
    reference_keys = set()
    def reference_state(raw, identifier):
        key = h.json_hash(raw)
        if key not in reference_keys:
            reference_keys.add(key)
            reference_items.append(dict(id=identifier, category='evidence', original=copy.deepcopy(raw),
                text=raw if isinstance(raw, str) else str(raw.get('text', raw)) if isinstance(raw, dict) else str(raw)))

    def task_state(raw, identifier):
        task = copy.deepcopy(raw)
        for key in ('status', 'blocking', 'completion_evidence', 'scope_evidence', 'note', 'reason', 'id'):
            task.pop(key, None)  # A stored claim is never a completion receipt.
        if not isinstance(task.get('text'), str):
            task['text'] = str(raw)
        kind, text = task.get('kind'), task.get('text', '')
        proof, blocking = None, True
        if kind == 'evidence' or text == LEGACY_EVIDENCE_TASK:
            # Preserve old preparation records without requiring a connection
            # or pretending that their instructions have been completed.
            blocking = False
            task['note'] = '이전 업무 근거 안내: 참고 기록'
        elif kind == 'slot_lookup':
            key = task.get('slot')
            if isinstance(key, str) and key in slots and table_proof and covered(key):
                proof = dict(table_proof, slot=key)
            elif isinstance(key, str) and key in fixed_scope and table_proof and approved:
                # The confirmed table defines the editing scope. Fixed headings
                # outside it remain guidance, not an invented confirmed value.
                blocking = False
                task['scope_evidence'] = dict(table_proof, slot=key, kind='checklist_fixed_text', approval=approval_proof)
                task['note'] = '확인표 대상 밖 안내: 완료 처리하지 않음'
            elif table_error:
                task['reason'] = table_error
        elif kind == 'draft_approval' and text == APPROVAL:
            proof = approval_proof
        elif kind == 'decisions' and text == DECISIONS:
            if table_proof and approved:
                proof = dict(table_proof, approval=approval_proof)
            elif not m.get('checklist') and approved and not any(i['phase'] == 'before_approval' for i in issues):
                proof = dict(input_proof, approval=approval_proof)
        elif isinstance(text, str) and text in TASK_FIELDS and kind == TASK_FIELDS[text][0]:
            prefixes = TASK_FIELDS[text][1]
            if fields_ok(prefixes):
                proof = dict(input_proof, fields=list(prefixes))
        task.update(id=identifier, status='completed' if proof else 'pending', blocking=blocking and not bool(proof))
        if proof:
            task['completion_evidence'] = proof
        tasks.append(task)

    def item_state(raw, identifier, category):
        if category == 'evidence' or isinstance(raw, dict) and raw.get('kind') == 'evidence':
            reference_state(raw, identifier)
            return
        stages = None
        if isinstance(raw, str) and raw in RENDER_NOTES:
            stages = RENDER_NOTES[raw]
        elif isinstance(raw, dict) and raw.get('kind') == 'validation':
            requested = raw.get('stages')
            if isinstance(requested, list) and requested and all(s in h.STAGES for s in requested):
                stages = requested
        item = dict(id=identifier, category='validation' if stages else category, original=copy.deepcopy(raw),
                    text=raw if isinstance(raw, str) else str(raw.get('text', raw)) if isinstance(raw, dict) else str(raw))
        if stages and report:
            work = Path(report['work_file'])
            digest = h.sha(work) if work.is_file() else None
            entries = {s: report.get('stages', {}).get(s, {}) for s in stages}
            visual_proof, visual_ok = None, True
            if 'visual_review' in stages and report.get('visual_review_confirmation') is not None:
                # The executor's existing confirmation binds a receipt file.
                # Reports themselves remain trusted local workflow records.
                try:
                    from hwpdoc_review import record_path
                    path = record_path(m)
                    receipt = h.read_json(path)
                    visual_ok = (h.sha(path) == report['visual_review_confirmation']['record_sha256']
                                 and receipt.get('confirmed') is True
                                 and receipt.get('document_sha256') == digest)
                    if visual_ok:
                        visual_proof = dict(path=str(path), sha256=h.sha(path), document_sha256=digest)
                except (OSError, ValueError, KeyError, TypeError, AttributeError):
                    visual_ok = False
            if digest and visual_ok and all(e.get('status') == 'pass' and e.get('after_sha256') == digest for e in entries.values()):
                item['completion_evidence'] = dict(kind='validation', document_sha256=digest,
                    stages={s: {k: e.get(k) for k in ('status', 'at', 'after_sha256')} for s, e in entries.items()})
                if visual_proof:
                    item['completion_evidence']['visual_review_record'] = visual_proof
                resolved.append(item)
                return
        unresolved.append(item)

    raw_tasks = m.get('preparation_tasks', [])
    if not isinstance(raw_tasks, list):
        item_state(raw_tasks, 'preparation_tasks', 'guidance')
    else:
        for index, task in enumerate(raw_tasks):
            if isinstance(task, dict):
                task_state(task, f'preparation_tasks:{index}')
            else:
                item_state(task, f'preparation_tasks:{index}', 'guidance')
    original = m.get('unresolved', [])
    for index, raw in enumerate(original):
        task = legacy_task(raw) if isinstance(raw, str) else None
        if task:
            task_state(task, f'unresolved:{index}')
        else:
            item_state(raw, f'unresolved:{index}', 'facts')
    if evidence is None:
        try:
            evidence = h.read_json(h.input_path(m['evidence']['record']))
        except (ValueError, OSError, KeyError, TypeError):
            evidence = {}
    if not isinstance(evidence, dict):
        evidence = {}
    pending = evidence.get('pending_items', [])
    pending = pending if isinstance(pending, list) else []
    for index, raw in enumerate(pending):
        item_state(raw, f'evidence:{index}', 'evidence')
    if evidence and evidence.get('freshness') != 'verified':
        item_state(LEGACY_EVIDENCE_FRESHNESS, 'evidence:freshness', 'evidence')
    recorded = []
    if report:
        # Old reports may also contain manually recorded blockers. Preserve all
        # records not accounted for by the manifest/evidence, including repeats.
        # Evidence prose belongs to the optional reference memo even when an old
        # executor copied it into the report's unresolved array.
        old_evidence = report.get('evidence', {})
        old_pending = old_evidence.get('pending_items', []) if isinstance(old_evidence, dict) else []
        old_pending = old_pending if isinstance(old_pending, list) else []
        for index, raw in enumerate(old_pending):
            item_state(raw, f'evidence:report:{index}', 'evidence')
        if isinstance(old_evidence, dict) and old_evidence and old_evidence.get('freshness') != 'verified':
            item_state(LEGACY_EVIDENCE_FRESHNESS, 'evidence:report:freshness', 'evidence')
        previous = report.get('pending_state') or {}
        previous_evidence = [*[item.get('original', item.get('text')) if isinstance(item, dict) else item
                               for item in previous.get('reference_items', [])],
                             *[item.get('original', item.get('text'))
                               for item in previous.get('unresolved', []) if evidence_item(item)]]
        for index, raw in enumerate(previous_evidence):
            item_state(raw, f'evidence:previous:{index}', 'evidence')
        legacy_counts = (Counter(h.json_hash(x) for x in pending)
                         | Counter(h.json_hash(x) for x in old_pending)
                         | Counter(h.json_hash(x) for x in previous_evidence))
        legacy_counts |= Counter(h.json_hash(x) for x in [LEGACY_EVIDENCE_FRESHNESS,
                                  '업무 근거 기록 미확인', '업무 근거 기록 JSON 객체 미확인',
                                  '업무 근거 pending_items 형식 오류'])
        counts = Counter(h.json_hash(x) for x in original)
        for index, raw in enumerate(report.get('unresolved_original', report.get('unresolved', []))):
            key = h.json_hash(raw)
            if counts[key]:
                counts[key] -= 1
            elif legacy_counts[key]:
                legacy_counts[key] -= 1
                item_state(raw, f'evidence:report_unresolved:{index}', 'evidence')
            else:
                item_state(raw, f'report:{index}', 'facts')
        if previous:
            recorded = copy.deepcopy(previous.get('recorded_unresolved', []))
            expected = Counter(h.json_hash(x['text']) for x in [*previous.get('unresolved', []),
                               *[t for t in previous.get('preparation_tasks', []) if t['blocking']]])
            for raw in report.get('unresolved', []):
                key = h.json_hash(raw)
                if expected[key]:
                    expected[key] -= 1
                else:
                    recorded.append(copy.deepcopy(raw))
            for index, raw in enumerate(recorded):
                item_state(raw, f'report_added:{index}', 'facts')
    return dict(version=1, preparation_tasks=tasks, unresolved=unresolved, resolved=resolved,
                recorded_unresolved=recorded, reference_items=reference_items)


def evidence_item(item):
    original = item.get('original')
    return (item.get('category') == 'evidence' or str(item.get('id', '')).startswith('evidence:')
            or isinstance(original, dict) and original.get('kind') == 'evidence')


def blockers(view):
    return [*[item for item in view['unresolved'] if not evidence_item(item)],
            *[dict(t, category='preparation') for t in view['preparation_tasks'] if t['blocking'] and t.get('kind') != 'evidence']]


def pending_summary(view, stages=None, changed=None):
    groups = {}
    fixes = {
        'preparation': '확인표를 확정·apply하고 check 후 실제 초안 확인을 approve로 기록하세요. 대상 밖 안내는 완료로 표시하지 않습니다.',
        'facts': '해당 원문 또는 교사 답으로 값을 확인하고 입력·초안을 다시 확인받으세요.',
        'guidance': '안내의 완료 근거를 확인하세요. 기계로 확인할 수 없는 안내는 남습니다.',
        'validation': '실패 원인을 고쳐 validate를 실행하세요. 판독 대기는 review → 실제 PNG 판독 → review --confirm → validate 순서입니다.',
        'freshness': '작업용 파일·검증 코드 변경은 validate, 승인 입력·근거 변경은 새 확인·새 작업으로 진행하세요.',
    }
    for item in blockers(view):
        groups.setdefault(item['category'], []).append(item['text'])
    if stages is not None:
        for name in dict.fromkeys([*h.STAGES, *stages]):
            entry = stages.get(name, {})
            if entry.get('status') not in ('pass', 'not_applicable'):
                groups.setdefault('validation', []).append(name + ': ' + entry.get('status', 'unconfirmed'))
    if changed:
        groups['freshness'] = list(changed)
    return {kind: dict(count=len(items), items=[s[:160] for s in items[:3]], how_to_fix=fixes[kind]) for kind, items in groups.items()}


def summary_text(summary):
    labels = {'preparation': '준비 안내', 'facts': '값·판단',
              'guidance': '미확인 안내', 'validation': '검증·판독', 'freshness': '입력·파일 변경'}
    return '\n'.join(f'{labels[kind]} {group["count"]}건: ' + '; '.join(group['items'])[:240]
                     + '\n해소: ' + group['how_to_fix'] for kind, group in summary.items() if kind != 'evidence')


def report_view(report):
    """Unreadable or non-object input is a blocker, never an empty manifest."""
    try:
        m = h.read_json(report['manifest_file'])
        if not isinstance(m, dict):
            raise ValueError('JSON 객체가 아닙니다')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        view = copy.deepcopy(report.get('pending_state', {}))
        view.setdefault('version', 1)
        view.setdefault('preparation_tasks', [])
        view.setdefault('unresolved', [dict(id=f'report:{i}', category='facts', text=str(raw), original=raw)
                                     for i, raw in enumerate(report.get('unresolved_original', report.get('unresolved', [])))])
        references = []
        reference_keys = set()
        for index, item in enumerate([*view.get('reference_items', []),
                                      *[item for item in view['unresolved'] if evidence_item(item)]]):
            raw = item.get('original', item.get('text')) if isinstance(item, dict) else item
            key = h.json_hash(raw)
            if key not in reference_keys:
                reference_keys.add(key)
                references.append(dict(id=f'evidence:cached:{index}', category='evidence', original=copy.deepcopy(raw),
                    text=raw if isinstance(raw, str) else str(raw.get('text', raw)) if isinstance(raw, dict) else str(raw)))
        view['reference_items'] = references
        # Keep newly recorded facts even while the manifest is unavailable.
        # Completed tasks are not report entries; counting them would swallow a
        # newly recorded fact with the same wording.
        expected = Counter(h.json_hash(item['text']) for item in [
            *view['unresolved'], *[t for t in view['preparation_tasks'] if t['blocking'] or t.get('kind') == 'evidence']])
        for raw in report.get('unresolved', []):
            key = h.json_hash(raw)
            if expected[key]:
                expected[key] -= 1
            else:
                recorded = view.setdefault('recorded_unresolved', [])
                recorded.append(copy.deepcopy(raw))
                view['unresolved'].append(dict(id=f'report_added:{len(recorded) - 1}', category='facts',
                                               text=str(raw), original=copy.deepcopy(raw)))
        view['resolved'] = []
        for item in view['unresolved']:
            raw = item.get('original', item.get('text'))
            if evidence_item(item) and h.json_hash(raw) not in reference_keys:
                reference_keys.add(h.json_hash(raw))
                view['reference_items'].append(copy.deepcopy(item))
        view['unresolved'] = [item for item in view['unresolved']
                              if item['id'] != 'manifest:read' and not evidence_item(item)]
        view['unresolved'].append(dict(id='manifest:read', category='facts', text='입력 manifest 읽기 실패: ' + str(exc)))
        return view
    return pending_view(m, report=report)


def sync_report(report):
    """Persist transitions in reports only; signed manifests retain exact bytes."""
    report.setdefault('unresolved_original', copy.deepcopy(report.get('unresolved', [])))
    view = report_view(report)
    previous = report.get('pending_state', {})
    def entries(state):
        return {item['id']: item for key in ('preparation_tasks', 'unresolved', 'resolved') for item in state.get(key, [])}
    old = entries(previous)
    for identifier, item in entries(view).items():
        if old.get(identifier) != item:
            report.setdefault('pending_history', []).append(dict(at=h.now(), id=identifier,
                before=old.get(identifier), after=copy.deepcopy(item)))
    report['pending_state'] = view
    report['unresolved'] = [item['text'] for item in blockers(view)]
    report['pending_summary'] = pending_summary(view, report.get('stages'))
    return view
