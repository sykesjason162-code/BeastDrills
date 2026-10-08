import json
import re
from pathlib import Path

from . import paths

_CATALOG_DIR = Path(__file__).parent / "command_display"

_CHARACTER_FILES = {
    "ryu": "Ryu", "luke": "Luke", "kimberly": "Kimberly", "chun_li": "ChunLi",
    "manon": "Manon", "zangief": "Zangief", "jp": "JP", "dhalsim": "Dhalsim",
    "cammy": "Cammy", "ken": "Ken", "dee_jay": "DeeJay", "lily": "Lily",
    "blanka": "Blanka", "juri": "Juri", "marisa": "Marisa", "guile": "Guile",
    "honda": "EHonda", "jamie": "Jamie", "mai": "Mai", "aki": "AKI",
    "akuma": "Akuma", "ed": "Ed", "rashid": "Rashid", "m_bison": "MBison",
    "terry": "Terry", "elena": "Elena", "sagat": "Sagat", "alex": "Alex",
    "c_viper": "CViper", "ingrid": "Ingrid", "yasmine": "Yasmine",
}

_cache: dict = {}

_DISPLAY_ALIASES = {
    "LPLK": "THROW",
    "4LPLK": "4THROW",
    "6LPLK": "6THROW",
    "HPHK": "DI",
}

_ALIAS_TO_INPUT = {display: written for written, display in _DISPLAY_ALIASES.items()}

_JUMP_ATTACK = re.compile(r"^[789](.+)$")

_MOVE_ALIASES = {
    "DR": "66MKMP", "DRIVERUSH": "66MKMP",
    "RAWDR": "66MKMP", "DRC": "66MKMP", "DRIVERUSHCANCEL": "66MKMP",
    "DI": "HPHK", "DRIVEIMPACT": "HPHK",
    "DRIVEPARRY": "MPMK", "PARRY": "MPMK",
}

def input_notation_for(token, character_id=None, data_dir=None):

    raw = str(token or "").strip()
    if not raw:
        return None

    flat = re.sub(r"[\s+]", "", raw).upper()
    cancelled = flat.lstrip(">.")
    if cancelled != flat and cancelled == "MPMK":
        return _MOVE_ALIASES["DRC"]
    return _ALIAS_TO_INPUT.get(cancelled) or _MOVE_ALIASES.get(cancelled)

def _normalize(text: str) -> str:

    s = re.sub(r"[\s+]", "", str(text or "")).upper()
    s = s.lstrip(">")

    s = _DISPLAY_ALIASES.get(s, s)

    if len(s) > 1 and s[0] == "5":
        s = s[1:]
    return s

def load_catalog(character_id: str):

    if not character_id:
        return None
    key = character_id.lower()
    if key in _cache:
        return _cache[key]

    stem = _CHARACTER_FILES.get(key)
    path = _CATALOG_DIR / f"{stem}.json" if stem else None
    if not path or not path.exists():
        _cache[key] = None
        return None

    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        _cache[key] = None
        return None

    table: dict = {}

    super_displays: dict = {}
    for action_id, entry in (raw or {}).items():
        if not isinstance(entry, dict):
            continue
        cmd = entry.get("classic_command") or {}

        names = [cmd.get("display")] + list(cmd.get("inputs") or [])
        try:
            aid = int(action_id)
        except (TypeError, ValueError):
            continue
        if SUPER_ART_1_ACTION_ID <= aid < SUPER_ART_1_ACTION_ID + 40:
            super_displays[aid] = cmd.get("display") or ""
        for name in names:
            norm = _normalize(name)
            if norm:
                table.setdefault(norm, set()).add(aid)

    _add_super_aliases(table, super_displays)
    _cache[key] = table or None
    return _cache[key]

SUPER_ART_1_ACTION_ID = 1200

def _add_super_aliases(table, by_id):

    base = (by_id or {}).get(SUPER_ART_1_ACTION_ID)
    if base is None:
        return
    ids, aid = set(), SUPER_ART_1_ACTION_ID
    while aid in by_id and _motion_of(by_id[aid]) == _motion_of(base):
        ids.add(aid)
        aid += 1
    if ids:

        for spelling in ("SA1", "Super Art 1"):
            key = _normalize(spelling)
            if key:
                table.setdefault(key, set()).update(ids)

def _motion_of(display) -> str:

    return _normalize(str(display or "").split("+")[0])

def resolve(character_id: str, notation: str, data_dir=None):

    table = load_catalog(character_id)
    if not table:
        return None

    branches = [b for b in str(notation or "").split("/") if b.strip()]
    if not branches:
        return table.get(_normalize(notation))

    ids: set = set()
    for branch in branches:
        found = next((f for f in (table.get(c) for c in _candidates(branch)) if f), None)
        if not found:
            found = _followup(character_id, table, branch, data_dir)
        if not found:
            found = _any_of_three(table, branch)
        if not found:
            return None
        ids |= found
    return ids

_ANY_STRENGTH = re.compile(r"^(.*?)(PPP|KKK)$")

_CHARGE = re.compile(r"^([1-9])([1-9].*)$")

_BARE_FOLLOWUP = re.compile(r"^(?:LP|MP|HP|LK|MK|HK|PP|KK|PPP|KKK|P|K)$")

