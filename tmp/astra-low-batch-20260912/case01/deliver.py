from pathlib import Path
import hashlib,json,shutil,datetime
r=Path.cwd();w=r/'tmp/astra-low-batch-20260912/case01';o=r/'output/astra-low-batch-20260912/case01';o.mkdir(parents=True,exist_ok=True)
f=w/'2026_2학기_1회고사_출제연수_기안문.hwpx'; sha=hashlib.sha256(f.read_bytes()).hexdigest();prov=json.loads((w/'provenance.json').read_text(encoding='utf8'))
report='''# Astra low 독립 재작성 case01 검증보고

Hwp_doc에서 내부결재 기안문 본체 1개를 새로 생성했다. 모델 설정은 부모가 지정한 gpt-6-astra / low이다. 기존 output·과거 세션·메모리·다른 사례·기대정답은 읽지 않았다. 기존 dirty 변경을 확인하고 보존했다. 사용자는 배치 재작성 실험을 요청했으며 검토 점수와 발송 승인은 만들지 않았다.

## 입력과 선택 근거

요청: 2026학년도 2학기 1회고사 출제 관련 연수. 2026. 10. 8. 13:00, 교무실, 전 교원. 관련 화동중학교-2058(2026. 3. 17.). 붙임 표시는 유지하되 첨부자료는 생성하지 않는 본체 한 파일 시험이다.

knowledge/examples/index.md 검색 후 3206_출제관련연수.md 및 원본 PDF를 읽고, knowledge/templates/본문-내부결재.md 실시형을 선택했다. 같은 유형의 편집 가능한 HWPX 본문은 발견하지 못했으므로 gonmun XML 신규 생성 경로를 사용했다. 기관명·수신·경유·제목·관련·2항·가나다 항·붙임 순서를 보존했다. 전자결재 원본 PDF의 로고·결재선·하단 연락처와 제목 밑줄은 생성하지 않았다. 따라서 원본 PDF의 시각적 완전 복제라고 판정하지 않는다.

실제 읽은 지침: 프로젝트 CLAUDE.md, .claude/skills/hwpx/SKILL.md 정본, references/xml-authoring.md, docs/업무지침-MCP-연결.md. 성립전예산요구 README도 후보 조사 때 읽었으나 다른 업무 양식이므로 쓰지 않았다. 스킬·코드·양식은 수정하지 않았다. 고정 Python312만 사용했다.

## 업무 지침 및 초안

find_tasks → get_task_guide → search_task_evidence → read_evidence를 호출했다. assessment.plan 안내는 partial, 확정 0/미확정 11, HOLD-GW-ASSESS-SCOPE와 설립구분 범위 미확인 및 추출 품질 경고가 있다. 2026 강원 중학교 학업성적관리시행지침 PDF 14~17쪽 문맥을 읽었다. 2026-09-07 판본 일치 확인은 있으나 이후 공문 전수 확인은 아니다. 해당 경고는 task_evidence.json에 보존했다. 광범위 검색의 전체 32,189건을 순회하지 않고 관련 상위 2건과 전후 문맥 4개를 읽었다(해당 read_evidence 결과 has_more=false).

원문 15쪽은 평가 실시 전 행정실직원을 포함한 교직원 연수를 언급한다. 요청한 대상은 전 교원이므로 본문은 요청 그대로 두며 행정실직원 포함 여부를 검토점으로 남긴다. 업무 안내의 보류 항목을 확정 의무로 바꾸지 않았다. related_lookup --doc 2058이 2026. 3. 17.을 확인했다.

초안은 draft.md에 있다. 초안 파일은 검색/원문 확인 완료 전에 미리 기록되었고, 원문 확인 후 동일 문안을 채택했다. 이는 초안 작성 전 원문 확인 순서와 어긋난 과정상 한계로 기록한다. 생성 승인은 사용자의 독립 재작성 배치 요청 범위이며 새 발언을 만들어 넣지 않았다.

## 검사 결과

| 단계 | 결과 |
|---|---|
| build_hwpx | PASS |
| validate / 11개 최소 패키지·XML | PASS |
| fix_namespaces | PASS, 변경 0 |
| finalize --strip-linesegarray | PASS, 제거 0 |
| validate --layout | PASS + body_paragraph_without_visible_indent 경고 1 |
| page_guard | 미실행. 동일 유형 기준 HWPX가 없어 비교 기준을 임의 생성하거나 결과물로 재설정하지 않음. 전체 필수 파이프라인 통과로 판정하지 않음 |
| finalize --hancom | PASS, 부모 COM 독점 허가 후 실행 |
| render_check | PASS, 1쪽, 앵커 8개, 발견비율·순서 정합 1.0 |
| PDF 육안 | 원본 1쪽/결과 1쪽, 잘림 없음. 기관명·본문 굴림, 본문 12pt. 로고·제목 밑줄·하단 전자결재 정보 차이 있음 |
| gonmun_lint | PASS, 위반 0. 요일을 입력하지 않아 DATE_WEEKDAY 대조 대상 없음 |
| content_guard | PASS, 1학기·옛 4월 날짜 및 다른 업무 명칭 잔재 없음 |
| 붙임 수 | 표시 1/생성 첨부 0: 사용자 지정 시험 범위에 따른 의도된 불일치 |
| kordoc compare_documents | 실행, 추가 8/삭제 4/동일 2. PDF 파싱이 본문을 표로 묶어 세밀한 텍스트 diff에는 한계 |
| 잔존 Hwp 프로세스 | 없음 확인 후 부모에게 COM 반납 |

같은 검사 단계의 재시도는 없었다. 파일 읽기 1회 경로 오기(gonmun/Contents/section0.xml)는 실제 gonmun/section0.xml로 바로잡았다. 원본 PDF PNG 읽기용 스크립트 생성 명령은 자동 보호 훅이 정적 경로 구분 불가로 1회 차단했다. 파일 쓰기를 case01 스크립트 파일에 명시적으로 분리해 apply_patch로 작성하고, 원본은 읽기만 하는 방식으로 실행했다. 구조나 보호 규칙을 변경하지 않았다.

## 전달 및 사람 검토

output/astra-low-batch-20260912/case01 및 OneDrive 작업 보고용/astra-low-batch-20260912/case01에 본체와 이 보고서를 복사한다. PDF/PNG·검사 로그·입력 해시·전체 지침 응답은 tmp의 작업 부산물이다. 전체 필수 검사 완료로 표시하지 않으며 발송 상태는 검토 대기다.

발송 전 한글로 열어 확인해주세요. 대상에 행정실직원을 포함할지, 기안문 제목·본문 배치와 붙임 표시를 확인해야 한다.

'''
report+='최종 HWPX SHA-256: `'+sha+'`\n\n초안 SHA-256: `'+prov['draft_sha256']+'`\n\n입력 SHA-256: `'+prov['request_sha256']+'`\n\n지침 해시:\n'
for k,v in prov['instructions'].items():report+='- '+k+': `'+v+'`\n'
(w/'검증보고.md').write_text(report,encoding='utf8')
cloud=Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용/astra-low-batch-20260912/case01');cloud.mkdir(parents=True,exist_ok=True)
for p in [f,w/'검증보고.md']:
 shutil.copy2(p,o/p.name);shutil.copy2(p,cloud/p.name)
 assert hashlib.sha256((o/p.name).read_bytes()).hexdigest()==hashlib.sha256((cloud/p.name).read_bytes()).hexdigest()
for action in ['parse','draft','hancom','render_check','deliver']:
 with (r/'logs/audit.jsonl').open('a',encoding='utf8') as a:a.write(json.dumps({'ts':datetime.datetime.now().isoformat(),'agent':'astra-low-case01','action':action,'target':str(o/f.name),'result':'completed_with_limitations','detail':'case01; 후속 정리 기록; page_guard 미실행, 상세 tmp/검증보고.md; sha256='+sha},ensure_ascii=False)+'\n')
print(o/f.name);print(sha);print('OneDrive identical')
