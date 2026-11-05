"""Copy preparation inputs and carry only unchanged, previously confirmed prose."""
import copy
from pathlib import Path
import re
import shutil

import hwpdoc as h


def prepared_manifest(job):
    h.job_dir(job)
    return h.workspace_path(Path('.hwpdoc/prepared') / job / 'manifest.json')


def revise_job(job, new_job):
    old_file, new_file = prepared_manifest(job), prepared_manifest(new_job)
    old_folder, folder = old_file.parent, new_file.parent
    if folder.exists() or h.job_dir(new_job).exists():
        raise ValueError('기존 준비 입력/작업은 덮어쓰지 않습니다. 새 --new-job을 사용하세요')
    m = h.read_json(old_file)
    if m.get('job_id') != job:
        raise ValueError('이전 manifest의 job_id 불일치')
    m = copy.deepcopy(m)
    copies, visiting = {}, set()

    def copy_input(value, *, structured=False):
        source = h.workspace_path(value)
        if source in visiting:
            raise ValueError('준비 입력의 순환 파일 참조')
        if source in copies:
            return copies[source].relative_to(h.ROOT).as_posix()
        if not source.is_file():
            raise ValueError('복사할 준비 입력 없음: ' + value)
        target = (folder / source.relative_to(old_folder) if source.is_relative_to(old_folder)
                  else folder / 'sources' / (h.sha(source)[:12] + '-' + source.name))
        target.parent.mkdir(parents=True, exist_ok=True)
        copies[source] = target
        visiting.add(source)
        if structured:
            h.write_json(target, rewrite(h.read_json(source)))
        else:
            shutil.copy2(source, target)
        visiting.remove(source)
        return target.relative_to(h.ROOT).as_posix()

    def rewrite(value):
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: rewrite(item) for key, item in value.items()}
        for key in ('path', 'ref'):
            candidate = value.get(key)
            if isinstance(candidate, str):
                try:
                    source = h.workspace_path(candidate)
                    exists = source.is_file()
                except (ValueError, OSError):
                    exists = False
                if exists:
                    result[key] = copy_input(candidate)
                    if 'sha256' in result:
                        result['sha256'] = h.sha(h.workspace_path(result[key]))
        if isinstance(value.get('fallback_sources'), list):
            result['fallback_sources'] = []
            for item in value['fallback_sources']:
                if isinstance(item, str):
                    try:
                        if h.workspace_path(item).is_file():
                            item = copy_input(item)
                    except (ValueError, OSError):
                        pass  # A quoted fallback description is not a path.
                else:
                    item = rewrite(item)
                result['fallback_sources'].append(item)
        return result

    # Only proposals have internal references rebased. Historical evidence
    # stays linked as a reference memo, without affecting required input copies.
    # Original documents/calendar responses, draft and base retain exact bytes.
    try:
        for key in ('base', 'sources', 'attachments', 'draft', 'checklist'):
            if key in m:
                m[key] = rewrite(m[key])
        for key in ('source', 'reference', 'shared_values_file'):
            if m.get(key):
                m[key] = copy_input(m[key])
        record = m.get('checklist', {}).get('proposals')
        if record and record.get('path'):
            # The proposal might already have been copied by rewrite(checklist).
            original = h.read_json(old_file)
            source_record = original['checklist']['proposals']
            old_path = h.workspace_path(source_record['path'])
            copies.pop(old_path, None)
            record['path'] = copy_input(source_record['path'], structured=True)
            record['sha256'] = h.sha(h.workspace_path(record['path']))
        if m.get('checklist'):
            # The evidence column names a rebased proposal source; decisions
            # and all other teacher prose remain untouched.
            import hwpdoc_workspace as w
            path = h.workspace_path(m['checklist']['path'])
            lines = path.read_text(encoding='utf-8-sig').splitlines(keepends=True)
            proposals = (h.read_json(h.workspace_path(m['checklist']['proposals']['path']))
                         if m['checklist'].get('proposals') else [])
            proposals = {p['slot']: p for p in proposals}
            for index, line in enumerate(lines):
                if re.match(r'^\|\s*\d+\s*\|', line):
                    cells = re.split(r'(?<!\\)\|', line)
                    key = cells[2].strip()
                    if key in proposals and proposals[key]['proposed'] is not None:
                        cells[5] = ' ' + w.checklist_cell(w.proposal_suggestion(proposals[key])[1]) + ' '
                        lines[index] = '|'.join(cells)
            path.write_text(''.join(lines), encoding='utf-8')
            m['checklist']['sha256'] = h.sha(path)
        slots = old_folder / 'slots.extracted.json'
        if slots.is_file():
            shutil.copy2(slots, folder / slots.name)
        m.update(job_id=new_job, previous_job_id=job,
                 draft_approval={'confirmed': False, 'by': '', 'at': '', 'record': '', 'input_sha256': ''})
        m.pop('approval_history', None)
        m.pop('visual_review', None)
        m.pop('paragraph_visual_record', None)
        if 'visual_review_record' in m or m.get('over_budget_cells'):
            m['visual_review_record'] = f'.hwpdoc/jobs/{new_job}/visual-review.json'
        h.write_json(new_file, m)
    except Exception:
        # Retain failed copies for diagnosis, never delete user inputs.
        raise
    h.audit('revise', new_file, 'unconfirmed', {'previous_job_id': job})
    return dict(status='unconfirmed', manifest=str(new_file), previous_job_id=job,
                next_action=f'check --job {new_job}; 내용이 같으면 approve --job {new_job} --carry-forward-from {job}')


