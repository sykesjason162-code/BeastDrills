from . import move_catalog

MIN_MOVES = 2

def notation_from_move_ids(character_id, move_ids, data_dir=None):

    if not character_id:
        return None, "the character played is not known"
    if not move_catalog.known_ids(character_id):
        return None, f"no move list for {character_id} yet"
    moves = move_catalog.filter_to_moves(character_id, list(move_ids or []), data_dir)
    if len(moves) < MIN_MOVES:
        return None, "fewer than two moves landed -- nothing to save"
    names = []
    for action_id in moves:
        name = move_catalog.notation_for(character_id, action_id)
        if name is None:
            return None, f"move {action_id} is not in {character_id}'s move list"
        names.append(name)
    return ", ".join(names), None

def drill_from_combo(character_id, move_ids, hits=None, data_dir=None):

    combo, why = notation_from_move_ids(character_id, move_ids, data_dir)
    if combo is None:
        return None, why
    name = f"My combo: {combo}"
    hit_text = f" ({hits} hits)" if hits else ""
    return {
        "id": _slug(f"{character_id} {name}"),
        "name": name,
        "description": f"Saved from a combo you landed{hit_text}. Rename it or add to it here.",
        "character_id": character_id,
        "fixed_expected_combo": combo,
        "training_settings": {"block_setting": "no_guard"},
        "source": "Saved from your last combo",
    }, None

def _slug(text):

    out = "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")
    while "__" in out:
        out = out.replace("__", "_")
    return out or "saved_combo"
