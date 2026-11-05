"""Pre-approval diagnostics on the editor's disposable copy, never a build input.

The authoritative guards still run independently during validate. In particular,
an explicit decision to retain a forbidden value is NOT a content_guard waiver.
"""
from collections import defaultdict
from pathlib import Path
import html
import json
import re
import tempfile
from zipfile import ZipFile

import hwpdoc as h

KEEP_RESIDUE = '유지(잔재 확인)'
KEEP_DATE = '유지(표기 확인)'
NORMALIZE_PREFIX = '표기 정리: '
FINAL_CONTENT_POLICY = '유지 결정은 기록만 합니다. 기존 forbid 규칙은 그대로여서 생성 후 content 검증은 실패합니다.'


def normalize_dates(text):
    """Only four-digit dotted dates; never infer a year or change a weekday."""
    # Consume the optional final dot atomically: a failed suffix check must not
    # backtrack past it and turn an identifier like 2026.01.02.003 into a date.
    # Hangul suffixes are safe only after that final dot; keep ambiguous tokens
    # without it (e.g. 2026.01.02호) protected by the original word boundary.
    def replace(match):
        month, day = int(match[2]), int(match[3])
        return (f'{match[1]}. {month}. {day}.' if 1 <= month <= 12 and 1 <= day <= 31
                else match[0])
    return re.sub(r'(?<![\w.-])(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})(?!\d)(?>\.?)'
                  r'(?:(?![\w-])|(?<=\.)(?=[가-힣]))',
                  replace, text)


def residue_receipts(m, content):
    from hwpdoc_workspace import parse_checklist
    rows, _ = parse_checklist(content)
    return {row[1]: dict(decision=KEEP_RESIDUE, value_sha256=h.json_hash(row[2]),
                         rules_sha256=h.json_hash(m.get('content_rules', {})),
                         final_content_policy=FINAL_CONTENT_POLICY)
            for row in rows if row[5] == KEEP_RESIDUE}


def normalized_checklist(content):
    """Batch choice covers resolved 유지 values; explicit formatting vetoes stay."""
    from hwpdoc_workspace import parse_checklist, checklist_cell
    rows, start = parse_checklist(content)
    lines = content.splitlines()
    count = 0
    for offset, row in enumerate(rows, start + 2):
        value = row[5]
        if value in (KEEP_DATE, KEEP_RESIDUE, '비움', '값만 비움', '문단 비움'):
            continue
        if value == '유지':
            value = row[2]
        # A per-slot keyword is interpreted by --apply, then materialized here
        # so reconciliation always sees exactly the table the teacher chose.
        if value.startswith(NORMALIZE_PREFIX):
            value = value[len(NORMALIZE_PREFIX):]
        normalized = normalize_dates(value)
        if value != normalized or row[5].startswith(NORMALIZE_PREFIX):
            count += 1
            row[5] = normalized
            lines[offset] = '| ' + ' | '.join(map(checklist_cell, row)) + ' |'
    return '\n'.join(lines) + '\n', count


def _locations(path, m, aliases):
    """Reconstruct each guard's line ownership from XML, not preview matching.

    content_guard includes ancestor paragraphs containing nested tables. Each
    line therefore retains its descendant text owners, avoiding false assignment
    to the outer wrapper. Other sections use section-qualified addresses.
    """
    from lxml import etree
    from hwpx_slots import NS
    selected = set(m.get('slots', {}).get('values', {})) | set(m.get('kept_slots', []))
    def address(key, section):
        if section != 'Contents/section0.xml':
            return section + '#' + key
        if key in selected:
            return key
        cell = aliases.get(key)
        return cell if cell in selected else key
    content_lines, gonmun_lines = [], []
    with ZipFile(path) as archive:
        for section in sorted(n for n in archive.namelist()
                              if re.fullmatch(r'Contents/section\d+\.xml', n)):
            root = etree.fromstring(archive.read(section), etree.XMLParser(resolve_entities=False))
            paragraphs = root.xpath('.//hp:p', namespaces=NS)
            keys = {p: address(f'p:{i}', section) for i, p in enumerate(paragraphs)}
            def owners(node):
                chunks = defaultdict(str)
                for t in node.xpath('.//hp:t', namespaces=NS):
                    parent = t.getparent()
                    while parent is not None and parent not in keys:
                        parent = parent.getparent()
                    chunks[keys.get(parent, section)] += ''.join(t.itertext())
                return dict(chunks)
            for p in paragraphs:
                text = ''.join(''.join(t.itertext()) for t in p.xpath('.//hp:t', namespaces=NS)).strip()
                if text:
                    # extract_plain joins nonempty paragraphs, including embedded newlines.
                    content_lines.extend([owners(p)] * len(text.splitlines()))
            # Follow exactly the raw hp:t stream used by gonmun_lint. In
            # particular, self-closing empty hp:t nodes do not create a line.
            stack, index = [], 0
            xml = archive.read(section).decode('utf-8', 'replace')
            stream = r'<hp:p\b[^>]*>|</hp:p\s*>|<hp:t(?:\s[^>]*)?>(.*?)</hp:t>'
            for match in re.finditer(stream, xml, re.DOTALL):
                token = match[0]
                if token.startswith('</hp:p'):
                    if stack:
                        stack.pop()
                elif token.startswith('<hp:p'):
                    stack.append(address(f'p:{index}', section))
                    index += 1
                    if token.endswith('/>'):
                        stack.pop()
                else:
                    text = html.unescape(re.sub(r'<[^>]+>', '', match[1]))
                    gonmun_lines.extend([stack[-1] if stack else section] * (text.count('\n') + 1))
    return content_lines, gonmun_lines


