"""Isolated COM availability probe, called under the runner's cross-process lock."""
import json
import sys
from hwpdoc_config import CODE_ROOT

skill = CODE_ROOT / '.claude/skills/hwpx/scripts'
sys.path.insert(0, str(skill if skill.is_dir() else CODE_ROOT / 'skills/hwpx/scripts'))
from hancom_com import session

def main():
    try:
        with session() as (app, context):
            result = dict(context, registered=True, version=str(app.Version))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(str(exc)); return 1

if __name__ == '__main__':
    sys.exit(main())
