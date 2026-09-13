from pathlib import Path
import datetime, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'tmp/approved-workflow-20260913'
OLD=ROOT/'tmp/remaining-20260913'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=read(RUN/'protected-before.json')
changed=[p for p,d in before.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=d]
assert not changed,changed
rows=[]
for app in ['codex','claude']:
    for flow in ['w1','w2']:
        job='approved-'+flow+'-20260913';ws=OLD/f'{app}-marked'
        key=f'{app}-{flow}-status'+('-current' if app=='codex' and flow=='w1' else '')
        command=read(RUN/'evidence'/f'{key}.json');status=json.loads(command['stdout'])
        assert command['exit_code']==0 and status['status']=='pass' and status['changed_files']==[],status
        out=ws/'output'/job;dest=ws/'approved-test-copy'/job
        hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}
        assert all(d==sha(dest/n) for n,d in hashes.items())
        report=read(ws/'.hwpdoc/jobs'/job/'report.json')
        assert report['delivery']['sent'] is False
        rows.append({'app':'Codex Desktop' if app=='codex' else 'Claude Code CLI 2.1.270','workflow':flow.upper(),
                     'status':status['status'],'copy':'pass','hashes':hashes,'output':str(out/'검증완료_검토대기.hwpx'),
                     'stages':{k:v['status'] for k,v in report['stages'].items()},
                     'paragraph_warning':report['stages']['page_guard'].get('reason','') if flow=='w2' else None,
                     'base_provenance':'unconfirmed; current reviewed registration plus full reference render',
                     'generation_route':'registered slot build' if flow=='w1' else 'manual paragraph edit after actual render receipt; common validation',
                     'sent':False,'final_human_review':'pending'})
same={flow:rows[i]['hashes']['검증완료_검토대기.hwpx']==rows[i+2]['hashes']['검증완료_검토대기.hwpx'] for i,flow in enumerate(['W1','W2'])}
cli=read(RUN/'evidence/claude-actual-cli.json');events=[]
for line in cli['stdout'].splitlines():
    try:events.append(json.loads(line))
    except ValueError:pass
reads=[];model=None;cli_result=None
for event in events:
    if event.get('subtype')=='init':model=event.get('model')
    if event.get('type')=='result':cli_result={k:event.get(k) for k in ['subtype','is_error','result']}
    message=event.get('message',{})
    for block in message.get('content',[]) if isinstance(message,dict) else []:
        if isinstance(block,dict) and block.get('type')=='tool_use' and block.get('name')=='Read':
            path=block.get('input',{}).get('file_path','')
            if path.endswith('.png'):reads.append(path)
assert reads,'No actual Claude image reads found'
summary={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'User-approved synthetic W1 and W2 system-submission drafts; current PC; Codex Desktop and actual Claude CLI. Not all W1/W2 variants or independent reevaluation.',
         'approval':read(RUN/'user-approval.json'),'rows':rows,'same_output_across_apps':same,'protected_count':len(before),'protected_changed':changed,
         'tests':{'runner_contract':20,'paragraph_render_receipt':4},'claude_cli_exit':cli['exit_code'],'claude_model':model,'claude_png_reads':reads,'claude_result':cli_result,
         'evidence_hashes':{p.relative_to(RUN).as_posix():sha(p) for p in (RUN/'evidence').glob('*.json')}}
