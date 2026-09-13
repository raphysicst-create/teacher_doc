from branch_acceptance_20260913 import *
from collections import Counter
import re
def main():
    evidence=RUN/'evidence';evidence.mkdir(exist_ok=True)
    log=Path('C:/Users/22/.claude/projects/c--Users-22-Desktop-maintain-teacher-doc/75162030-2b08-4967-ba1d-10dd61dd0752.jsonl')
    events=[json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()]
    uses=[];results={};texts=[]
    for e in events:
        content=e.get('message',{}).get('content',[])
        if not isinstance(content,list):continue
        for c in content:
            if c.get('type')=='tool_use':uses.append({'id':c['id'],'name':c['name'],'input':c['input']})
            if c.get('type')=='tool_result':results[c['tool_use_id']]={'is_error':bool(c.get('is_error',False)),'content_sha256':hashlib.sha256(json.dumps(c.get('content'),ensure_ascii=False).encode()).hexdigest()}
            if e.get('type')=='assistant' and c.get('type')=='text':texts.append(c['text'])
    assert len(uses)==4 and all(u['name']=='Read' and results.get(u['id'],{}).get('is_error') is False for u in uses),uses
    vs={'at':now(),'host':'VS Code Claude Code extension','session_id':'75162030-2b08-4967-ba1d-10dd61dd0752','observed_model':'Opus 5 High (actual UI)','extension_installed_version':'2.1.270','log_version':list({e.get('version') for e in events if e.get('version')}),'actual_read_calls':[{**u,**results[u['id']]} for u in uses],'response':'\n\n'.join(texts),'com':'not_run','full_workflow':'pending_user_start','ui_limit':'Computer-use guidance forbids direct or indirect Windows terminal commands; prepared user-start request. Not an observed application failure.','ui_input_limit':'set_value returned UIA CacheRequest 0x80070057; ordinary focused typing and submit succeeded; no settings changed.'}
    save(evidence/'vscode-read-result.json',vs)
    cli=read(evidence/'claude-actual-cli.json');assert cli['exit_code']==0
    ce=[json.loads(line) for line in cli['stdout'].splitlines() if line.startswith('{')]
    tool_names=[c['name'] for e in ce for c in e.get('message',{}).get('content',[]) if isinstance(c,dict) and c.get('type')=='tool_use']
    assert not any(n in ('Task','Agent') for n in tool_names),tool_names
    init=next(e for e in ce if e.get('type')=='system' and e.get('subtype')=='init')
    checks={}
    for app in ['codex','claude']:
        rows=read(evidence/f'{app}-preflight-summary.json')['results']
        assert len(rows)==5 and all(r['exit_code']==2 and not r['generated'] for r in rows)
        checks[app]=rows
    before=read(RUN/'protected-before.json')
    changed=[p for p,h in before.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not changed,changed
    result={'at':now(),'full_workflow_complete':False,'approval':'pending','vscode':{'read_calls':4,'full_workflow':'pending_user_start','com':'not_run'},'codex':{'host':'Codex Desktop','negative_cases':5},'claude':{'host':'Claude Code CLI','version':init.get('claude_code_version'),'model':init.get('model'),'actual_tools':tool_names,'negative_cases':5},'protected_originals':len(before),'changed_originals':changed,'draft_sha256':sha(RUN/'drafts.md'),'new_hwpx_generated':0,'actual_dispatch':False,'regression_suite':'not run: no production code changes in this turn','limitation':'Approval rejection and unknown-method diagnostics only; not full semantic/layout/COM/delivery acceptance.'}
    save(RUN/'summary.json',result)
    report=ROOT/'docs/미검증-분기-시험-2026-09-13.md';assert not report.exists()
    report.write_text(f'''# 미검증 분기 시험 — 2026. 9. 13.

전체 흐름 시험은 아직 완료하지 않았다. 실제로 실행한 범위는 VS Code의 지침 읽기와 Codex Desktop·Claude Code CLI의 미승인 입력 차단이다. 최초 독립 평가와 기존 성공 기록은 보존한다.

## 실제 실행 결과

| 환경 | 실행 | 결과 | 미완료 범위 |
|---|---|---|---|
| VS Code Claude 확장(설치 2.1.270, UI Opus 5 High) | 실제 Read 4회 | CLAUDE.md·hwpx SKILL·workflow·W2 원문 읽기 성공 | 작성·COM·렌더·시험 전달 |
| Codex Desktop | 일반 가통·회신형·공문 회신·이메일·방법 미확인 5건 build | 모두 exit 2, 작업 HWPX 생성 없음 | 문안 확인 후 정상 생성·검증·전달 |
| Claude Code CLI {init.get('claude_code_version')} | 같은 5건을 실제 CLI에서 실행 | 모두 exit 2, 작업 HWPX 생성 없음 | 문안 확인 후 정상 생성·검증·전달 |

승인 필드가 비어 있어 `사용자 초안 확인 기록`, `input_sha256`, `승인 시각` 진단이 함께 나왔다. 이는 시험에서 의도한 미승인 입력이며 제품 결함이나 원래 평가의 새 합격으로 세지 않는다. W2 방법 미확인은 추가로 `W2 제출 방법 미확인`을 반환했다. 방법 진단을 승인 조건과 독립적으로 통과시킨 시험은 아니다.

## 문안과 자료

[시험 초안 4종](../tmp/branch-acceptance-20260913/drafts.md)을 제시했으며 새 문안 확인을 기다린다. 기존 W1 기능 시험 계획·W2 시스템 제출 승인을 새 문안 승인으로 만들지 않았다. 일반 가통 문서번호·연락처, 회신형 문서번호·배부일·대상·인솔·제출처, 이메일 실제 주소는 미확인이다. 가상 정보·사람 평점·실제 발송을 지어내지 않는다.

원본 슬롯을 다시 추출했다. 일반 가통 제목은 공백 제외 8자로 예산 안이다. 회신형 일정은 5개 활동을 5개 행으로 유지하며 p:26(4/2자), p:29(6/4자), p:32(6/2자)의 원문 예산 초과를 기록했다. W2 공문 수신자 p:3(9/6자), 두 W2 관련번호 p:7(28/27자)도 렌더 판독 대상이다. 실제 렌더 전에는 확인 옵션을 붙이지 않는다. 학교 시험 설정의 행사 4일 전을 Python datetime으로 계산해 회신기한은 2026. 10. 12.로 제시했다.

## VS Code 후속 실행

[실행 요청문](../tmp/branch-acceptance-20260913/vscode-run-request.md)과 폐기용 작업 폴더를 준비했다. 기존 승인 W1·W2 문안만 재사용하며 드라이버는 부모 프로세스의 Code.exe를 확인한다. 현재 Codex 프로세스 계보에서 Code.exe가 없음을 별도로 확인했다. VS Code 밖 실행을 VS Code 통과로 기록하지 않는다. 문안 외 새 HWPX는 아직 생성하지 않았고 새 COM·렌더도 실행하지 않았다.

화면 조작에 사용한 computer-use SKILL.md가 연결하는 guidance.md의 `Do not run Windows terminal commands via UI automation directly or indirectly.` 제한 때문에 명령 실행 시작은 사용자가 VS Code에서 해야 한다. 이는 앱 자체의 실패가 아니다. 입력창 set_value의 UIA 오류는 일반 텍스트 입력으로 복구해 읽기 시험을 마쳤다. 보안·권한 설정은 변경하지 않았다.

## 보존과 근거

- 기존 보호 대상 {len(before)}개 파일의 해시가 모두 동일하다. 신규 시험 HWPX는 0개이며 실제 전송은 0건이다.
- [시험 요약](../tmp/branch-acceptance-20260913/summary.json)
- [Codex 차단 결과](../tmp/branch-acceptance-20260913/evidence/codex-preflight-summary.json) · [Claude 차단 결과](../tmp/branch-acceptance-20260913/evidence/claude-preflight-summary.json)
- [VS Code 실제 읽기](../tmp/branch-acceptance-20260913/evidence/vscode-read-result.json) · [Claude 실제 CLI](../tmp/branch-acceptance-20260913/evidence/claude-actual-cli.json)
- [슬롯 예산](../tmp/branch-acceptance-20260913/budget-check.json) · [날짜 계산](../tmp/branch-acceptance-20260913/date-check.json)

향후 검토본 생성 시 발송 전 한글로 열어 확인해주세요. 시험 결과를 사람 최종 검토나 발송 완료로 기록하지 않는다.
''',encoding='utf-8',newline='\n')
    with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'ts':now(),'agent':'codex','action':'branch_acceptance_partial','target':str(report),'result':'partial','detail':result},ensure_ascii=False)+'\n')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
