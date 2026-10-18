from __future__ import annotations

from . import attack_string, move_catalog

def build(drill_id: str, character_id: str, expected_combo: str, data_dir=None) -> dict | None:

    if not (drill_id and character_id and expected_combo):
        return None
    if not move_catalog.load_catalog(character_id):
        return None
    mode, combo_text = attack_string.split_mode(expected_combo)
    steps = []
    for token in combo_text.split(","):
        text = token.strip()
        if not text:
            continue
        if text in ("...", "…"):
            steps.append({"text": text, "gap": True})
        elif attack_string.is_movement(text):
            steps.append({"text": text, "movement": True})
        else:
            ids = move_catalog.resolve(character_id,
                                       attack_string.strip_movement_prefix(text), data_dir)
            steps.append({"text": text, "ids": sorted(ids or [])})
    return {
        "drill_id": drill_id,
        "character_id": character_id,
        "mode": mode,
        "steps": steps,
        "aliases": {str(k): v for k, v in sorted(_aliases(character_id, data_dir).items())},
        "moves": sorted(_moves(character_id, data_dir)),
    }

def _aliases(character_id, data_dir) -> dict:

    return dict(move_catalog._stage_aliases(character_id, data_dir))

def _moves(character_id, data_dir) -> set:

    movement = move_catalog.movement_ids(character_id, data_dir)
    return {aid for aid in move_catalog.known_ids(character_id)
            if aid not in movement
            and not attack_string.is_movement(move_catalog.notation_for(character_id, aid))}

def performed(plan: dict, raw_action_ids) -> list:

    aliases = {int(k): v for k, v in plan["aliases"].items()}
    moves = set(plan["moves"])
    out, prev = [], object()
    for raw in raw_action_ids:
        mapped = aliases.get(raw, raw)
        if mapped == prev:
            continue
        prev = mapped
        if mapped in moves:
            out.append(mapped)
    return out
