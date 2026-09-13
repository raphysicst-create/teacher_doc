from pathlib import Path
import json,hashlib,shutil,datetime
r=Path(__file__).resolve().parents[3];t=Path(__file__).resolve().parent
out=r/'output/astra-low-batch-20260912/case02';out.mkdir(parents=True,exist_ok=True)
f=out/'2026_2학기_교과별평가계획수립_기안문_검토초안.hwpx';shutil.copy2(t/'result.hwpx',f)
proof=json.loads((t/'provenance.json').read_text(encoding='utf-8'))
report='''# case02 독립 재작성 검증보고서

Hwp_doc에서 2026학년도 화동중학교 2학기 교과별 평가계획 수립 기안문 본체를 작성했다. 모델 gpt-6-astra, reasoning low. 전체 검증 통과가 아닌 검토 초안이다.

## 근거와 승인 범위
실제 사용자 요청: “이 실험 astra-light 수준으로 5건 정도 랜덤 배치로 돌려서 기존 ouput 폴더의 최종 산출물들처럼 나오는지 확인해줘”. 배정 request.md의 동일 입력 재작성으로 해석했다. 새 승인 발언, 평가점수, 발송 기록은 생성하지 않았다.
knowledge/examples/index.md에서 2861 동일 업무 예시와 본문-내부결재.md를 확인했다. 베이스는 knowledge/templates/성립전예산요구/양식.hwpx로 기관명·수신·경유·제목·관련·본문·붙임 공통 배치를 보존했다. 공문용 굴림 12pt 양식이다. 원본/코드/스킬/기존 dirty 변경은 수정하지 않았다.
related_lookup --doc 2058로 화동중학교-2058(2026. 3. 17.)와 시행 문서 제목을 확인했다. 학교 학업성적관리규정 원문도 kordoc으로 읽었다. 교과협의회 수립·학업성적관리위원회 심의·학교장 결정 및 평가계획 공시/안내 조건이 있으나 이번 입력에 이행 증빙은 없으므로 완료로 단정하지 않았다. school_task_guide find_tasks는 120초 timeout, 후속 3단계는 미실행. 등록 지침 최신판/적용기간 확인은 미확인이다.

## 검사 결과
| 단계 | 결과 |
|---|---|
| validate / fix_namespaces / finalize / layout | PASS. namespace 변경0, 캐시 제거0. layout 승계 경고 body_paragraph_without_visible_indent 1건 |
| page_guard | FAIL 2회(미검증 사본, 최종). p9 예산54→59, p11 예산30→72. 추가 재시도 중단; 기준 재설정 없음 |
| 한컴 실열림 | PASS |
| render_check | PASS, 산출1쪽/베이스1쪽, anchors=1.0, order=1.0 |
| PDF→PNG 육안 | 1쪽, 잘림/겹침 없음. 붙임 둘째 항 앞 공백을 6→2→0으로 두 차례 조정하여 끝. 분리 해결. 번호 들여쓰기가 첫 항과 다르므로 사람 검토 필요 |
| content_guard | PASS. 원 사업명·정책기획과-3100·2025. 3. 19.·1학기 잔재 없음, 필수 관련/학년/학기 확인 |
| gonmun_lint | 위반0 |
| kordoc compare_documents | 수행. 2861 PDF 대비 추가5/삭제4/동일2. PDF 본문이 표/이미지 블록이어서 문장별 정밀 대조에는 한계. 1학기→2학기, 관련 자교1건, 붙임명 2026학년도 적용은 수동 대조 |
| 붙임 수 | 표시2, 생성0. 사용자 요청이 기안문 본체만이므로 의도된 범위. 실사용 시 첨부2건 연결 필요 |

첫 edit_hwpx 실행은 위 문단 예산 초과로 실패했다. 스킬의 미검증 사본 렌더 경로로 원시 ZIP 보존 편집 API를 사용해 사본을 만들고 실제 PNG 판독 후에만 --allow-over-budget --verified-by-render로 최종 편집했다. 최종 파일과 판독 사본 해시가 일치한다. 예산 WARNING 2건은 유지한다. 보호 훅이 복합 셸 명령의 대상 판별을 거절한 실행들은 분리된 명시적 대상 명령/apply_patch로 처리했으며 보호 설정 변경은 하지 않았다.

COM은 부모의 독점 허가 후만 실행했다. 완료 후 잔존 Hwp 프로세스 없음 확인 및 반납했다.

발송 전 한글로 열어 확인해주세요. 특히 붙임 둘째 항의 들여쓰기와 첨부 연결, 지침/심의 이행 여부를 확인해 주세요.

## 실제 로딩 지침 및 입력 해시
'''
for p,h in proof['hashes'].items():report+=f'- {p}: `{h}`\n'
report+='\n최종 HWPX SHA-256: `'+hashlib.sha256(f.read_bytes()).hexdigest()+'`\n'
report+='\n최종 values.json SHA-256: `'+hashlib.sha256((t/'values.json').read_bytes()).hexdigest()+'`\n'
(out/'검증보고서.md').write_text(report,encoding='utf-8')
dest=Path('C:/Users/22/OneDrive - 화동중학교/작업 보고용/astra-low-batch-20260912/case02');dest.mkdir(parents=True,exist_ok=True)
for p in [f,out/'검증보고서.md']:shutil.copy2(p,dest/p.name)
with (r/'logs/audit.jsonl').open('a',encoding='utf-8') as a:
 for act,res,detail in [('parse','ok','2861/2058 예시와 학업성적관리규정 kordoc 확인'),('guide','error','find_tasks timeout 120s 후속 미실행'),('draft','ok','사용자 시험 요청에 의한 재작성; 초안/입력 해시 기록'),('generate','warning','문단 예산초과1회 실패; 미검증 렌더 후 최종 CLI 편집'),('validate','partial','page_guard 예산초과2회 FAIL 유지; 기타 구조/COM/render/content/lint PASS'),('deliver','draft','output 및 OneDrive 복사; 미발송')]:
  a.write(json.dumps({'ts':datetime.datetime.now().astimezone().isoformat(),'agent':'astra-low-case02','action':act,'target':str(f),'result':res,'detail':detail},ensure_ascii=False)+'\n')
print(str(f));print(str(dest));print(hashlib.sha256(f.read_bytes()).hexdigest())
