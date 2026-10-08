HEALTH_PERCENTS = tuple(range(0, 101, 10))
DRIVE_STOCKS = tuple(range(0, 7))
SA_STOCKS = tuple(range(0, 4))

CPU_LEVELS = tuple(range(1, 9))

RECOVERY_MODES = ("refill", "fixed", "standard")

DEFAULTS = {
    "health": 100,
    "drive": 6,
    "sa": 0,
    "health_recovery": "refill",
    "drive_recovery": "refill",
    "sa_recovery": "refill",
}

_RECOVERY_HELP = "one of " + ", ".join(RECOVERY_MODES)

SPEC = {
    "health": (HEALTH_PERCENTS, "a percentage in steps of 10, 0 to 100"),
    "drive": (DRIVE_STOCKS, "0 to 6"),
    "sa": (SA_STOCKS, "0 to 3"),
    "health_recovery": (RECOVERY_MODES, _RECOVERY_HELP),
    "drive_recovery": (RECOVERY_MODES, _RECOVERY_HELP),
    "sa_recovery": (RECOVERY_MODES, _RECOVERY_HELP),
}

_WORD_KEYS = frozenset(k for k in SPEC if k.endswith("_recovery"))

PAIR_KEYS = (
    "health", "health_recovery",
    "drive", "drive_recovery",
    "sa", "sa_recovery",
)

def parse_pair(key: str, text: str):

    allowed, described = SPEC[key]
    parts = [p.strip() for p in str(text).split(",")]
    if len(parts) > 2:
        return None, [f"{key}: expected one value or two (mine, theirs), "
                      f"got {len(parts)}"]

    out, errors = {}, []
    for part, side in zip(parts, ("mine", "theirs")):
        if part == "":
            continue
        if key in _WORD_KEYS:
            word = part.lower()
            if word not in allowed:
                errors.append(f"{key}: '{part}' is not a mode -- {described}")
                continue
            out[side] = word
            continue
        try:
            number = int(part)
        except ValueError:
            errors.append(f"{key}: '{part}' is not a number -- {described}")
            continue
        if number not in allowed:
            errors.append(f"{key}: {number} is out of range -- {described}")
            continue
        out[side] = number
    if errors:
        return None, errors
    if not out:
        return None, [f"{key}: needs a value"]

    return {side: v for side, v in out.items() if v != DEFAULTS[key]}, []

def render_pair(key: str, value) -> str:

    mine = value.get("mine", DEFAULTS[key])
    theirs = value.get("theirs")
    if theirs is None or theirs == DEFAULTS[key]:
        return str(mine)
    return f"{mine}, {theirs}"

def resolved(key: str, value) -> dict:

    value = value or {}
    return {"mine": value.get("mine", DEFAULTS[key]),
            "theirs": value.get("theirs", DEFAULTS[key])}

def errors(key: str, value) -> list:

    if value is None:
        return []
    if not isinstance(value, dict):
        return [f"{key}: expected an object with mine/theirs"]
    allowed, described = SPEC[key]
    found = []
    for side in ("mine", "theirs"):
        if side not in value:
            continue
        if value[side] not in allowed:
            found.append(f"{key}.{side}: {value[side]!r} is out of range -- {described}")
    extra = set(value) - {"mine", "theirs"}
    if extra:
        found.append(f"{key}: unknown side(s) {', '.join(sorted(extra))}")
    return found

def cpu_level_errors(value) -> list:
    if value is None:
        return []
    if value not in CPU_LEVELS:
        return [f"cpu-level: {value!r} is out of range -- 1 to 8"]
    return []
