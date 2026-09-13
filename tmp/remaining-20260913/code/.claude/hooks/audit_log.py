#!/usr/bin/env python3
"""PostToolUse 훅: 파일 생성/수정을 logs/audit.jsonl 에 자동 기록.
LLM에게 기록을 맡기지 않고 훅이 결정적으로 남긴다.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from event_adapter import targets_for_event, normalize_path
from hwpdoc_config import owned_workspace

def main():
    data = json.load(sys.stdin)
    root = owned_workspace(data.get('cwd', ''))
    if root is None:
        print('{}'); return
    project_dir = str(root)
    log_dir = os.path.join(project_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    try:
        targets = [normalize_path(p, data['cwd']) for _, p in targets_for_event(data)]
        target_error = None
    except (ValueError, TypeError, KeyError) as exc:
        targets = []
        target_error = str(exc)
    response = data.get('tool_response')
    result = 'unconfirmed'
    if isinstance(response, dict):
        if response.get('isError') is True or response.get('exit_code', 0) not in (None, 0):
            result = 'fail'
        elif response.get('isError') is False or response.get('exit_code') == 0:
            result = 'pass'
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "agent": "hook",
        "action": data.get("tool_name", ""),
        "target": targets,
        "result": result,
        "detail": {'event': data.get('hook_event_name'), 'tool_use_id': data.get('tool_use_id'),
                   'target_error': target_error, 'note': 'post 이벤트는 사전 차단이나 파일 불변의 증거가 아님'},
    }
    with open(os.path.join(log_dir, "audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print('{}')
    sys.exit(0)

if __name__ == "__main__":
    main()
