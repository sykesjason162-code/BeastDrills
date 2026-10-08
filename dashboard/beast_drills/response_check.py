import logging

from . import criteria, grader

log = logging.getLogger(__name__)

def hit_or_damage(snapshot: dict) -> str:

    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p2_combo_cnt", 0) > 0 or snapshot.get("p2_act_st") == 32:
        return "hit"
    return "miss"

def tally_saw(snapshot: dict, key: str):

    seen = snapshot.get("seen_at")
    if not isinstance(seen, dict):
        return None
    if not any(k.startswith("tally:") for k in seen):
        return None
    return ("tally:" + key) in seen

def anti_air_check(snapshot: dict) -> str:

    if snapshot.get("p1_hit"):
        return "damage_taken"
    saw = tally_saw(snapshot, "anti_air")
    if saw is not None:
        return "hit" if saw else "miss"
    if snapshot.get("p2_hit_while_airborne"):
        return "hit"
    return "miss"

def throw_or_damage(snapshot: dict) -> str:

    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p2_throw_connected"):
        return "hit"
    return "miss"

def drive_impact_check(snapshot: dict) -> str:

    if snapshot.get("p1_hit"):
        return "damage_taken"
    saw = tally_saw(snapshot, "drive_impact")
    if saw is not None:
        return "hit" if saw else "miss"
    if snapshot.get("p2_hit_after_drive_impact"):
        return "hit"
    return "miss"

def drive_impact_counter_check(snapshot: dict) -> str:
    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p2_hit_after_di_counter"):
        return "hit"
    return "miss"

def drive_impact_vs_di_check(snapshot: dict) -> str:
    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p2_hit_after_di_clash"):
        return "hit"
    return "miss"

def block_check(snapshot: dict) -> str:

    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p1_blocked"):
        return "hit"
    return "miss"

def perfect_parry_check(snapshot: dict) -> str:

    return "hit" if snapshot.get("p2_perfect_parried") else "miss"

def counter_hit_check(snapshot: dict) -> str:
    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p2_counter_dm_flag"):
        return "hit"
    return "miss"

def punish_counter_hit_check(snapshot: dict) -> str:
    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p2_counter_fw_flag"):
        return "hit"
    return "miss"

def throw_tech_check(snapshot: dict) -> str:

    if snapshot.get("p1_throw_teched"):
        return "hit"
    if snapshot.get("p1_hit"):
        return "damage_taken"
    return "miss"

def stuff_drive_rush_check(snapshot: dict) -> str:
    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p2_pc_after_drive_rush"):
        return "miss"
    if snapshot.get("p2_ch_after_drive_rush"):
        return "hit"
    return "miss"

def stuff_dash_check(snapshot: dict) -> str:
    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p2_hit_after_dash"):
        return "hit"
    return "miss"

CONFIRM_MIN_HITS = 2

def block_then_punish_check(snapshot: dict) -> str:

    if snapshot.get("p1_hit"):
        return "damage_taken"
    if snapshot.get("p1_blocked_then_hit"):
        return "hit"
    return "miss"

def reversal_check(snapshot: dict) -> str:

    return "hit" if snapshot.get("p1_reversal") else "miss"

def backroll_check(snapshot: dict) -> str:

    return "hit" if snapshot.get("p1_backroll") else "miss"

def do_nothing_check(snapshot: dict) -> str:

    if "p1_attacked" not in snapshot:
        return None
    if snapshot.get("p1_hit"):
        return "damage_taken"
    return "miss" if snapshot.get("p1_attacked") else "hit"

CHECKERS = {
    "anti_air": anti_air_check,
    "stuff_dash": stuff_dash_check,
    "stuff_drive_rush": stuff_drive_rush_check,
    "counter_hit": counter_hit_check,
    "punish_counter_hit": punish_counter_hit_check,
    "throw": throw_or_damage,
    "drive_impact": drive_impact_check,
    "drive_impact_counter": drive_impact_counter_check,
    "drive_impact_vs_di": drive_impact_vs_di_check,
    "block": block_check,
    "perfect_parry": perfect_parry_check,
    "reversal": reversal_check,
    "throw_tech": throw_tech_check,
    "block_then_punish": block_then_punish_check,
    "do_nothing": do_nothing_check,
    "backroll": backroll_check,
}

SUPPORTED = sorted(set(CHECKERS) | set(criteria.ALIASES))

def _check_single(expected_response: str, snapshot: dict) -> tuple:

    if criteria.is_expression(expected_response) or (
            expected_response in criteria.ALIASES
            and expected_response not in CHECKERS):
        try:
            outcome, why = criteria.explain(expected_response, snapshot)
        except ValueError as exc:

            return None, f"unsupported: {exc}"

        if outcome != "hit" and why:
            log.info("ordered criterion %r -> %s (%s)",
                     expected_response, outcome or "unsupported", why)
        return (outcome, None) if outcome is not None else (None, "unsupported")

    checker = CHECKERS.get(expected_response)
    if not checker:
        return None, "unsupported"
    outcome = checker(snapshot)
    if outcome is None:

        return None, "unsupported"
    return outcome, None

def check_response(expected_response, snapshot: dict, setup=None) -> tuple:

    if setup:
        try:
            snapshot = criteria.setup_masked(snapshot, setup)
        except ValueError as exc:
            return None, f"unsupported: {exc}"

    if isinstance(expected_response, list):
        any_supported = False
        saw_damage_taken = False
        for single in expected_response:
            outcome, _ = _check_single(single, snapshot)
            if outcome is not None:
                any_supported = True
                if outcome == "hit":
                    return "hit", None
                elif outcome == "damage_taken":
                    saw_damage_taken = True
        if not any_supported:
            return None, "unsupported"
        if saw_damage_taken:
            return "damage_taken", None
        return "miss", None
    return _check_single(expected_response, snapshot)

def grade_response(expected_response, snapshot: dict, setup=None) -> tuple:

    outcome, reason = check_response(expected_response, snapshot, setup)
    if outcome is None:
        return None, reason
    if outcome == "hit":
        return grader.GOOD, None
    return grader.AGAIN, None
