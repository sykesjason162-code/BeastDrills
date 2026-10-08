import json
import re
from pathlib import Path

from . import paths

from . import attack_string, attempts, move_catalog, move_timing
from . import criteria as _criteria
from . import gauges as _gauges
from .response_check import SUPPORTED as _SUPPORTED

RESPONSE_CATEGORIES = list(_SUPPORTED)

POSITION_PRESETS = [
    "dummy_corner_right", "dummy_corner_left", "player_corner_left",
    "player_corner_right", "center", "center_reversed",
]
BLOCK_SETTINGS = ["no_guard", "block_after_first_hit", "all_block", "random_guard"]

DIFFICULTY_VALUES = ["very-easy", "easy", "medium", "hard", "very-hard"]

REPEAT_REPLAY_VALUES = ["off", "on", "always"]

COUNTER_VALUES = ["standard", "counter", "punish-counter", "random"]

TRAINS_CATEGORIES = [
    "whiff",
    "got_hit",
    "got_hit_high",
    "got_hit_mid",
    "got_hit_low",
    "throw_whiff",
    "throw_got_teched",
    "got_drive_impact_countered",
    "lost_di_clash",
    "dash_got_stuffed",
    "drive_rush_got_stuffed",
    "block_miss",
    "parry_miss",
    "got_thrown",
    "got_counter_hit",
    "got_punish_countered",
    "got_blocked",
    "got_parried",
    "got_anti_aired",
    "got_drive_impacted",
    "got_jump_attacked",
    "got_hit_confirmed",
    "non_hit_confirm",
    "parry_whiff",
    "got_reversaled",
    "got_backrolled",

    "no_backroll",
]

TRAINS_FOR_CATEGORIES = [
    "anti_air",
    "throw",
    "throw_missed_me",
    "throw_tech",
    "counter_hit",
    "punish_counter_hit",
    "block",
    "parry",
    "perfect_parry",
    "drive_impact",
    "drive_impact_counter",
    "drive_impact_vs_di",
    "stuff_dash",
    "stuff_drive_rush",
    "jump_attack",
    "hit_confirm",
    "reversal",
    "backroll",
    "blocked_their_string",
    "hit",
    "hit_high",
    "hit_mid",
    "hit_low",
]
CHARACTER_IDS = [

    "ryu", "luke", "kimberly", "chun_li", "manon", "zangief", "jp", "dhalsim",
    "cammy", "ken", "dee_jay", "lily", "blanka", "juri", "marisa", "guile",
    "honda", "jamie", "mai",

    "aki", "akuma", "ed", "elena", "m_bison", "rashid", "sagat", "terry",

    "alex", "c_viper", "ingrid", "yasmine",
]

REVERSAL_TYPE_TO_INT = {
    "NONE": -1, "NORMAL": 0, "COMMAND_NORMAL": 1, "SPECIAL": 2, "SA": 3,
    "RECORDING": 4, "COMMON": 5, "OTHER": 6, "MAX": 7,
}
REVERSAL_INT_TO_TYPE = {v: k for k, v in REVERSAL_TYPE_TO_INT.items()}

SLOT_KIND_MAX_INDEX = {
    "reversal": 9, "block_reversal": 9, "damage_reversal": 9,
    "recording": 7,
}

DIGIT_TO_BITS = {
    "1": 2 | 4, "2": 2, "3": 2 | 8,
    "4": 4, "5": 0, "6": 8,
    "7": 1 | 4, "8": 1, "9": 1 | 8,
}
BUTTON_NAME_TO_BIT = {"LP": 16, "MP": 32, "HP": 64, "LK": 128, "MK": 256, "HK": 512}

BUTTON_NAME_TO_BIT["PP"]  = BUTTON_NAME_TO_BIT["LP"] | BUTTON_NAME_TO_BIT["MP"]
BUTTON_NAME_TO_BIT["KK"]  = BUTTON_NAME_TO_BIT["LK"] | BUTTON_NAME_TO_BIT["MK"]
BUTTON_NAME_TO_BIT["PPP"] = BUTTON_NAME_TO_BIT["LP"] | BUTTON_NAME_TO_BIT["MP"] | BUTTON_NAME_TO_BIT["HP"]
BUTTON_NAME_TO_BIT["KKK"] = BUTTON_NAME_TO_BIT["LK"] | BUTTON_NAME_TO_BIT["MK"] | BUTTON_NAME_TO_BIT["HK"]

BIT_TO_BUTTON_NAME = {v: k for k, v in BUTTON_NAME_TO_BIT.items() if len(k) == 2}
BIT_TO_DIGIT = {v: k for k, v in DIGIT_TO_BITS.items() if k != "5"}

MOTION_STEP_FRAMES = 2

