import json,sys,hashlib
from pathlib import Path
from datetime import datetime
root=Path(__file__).resolve().parents[2]; work=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'.claude/skills/hwpx/scripts'))
import edit_hwpx as ed
v=json.loads((work/'values.json').read_text(encoding='utf-8'))
v.update({
 'p:14':'본교의 교육 활동에 관심을 보내주시는 가정에 감사드립니다. 2026학년도 2학기 과목별 평가계획을 안내하오니 학생들의 자기주도적 학습에 많은 관심 부탁드립니다. 1학년은 자유학기로 지필고사 없이 과정중심평가를 실시하며, 성취도 대신 학습 과정과 성장을 기록합니다. 1학년 평가 비율은 계획에 명시된 경우만 표시하였습니다.',
 'p:17':'2학년 1회고사: 2026. 10. 27.~10. 28.',
 'p:18':'2학년 2회고사: 2026. 12. 7.~12. 8.',
 'p:20':'<과목별 평가계획>',
 'p:156':'※ 학사 일정 및 평가계획이 변경될 경우 평가 실시 전에 안내드립니다.',
 'cell:2:2:5':'독후보고서 30%, 포트폴리오 40%, 연계심화 30%',
 'cell:2:4:5':'영어 쓰기·말하기 각 30%, 한국 명소 소개 발표 40%',
 'cell:2:6:4':'과정형',
 'cell:2:6:5':'삼각형 작도·합동조건 발표, 다면체·정다면체 제작 및 성질 탐구',
 'cell:2:8:5':'스스로 내용정리·인권신문 각 30%, 영상 제작 40%',
 'cell:2:9:5':'스스로 내용정리 30%',
 'cell:2:10:5':'기체 부피·달 모형 실험 각 30%, 포트폴리오 40%',
 'cell:2:12:5':'피아노 코드 반주·몸타 리듬 창작 각 35%, 극음악 감상 30%',
 'cell:2:13:5':'피아노 연주(음계·코드 25%, 악곡 40%), 랩 창작 35%',
 'cell:2:14:4':'과정형',
 'cell:2:14:5':'생태 열쇠고리, 나전칠기 공예, 수묵 콤포지션',
 'cell:2:15:5':'화가의 방 40%, 나전칠기·나의 상징 문자도 각 30%',
 'cell:2:18:5':'옷차림 분석·소비자 문제 해결방안 각 30%, 도면 표현 40%',
 'cell:2:19:5':'아크릴 무드등·공익광고 제작 각 30%',
 'cell:2:20:5':'가상공간 성찰일기 30%, 다문화사회 포스터·생명보호 기념일 홍보/연설 각 35%',
 'cell:2:21:5':'성 편견 극복 포스터·학교 문제 해결 프로젝트 각 30%',
 'cell:2:23:5':'인공지능 프로그래밍·데이터 분석 프로젝트 각 40%, 포트폴리오 20%',
})
# The word 과정형 is defined explicitly in the general explanatory paragraph.
v['p:14']=v['p:14'].replace('과정중심평가를 실시하며','과정중심평가(표의 과정형)를 실시하며')
slots={s['key']:s for s in json.loads((work/'slots.json').read_text(encoding='utf-8'))['slots']}
over=[{'slot':k,'budget':slots[k]['max_chars'],'actual':len(''.join(t.split())),'text':t} for k,t in v.items() if len(''.join(t.split()))>slots[k]['max_chars']]
(work/'compact-values.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
(work/'compact-budget-review.json').write_text(json.dumps(over,ensure_ascii=False,indent=2),encoding='utf-8')
old=json.loads((work/'values.json').read_text(encoding='utf-8'))
lines=['# 축약 문구 대조','', '| 위치 | 초안 | 적용 문구 |','|---|---|---|']
for k,t in v.items():
 if t!=old[k]: lines.append(f'| {k} | {old[k]} | {t} |')
(work/'축약대조.md').write_text('\n'.join(lines),encoding='utf-8')
# Render-only proof: no claim of budget/visual acceptance. Final CLI edit is
# allowed only after the PDF image is inspected and the visual record exists.
p,c=ed._targets_from_slots(v)
src=root/'knowledge/examples/2026학년도 1학기 과목별 평가계획 안내 가정통신문.hwpx'
out=work/'render-proof.hwpx'
ed._pack_from_original(src,out,{},c,p)
print('RENDER PROOF ONLY:',out)
print(json.dumps(over,ensure_ascii=False))
event={'ts':datetime.now().astimezone().isoformat(),'agent':'Codex','action':'render_proof','target':str(out),'result':'unverified','detail':'사용자 승인: 기존 배치/1쪽, 의미 보존 축약. 원시 ZIP 보존 편집기로 렌더 전용 사본 생성. 예산 초과를 별도 기록하며 최종 CLI 생성은 실제 렌더 확인 이후만 수행.'}
with (root/'logs/audit.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