def _rewrites(form):

    out = []
    charge = _CHARGE.match(form)
    if charge:
        out.append(f"[{charge.group(1)}]{charge.group(2)}")
    strength = _ANY_STRENGTH.match(form)
    if strength:
        out.append(strength.group(1) + strength.group(2)[0])
    jump = _JUMP_ATTACK.match(form)
    if jump:
        rest = jump.group(1)

        out.append("J." + (rest[1:] if len(rest) > 1 and rest[0] == "5" else rest))
    return out

_BARE_BUTTON = re.compile(r"^(.+?)([PK])$")

def _followup(character_id, table, branch, data_dir):

    if data_dir is None or not _BARE_FOLLOWUP.match(_normalize(branch)):
        return None
    names = _action_names(character_id, data_dir)
    if not names:
        return None

    prefixed = [p + c for c in _candidates(branch) for p in ("6", "J.")]
    for candidate in prefixed:
        ids = table.get(candidate)
        if not ids:
            continue

        if all(str(names.get(str(i)) or "").startswith("SPA") for i in ids):
            return ids
    return None

def _any_of_three(table, branch):
    for form in _candidates(branch):
        m = _BARE_BUTTON.match(form)
        if not m:
            continue
        motion, button = m.group(1), m.group(2)
        found: set = set()
        for strength in ("L", "M", "H"):
            found |= table.get(motion + strength + button) or set()
        if found:
            return found
    return None

def _candidates(branch):

    forms = [_normalize(branch)]
    i = 0
    while i < len(forms):
        for rewrite in _rewrites(forms[i]):
            if rewrite not in forms:
                forms.append(rewrite)
        i += 1
    return forms

def resolve_all(character_id: str, notations, data_dir=None):

    if not load_catalog(character_id):
        return None, f"no move catalog for character {character_id!r}"
    out = []
    for n in notations:

        if n is None or (isinstance(n, str) and n.strip() in ("...", "…")):
            out.append(None)
            continue
        ids = resolve(character_id, n, data_dir)
        if not ids:
            return None, f"{n!r} isn't a known move for {character_id!r}"
        out.append(ids)
    return out, None

def known_ids(character_id):

    table = load_catalog(character_id)
    if not table:
        return None
    out = set()
    for ids in table.values():
        out |= ids
    return out

_SPA = re.compile(r"^(SPA_SP\d+)(?:_[A-Z]+)*(?:\((\d+)\))?(?:\s+PROJ)?$")
_ATK = re.compile(r"^(ATK_[A-Z0-9_]+?)(?:\((\d+)\))?$")

_alias_cache: dict = {}
_names_cache: dict = {}
_movement_cache: dict = {}

_NON_LANDING = re.compile(r"^(?:BAS_DASH_|DPA_|BAS_JUMP_\w*_(?:AIR|START))")

def _action_names(character_id, data_dir):

    ck = (str(character_id).lower(), str(data_dir))
    if ck not in _names_cache:
        names = None
        if data_dir:
            path = paths.reference_dir(data_dir, "action_names") / f"{str(character_id).lower()}.json"
            try:
                with open(path, encoding="utf-8") as f:
                    names = json.load(f)
            except (OSError, ValueError):
                names = None
        _names_cache[ck] = names
    return _names_cache[ck]

def movement_ids(character_id, data_dir=None):

    ck = (str(character_id).lower(), str(data_dir))
    if ck not in _movement_cache:
        out = set()
        for raw_id, name in (_action_names(character_id, data_dir) or {}).items():
            if _NON_LANDING.match(name or ""):
                try:
                    out.add(int(raw_id))
                except (TypeError, ValueError):
                    continue
        _movement_cache[ck] = out
    return _movement_cache[ck]

def _move_key(name):
    m = _SPA.match(name or "")
    if m:
        return (m.group(1), int(m.group(2) or 0))
    m = _ATK.match(name or "")
    if m:
        return (m.group(1), None)
    return None

def _stage_aliases(character_id, data_dir):

    ck = (str(character_id).lower(), str(data_dir))
    if ck in _alias_cache:
        return _alias_cache[ck]

    aliases: dict = {}
    catalog = load_catalog(character_id)
    names = _action_names(character_id, data_dir) if catalog else None

    if names:
        known = {aid for ids in catalog.values() for aid in ids}
        by_key: dict = {}
        for aid in known:
            k = _move_key(names.get(str(aid)))
            if k:
                by_key.setdefault(k, set()).add(aid)
        for raw_id, name in names.items():
            try:
                aid = int(raw_id)
            except (TypeError, ValueError):
                continue
            if aid in known:
                continue
            same = by_key.get(_move_key(name)) or set()
            if len(same) == 1:
                aliases[aid] = next(iter(same))

    _alias_cache[ck] = aliases
    return aliases

def filter_to_moves(character_id, action_ids, data_dir=None):

    from .attack_string import is_movement

    known = known_ids(character_id)
    if not known:
        return list(action_ids or [])

    aliases = _stage_aliases(character_id, data_dir)
    moves_only = movement_ids(character_id, data_dir)
    out, prev_mapped = [], object()
    for aid in action_ids or []:

        mapped = aliases.get(aid, aid)

        if mapped == prev_mapped:
            continue
        prev_mapped = mapped
        if mapped not in known:
            continue
        aid = mapped

        if aid in moves_only:
            continue
        if is_movement(notation_for(character_id, aid)):
            continue
        out.append(aid)
    return out

def notation_for(character_id, action_id):

    table = load_catalog(character_id)
    if not table:
        return None
    matches = [notation for notation, ids in table.items() if action_id in ids]
    if not matches:
        return None
    return min(matches, key=lambda n: (len(n), n))