DASH_RELEASE_FRAMES = 5

INTER_ACTION_GAP_FRAMES = 6

_BUTTON_ATOM = r"[A-Za-z]{2}"
_STEP_ATOM = rf"(?:[1-9]|[Nn]|{_BUTTON_ATOM})"
_BARE_BUTTON_RUN = rf"(?:{_BUTTON_ATOM}){{2,}}"

_STEP_PART = rf"(?:{_BARE_BUTTON_RUN}|{_STEP_ATOM})"
_STEP_CODE = rf"{_STEP_PART}(?:\+{_STEP_PART})*"
_STEP_RE = re.compile(
    rf"\[(?P<hcode>{_STEP_CODE}):(?P<hframes>\d+)f\]|(?P<code>{_STEP_CODE})"
)
_STEP_PART_RE = re.compile(r"[1-9]|[Nn]|[A-Za-z]{2}")

def _resolve_step_code(code, errors, line_no, raw_token):

    mask = 0
    for part in _STEP_PART_RE.findall(code.replace("+", "")):
        if part in ("N", "n", "5"):
            continue
        elif part in DIGIT_TO_BITS:
            mask |= DIGIT_TO_BITS[part]
        else:
            bit = BUTTON_NAME_TO_BIT.get(part.upper())
            if bit is None:
                _err(errors, line_no, f"unknown step '{part}' in pattern token '{raw_token}'")
                return None
            mask |= bit
    return mask

_GAP_SEQUENCE = [0] * INTER_ACTION_GAP_FRAMES

SLOT_END_NEUTRAL_FRAMES = 60

_DIRECTION_DIGITS = set("12346789")

_OPPOSITE_DIGIT = {"1": "9", "9": "1", "2": "8", "8": "2", "3": "7", "7": "3", "4": "6", "6": "4"}

def _is_pure_button_step(code):

    parts = _STEP_PART_RE.findall(code.replace("+", ""))
    return bool(parts) and all(p not in ("N", "n") and p not in DIGIT_TO_BITS for p in parts)

def _parse_pattern_token(token, errors, line_no):

    matches = list(_STEP_RE.finditer(token))
    frames = []
    pos = 0

    prev_direction_digit = None
    i = 0
    while i < len(matches):
        m = matches[i]
        if m.start() != pos:
            _err(errors, line_no, f"malformed pattern token '{token}' (expected e.g. '236HP' or '[6:10f]')")
            return None
        pos = m.end()

        is_held = m.group("hcode") is not None
        if is_held:
            code, n = m.group("hcode"), int(m.group("hframes"))
            if n <= 0:
                _err(errors, line_no, f"pattern step '{m.group(0)}' must be a positive frame count")
                return None
        else:
            code, n = m.group("code"), MOTION_STEP_FRAMES

        bit = _resolve_step_code(code, errors, line_no, token)
        if bit is None:
            return None

        dir_digit = BIT_TO_DIGIT.get(bit & _DIRECTION_MASK)
        is_reversal = dir_digit is not None and prev_direction_digit is not None and (
            dir_digit == prev_direction_digit
            or dir_digit == _OPPOSITE_DIGIT.get(prev_direction_digit)
        )

        if not is_held and code in _DIRECTION_DIGITS and i + 1 < len(matches):
            nxt = matches[i + 1]
            if nxt.start() == pos and nxt.group("hcode") is None and _is_pure_button_step(nxt.group("code")):
                if is_reversal:
                    frames.extend([0] * DASH_RELEASE_FRAMES)
                btn_bit = _resolve_step_code(nxt.group("code"), errors, line_no, token)
                if btn_bit is None:
                    return None
                frames.extend([bit | btn_bit] * MOTION_STEP_FRAMES)
                pos = nxt.end()
                i += 2

                prev_direction_digit = dir_digit
                continue

        if is_reversal:
            frames.extend([0] * DASH_RELEASE_FRAMES)

        frames.extend([bit] * n)

        prev_direction_digit = dir_digit
        i += 1

    if not matches or pos != len(token):
        _err(errors, line_no, f"malformed pattern token '{token}' (expected e.g. '236HP' or '[6:10f]')")
        return None
    return frames

def _is_pure_neutral(frames):
    return all(f == 0 for f in frames)

_NAMED_HOLD_RE = re.compile(r"^\[(?P<code>.+):(?P<frames>\d+)f\]$")

def _resolve_named_token(token, character_id=None, data_dir=None):

    if not token:
        return token
    hold = _NAMED_HOLD_RE.match(token)
    inner = hold.group("code") if hold else token
    if _parses_as_steps(inner):
        return token
    resolved = move_catalog.input_notation_for(inner, character_id, data_dir)
    if not resolved or not _parses_as_steps(resolved):
        return token
    return f"[{resolved}:{hold.group('frames')}f]" if hold else resolved

