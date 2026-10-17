from .wongscript import TRAINS_CATEGORIES, TRAINS_FOR_CATEGORIES

RECEIVER_KEYS = list(TRAINS_CATEGORIES)

GIVER_KEYS = list(TRAINS_FOR_CATEGORIES)

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

    newest = latest_record(database, character_id, dummy_character_id)
    out = []
    for rec in (newest or {}).get("recommendations") or []:
        drill_id = rec.get("drill_id") if isinstance(rec, dict) else None
        if drill_id and drill_id not in out:
            out.append(drill_id)
    return out

def _records(database, character_id, dummy_character_id):
    pools = []
    by_character = (database or {}).get("scrimmage") or {}
    for char, dummies in by_character.items():
        if character_id is not None and char != character_id:
            continue
        for dummy, state in (dummies or {}).items():
            if dummy_character_id is not None and dummy != dummy_character_id:
                continue
            for session in (state or {}).get("sessions") or []:
                pools.append(session)

    for char, opponents in ((database or {}).get("matches") or {}).items():
        if character_id is not None and char != character_id:
            continue
        for opponent, state in (opponents or {}).items():
            if dummy_character_id is not None and opponent != dummy_character_id:
                continue
            latest = (state or {}).get("latest")
            if latest:
                pools.append(latest)
    return pools

def latest_record(database, character_id=None, dummy_character_id=None):

    pools = _records(database, character_id, dummy_character_id)
    if not pools and dummy_character_id is not None:
        pools = _records(database, character_id, None)
    if not pools:
        return None

    return max(pools, key=lambda r: r.get("at") or "")

def reason_for(database, drill_id, character_id=None, dummy_character_id=None):

    newest = latest_record(database, character_id, dummy_character_id)
    for rec in (newest or {}).get("recommendations") or []:
        if isinstance(rec, dict) and rec.get("drill_id") == drill_id:
            source = "match" if newest.get("match_id") else "scrimmage"
            what = str(rec.get("weakness") or "").replace("_", " ")
            count = rec.get("weakness_count")
            return (f"Moved up by your last {source}: {what} x{count}"
                    if what and count else f"Moved up by your last {source}")
    return None

def reorder_by_recommendations(due, recommended):

    if not recommended:
        return list(due)
    rank = {drill_id: i for i, drill_id in enumerate(recommended)}

    return [d for _, _, d in sorted(
        ((rank.get(d.get("id"), len(rank)), i, d) for i, d in enumerate(due)),
        key=lambda t: (t[0], t[1]))]

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
    }

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
