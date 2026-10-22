from copy import deepcopy

from . import progress

PERSONAL_FIELDS = (*progress.STATE_FIELDS, progress.PROGRESS_KEY, "selected", "favorite")

LIBRARY_KEYS = ("drills",)

def split(db: dict, public_ids) -> tuple:

    public_ids = set(public_ids or ())
    library = {"drills": []}
    profile = {"progress": {}, "drills": [], "drill_order": []}
    for drill in db.get("drills") or []:
        drill_id = drill.get("id")
        profile["drill_order"].append(drill_id)
        if drill_id in public_ids:
            definition = {k: deepcopy(v) for k, v in drill.items() if k not in PERSONAL_FIELDS}
            state = {k: deepcopy(drill[k]) for k in PERSONAL_FIELDS if k in drill}
            library["drills"].append(definition)
            if state:
                profile["progress"][drill_id] = state
        else:
            profile["drills"].append(deepcopy(drill))
    for key, value in db.items():
        if key not in LIBRARY_KEYS:
            profile[key] = deepcopy(value)
    return library, profile

def merge(library: dict, profile: dict) -> dict:

    progress = profile.get("progress") or {}
    private = {d.get("id"): d for d in profile.get("drills") or []}
    by_id = {}
    for definition in library.get("drills") or []:
        drill_id = definition.get("id")
        drill = deepcopy(definition)
        drill.update(deepcopy(progress.get(drill_id) or {}))
        by_id[drill_id] = drill
    for drill_id, drill in private.items():
        by_id[drill_id] = deepcopy(drill)

    ordered, seen = [], set()
    for drill_id in profile.get("drill_order") or []:
        if drill_id in by_id and drill_id not in seen:
            ordered.append(by_id[drill_id])
            seen.add(drill_id)
    for drill_id, drill in by_id.items():
        if drill_id not in seen:
            ordered.append(drill)
            seen.add(drill_id)

    db = {"drills": ordered}
    for key, value in profile.items():
        if key not in ("progress", "drills", "drill_order"):
            db[key] = deepcopy(value)
    return db

def lossless(db: dict, public_ids) -> tuple:

    library, profile = split(db, public_ids)
    back = merge(library, profile)
    if back == db:
        return True, None
    if set(back) != set(db):
        return False, f"top-level keys differ: {sorted(set(back) ^ set(db))}"
    if len(back.get("drills") or []) != len(db.get("drills") or []):
        return False, "drill count differs"
    for a, b in zip(back.get("drills") or [], db.get("drills") or [], strict=True):
        if a != b:
            return False, f"drill {b.get('id')!r} differs"
    return False, "a top-level value differs"
