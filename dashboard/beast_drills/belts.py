from __future__ import annotations

BELTS = [
    ("white", "White", "Rookie"),
    ("yellow", "Yellow", "Iron / Bronze"),
    ("blue", "Blue", "Silver / Gold"),
    ("red", "Red", "Platinum / Diamond"),
    ("black", "Black", "Master"),
]
BELT_INDEX = {b[0]: i for i, b in enumerate(BELTS)}

SKILLS = [
    ("movement", "Movement", "white"),
    ("reaction", "Reaction", "white"),
    ("buttons", "Buttons and layout", "white"),
    ("throw", "Throws", "white"),
    ("dash", "Forward and back dash", "white"),
    ("jump_attack", "Jump attacks", "yellow"),
    ("anti_air", "Anti-air", "yellow"),
    ("reverse_di", "Reverse Drive Impact", "yellow"),
    ("block", "Blocking", "yellow"),
    ("cancel_combo", "Cancel combos", "yellow"),
    ("drive_rush", "Drive Rush", "yellow"),
    ("parry", "Parry", "blue"),
    ("punish_counter", "Punish counters", "blue"),
    ("ranges", "Character ranges", "blue"),
    ("oki", "Oki-waza", "blue"),
    ("ate_waza", "Ate-waza", "blue"),
    ("sashi_kaeshi", "Sashi-kaeshi", "blue"),
    ("corner_pressure", "Corner pressure", "blue"),
    ("pressure", "Pressure", "blue"),
    ("combo_easy", "Combos (easy)", "blue"),
    ("zoning", "Zoning", "blue"),
    ("combo_medium", "Combos (medium)", "red"),
    ("perfect_parry", "Perfect parry", "red"),
    ("baiting", "Baiting", "red"),
    ("counter_hit", "Counter hits", "red"),
    ("corner_defense", "Corner defense", "red"),
    ("jump_in", "Jumping in", "red"),
    ("anti_zoning", "Anti-zoning", "red"),
    ("combo_hard", "Advanced combos", "black"),
    ("meter_waste", "Wasting their meter", "black"),
]
SKILL = {s[0]: {"id": s[0], "label": s[1], "belt": s[2]} for s in SKILLS}

MATCH_ONLY = frozenset({"meter_waste"})

DIFFICULTY_RANK = {"very-easy": 0, "easy": 1, "medium": 2, "hard": 3, "very-hard": 4}

START_RANK = DIFFICULTY_RANK["easy"]

COMBO_BY_DIFFICULTY = {
    "very-easy": "cancel_combo",
    "easy": "combo_easy",
    "medium": "combo_medium",
    "hard": "combo_hard",
    "very-hard": "combo_hard",
}

PASS_RATE = 0.70
DRILLS_PER_SKILL = 3
MIN_ATTEMPTS = 10

FIELD = "belt_drill"
COMBO = "combo"

def parse_belt_drill(text):

    raw = [t.strip().lower().replace("-", "_") for t in str(text or "").split(",")]
    raw = [t for t in raw if t]
    if not raw or raw[0] in ("no", "none", "off", "false"):
        return None, None
    skill, rest = raw[0], raw[1:]
    if skill != COMBO and skill not in SKILL:
        return None, (f"belt-drill: unknown skill {skill!r} -- one of "
                      f"{', '.join(k.replace('_', '-') for k in SKILL)}, or combo")
    value = {"skill": skill}
    if rest:
        if len(rest) > 1 or rest[0] not in BELT_INDEX:
            return None, (f"belt-drill: after the skill, only a belt "
                          f"({', '.join(BELT_INDEX)}), got {', '.join(rest)!r}")
        value["belt"] = rest[0]
    return value, None

def render_belt_drill(value) -> str | None:

    if not is_belt_drill({FIELD: value}):
        return None
    out = value["skill"].replace("_", "-")
    return f"{out}, {value['belt']}" if value.get("belt") else out

