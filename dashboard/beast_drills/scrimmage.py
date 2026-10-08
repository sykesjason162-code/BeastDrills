from .wongscript import TRAINS_CATEGORIES, TRAINS_FOR_CATEGORIES

RECEIVER_KEYS = list(TRAINS_CATEGORIES)

GIVER_KEYS = list(TRAINS_FOR_CATEGORIES)

ROUNDS_PER_SET = 3

def configure(rounds_per_set=None, max_cpu_level=None) -> None:

    global ROUNDS_PER_SET, MATCHES_PER_SESSION, MAX_DIFFICULTY
    if rounds_per_set and rounds_per_set > 0:
        ROUNDS_PER_SET = MATCHES_PER_SESSION = int(rounds_per_set)
    if max_cpu_level and max_cpu_level > 0:
        MAX_DIFFICULTY = max(MIN_DIFFICULTY, int(max_cpu_level))

MATCHES_PER_SESSION = ROUNDS_PER_SET

MAX_DIFFICULTY = 6
MIN_DIFFICULTY = 1

def _total(tally, keys):
    return sum(int((tally or {}).get(k, 0) or 0) for k in keys)

def score_tally(tally, giver_keys=None, receiver_keys=None):

    tally = tally or {}
    use_giver = giver_keys is not None
    use_receiver = receiver_keys is not None or not use_giver
    if receiver_keys is None:
        receiver_keys = RECEIVER_KEYS
    if giver_keys is None:
        giver_keys = GIVER_KEYS

    giver_events = _total(tally, GIVER_KEYS)
    receiver_events = _total(tally, RECEIVER_KEYS)
    exchanges = giver_events + receiver_events

    buckets = {}
    if exchanges == 0:
        score = 0.0
        if use_receiver:
            buckets["receiver"] = 0.0
        if use_giver:
            buckets["giver"] = 0.0
    else:
        weight = 50.0 if (use_giver and use_receiver) else 100.0
        score = 0.0
        if use_receiver:
            bad = _total(tally, receiver_keys)
            b = weight * (1.0 - min(1.0, bad / exchanges))
            buckets["receiver"] = round(b, 1)
            score += b
        if use_giver:
            good = _total(tally, giver_keys)
            b = weight * min(1.0, good / exchanges)
            buckets["giver"] = round(b, 1)
            score += b

    return {
        "score": round(score, 1),
        "buckets": buckets,
        "exchanges": exchanges,
        "giver_events": giver_events,
        "receiver_events": receiver_events,
    }

def rank_weaknesses(tally, receiver_keys=None):

    keys = receiver_keys if receiver_keys is not None else RECEIVER_KEYS
    counts = [(k, int((tally or {}).get(k, 0) or 0)) for k in keys]
    hits = [(k, n) for k, n in counts if n > 0]

    return sorted(hits, key=lambda kv: (-kv[1], kv[0]))

def recommend_drills(tally, drills, limit=5, character_id=None):

    ranked = rank_weaknesses(tally)
    by_category = {}
    for drill in drills or []:
        if character_id is not None:
            drill_char = drill.get("character_id")
            if drill_char is not None and drill_char != character_id:
                continue
        if drill.get("unsupported"):
            continue
        for category in drill.get("trains") or []:
            by_category.setdefault(category, []).append(drill)

    out, seen = [], set()
    for category, count in ranked:
        for drill in by_category.get(category, []):
            drill_id = drill.get("id")
            if drill_id in seen:
                continue
            seen.add(drill_id)
            out.append({
                "drill_id": drill_id,
                "name": drill.get("name"),
                "weakness": category,
                "weakness_count": count,
            })
            if len(out) >= limit:
                return out
    return out

def unaddressed_weaknesses(tally, drills, character_id=None):

    claimed = set()
    for drill in drills or []:
        if character_id is not None:
            drill_char = drill.get("character_id")
            if drill_char is not None and drill_char != character_id:
                continue
        if drill.get("unsupported"):
            continue
        claimed.update(drill.get("trains") or [])
    return [(k, n) for k, n in rank_weaknesses(tally) if k not in claimed]

def latest_recommendations(database, character_id=None, dummy_character_id=None):

    by_character = (database or {}).get("scrimmage") or {}
    pools = []
    for char, dummies in by_character.items():
        if character_id is not None and char != character_id:
            continue
        for dummy, state in (dummies or {}).items():
            if dummy_character_id is not None and dummy != dummy_character_id:
                continue
            for session in (state or {}).get("sessions") or []:
                pools.append(session)
    if not pools:
        return []

    newest = max(pools, key=lambda s: s.get("at") or "")
    out = []
    for rec in newest.get("recommendations") or []:
        drill_id = rec.get("drill_id") if isinstance(rec, dict) else None
        if drill_id and drill_id not in out:
            out.append(drill_id)
    return out