def _parses_as_steps(code) -> bool:

    probe = []
    return _parse_pattern_token(code, probe, 0) is not None and not probe

def _parse_pattern_notation(value, errors, line_no, character_id=None, data_dir=None):

    tokens = [t.strip() for t in value.split(",") if t.strip()]
    if not tokens:
        _err(errors, line_no, "expected at least one pattern token")
        return None

    token_frame_lists = []
    for token in tokens:
        token = _resolve_named_token(token, character_id, data_dir)
        token_frames = _parse_pattern_token(token, errors, line_no)
        if token_frames is None:
            return None
        token_frames = _pad_to_move_length(token, token_frames, character_id, data_dir)
        token_frame_lists.append(token_frames)

    frames = []
    for i, token_frames in enumerate(token_frame_lists):
        if i > 0:
            prev_is_neutral = _is_pure_neutral(token_frame_lists[i - 1])
            this_is_neutral = _is_pure_neutral(token_frames)
            if not prev_is_neutral and not this_is_neutral:
                frames.extend(_GAP_SEQUENCE)
        frames.extend(token_frames)
    frames.extend([0] * SLOT_END_NEUTRAL_FRAMES)
    return frames

def retime_pattern(action_text, character_id, data_dir):

    if not action_text or not character_id or data_dir is None:
        return None
    errors = []
    frames = _parse_pattern_notation(action_text, errors, 1, character_id, data_dir)
    return None if errors else frames

def _pad_to_move_length(token, token_frames, character_id, data_dir):

    if not character_id or data_dir is None:
        return token_frames
    if _is_pure_neutral(token_frames):
        return token_frames
    try:
        duration = move_timing.tape_duration(character_id, token, data_dir)
    except Exception:

        return token_frames
    if not duration or duration <= len(token_frames):
        return token_frames
    return token_frames + [0] * (duration - len(token_frames))

_ALL_BUTTON_BITS = sorted(BUTTON_NAME_TO_BIT.values())
_DIRECTION_MASK = 1 | 2 | 4 | 8

def _bits_to_code(value):

    if value == 0:
        return "N"
    if value in BIT_TO_DIGIT:
        return BIT_TO_DIGIT[value]
    if value in BIT_TO_BUTTON_NAME:
        return BIT_TO_BUTTON_NAME[value]

    direction_bits = value & _DIRECTION_MASK
    remaining = value & ~_DIRECTION_MASK
    direction_part = None
    if direction_bits:
        if direction_bits not in BIT_TO_DIGIT:
            return str(value)
        direction_part = BIT_TO_DIGIT[direction_bits]

    button_parts = []
    for bit in _ALL_BUTTON_BITS:
        if remaining & bit:
            button_parts.append(BIT_TO_BUTTON_NAME[bit])
            remaining &= ~bit
    if remaining or not (direction_part or button_parts):
        return str(value)

    if direction_part:
        return "+".join([direction_part] + button_parts)
    return "".join(button_parts)

_ALL_BUTTON_MASK = 0
for _b in BUTTON_NAME_TO_BIT.values():
    _ALL_BUTTON_MASK |= _b

def _is_pure_direction_value(value):
    return value != 0 and value in BIT_TO_DIGIT

def _is_pure_button_value(value):
    return value != 0 and (value & _DIRECTION_MASK) == 0 and (value & ~_ALL_BUTTON_MASK) == 0

def _render_pattern_notation(pattern):

    if not pattern:
        return ""
    runs = []
    for value in pattern:
        if runs and runs[-1][0] == value:
            runs[-1] = (value, runs[-1][1] + 1)
        else:
            runs.append((value, 1))

    if len(runs) > 1 and runs[-1][0] == 0 and runs[-1][1] >= SLOT_END_NEUTRAL_FRAMES:
        remainder = runs[-1][1] - SLOT_END_NEUTRAL_FRAMES
        if remainder:
            runs[-1] = (0, remainder)
        else:
            runs.pop()

    def render_run(value, count, force_bracket=False):
        code = _bits_to_code(value)

        if not force_bracket and count == MOTION_STEP_FRAMES and re.fullmatch(_STEP_CODE, code):
            return code
        return f"[{code}:{count}f]"

    tokens = []
    current = []
    for i, (value, count) in enumerate(runs):
        if value == 0 and count == INTER_ACTION_GAP_FRAMES and 0 < i < len(runs) - 1:

            if current:
                tokens.append("".join(current))
                current = []
            continue
        if value == 0 and count == DASH_RELEASE_FRAMES and 0 < i < len(runs) - 1:

            continue
        if value == 0:

            if current:
                tokens.append("".join(current))
                current = []
            tokens.append(render_run(value, count))
            continue
        force_bracket = (
            _is_pure_direction_value(value) and i + 1 < len(runs) and
            _is_pure_button_value(runs[i + 1][0])
        )
        current.append(render_run(value, count, force_bracket))
    if current:
        tokens.append("".join(current))
    return ", ".join(tokens)

