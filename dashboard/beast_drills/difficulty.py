from . import scrimmage

MIN_HANDICAP = -4
MAX_HANDICAP = 4

RUNGS = (
    ("sa", 1, "favoured"),
    ("drive", 1, "pressured"),
    ("vitality", 10, "pressured"),
)

RECOVERY_RUNG = 4

FULL_VITALITY = 100
FULL_DRIVE = 6
MAX_SA = 3

START_SA = 0

def _clamp(value, low, high):
    return max(low, min(high, value))

def parameters_for(cpu_level, handicap=0):

    cpu_level = _clamp(int(cpu_level or scrimmage.MIN_DIFFICULTY),
                       scrimmage.MIN_DIFFICULTY, scrimmage.MAX_DIFFICULTY)
    handicap = _clamp(int(handicap or 0), MIN_HANDICAP, MAX_HANDICAP)

    p1 = {"vitality": FULL_VITALITY, "drive": FULL_DRIVE, "sa": START_SA}
    p2 = {"vitality": FULL_VITALITY, "drive": FULL_DRIVE, "sa": START_SA}

    pressured, favoured = (p1, p2) if handicap > 0 else (p2, p1)

    for depth, (name, amount, lands_on) in enumerate(RUNGS, start=1):
        if abs(handicap) < depth:
            break
        if lands_on == "favoured":
            favoured[name] += amount
        else:
            pressured[name] -= amount

    for side in (p1, p2):
        side["vitality"] = _clamp(side["vitality"], 25, FULL_VITALITY)
        side["drive"] = _clamp(side["drive"], 0, FULL_DRIVE)
        side["sa"] = _clamp(side["sa"], 0, MAX_SA)

    p1["drive_recovery"] = p2["drive_recovery"] = "standard"
    if abs(handicap) >= RECOVERY_RUNG:

        (p2 if handicap > 0 else p1)["drive_recovery"] = "refill"
    return {"cpu_level": cpu_level, "handicap": handicap, "p1": p1, "p2": p2}

def harder(cpu_level, handicap):

    if handicap < MAX_HANDICAP:
        return cpu_level, handicap + 1
    if cpu_level < scrimmage.MAX_DIFFICULTY:

        return cpu_level + 1, 0
    return cpu_level, handicap

def easier(cpu_level, handicap):

    if handicap > MIN_HANDICAP:
        return cpu_level, handicap - 1
    if cpu_level > scrimmage.MIN_DIFFICULTY:
        return cpu_level - 1, 0
    return cpu_level, handicap

def describe(cpu_level, handicap):

    if not handicap:
        return f"CPU {cpu_level}, even gauges"
    applied = [name for depth, (name, _amount, _side) in enumerate(RUNGS, start=1)
               if abs(handicap) >= depth]
    pressured = "you" if handicap > 0 else "the dummy"
    favoured = "the dummy" if handicap > 0 else "you"
    parts = []
    if "sa" in applied:
        parts.append(f"super for {favoured}")
    taken = [n for n in applied if n != "sa"]
    if taken:
        parts.append(f"{', '.join(taken)} down for {pressured}")
    text = f"CPU {cpu_level}, " + ", ".join(parts)
    if abs(handicap) >= RECOVERY_RUNG:
        text += f", refill for {favoured}"
    return text
