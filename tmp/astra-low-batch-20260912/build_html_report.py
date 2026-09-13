from pathlib import Path
import base64, html, json, re, hashlib, shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / 'tmp/astra-low-batch-20260912'
OUT = ROOT / 'output/astra-low-batch-20260912'
data = json.loads((TMP / 'batch-result.json').read_text(encoding='utf-8'))
source = OUT / 'Astra_low_무작위5건_비교결과.md'
target = OUT / 'Astra_low_무작위5건_비교결과.html'

def inline(s):
    s = html.escape(s)
    s = re.sub(r'\[([^\]]+)\]\(&lt;([^<>]+?)&gt;\)', lambda m: '<span class="file-ref">'+m[1]+' <small>'+m[2]+'</small></span>', s)
    s = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', s)

def markdown(text):
    out, listing, table = [], False, False
    for line in text.splitlines():
        is_list = bool(re.match(r'^(?:- |\d+\. )', line))
        if listing and not is_list:
            out.append('</ul>'); listing = False
        if table and not line.startswith('|'):
            out.append('</tbody></table></div>'); table = False
        if not line.strip(): continue
        if line.startswith('|'):
            cells = [x.strip() for x in line.strip('|').split('|')]
            if all(re.fullmatch(r'[-:]+', x) for x in cells): continue
            if not table:
                out.append('<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+inline(x)+'</th>' for x in cells)+'</tr></thead><tbody>'); table = True
            else: out.append('<tr>'+''.join('<td>'+inline(x)+'</td>' for x in cells)+'</tr>')
        elif line.startswith('#'):
            n = min(len(line)-len(line.lstrip('#'))+1, 4)
            out.append(f'<h{n}>'+inline(line.lstrip('#').strip())+f'</h{n}>')
        elif is_list:
            if not listing: out.append('<ul>'); listing=True
            out.append('<li>'+inline(re.sub(r'^(?:- |\d+\. )', '', line))+'</li>')
        else: out.append('<p>'+inline(line)+'</p>')
    if listing: out.append('</ul>')
    if table: out.append('</tbody></table></div>')
    return '\n'.join(out)

new_images = ['case01/result.png','case02/preview.png','case03/render.png','case04/render.png','case05/final-1.png']
tabs, panels = [], []
for i, (case, values) in enumerate(data['visual_findings'].items()):
    title, verdict, finding, route, status = values
    tabs.append(f'<button role="tab" id="tab-{case}" aria-controls="{case}" aria-selected="{str(i==0).lower()}" onclick="selectCase({i})">{i+1:02d} · {html.escape(title)}</button>')
    pictures = []
    for label, path in [('기존 output 최종본', TMP / f'{case}-baseline-1.png'), ('Astra low 재작성', TMP / new_images[i])]:
        src = 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
        pictures.append(f'<figure><figcaption>{label}<span>1쪽 · 클릭하여 확대</span></figcaption><div class="paper-scroll"><img src="{src}" alt="{html.escape(title)} — {label}" onclick="enlarge(this)" tabindex="0" onkeydown="if(event.key===\'Enter\')enlarge(this)"></div></figure>')
    panels.append(f'''<section role="tabpanel" id="{case}" aria-labelledby="tab-{case}" {"hidden" if i else ""}>
<div class="case-head"><div><span class="eyebrow">CASE {i+1:02d}</span><h2>{html.escape(title)}</h2></div><span class="badge {'good' if i==4 else ''}">{html.escape(verdict)}</span></div>
<p class="finding">{html.escape(finding)}</p><div class="process"><span><b>작성 경로</b> {html.escape(route)}</span><span><b>남은 검증</b> {html.escape(status)}</span></div>
<div class="pair">{''.join(pictures)}</div></section>''')

CSS = '''
:root{--ink:#172d36;--muted:#61737c;--line:#dbe4e7;--accent:#086b62;--paper-scale:100%}*{box-sizing:border-box}body{margin:0;background:#f1f5f5;color:var(--ink);font:16px/1.65 "Malgun Gothic",system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:48px 36px}h1,h2,h3,h4,p{margin-top:0}h1{font-size:40px;line-height:1.25;letter-spacing:-1.6px;margin:12px 0 18px}h2{font-size:25px;line-height:1.4;margin:6px 0}h3{margin-top:28px}a{color:var(--accent)}.eyebrow{font-size:12px;font-weight:800;letter-spacing:1.6px;color:var(--accent)}.lead{font-size:20px;max-width:880px}.muted{color:var(--muted)}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:30px 0}.metric{border:1px solid var(--line);background:white;padding:20px 24px;border-radius:12px}.metric strong{display:block;font-size:32px;line-height:1.3}.metric span{color:var(--muted);font-size:14px}.notice{background:#fff5df;border-left:4px solid #bb861d;padding:14px 20px;border-radius:0 8px 8px 0;margin:22px 0}.nav{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0 14px}button{font:inherit;cursor:pointer;border:1px solid #cdd9dd;background:white;border-radius:8px;padding:10px 15px;color:var(--ink)}button[aria-selected=true]{background:var(--ink);border-color:var(--ink);color:white}button:focus-visible,img:focus-visible{outline:3px solid #db9b32;outline-offset:3px}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:10px 0 20px;color:var(--muted);font-size:14px}.toolbar label{display:flex;align-items:center;gap:10px}.case-head{display:flex;align-items:center;justify-content:space-between;gap:18px}.badge{font-size:13px;white-space:nowrap;background:#ffedcd;color:#805316;border-radius:30px;padding:7px 14px}.badge.good{background:#dcefe6;color:#1d6342}.finding{font-size:17px;margin:14px 0}.process{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;font-size:13px}.process span{background:#e7edef;padding:7px 12px;border-radius:6px}.process b{margin-right:8px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0;min-width:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#e2e8ea}figcaption{display:flex;justify-content:space-between;background:white;padding:12px 16px;font-weight:700;font-size:14px}figcaption span{font-weight:400;font-size:12px;color:var(--muted)}.paper-scroll{overflow:auto;max-height:940px;padding:14px}.paper-scroll img{display:block;width:var(--paper-scale);max-width:none;height:auto;box-shadow:0 3px 10px #20333a20;cursor:zoom-in}.recommend{background:var(--ink);color:white;border-radius:14px;padding:30px;margin:32px 0}.recommend .eyebrow{color:#80d6bf}.recommend p{margin:10px 0 0;max-width:950px}.report{background:white;border:1px solid var(--line);border-radius:12px;padding:28px 32px;margin-top:24px}summary{cursor:pointer;font-weight:bold;font-size:20px}.report-body{margin-top:24px}li{margin-bottom:10px}code{background:#edf2f4;padding:2px 5px;border-radius:4px;font-size:.9em;overflow-wrap:anywhere}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--line);padding:12px;text-align:left;min-width:130px;vertical-align:top}th{background:#edf3f3}.file-ref small{display:block;color:var(--muted);overflow-wrap:anywhere;font-size:11px}footer{margin-top:30px;color:var(--muted);font-size:13px}dialog{border:0;padding:0;border-radius:12px;width:95vw;height:94vh;max-width:1500px;max-height:96vh;background:#e4eaec}dialog::backdrop{background:#142d3ad9}.dialog-bar{position:sticky;top:0;display:flex;align-items:center;justify-content:space-between;padding:10px 20px;background:white;z-index:1}.dialog-body{padding:20px;overflow:auto;height:calc(100% - 65px)}.dialog-body img{display:block;width:1100px;max-width:none;margin:auto}body.modal-open{overflow:hidden}[hidden]{display:none!important}@media(max-width:760px){main{padding:26px 16px}h1{font-size:29px}.lead{font-size:17px}.metrics{grid-template-columns:1fr 1fr;gap:9px}.metric{padding:14px}.metric strong{font-size:26px}.pair{grid-template-columns:1fr}.case-head{align-items:flex-start;flex-direction:column;gap:10px}.toolbar{align-items:flex-start;flex-direction:column}.nav button{font-size:13px;padding:8px 10px}.report{padding:20px 16px}h2{font-size:22px}.paper-scroll{max-height:700px}figcaption{padding:10px;font-size:13px}.recommend{padding:23px}}@media print{body{background:white}main{padding:0}.nav,.toolbar,dialog,summary{display:none}.metrics{gap:8px}.metric{padding:12px}.pair{grid-template-columns:1fr 1fr}section[role=tabpanel]{display:block!important;break-before:page}.paper-scroll{max-height:none;overflow:visible;padding:0}.paper-scroll img{width:100%}.report{border:0;padding:0}.recommend{background:#edf3f3;color:var(--ink)}figure{break-inside:avoid}.process{font-size:11px}.badge{white-space:normal}}
'''
page = '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Astra low · 무작위 5건 비교 보고서</title><style>'''+CSS+'''</style></head><body><main>
<header><span class="eyebrow">HWP_DOC / REPRODUCTION REVIEW / 2026. 9. 12.</span><h1>내용은 재현됐고,<br>기안문 서식에는 차이가 남았습니다.</h1><p class="lead">기존 최종본과 새 세션에서 만든 문서 5건을 비교했습니다. 가정통신문은 기존 양식에 가까웠고, 기안문 4건은 제목 굵기 또는 붙임 정렬에 손볼 부분이 있었습니다.</p><p class="muted">gpt-6-astra · reasoning low · 후보 17건 중 무작위 5건 · 정답 비공개</p></header>
<div class="metrics"><div class="metric"><strong>5 / 5</strong><span>핵심 내용 재현</span></div><div class="metric"><strong>68 / 68</strong><span>사실·수치 검사 통과</span></div><div class="metric"><strong>5 / 5</strong><span>한글 실열림 · 1쪽 렌더</span></div><div class="metric"><strong>4건</strong><span>서식 보정 필요</span></div></div>
<div class="notice"><b>검증 완료와는 구분합니다.</b> 글자 수 예산 FAIL, 기준 부재로 인한 검사 미실행, 업무지침 미확인이 남았습니다. 추첨 결과는 기안문 4건과 가정통신문 1건으로, 복잡한 계획서 품질까지 대표하지 않습니다.</div>
<nav class="nav" role="tablist" aria-label="비교할 문서">'''+''.join(tabs)+'''</nav><div class="toolbar"><span>왼쪽: 기존 최종본 · 오른쪽: 새 결과 / 모바일에서는 위·아래로 표시</span><label>문서 확대 <input id="zoom" type="range" min="100" max="200" value="100" step="10" aria-label="문서 확대 비율"><output id="zoom-value">100%</output></label></div>
'''+''.join(panels)+'''
<aside class="recommend"><span class="eyebrow">NEXT IMPROVEMENT</span><h2>공통 기안문 HWPX 양식과 붙임 정렬부터</h2><p>PDF·Markdown을 참고해 새 XML로 만든 3건에서 모두 제목 굵기가 빠졌습니다. 공통 양식의 제목·상단 간격을 보존하고, ‘끝.’의 줄바꿈을 줄이려고 붙임 들여쓰기를 없애지 않도록 하는 개선이 우선입니다. 모델 강도에 따른 대조시험은 하지 않았으므로 모델을 원인으로 단정할 수는 없습니다.</p></aside>
<details class="report" open><summary>시험 조건 · 작업 절차 · 검증 근거 전체 보기</summary><article class="report-body">'''+markdown(source.read_text(encoding='utf-8'))+'''</article></details>
<footer>Hwp_doc · 기존 Markdown 보고서를 바탕으로 만든 시각 비교판. 문서 이미지를 포함한 단일 HTML이며 인터넷 연결 없이 열 수 있습니다. HWPX 본문과 시험 판정은 변경하지 않았습니다.</footer></main>
<dialog id="viewer" aria-label="문서 확대 보기"><div class="dialog-bar"><strong id="viewer-title"></strong><button onclick="closeViewer()">닫기 ×</button></div><div class="dialog-body"><img id="viewer-image" alt=""></div></dialog>
<script>
const tabs=[...document.querySelectorAll('[role=tab]')], panels=[...document.querySelectorAll('[role=tabpanel]')];
function selectCase(n){tabs.forEach((t,i)=>{t.setAttribute('aria-selected',i===n);t.tabIndex=i===n?0:-1;panels[i].hidden=i!==n});}
tabs.forEach((t,i)=>t.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();let n=e.key==='Home'?0:e.key==='End'?4:(i+(e.key==='ArrowRight'?1:4))%5;selectCase(n);tabs[n].focus()}}));selectCase(0);
const zoom=document.getElementById('zoom');zoom.addEventListener('input',()=>{document.documentElement.style.setProperty('--paper-scale',zoom.value+'%');document.getElementById('zoom-value').textContent=zoom.value+'%'});
const viewer=document.getElementById('viewer');function enlarge(img){document.getElementById('viewer-image').src=img.src;document.getElementById('viewer-image').alt=img.alt;document.getElementById('viewer-title').textContent=img.alt;viewer.showModal();document.body.classList.add('modal-open')}function closeViewer(){viewer.close()}viewer.addEventListener('close',()=>document.body.classList.remove('modal-open'));
window.addEventListener('beforeprint',()=>document.querySelector('details').open=true);
</script></body></html>'''
target.write_text(page, encoding='utf-8')
destination = Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용/astra-low-batch-20260912') / target.name
destination.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(target, destination)
digest = hashlib.sha256(target.read_bytes()).hexdigest()
assert digest == hashlib.sha256(destination.read_bytes()).hexdigest()
with (ROOT / 'logs/audit.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps({'ts':datetime.now().astimezone().isoformat(),'agent':'codex','action':'html_comparison_report','target':str(target),'result':'created','detail':{'embedded_images':10,'source':str(source),'sha256':digest,'onedrive':str(destination)}},ensure_ascii=False)+'\n')
print(json.dumps({'html':str(target),'bytes':target.stat().st_size,'images':10,'onedrive':str(destination)},ensure_ascii=False))
