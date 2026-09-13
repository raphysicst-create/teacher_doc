"""Disposable diagnostic wrapper. Captures only synthetic test hook events."""
import json
from pathlib import Path
import sys

RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN / 'code-v3/.claude/hooks'))
from event_adapter import evaluate, emit_pre

data = json.load(sys.stdin)
result = evaluate(data)
with (RUN / 'evidence/codex-pre-trace.jsonl').open('a', encoding='utf-8') as stream:
    stream.write(json.dumps({'input': data, 'evaluation': result}, ensure_ascii=False) + '\n')
sys.exit(emit_pre(data))
