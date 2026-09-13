import datetime
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
prompt = '''This is a bounded independent Codex CLI acceptance test requested by the user to diagnose Hancom COM. Run exactly once:
& 'C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe' -B -X utf8 'C:/Users/22/Desktop/maintain/teacher_doc/tmp/com-timeout-20260913/acceptance.py'
The reviewed driver resumes the SAME interrupted acceptance after the previous CLI shell tool killed it at the default 10-second limit. Evidence and completed stages are preserved; do not reset anything. IMPORTANT: if using the shell tool, set timeout_ms=240000 explicitly for this command. If using exec_command with yield_time_ms, use 1000 and poll its returned session until completion. The driver runs COM Open and PDF render on copies of already-approved synthetic W1/W2 documents, records results, and stops at failure. Do not write code, edit settings, change permissions, retry failures, send documents, or spawn agents. Wait for the command to complete and report its result. Use the existing session permission configuration; do not override it. No further user approval is needed for this read-only test. Final human document review is still pending.'''
(RUN / 'acceptance-prompt.txt').write_text(prompt, encoding='utf-8')
args = ['C:/Users/22/AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe', 'exec', '--json', '-C', str(ROOT), '-']
start = time.monotonic()
with (RUN/'actual-cli.stdout.jsonl').open('w', encoding='utf-8') as out, (RUN/'actual-cli.stderr.txt').open('w', encoding='utf-8') as err:
    r = subprocess.run(args, cwd=ROOT, input=prompt, text=True, encoding='utf-8', stdout=out, stderr=err, timeout=300)
result = {'argv': args, 'exit_code': r.returncode, 'seconds': time.monotonic()-start,
          'at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
(RUN / 'actual-cli.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