def teacher_content(m):
    """Compare decisions, not job paths or regenerated layout artifacts."""
    from hwpdoc_workspace import parse_checklist, applied_checklist_values, checklist_aliases
    table = None
    if m.get('checklist'):
        path = h.workspace_path(m['checklist']['path'])
        if h.sha(path) != m['checklist']['sha256']:
            raise ValueError('확인표 파일 해시 불일치')
        entries, _ = parse_checklist(path.read_text(encoding='utf-8-sig'))
        from hwpdoc_templates import extracted
        slots = extracted(h.template_file(m))
        applied_checklist_values(m, slots, checklist_aliases(m, slots))
        table = [[row[1], row[5]] for row in entries]
    return dict(checklist_values=table, draft_sha256=h.sha(h.input_path(m['draft']['path'])),
                over_budget_cells=m.get('over_budget_cells', []), cell_fills=m.get('cell_fills', {}),
                shading_ack=m.get('shading_ack', []),
                values=h.resolved_values(m) if table is None else None,
                kept_slots=m.get('kept_slots', []) if table is None else None,
                base_sha256=h.sha(h.template_file(m)), workflow=m['workflow'], document_type=m['document_type'])


def carry_approval(m, previous_job):
    if m.get('previous_job_id') != previous_job:
        raise ValueError('--carry-forward-from은 revise의 previous_job_id와 같아야 합니다')
    path = prepared_manifest(previous_job)
    previous = h.read_json(path)
    # Old generator bugs do not erase actual teacher consent to a hash-bound
    # checklist/draft. The NEW job must pass today's full build preflight; the
    # source needs a valid original approval and unchanged preparation evidence.
    issues = h.blocking_issues(h.prerequisite_issues(previous, build=True))
    if issues:
        raise ValueError('이전 교사 확인/입력이 유효하지 않습니다. 새 approve --by --record 필요: '
                         + '; '.join(i['problem'] for i in issues))
    before, after = teacher_content(previous), teacher_content(m)
    changed = [key for key in before if before[key] != after[key]]
    if changed:
        raise ValueError('교사가 보는 내용 변경: ' + ', '.join(changed) + '. 새 approve --by --record 필요')
    approval = copy.deepcopy(previous['draft_approval'])
    approval['carried_forward_from'] = dict(job_id=previous_job, manifest_sha256=h.sha(path),
        approval={key: previous['draft_approval'][key] for key in ('by', 'at', 'record', 'input_sha256')},
        teacher_content_sha256=h.json_hash(before))
    # This is the carry operation's time, not a second human confirmation.
    # Original by/at/record remain in the source snapshot above. An identical
    # draft regenerated later must not require another teacher response.
    approval['at'] = h.now()
    return approval
