from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import json,hashlib,shutil,subprocess,sys
from datetime import datetime
W=Path(__file__).resolve().parent
R=W.parents[1]
O=R/'output/fresh-notice-reproduction-20260912'
F=O/'2026학년도_2학기_1회고사_안내_검토초안.hwpx'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ns={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph'}
root=etree.fromstring(ZipFile(F).read('Contents/section0.xml'))
ps=root.findall('.//hp:p',ns)
vals=json.loads((W/'values.json').read_text(encoding='utf-8'))
def txt(el):return ''.join(el.itertext()).strip()
tables=root.findall('.//hp:tbl',ns)
checks=[]
for key,want in vals.items():
    parts=key.split(':')
    if parts[0]=='p': got=txt(ps[int(parts[1])])
    else:
        ti,row,col=map(int,parts[1:])
        cell=next(tc for tc in tables[ti].findall('./hp:tr/hp:tc',ns) if tc.find('hp:cellAddr',ns).get('rowAddr')==str(row) and tc.find('hp:cellAddr',ns).get('colAddr')==str(col))
        got=txt(cell)
    checks.append({'key':key,'expected':want,'actual':got,'pass':got==want})
assert all(c['pass'] for c in checks),[c for c in checks if not c['pass']]
(W/'final-value-check.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
assert sha(R/'knowledge/templates/가정통신문-고사안내/양식.hwpx')=='c3586a7b0364cc711951b0697837c70369462397ad58f2d25a7c066d7855dae1'
lint=subprocess.run([sys.executable,'-X','utf8',str(R/'.claude/skills/hwpx/scripts/gonmun_lint.py'),'--hwpx',str(F),'--format','json'],capture_output=True,text=True,encoding='utf-8')
(W/'10_gonmun_corrected.log').write_text(lint.stdout+lint.stderr,encoding='utf-8')
assert lint.returncode==0
report=f'''# 독립 세션 가정통신문 재작성 시험 결과

Hwp_doc에서 요청 사실을 새로 입력해 고사 안내 HWPX 검토초안 1건을 만들었다. 내용과 기존 양식은 재현되었고 한글에서 원본과 같은 1쪽으로 열렸다. 필수 page_guard에 배부일 글자 예산 FAIL이 남아 전체 Validator 통과본으로 표시하지 않는다.

- 파일: `{F.name}`
- 최종 SHA256: `{sha(F)}`
- 판독한 v2 사본과 최종 파일 SHA256 일치. 최종 PDF도 별도로 내보내 검증했다.
- 사용자가 지정한 통신문번호 미부여를 그대로 표시했다. 관련번호·새 사용자 검토점수·새 발송 기록을 만들지 않았다.

## 실제 확인

| 검사 | 결과 |
|---|---|
| 구조 validate 및 11개 최소 패키지 | PASS |
| fix_namespaces | PASS, 변경 0 |
| finalize·layout | PASS, 기존 본문 들여쓰기 경고 보존 |
| page_guard | FAIL: 배부일 p113 예산 10자 대비 11자 |
| 구조 fingerprint | page_guard에서 구조 변경 위반 없음, 원본 문단 115개·표 3개 유지 |
| 한컴 COM 실열림 | PASS |
| 한컴 PDF 렌더 | PASS, 결과 1쪽·기준 1쪽, 앵커 100%, 순서 0.946 |
| PDF→PNG 육안 판독 | 원본 대비 제목·상자·표 순서·병합·하단 명의 보존, 날짜 및 정상수업 표시 잘림 없음 |
| content_guard | PASS, 과거 학기·고사 날짜·배부일·번호·출제범위 잔재 없음 |
| 입력값 직접 대조 | {len(checks)}개 슬롯값 모두 일치 |
| gonmun_lint | 교정 호출 PASS, 위반 0 |
| kordoc 신구대조 | 추가 0·삭제 0·변경 8·동일 5 |
| 원본 불변 | 양식 SHA256 작업 전후 일치 |

첫 gonmun_lint 호출은 위치 인자 사용 문법 오류(exit 2)로 실행되지 않았다. `--hwpx`로 바로잡은 재호출에서 위반 0을 확인했다. 실패 이력은 삭제하지 않았다.

## 독립 실행과 부모 개입 구분

1. 정본 지침·스킬을 직접 읽고 유사 문서 3306과 2일×4교시 슬롯 양식을 선택했다. 기존 output 결과, 다른 tmp 작업물, 과거 세션·메모리 및 evals 기대 판단을 참고하지 않았다.
2. 최초 기준 사본 복사에서 보호 훅이 정상 Copy-Item을 직접 쓰기로 판정해 2회 차단했다. 지침대로 중단했다.
3. 부모가 안전한 단일 복사를 허용하도록 훅 오탐을 수정하고 재개를 지시했다. 첫 수정 후 재개는 실제 훅 이벤트 명칭 차이로 다시 차단됐다. 부모가 Bash로 전달되는 Windows 이벤트를 반영했다고 보고한 뒤 두 번째 재개에서 복사가 성공했다. 부모의 회귀검사 27건 통과는 부모 보고이며 이 에이전트가 독립 실행한 검사는 아니다.
4. 부모는 초안을 확인하고 실제 사용자 재작성 시험 요청이 기존 확정 사실로 생성하는 범위를 승인한다고 확인했다. 새 사용자 발언을 꾸미거나 최종 검토 승인을 대신 기록하지 않았다.
5. 생성·COM·렌더·내용검사·보고는 이 독립 에이전트가 수행했다. 부모는 최종 COM 완료 후 별도로 이전 결과와 비교한다.

## 작성과 자가교정

베이스는 `knowledge/templates/가정통신문-고사안내/양식.hwpx`이다. 1학년 자유학기 미응시와 양일 정상수업을 인사말에 명시하고 시간표에 정상수업, 출제표에 미응시를 표기했다. 기존 사용자 결정대로 1학년 행 및 사회 열을 삭제하지 않았다. 필요하면 사용자가 해당 행·열을 직접 정리할 수 있다.

첫날 병합된 중식후 행은 `2학년 중식 후 하교`로 표기하여 1학년 정상수업 안내와 충돌하지 않게 했다. 출제범위·선택형/서·논술형 비율·문항수는 요청값을 보존했다.

초회 PDF 대조에서 슬롯 전체문단 치환이 일정·이의신청 소제목의 굵기를 없앤 것을 발견했다. 두 문단은 원래 굵은 표제 런과 보통 날짜 런 각각에서 부분 치환하여 원래 굵기를 복원했다. 수정 후 PDF를 다시 직접 판독했다.

일정·이의신청의 반복 회차 표현을 덜어 `1. 고사 일정`, `3. 이의 신청 기간`으로 썼다. 대상·날짜·요일·2일간 및 배부일은 보존했다.

## 예산 경고와 미확인

렌더 확인 후 최종 편집에서 허용된 입력 길이 경고는 3건이다. 고사 날짜 부분 25→27자, 이의신청 날짜 부분 21→23자, 배부일 10→11자다. 원본 슬롯 프로파일보다 긴 정상수업 셀과 날짜도 실제 PDF에서 확인했다. `--verified-by-render`는 v2 PDF→PNG 판독 뒤에만 사용했고 최종 HWPX 해시가 그 사본과 일치한다.

page_guard의 배부일 FAIL은 그대로 남겼다. 날짜를 줄이거나 출력으로 기준 프로파일을 재설정하지 않았다. 이는 필수 검사 미통과 상태지만, 해당 날짜는 실제 한글에서 한 줄로 정상 표시됨을 확인했다.

업무지침 find_tasks는 not_found였으며 업무 ID가 없어서 규정대로 원문 검색으로 진행했다. search_task_evidence는 partial. read_evidence에서 2026 강원 중학교 학업성적관리 시행지침 39쪽 부록 예시의 학교별 이의신청 기간 자율 결정을 확인했다. 설립구분 미확인·추출품질 경고·2026-09-07 이후 별도 공문 전수 확인 한계를 유지했다. 이의신청 방법은 입력에 없어서 새 절차를 쓰지 않았다.

통신문번호 미부여는 사용자 지정 정상 상태다. 최종 사람 검토·점수·발송은 미실행이다.

## 증거 위치

작업 부산물: `tmp/fresh-notice-reproduction-20260912/`. `environment-and-sources.json`은 실제 환경과 지침·스킬·양식 SHA256, `validation-results.json`은 순서별 명령·결과·전후 해시, `final-value-check.json`은 슬롯값 직접 대조, `evidence-raw.json`은 지침 원문과 경고를 기록한다. `reference-1.png`, `preview-1.png`, `preview-v2-1.png`, `final-1.png`에서 원본·초회·교정·최종 이미지를 확인할 수 있다. `진행보고.md`는 최초 중단 당시 기록이며 이 최종 보고와 구분한다.

발송 전 한글로 열어 확인해주세요.
'''
(O/'재작성_검증보고.md').write_text(report,encoding='utf-8')
dest=Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용/fresh-notice-reproduction-20260912')
dest.mkdir(parents=True,exist_ok=True)
copies=[]
for src in [F,O/'재작성_검증보고.md']:
    target=dest/src.name
    if target.exists(): raise SystemExit(f'Refuse overwrite {target}')
    shutil.copy2(src,target)
    copies.append({'source':str(src),'destination':str(target),'sha256':sha(src),'verified':sha(src)==sha(target)})
(W/'delivery.json').write_text(json.dumps(copies,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'value_checks':len(checks),'final':str(F),'sha256':sha(F),'copies':copies},ensure_ascii=False,indent=2))
