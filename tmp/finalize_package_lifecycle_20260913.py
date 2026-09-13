from package_lifecycle_20260913 import *
from collections import Counter
import re

def finish():
    before=read(RUN/'protected-before.json')
    changed=[p for p,h in before.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not changed,changed
    globals_before=read(RUN/'global-config-before.json')
    globals_after={p:sha(p) if Path(p).is_file() else None for p in globals_before}
    assert globals_after==globals_before
    save(RUN/'global-config-after.json',globals_after)
    apps={}
    for app in ['codex','claude']:
        update=read(RUN/f'{app}-update-verification.json');removed=read(RUN/f'{app}-uninstall-verification.json')
        assert update['new_full_validation_passed'] and removed['plugin_uninstalled']
        assert protected(app)==read(RUN/f'{app}-protected-before-update.json')
        a=read(RUN/f'{app}-report-before-update.json');b=read(RUN/f'{app}-report-after-update.json')
        assert a['status']==b['status']=='pass' and a['delivery']['sent'] is False
        assert a['validated_sha256']==b['validated_sha256']
        assert all(a['stages'][s]['status']==b['stages'][s]['status']=='pass' for s in ['hancom','render','page_guard','structure','gonmun','content'])
        ws=RUN/f'ws-{app}';delivered=ws/'output/approved-w1-20260913/검증완료_검토대기.hwpx'
        copies=[p for p in (ws/'test-copy').rglob('*.hwpx')]
        assert len(copies)==1 and sha(copies[0])==sha(delivered)==a['validated_sha256']
        settings=ws/('.codex/hooks.json' if app=='codex' else '.claude/settings.json')
        assert read(settings)==read(RUN/f'{app}-user-hooks-original.json')
        apps[app]={'install':'pass','installed_code_build_validate_deliver':'pass','update':'pass','stale_validation_rejected':'pass','revalidation':'pass','uninstall':'pass','protected_entries':len(protected(app)),'custom_hooks_preserved':True,'job_hwpx_sha256':b['validated_sha256'],'manifest_sha256':b['manifest_sha256'],'trial_external_copy_matches':True,'human_review':'pending','sent':False,'update_detail':update,'uninstall_detail':removed}
    receipts={p.name:read(p)['exit_code'] for p in (RUN/'lifecycle-evidence').glob('*.json')}
    assert all(code==(2 if 'status-stale-b' in name else 0) for name,code in receipts.items())
    archive=read(RUN/'archive-verification.json');assert sha(archive['zip'])==archive['sha256']
    current=require(call('final-release-gate',[PY,'-B','-X','utf8',ROOT/'scripts/build_distribution.py','--rights',ROOT/'distribution/rights.pending.json']))
    gate=json.loads(current['stdout']);assert gate['status']=='ready_to_package' and not gate['issues']
    assert {i['destination']:i['sha256'] for i in gate['files']}=={i['destination']:i['sha256'] for i in read(PACKAGE/'release-inventory.json')['files']}
    summary={'at':now(),'task':'Actual distribution package lifecycle verification','package_cli_lifecycle':'pass','public_release_decision':'hold','public_release_reasons':['Fresh GUI/app-context acceptance is not replaced by CLI plugin-manager and direct installed-code execution','VS Code full workflow and general/reply notices plus W2 official/email branches remain incomplete','Five-location sentinel fault injection and colleague pilot remain unperformed'],'scope':'Codex CLI 0.147.0 and Claude Code CLI 2.1.270, disposable profiles on current Windows PC; fixed Python312, Hancom COM serial; no new LLM session or desktop UI installation trial','package':{k:v for k,v in archive.items() if k!='files'},'updated_fixture':read(RUN/'update-package.json'),'apps':apps,'original_files_checked':len(before),'original_files_changed':changed,'global_config_files_checked':len(globals_before),'global_config_unchanged':True,'gate_issues':[],'gate_allowlisted_files':len(gate['files']),'regression_tests':{'tests':133,'status':'passed','elapsed_seconds':107.737,'evidence':'Observed exec_command session 31772 output: Ran 133 tests in 107.737s; OK. New budget-reader regressions included.'},'test_harness_correction':{'failure':'Claude update installed successfully; test harness initially assumed version string equalled directory basename and raised AssertionError before validation','correction':'Use actual plugin list --json installPath (Claude changes + to - in its cache directory)','update_retried':False,'continuation':'Resumed only remaining verification using installed path; original success receipts preserved'},'fixture_environment_note':'Unchanged historically approved manifest reports Codex Desktop. That is fixture provenance only; actual execution host/scope is recorded here and in subprocess receipts. No new approval fabricated.','kordoc':'Not connected to child executor; text_extract diff fallback used','actual_external_dispatch':False}
    save(RUN/'summary.json',summary)
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in (RUN/'lifecycle-evidence').glob('*.json')}
    for n in ['summary.json','archive-verification.json','clean-candidate-scan.json','global-config-before.json','global-config-after.json','protected-before.json','codex-update-verification.json','claude-update-verification.json','codex-uninstall-verification.json','claude-uninstall-verification.json']:
        evidence[(RUN/n).relative_to(ROOT).as_posix()]=sha(RUN/n)
    save(RUN/'evidence-index.json',evidence)
    report=ROOT/'docs/실제-배포-패키지-검증-2026-09-13.md'
    report.write_text(f'''# 실제 배포 패키지 검증 — 2026. 9. 13.

**현재 PC의 Codex·Claude CLI 패키지 설치·업데이트·제거 및 자료 보존 시험은 통과했다. 공개 배포는 보류한다.** 새 앱 문맥의 인수, 남은 업무 분기, 동료 교사 시범 사용을 이번 CLI 시험으로 대체하지 않는다.

## 패키지

- 후보 A: [teacher_doc-0.1.0.zip](../distribution/releases/2026-09-13/teacher_doc-0.1.0.zip), {archive['bytes']:,} bytes. 실제 설치한 디렉터리와 ZIP 전체 파일의 CRC·SHA256을 대조했다.
- ZIP SHA256: `{archive['sha256']}`.
- 허용 파일 103개 + 생성된 release-inventory.json 1개. 허용 목록 외 파일 0개. 운영 공문·로그·메모리·학교 설정을 포함하지 않는다. 텍스트 파일 87개에서 학교명·개인 경로·시험 표식이 발견되지 않았고, 유일한 PNG 미리보기는 직접 열어 흰 빈 이미지임을 확인했다. 상류 소스 압축본은 확인된 원본 해시를 유지한다.
- 업데이트 후보 B: `{summary['updated_fixture']['version']}`. 별도 시험 사본의 버전과 기능에 영향 없는 주석만 변경했다. 실제 패키지 빌더로 포장했으며 B는 공개 후보가 아니다.
- 최신 [권리·자산 게이트](../tmp/package-lifecycle-20260913/lifecycle-evidence/final-release-gate.json): 103개 파일, 차단 0건. 포장 가능은 최종 배포 승인이 아니다.

## 실제 시험 결과

| 항목 | Codex CLI 0.147.0 | Claude Code CLI 2.1.270 |
|---|---|---|
| 격리 설정에서 실제 plugin 설치 | 통과 | 통과 |
| 설치 캐시의 103개 파일 해시 | 일치 | 일치 |
| 설치된 실행기로 승인된 W1 작성·전체 검증·시험 전달 | 통과 | 통과 |
| 실제 plugin 업데이트·새 코드 해시 확인 | 통과 | 통과 |
| 이전 검증 무효 판정 | exit 2, hwpdoc.py 변경 감지 | exit 2, hwpdoc.py 변경 감지 |
| 승인 입력 유지 후 새 코드로 전체 재검증 | 통과 | 통과 |
| 소유 훅 제거 → plugin 제거 → 설치 목록 확인 | 통과 | 통과 |
| 입력·등록 양식·문서·PC 설정 보존 | 42개 해시 일치 | 42개 해시 일치 |
| 사용자 훅·기타 설정 보존 | 원래 JSON과 동일 | 원래 JSON과 동일 |

구조·namespace·finalize·layout·page_guard·한글 COM·참조 렌더·lint·내용·붙임·신구대조를 확인했다. 예산·시간표·관련번호가 없는 가상 기능 시험이므로 이 항목은 근거를 갖춘 적용 제외다. kordoc 미연결로 신구대조는 text_extract 폴백을 사용했다. COM은 직렬 실행했다.

기존 승인 W1 문안과 승인 입력 해시를 그대로 사용했다. 시험 폴더 안의 output과 시험용 전달 폴더만 사용했으며 실제 OneDrive 전송·발송·사람 평점은 기록하지 않았다. 산출물의 `sent=false`, `human_review=pending`을 확인했다. 원본 **{len(before)}개** 및 사용자 전역 설정 **{len(globals_before)}개**의 해시는 그대로다. 설치 캐시와 전역 설정이 아닌 별도 작업 폴더에 업무 자료가 남는다.

## 발견 사항과 수정

1. 기존 xlrd 광고 조항의 결합 조건을 임의 승인하지 않고 XLS 판독기를 MIT python-calamine 0.7.0으로 교체했다. 원본 사본 318개 셀의 값·타입과 파생 JSON 바이트가 동일했다. 전체 회귀시험 133개가 통과했다. 기존 저작자 표시와 향후 광고 시 반드시 표시하겠다는 README 약속은 보존한다. [교체·권리 검토](../distribution/calamine-review-2026-09-13.md).
2. Claude 업데이트는 성공했지만 시험 코드가 캐시 폴더를 버전 문자열로 추정해 중단됐다. `+`가 `-`로 저장되는 실제 `installPath`를 읽도록 시험 코드만 고친 뒤 남은 검증을 통과했다. 실패를 제품 업데이트 실패로 기록하지 않고 원래 실행 증거를 보존했다.

## 판단과 남은 범위

로컬 CLI 패키지 수명주기 검증에는 재현된 제품 결함이 없다. 공개 배포는 아직 보류한다. 앱을 새로 시작한 문맥에서 스킬·훅 로딩을 포함한 인수, VS Code 전체 흐름, 일반·회신형 가통 및 W2 공문·메일 분기, 5위치 식별 표식 삽입 시험, 동료 시범 사용이 남아 있다. 외부 PC 시험은 사용자 요청대로 제외한다.

이 시험은 `plugin` CLI가 설치한 코드를 직접 실행한 결과다. 새 LLM 세션·Codex Desktop UI·Claude Desktop Cowork 인수로 표시하지 않는다. 복사한 승인 manifest의 환경 표기는 과거 시험 출처이며, 이번 실제 호스트는 실행 명령과 본 보고서가 명시한다. 최초 독립 평가 판정은 보존하고 후속 범위만 갱신한다.

[종합 증거](../tmp/package-lifecycle-20260913/summary.json) · [명령·파일 해시](../tmp/package-lifecycle-20260913/evidence-index.json) · [최신 평가표](플러그인-보급-평가통합표-2026-09-13.md)

시험 산출물을 업무에 전용하려면 사람이 다시 검토해야 한다. **발송 전 한글로 열어 확인해주세요.**
''',encoding='utf-8')
    with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'ts':now(),'agent':'codex','action':'package_lifecycle_verification','target':str(report),'result':'cli_pass_public_hold','detail':{'package_files':103,'original_files_unchanged':len(before),'apps':['codex-cli','claude-code-cli'],'harness_path_assumption_corrected':True}},ensure_ascii=False)+'\n')
    print(json.dumps({'report':str(report),'originals':len(before),'global_settings':len(globals_before),'status':'cli_pass_public_hold'},ensure_ascii=False))

if __name__=='__main__':finish()