def inspect_inputs(m, template, extracted, values, aliases, *, draft_over_budget, checklist_labels,
                   undeclared=None, inspect=None):
    """Cache only completed editor checks, before invoking either editor pass."""
    payload = dict(manifest=h.approval_payload(m), extracted=extracted,
                   template=h.sha(template), values=values, aliases=aliases,
                   draft_over_budget=draft_over_budget, undeclared=undeclared,
                   checklist_labels=checklist_labels,
                   settings=h.CONTEXT.settings if h.CONTEXT else {}, tools=h.tool_dependencies())
    record = m.get('checklist')
    if record:
        payload['checklist_file'] = h.sha(h.workspace_path(record['path']))
    if m.get('shared_values_file'):
        payload['shared_values_file'] = h.sha(h.input_path(m['shared_values_file']))
    digest = h.json_hash(payload)
    cache = Path(tempfile.gettempdir()) / 'hwpdoc-content-cache' / (h.json_hash(str(h.ROOT)) + '.json')
    try:
        stored = h.read_json(cache)
        if (inspect is None and stored.get('input_sha256') == digest and stored.get('editor_ok') is True
                and isinstance(stored.get('detail'), dict)
                and h.json_hash(stored['detail']) == stored.get('detail_sha256')):
            return [], stored['detail']
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        pass
    # A failed/interrupted attempt must not leave a previous successful entry
    # reusable as the most recent check.
    try:
        h.write_json(cache, dict(input_sha256=digest, editor_ok=False))
    except OSError:
        pass
    issues, detail = [], {}
    if undeclared:
        issues += h.editor_issues(template, undeclared, checklist_labels=checklist_labels)
    def inspect_edited(path, folder):
        detail.update(inspect_copy(path, folder, m, template, extracted, values, aliases))
        if inspect:
            inspect(path, folder)
    issues += h.editor_issues(template, values, draft_over_budget=draft_over_budget,
                              checklist_labels=checklist_labels, inspect=inspect_edited,
                              cell_fills=m.get('cell_fills'))
    # A cache failure must never hide an inspection result or bypass a guard.
    if (not issues and detail and
            not any('검사 실행 실패' in f['message'] for group in detail['groups'].values() for f in group)):
        try:
            h.write_json(cache, dict(input_sha256=digest, editor_ok=True,
                                    detail_sha256=h.json_hash(detail), detail=detail))
        except OSError:
            pass
    return issues, detail


def inspect_copy(path, folder, m, template, extracted, values, aliases):
    return _inspect_copy(path, folder, m, template, extracted, values, aliases)


def subject_code_findings(m, extracted, values, aliases):
    """Compare only teacher-confirmed subjects/codes against the unchanged base."""
    from hwpdoc_workspace import subject_code_map, checklist_code_columns
    mapping = subject_code_map(extracted)
    columns = checklist_code_columns(extracted, labeled=True)
    slots = {s['key']: s.get('text', s.get('preview', '')) for s in extracted['slots']}
    rows = defaultdict(list)
    for key in sorted(set(values) | set(m.get('kept_slots', []))):
        cell = aliases.get(key, key).split(':')
        if len(cell) == 4 and cell[0] == 'cell':
            text = ''.join(values.get(key, slots.get(key, '')).split())
            rows[tuple(cell[1:3])].append((key, cell[3], text))
    findings = []
    for (table, _), cells in rows.items():
        subjects = {text for _, col, text in cells if (table, col) not in columns and text in mapping}
        expected = {mapping[subject] for subject in subjects}
        if len(expected) != 1:
            continue
        code = next(iter(expected))
        for key, col, text in cells:
            if (table, col) in columns and text != code:
                findings.append(dict(slot=key, guard='subject_code', blocking=False,
                    subject='·'.join(sorted(subjects)), current=text, expected=code,
                    message=f'확정 과목 {"·".join(sorted(subjects))}의 코드 {text or "(비움)"}가 같은 문서 코드표 {code}와 다릅니다.',
                    how_to_fix=f'코드표 기준 값 `{code}`로 바꾸거나 의도라면 그대로 두세요.'))
    return findings


