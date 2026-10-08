from . import progress, scrimmage

DIFFICULTY_ORDER = ["very-easy", "easy", "medium", "hard", "very-hard"]

UNLOCK_REQUIREMENT = 2

UNLOCK_STREAK = 2

def unlocked_difficulties(drills: list, character_id: str | None = None) -> set:

    unlocked = set(DIFFICULTY_ORDER[:2])
    for i in range(1, len(DIFFICULTY_ORDER)):
        below = DIFFICULTY_ORDER[i - 1]
        if DIFFICULTY_ORDER[i] in unlocked:
            continue
        strong = sum(1 for d in drills
                     if d.get("difficulty") == below
                     and progress.streak_for(d, character_id) >= UNLOCK_STREAK)
        if strong >= UNLOCK_REQUIREMENT:
            unlocked.add(DIFFICULTY_ORDER[i])
        else:

            break
    return unlocked

DEBUG_PREFIX = "debug_"

def is_debug_drill(drill: dict) -> bool:

    return str(drill.get("id") or "").lower().startswith(DEBUG_PREFIX)

def get_due_drills(database: dict, now: str, character_id: str | None = None,
                   dummy_character_id: str | None = None,
                   gate_difficulty: bool = True,
                   favorites_only: bool = False) -> list:

    drills = database.get("drills") or []
    any_selected = any(d.get("selected") for d in drills)

    gate_pool = [d for d in drills
                 if character_id is None
                 or d.get("character_id") is None
                 or d.get("character_id") == character_id]
    unlocked = unlocked_difficulties(gate_pool, character_id) if gate_difficulty else None

    due = []
    for drill in drills:

        scheduled = drill.get("next_review") is not None
        fresh_for_character = not progress.has_state(drill, character_id)
        next_review = progress.next_review_for(drill, character_id)
        matches_character = (
            character_id is None
            or drill.get("character_id") is None
            or drill.get("character_id") == character_id
        )
        matches_dummy = (
            dummy_character_id is None
            or drill.get("dummy_character_id") is None
            or drill.get("dummy_character_id") == dummy_character_id
        )
        matches_selection = (not any_selected) or bool(drill.get("selected"))
        matches_favorite = (not favorites_only) or bool(drill.get("favorite"))

        matches_difficulty = (
            unlocked is None
            or not drill.get("difficulty")
            or drill["difficulty"] in unlocked
        )
        if (
            not drill.get("unsupported")
            and not is_debug_drill(drill)
            and matches_character
            and matches_dummy
            and matches_selection
            and matches_favorite
            and matches_difficulty
            and scheduled
            and (fresh_for_character or (next_review is not None and next_review <= now))
        ):
            due.append(drill)

    return scrimmage.reorder_by_recommendations(
        due, scrimmage.latest_recommendations(database, character_id,
                                              dummy_character_id))

def select_next_drill(due_drills: list) -> dict | None:

    selected = None
    for drill in due_drills:
        if selected is None or drill["next_review"] < selected["next_review"]:
            selected = drill
    return selected
