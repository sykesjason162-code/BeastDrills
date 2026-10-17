from . import scoring

_PAIRS = [
    ("throw", "got_thrown"),
    ("throw_tech", "throw_got_teched"),
    ("throw_whiff", "throw_missed_me"),
    ("reversal", "got_reversaled"),
    ("parry", "got_parried"),
    ("block", "got_blocked"),
    ("backroll", "got_backrolled"),
    ("anti_air", "got_anti_aired"),
    ("jump_attack", "got_jump_attacked"),
    ("hit", "got_hit"),
    ("hit_high", "got_hit_high"),
    ("hit_mid", "got_hit_mid"),
    ("hit_low", "got_hit_low"),
    ("drive_impact", "got_drive_impacted"),
    ("counter_hit", "got_counter_hit"),
    ("punish_counter_hit", "got_punish_countered"),
    ("drive_impact_counter", "got_drive_impact_countered"),
    ("drive_impact_vs_di", "lost_di_clash"),
    ("hit_confirm", "got_hit_confirmed"),
    ("non_hit_confirm", "blocked_their_string"),
    ("stuff_dash", "dash_got_stuffed"),
    ("stuff_drive_rush", "drive_rush_got_stuffed"),
]
MIRROR = {}
for _a, _b in _PAIRS:
    MIRROR[_a] = _b
    MIRROR[_b] = _a

UNMIRRORABLE = frozenset({
    "whiff", "block_miss", "parry_miss", "parry_whiff", "perfect_parry", "no_backroll",
})

MODE_NAMES = {
    1: "Arcade",
    3: "Versus",
    4: "Versus CPU",
    14: "Ranked",
    15: "Casual",
    16: "Battle Hub",
    17: "Custom Room",
    20: "CPU Exam",
    21: "Battle Hub CPU",
    22: "Learning AI",
}

CTRL_PLAYER, CTRL_NET_PLAYER, CTRL_CPU = 0, 1, 2

def mode_name(mode) -> str:
    try:
        return MODE_NAMES.get(int(mode), f"Mode {int(mode)}")
    except (TypeError, ValueError):
        return "Unknown mode"

def mirror_tally(tally: dict) -> dict:

    out = {}
    for key, count in (tally or {}).items():
        if key in UNMIRRORABLE:
            continue
        out[MIRROR.get(key, key)] = count
    return out

def _side(value):
    return value if value in (0, 1) else None

def perspective(event: dict) -> dict:

    local = _side(event.get("local_side"))
    side = 0 if local is None else local
    other = 1 - side
    chars = list(event.get("fighter_characters") or [None, None]) + [None, None]
    ctrl = list(event.get("ctrl") or [-1, -1]) + [-1, -1]
    ai = list(event.get("ai_level") or [-1, -1]) + [-1, -1]
    tally = event.get("tally") or {}
    return {
        "player_side": local,
        "character_id": chars[side],
        "opponent_id": chars[other],
        "opponent_kind": {CTRL_CPU: "cpu", CTRL_NET_PLAYER: "online",
                          CTRL_PLAYER: "local"}.get(ctrl[other], "unknown"),
        "opponent_cpu_level": ai[other] if ctrl[other] == CTRL_CPU else None,
        "mirrored": side == 1,
        "tally": mirror_tally(tally) if side == 1 else dict(tally),
    }

def round_won(won_by, player_side):

    if player_side is None:
        return None
    won_by = set(won_by or [])
    if won_by == {player_side}:
        return True
    if won_by == {1 - player_side}:
        return False
    return None

def grade_round(event: dict, drills=None) -> dict:

    who = perspective(event)
    won = round_won(event.get("won_by"), who["player_side"])
    analysis = scoring.analyse_round(who["tally"], drills or [], who["character_id"], won)
    return {
        "match_id": event.get("match_id"),
        "round": int(event.get("round") or 0),
        "mode": event.get("mode"),
        "online": bool(event.get("online")),
        "player_side": who["player_side"],
        "character_id": who["character_id"],
        "opponent_id": who["opponent_id"],
        "opponent_kind": who["opponent_kind"],
        "won": won,
        "finish": event.get("finish"),
        "score": analysis["score"],
        "exchanges": analysis["exchanges"],
        "worst": analysis["worst"],
        "worst_count": analysis["worst_count"],
        "mirrored": who["mirrored"],
        "tally": who["tally"],

        "side_by": event.get("side_by"),
    }