def _inspect_copy(path, folder, m, template, extracted, values, aliases):
    """Run the same CLI guards; group all findings by actual checklist address."""
    from page_guard import collect_text_budget_profile, compare_text_budget_profile
    # Only the disposable editor output is changed. Match the final pipeline's
    # namespace normalization before guards that read literal hp:t prefixes.
    code, output = h.run([h.SKILL / 'fix_namespaces.py', path])
    if code:
        return dict(groups={'document': [dict(slot='document', guard='namespaces', blocking=True,
                    message=f'내용 사전 검사 실행 실패: 네임스페이스 보정: {output[:300]}')]},
                    date_normalizations=[], final_content_policy=FINAL_CONTENT_POLICY,
                    temporary_copy_discarded=True)
    content_lines, gonmun_lines = _locations(path, m, aliases)
    findings = subject_code_findings(m, extracted, values, aliases)
    rules = dict(m['content_rules'])
    rules['forbid_regex'] = [*rules.get('forbid_regex', []), r'\[\[[^\]]+\]\]']
    h.write_json(folder / 'content.rules.json', rules)
    year = (h.CONTEXT.settings.get('school') or {}).get('academic_year') if h.CONTEXT else None
    commands = {
        'content': [h.SKILL / 'content_guard.py', path, '--rules', folder / 'content.rules.json', '--json'],
        'gonmun': [h.SKILL / 'gonmun_lint.py', '--hwpx', path, '--format', 'json']}
    if type(year) is int:
        commands['gonmun'] += ['--academic-year', str(year)]
    receipts = m.get('checklist', {}).get('residue_decisions', {})
    kept = set(m.get('kept_slots', []))
    reviewed = kept | set(values)
    for guard, command in commands.items():
        code, output = h.run(command)
        try:
            result = json.loads(output)
            raw = result['findings']
            if code not in (0, 1) or not isinstance(raw, list):
                raise ValueError(f'검사 종료 코드 {code}')
        except (ValueError, KeyError, TypeError) as exc:
            findings.append(dict(slot='document', guard=guard, blocking=True,
                                 message=f'내용 사전 검사 실행 실패: {exc}: {output[:300]}'))
            continue
        for item in raw:
            line = item.get('line', 0)
            locations = ['document']
            if guard == 'gonmun' and 0 < line <= len(gonmun_lines):
                locations = [gonmun_lines[line - 1]]
            elif guard == 'content' and 0 < line <= len(content_lines):
                chunks = content_lines[line - 1]
                pattern = item.get('pattern', '')
                is_regex = item.get('kind') in ('forbidden-regex', 'placeholder')
                locations = [key for key, text in chunks.items()
                             if (re.search(pattern, text) if is_regex else pattern in text)] or list(chunks)
            for key in locations:
                residue = guard == 'content' and (item.get('kind') == 'forbidden' or
                           item.get('kind') == 'forbidden-regex' and item.get('pattern') in m['content_rules'].get('forbid_regex', []))
                # Only what would mislead blocks approval: a wrong weekday, a
                # placeholder, or residue in text nobody reviewed. Notation style
                # and residue in a row the teacher answered (유지 or a typed value,
                # e.g. an attendee who also came last year) are notes for the same
                # approval request; validate still checks both. On 11. 4. blocking
                # them stopped replays before any draft.
                if guard == 'gonmun':
                    blocking = item.get('rule') == 'DATE_WEEKDAY' and item.get('severity') == 'error'
                else:
                    blocking = not (residue and key in reviewed)
                receipt = receipts.get(key, {})
                acknowledged = bool(residue and key in kept and receipt
                                    and receipt.get('rules_sha256') == h.json_hash(m['content_rules']))
                findings.append(dict(slot=key, guard=guard, blocking=blocking and not acknowledged,
                                     residue_conflict=residue and key in kept,
                                     acknowledged=acknowledged, finding=item,
                                     message=(FINAL_CONTENT_POLICY if acknowledged else
                                              item.get('message') or f"{item['kind']}: {item['pattern']}")))
    # Same non-whitespace budget calculation as final page_guard. Do not write
    # a new baseline profile: neither the original nor its fingerprint changes.
    base_profile = collect_text_budget_profile(template)
    output_profile = collect_text_budget_profile(path)
    budgets = compare_text_budget_profile(base_profile, output_profile, strict_paragraphs=False)
    selected = set(values) | kept
    for message in budgets:
        match = re.match(r'(p:\d+|cell:\d+:\d+:\d+:\d+) ', message)
        key = match[1] if match else 'document'
        if key.startswith('cell:') and key.endswith(':0'):
            key = key[:-2]
        labels = [p for p, cell in aliases.items() if cell == key and p in selected]
        locations = labels or [key]
        for location in locations:
            declared = location in m.get('over_budget_cells', []) or key in m.get('over_budget_cells', [])
            findings.append(dict(slot=location, guard='budget', blocking=not declared,
                                 message=message, after_build_render_review=declared))
    slots = {s['key']: s for s in extracted['slots']}
    proposals = []
    for key in sorted(selected):
        text = values.get(key, slots.get(key, {}).get('preview', ''))
        normalized = normalize_dates(text)
        if normalized == text:
            continue
        limit = slots.get(key, {}).get('max_chars', 0)
        if not limit and key.startswith('cell:'):
            limit = next((s['max_chars'] for s in base_profile['slots'] if s['key'] == key + ':0'), 0)
        size = len(''.join(normalized.split()))
        proposals.append(dict(slot=key, current=text, proposed=normalized, max_chars=limit,
                              proposed_chars=size, over_budget=bool(limit and size > limit),
                              added_spaces=normalized.count(' ') - text.count(' '),
                              budget_unit='non_whitespace_characters',
                              apply_value=NORMALIZE_PREFIX + text))
    grouped = defaultdict(list)
    # Ancestor content lines can repeat the same finding. Retain guard output
    # in each finding but report one issue per slot/rule/match.
    seen = set()
    for item in findings:
        raw = item.get('finding', {})
        signature = (item['slot'], item['guard'], raw.get('rule') or raw.get('kind'),
                     raw.get('match') or raw.get('pattern'), item['message'])
        if signature not in seen:
            grouped[item['slot']].append(item)
            seen.add(signature)
    return dict(groups=dict(grouped), date_normalizations=proposals,
                final_content_policy=FINAL_CONTENT_POLICY, temporary_copy_discarded=True)


