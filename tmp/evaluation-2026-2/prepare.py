import json, hashlib, sys
from pathlib import Path
from datetime import datetime
root = Path(__file__).resolve().parents[2]
work = Path(__file__).resolve().parent
draft = root/'output/2026_2학기_평가계획_가정통신문_초안.md'
slots = json.loads((work/'slots.json').read_text(encoding='utf-8'))['slots']
lookup = {s['key']: s for s in slots}
rows = [[c.strip() for c in line.split('|')[1:-1]] for line in draft.read_text(encoding='utf-8').splitlines() if line.startswith('|') and ('| 1학년 |' in line or '| 2학년 |' in line)]
assert len(rows) == 22
values = {
 'p:3':'화동중 제2026-   호',
 'p:12':'2026학년도 2학기 과목별 평가계획 안내',
 'p:14':'항상 본교의 교육 활동에 많은 관심과 사랑을 보내주시는 가정에 감사드립니다. 2026학년도 2학기 과목별 평가계획을 다음과 같이 안내드립니다. 학년별 평가 방법과 과목별 평가 활동을 확인하시고, 학생들의 자기주도적 학습이 이루어질 수 있도록 가정의 많은 관심 부탁드립니다. 1학년은 자유학기로 지필고사 없이 과정중심평가를 실시합니다.',
 'p:17':'2학년 2학기 1회고사: 2026. 10. 27.~10. 28.',
 'p:18':'2학년 2학기 2회고사: 2026. 12. 7.~12. 8.',
 'p:20':'<과목별 평가 활동 및 반영 비율>',
 'cell:2:0:2':'2학기',
 'p:156':'※ 1학년 비율은 계획에 명시된 경우만 표시하며 교과별 성취도는 산출하지 않고 학습 과정과 성장을 기록합니다. 일정 및 평가계획 변경 시 평가 전에 안내합니다.',
 'p:158':'2026.    .    .',
}
# Only use actual extractor cell addresses; align rows by their explicit grade cells.
grade_slots = [s for s in slots if s['kind']=='cell' and s['key'].startswith('cell:2:') and s['key'].endswith(':1') and s['preview'] in ('1학년','2학년')]
assert len(grade_slots)==len(rows)
for source_slot,row in zip(grade_slots,rows):
 assert source_slot['preview']==row[1]
 prefix=source_slot['key'].rsplit(':',1)[0]
 for col,value in zip((2,3,4,5),row[2:]):
  key=f'{prefix}:{col}'
  assert key in lookup
  values[key]=value
(work/'values.json').write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf-8')
over=[]
for key,value in values.items():
 n=len(''.join(value.split()))
 if n>lookup[key]['max_chars']:
  over.append({'slot':key,'budget':lookup[key]['max_chars'],'actual':n,'text':value})
(work/'budget-review.json').write_text(json.dumps(over,ensure_ascii=False,indent=2),encoding='utf-8')
record={'confirmed':True,'by':'user','message':'작성해줘','draft_sha256':hashlib.sha256(draft.read_bytes()).hexdigest(),'at':datetime.now().astimezone().isoformat(),'scope':'직전 턴 마크다운 초안의 HWPX 작성 승인. 번호 및 배부일 미제공 유지.'}
(work/'approval.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(over,ensure_ascii=False,indent=2))
