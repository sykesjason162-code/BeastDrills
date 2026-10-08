import re

from . import wongscript

MODE_PREFIX = "prefix"

MODE_CONTAINS = "contains"
MODE_POSTFIX = MODE_CONTAINS

_ELLIPSIS = ("...", "…")

GAP = None

def is_gap(token):
    return isinstance(token, str) and token.strip() in _ELLIPSIS

def segments(spec):

    out, current = [], []
    for item in spec:
        if item is GAP:
            if current:
                out.append(current)
            current = []
        else:
            current.append(item)
    if current:
        out.append(current)
    return out

def split_mode(text):

    t = (text or "").strip()
    for e in _ELLIPSIS:
        if t.startswith(e):
            return MODE_POSTFIX, t[len(e):].lstrip(" ,	")
    return MODE_PREFIX, t

MOVEMENT = {
    "MPMK", "MKMP",
    "66MKMP", "66MPMK", "44MKMP", "44MPMK",
    "66", "44",
    "DR", "DRC", "PDR", "RAWDR", "DRIVERUSH",
}

def is_movement(token) -> bool:

    return str(token or "").strip().upper().replace(".", "") in MOVEMENT

_DASH_PREFIX = re.compile(r"^(?:66|44)(?=[0-9A-Za-z])")

_CHARGE_PREFIX = re.compile(r"^\[[1-9]\][0-9A-Za-z]")

_MOVE_WORD_PREFIX = re.compile(r"^(?:DRC?|PDR|HJC|jc|dl)[\s.]*", re.I)

def strip_movement_prefix(token) -> str:

    t = _MOVE_WORD_PREFIX.sub("", str(token or "").strip())
    return _DASH_PREFIX.sub("", t)

_GROUP_REPEAT = re.compile(r"\(([^()]*)\)\s*[xX]\s*(\d+)")
_TOKEN_REPEAT = re.compile(r"^(.*?)\s*[xX]\s*(\d+)$")

MAX_REPEAT = 20

def expand_repeats(text, errors=None, line_no=1):

    if errors is None:
        errors = []
    if not text:
        return text

    def group(m):
        body, n = m.group(1).strip(), int(m.group(2))
        if not 1 <= n <= MAX_REPEAT:
            raise ValueError(f"repeat x{n} is out of range (1-{MAX_REPEAT})")
        return ", ".join([body] * n)

    try:

        for _ in range(MAX_REPEAT):
            new = _GROUP_REPEAT.sub(group, text)
            if new == text:
                break
            text = new

        out = []
        for token in text.split(","):
            token = token.strip()
            if not token:
                continue
            m = _TOKEN_REPEAT.match(token)
            if not m or not m.group(1):
                out.append(token)
                continue
            body, n = m.group(1).strip(), int(m.group(2))
            if not 1 <= n <= MAX_REPEAT:
                raise ValueError(f"repeat x{n} is out of range (1-{MAX_REPEAT})")
            out.extend([body] * n)
    except ValueError as exc:
        errors.append({"line": line_no, "message": str(exc)})
        return None
    return ", ".join(out)

def parse_attack_string(text, errors=None, line_no=1):

    if errors is None:
        errors = []
    text = expand_repeats(text, errors, line_no)
    if text is None:
        return None
    tokens = [t.strip() for t in (text or "").split(",") if t.strip()]
    if not tokens:
        errors.append({"line": line_no, "message": "expected at least one attack"})
        return None

    attacks = []
    for token in tokens:

        if is_gap(token):
            attacks.append(GAP)
            continue

        if is_movement(token):
            continue

        token = strip_movement_prefix(token)

        if _CHARGE_PREFIX.match(token):
            pass
        elif token.startswith("["):
            errors.append({
                "line": line_no,
                "message": f"hold syntax '{token}' isn't valid in an attack string "
                           "(an attack string matches which moves landed, not input timing)",
            })
            return None
        bits = wongscript._resolve_step_code(token, errors, line_no, token)
        if bits is None:
            return None
        if bits == 0:
            errors.append({
                "line": line_no,
                "message": f"'{token}' is neutral -- an attack string needs real attacks",
            })
            return None
        attacks.append(_motion_to_matchable(token, bits))

    if not any(a is not GAP for a in attacks):
        errors.append({"line": line_no,
                       "message": "an attack string needs at least one real attack"})
        return None
    return attacks

