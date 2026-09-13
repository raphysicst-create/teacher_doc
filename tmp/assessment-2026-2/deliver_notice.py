from pathlib import Path
import json,hashlib,shutil,datetime
w=Path(__file__).resolve().parent;root=w.parents[1]
out=root/'output/2026학년도_2학기_평가계획_가정통신문'
cloud=Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용/2026학년도_2학기_평가계획_가정통신문')
out.mkdir(exist_ok=True);cloud.mkdir(exist_ok=True)
name='2026학년도_2학기_평가계획_가정통신문_검토본'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report='''# 2026학년도 2학기 평가계획 가정통신문 — 검토 보고

상태: HWPX·PDF 제작 및 기술 검증 완료, 문서번호·배부일 기입과 최종 사람 검토 대기. 발송하지 않음.

## 반영 내용
- 사용자 승인: 초안 제시 후 “작성해줘”. 승인 초안 해시와 원문 기록은 작업 폴더 approval.json에 보존.
- 1회고사 2026. 10. 27. ~ 2026. 10. 28., 2회고사 2026. 12. 7. ~ 2026. 12. 8.
- reference의 1·2학년 2학기 교수학습 및 평가계획을 반영. 1학년 자유학기 평가와 2학년 고사·수행평가를 구분.
- 승인 초안의 표 값 84개 전수 대조 일치. 수학·미술·체육(1학년)은 원문 미기재 영역별 비율을 만들지 않음.
- 문서번호는 머리말의 “화동중 제2026-  호” 공란, 배부일은 [[배부일]] 유지. 문서번호의 긴 플레이스홀더는 머리말 폭에 맞춰 공란으로 표시했으며 번호를 추정하지 않음.

## 구조와 검증
- 기존 2956 첨부의 학교 머리말·서체·A4 용지를 이용. 승인 초안의 학년별 2개 표로 재구성하고 두 표의 전체 폭은 원래 평가표 폭 47185 HWPUNIT 유지. 원본·결과 모두 한글 실측 1쪽.
- 최초 변환 양식은 container.rdf·Preview 누락 및 mimetype 순서/압축 오류가 있어 한글의 다른 이름 저장으로 정상 패키지 복구. 원본은 수정하지 않음.
- validate: 최소 패키지·XML 구조 통과. fix_namespaces: 변경 필요 없음. finalize --strip-linesegarray: 완료. validate --layout: 통과, 본문 들여쓰기 관련 휴리스틱 경고 2건(가통 인사말·소제목 배치, 육안 확인).
- 원본 fingerprint 대조: FAIL 보존. 원인은 승인 초안에 따른 24×6 표 → 학년별 12×2·12×5 표 재구성, 본문 문단 재배치, 한글 네이티브 저장의 패키지 복구·XML/ZIP 정규화. 기존 표 위치 예산을 신규 주소에 적용한 비교는 동일 양식 검증으로 볼 수 없음. 학교 로고와 본문 서체·용지·원본 쪽수를 시각 대조.
- 구조 변경 경로: finalize 완료 후 신규 budget·structure 프로파일을 기록하고 page_guard 통과. 이는 원본 구조와 동일하다는 뜻이 아니며 후속 편집의 기준임.
- finalize --hancom: 통과. 한글 작업 프로세스 종료 확인.
- render_check: 첫 검사 텍스트 순서 86%로 실패. 표를 본문 흐름으로 배치하여 수정한 뒤 두 번째 검사 PASS. 원본/결과 1쪽, 텍스트 앵커 발견 100%, 순서 정합 97.7%, 역순·개체 잔재 없음. 세 번째 시도 없음.
- PDF를 PNG로 렌더하여 직접 판독: 1쪽, 모든 과목·영역 보임, 셀 잘림·겹침 없음, 날짜·학교장 명의 맨 아래 확인. 글자 크기 임의 축소 없음.
- gonmun_lint: 위반 0건. content_guard: 옛 학기·날짜·문서번호·행사명 및 필수 값 검사 통과. 명시적 [[...]] 검사는 [[배부일]] 1건 검출(사용자 미제공으로 예상된 정상 상태, 전체 완료 상태로 숨기지 않음).
- kordoc compare_documents 신구대조 완료, 신구대조.md 동봉.
- 본문 기안문·붙임·예산·관련번호·수업 대체는 이번 가정통신문 범위에 없어 해당 검사 적용 대상 아님.

## 근거 상태
school_task_guide의 assessment.plan은 partial, 확정 0·보류 11개. HOLD-GW-ASSESS-SCOPE·설립구분 적용 범위 미확인·추출 품질 미확인 보존. 확정 의무로 바꾸지 않음. 지침 PDF 13~14쪽의 자유학기 평가와 학기 초 공개·변경 시 안내 원문 확인. 2026-09-07 공식 첨부 일치, 2026-03-01 시행 확인, 종료일 미명시, 이후 별도 공문 전수 확인 아님.

## 작업 이력
초기 읽기/복사 명령은 보호 훅의 정적 경로 판별로 차단되어 실행되지 않음. 원본을 읽는 analyze_template 정식 추출 명령으로 진행. 지침·훅 변경 없음. 작업용 생성 스크립트의 속성 갱신 오류 1회 수정. 첫 native 생성 전 파일 없음 검사는 완료 근거로 사용하지 않음. 이전 세션의 git 변경을 보존.

발송 전 한글로 열어 확인해주세요. 문서번호와 배부일을 기입하고 최종 검토를 마친 뒤 사람이 발송합니다.
'''
for src,dst in [(w/'final.hwpx',out/(name+'.hwpx')),(w/'final.pdf',out/(name+'.pdf')),(w/'diff.md',out/'신구대조.md')]:
 shutil.copy2(src,dst)
(out/'검토보고.md').write_text(report,encoding='utf-8')
hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}
(out/'파일해시.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2),encoding='utf-8')
for p in out.iterdir():
 if p.is_file():
  shutil.copy2(p,cloud/p.name)
  assert sha(p)==sha(cloud/p.name)
events=[('generation','초안 승인 후 학년별 표 재구성·한글 네이티브 저장'),('validation','초기 패키지 누락 복구; render 순서 86% FAIL → 수정 후 97.7% PASS, 1쪽'),('validation','placeholder [[배부일]] 1건은 미제공값으로 유지'),('delivery','output·OneDrive HWPX/PDF/검토보고/신구대조 복사 및 SHA256 일치')]
with (root/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
 for action,detail in events:f.write(json.dumps({'ts':datetime.datetime.now().astimezone().isoformat(),'agent':'codex','action':action,'target':str(out/(name+'.hwpx')),'result':'human_review_pending','detail':detail},ensure_ascii=False)+'\n')
print(json.dumps({'output':str(out),'onedrive':str(cloud),'hashes':hashes},ensure_ascii=False))
