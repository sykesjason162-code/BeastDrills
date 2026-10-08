from __future__ import annotations

import json
from pathlib import Path

LISTS = ("grades", "range_points", "combo_hits", "rep_avoided", "reps")

def load(path) -> dict:

    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}

    out: dict = {}
    for session_id, state in raw.items():
        if not isinstance(state, dict):
            continue
        lists = {name: state.get(name) for name in LISTS}
        if not all(isinstance(v, list) for v in lists.values()):
            continue

        if len({len(v) for v in lists.values()}) > 1:
            continue
        out[session_id] = lists
    return out

def save(path, state: dict) -> tuple[bool, str | None]:

    from . import paths

    target = Path(path)
    try:
        if not state:
            target.unlink(missing_ok=True)
            return True, None
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        paths.atomic_replace(tmp, target)
        return True, None
    except OSError as exc:
        return False, str(exc)
