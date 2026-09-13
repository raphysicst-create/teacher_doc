from pathlib import Path
from datetime import datetime
import json, hashlib, shutil

ROOT=Path(__file__).resolve().parents[2]; WORK=Path(__file__).resolve().parent
OUT=ROOT/'output/astra-low-batch-20260912'
selection=json.loads((WORK/'selection.json').read_text(encoding='utf-8'))
facts=json.loads((WORK/'facts-checks.json').read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert len(facts)==5 and all(r['all_pass'] for r in facts)
source_changes=[p for p,h in selection['source_hashes'].items() if sha(ROOT/p)!=h]
baseline_changes=[c['baseline'] for c in selection['cases'] if sha(ROOT/c['baseline'])!=c['sha256']]
assert not source_changes and not baseline_changes
comparisons=[json.loads((WORK/(c['case']+'-comparison.json')).read_text(encoding='utf-8')) for c in selection['cases']]
for c in comparisons:assert sha(Path(c['candidate']))==c['candidate_sha256']
observations={
 'case01':('출제연수 기안문','내용 재현 / 서식 차이','제목 굵기 빠짐. 문서 전체가 기존보다 약 19.2pt(6.8mm) 위로 이동. 날짜·시각·대상·장소·관련번호 일치, 요일 표시는 생략.','PDF/MD 참고 → 신규 XML','기준 HWPX 없어 page_guard 미실행'),
 'case02':('평가계획 수립 기안문','내용 재현 / 작은 서식 보정 필요','제목 굵기·기관명·본문 서체 유지. 붙임 둘째 항 들여쓰기가 첫 항과 맞지 않음. 붙임 2건의 명칭·학년·수량은 일치.','기존 HWPX 슬롯 편집','page_guard 문단 예산 2건 FAIL'),
 'case03':('1회고사 가통 배부 기안문','내용 재현 / 서식 차이','제목 굵기 빠짐, 기관명 아래 간격과 본문 줄바꿈 변화. 관련번호·시행일은 미확인 표시로 유지.','PDF/MD 참고 → 신규 XML','자기비교 page_guard는 독립 근거에서 제외'),
 'case04':('2회고사 협의회 기안문','내용 재현 / 서식 차이','제목 굵기 빠짐, 수신·경유·제목 간격 변화. 계획 결재 후 번호·시행일 기재 상태 보존.','PDF/MD 참고 → 신규 XML','기준 HWPX 없어 page_guard 미실행'),
 'case05':('2회고사 가정통신문','내용·양식 대체로 재현','제목 15pt·굵기, 표 3개의 행·열·병합·셀 크기·여백 동일. 8교시 과목과 5과목 범위·비율·문항 수 일치. 도입문 축약으로 표의 세로 위치는 달라짐.','고사안내 HWPX 슬롯 편집','page_guard 날짜 예산 11/10자 FAIL'),
}
rows=[]
links=[]
for c in comparisons:
    case=c['case']; name,verdict,note,route,limit=observations[case]
    rows.append(f'| {case} {name} | 1쪽 / 일치 | {verdict} | {note} |')
    candidate=Path(c['candidate']); reports=list(candidate.parent.glob('*.md'))
    links.append(f'- **{case} {name}**: [새 HWPX](<{candidate.as_posix()}>) · [기존 최종본](<{Path(c["baseline"]).as_posix()}>) · [작성 세션 검증보고](<{reports[0].as_posix()}>)')
check_count=sum(len(r['checks']) for r in facts)
report=f'''# Astra low 무작위 5건 재작성 비교

작성일: 2026. 9. 12. / 프로젝트: Hwp_doc

**핵심 내용은 5건 모두 재현했지만, 기존 최종본 수준의 서식을 일관되게 재현하지는 못했다.** 가정통신문은 기존 양식에 가까웠고, 기안문 4건은 제목 굵기 또는 붙임 정렬에 손볼 부분이 있었다. 부모는 생성 결과를 수정하거나 품질 코칭으로 보정하지 않았다.

## 시험 조건

- 사용자 요청의 `astra-light 수준`을 **gpt-6-astra / reasoning_effort low**로 해석해 5건 모두 명시적으로 지정했다. 별도 `astra-light` 모델 ID를 사용한 시험은 아니다. 로컬 models_cache의 Astra 지원 강도에서 low를 확인했고 각 새 에이전트 호출에도 같은 설정을 전달했다. 참고: [공식 Astra 모델 문서](https://developers.openai.com/api/docs/models/gpt-6-astra).
- 검토 동의가 기록된 최종본과 명시적으로 함께 승인된 첨부로 구성한 **17개 후보**에서 비복원 균등 무작위 추출했다. 이전 버전·거절본·실험 초안·직전 시험한 1회고사 가통은 제외했다. seed: `{selection['seed']}`. 결과를 본 뒤 재추첨하지 않았다.
- 추첨 결과 **기안문 4건 + 가정통신문 1건**으로 몰렸다. 운영계획서·정산서·회의록 본체·교수학습계획서 등 다른 유형의 성능을 대표하지 않는다.
- 5건마다 `fork_turns=none`인 새 대화를 사용했다. 이전 output 정답, 이전 세션·메모리·다른 사례·평가 정답은 공개하지 않았다. 현재 CLAUDE.md·스킬·knowledge 자료와 업무 입력 사실은 읽을 수 있었다. 정답 비공개는 의도된 시험 조건이며 기존 output을 활용하지 않은 것 자체는 결함이 아니다.
- 선택된 **파일 본체 1개씩**만 재작성했다. 기안문에 적힌 붙임 파일 자체의 신규 생성은 입력에서 명시적으로 제외했다. 과거 문서의 사실을 재현하는 시험이며 현재 실제 학교 일정·결재가 완료됐다는 의미는 아니다.
- 준비·편집은 최대 3건 병렬, COM은 부모가 순서만 조정해 직렬 실행했다. 부모 개입은 배정·생성 범위 명시·COM 순서 조정·독립 검수다. 배치 도중 코드·스킬·양식을 고치지 않았다.

## 최종 산출물 비교

| 문서 | 페이지 / 핵심 사실 | 판단 | 확인한 차이 |
|---|---|---|---|
{chr(10).join(rows)}

기존 5건도 한글에서 다시 PDF로 내보냈으며 모두 1쪽이었다. 새 5건 역시 한글 실열림·PDF 렌더를 통과했다. 부모가 각 페이지를 직접 보았고 XML의 실제 서체·크기·굵기·표 셀 구조와 내용을 비교했다. **1쪽·잘림 없음만으로 서식 재현 통과를 판정하지 않았다.**

부모가 입력에서 별도로 정의한 핵심 사실·번호 미창작·표 수치 검사 **{check_count}건 모두 통과**했다. 가정통신문은 8교시 과목과 5교과별 범위·비율·문항 수를 XML 셀 주소로 직접 확인했다. 이 검사는 품질 점수나 전 문장 의미의 자동 보증이 아니며, 문안은 별도 대조했다.

## 반복된 문제와 근거

1. **기안문 생성 경로에 따라 제목 서식이 달라진다.** case01·03·04는 PDF/MD 예시를 보고 신규 XML로 만들었고, 세 건 모두 기존 최종본의 제목 굴림 12pt **굵게**가 보통 굵기로 바뀌었다. 기관명 22pt와 본문 굴림 12pt 자체는 유지했다. case02는 성립전예산요구 양식의 공통 기안문 골격을 편집해 제목 굵기를 유지했다. 즉 이번 관찰은 모델의 사실 이해보다 **공통 기안문 베이스 선택과 서식의 명시성** 문제를 가리킨다. 모델 강도만 바꾼 대조시험은 하지 않았으므로 모델을 원인으로 단정할 수 없다.
2. **줄바꿈을 줄이려다 정렬을 희생한다.** case02는 붙임의 `끝.`이 분리되는 것을 줄이려고 둘째 항 앞 공백을 줄였다고 기록했다. 결국 둘째 항의 들여쓰기가 첫 항과 달라졌다. 원래 최종본도 전체 1쪽이므로 ‘끝.을 같은 줄에 두기’가 정렬보다 우선해야 한다는 근거는 없다.
3. **실제 렌더 정상과 글자 수 예산 FAIL이 연결되지 않는다.** case02는 본문 54→59자·붙임 30→72자, case05는 배부일 10→11자로 page_guard FAIL이 남았다. PDF에서는 모두 수용됐고 작성자들은 FAIL을 숨기지 않았다. 짧은 날짜 형식만 바뀌어도 예산에 걸리는 현재 기준은 자동 완료 판단에 소음을 준다.
4. **신규 문서의 검증 완료 조건이 불명확하다.** case01·04는 같은 본체 HWPX 기준이 없어 page_guard를 미실행으로 남겼다. case03은 결과물을 자기 자신과 비교한 PASS를 한 차례 만들었지만, 최종 보고에서 독립 검증 근거가 아니라고 정정했다. 자기비교는 이 평가에서도 인정하지 않았다.
5. **도구 호출 마찰이 반복된다.** case03·04·05는 gonmun_lint의 첫 위치 인자 호출이 실패해 `--hwpx`로 수정했다. case02·03의 업무지침 조회는 120초 timeout, 다른 사례도 partial·적용범위 미확인을 보존했다. case01은 초안을 원문 확인 완료 전에 기록한 순서상 한계도 스스로 보고했다.

## 권장하는 다음 개선

- **일반 기안문용 HWPX 공통 골격과 선택 규칙을 명시한다.** 기존 공개 양식의 공통 배치를 독립 유형으로 정리하고 제목 굵기·상단 간격·붙임 번호 들여쓰기를 고정한다. 시험용 정답 output을 몰래 베이스로 주거나 사용자가 의도적으로 제외한 자료를 자동 연결하는 개선을 뜻하지 않는다.
- **붙임은 항목별 들여쓰기를 보존한다.** `끝.`이 줄바꿈되는 것을 해결하려고 앞 공백을 없애지 않도록 한다. 같은 1쪽이면 번호 정렬을 먼저 유지한다.
- **렌더로 확인한 예산 예외와 신규 문서 검증을 명확히 구분한다.** 날짜 필드의 길이 기준, 최종 파일 해시에 연결된 렌더 증거, 신규 작성의 실제 쪽수/서식 조건을 다룬다. FAIL을 삭제하거나 자기 결과로 기준을 재설정해 통과시키는 방식은 피한다.
- **실행 예시와 공통 진입점을 정리한다.** 반복된 lint 인수 오류와 기안문 생성 경로의 분산을 줄이는 방향이 우선이다. 이 배치에서는 개선 코드를 적용하지 않았다.

## 검증 상태를 해석할 때

5건 모두 구조·실열림·실제 렌더·최종 공문 규칙 검사를 통과했다. 다만 **5건 모두 전체 필수 파이프라인 완료본이라고 표시하지 않았다.** 새 문서 기준 부재, 예산 FAIL, 업무지침 미확인 등을 각각 보존했다.

관련번호·통신문 번호 미부여, 이의신청 방법 미제공, 본체만 생성해 실제 붙임이 없는 상태는 입력·시험 범위다. 이를 사실 오류로 세지 않았다. 사용자 검토 점수와 발송 승인도 새로 만들지 않았다. 각 작성 세션의 원문 PDF 비교는 자료 형식의 영향을 받으므로, 여기의 판단은 별도로 보관한 **output 최종본**과의 비교를 기준으로 했다.

## 결과 파일

{chr(10).join(links)}

시험 부산물은 `tmp/astra-low-batch-20260912/`에 있다. `selection.json`(추첨·원본 해시), `facts-checks.json`(핵심 사실 대조), `caseNN-comparison.json`(XML 차이), `title-style-comparison.json`(제목 굵기), `draft-layout-observations.json`(PDF 좌표), `baseline-results.json` 및 각 case의 검사 로그/PNG가 증거다.

원본 최종본 5개와 사전 기록한 지침·도구·양식 {len(selection['source_hashes'])}개 해시는 모두 불변이다. 새 HWPX와 보고서는 output 및 OneDrive 작업 보고용에 보관했다.

**발송 전 한글로 열어 확인해주세요.** 이번 결과는 재현 시험의 검토초안이며 실제 발송용 내용 확정·사람 검토는 별도다.
'''
dest_report=OUT/'Astra_low_무작위5건_비교결과.md'
if dest_report.exists():raise SystemExit('Final report already exists')
dest_report.write_text(report,encoding='utf-8')
onedrive=Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용/astra-low-batch-20260912')
onedrive.mkdir(parents=True,exist_ok=True)
copies=[]
for f in sorted(OUT.rglob('*')):
    if not f.is_file() or f.suffix not in ('.hwpx','.md'):continue
    target=onedrive/f.relative_to(OUT); target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if sha(target)!=sha(f):raise SystemExit('Refuse conflicting OneDrive overwrite: '+str(target))
    else:shutil.copy2(f,target)
    assert sha(f)==sha(target)
    copies.append({'source':str(f),'destination':str(target),'sha256':sha(f)})
result={'finished_at':datetime.now().astimezone().isoformat(),'configured_model':'gpt-6-astra','reasoning_effort':'low',
 'generated':5,'rendered_one_page':5,'core_fact_checks':check_count,'core_fact_failures':0,
 'visual_findings':observations,'source_changes':source_changes,'baseline_changes':baseline_changes,
 'copies':copies,'report':str(dest_report),'parent_generation_quality_corrections':0,'mid_batch_tool_or_skill_changes':0}
(WORK/'batch-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps({'ts':result['finished_at'],'agent':'codex-parent','action':'astra_low_random_batch_review','target':str(dest_report),
      'result':'five_generated_content_matches_four_typographic_differences','detail':{'seed':selection['seed'],'cases':5,'fact_checks':check_count,
      'originals_unchanged':True,'mid_batch_fixes':0,'user_score_created':False,'evidence':str(WORK/'batch-result.json')}},ensure_ascii=False)+'\n')
print(json.dumps({'report':str(dest_report),'copied_files':len(copies),'facts':check_count,'source_changes':source_changes},ensure_ascii=False))
