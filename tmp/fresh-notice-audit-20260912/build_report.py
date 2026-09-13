from pathlib import Path
from datetime import datetime
import base64, hashlib, html, json, shutil

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
CHILD = ROOT / 'tmp/fresh-notice-reproduction-20260912'
OUT = ROOT / 'output/fresh-notice-reproduction-20260912'
comparison = json.loads((WORK / 'comparison.json').read_text(encoding='utf-8'))
hashes = json.loads((CHILD / 'final-hashes.json').read_text(encoding='utf-8'))
candidate = Path(comparison['candidate'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(candidate) == comparison['candidate_sha256'] == hashes['sha256']
assert hashes['same_as_visual_preview']
before = json.loads((WORK / 'before.json').read_text(encoding='utf-8'))
assert all(sha(ROOT / p) == h for p, h in before['files'].items())
def image_data(p):
    return 'data:image/png;base64,' + base64.b64encode(p.read_bytes()).decode('ascii')
figures = ''.join(
    f'<figure><figcaption>{label}</figcaption><img alt="{label} 전체 1쪽" src="{image_data(p)}"></figure>'
    for label, p in [('기존 검토본', WORK / 'baseline-1.png'), ('새 세션 최종 결과', CHILD / 'final-1.png')]
)
facts = [
    ('시험 방식', '기존 대화 이력을 전달하지 않은 별도 에이전트. 기존 결과 파일·과거 세션·평가 정답은 비공개. 현재 지침·양식과 같은 업무의 확정 사실만 제공.'),
    ('시험 문서', '2026학년도 2학기 1회고사 실시 안내 가정통신문 본체 1건. 기존 검토 묶음 B6의 재작성 시험.'),
    ('최종 품질', '1쪽 유지. 제목 15pt, 표 3개의 행·열·병합·셀 크기·여백 동일. 출제범위·비율·문항 수 일치. 실제 한글 PDF에서 잘림·겹침 없음.'),
    ('문안 변화', '1학년 양일 정상수업을 인사말에 명시. 병합된 하교 안내에 대상인 2학년을 명시. 통신문번호 미부여 표시. 날짜를 현재 지침 형식으로 정리하고 소제목의 반복 표현만 축약.'),
    ('초안→생성', '초안부터 기존 표를 유지했다. 사용자 재작성 시험 요청을 생성 권한으로 해석한다는 부모 확인이 1회 있었으며, 새 사용자 승인 발언·평가 점수를 만들지 않았다.'),
    ('자가교정', '첫 렌더에서 일정·이의신청 소제목의 혼합 굵기 손실을 발견했다. 원래 런의 부분 치환으로 보정한 뒤 다시 판독했다. 임의 표 재설계·글자 크기 축소·2쪽 증가는 없었다.'),
    ('렌더 증거', '미검증 사본 PDF→PNG 판독 후 편집 예산 예외 플래그 적용. 최종 HWPX와 판독 사본 해시가 같다. 최종 파일 자체도 COM 열기 및 PDF 내보내기 통과.'),
    ('원본 보존', f'사전 해시를 보관한 원본·지침·양식·편집 스크립트 {len(before["files"])}개 모두 불변. 이번 부모 수정은 보호 훅 어댑터와 관련 회귀검사다.'),
]
rows = ''.join(f'<tr><th>{html.escape(a)}</th><td>{html.escape(b)}</td></tr>' for a,b in facts)
body = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>새 세션 재작성 — 독립 비교 결과</title><style>
body{{margin:0;background:#f5f6f7;color:#172327;font:16px/1.7 "Malgun Gothic",sans-serif}}main{{max-width:1240px;margin:auto;padding:28px}}h1{{font-size:28px;margin:0 0 12px}}h2{{font-size:20px;margin:30px 0 12px}}p{{margin:10px 0}}.lead{{font-size:20px;font-weight:700}}.panel{{background:white;padding:24px;border-radius:12px;margin:18px 0}}.warn{{border-left:5px solid #bc7513;background:#fff8e9}}.good{{color:#12624c}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}figure{{margin:0;background:white;border:1px solid #d8dfe0}}figcaption{{font-weight:700;padding:14px;border-bottom:1px solid #d8dfe0}}img{{width:100%;height:auto;display:block}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #d8dfe0;padding:13px}}th{{width:140px}}code{{overflow-wrap:anywhere;font-size:13px}}.muted{{font-size:14px;color:#536569}}@media(max-width:760px){{main{{padding:16px}}.pair{{grid-template-columns:1fr}}th{{width:90px}}.panel{{padding:16px}}}}@media print{{body{{background:white}}main{{padding:0}}.pair{{break-inside:avoid}}}}
</style><main><h1>새 세션 재작성 시험</h1><p class="muted">Hwp_doc · 2026. 9. 12. · 고사 안내문 1건</p>
<div class="panel"><p class="lead good">최종 문서의 배치와 내용은 의도대로 재현됐습니다.</p><p>다만 첫 독립 실행은 복사 명령의 보호 훅 오탐으로 생성 전에 중단됐습니다. 부모가 훅을 수정한 뒤 같은 세션에서 재개했습니다. 따라서 처음부터 무개입으로 통과한 시험은 아닙니다.</p></div>
<div class="pair">{figures}</div>
<section class="panel"><h2>독립 비교와 실제 작업 절차</h2><table>{rows}</table></section>
<section class="panel warn"><h2>완료 판정에서 남긴 예외</h2><p><b>page_guard는 FAIL을 유지합니다.</b> 배부일 <code>2026. 10. 14.</code>이 기존 문단 예산 10자보다 1자 길어 발생했습니다. 실제 1쪽 렌더에서 정상 수용됨을 확인했으며, 검사 실패를 없애려고 결과물로 기준을 재설정하지 않았습니다.</p><p>편집 시 날짜 관련 예산 경고 3건과 원래 본문 들여쓰기 경고도 보존했습니다. 문서번호 미부여는 입력 조건이며, 이의신청 방법은 미제공으로 남겼습니다. 전체 필수 검증 통과본으로 표시하지 않고 검토초안으로 전달합니다.</p></section>
<section class="panel"><h2>실제로 발견하고 고친 문제</h2><p>보호 훅이 복사의 읽기 원본과 쓰기 대상을 구분하지 않아 정상 템플릿 복사를 차단했습니다. 기존 파일을 읽어 현재 프로젝트 <code>tmp/output</code>의 새 파일로 복사하는 단일 명령만 허용하도록 수정했습니다. 원본 덮어쓰기·폴더 복사·작업 폴더 밖 목적지·복합 명령은 이 허용 경로에 포함하지 않습니다.</p><p>첫 수정은 단위검사 뒤에도 실제 호출이 막혔습니다. Windows Codex가 명령을 훅에 <code>Bash</code>로 전달하는 사실을 반영한 두 번째 수정 후 실제 복사가 성공했습니다. 보호 관련 회귀검사 27건이 통과했습니다. 이 결과는 모든 동적 셸 쓰기 보호 완료를 뜻하지 않습니다.</p><p>별도로 문서 작성 에이전트는 공문 검사 명령의 첫 호출에서 인수 문법 오류를 냈습니다. 최초 오류와 교정 실행 기록을 작업 보고에 남깁니다.</p></section>
<section class="panel"><h2>이 시험으로 확인한 범위</h2><p>기존 양식 탐색, 초안 구조 유지, 의미를 보존한 축약, 실제 렌더 후 예외 판단, 혼합 서식 자가교정은 이번 1건에서 작동했습니다. 평가계획서와 같은 다른 유형이나 반복 실행의 일관성까지 입증한 결과는 아닙니다.</p><p>남은 개선점은 날짜처럼 폭에 문제가 없는 고정값의 예산 실패와 실제 렌더 확인을 검증 기록에서 함께 해석할 수 있도록 하는 것입니다. 현재 시험에서는 실패를 지우지 않고 화면 정상 여부를 별도 근거로 남겼습니다.</p><p><b>발송 전 한글로 열어 확인해주세요.</b> 최종 사람 검토·평가·발송은 하지 않았습니다.</p></section>
<details class="panel"><summary>검증 자료와 파일 식별</summary><p>최종 파일: {html.escape(candidate.name)}</p><p><code>SHA256 {sha(candidate)}</code></p><p>원본 대조: <code>tmp/fresh-notice-audit-20260912/comparison.json</code><br>보호 훅 수정: <code>tmp/fresh-notice-audit-20260912/hook-fix-evidence.json</code><br>단계별 검증: <code>tmp/fresh-notice-reproduction-20260912/validation-results.json</code></p><p>최종 렌더: 1쪽, 앵커 발견 100%, 순서 정합 0.946. 부모가 내보낸 기존 결과: 1쪽, 앵커 발견 100%, 순서 정합 0.941. 이 수치는 사용자 품질 점수가 아닙니다.</p></details></main></html>'''
report = OUT / '새세션_재작성_독립비교보고.html'
if report.exists():
    raise SystemExit('Report exists; do not silently overwrite')
report.write_text(body, encoding='utf-8')
destdir = Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용')
assert destdir.is_dir()
dest = destdir / '20260912_새세션_재작성_독립비교보고.html'
if dest.exists():
    raise SystemExit('OneDrive report exists; do not overwrite')
shutil.copy2(report, dest)
assert sha(report) == sha(dest)
with (ROOT / 'logs/audit.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps({'ts':datetime.now().astimezone().isoformat(), 'agent':'codex-parent',
        'action':'fresh_reproduction_independent_comparison', 'target':str(report),
        'result':'layout_and_content_match_with_pipeline_exception',
        'detail':{'first_run':'hook_blocked_then_fixed_and_resumed','pages':[1,1],
                  'title_pt':[15,15],'source_changes':[],
                  'mandatory_exception':'page_guard p113 11/10',
                  'onedrive':str(dest),'candidate_sha256':sha(candidate)}}, ensure_ascii=False)+'\n')
print(json.dumps({'report':str(report),'onedrive':str(dest),'sha256':sha(report)},ensure_ascii=False))