def _to_kebab(snake: str) -> str:
    return snake.lower().replace("_", "-")

def _from_kebab(kebab: str) -> str:
    return kebab.lower().replace("-", "_")

def _err(errors, line_no, message):
    errors.append({"line": line_no, "message": message})

def _load_json(path: Path):
    if not path or not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None

def _resolve_skill_index(data_dir, dummy_char, reversal_type, skill_token, errors, line_no):

    stripped = skill_token.lstrip("-")
    if stripped.isdigit():
        return int(skill_token)

    name_wanted = skill_token.replace("-", " ").strip().lower()
    candidates = skill_names_for(data_dir, dummy_char, reversal_type)

    for idx, real_name in enumerate(candidates):
        if real_name.lower() == name_wanted:
            return idx

    hint = " (set 'dummy:' to the opponent's character)" if (
        not candidates and not dummy_char) else ""
    _err(errors, line_no, f"unknown skill name '{skill_token}' for type={reversal_type}{hint}")
    return None

def skill_names_for(data_dir, dummy_char, reversal_type):

    if not data_dir:
        return []
    root = paths.reference_dir(data_dir, "reversal_skills")
    if dummy_char:
        per_char = _load_json(root / f"{dummy_char}.json")
        names = (per_char or {}).get(reversal_type)
        if names:
            return names
    common = _load_json(root / "_common.json")
    return (common or {}).get(reversal_type) or []

def _name_for_skill_index(data_dir, dummy_char, reversal_type, skill_index):

    if not data_dir or skill_index is None:
        return None

    candidates = skill_names_for(data_dir, dummy_char, reversal_type)
    if 0 <= skill_index < len(candidates):
        return _to_kebab(candidates[skill_index].replace(" ", "_").replace("-", "_"))
    return None

_ACTION_RE = re.compile(
    r"^type=(?P<type>[\w-]+)\s+skill=(?P<skill>[\w-]+)\s*(?:,\s*(?P<delay>\d+)f)?$"
)

def _parse_categories(value, errors, line_no):

    tokens = [t.strip() for t in value.split(",") if t.strip()]
    if not tokens:
        _err(errors, line_no, "expected at least one response category")
        return None
    result = []
    for t in tokens:

        if ">" in t:
            expr = " > ".join(_from_kebab(p.strip()) for p in t.split(">") if p.strip())
            try:
                _criteria.parse(expr)
            except ValueError as exc:
                _err(errors, line_no, str(exc))
                return None
            result.append(expr)
            continue
        snake = _from_kebab(t)
        if snake not in RESPONSE_CATEGORIES:
            _err(errors, line_no, f"unknown response category '{t}'")
            return None
        result.append(snake)
    return result[0] if len(result) == 1 else result

def _render_categories(value):
    if isinstance(value, list):
        return ", ".join(_to_kebab(v) for v in value)
    return _to_kebab(value)