def grade_match(event: dict, rounds: list, drills=None) -> dict:

    who = perspective(event)
    if who["opponent_kind"] == "unknown" and rounds:

        who["opponent_kind"] = rounds[0].get("opponent_kind") or "unknown"
    side = who["player_side"]
    wins = list(event.get("wins") or [0, 0]) + [0, 0]
    winner = event.get("winner_side")
    won = None if side is None or winner not in (0, 1) else winner == side
    summary = scoring.summarise_set(
        [{"tally": r.get("tally") or {}, "won": r.get("won"), "score": r.get("score")}
         for r in rounds or []],
        drills or [], who["character_id"])
    mine = wins[side] if side is not None else wins[0]
    theirs = wins[1 - side] if side is not None else wins[1]
    return {
        "match_id": event.get("match_id"),
        "mode": event.get("mode"),
        "mode_name": mode_name(event.get("mode")),
        "online": bool(event.get("online")),
        "player_side": side,
        "character_id": who["character_id"],
        "opponent_id": who["opponent_id"],
        "opponent_kind": who["opponent_kind"],
        "opponent_cpu_level": who["opponent_cpu_level"],
        "rounds": int(event.get("rounds") or len(rounds or [])),
        "rounds_to_win": event.get("rounds_to_win"),
        "wins": mine,
        "losses": theirs,
        "won": won,
        "completed": bool(event.get("completed")),
        "how": event.get("how"),
        "score": summary["score"],
        "weaknesses": summary["weaknesses"],
        "recommendations": summary["recommendations"],
        "unaddressed": summary["unaddressed"],
        "tally": summary["tally"],
    }

def _ranked(pairs):
    return [{"weakness": k, "count": n} for k, n in pairs or []]

def view(rows: list) -> list:

    out = []
    for m in rows or []:
        m = dict(m)
        tally = m.get("tally")
        if tally is None:
            tally = {}
            for r in m.get("rounds_list") or []:
                for k, v in (r.get("tally") or {}).items():
                    tally[k] = tally.get(k, 0) + int(v or 0)
            m["tally"] = tally
            m["weaknesses"] = scoring.rank_weaknesses(tally)
        scored = scoring.score_tally(tally, scoring.GIVER_KEYS, scoring.RECEIVER_KEYS)
        m["giver_events"] = scored["giver_events"]
        m["receiver_events"] = scored["receiver_events"]
        m["exchanges"] = scored["exchanges"]
        if m.get("score") is None:
            m["score"] = scored["score"]
        m["weaknesses"] = _ranked(m.get("weaknesses"))
        m["unaddressed"] = _ranked(m.get("unaddressed"))
        m.setdefault("recommendations", [])
        m["mode_name"] = mode_name(m.get("mode"))
        rounds = []
        for r in m.get("rounds_list") or []:
            r = dict(r)
            r["weaknesses"] = _ranked(scoring.rank_weaknesses(r.get("tally") or {}))
            rounds.append(r)
        m["rounds_list"] = rounds
        out.append(m)
    return out

