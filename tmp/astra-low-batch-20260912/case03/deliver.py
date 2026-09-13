from pathlib import Path
import json,hashlib,shutil,datetime,difflib
W=Path(__file__).parent;R=W.resolve().parents[2]; O=R/'output/astra-low-batch-20260912/case03';O.mkdir(parents=True,exist_ok=True)
f=O/'case03_2026학년도_2학기_1회고사_가정통신문_배부_검토초안.hwpx';shutil.copy2(W/'result.hwpx',f)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rec=json.loads((W/'input-record.json').read_text(encoding='utf-8'))
diff=''.join(difflib.unified_diff((R/'knowledge/templates/본문-가정통신문배부.md').read_text(encoding='utf-8').splitlines(True),(W/'draft.md').read_text(encoding='utf-8').splitlines(True),fromfile='본문-가정통신문배부.md',tofile='draft.md'));(W/'text-diff.md').write_text(diff,encoding='utf-8')
report=f'''# case03 독립 재작성 검증 보고

상태: **미확인 값이 있는 검토 초안**. 전체 필수검증 통과로 판정하지 않는다. 본체 HWPX만 만들었으며 발송·사용자 검토 승인·점수 기록 없음.

- 실제 모델/설정: gpt-6-astra / low (부모 배치 지정).
- 실제 사용자 권한 근거: “{rec['authorization']}”. 독립 재작성 시험 생성 권한이며 새로운 문안 승인 발언을 만들지 않았다.
- 입력 SHA256: `{rec['request_sha256']}`
- 초안 SHA256: `{rec['draft_sha256']}` (tmp/astra-low-batch-20260912/case03/draft.md)
- 직접 읽은 지침: `{json.dumps(rec['instruction_hashes'],ensure_ascii=False)}`
- 시작 git status에 기존 지침·훅·로그·스크립트 등의 dirty 변경 존재. 변경하지 않음.

선택 근거: knowledge/examples/index.md의 가정통신문 배부 매핑을 따라 knowledge/templates/본문-가정통신문배부.md와 examples/md/3306_1학기1회고사가통배부.md 및 7685_2학기1회고사가통.md를 읽었다. 본체 예시가 PDF/MD이므로 별도 HWPX 원본 편집 없이 hwpx 정본의 XML-first build_hwpx.py --template gonmun 경로를 사용했다. 기관명·수신·경유·제목·관련·배부 본문·붙임의 순서를 유지했다. 전체 서체 굴림, 본문 12pt, 기관명 22pt. 기존 최종 output/타 case/정답/메모리는 읽지 않았다.

| 단계 | 결과 및 한계 |
|---|---|
| 업무 근거 조회 | find_tasks(중학교 고사 가정통신문 배부) 120초 timeout 1회. get_task_guide/search_task_evidence/read_evidence 미실행. 연결 오류 후 확인된 학교 예시·스켈레톤 사용. 최신 지침 확인 미완료 |
| 관련번호 | related_lookup --search '2026학년도 2학기 1회고사' exit1. 화동중학교-[[문서번호 확인 후 기재]]([[시행일 확인 후 기재]]) 유지. 이전 3205·7341을 가져오지 않음 |
| 초안/생성 | 초안·입력해시 기록 후 신규 XML build PASS. 구조변경 승인 발언 없음; 기존 HWPX 구조를 편집한 작업 아님 |
| validate | PASS, 최소 패키지 및 구조 |
| fix_namespaces | PASS, 변경 0개 |
| finalize --strip-linesegarray | PASS |
| validate --layout | PASS + body_paragraph_without_visible_indent 경고 1건. 본문 1./2. 항목은 이미지에서 확인 |
| page_guard | 자기 자신 reference 비교 명령 PASS이나 독립된 참조 비교가 아니므로 양식보존 증거로 인정하지 않음. HWPX 참조 없는 신규 문서로 비교 검증 제한. COM 1쪽은 별도 확인 |
| finalize --hancom | PASS. 부모 COM 허가 후 직렬 실행, 종료 후 Hwp 잔존 없음 |
| render_check | PASS, 1쪽, anchors 5/5, order_lis_ratio 1.0. PDF→PNG 직접 판독: 기관명·제목·문단·붙임 모두 표시, 잘림 없음 |
| content_guard | 원문잔재 및 필수문구 검사 PASS. 추가 [[...]] placeholder 정규식 검사 **FAIL**: 미제공 번호/시행일을 보존한 예상된 정상 상태 |
| gonmun_lint | 최초 CLI positional 인자 오류(exit2) 후 --hwpx로 1회 수정 실행 PASS(0 findings). 총 2회 |
| 붙임 개수 | 표시 1부 / 실제 파일 0건. 본체만 만드는 명시적 시험 범위; 발송 시 실제 붙임 필요 |
| 신구대조 | HWPX 원본 없음. kordoc 미사용. 스켈레톤→초안 텍스트 diff를 작업 폴더에 기록 |
| 예산/시간표 | 해당 없음 |

최종 파일: `{f}`

최종 SHA256: `{sha(f)}`

OneDrive 작업 보고용에 같은 이름의 HWPX와 이 보고서를 복사하고 해시를 대조했다. 관련번호·시행일과 실제 붙임을 사람이 확인해야 한다. **발송 전 한글로 열어 확인해주세요.**

Hwp_doc 프로젝트에서 case03 고사 가정통신문 배부 기안문 본체를 독립 생성하고 검토 초안으로 전달했다.
'''
rp=O/'case03_검증보고.md';rp.write_text(report,encoding='utf-8')
dest=Path(r'C:\Users\22\OneDrive - 화동중학교\작업 보고용')
for p in [f,rp]:
 shutil.copy2(p,dest/p.name);assert sha(p)==sha(dest/p.name)
with (R/'logs/audit.jsonl').open('a',encoding='utf-8') as a:a.write(json.dumps(dict(ts=datetime.datetime.now().isoformat(),agent='astra-low-case03',action='deliver',target=str(f),result='DRAFT',detail={'sha256':sha(f),'COM':'PASS','render':'PASS 1page','content_guard':'expected placeholder FAIL','OneDrive':'hash identical'}),ensure_ascii=False)+'\n')
print(f);print(rp);print(sha(f))