def issues_for(detail):
    issues = []
    for key, findings in detail.get('groups', {}).items():
        blocked = any(f['blocking'] for f in findings)
        messages = list(dict.fromkeys(f['message'] for f in findings))
        message = '; '.join(m[:200] for m in messages[:3])
        if len(messages) > 3:
            message += f'; 외 {len(messages) - 3}건(상세 파일)'
        fixes = ['내용 검사 상세 파일의 같은 슬롯을 확인표에서 함께 처리한 뒤 --apply하세요.']
        if any(f['guard'] == 'gonmun' for f in findings):
            fixes.append(f'날짜 표기는 `{NORMALIZE_PREFIX}<확정 원문>` 또는 --apply --normalize-dates로 정리하고, 다른 표기 오류는 검사 제안대로 고치세요.')
        if any(f.get('residue_conflict') for f in findings):
            fixes.append(f'잔재 유지는 `{KEEP_RESIDUE}`로 명시하세요. ' + FINAL_CONTENT_POLICY)
        if any(f['guard'] == 'budget' for f in findings):
            fixes.append('뜻을 보존한 짧은 문구로 바꾸거나, 교사가 문구 유지를 택하면 over_budget_cells에 넣고 생성 후 렌더·육안 확인을 진행하세요.')
        fixes.extend(dict.fromkeys(f['how_to_fix'] for f in findings if f['guard'] == 'subject_code'))
        issue = h.preflight_issue('content_check.' + key,
                    key + ': ' + message, ' '.join(fixes))
        issue.update(content_check=True, slot=key, blocking=blocked,
                     phase=('before_approval' if blocked else 'after_build_render_review'
                            if any(f.get('after_build_render_review') for f in findings) else 'review_note'))
        issues.append(issue)
    return issues


def summary(detail):
    findings = [f for group in detail.get('groups', {}).values() for f in group]
    return dict(slot_count=len(detail.get('groups', {})), finding_count=len(findings),
                blocking_count=sum(f['blocking'] for f in findings),
                note_count=sum(not f['blocking'] for f in findings),
                date_normalization_count=len(detail.get('date_normalizations', [])))
