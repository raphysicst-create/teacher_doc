"""Real editor/validator/COM smoke on copies of five templates.

This tests software plumbing using synthetic manifest/approval records. It does
not count toward the 36 model + human-review acceptance runs and never delivers.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import hwpdoc as h
sys.path.insert(0, str(h.SKILL))
from hwpx_slots import collect_slots
from text_extract import extract_plain
import re


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    folder = ROOT / '.claude/scratchpad/gpt-migration' / ('smoke-' + stamp)
    folder.mkdir(parents=True)
    draft = folder / 'software-test.md'
    draft.write_text('소프트웨어 연결 시험. 실무 공문·사람 승인·36회 모델 인수가 아닙니다. 원본 값을 보존하고 제목 슬롯만 같은 길이의 시험 문자열로 교체합니다.', encoding='utf-8')
    evidence = folder / 'synthetic-evidence.json'
    h.write_json(evidence, dict(status='ok', steps=['find_tasks', 'get_task_guide', 'search_task_evidence', 'read_evidence'],
                   conditions=[], exceptions=[], pending_items=[], reviewed_at='2026-09-10T01:00:00+00:00', freshness='verified',
                   fixture_only=True))
    summaries = []
    for index, name in enumerate(h.TEMPLATES):
        template = ROOT / 'knowledge/templates' / name / '양식.hwpx'
        slots = collect_slots(template)
        # Extracted address only; preserve original values and change one short label.
        chosen = next(s for s in slots['slots'] if s['kind'] == 'paragraph' and s['max_chars'] >= 4)
        before = h.sha(template)
        m = dict(job_id=f'smoke-{stamp}-{index}', workflow='W1', document_type='software-smoke', template=name,
                 shared_values={'test_label': '연결 시험'}, slots={'template_sha256': before, 'values': {chosen['key']: {'shared': 'test_label'}}},
                 sources=[{'path': str(template)}], evidence={'record': str(evidence)}, attachments=[], attachment_mentions=[],
                 draft={'path': str(draft), 'sha256': h.sha(draft), 'created_at': '2026-09-10T02:00:00+00:00'},
                 content_rules={'forbid': ['SYNTHETIC_TOKEN_MUST_NOT_APPEAR']},
                 checks={x: {'applicable': False, 'reason': 'software smoke only'} for x in ('budget_names', 'related', 'timetable')},
                 environment={'app': 'software-smoke', 'model': 'none', 'hancom': 'real COM'}, unresolved=[],
                 exploration={'record': 'software fixture from existing template'}, reuse_review={'record': 'preserve original prose for plumbing test',
                 'names': ['SYNTHETIC_TOKEN_MUST_NOT_APPEAR'], 'dates': [], 'dates_empty_reason': 'preserve original text; software fixture only'}, base_provenance='native')
        m['draft_approval'] = dict(confirmed=True, by='SYNTHETIC_TEST_NOT_USER', at='2026-09-10T03:00:00+00:00',
                                    record='software fixture only', input_sha256=h.json_hash(h.approval_payload(m)))
        # Keep the original attachment mention and provide a visibly synthetic
        # text attachment. Never pretend the referenced real attachment exists.
        visible = extract_plain(template, include_tables=True)
        match = re.search(r'^붙임\s+(.+?)\s+1부', visible, re.M)
        if match:
            attachment = folder / f'{index}-synthetic-attachment.txt'
            attachment.write_text('SOFTWARE FIXTURE ONLY. Not the real referenced attachment.', encoding='utf-8')
            m['attachments'] = [{'path': str(attachment), 'title': match.group(1)}]
            m['attachment_mentions'] = [match.group(1)]
            m['draft_approval']['input_sha256'] = h.json_hash(h.approval_payload(m))
        manifest = folder / f'{index}.json'; h.write_json(manifest, m)
        report = h.build_document(manifest)
        if report['stages']['build']['status'] == 'pass':
            report = h.validate_document(report)
        entry = dict(template=name, report=str(h.job_dir(m['job_id']) / 'report.json'),
                     status=h.result_state(report), stages={k: v['status'] for k, v in report['stages'].items()},
                     original_unchanged=before == h.sha(template), acceptance_run=False)
        summaries.append(entry)
        h.write_json(folder / 'summary.json', summaries)
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    return 0 if all(x['original_unchanged'] and x['stages'].get('hancom') == 'pass' for x in summaries) else 1


if __name__ == '__main__':
    raise SystemExit(main())
