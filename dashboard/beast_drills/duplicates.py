import re

WIKI_MARKER = "[SuperCombo wiki]"

def _norm(text) -> str:

    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())

def sessions(drill: dict) -> int:

    total = drill.get("total_sessions") or 0
    for state in (drill.get("character_progress") or {}).values():
        total += state.get("total_sessions") or 0
    return total

def _rank(drill: dict) -> tuple:

    return (
        -sessions(drill),
        WIKI_MARKER in (drill.get("description") or ""),
        drill.get("id") or "",
    )

BEHAVIOUR_FIELDS = ("fixed_expected_response", "expected_setup",
                    "against_criteria", "training_settings", "slot_outcomes")

def same_behaviour(members: list) -> bool:

    import json as _json
    seen = {_json.dumps({f: d.get(f) for f in BEHAVIOUR_FIELDS}, sort_keys=True)
            for d in members}
    return len(seen) == 1

def find_groups(drills: list, last_reviewed: dict | None = None) -> list:

    buckets: dict = {}
    for drill in drills:
        combo = drill.get("fixed_expected_combo")
        if not combo:
            continue
        buckets.setdefault((drill.get("character_id"), _norm(combo)), []).append(drill)

    groups = []
    for (character_id, _), members in buckets.items():
        if len(members) < 2:
            continue
        ordered = sorted(members, key=_rank)
        keep, others = ordered[0], ordered[1:]
        wiki = [WIKI_MARKER in (d.get("description") or "") for d in ordered]

        if any(wiki) and not all(wiki):
            reason = "an imported copy of a hand-authored drill"
        elif all(wiki):
            reason = "both imported -- may be the same combo listed twice, or genuinely different setups"
        else:
            reason = "neither imported"

        groups.append({
            "character_id": character_id,
            "combo": keep.get("fixed_expected_combo"),
            "reason": reason,

            "risk": "history" if sessions(keep) else None,
            "keep": _summary(keep),
            "others": [_summary(d) for d in others],
            "merge": merge_plan(ordered, last_reviewed),

            "identical_setup": same_behaviour(ordered),
        })
    groups.sort(key=lambda g: (g["risk"] is None, g["character_id"] or "", g["combo"] or ""))
    return groups

def _summary(drill: dict) -> dict:
    return {
        "id": drill.get("id"),
        "name": drill.get("name"),
        "sessions": sessions(drill),
        "streak": drill.get("streak") or 0,
        "imported": WIKI_MARKER in (drill.get("description") or ""),
        "difficulty": drill.get("difficulty"),
    }

def summarise(drills: list) -> dict:

    groups = find_groups(drills)
    return {
        "groups": len(groups),
        "drills": sum(1 + len(g["others"]) for g in groups),
        "with_history": sum(1 for g in groups if g["risk"]),
        "imported_over_authored": sum(
            1 for g in groups if g["reason"].startswith("an imported copy")),

        "identical_setup": sum(1 for g in groups if g["identical_setup"]),
        "different_setup": sum(1 for g in groups if not g["identical_setup"]),
    }

def name_key(drill: dict) -> tuple:

    return (drill.get("character_id"), _norm(drill.get("name")))

SCHEDULE_FIELDS = ("streak", "ease_factor", "interval_days", "next_review")

def _reviewed_at(drill: dict, last_reviewed: dict | None) -> str:

    if last_reviewed and drill.get("id") in last_reviewed:
        return str(last_reviewed[drill["id"]])
    return str(drill.get("next_review") or "")

def merge_plan(members: list, last_reviewed: dict | None = None) -> dict | None:

    with_history = [d for d in members if sessions(d)]
    if len(with_history) < 2:
        return None

    ordered = sorted(members, key=_rank)
    keep = ordered[0]
    recent = max(with_history, key=lambda d: _reviewed_at(d, last_reviewed))

    merged = {f: recent.get(f) for f in SCHEDULE_FIELDS}
    merged["total_sessions"] = sum(d.get("total_sessions") or 0 for d in members)

    progress: dict = {}
    for drill in members:
        for character, state in (drill.get("character_progress") or {}).items():
            seen = progress.setdefault(character, {"total_sessions": 0, "_at": ""})
            seen["total_sessions"] += state.get("total_sessions") or 0
            at = str(state.get("next_review") or "")
            if at >= seen["_at"]:
                seen["_at"] = at
                for f in SCHEDULE_FIELDS:
                    seen[f] = state.get(f)
    for state in progress.values():
        state.pop("_at", None)
    if progress:
        merged["character_progress"] = progress

    return {
        "keep": keep.get("id"),
        "schedule_from": recent.get("id"),
        "merged": merged,

        "rekey_reviews_from": [d.get("id") for d in members
                               if d.get("id") != keep.get("id") and sessions(d)],
    }