def parse(text: str, data_dir: Path = None):

    errors = []
    name = None
    description = ""
    training_settings = {}
    slot_outcomes = {}
    fixed_expected_response = None
    expected_setup = None
    against_criteria = None
    survive_seconds = None
    fixed_expected_combo = None
    response_window_frames = None
    game_speed = None
    reps = None
    attempt_source = attempts.DEFAULT
    character_id = None
    dummy_char = None
    repeat_replay = None
    counter = None
    require_slot = None
    difficulty = None
    trains = None
    trains_for = None
    recording_slots = []

    slot_lists = {"reversal": [], "block_reversal": [], "damage_reversal": []}

    current_kind = None
    current_index = None
    REVERSAL_KINDS = ("reversal", "block_reversal", "damage_reversal")
    SLOT_KEY_FOR_KIND = {
        "reversal": "wake-up-rev-slot", "block_reversal": "block-rev-slot",
        "damage_reversal": "damage-rev-slot",
    }

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            _err(errors, line_no, f"malformed line (expected 'key: value'): {raw_line}")
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "title":
            name = value
        elif key == "difficulty":
            value_kebab = _to_kebab(value.strip().lower())
            if value_kebab not in DIFFICULTY_VALUES:
                _err(errors, line_no, f"unknown difficulty {value!r} -- "
                     f"expected one of {', '.join(DIFFICULTY_VALUES)}")
            else:
                difficulty = value_kebab
        elif key == "description":

            description = value.strip('"').replace("\\n", "\n")
        elif key == "position" and "," in value:

            try:
                p1_text, p2_text = value.split(",", 1)
                training_settings["position"] = {
                    "p1_x": float(p1_text.strip()),
                    "p2_x": float(p2_text.strip()),
                }
            except ValueError:
                _err(errors, line_no, f"malformed position coordinates '{value}'")
        elif key == "position":
            snake = _from_kebab(value)
            if snake not in POSITION_PRESETS:
                _err(errors, line_no, f"unknown position '{value}'")
            else:
                training_settings["position"] = snake
        elif _from_kebab(key) in _gauges.PAIR_KEYS:
            key = _from_kebab(key)

            value_obj, problems = _gauges.parse_pair(key, value)
            for message in problems:
                _err(errors, line_no, message)

            if value_obj:
                training_settings[key] = value_obj
        elif key in ("cpu-level", "cpu_level"):
            try:
                level = int(value.strip())
            except ValueError:
                _err(errors, line_no, f"cpu-level: '{value}' is not a number -- 1 to 8")
            else:
                problems = _gauges.cpu_level_errors(level)
                for message in problems:
                    _err(errors, line_no, message)
                if not problems:
                    training_settings["cpu_level"] = level
        elif key == "block":
            snake = _from_kebab(value)
            if snake not in BLOCK_SETTINGS:
                _err(errors, line_no, f"unknown block setting '{value}'")
            else:
                training_settings["block_setting"] = snake
        elif key == "character":
            snake = _from_kebab(value)
            if snake not in CHARACTER_IDS:
                _err(errors, line_no, f"unknown character '{value}'")
            else:
                character_id = snake
        elif key == "dummy":
            snake = _from_kebab(value)
            if snake not in CHARACTER_IDS:
                _err(errors, line_no, f"unknown dummy character '{value}'")
            else:
                dummy_char = snake
        elif key == "reps":
            if not value.isdigit() or int(value) <= 0:
                _err(errors, line_no, f"reps must be a positive integer, got '{value}'")
            else:
                reps = int(value)
        elif key == attempts.FIELD:

            problems = attempts.errors(value)
            if problems:
                _err(errors, line_no, problems[0])
            else:
                attempt_source = attempts.normalize(value)
        elif key == "game-speed":
            if not value.isdigit() or not (0 <= int(value) <= 10):
                _err(errors, line_no, f"game-speed must be 0-10, got '{value}'")
            else:
                game_speed = int(value)
        elif key == "response-window":
            if not value.isdigit() or int(value) <= 0:
                _err(errors, line_no, f"response-window must be a positive integer, got '{value}'")
            else:
                response_window_frames = int(value)
        elif key == "require-slot":

            val = value.strip().lower()
            if val in ("no", "false", "off"):
                require_slot = False
            elif val in ("yes", "true", "on"):
                require_slot = True
            else:
                _err(errors, line_no, f"require-slot must be yes or no, got '{value}'")
        elif key == "trains":

            picked, bad = [], []
            for raw in value.split(","):
                token = _from_kebab(raw.strip())
                if not token:
                    continue
                (picked if token in TRAINS_CATEGORIES else bad).append(token)
            if bad:
                _err(errors, line_no,
                     f"trains: unknown categor{'y' if len(bad) == 1 else 'ies'} "
                     f"{', '.join(bad)} -- expected receiver tallies like "
                     f"got_thrown, got_hit, got_blocked")
            elif not picked:
                _err(errors, line_no, "trains: needs at least one category")
            else:

                trains = list(dict.fromkeys(picked))
        elif key in ("trains-for", "trains_for"):

            picked, bad = [], []
            for raw in value.split(","):
                token = _from_kebab(raw.strip())
                if not token:
                    continue
                (picked if token in TRAINS_FOR_CATEGORIES else bad).append(token)
            if bad:
                _err(errors, line_no,
                     f"trains-for: unknown categor{'y' if len(bad) == 1 else 'ies'} "
                     f"{', '.join(bad)} -- expected giver tallies like "
                     f"anti_air, hit_confirm, perfect_parry")
            elif not picked:
                _err(errors, line_no, "trains-for: needs at least one category")
            else:
                trains_for = list(dict.fromkeys(picked))
        elif key == "counter":

            val = value.strip().lower()
            if val not in COUNTER_VALUES:
                _err(errors, line_no, f"counter must be one of {', '.join(COUNTER_VALUES)}, got '{value}'")
            else:
                counter = val
        elif key == "repeat-replay":
            snake = _from_kebab(value)
            if snake not in REPEAT_REPLAY_VALUES:
                _err(errors, line_no, f"repeat-replay must be one of {', '.join(REPEAT_REPLAY_VALUES)}, got '{value}'")
            else:
                repeat_replay = snake
        elif key in ("wake-up-rev-slot", "block-rev-slot", "damage-rev-slot"):
            kind = {"wake-up-rev-slot": "reversal", "block-rev-slot": "block_reversal",
                    "damage-rev-slot": "damage_reversal"}[key]
            if not value.isdigit():
                _err(errors, line_no, f"{key} needs a slot number, got '{value}'")
                current_kind = None
            elif int(value) > SLOT_KIND_MAX_INDEX[kind]:
                _err(errors, line_no, f"{key} {value} is out of range -- Reversal Settings only has slots 0-{SLOT_KIND_MAX_INDEX[kind]} in-game")
                current_kind = None
            else:
                current_kind = kind
                current_index = int(value)
        elif key == "rec-slot":
            if not value.isdigit():
                _err(errors, line_no, f"rec-slot needs a slot number, got '{value}'")
                current_kind = None
            elif int(value) > SLOT_KIND_MAX_INDEX["recording"]:
                _err(errors, line_no, f"rec-slot {value} is out of range -- Recording Settings only has slots 0-{SLOT_KIND_MAX_INDEX['recording']} in-game")
                current_kind = None
            else:
                current_kind = "recording"
                current_index = int(value)
                recording_slots.append({"index": current_index})
        elif key == "action":

            if current_kind == "recording":
                parsed_pattern = _parse_pattern_notation(value, errors, line_no)
                if parsed_pattern is not None:
                    recording_slots[-1]["pattern"] = parsed_pattern

                    recording_slots[-1]["action_text"] = value
                continue
            if current_kind not in REVERSAL_KINDS:
                _err(errors, line_no, "action: needs an open wake-up-rev-slot:/block-rev-slot:/damage-rev-slot:/rec-slot: above it")
                continue
            m = _ACTION_RE.match(value)
            if not m:
                _err(errors, line_no,
                     f"malformed action line: '{value}' (expected 'type=<TYPE> skill=<name-or-n>, <n>f')")
                continue
            rtype = m.group("type").upper().replace("-", "_")
            if rtype not in REVERSAL_TYPE_TO_INT:
                _err(errors, line_no, f"unknown reversal type '{m.group('type')}'")
                continue
            skill_idx = _resolve_skill_index(data_dir, dummy_char, rtype, m.group("skill"), errors, line_no)
            if skill_idx is None:
                continue
            delay = int(m.group("delay")) if m.group("delay") else 0
            slot_lists[current_kind].append({
                "index": current_index,
                "type": REVERSAL_TYPE_TO_INT[rtype],
                "skill_index": skill_idx,
                "delay": delay,
            })
        elif key == "weight":

            if current_kind != "recording":
                _err(errors, line_no, "weight: needs an open rec-slot: above it")
            elif not value.isdigit() or int(value) <= 0:
                _err(errors, line_no, f"weight must be a positive integer, got '{value}'")
            else:
                recording_slots[-1]["weight"] = int(value)
        elif key == "success":
            if current_kind is None:
                _err(errors, line_no, f"success: needs an open {'/'.join(SLOT_KEY_FOR_KIND.values())}/rec-slot: above it")
                continue
            categories = _parse_categories(value, errors, line_no)
            if categories is None:
                continue

            entry = slot_outcomes.setdefault(str(current_index), {})
            entry["expected_response"] = categories
        elif key == "combo":

            if current_kind is None:
                _err(errors, line_no, f"combo: needs an open {'/'.join(SLOT_KEY_FOR_KIND.values())}/rec-slot: above it")
                continue
            combo_errors = []

            _, _combo_body = attack_string.split_mode(value)
            if attack_string.parse_attack_string(_combo_body, combo_errors, line_no) is None:
                errors.extend(combo_errors)
                continue
            entry = slot_outcomes.setdefault(str(current_index), {})
            entry["expected_combo"] = value
        elif key == "fixed-combo":
            combo_errors = []
            _, _combo_body = attack_string.split_mode(value)
            if attack_string.parse_attack_string(_combo_body, combo_errors, line_no) is None:
                errors.extend(combo_errors)
                continue
            fixed_expected_combo = value
        elif key == "survive":

            try:
                seconds = int(value)
            except ValueError:
                _err(errors, line_no, f"survive: expected a number of seconds, got '{value}'")
            else:
                if seconds < 1 or seconds > 99:
                    _err(errors, line_no,
                         "survive: must be 1-99 seconds (a round is 99 at most)")
                else:
                    survive_seconds = seconds
        elif key == "against":

            names = [_from_kebab(t.strip()) for t in value.split(",") if t.strip()]
            bad = [n for n in names if n not in _criteria.AGAINST_ATOMS]
            if bad:
                _err(errors, line_no,
                     f"against: cannot name {bad[0]!r} -- only "
                     f"{', '.join(_to_kebab(a) for a in _criteria.AGAINST_ATOMS)}")
            else:
                against_criteria = names
        elif key == "setup":

            names = [_from_kebab(t.strip()) for t in value.split(",") if t.strip()]
            bad = [n for n in names if n not in _criteria.SETUP_ATOMS]
            if bad:
                _err(errors, line_no,
                     f"setup: cannot name {bad[0]!r} -- only "
                     f"{', '.join(_to_kebab(a) for a in _criteria.SETUP_ATOMS)}")
            else:
                expected_setup = names
        elif key == "fixed-success":
            categories = _parse_categories(value, errors, line_no)
            if categories is not None:
                fixed_expected_response = categories
        else:
            _err(errors, line_no, f"unknown key '{key}'")

    if name is None or not name.strip():
        _err(errors, 0, "missing required 'title:' line")

    if errors:
        return None, errors

    if recording_slots:
        training_settings["recording_slots"] = recording_slots
    if repeat_replay:
        training_settings["repeat_replay"] = repeat_replay
    if counter:
        training_settings["counter"] = counter
    if require_slot is not None:
        training_settings["require_slot"] = require_slot
    if slot_lists["reversal"]:
        training_settings["reversal_slots"] = slot_lists["reversal"]
    if slot_lists["block_reversal"]:
        training_settings["block_reversal_slots"] = slot_lists["block_reversal"]
    if slot_lists["damage_reversal"]:
        training_settings["damage_reversal_slots"] = slot_lists["damage_reversal"]

    drill = {
        "name": name,
        "description": description,
        "training_settings": training_settings,
        "slot_outcomes": slot_outcomes or None,
        "fixed_expected_response": fixed_expected_response,
        "expected_setup": expected_setup,
        "against_criteria": against_criteria,
        "survive_seconds": survive_seconds,
        "fixed_expected_combo": fixed_expected_combo,
        "response_window_frames": response_window_frames,
        "game_speed": game_speed,
        "reps": reps,
        attempts.FIELD: attempt_source,
        "wongscript_text": text,
    }
    if character_id:
        drill["character_id"] = character_id
    if dummy_char:
        drill["dummy_character_id"] = dummy_char
    if trains:
        drill["trains"] = trains
    if trains_for:
        drill["trains_for"] = trains_for
    if difficulty:
        drill["difficulty"] = difficulty
    return drill, []