def reorder_by_recommendations(due, recommended):

    if not recommended:
        return list(due)
    rank = {drill_id: i for i, drill_id in enumerate(recommended)}

    return [d for _, _, d in sorted(
        ((rank.get(d.get("id"), len(rank)), i, d) for i, d in enumerate(due)),
        key=lambda t: (t[0], t[1]))]

def advance_difficulty(current_difficulty, round_results):

    results = list(round_results or [])
    if len(results) < ROUNDS_PER_SET:
        return current_difficulty, "incomplete"
    wins = sum(1 for r in results[:ROUNDS_PER_SET] if r)
    if wins == ROUNDS_PER_SET:
        return min(MAX_DIFFICULTY, current_difficulty + 1), (
            "held" if current_difficulty >= MAX_DIFFICULTY else "advanced")
    if wins == 0:
        return max(MIN_DIFFICULTY, current_difficulty - 1), (
            "held" if current_difficulty <= MIN_DIFFICULTY else "dropped")
    return current_difficulty, "held"

def analyse_round(tally, drills=None, character_id=None, won=None):

    scored = score_tally(tally, GIVER_KEYS, RECEIVER_KEYS)
    ranked = rank_weaknesses(tally)
    worst = ranked[0] if ranked else None
    suggestions = recommend_drills(tally, drills or [], limit=1,
                                   character_id=character_id)
    return {
        "won": won,
        "score": scored["score"],
        "exchanges": scored["exchanges"],
        "worst": worst[0] if worst else None,
        "worst_count": worst[1] if worst else 0,
        "suggestion": suggestions[0] if suggestions else None,
        "lines": _round_lines(scored, worst, suggestions, won),
    }

def _round_lines(scored, worst, suggestions, won):

    out = []
    if won is not None:
        out.append("Round won" if won else "Round lost")
    if scored["exchanges"] == 0:

        out.append("No exchanges to judge this round on.")
        return out
    out.append(f"Score {scored['score']} of 100 over {scored['exchanges']} exchanges")
    if worst:
        out.append(f"Worst: {worst[0].replace('_', ' ')} x{worst[1]}")
    if suggestions:
        out.append(f"Drill for it: {suggestions[0]['name'] or suggestions[0]['drill_id']}")
    return out

def summarise_set(rounds, drills=None, character_id=None):

    rounds = rounds or []
    combined: dict = {}
    for r in rounds:
        for key, count in (r.get("tally") or {}).items():
            combined[key] = combined.get(key, 0) + int(count or 0)

    won = [bool(r.get("won")) for r in rounds]
    scored = score_tally(combined, GIVER_KEYS, RECEIVER_KEYS)
    return {
        "rounds": len(rounds),
        "won": sum(1 for w in won if w),
        "lost": sum(1 for w in won if not w),
        "results": won,
        "score": scored["score"],
        "per_round_scores": [r.get("score") for r in rounds],
        "weaknesses": rank_weaknesses(combined),
        "recommendations": recommend_drills(combined, drills or [],
                                            character_id=character_id),
        "unaddressed": unaddressed_weaknesses(combined, drills or [],
                                              character_id=character_id),
        "tally": combined,
    }

def level_for(state, character_id, dummy_id):

    state = state or {}
    exact = (state.get(character_id) or {}).get(dummy_id)
    if exact and exact.get("difficulty"):
        return int(exact["difficulty"])

    best_at, best_level = "", None
    for _player, versus in state.items():
        record = (versus or {}).get(dummy_id)
        if not record or not record.get("difficulty"):
            continue
        sessions = record.get("sessions") or []
        at = str(sessions[-1].get("at") or "") if sessions else ""
        if best_level is None or at >= best_at:
            best_at, best_level = at, int(record["difficulty"])
    return best_level if best_level is not None else MIN_DIFFICULTY

def set_lines(summary, difficulty_before=None, difficulty_after=None,
              handicap_before=None, handicap_after=None, outcome=None):

    out = [f"{summary['won']} of {summary['rounds']} rounds won"]
    if summary.get("per_round_scores"):
        out.append("Rounds: " + "  ".join(
            f"{s:g}" if s is not None else "-" for s in summary["per_round_scores"]))
    if summary["score"]:
        out.append(f"Score {summary['score']} of 100")

    weaknesses = summary.get("weaknesses") or []
    if weaknesses:
        out.append("What kept happening:")
        for name, count in weaknesses[:3]:
            out.append(f"    {name.replace('_', ' ')} x{count}")

    for pick in (summary.get("recommendations") or [])[:3]:
        out.append(f"Work on: {pick['name'] or pick['drill_id']}")

    for name, count in (summary.get("unaddressed") or [])[:2]:
        out.append(f"No drill trains {name.replace('_', ' ')} (x{count})")

    if outcome == "advanced":
        out.append(f"Next time: harder (CPU {difficulty_after}, handicap {handicap_after})")
    elif outcome == "dropped":
        out.append(f"Next time: easier (CPU {difficulty_after}, handicap {handicap_after})")
    elif outcome:
        out.append(f"Next time: unchanged (CPU {difficulty_after})")
    return out
