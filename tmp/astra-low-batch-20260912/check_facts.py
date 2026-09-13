from pathlib import Path
import json, re
from audit_batch import inspect
ROOT=Path(__file__).resolve().parents[2]; WORK=Path(__file__).resolve().parent
required={
 'case01':['화동중학교','내부결재','2026학년도 2학기 1회고사 출제 관련 연수','화동중학교-2058(2026. 3. 17.)','2026. 10. 8.','13:00','교무실','전 교원','2026학년도 2학기 시험출제 관련 연수 자료 1부'],
 'case02':['내부결재','2026학년도 화동중학교 2학기 교과별 평가계획 수립','화동중학교-2058(2026. 3. 17.)','수립하여 운영','2026학년도 화동중 1학년 2학기 교수학습 및 평가계획(전체) 1부','2026학년도 화동중 2학년 2학기 교수학습 및 평가계획(전체) 1부'],
 'case03':['내부결재','2026학년도 2학기 1회고사 가정통신문 배부','배부하고자','확인 후 기재','2026학년도 2학기 1회고사 관련 가정통신문 1부'],
 'case04':['내부결재','2026학년도 2학기 2회고사 교과협의회 회의록','실시하여 보고','계획 결재 후','문서번호','시행일','2026학년도 2학기 2회고사 교과협의회 회의록 1부'],
 'case05':['2026학년도 2학기 2회고사 실시 안내','자유학기','양일 정상수업','중식 후 하교','중식 후 정상수업','2026. 12. 9.','12. 12.','2026. 11. 24.','화 동 중 학 교 장','샤프','지우개','컴퓨터용 수성싸인펜','검은색 볼펜','수정테이프','즉시 공지','미부여'],
}
norm=lambda s:re.sub(r'\s+','',s)
results=[]
for case,need in required.items():
    files=list((ROOT/'output/astra-low-batch-20260912'/case).glob('*.hwpx'))
    if len(files)!=1:raise SystemExit(case+' requires exactly one final file')
    doc=inspect(files[0]); full=norm('\n'.join(x['text'] for x in doc['paragraphs']))
    checks=[{'item':s,'pass':norm(s) in full} for s in need]
    if case in ('case03','case04'):
        checks.append({'item':'새 자교 문서번호를 지어내지 않음','pass':not bool(re.search(r'화동중학교-\d{3,}',full))})
    if case=='case05':
        def cell(t,r,c):
            return next(x['text'] for x in doc['tables'][t]['cells'] if x['cellAddr']=={'colAddr':str(c),'rowAddr':str(r)})
        for r,subj in zip([1,2,3,4,6,7,8,9],['국어','영어','자습','자습','수학','역사','자습','과학']):
            checks.append({'item':f'시간표 row{r} 2학년={subj}','pass':norm(cell(1,r,3))==subj})
        for col,ranges,ratios,counts in [(2,[3,4],[60,40],[16,6]),(3,[3,4],[84,16],[16,4]),(4,[3,4,1],[70,30],[18,2]),(5,[4,6],[85,15],[20,2]),(7,[4,5],[75,25],[20,5])]:
            for row,expected in [(4,ranges),(5,ratios),(6,counts)]:
                actual=list(map(int,re.findall(r'\d+',cell(2,row,col))))
                checks.append({'item':f'출제표 row{row} col{col}={expected}','pass':actual==expected,'actual':actual})
    results.append({'case':case,'sha256':doc['sha256'],'checks':checks,'all_pass':all(x['pass'] for x in checks)})
(WORK/'facts-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'case':x['case'],'checks':len(x['checks']),'all_pass':x['all_pass'],'failures':[c for c in x['checks'] if not c['pass']]} for x in results],ensure_ascii=False,indent=2))
