import sys,json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parents[3]
t=Path(__file__).resolve().parent
sys.path.insert(0,str(r/'.claude/skills/hwpx/scripts'))
import edit_hwpx as e
# 미검증 렌더용 사본만 생성. 최종 편집은 실제 이미지 판독 후 CLI로 수행한다.
v=json.loads((t/'values.json').read_text(encoding='utf-8'))
e._pack_from_original(r/'knowledge/templates/성립전예산요구/양식.hwpx',t/'unverified.hwpx',{},[],[e.ParagraphTarget(int(k.split(':')[1]),value) for k,value in v.items()])
paths=[r/'CLAUDE.md',r/'.claude/skills/hwpx/SKILL.md',t/'request.md',t/'draft.md',t/'values.json']
(t/'provenance.json').write_text(json.dumps({'model':'gpt-6-astra','reasoning':'low','hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'guide':'find_tasks timeout after 120s; later calls unexecuted; freshness unchecked','preview':'미검증 사본, 편집 세부 2단계 렌더 검사용. 최종 산출물 아님'},ensure_ascii=False,indent=2),encoding='utf-8')
