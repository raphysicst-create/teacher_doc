from pathlib import Path
import sys, json, hashlib, platform, subprocess
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.claude/skills/hwpx/scripts'))
from page_guard import collect_text_budget_profile

def write(name, obj):
    (WORK / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

base = ROOT / 'knowledge/templates/가정통신문-고사안내/양식.hwpx'
slots = json.loads((WORK/'slots-current.json').read_text(encoding='utf-8'))['slots']
values = {
 'p:3': '통신문번호: 미부여',
 'p:12': '2026학년도 2학기 1회고사 실시 안내',
 'p:14': '각 가정에 건강과 행복이 가득하시길 기원합니다. 2026학년도 2학기 1회고사를 다음과 같이 안내합니다. 1학년은 자유학기로 지필고사에 응시하지 않고 양일 정상수업합니다. 학생들에게 관심과 격려를 부탁드립니다.',
 'p:16': '1. 1회고사 일정 2026. 10. 27.(화) ~ 10. 28.(수) 2일간',
 'cell:1:1:0':'10/27(화)', 'cell:1:6:0':'10/28(수)',
 'cell:1:5:2':'2학년 중식 후 하교',
 'p:109':'3. 1회고사 이의 신청 기간 : 2026. 10. 29.(목) ~ 11. 2.(월)',
 'p:113':'2026. 10. 14.',
}
for row in [1,2,3,4,6,7,8,9]: values[f'cell:1:{row}:2']='정상수업'
for row,subject in zip([1,2,3,4,6,7,8,9],['자습','국어','자습','수학','자습','영어','과학','역사']): values[f'cell:1:{row}:3']=subject
for s in slots:
    if s['kind']=='paragraph' and s['index'] in [65,66,67,69,70,72,73,74,75,76,79,80,81,83,84]: values[s['key']]='미응시'
# 기존 두 문단 셀의 문단 수는 유지한다.
values['p:82']=''
for idx, value in {88:'4-5단원',89:'5-6과',90:'3-4(1)단원',91:'4-5단원',93:'3-4단원',95:'선택형 70%, 서·논술형 30%',96:'선택형 85%, 서·논술형 15%',97:'선택형 75%, 서·논술형 25%',98:'선택형 85%, 서·논술형 15%',99:'선택형 80%, 서·논술형 20%',102:'선택형 16, 서·논술형 4',103:'선택형 17, 서·논술형 3',104:'선택형 15,',105:'서·논술형 5',106:'선택형 18, 서·논술형 2',107:'선택형 17,',108:'서·논술형 3'}.items(): values[f'p:{idx}']=value
assert set(values) <= {s['key'] for s in slots}
write('values.json', values)
write('read-only-budget-inspection.json', collect_text_budget_profile(base))
paths=['CLAUDE.md','.claude/skills/hwpx/SKILL.md','.agents/skills/hwpx/SKILL.md','knowledge/examples/index.md','knowledge/templates/가정통신문-고사안내/README.md','knowledge/templates/가정통신문-고사안내/양식.hwpx','knowledge/templates/가정통신문-고사안내/slots.json']
write('environment-and-sources.json', {'observed_at':datetime.now().astimezone().isoformat(),'application':'Codex delegated agent via desktop root thread','app_version':'미확인','model':'GPT-6 (시스템 제공 계열 정보, 정확한 모델 ID 미확인)','reasoning_effort':'미확인','shell':'PowerShell','sandbox_mode':'danger-full-access','approval_policy':'never','protection':'PreToolUse hook blocked safe Copy-Item twice; actual protection boundary unverified','cwd':str(ROOT),'python':sys.executable,'python_version':sys.version,'platform':platform.platform(),'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'skill_junction':str((ROOT/'.agents/skills/hwpx').resolve()),'generation_authorization':{'user_original':'새 세션에서 미리 작업했던 아무 공문 하나 골라집고 만들어달라고 해서 의도한대로 나오는지 확인해줘','scope':'기존 확정 사실 동일 업무 재작성 시험','parent_confirmation':'초안 확인 후 기존 범위 내 생성 진행 가능, 새 사용자 승인 문구 금지','new_user_approval_fabricated':False},'read_isolation':'기존 output, 다른 tmp 작업물, 과거 세션·메모리 및 evals 기대 판단 미열람','git_status_before':subprocess.run(['git','status','--short'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8').stdout})
write('content-rules.json', {'require':['2026학년도 2학기 1회고사 실시 안내','1학년은 자유학기로 지필고사에 응시하지 않고 양일 정상수업합니다.','통신문번호: 미부여','2학년 중식 후 하교','10/27(화)','10/28(수)','4-5단원','5-6과','3-4(1)단원','3-4단원','2026. 10. 14.'], 'forbid':['2026학년도 1학기','화동중 제2026-23호','4/28','4/29','2026. 4. 21.','2026년 4월 28일','2026년 4월 30일','5월 4일','1-2단원','1-2과','1-2(2)단원','1-3단원','2-3단원']})
print('Prepared values, environment and input evidence. No HWPX generated.')
