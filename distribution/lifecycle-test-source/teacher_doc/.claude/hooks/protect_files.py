#!/usr/bin/env python3
"""PreToolUse 훅: CLAUDE.md 금지 규칙을 강제한다.
- knowledge/, docs/ 폴더의 기존 파일 덮어쓰기 차단 (원본 보존)
- 신규 파일 생성은 허용 (파생물: md 변환본·index·템플릿 — 2026. 7. 8. 사용자 승인)
- 파생물 화이트리스트(.md 한정)는 기존 파일이라도 갱신 허용 (2026. 7. 24. 사용자 승인)
- 위험한 셸 명령 차단
exit 0 = 허용, exit 2 = 차단 (stderr 메시지가 Claude에게 전달됨)
"""
import json
import os
import re
import sys

PROTECTED_DIRS = ("knowledge/", "knowledge\\", "docs/", "docs\\")
# 에이전트가 만들고 유지보수하는 파생물 — 원본(발송본 hwpx·pdf) 보호는 그대로 두고
# 갱신을 허용한다. .md 확장자에 한정해 원본이 이 경로에 놓여도 보호가 유지된다.
DERIVED_WHITELIST = ("knowledge/examples/index.md", "knowledge/examples/md/")
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdel\s+/[sq]\b",
    r"\brmdir\s+/s\b",
    r"\bformat\s+[a-z]:",
    r"\btaskkill\b",
]

def protected_reason(path):
    """Normalized absolute path; segment matching avoids the old /output bypass."""
    from pathlib import Path
    from hwpdoc_config import owned_workspace
    root = owned_workspace(path)
    if root is None:
        return None
    parts = Path(path).resolve().relative_to(root).as_posix().lower().split('/')
    derived = path.lower().endswith('.md') and any(
        parts[i:i+3] == ['knowledge', 'examples', 'index.md'] and i+3 == len(parts)
        or parts[i:i+3] == ['knowledge', 'examples', 'md']
        for i in range(len(parts))
    )
    if any(p in ('knowledge', 'docs') for p in parts) and not derived and Path(path).exists():
        return '기존 원본 보호: ' + path + ' — 수정본은 새 파일로 저장하세요.'
    return None

def main():
    from event_adapter import emit_pre
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        data = json.load(sys.stdin)
        # Claude also supplies cwd; absence must not use an unrelated process cwd.
        return emit_pre(data)
    except (ValueError, TypeError) as exc:
        print('차단: 훅 입력 해석 실패: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
