from __future__ import annotations

from . import attempts, belts

EDITABLE = (
    "name",
    "description",
    "training_settings",
    "slot_outcomes",
    "fixed_expected_response",
    "expected_setup",
    "against_criteria",
    "survive_seconds",
    "fixed_expected_combo",
    "response_window_frames",
    "game_speed",
    "reps",
    attempts.FIELD,
    "character_id",
    "dummy_character_id",
    "trains",
    "trains_for",
    "difficulty",
    "wongscript_text",
    belts.FIELD,
)

KEEP_UNLESS_SENT = ("fixed_expected_combo", belts.FIELD)

def from_body(body: dict) -> dict:

    return {key: body.get(key) for key in EDITABLE
            if key not in KEEP_UNLESS_SENT or key in body}
