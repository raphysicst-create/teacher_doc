from pathlib import Path
import sys, json
WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[1]
sys.path.insert(0,str(ROOT/'.claude/skills/hwpx/scripts'))
import edit_hwpx as edit
values=json.loads((WORK/'values.json').read_text(encoding='utf-8'))
values['p:16']='1. 고사 일정 2026. 10. 27.(화) ~ 10. 28.(수) 2일간'
values['p:109']='3. 이의 신청 기간 : 2026. 10. 29.(목) ~ 11. 2.(월)'
(WORK/'values.json').write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf-8')
paragraphs,cells=edit._targets_from_slots(values)
replacements={
 '1. 1회고사 일정 ':'1. 고사 일정 ',
 '2026년 4월 28일(화) - 4월 29일(수) 2일간':'2026. 10. 27.(화) ~ 10. 28.(수) 2일간',
 '3. 1회고사 이의 신청 기간 : ':'3. 이의 신청 기간 : ',
 '2026년 4월 30일(목) - 5월 4일(월)':'2026. 10. 29.(목) ~ 11. 2.(월)',
}
values.pop('p:16')
values.pop('p:109')
(WORK/'edit-values.json').write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'replacements.json').write_text(json.dumps(replacements,ensure_ascii=False,indent=2),encoding='utf-8')
paragraphs,cells=edit._targets_from_slots(values)
try:
    edit.preflight_text_budget(WORK/'reference.hwpx',replacements,cells,paragraphs,12)
    findings='입력 전 검사 통과'
except SystemExit as e:
    findings=str(e)
(WORK/'preview-budget-warning.txt').write_text(findings,encoding='utf-8')
# SKILL.md의 미검증 사본 렌더 경로. 확인 플래그를 붙이지 않으며
# 원본 보호·원시 ZIP 복사 및 기존 슬롯 편집 함수를 그대로 사용한다.
result=edit._pack_from_original(WORK/'reference.hwpx',WORK/'미검증_렌더용_v2.hwpx',replacements,cells,paragraphs)
print(findings)
print('미검증 사본 생성:',result)
