ATOMS = {
    "hit": "p2_hit",
    "got_hit": "p1_hit",
    "block": "p1_blocked",
    "got_blocked": "p2_blocked",
    "combo": "combo",
    "attack": "p1_attacked",
    "throw": "p2_throw_connected",
    "throw_tech": "p1_throw_teched",
    "parry": "p2_parried",
    "perfect_parry": "p2_perfect_parried",
    "counter_hit": "p2_counter_dm_flag",
    "punish_counter": "p2_counter_fw_flag",
    "reversal": "p1_reversal",
    "anti_air": "p2_hit_while_airborne",
    "wakeup": "p2_wakeup_seen",
    "backroll": "p1_backroll",

    "got_thrown": "p1_thrown",
    "got_counter_hit": "p1_counter_hit",
    "got_punish_countered": "p1_punish_countered",
    "got_drive_impacted": "p1_drive_impacted",
    "got_anti_aired": "p1_anti_aired",

    "punish_counter_hit": "p2_counter_fw_flag",
    "drive_impact": "p2_hit_after_drive_impact",
    "drive_impact_counter": "p2_hit_after_di_counter",
    "drive_impact_vs_di": "p2_hit_after_di_clash",
    "stuff_dash": "p2_hit_after_dash",

    "stuff_drive_rush": "p2_ch_after_drive_rush",
}

NOT_ORDERABLE = ("do_nothing",)

AGAINST_ATOMS = ("got_hit", "got_thrown", "got_counter_hit",
                 "got_punish_countered", "got_drive_impacted",
                 "got_anti_aired", "got_blocked")

def rep_avoided(snapshot: dict, against) -> bool:

    if not against:
        return True
    names = [against] if isinstance(against, str) else list(against)
    for name in names:
        if name not in AGAINST_ATOMS:
            raise ValueError(
                f"against: cannot name {name!r} -- only {', '.join(AGAINST_ATOMS)}")
        if snapshot.get(ATOMS[name]):
            return False
    return True

ALIASES = {

    "pressure": "got_blocked > hit",

    "hit_confirm": "hit > combo",
    "block_then_punish": "block > hit",
}

MAX_DEPTH = 8

SETUP_ATOMS = ("got_hit", "got_blocked")

def setup_masked(snapshot: dict, setup) -> dict:

    if not setup:
        return snapshot
    names = [setup] if isinstance(setup, str) else list(setup)
    masked = dict(snapshot)
    for name in names:
        if name not in SETUP_ATOMS:
            raise ValueError(
                f"setup: cannot name {name!r} -- only {', '.join(SETUP_ATOMS)} "
                f"(it may only excuse what happens TO you, never a success signal)")
        masked[ATOMS[name]] = False
    return masked

def is_expression(text) -> bool:

    return isinstance(text, str) and ">" in text

def expand(text: str, _depth: int = 0) -> str:

    if _depth > MAX_DEPTH:
        raise ValueError(f"alias expansion too deep near {text!r}")
    out = []
    for branch in text.split(","):
        terms = [t.strip() for t in branch.split(">") if t.strip()]
        expanded = []
        for term in terms:
            if term in ALIASES:
                sub = expand(ALIASES[term], _depth + 1)
                if "," in sub:

                    if len(terms) > 1:
                        raise ValueError(
                            f"alias {term!r} holds alternatives and cannot be "
                            f"used inside a sequence")
                    expanded.append(sub)
                else:
                    expanded.append(sub)
            else:
                expanded.append(term)
        out.append(" > ".join(expanded))
    return ", ".join(out)

def _looks_like_a_move(term: str) -> bool:

    lowered = term.lower()
    if any(ch in term for ch in ".+~"):
        return True
    if any(ch.isdigit() for ch in term):
        return True
    return lowered in {"dr", "di", "od", "sa1", "sa2", "sa3", "ca", "dp"}

def parse(text: str) -> list:

    alternatives = []
    for branch in expand(text).split(","):
        seq = [t.strip() for t in branch.split(">") if t.strip()]
        if not seq:
            continue
        for term in seq:
            if term not in ATOMS:

                why = (" -- that looks like a move, and a sequence names"
                       " outcomes (what happened), not the moves you threw"
                       ) if _looks_like_a_move(term) else ""
                raise ValueError(
                    f"unknown term {term!r}{why}. known: {', '.join(sorted(ATOMS))}"
                    f" (aliases: {', '.join(sorted(ALIASES))})")
        alternatives.append(seq)
    if not alternatives:
        raise ValueError(f"no criteria in {text!r}")
    return alternatives

def evaluate(text: str, snapshot: dict):

    verdict, _ = explain(text, snapshot)
    return verdict

def explain(text: str, snapshot: dict):

    seen = snapshot.get("seen_at")
    if not isinstance(seen, dict):

        return None, "no seen_at in the snapshot"

    facts = []
    hits = snapshot.get("p1_hit_count")
    if hits is not None:
        facts.append(f"p1_hit_count={hits}")
    ticks = snapshot.get("rep_ticks")
    if ticks is not None:
        facts.append(f"rep_ticks={ticks}")
    if seen:
        facts.append("saw " + ", ".join(
            f"{k}@{v}" for k, v in sorted(seen.items(), key=lambda kv: kv[1])))
    trailer = ("  [" + "; ".join(facts) + "]") if facts else ""

    reasons = []
    for sequence in parse(text):
        ticks = [seen.get(ATOMS[term]) for term in sequence]
        missing = [t for t, tick in zip(sequence, ticks) if tick is None]
        if missing:
            reasons.append(f"{' > '.join(sequence)}: never happened: "
                           + ", ".join(missing))
            continue
        if all(a < b for a, b in zip(ticks, ticks[1:])):
            return "hit", None
        reasons.append(
            f"{' > '.join(sequence)}: all happened, wrong order: "
            + ", ".join(f"{t}@{tick}" for t, tick in zip(sequence, ticks)))
    return "miss", "; ".join(reasons) + trailer
