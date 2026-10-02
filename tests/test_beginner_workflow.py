"""Offline safety regressions for the first real document and the next session."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'skills/hwpx/scripts'))
import hwpdoc as h
from hwpdoc_config import load_context
from hwpdoc_workspace import instruction_text
import hwpx_slots
import edit_hwpx as edit
from lxml import etree

HP = edit.NS['hp']
HS = edit.NS['hs']


def paragraph(text):
    return '<hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0"><hp:t>' + text + '</hp:t></hp:run></hp:p>'


def container(body):
    return '<hp:p paraPrIDRef="0" styleIDRef="0"><hp:run charPrIDRef="0">' + body + '</hp:run></hp:p>'


def table(body):
    return ('<hp:tbl rowCnt="1" colCnt="1"><hp:tr><hp:tc><hp:cellAddr rowAddr="0" colAddr="0"/>'
            '<hp:cellSz width="30000" height="2400"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>'
            '<hp:subList>' + body + '</hp:subList></hp:tc></hp:tr></hp:tbl>')


def section(body):
    return f'<hs:sec xmlns:hs="{HS}" xmlns:hp="{HP}">{body}</hs:sec>'.encode()


def package(path, xml):
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('mimetype', 'application/hwp+zip')
        archive.writestr('Contents/section0.xml', xml)
        archive.writestr('Preview/PrvText.txt', 'untouched preview')
    return path


class TextSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.xml = section(container(table(paragraph('바깥 제목') + container(table(paragraph('내부 안내'))))))
        self.source = package(self.root / 'source.hwpx', self.xml)

    def tearDown(self):
        self.temp.cleanup()

    def test_nested_parent_not_editable_and_child_not_duplicated(self):
        profile = hwpx_slots.collect_slots(self.source)
        cells = [s['key'] for s in profile['slots'] if s['kind'] == 'cell']
        self.assertEqual(cells, ['cell:1:0:0'])
        self.assertEqual(profile['blocked_slots'][0]['key'], 'cell:0:0:0')

    def test_nested_whole_cell_rejected_without_mutation(self):
        root = etree.fromstring(self.xml)
        before = etree.tostring(root)
        with self.assertRaisesRegex(SystemExit, '복합 셀'):
            edit.set_cells(root, [edit.CellTarget(0, 0, 0, '새 제목')])
        self.assertEqual(etree.tostring(root), before)

    def test_title_and_inner_cell_edits_preserve_unselected_text(self):
        root = etree.fromstring(self.xml)
        nested = root.xpath('.//hp:tbl', namespaces=edit.NS)[1]
        before = etree.tostring(nested)
        edit.set_paragraphs(root, [edit.ParagraphTarget(1, '새 제목')], {})
        self.assertEqual(etree.tostring(nested), before)
        edit.set_cells(root, [edit.CellTarget(1, 0, 0, '새 안내')])
        self.assertEqual(root.xpath('.//hp:t/text()', namespaces=edit.NS), ['새 제목', '새 안내'])

    def test_split_run_replace_does_not_rewrite_container(self):
        xml = self.xml.replace('내부 안내'.encode(), '내부</hp:t></hp:run><hp:run charPrIDRef="0"><hp:t> 안내'.encode())
        root = etree.fromstring(xml)
        edit.replace_text(root, {'내부 안내': '새 안내'}, {})
        texts = root.xpath('.//hp:t/text()', namespaces=edit.NS)
        self.assertEqual([t for t in texts if t], ['바깥 제목', '새 안내'])
        self.assertEqual(root.xpath('string(.//hp:tbl[1]/hp:tr/hp:tc/hp:subList/hp:p[1]/hp:run/hp:t)', namespaces=edit.NS), '바깥 제목')

    def test_source_output_alias_rejected(self):
        before = self.source.read_bytes()
        with self.assertRaisesRegex(SystemExit, '원본'):
            edit._pack_from_original(self.source, self.source, {}, [], [edit.ParagraphTarget(1, '새 제목')])
        self.assertEqual(self.source.read_bytes(), before)

    def test_plain_cell_still_editable(self):
        root = etree.fromstring(section(container(table(paragraph('원래 문구')))))
        self.assertEqual(edit.set_cells(root, [edit.CellTarget(0, 0, 0, '새 문구')]), 1)
        self.assertEqual(root.xpath('.//hp:t/text()', namespaces=edit.NS), ['새 문구'])

    def test_mixed_container_split_replace_fails_explicitly(self):
        mixed = ('<hp:p><hp:run><hp:t>혼합</hp:t></hp:run><hp:run><hp:t> 문단 앞말</hp:t>'
                 + table(paragraph('내부 유지')) + '</hp:run></hp:p>')
        root = etree.fromstring(section(mixed))
        with self.assertRaisesRegex(SystemExit, '컨테이너'):
            edit.replace_text(root, {'혼합 문단 앞말': '새 제목'}, {})

    def test_complex_cell_is_blocked_even_with_budget_override(self):
        with self.assertRaisesRegex(SystemExit, '복합 셀'):
            edit.preflight_text_budget(self.source, {}, [edit.CellTarget(0, 0, 0, '새 제목')], [], 24,
                                       allow_over_budget=True, render_verified=True)

    def test_second_section_and_nonsection_entries_are_unchanged(self):
        with zipfile.ZipFile(self.source, 'a') as archive:
            archive.writestr('Contents/section1.xml', section(paragraph('두 번째 섹션 보존')))
        profile = hwpx_slots.collect_slots(self.source)
        self.assertEqual(profile['edit_scope']['section_count'], 2)
        self.assertTrue(profile['warnings'])
        target = self.root / 'result.hwpx'
        edit._pack_from_original(self.source, target, {}, [], [edit.ParagraphTarget(1, '새 제목')])
        with zipfile.ZipFile(self.source) as old, zipfile.ZipFile(target) as new:
            for name in old.namelist():
                if name != 'Contents/section0.xml':
                    self.assertEqual(old.read(name), new.read(name))



class SessionPaths(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / '교사 작업'
        self.data = self.root / '별도 PC 데이터'
        (self.work / '.hwpdoc').mkdir(parents=True)
        self.data.mkdir()
        h.write_json(self.work / '.hwpdoc/workspace.json', {'kind': 'hwpdoc-workspace', 'version': 1})
        h.write_json(self.data / 'runtime.json', {'version': 1, 'python': sys.executable})
        h.write_json(self.work / '.hwpdoc/onboarding.json', {'pc_data': str(self.data), 'python': sys.executable,
                                                         'workspace': str(self.work), 'status': 'ready_xml'})
        self.env = patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in ('HWPDOC_PC_DATA', 'HWPDOC_WORKSPACE')}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_receipt_recovers_custom_paths_without_environment(self):
        context = load_context(self.work)
        self.assertEqual(context.pc_data, self.data)
        self.assertEqual(context.python, Path(sys.executable))

    def test_missing_recorded_runtime_fails_closed(self):
        (self.data / 'runtime.json').unlink()
        with self.assertRaisesRegex(ValueError, 'runtime.json'):
            load_context(self.work)

    def test_recorded_python_mismatch_fails_closed(self):
        h.write_json(self.work / '.hwpdoc/onboarding.json', {'pc_data': str(self.data), 'python': str(self.root / 'missing'), 'workspace': str(self.work)})
        with self.assertRaisesRegex(ValueError, 'Python|python'):
            load_context(self.work)

    def test_instructions_point_to_receipt_not_default_path(self):
        text = instruction_text('codex', 'hwpx')
        self.assertIn('.hwpdoc/onboarding.json', text)
        self.assertNotIn('%LOCALAPPDATA%', text)

    def test_bad_explicit_override_does_not_fall_back(self):
        with self.assertRaisesRegex(ValueError, 'runtime.json'):
            load_context(self.work, pc_data=self.root / 'missing')

    def test_moved_workspace_on_same_pc_keeps_runtime(self):
        moved = self.root / '옮긴 작업'
        self.work.rename(moved)
        self.assertEqual(load_context(moved).pc_data, self.data)



class EmptyReuseReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.patch = patch.object(h, 'ROOT', self.root)
        self.patch.start()
        (self.root / 'draft.txt').write_text('검토용 초안', encoding='utf-8')
        (self.root / 'source.txt').write_text('빈 양식', encoding='utf-8')
        h.write_json(self.root / 'evidence.json', {'status': 'unsupported', 'steps': [], 'conditions': [], 'exceptions': [],
                      'pending_items': [], 'reviewed_at': '2026-10-01T00:00:00+00:00', 'freshness': 'verified', 'fallback_sources': ['source.txt']})
        self.m = {'version': 1, 'job_id': 'blank', 'workflow': 'W1', 'document_type': '메모', 'shared_values': {},
                  'sources': [{'path': 'source.txt'}], 'attachments': [], 'evidence': {'record': 'evidence.json'},
                  'draft': {'path': 'draft.txt', 'sha256': h.sha(self.root / 'draft.txt'), 'created_at': '2026-10-01T00:01:00+00:00'},
                  'draft_approval': {'confirmed': True, 'by': 'fixture', 'at': '2026-10-01T00:02:00+00:00', 'record': 'synthetic test only'},
                  'content_rules': {'forbid': []}, 'checks': {k: {'applicable': False, 'reason': '무관한 문서'} for k in ('budget_names', 'related', 'timetable')},
                  'environment': {}, 'unresolved': [], 'exploration': {'record': '빈 양식 확인'}, 'reference': 'source.txt',
                  'reuse_review': {'record': '원문을 확인한 합성 fixture', 'names': [], 'dates': [],
                                   'names_empty_reason': '이름 없는 빈 양식', 'dates_empty_reason': '날짜 없는 빈 양식'}}

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def errors(self):
        self.m['draft_approval']['input_sha256'] = h.json_hash(h.approval_payload(self.m))
        return h.prerequisite_errors(self.m)

    def test_reviewed_blank_allows_empty_forbid(self):
        self.assertEqual(self.errors(), [])

    def test_missing_reason_or_record_still_blocked(self):
        del self.m['reuse_review']['names_empty_reason']
        self.assertTrue(self.errors())
        self.m['reuse_review']['names_empty_reason'] = '   '
        self.assertTrue(self.errors())

    def test_found_name_must_still_be_forbidden(self):
        self.m['reuse_review']['names'] = ['이전 담당자']
        self.assertTrue(any('모두' in x for x in self.errors()))
        self.m['content_rules']['forbid'] = ['이전 담당자']
        self.assertEqual(self.errors(), [])


class RetrySafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / 'work.hwpx'
        self.work.write_bytes(b'bad fixture')
        self.folder = self.root / 'job'
        self.folder.mkdir()
        self.patches = [patch.object(h, 'ROOT', self.root), patch.object(h, 'audit'), patch.object(h, 'save_report')]
        for item in self.patches:
            item.start()
        self.report = {'work_file': str(self.work), 'stages': {}, 'history': [], 'validated_sha256': 'stale'}
        with patch.object(h, 'run', return_value=(1, '[warn] preserve this warning')) as run:
            h.stage(self.report, 'content', ['fixture.py'])
            h.stage(self.report, 'content', ['fixture.py'])
            h.stage(self.report, 'content', ['fixture.py'])
            self.assertEqual(run.call_count, 2)
        self.evidence = self.root / 'repair.txt'
        self.evidence.write_text('synthetic repair evidence, not a real approval')

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def proof(self):
        receipt = {'confirmed': True, 'by': 'fixture only', 'at': h.now(), 'record': 'synthetic test confirmation',
                   'cause': 'fixture leftover', 'resolution': 'removed from work copy', 'stage': 'content',
                   'stage_sha256': h.stage_challenge(self.report['stages']['content']), 'document_sha256': h.sha(self.work),
                   'input_sha256': 'unchanged-approval', 'evidence': [{'path': 'repair.txt', 'sha256': h.sha(self.evidence)}]}
        h.write_json(self.root / 'resume.json', receipt)
        return receipt

    def test_unchanged_conditions_cannot_be_reset_by_new_explanation(self):
        self.proof()
        with self.assertRaisesRegex(ValueError, '실패 조건'):
            h.resume_stage(self.report, 'content', 'resume.json', self.work, 'unchanged-approval', self.folder)
        self.assertEqual(self.report['stages']['content']['failures'], 2)

    def test_repaired_copy_requires_evidence_then_actually_reruns(self):
        self.work.write_bytes(b'repaired fixture')
        receipt = self.proof()
        receipt['evidence'] = []
        h.write_json(self.root / 'resume.json', receipt)
        with self.assertRaisesRegex(ValueError, '증거'):
            h.resume_stage(self.report, 'content', 'resume.json', self.work, 'unchanged-approval', self.folder)
        self.proof()
        h.resume_stage(self.report, 'content', 'resume.json', self.work, 'unchanged-approval', self.folder)
        self.assertEqual(self.report['stages']['content']['failures'], 2)
        self.assertEqual(self.report['stages']['content']['status'], 'unconfirmed')
        self.assertNotIn('validated_sha256', self.report)
        self.assertTrue(list((self.folder / 'resumes').glob('*/confirmation.json')))
        with patch.object(h, 'run', return_value=(0, 'pass')) as run:
            h.stage(self.report, 'content', ['fixture.py'])
            self.assertEqual(run.call_count, 1)
        self.assertEqual(self.report['stages']['content']['status'], 'pass')
        self.assertEqual(self.report['stages']['content']['failures'], 2)
        self.assertGreaterEqual(len(self.report['history']), 5)

    def test_changed_approval_or_evidence_rejects_resume(self):
        self.work.write_bytes(b'repaired fixture')
        self.proof()
        with self.assertRaisesRegex(ValueError, '해시 불일치'):
            h.resume_stage(self.report, 'content', 'resume.json', self.work, 'changed-approval', self.folder)
        self.evidence.write_text('changed')
        with self.assertRaisesRegex(ValueError, '증거'):
            h.resume_stage(self.report, 'content', 'resume.json', self.work, 'unchanged-approval', self.folder)

    def test_warn_brackets_are_collected(self):
        warnings = self.report['history'][0]['warnings']
        self.assertIn('[warn] preserve this warning', warnings)



if __name__ == '__main__':
    unittest.main()
