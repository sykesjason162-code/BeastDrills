from . import scheduler

STATE_FIELDS = ("interval_days", "ease_factor", "streak", "next_review",
                "total_sessions", "speed_level")

PROGRESS_KEY = "character_progress"

def is_per_character(drill: dict) -> bool:

    return not drill.get("character_id")

def state_for(drill: dict, character_id: str | None) -> dict:

    if not is_per_character(drill) or character_id is None:
        return {k: drill.get(k) for k in STATE_FIELDS}

    per = (drill.get(PROGRESS_KEY) or {}).get(character_id) or {}
    state = dict(scheduler.STARTING_STATE)
    state.update({k: v for k, v in per.items() if k in STATE_FIELDS})
    return {k: state.get(k) for k in STATE_FIELDS}

def has_state(drill: dict, character_id: str | None) -> bool:

    if not is_per_character(drill) or character_id is None:
        return drill.get("next_review") is not None
    return bool((drill.get(PROGRESS_KEY) or {}).get(character_id))

def next_review_for(drill: dict, character_id: str | None):
    return state_for(drill, character_id).get("next_review")

def streak_for(drill: dict, character_id: str | None) -> int:
    return state_for(drill, character_id).get("streak") or 0

def apply_state(drill: dict, character_id: str | None, state: dict) -> None:

    target = drill
    if is_per_character(drill) and character_id is not None:
        per = drill.setdefault(PROGRESS_KEY, {})
        target = per.setdefault(character_id, {})
    for key in STATE_FIELDS:
        if key in state:
            target[key] = state[key]

def characters_practised(drill: dict) -> list:

    if not is_per_character(drill):
        return []
    return sorted((drill.get(PROGRESS_KEY) or {}).keys())