def _split_into_drill_blocks(text: str):

    lines = text.splitlines()
    blocks = []
    start = None
    current = []
    for i, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        is_title = ":" in stripped and stripped.split(":", 1)[0].strip().lower() == "title"
        if is_title:
            if start is not None:
                blocks.append((start, "\n".join(current)))
            start = i
            current = [raw_line]
        elif start is not None:
            current.append(raw_line)
    if start is not None:
        blocks.append((start, "\n".join(current)))
    return blocks

def parse_bundle(text: str, data_dir: Path = None):

    blocks = _split_into_drill_blocks(text)
    if not blocks:
        return [], [{"line": 0, "message": "no 'title:' line found -- nothing to import"}]

    drills = []
    errors = []
    for start_line, block_text in blocks:
        drill, block_errors = parse(block_text, data_dir=data_dir)
        if block_errors:
            for e in block_errors:
                offset = (e["line"] - 1) if e["line"] > 0 else 0
                errors.append({"line": start_line + offset, "message": e["message"]})
        else:
            drills.append(drill)
    return drills, errors

def render_bundle(drills, dummy_chars: dict = None, data_dir: Path = None) -> str:

    dummy_chars = dummy_chars or {}
    parts = [
        render(d, dummy_char=dummy_chars.get(d.get("id"), d.get("dummy_character_id")), data_dir=data_dir)
        for d in drills
    ]
    return "\n".join(parts)