_DIRECTION_MASK = 1 | 2 | 4 | 8

def _motion_to_matchable(token, bits):

    digits = [c for c in token if c in "123456789"]
    if len(digits) >= 2:
        return bits & ~_DIRECTION_MASK
    return bits

def _matches(required, landed):

    return (landed & required) == required

def check_attack_string(spec_attacks, landed_attacks):

    if not spec_attacks:
        return False, "no attacks specified"
    landed_attacks = landed_attacks or []
    if len(landed_attacks) < len(spec_attacks):
        return False, (
            f"needed {len(spec_attacks)} attack(s) to land, got {len(landed_attacks)}"
        )

    for i, required in enumerate(spec_attacks):
        entry = landed_attacks[i]
        bits = entry.get("bits") if isinstance(entry, dict) else entry
        if bits is None or not _matches(required, bits):
            return False, (
                f"attack {i + 1} was {wongscript._bits_to_code(bits or 0)}, "
                f"expected {wongscript._bits_to_code(required)}"
            )
        if i > 0 and isinstance(entry, dict) and not entry.get("comboed_from_previous"):
            return False, f"attack {i + 1} landed but didn't combo from the previous one"
    return True, None

def check_attack_inputs(spec_attacks, attack_inputs, hit_count, mode=MODE_PREFIX):

    if not spec_attacks:
        return False, "no attacks specified"
    inputs = attack_inputs or []
    if len(inputs) < len(spec_attacks):
        return False, (
            f"needed {len(spec_attacks)} attack input(s), saw {len(inputs)}"
        )
    def run_matches(start):
        for i, required in enumerate(spec_attacks):
            entry = inputs[start + i]
            bits = entry.get("bits") if isinstance(entry, dict) else entry
            if bits is None or not _matches(required, bits):
                return i, bits
        return None, None

    starts = ([0] if mode != MODE_CONTAINS
              else range(0, len(inputs) - len(spec_attacks) + 1))
    failed_at, saw = None, None
    for start in starts:
        failed_at, saw = run_matches(start)
        if failed_at is None:
            break
    if failed_at is not None:
        return False, (
            f"attack {failed_at + 1} was {wongscript._bits_to_code(saw or 0)}, "
            f"expected {wongscript._bits_to_code(spec_attacks[failed_at])}"
        )
    if (hit_count or 0) < len(spec_attacks):
        return False, (
            f"right inputs but only {hit_count or 0} of {len(spec_attacks)} hit"
        )
    return True, None

def check_move_ids(spec_id_sets, landed_move_ids, mode=MODE_PREFIX):

    if not spec_id_sets:
        return False, "no attacks specified"
    landed = [m for m in (landed_move_ids or []) if m]

    required = [a for a in spec_id_sets if a is not GAP]
    if len(landed) < len(required):
        return False, f"needed {len(required)} move(s) to land, got {len(landed)}"

    groups = segments(spec_id_sets)
    if not groups:
        return False, "no attacks specified"

    anchored = mode != MODE_CONTAINS
    at = 0
    for index, group in enumerate(groups):
        n = len(group)
        found = None

        starts = [at] if (anchored and index == 0) else range(at, len(landed) - n + 1)
        for start in starts:
            if start + n > len(landed):
                break
            if all(landed[start + i] in allowed for i, allowed in enumerate(group)):
                found = start
                break
        if found is None:
            expected = " > ".join(str(sorted(a)) for a in group)
            where = "at the start" if (anchored and index == 0) else "after the previous run"
            return False, (f"required run never landed together: expected {expected} "
                           f"{where}, in {landed}")
        at = found + n
    return True, None
