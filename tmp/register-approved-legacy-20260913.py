"""Record the user's explicit five-template registration approval."""
import copy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import hwpdoc as h
import hwpdoc_templates as templates

h.configure(ROOT)
names = ['가정통신문', '가정통신문-회신형', '가정통신문-고사안내', '성립전예산요구', '회의록-교과협의회']
at = h.now()
prepared = []
for name in names:
    folder = templates.folder_for(name, 'legacy-1')
    r = h.read_json(folder / 'registration.json')
    assert r['status'] == 'awaiting_review', (name, r['status'])
    assert r['hashes'] == templates.file_hashes(folder), name
    assert all(s['status'] == 'pass' for s in r['stages'].values()), name
    review = copy.deepcopy(h.read_json(folder / 'review.draft.json'))
    assert review['hashes'] == r['hashes'], name
    review.update(confirmed=True, by='사용자 (현재 대화)', at=at,
                  record='현재 대화 사용자 원문: "기존양식 5종 승인". docs/기존5종-등록검토자료-2026-09-13.md에 제시된 기존 5종의 양식·매핑·지원 용도 등록 승인. 공문 생성·발송 또는 재배포 라이선스 승인이 아님.',
                  approval_source={'kind': 'user_message', 'text': '기존양식 5종 승인', 'recorded_at': at})
    review['visual']['record'] = ('docs/기존5종-등록검토자료-2026-09-13.md의 에이전트 실제 PNG 판독 및 원본/등록 사본 비교 기록에 근거. '
                                 '현재 PDF/PNG와 문서 해시 재대조 완료. 사용자 원문 "기존양식 5종 승인"으로 등록 승인 수리. '
                                 '사용자의 개별 이미지 열람 행위를 별도로 추정하지 않음.')
    errors = templates.review_errors(r, review)
    assert not errors, (name, errors)
    target = folder / 'review.user-approval-20260913.json'
    assert not target.exists() and not (folder / 'review.json').exists(), name
    prepared.append((name, folder, target, review))

for name, folder, target, review in prepared:
    with target.open('x', encoding='utf-8') as stream:
        json.dump(review, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/hwpdoc.py'),
                             '--workspace', str(ROOT), 'add-template', '--id', name,
                             '--version', 'legacy-1', '--review', str(target)],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    r, issues = templates.inspect_registration(folder)
    assert r['status'] == 'registered' and not issues, (name, issues)
    templates.resolve_template({'id': name, 'version': 'legacy-1', 'sha256': r['hashes']['template.hwpx']})
    print(json.dumps({'id': name, 'status': r['status'], 'issues': issues}, ensure_ascii=False))

report = ROOT / 'docs/기존5종-등록승인-2026-09-13.md'
with report.open('x', encoding='utf-8') as stream:
    stream.write('# 기존 양식 5종 등록 승인\n\n')
    stream.write(f'승인 기록 시각: {at}\n\n사용자 원문: **기존양식 5종 승인**\n\n')
    stream.write('[기존 검토 자료](기존5종-등록검토자료-2026-09-13.md)에 제시한 양식·매핑·지원 용도를 현재 해시에 연결해 등록했다.\n\n')
    for name in names:
        stream.write(f'- {name}: `legacy-1`, `registered`\n')
    stream.write('\n5종 모두 원본·양식·슬롯·매핑·프로파일과 PDF/PNG 해시가 검토 자료와 일치했고, 기존 검증 8단계 통과 및 등록 후 무결성·양식 선택 검사를 확인했다.\n\n')
    stream.write('각 `.hwpdoc/templates/<양식>/legacy-1/`의 `review.user-approval-20260913.json`과 `review.json`에 사용자 원문과 승인 범위를 보존했다. 미승인 초안은 그대로 보존했다.\n\n')
    stream.write('이번 승인은 양식 등록에 한정한다. 문서별 초안 승인·최종 검토·발송, 재배포 권리, 교사 시범 시험을 승인 또는 통과로 바꾸지 않는다. 기존 Evals 동결 장부는 유지하며 후속 평가에서 승인 조건 해소를 확인해야 한다.\n')
h.audit('template_registration_approval', report, 'pass', {'user_message': '기존양식 5종 승인', 'templates': names, 'version': 'legacy-1'})
print(str(report))
