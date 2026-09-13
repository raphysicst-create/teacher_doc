from pathlib import Path
import hashlib,json,subprocess,datetime,shutil
R=Path('C:/Users/22/Desktop/maintain/Hwp_doc');T=R/'tmp/astra-low-batch-20260912/case05';D=R/'output/astra-low-batch-20260912/case05';D.mkdir(parents=True,exist_ok=True)
P='C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe'
r=subprocess.run([P,'-X','utf8',str(R/'.claude/skills/hwpx/scripts/gonmun_lint.py'),'--hwpx',str(T/'case05.hwpx'),'--format','text'],capture_output=True,text=True,encoding='utf-8')
(T/'gonmun_lint-retry.log').write_text(r.stdout+r.stderr,encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
h=sha(T/'case05.hwpx'); prov=json.loads((T/'provenance.json').read_text(encoding='utf-8'))
report=f'''# case05 독립 재작성 검증보고

Hwp_doc에서 2026학년도 2학기 2회고사 안내 가정통신문 본체를 작성했다. **검토 초안**이며 전체 필수 검증 통과로 판정하지 않는다. 기안문·발송·검토 점수 기록은 없다.

- 실행 설정: gpt-6-astra / reasoning_effort low (astra-light 시험의 전달된 실행 설정).
- 권한 근거: 사용자의 “이 실험 astra-light 수준으로 5건 정도 랜덤 배치로 돌려서 기존 ouput 폴더의 최종 산출물들처럼 나오는지 확인해줘”. request.md 입력을 재작성하는 시험 범위. 새 초안 승인 발언은 만들지 않았다.
- 입력 SHA-256: `{prov['request_sha256']}`
- 최종 값 매핑 SHA-256: `{sha(T/'values.json')}`
- 최종 HWPX SHA-256: `{h}`
- 작업 전 git dirty 확인: 훅·스킬·CLAUDE.md·로그 등 기존 변경 있음. 기존 변경은 수정하지 않았다.
- 기존 output·타 case·selection·eval 정답·과거 세션은 열람하지 않았다.

## 양식 선택과 초안

knowledge/examples/index.md → 3306_1학기1회고사가통배부.md → knowledge/templates/가정통신문-고사안내/README.md를 확인했다. 베이스는 `knowledge/templates/가정통신문-고사안내/양식.hwpx`이며 3306 변환/재패키징 계보이므로 render_check를 적용했다. hwpx_slots.py로 189개 슬롯을 직접 추출했다.

제목 강조, 상단 학교 헤더, 시간표, 과목×학년 출제범위 표의 행·열·병합·순서, 하단 날짜·명의를 보존했다. 1학년 칸은 삭제하지 않았으며 시간표 ‘수업’과 본문의 ‘자유학기로 지필고사 없이 양일 정상수업’으로 의미를 함께 표시했다. 2학년 하교는 본문의 중식 후 하교와 연결했다. 1학년 출제정보는 ‘미실시’, 구조상 원래 사선 셀은 보존했다. 행·열 구조 변경 승인은 요청하거나 꾸미지 않았다. 필요하면 미응시 학년·과목 칸은 사용자가 직접 지워도 된다.

초안은 tmp/astra-low-batch-20260912/case05/draft.md, 최종 값은 같은 폴더 values.json. 초안에서 1학년 수학 문항수의 ‘미실시’ 중복을 발견해 두 번째 문단 텍스트만 비웠다. 기능 코드·템플릿 수정 없음.

## 업무 지침 근거

find_tasks → get_task_guide(assessment.plan) → search_task_evidence → read_evidence를 호출했다. 상세 응답은 task-guide.json에 보존했다. 안내 상태 **partial**, 확정 0개·검토/조건 미확정 11개, HOLD-GW-ASSESS-SCOPE와 설립구분 적용 범위 미확인을 유지했다. 공식 게시물과 등록 파일 일치 확인일은 2026-09-07이며 이후 별도 공문 전수 확인은 아니다. 품질 미검토 경고도 유지한다.

2026 강원 중학교 학업성적관리 시행지침 PDF 39쪽의 이의신청 예시는 기간을 학교별 자율 결정하고 학교가 정한 방법으로 신청하도록 한다. 이번 입력의 12. 9.~12. 12. 기간을 그대로 보존했으며 신청 방법은 미제공이라 창작하지 않았다. pending 안내를 확정 의무로 승격하거나 제공된 시험 비율을 지침의 학기말 비율로 바꾸지 않았다. 본체에 예산·관련번호·붙임 없음으로 해당 검사는 비대상이다.

## 검사 및 재시도

| 단계 | 결과 | 근거/제한 |
|---|---|---|
| 첫 edit | FAIL | 번호 13/12자, 배부일 11/10자. 번호를 ‘통신문 번호 미부여’로 표현 수정 |
| 미검증 사본 | 생성 | 정본 편집 모듈의 원시 ZIP 보존 함수로 렌더 전용 사본, 승인 플래그 미사용 |
| validate | PASS | 최초/최종 구조 및 11개 최소 패키지 검사 |
| fix_namespaces | PASS | 변경 0 XML |
| finalize --strip-linesegarray | PASS | 최종 57개 제거 |
| validate --layout | PASS + WARNING | 본문 들여쓰기 경고 1건 |
| 기준 프로파일 | 생성 | 원본 사본 finalize 후 budget/structure 생성, 결과물로 기준 재설정 안 함 |
| page_guard | **FAIL 2회** | p:113 날짜 11자 > 원본 예산10자. 2회 후 중단, FAIL 유지 |
| 한글 COM | PASS | 미검증 사본 및 최종 실열림 |
| render_check | PASS | 원본1쪽=최종1쪽, anchors_found 1.0, order_lis 0.917 |
| PDF→PNG 판독 | PASS | 원본과 최종의 제목/상자/표/명의 비교, 날짜 한 줄·잘림 없음 |
| 정식 edit CLI | PASS + WARNING | 실렌더 판독 후 --allow-over-budget --verified-by-render 적용. p:113 11/10자 경고 보존 |
| gonmun_lint | PASS | 최초 인자 오류 1회, --hwpx로 정정하여 위반0건(error0, warning0), exit {r.returncode} |
| content_guard | **예상 FAIL** | ‘미부여’ placeholder 2곳. 이전 고사명/번호/날짜 잔재 및 필수값 검사 이상 없음 |
| 신구대조 | 완료 | kordoc compare_documents, diff.md에 보존 |

날짜 요일은 fusion_timetable.py 계산 12/7 월·12/8 화를 사용했고 gonmun_lint로 검사했다. 기초시간표의 과목을 시험 시간표에 대입하지 않았다. 한글 COM은 부모의 독점 허가 후 직렬 실행하고 종료 시 Hwp 프로세스 없음을 확인해 반납했다. 최종 PNG는 최종 편집 후 다시 렌더하여 직접 판독했다.

## 사람이 확인할 사항

통신문 번호를 부여하고 이의신청 방법을 정해 안내에 반영해야 한다. 기간은 사용자가 정한 시험값(12. 9.~12. 12.) 그대로다. 날짜 예산 초과는 육안상 정상이나 page_guard의 필수 FAIL을 숨기지 않았다. **발송 전 한글로 열어 확인해주세요.**

## 실제 읽은 지침 해시

'''
for p,x in prov['instructions'].items():report+=f'- `{p}`: `{x}`\n'
(D/'검증보고.md').write_text(report,encoding='utf-8')
dest=D/'2026학년도_2학기_2회고사_안내_검토초안.hwpx';shutil.copy2(T/'case05.hwpx',dest)
OD=Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용')
odhw=OD/'astra-low-case05_2026학년도_2학기_2회고사_안내_검토초안.hwpx';odmd=OD/'astra-low-case05_검증보고.md'
shutil.copy2(dest,odhw);shutil.copy2(D/'검증보고.md',odmd)
assert sha(dest)==h==sha(odhw)
with (R/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
 f.write(json.dumps(dict(ts=datetime.datetime.now().isoformat(),agent='astra-low-case05',action='deliver_review_draft',target=str(dest),result='partial',detail={'sha256':h,'onedrive':str(odhw),'page_guard':'FAIL date budget','content_guard':'FAIL unassigned number','gonmun_lint_exit':r.returncode}),ensure_ascii=False)+'\n')
print(dest);print(h);print('OneDrive identical:',sha(odhw)==h)