def _summarise(rows: list) -> dict:

    tally: dict = {}
    out = {k: 0 for k in ("matches", "wins", "losses", "rounds", "rounds_won", "rounds_lost")}
    by_opp: dict = {}
    for r in rows:
        for k in out:
            out[k] += int(r.get(k) or 0)
        for k, v in (r.get("tally") or {}).items():
            tally[k] = tally.get(k, 0) + int(v or 0)
        o = by_opp.setdefault(r.get("opponent_id") or "unknown",
                              {"opponent_id": r.get("opponent_id") or "unknown",
                               "matches": 0, "wins": 0, "losses": 0, "tally": {}})
        for k in ("matches", "wins", "losses"):
            o[k] += int(r.get(k) or 0)
        for k, v in (r.get("tally") or {}).items():
            o["tally"][k] = o["tally"].get(k, 0) + int(v or 0)
    scored = scoring.score_tally(tally, scoring.GIVER_KEYS, scoring.RECEIVER_KEYS)
    opponents = []
    for o in by_opp.values():
        s = scoring.score_tally(o.pop("tally"), scoring.GIVER_KEYS, scoring.RECEIVER_KEYS)
        o["score"] = s["score"] if s["exchanges"] else None
        opponents.append(o)
    opponents.sort(key=lambda o: (-o["matches"], o["opponent_id"]))
    out.update({
        "score": scored["score"] if scored["exchanges"] else None,
        "exchanges": scored["exchanges"],
        "giver_events": scored["giver_events"],
        "receiver_events": scored["receiver_events"],
        "weaknesses": _ranked(scoring.rank_weaknesses(tally)),

        "strengths": _ranked(scoring.rank_weaknesses(tally, scoring.GIVER_KEYS)),
        "opponents": opponents,
    })
    return out

def overall(rows: list) -> dict:

    out = {"all": _summarise(rows)}
    for char in sorted({r["character_id"] for r in rows}):
        out[char] = _summarise([r for r in rows if r["character_id"] == char])
    return out

BADGE_MIN_MATCHES = 3

def _skill(wins, losses):

    return (wins + 1) / (wins + losses + 2)

def _rank(records: dict) -> dict:

    if not records:
        return records
    most = max(r["matches"] for r in records.values()) or 1
    skills = {c: _skill(r["wins"], r["losses"]) for c, r in records.items()}
    lo, hi = min(skills.values()), max(skills.values())
    for c, r in records.items():
        decided = r["wins"] + r["losses"]
        r["rate"] = round(100 * r["wins"] / decided) if decided else None
        r["skill"] = round(skills[c], 4)

        r["tier"] = round((skills[c] - lo) / (hi - lo), 4) if hi > lo else round(skills[c], 4)
        r["usage"] = round(r["matches"] / most, 4)
    return records

def _extremes(records: dict):
    eligible = [(c, r) for c, r in records.items() if r["matches"] >= BADGE_MIN_MATCHES]
    if len(eligible) < 2:
        return None, None
    best = max(eligible, key=lambda cr: (cr[1]["skill"], cr[1]["matches"]))
    worst = min(eligible, key=lambda cr: (cr[1]["skill"], -cr[1]["matches"]))
    if best[1]["skill"] == worst[1]["skill"]:
        return None, None
    return best[0], worst[0]

def roster(rows: list, player: str | None = None) -> dict:

    as_char: dict = {}
    vs_char: dict = {}
    total = 0
    for r in rows or []:
        char, opp = r.get("character_id"), r.get("opponent_id") or "unknown"
        m, w, l = int(r.get("matches") or 0), int(r.get("wins") or 0), int(r.get("losses") or 0)
        total += m
        if char:
            a = as_char.setdefault(char, {"matches": 0, "wins": 0, "losses": 0})
            a["matches"] += m; a["wins"] += w; a["losses"] += l
        if opp != "unknown" and (player is None or char == player):
            v = vs_char.setdefault(opp, {"matches": 0, "wins": 0, "losses": 0})
            v["matches"] += m; v["wins"] += w; v["losses"] += l
    _rank(as_char)
    _rank(vs_char)
    for r in as_char.values():
        r["share"] = round(r["matches"] / total, 4) if total else 0
    best_as, worst_as = _extremes(as_char)
    best_vs, worst_vs = _extremes(vs_char)
    return {"as_char": as_char, "vs_char": vs_char, "player": player, "total": total,
            "best_as": best_as, "worst_as": worst_as,
            "best_vs": best_vs, "worst_vs": worst_vs}
