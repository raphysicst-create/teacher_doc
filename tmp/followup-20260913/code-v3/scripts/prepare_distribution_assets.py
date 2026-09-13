"""Prepare redacted release candidates without modifying operational templates."""
import hashlib
import json
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.claude/skills/hwpx/templates'
DESTINATION = ROOT / 'distribution/assets/templates'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata_candidate(data):
    root = etree.fromstring(data)
    keys = {'creator', 'lastsaveby', 'CreatedDate', 'ModifiedDate', 'date'}
    for element in root.iter('{http://www.idpf.org/2007/opf/}meta'):
        if element.get('name') in keys:
            element.text = None
    return etree.tostring(root, encoding='utf-8', xml_declaration=True)


def proposal_candidate(data):
    root = etree.fromstring(data)
    headings = {'Ⅰ', '사업 개요', '1', '사업명', '2', '추진 배경', '3', '추진 근거', '- 1 -'}
    prefixes = {'○ 사업명:': '  ○ 사업명: {{사업명}}', '○ 사업기간:': '  ○ 사업기간: {{사업기간}}',
                '- 1차:': '    - {{단계별 사업기간}}', '○ 소요예산:': '  ○ 소요예산: {{소요예산}}',
                '○ 계약방법:': '  ○ 계약방법: {{계약방법}}'}
    section = None; counts = {'추진 배경': 0, '추진 근거': 0, '사업값': 0}
    for element in root.iter('{http://www.hancom.co.kr/hwpml/2011/paragraph}t'):
        text = (element.text or '').strip()
        if not text:
            continue
        if text in headings:
            if text in ('추진 배경', '추진 근거'):
                section = text
            continue
        if section and text.startswith('○'):
            counts[section] += 1
            element.text = '  ○ {{' + section + ' ' + str(counts[section]) + '}}'
            continue
        for prefix, replacement in prefixes.items():
            if text.startswith(prefix):
                element.text = replacement; counts['사업값'] += 1
                break
        else:
            raise ValueError('새 원문 항목은 자동 추정하지 않습니다: ' + text)
    if counts != {'추진 배경': 4, '추진 근거': 7, '사업값': 5}:
        raise ValueError('기본 제안서 구조가 달라져 재검토가 필요합니다')
    return etree.tostring(root, encoding='utf-8', xml_declaration=True)


def prepare():
    report = {'status': 'candidates_prepared', 'redistribution_permission': 'unconfirmed', 'files': []}
    for relative, transform in [('base/Contents/content.hpf', metadata_candidate), ('proposal/section0.xml', proposal_candidate)]:
        source = SOURCE / relative; target = DESTINATION / relative
        original = source.read_bytes(); candidate = transform(original)
        if target.exists() and target.read_bytes() != candidate:
            raise ValueError('기존 배포 후보가 달라졌습니다. 검토 기록을 보존하고 새 후보 경로를 사용하세요: ' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(candidate)
        report['files'].append({'source': source.relative_to(ROOT).as_posix(), 'source_sha256': digest(original),
                                'candidate': target.relative_to(ROOT).as_posix(), 'candidate_sha256': digest(candidate)})
    record = ROOT / 'distribution/assets/preparation.json'
    content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if record.exists() and record.read_text(encoding='utf-8') != content:
        raise ValueError('기존 자산 준비 기록을 덮어쓰지 않습니다')
    if not record.exists():
        record.write_text(content, encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))
