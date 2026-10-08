from __future__ import annotations

import re

UNSET = "__unset__"

SLOT_KEYS = {
    "recording": ("recording_slots",),
    "reversal": ("reversal_slots", "block_reversal_slots", "damage_reversal_slots"),
}

def drill_types(drill: dict) -> set:

    settings = drill.get("training_settings") or {}
    found = set()
    for kind, keys in SLOT_KEYS.items():
        if any((settings.get(k) or []) for k in keys):
            found.add(kind)
    outcomes = (drill.get("slot_outcomes") or {}).values()
    if drill.get("fixed_expected_combo") or any(o and o.get("expected_combo") for o in outcomes):
        found.add("combo")
    return found or {"none"}

DIFFICULTY_ORDER = ["very-easy", "easy", "medium", "hard", "very-hard"]

FREE_TEXT_FIELDS = ("name", "description", "fixed_expected_combo", "id")

FIELDS = {
    "character": ("character_id",),
    "char": ("character_id",),
    "dummy": ("dummy_character_id",),
    "difficulty": ("difficulty",),
    "diff": ("difficulty",),
    "combo": ("fixed_expected_combo",),
    "name": ("name",),
    "id": ("id",),
    "desc": ("description",),
    "description": ("description",),
    "source": ("source",),
    "position": ("training_settings.position",),
    "trains": ("trains",),
    "trains-for": ("trains_for",),
    "trains_for": ("trains_for",),
    "response": ("fixed_expected_response",),

    "type": (),
    "selected": (),
    "favorite": (),
    "fav": (),
    "due": (),
}

_TOKEN = re.compile(r'(-?)(?:(\w[\w-]*):)?(?:"([^"]*)"|(\S+))')
_COMPARISON = re.compile(r"^(<=|>=|<|>)(.+)$")

class Term:
    __slots__ = ("negated", "field", "value")

    def __init__(self, negated, field, value):
        self.negated = negated
        self.field = field
        self.value = value

def parse_query(query: str) -> list:

    terms = []
    for negated, field, quoted, bare in _TOKEN.findall(query or ""):
        value = quoted if quoted else bare
        if not value and not quoted:
            continue
        key = (field or "").lower()
        if key and key not in FIELDS:

            value = f"{field}:{value}"
            key = ""
        terms.append(Term(bool(negated), key or None, value))
    return terms

def _get(drill: dict, path: str):
    value = drill
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value

def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_as_text(v) for v in value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)

def _matches_term(drill: dict, term: Term, now: str | None) -> bool:
    needle = term.value.lower()

    if term.field is None:
        haystack = " ".join(_as_text(drill.get(f)) for f in FREE_TEXT_FIELDS)
        return needle in haystack.lower()

    if term.field == "selected":
        return bool(drill.get("selected")) == (needle in ("yes", "true", "1"))

    if term.field in ("favorite", "fav"):
        return bool(drill.get("favorite")) == (needle in ("yes", "true", "1"))

    if term.field == "type":
        return needle in drill_types(drill)

    if term.field == "due":
        due = bool(now and drill.get("next_review") and drill["next_review"] <= now)
        return due == (needle in ("yes", "true", "1"))

    comparison = _COMPARISON.match(needle)
    if comparison and term.field in ("difficulty", "diff"):
        op, wanted = comparison.groups()
        actual = (drill.get("difficulty") or "").lower()
        if actual not in DIFFICULTY_ORDER or wanted not in DIFFICULTY_ORDER:
            return False
        a, b = DIFFICULTY_ORDER.index(actual), DIFFICULTY_ORDER.index(wanted)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]

    values = [_get(drill, p) for p in FIELDS[term.field]]
    if needle == UNSET:
        return not any(v for v in values)
    haystack = " ".join(_as_text(v) for v in values)
    return needle in haystack.lower()

def matches(drill: dict, terms: list, now: str | None = None) -> bool:

    for term in terms:
        hit = _matches_term(drill, term, now)
        if term.negated and hit:
            return False
        if not term.negated and not hit:
            return False
    return True

def search(drills, query: str, now: str | None = None) -> list:
    terms = parse_query(query)
    if not terms:
        return list(drills)
    return [d for d in drills if matches(d, terms, now)]
