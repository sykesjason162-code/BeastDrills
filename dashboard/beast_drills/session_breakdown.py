from . import criteria, response_check

def _label(expected, combo=None):

    if expected is None and combo:
        return combo
    if expected is None:
        return "(none)"
    if isinstance(expected, list):
        return ", ".join(str(e) for e in expected)
    return str(expected)

def per_slot(reps: list) -> list:

    groups: dict = {}
    for rep in reps:
        slot = rep.get("slot")
        key = (slot, _label(rep.get("expected_response"), rep.get("expected_combo")))
        row = groups.setdefault(key, {
            "slot": slot,
            "criteria": key[1],
            "attempts": 0, "successes": 0, "misses": 0,
            "hit_taken": 0, "masked": 0, "pressed": 0,
        })
        row["attempts"] += 1

        outcome = rep.get("outcome")
        snapshot = rep.get("snapshot") or {}
        if snapshot.get("p1_hit"):
            row["hit_taken"] += 1

        if outcome == "hit":
            row["successes"] += 1
            continue
        row["misses"] += 1

        if "do_nothing" in row["criteria"] and snapshot.get("p1_attacked"):
            row["pressed"] += 1

        if outcome == "damage_taken":
            masked, _ = response_check.check_response(
                rep.get("expected_response"), snapshot, setup=["got_hit"])
            if masked == "hit":
                row["masked"] += 1

    rows = list(groups.values())

    rows.sort(key=lambda r: (r["slot"] is None, r["slot"] if r["slot"] is not None else 0))
    return rows

def summarise(reps: list) -> dict:

    rows = per_slot(reps)
    return {
        "slots": rows,
        "attempts": sum(r["attempts"] for r in rows),
        "successes": sum(r["successes"] for r in rows),
        "misses": sum(r["misses"] for r in rows),
        "hit_taken": sum(r["hit_taken"] for r in rows),
        "masked": sum(r["masked"] for r in rows),
        "pressed": sum(r["pressed"] for r in rows),
    }

def lines(breakdown: dict) -> list:

    out = []
    for row in breakdown.get("slots") or []:
        where = f"Slot {row['slot']}" if row["slot"] is not None else "All reps"
        out.append(f"{where}  {row['criteria']}")
        out.append(f"    {row['successes']}/{row['attempts']} success"
                   + (f", {row['misses']} missed" if row["misses"] else ""))
        if row["masked"]:
            out.append(f"    {row['masked']} landed but got clipped -- not counted")
        if row.get("pressed"):
            n = row["pressed"]
            out.append(f"    {n} of those {'was' if n == 1 else 'were'} an attack coming out")

    total = breakdown.get("attempts") or 0
    if total:
        out.append(f"Total  {breakdown['successes']}/{total}")
    if breakdown.get("hit_taken"):

        out.append(f"Hit {breakdown['hit_taken']}x this session (does not reduce your score)")
    return out
