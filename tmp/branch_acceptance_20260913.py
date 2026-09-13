"""Disposable branch acceptance evidence; never manufactures user approval."""
from pathlib import Path
import datetime, hashlib, json, shutil, sys, os, subprocess, time
ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'tmp/branch-acceptance-20260913'
PY=Path(sys.executable)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def prepare():
    assert not RUN.exists()
    RUN.mkdir()
    save(RUN/'protected-before.json',{p.relative_to(ROOT).as_posix():sha(p) for f in ['knowledge','output','.hwpdoc/templates'] for p in (ROOT/f).rglob('*') if p.is_file()})
    src=ROOT/'tmp/materials-followup-20260913/sources'
    sys.path.insert(0,str(ROOT/'.claude/skills/hwpx/scripts'))
    from hwpx_slots import collect_slots
    for name in ['notice','reply','gianmun']:
        dest=RUN/'sources'/f'{name}.hwpx';dest.parent.mkdir(exist_ok=True)
        shutil.copy2(src/f'{name}.hwpx',dest)
        save(RUN/'sources'/f'{name}-slots.json',collect_slots(dest,preview_len=1000))
    for name in ['w2_sources','school_alpha','activities','policy']:
        shutil.copy2(ROOT/f'evals/plugin_distribution/fixtures/{name}.json',RUN/'sources'/f'{name}.json')
    reply_date=datetime.date.fromisoformat(read(RUN/'sources/school_alpha.json')['date'])-datetime.timedelta(days=read(RUN/'sources/policy.json')['preferences']['reply_days_before'])
    save(RUN/'date-check.json',{'activity':'2026-10-16','reply_days_before':4,'reply_date':reply_date.isoformat(),'weekday':reply_date.weekday(),'source':'datetime calculation from frozen school policy; not a legal rule'})
    common={'p:3':'[[문서번호]]','p:4':'교무실: 미확인','p:5':'행정실: 미확인','p:6':'누리집: 미확인','p:7':'주소','p:8':'미확인','p:9':'안 내','p:10':'검토용 시험','p:11':'가람중학교 가상 시험 문서'}
    notice=dict(common)
    notice.update({'p:13':'과학 독서 나눔 안내','p:14':'학부모님, 안녕하십니까?','p:15':'과학 독서 나눔 활동을 다음과 같이 안내합니다. 이 문서는 가람중학교의 가상 기능 시험용 검토 초안입니다.','p:16':'감사합니다.','p:19':'과학 독서 나눔 안내','p:21':'1. 활동 안내','p:22':'가. 기간: 2026. 10. 12.~10. 16.','p:23':'나. 장소: 과학실','p:24':'다. 대상: 1학년 20명','p:29':'2. 확인 사항','p:30':'문서번호와 학교 연락처는 확인 후 입력합니다. 실제 발송하지 않습니다.','p:34':'3. 참고 사항','p:35':'가상 시험 자료로 작성한 검토 초안입니다.','p:40':'2026. 10. 5.','p:42':'가람중학교장[직인생략]'})
    for i in [25,26,27,31,32,36,37]:notice[f'p:{i}']=''
    reply=dict(common)
    reply.update({'p:13':'가람과학관 체험 참가 안내','p:14':'학부모님 안녕하십니까?','p:15':'가람과학관 체험 참가 여부를 아래 회신란에 표시해 2026. 10. 12.까지 제출해 주시기 바랍니다. 제출처는 확인 후 안내합니다. 이 문서는 가상 기능 시험용 검토 초안입니다.','p:17':'○ 일 시: 2026. 10. 16. 09:00~13:00','p:18':'○ 장 소: 가람과학관','p:19':'○ 대 상: 미확인','p:20':'○ 인 솔: 미확인','p:42':'가람과학관 체험 참가 동의서','p:52':'2026학년도','p:53':'가람과학관 체험','p:56':'[[배부일]]','p:57':'가 람 중 학 교 장 [직인생략]'})
    for i,(t,activity) in enumerate(read(RUN/'sources/activities.json')['five']):
        for col,val in enumerate([t,activity,'']):reply[f'p:{25+i*3+col}']=val
    base=['가람중학교',None,'(경유)','제목 과학 체험 참여 현황 제출','1. 관련: 가상교육지원청-200(2026. 10. 1.)',None,'3. 제출 기한: 2026. 10. 8. 끝.']
    values={'notice':notice,'reply':reply}
    for variant,recipient,sentence in [('official_reply','수신 가상교육지원청','2. 과학 체험 참여 현황을 제출합니다. 가람중학교 1학년 참여 학생은 20명입니다.'),('email','수신 내부결재','2. 과학 체험 참여 현황(1학년 20명)을 담당자 이메일로 제출하고자 합니다.')]:
        lines=base.copy();lines[1]=recipient;lines[5]=sentence
        values[variant]=dict(zip(['p:1','p:3','p:4','p:5','p:7','p:9','p:11'],lines))
    save(RUN/'proposed-values.json',values)
    budgets={}
    for name,mapping in values.items():
        kind=name if name in ('notice','reply') else 'gianmun'
        slots={x['key']:x for x in read(RUN/'sources'/f'{kind}-slots.json')['slots']}
        assert set(mapping)<=set(slots)
        budgets[name]=[{'slot':k,'text':v,'length':len(''.join(v.split())),'budget':slots[k]['max_chars']} for k,v in mapping.items() if len(''.join(v.split()))>slots[k]['max_chars']]
    save(RUN/'budget-check.json',budgets)
    draft=['# 미검증 업무 분기 시험 초안','', '가상 시험용이며 실제 공문·이메일 발송은 하지 않습니다. 기존 양식의 표·여백·서명 위치를 유지합니다. 일반 가통의 제목은 8자로 예산 안에 들어갑니다. 회신형 일정 일부는 원문을 보존하고 미검증 사본의 실제 렌더로 수용 여부를 확인합니다. 구조 변경은 제안하지 않습니다.','', '학교가 다른 가상 시험이므로 원래 학교 연락처·주소·교훈은 시험용 미확인 표기로 교체합니다. 연락처나 실제 주소를 지어내지 않습니다.','']
    for name,title in [('notice','일반 가정통신문'),('reply','회신형 가정통신문'),('official_reply','W2 공문 회신'),('email','W2 이메일 제출용 내부결재')]:
        draft+=['## '+title,'']
        for k,v in values[name].items():
            if v: draft.append(v)
        if name=='reply':draft+=['','기존 참가( )·불참( )·학생 및 보호자 서명란을 그대로 보존합니다. 문서번호·배부일·대상·인솔 인원·회신 제출처는 미확인입니다.']
        if name=='email':draft+=['','이메일 주소가 원문에 없으므로 미확인으로 유지합니다. 실제 전송하지 않습니다.']
        draft+=['']
    draft+=['## 승인 범위','', '이 문안으로 시험용 HWPX 사본을 생성·검증하는 것에 대한 확인을 요청합니다. 미확인 값이 남으면 검증완료본으로 전달하지 않고 미확인 검토 초안으로만 시험합니다. 실제 문서번호·주소·학생 정보와 사람 최종 검토 평점은 만들지 않습니다.']
    (RUN/'drafts.md').write_text('\n'.join(draft)+'\n',encoding='utf-8')
    save(RUN/'preparation.json',{'at':now(),'draft_sha256':sha(RUN/'drafts.md'),'approval':'pending','fixture_only':True,'sources':{p.name:sha(p) for p in (RUN/'sources').iterdir() if p.is_file()}})
    print(str(RUN/'drafts.md'))
if __name__=='__main__':prepare()