(RUN/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# W1·W2 승인 후 두 앱 흐름 시험 — 2026. 9. 13.','',
       '사용자가 준비된 W1·W2 시험 초안에 “진행해”라고 확인한 뒤, 문안·배치를 보존해 두 앱에서 생성 → 전체 검증 → 시험 폴더 전달을 수행했다. 실제 발송·시스템 제출·사람의 최종 평점은 실행하지 않았다.','',
       '| 앱 | W1 기능 시험 계획 | W2 시스템 제출 내부결재 | 전달 |','|---|---|---|---|',
       '| Codex Desktop | 통과 | 통과 | 2건·복사 해시 일치 |','| Claude Code CLI 2.1.270 | 통과 | 통과 | 2건·복사 해시 일치 |','',
       f'기존 원본 {len(before)}개가 모두 그대로다. 두 앱의 W1·W2 HWPX도 각각 해시가 동일하다. W2 기한은 **2026. 10. 8.**이며 수신 원문은 가상 평가 자료의 system 변형이다. 다른 W2 제출 분기와 일반/회신형 가정통신문을 이번 4건으로 검증했다고 보지 않는다.','',
       '## 승인·검토 범위','',
       '기준 초안은 `tmp/remaining-20260913/workflow-drafts.md`다. 사용자 원문과 초안 SHA256은 [승인 기록](../tmp/approved-workflow-20260913/user-approval.json)에 보존했다. 기존 기안문 사본의 p:1·3·4·5·7·9·11 매핑과 W1/W2 용도를 사용했다. 표·문단 추가/삭제나 구조 프로파일 재설정은 하지 않았다. 실제 학교 업무지침 조회를 가장하지 않고 고정 시험 원문 확인을 근거로 기록했다. kordoc 미사용: 추출 텍스트 신구대조를 사용했다.','',
       '등록 양식의 원본 유래는 unconfirmed로 보존했다. 현재 해시의 등록 검토를 통과한 같은 양식과 결과물을 실제 렌더로 대조했으며 이를 native 출처 확인으로 바꾸지 않았다.','',
       '## 시험 중 확인·수정한 연결 문제','',
       '1. 출처 유형이 미확인인 양식이 검토·등록을 마쳐도 문서 검증에서 계속 미확인으로 남던 경로를 수정했다. 현재 등록된 동일 양식에 한해 실제 비교 렌더를 필수 실행한다. 등록 없는 미확인 문서는 계속 미확인으로 남는다.','2. W2 관련번호 문단은 공백 제외 **28자 / 기존 예산 27자**다. 문안을 축약하지 않고 미검증 사본을 PDF·PNG로 실제 판독한 뒤 최종 편집했다. 최종 파일과 판독 사본의 해시가 일치한다. 이 판독을 페이지 검사까지 연결하고, 지정 문단 외 예산·셀·구조 검사는 유지했다. 해당 초과는 WARNING으로 남겼다.','',
       '현재 원본·결과물·PDF·PNG 해시, 문단 키와 판독 기록이 모두 맞아야 문단 판독을 적용한다. 소비한 판독 자료도 이후 status의 변경 감지 대상이다. 관련 회귀시험 **24개(실행기 20 + 문단 판독 4)**가 통과했다.','',
       'Codex의 최초 render 미확인 및 W2 page_guard 실패, 시험 보조 명령의 잘못된 옵션·선행 source 누락·수정 중 구문 오류는 evidence에 그대로 보존했다. 같은 문안·작업 ID로 복구했으며 실패를 없애려고 원본·기준 프로파일·기존 평가 기록을 바꾸지 않았다.','',
       '## 산출물','']
for row in rows:
    p=Path(row['output']);lines.append(f"- {row['app']} {row['workflow']}: [시험 HWPX](../{p.relative_to(ROOT).as_posix()})")
lines += ['', '각 output 폴더에는 검토보고서 JSON/Markdown도 있고, 같은 시험 작업 폴더의 approved-test-copy에 3개 파일씩 복사했다. 실제 OneDrive나 제출 시스템에는 전송하지 않았다.','',
          '구조·레이아웃·페이지·COM 실열림·실제 비교 렌더·문안/슬롯·옛 명칭/날짜 잔재·공문 규칙·붙임·신구대조를 확인했다. W2는 가상 수신번호 조회도 통과했다. 예산 항목·시간표는 문안에 해당 내용이 없어 사유를 적어 제외했다.','',
          '사람의 최종 검토는 별도다. 검토본에는 표준 안내 “발송 전 한글로 열어 확인해주세요”가 포함돼 있으나 이번 결과는 발송하지 않는 시험 자료다.','',
          '## 기록','',
          '- [전체 상태·해시·실제 Claude PNG 읽기 기록](../tmp/approved-workflow-20260913/summary.json)',
          '- [Claude 앱 자체 보고서](../tmp/remaining-20260913/claude-marked/output/approved-workflow-results.md)',
          '- 최초 독립 평가 176행과 과거 원시 기록은 보존했다. 이 결과는 현재 PC에서 승인한 두 문안에 대한 후속 시험이며 배포 권리/자산 검토나 전체 독립 인수를 대신하지 않는다.']
report=ROOT/'docs/W1-W2-승인후-두앱-흐름시험-2026-09-13.md';assert not report.exists()
report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps({'ts':summary['at'],'agent':'Codex','action':'approved_w1_w2_app_workflows','target':str(report),'result':'pass','detail':{'apps':2,'documents':4,'protected_unchanged':len(before),'tests':24,'real_dispatch':False,'summary':str(RUN/'summary.json')}},ensure_ascii=False)+'\n')
print(json.dumps({'report':str(report),'rows':len(rows),'same_outputs':same,'protected_unchanged':len(before),'claude_png_reads':len(reads),'claude_model':model},ensure_ascii=False))