def is_belt_drill(drill: dict) -> bool:
    value = (drill or {}).get(FIELD)
    return (isinstance(value, dict)
            and (value.get("skill") in SKILL or value.get("skill") == COMBO))

def placement(drill: dict):

    if not is_belt_drill(drill):
        return None
    value = drill[FIELD]
    skill = value.get("skill")
    difficulty = drill.get("difficulty")
    if skill in SKILL:
        explicit = value.get("belt")
        if explicit in BELT_INDEX:
            return skill, explicit
        base = BELT_INDEX[SKILL[skill]["belt"]]
        bump = max(0, DIFFICULTY_RANK.get(difficulty, START_RANK) - START_RANK)
        return skill, BELTS[min(len(BELTS) - 1, base + bump)][0]
    if skill == COMBO and difficulty in COMBO_BY_DIFFICULTY:
        skill = COMBO_BY_DIFFICULTY[difficulty]
        return skill, SKILL[skill]["belt"]
    return None

def _applies(drill: dict, character_id: str) -> bool:

    owner = drill.get("character_id")
    return owner in (None, "", character_id)

def drill_stats(reviews: list, character_id: str) -> dict:

    out: dict = {}
    for r in reviews or []:
        if r.get("character_id") != character_id:
            continue
        a, s = out.get(r["drill_id"], (0, 0))
        out[r["drill_id"]] = (a + int(r.get("attempts") or 0), s + int(r.get("successes") or 0))
    return out

def _passed(attempts: int, successes: int) -> bool:
    return attempts >= MIN_ATTEMPTS and successes / attempts >= PASS_RATE

def tag(drill: dict):

    where = placement(drill)
    if where is None:
        return None
    skill, belt = where
    return {"belt": belt, "belt_name": BELTS[BELT_INDEX[belt]][1],
            "skill": skill, "skill_label": SKILL[skill]["label"]}

def belt_for(drills: list, reviews: list, character_id: str) -> dict:

    stats = drill_stats(reviews, character_id)
    placed: dict = {}
    unplaced = 0
    for d in drills or []:
        if not _applies(d, character_id):
            continue
        where = placement(d)
        if where is None:
            unplaced += 1
            continue
        a, s = stats.get(d.get("id"), (0, 0))
        placed.setdefault((where[1], where[0]), []).append(_passed(a, s))

    belts_out = []
    earned_through = -1
    still_earning = True
    for i, (bid, name, ranks) in enumerate(BELTS):
        skills_here = [s for s in SKILLS
                       if s[2] == bid or any(k == (bid, s[0]) for k in placed)]
        rows, any_drills, all_passed = [], False, True
        for sid, label, _base in skills_here:
            results = placed.get((bid, sid), [])
            if sid in MATCH_ONLY:
                rows.append({"id": sid, "label": label, "drills": 0, "passed": 0,
                             "needed": 0, "status": "match_only"})
                continue
            if not results:
                rows.append({"id": sid, "label": label, "drills": 0, "passed": 0,
                             "needed": 0, "status": "needs_drills"})
                continue
            any_drills = True
            needed = min(DRILLS_PER_SKILL, len(results))
            got = sum(results)
            done = got >= needed
            all_passed &= done
            rows.append({"id": sid, "label": label, "drills": len(results), "passed": got,
                         "needed": needed, "status": "passed" if done else "working"})
        earned = still_earning and any_drills and all_passed
        if earned:
            earned_through = i
        else:
            still_earning = False
        belts_out.append({"id": bid, "name": name, "ranks": ranks,
                          "earned": earned, "skills": rows})

    belt = BELTS[earned_through][0] if earned_through >= 0 else None
    nxt = BELTS[earned_through + 1][0] if earned_through + 1 < len(BELTS) else None
    return {"character_id": character_id, "belt": belt,
            "belt_name": BELTS[earned_through][1] if belt else None,
            "next": nxt, "belts": belts_out, "unplaced": unplaced}