def render(drill: dict, dummy_char: str = None, data_dir: Path = None) -> str:

    if drill.get("wongscript_text"):
        return drill["wongscript_text"]
    dummy_char = dummy_char or drill.get("dummy_character_id")
    lines = [f"title: {drill.get('name') or ''}"]
    if drill.get("description"):

        escaped = str(drill["description"]).replace("\n", "\\n")
        lines.append(f'description: "{escaped}"')

    ts = drill.get("training_settings") or {}
    position = ts.get("position")
    if isinstance(position, str) and position in POSITION_PRESETS:
        lines.append(f"position: {_to_kebab(position)}")
    elif isinstance(position, dict) and "p1_x" in position and "p2_x" in position:

        lines.append(f"position: {position['p1_x']}, {position['p2_x']}")
    block_setting = ts.get("block_setting")
    if block_setting:
        lines.append(f"block: {_to_kebab(block_setting)}")
    if dummy_char:
        lines.append(f"dummy: {_to_kebab(dummy_char)}")
    if drill.get("character_id"):
        lines.append(f"character: {_to_kebab(drill['character_id'])}")
    if drill.get("reps") is not None:
        lines.append(f"reps: {drill['reps']}")
    if attempts.normalize(drill.get(attempts.FIELD)) != attempts.DEFAULT:
        lines.append(f"{attempts.FIELD}: {attempts.normalize(drill.get(attempts.FIELD))}")
    if drill.get("game_speed") is not None:
        lines.append(f"game-speed: {drill['game_speed']}")
    if drill.get("response_window_frames") is not None:
        lines.append(f"response-window: {drill['response_window_frames']}")
    if ts.get("repeat_replay"):
        lines.append(f"repeat-replay: {_to_kebab(ts['repeat_replay'])}")
    if drill.get("trains"):
        lines.append("trains: " + ", ".join(drill["trains"]))
    if drill.get("trains_for"):
        lines.append("trains-for: " + ", ".join(drill["trains_for"]))
    if ts.get("counter"):
        lines.append(f"counter: {ts['counter']}")
    for gauge in _gauges.PAIR_KEYS:
        if ts.get(gauge):
            lines.append(f"{_to_kebab(gauge)}: "
                         f"{_gauges.render_pair(gauge, ts[gauge])}")
    if ts.get("cpu_level") is not None:
        lines.append(f"cpu-level: {ts['cpu_level']}")
    if drill.get("difficulty"):
        lines.append(f"difficulty: {drill['difficulty']}")
    if ts.get("require_slot") is not None:
        lines.append("require-slot: " + ("yes" if ts["require_slot"] else "no"))

    slot_outcomes = drill.get("slot_outcomes") or {}

    for slot_key, wong_key in (
        ("reversal_slots", "wake-up-rev-slot"),
        ("block_reversal_slots", "block-rev-slot"),
        ("damage_reversal_slots", "damage-rev-slot"),
    ):
        for cfg in ts.get(slot_key) or []:
            lines.append("")
            lines.append(f"{wong_key}: {cfg['index']}")
            rtype = REVERSAL_INT_TO_TYPE.get(cfg.get("type"), str(cfg.get("type")))
            skill_name = _name_for_skill_index(data_dir, dummy_char, rtype, cfg.get("skill_index"))
            skill_token = skill_name or str(cfg.get("skill_index"))
            lines.append(f"action: type={_to_kebab(rtype)} skill={skill_token}, {cfg.get('delay', 0)}f")
            outcome = slot_outcomes.get(str(cfg["index"]))
            if outcome and outcome.get("expected_combo"):
                lines.append(f"combo: {outcome['expected_combo']}")
            if outcome and outcome.get("expected_response"):
                lines.append(f"success: {_render_categories(outcome['expected_response'])}")

    for entry in ts.get("recording_slots") or []:

        idx = entry["index"] if isinstance(entry, dict) else entry
        weight = entry.get("weight") if isinstance(entry, dict) else None
        pattern = entry.get("pattern") if isinstance(entry, dict) else None

        authored = entry.get("action_text") if isinstance(entry, dict) else None
        lines.append("")
        lines.append(f"rec-slot: {idx}")
        if authored:
            lines.append(f"action: {authored}")
        elif pattern:
            lines.append(f"action: {_render_pattern_notation(pattern)}")

        if weight is not None:
            lines.append(f"weight: {weight}")
        outcome = slot_outcomes.get(str(idx))
        if outcome and outcome.get("expected_combo"):
            lines.append(f"combo: {outcome['expected_combo']}")
        if outcome and outcome.get("expected_response"):
            lines.append(f"success: {_render_categories(outcome['expected_response'])}")

    if drill.get("fixed_expected_combo"):
        lines.append("")
        lines.append(f"fixed-combo: {drill['fixed_expected_combo']}")
    if drill.get("fixed_expected_response"):
        lines.append("")
        lines.append(f"fixed-success: {_render_categories(drill['fixed_expected_response'])}")
    if drill.get("survive_seconds"):
        lines.append(f"survive: {drill['survive_seconds']}")
    if drill.get("against_criteria"):
        lines.append("against: " + ", ".join(
            _to_kebab(a) for a in drill["against_criteria"]))
    if drill.get("expected_setup"):
        lines.append("setup: " + ", ".join(
            _to_kebab(a) for a in drill["expected_setup"]))

    return "\n".join(lines) + "\n"
