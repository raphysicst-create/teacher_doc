"""Replay unchanged historical software fixtures; never generate human approvals."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, time

ws=Path.cwd().resolve()
run=ws.parent
assert ws.name in ('claude-marked','codex-marked')
assert run.name=='remaining-20260913'
code=run/'code'
# Parent releases this only after the other app's registration COM has ended.
deadline=time.monotonic()+180
while not (run/'delivery-com-ready').is_file():
    if time.monotonic()>deadline:
        raise RuntimeError('COM serial gate not released; trial not executed')
    time.sleep(1)
results=[]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(*args):
    argv=[sys.executable,'-B','-X','utf8',str(code/'scripts/hwpdoc.py'),'--workspace',str(ws),*args]
    r=subprocess.run(argv,cwd=ws,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=150)
    results.append({'argv':argv,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    (ws/'output/delivery-trial.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(args,r.returncode,flush=True)
    return r.returncode
def report(job):return read(ws/f'.hwpdoc/jobs/{job}/report.json')
for i in (0,1):
    manifest=ws/f'eval-inputs/{i}-1.json'
    m=read(manifest)
    assert m['draft_approval']['by']=='SYNTHETIC_TEST_NOT_USER'
    original_manifest=sha(manifest)
    job=m['job_id']
    assert command('build','--manifest',f'eval-inputs/{i}-1.json')==0
    baseline=report(job)
    document=ws/f'.hwpdoc/jobs/{job}/work.hwpx'
    file_hash=sha(document)
    remote=ws/'fake-copy'
    if i==0:
        assert not remote.exists()
        assert command('deliver','--job',job)==1
        failed=report(job)
        assert failed['copy']['failures']==1 and failed['copy']['status']=='fail'
        remote.mkdir()
        assert command('deliver','--job',job)==0
        finished=report(job)
        assert finished['copy']['status']=='pass' and finished['copy']['failures']==1
        local=ws/f'output/{job}/검증완료_검토대기.hwpx'
        assert sha(local)==sha(remote/job/local.name)==file_hash
        assert read(remote/job/'검토보고서.json')['copy']['status']=='pass'
    else:
        collision=remote/job/'검증완료_검토대기.hwpx'
        collision.parent.mkdir()
        collision.write_bytes(b'EXISTING_REMOTE_TEST_FILE_DO_NOT_OVERWRITE')
        collision_hash=sha(collision)
        assert command('deliver','--job',job)==1
        assert command('deliver','--job',job)==1
        assert command('deliver','--job',job)==2
        finished=report(job)
        assert finished['copy']['failures']==2
        assert sha(collision)==collision_hash
    assert finished['history']==baseline['history'], 'copy retried validation unexpectedly'
    assert not finished['delivery']['sent']
    assert sha(document)==file_hash and sha(manifest)==original_manifest
    results.append({'job':job,'assertions':'pass','history_unchanged':True,'manifest_unchanged':True,'work_sha256':file_hash,'copy':finished['copy'],'scope':'historical synthetic approval fixture, not new W1/W2 human acceptance'})
    (ws/'output/delivery-trial.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
