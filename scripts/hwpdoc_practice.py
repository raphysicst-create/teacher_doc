"""Non-sensitive, repeatable XML-only first document; never a real approval."""
from pathlib import Path
import copy
import tempfile
import zipfile

import hwpdoc as h


def first_doc():
    # Imports are intentionally deferred until after the runtime doctor.
    import sys
    sys.path.insert(0, str(h.SKILL))
    from lxml import etree
    from build_hwpx import build
    from hwpx_slots import collect_slots
    from validate import validate
    folder = h.workspace_path('output/teacher-doc-practice')
    receipt = folder / 'practice-report.json'
    if folder.exists():
        if not receipt.is_file():
            raise ValueError('기존 연습 폴더를 덮어쓰지 않습니다: ' + str(folder))
        result = h.read_json(receipt)
        if not isinstance(result, dict) or result.get('kind') != 'teacher-doc-practice-v1':
            raise ValueError('연습 소유 기록이 일치하지 않습니다')
        expected = {'template.hwpx', 'first-document.hwpx', 'slot-values.json'}
        if not isinstance(result.get('files'), dict) or set(result['files']) != expected:
            raise ValueError('연습 파일 기록이 불완전합니다')
        for name, digest in result['files'].items():
            path = folder / name
            if not path.is_file() or h.sha(path) != digest:
                raise ValueError('연습 파일이 변경됐습니다. 수정본은 보존하고 별도 작업 폴더에서 연습하세요: ' + name)
        for name in ('template.hwpx', 'first-document.hwpx'):
            errors = validate(str(folder / name))
            if errors:
                raise ValueError('; '.join(errors))
        return dict(result, reused=True, report=str(receipt))
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.teacher-doc-practice-', dir=folder.parent) as temporary:
        work = Path(temporary)
        base = h.SKILL.parent / 'templates/base/Contents/section0.xml'
        tree = etree.parse(str(base))
        root = tree.getroot()
        ns = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}
        first = copy.deepcopy(root.find('hp:p', ns))
        for item in list(root):
            root.remove(item)
        root.append(first)
        for item in root.xpath('.//hp:linesegarray', namespaces=ns):
            item.getparent().remove(item)
        phrases = [
            '설치 확인 연습 양식 — 실제 발송이나 제출에 사용하지 않습니다',
            '연습 제목 입력 자리: 실제 학교나 학생 정보 없이 작성합니다',
            '연습 본문 입력 자리: 이 문서는 프로그램 동작 확인만을 위한 합성 자료입니다',
            '한글 열기와 화면 검토는 별도로 필요합니다. 이 파일은 승인된 공문이 아닙니다',
        ]
        for index, phrase in enumerate(phrases, 2):
            p = etree.SubElement(root, '{%s}p' % ns['hp'], id=str(2000000000 + index),
                                 paraPrIDRef='0', styleIDRef='0', pageBreak='0', columnBreak='0', merged='0')
            run = etree.SubElement(p, '{%s}run' % ns['hp'], charPrIDRef='0')
            etree.SubElement(run, '{%s}t' % ns['hp']).text = phrase
        section = work / 'practice-section.xml'
        tree.write(str(section), encoding='UTF-8', xml_declaration=True)
        template = work / 'template.hwpx'
        # The existing builder owns the package/layout; only synthetic section text changes.
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            build(None, None, section, 'teacher_doc 설치 확인 연습', 'teacher_doc practice', template)
        slots = collect_slots(template)['slots']
        values = {slot['key']: ('첫 문서 생성 연습' if '연습 제목 입력' in slot['preview'] else
                               '개인정보 없는 연습 문서가 생성되었습니다')
                  for slot in slots if '연습 제목 입력' in slot['preview'] or '연습 본문 입력' in slot['preview']}
        if len(values) != 2:
            raise ValueError('연습 양식 슬롯을 확인하지 못했습니다')
        h.write_json(work / 'slot-values.json', values)
        target = work / 'first-document.hwpx'
        code, output = h.run([h.SKILL / 'edit_hwpx.py', template, '-o', target,
                              '--slot-json', work / 'slot-values.json'])
        if code:
            raise ValueError('연습 슬롯 편집 실패: ' + output)
        for path in (template, target):
            errors = validate(str(path))
            if errors:
                raise ValueError('; '.join(errors))
        with zipfile.ZipFile(target) as archive:
            section_text = ''.join(etree.fromstring(archive.read('Contents/section0.xml')).xpath('.//hp:t//text()', namespaces=ns))
        if not all(value in section_text for value in values.values()):
            raise ValueError('연습 문서 내용 교체 검사 실패')
        section.unlink()
        result = {'kind': 'teacher-doc-practice-v1', 'status': 'xml_pass',
                  'at': h.now(), 'files': {p.name: h.sha(p) for p in (template, target, work / 'slot-values.json')},
                  'checks': {'package_xml': 'pass', 'slot_edit': 'pass', 'content': 'pass',
                             'hancom_open': 'not_run', 'pdf_render': 'not_run', 'visual_review': 'not_run'},
                  'template_registration': 'practice_only_not_registered', 'human_approval': False, 'sent': False,
                  'note': '비민감 합성 연습 자료입니다. 구조 검사 통과는 한글 열기·레이아웃·실제 공문 승인이 아닙니다.'}
        h.write_json(work / 'practice-report.json', result)
        # No replacing existing output. The temporary directory is cleaned on failures.
        work.rename(folder)
    return dict(result, reused=False, report=str(receipt))
