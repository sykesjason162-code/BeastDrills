import json
import re
from pathlib import Path

from . import paths

from . import attack_string, attempts, belts, move_catalog, move_timing
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

    "alex", "c_viper", "ingrid", "yasmine", "arjun",
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

        if stripped != skill_token:
            _err(errors, line_no, f"skill={skill_token} is negative -- "
                 f"use a move name or a number from 0 for type={reversal_type}")
            return None
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

_REVERSAL_KINDS = ("reversal", "block_reversal", "damage_reversal")

_SLOT_KEY_FOR_KIND = {
    "reversal": "wake-up-rev-slot", "block_reversal": "block-rev-slot",
    "damage_reversal": "damage-rev-slot",
}
_KIND_FOR_SLOT_KEY = {key: kind for kind, key in _SLOT_KEY_FOR_KIND.items()}

class _ParseState:

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.errors = []
        self.name = None
        self.description = ""
        self.training_settings = {}
        self.slot_outcomes = {}
        self.fixed_expected_response = None
        self.expected_setup = None
        self.against_criteria = None
        self.survive_seconds = None
        self.fixed_expected_combo = None
        self.response_window_frames = None
        self.game_speed = None
        self.reps = None
        self.attempt_source = attempts.DEFAULT
        self.character_id = None
        self.dummy_char = None
        self.repeat_replay = None
        self.counter = None
        self.require_slot = None
        self.difficulty = None
        self.belt_drill = None
        self.trains = None
        self.trains_for = None
        self.recording_slots = []
        self.slot_lists = {kind: [] for kind in _REVERSAL_KINDS}
        self.current_kind = None
        self.current_index = None

        self.reversal_outcomes = []
        self.reversal_actioned = set()

    def err(self, line_no, message):
        _err(self.errors, line_no, message)

def _p_title(st, key, value, line_no):
    st.name = value

def _p_belt_drill(st, key, value, line_no):

    value_obj, problem = belts.parse_belt_drill(value)
    if problem:
        st.err(line_no, problem)
    else:
        st.belt_drill = value_obj

def _p_difficulty(st, key, value, line_no):
    value_kebab = _to_kebab(value.strip().lower())
    if value_kebab not in DIFFICULTY_VALUES:
        st.err(line_no, f"unknown difficulty {value!r} -- "
               f"expected one of {', '.join(DIFFICULTY_VALUES)}")
    else:
        st.difficulty = value_kebab

_DESCRIPTION_ESCAPE = re.compile(r"\\([n\\])")

def _p_description(st, key, value, line_no):

    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    st.description = _DESCRIPTION_ESCAPE.sub(
        lambda m: "\n" if m.group(1) == "n" else "\\", value)

def _p_position(st, key, value, line_no):
    if "," in value:

        try:
            p1_text, p2_text = value.split(",", 1)
            st.training_settings["position"] = {
                "p1_x": float(p1_text.strip()),
                "p2_x": float(p2_text.strip()),
            }
        except ValueError:
            st.err(line_no, f"malformed position coordinates '{value}'")
        return
    snake = _from_kebab(value)
    if snake not in POSITION_PRESETS:
        st.err(line_no, f"unknown position '{value}'")
    else:
        st.training_settings["position"] = snake

def _p_gauge(st, key, value, line_no):
    key = _from_kebab(key)

    value_obj, problems = _gauges.parse_pair(key, value)
    for message in problems:
        st.err(line_no, message)

    if value_obj:
        st.training_settings[key] = value_obj

def _p_cpu_level(st, key, value, line_no):
    try:
        level = int(value.strip())
    except ValueError:
        st.err(line_no, f"cpu-level: '{value}' is not a number -- 1 to 8")
        return
    problems = _gauges.cpu_level_errors(level)
    for message in problems:
        st.err(line_no, message)
    if not problems:
        st.training_settings["cpu_level"] = level

def _p_block(st, key, value, line_no):
    snake = _from_kebab(value)
    if snake not in BLOCK_SETTINGS:
        st.err(line_no, f"unknown block setting '{value}'")
    else:
        st.training_settings["block_setting"] = snake

def _p_character(st, key, value, line_no):
    snake = _from_kebab(value)
    if snake not in CHARACTER_IDS:
        st.err(line_no, f"unknown character '{value}'")
    else:
        st.character_id = snake

def _p_dummy(st, key, value, line_no):
    snake = _from_kebab(value)
    if snake not in CHARACTER_IDS:
        st.err(line_no, f"unknown dummy character '{value}'")
    else:
        st.dummy_char = snake

def _p_reps(st, key, value, line_no):
    if not value.isdigit() or int(value) <= 0:
        st.err(line_no, f"reps must be a positive integer, got '{value}'")
    else:
        st.reps = int(value)

def _p_attempts(st, key, value, line_no):

    problems = attempts.errors(value)
    if problems:
        st.err(line_no, problems[0])
    else:
        st.attempt_source = attempts.normalize(value)

def _p_game_speed(st, key, value, line_no):
    if not value.isdigit() or not (0 <= int(value) <= 10):
        st.err(line_no, f"game-speed must be 0-10, got '{value}'")
    else:
        st.game_speed = int(value)

def _p_response_window(st, key, value, line_no):
    if not value.isdigit() or int(value) <= 0:
        st.err(line_no, f"response-window must be a positive integer, got '{value}'")
    else:
        st.response_window_frames = int(value)

def _p_require_slot(st, key, value, line_no):

    val = value.strip().lower()
    if val in ("no", "false", "off"):
        st.require_slot = False
    elif val in ("yes", "true", "on"):
        st.require_slot = True
    else:
        st.err(line_no, f"require-slot must be yes or no, got '{value}'")

def _parse_tally_list(st, value, line_no, allowed, label, examples):

    picked, bad = [], []
    for raw in value.split(","):
        token = _from_kebab(raw.strip())
        if not token:
            continue
        (picked if token in allowed else bad).append(token)
    if bad:
        st.err(line_no,
               f"{label}: unknown categor{'y' if len(bad) == 1 else 'ies'} "
               f"{', '.join(bad)} -- expected {examples}")
        return None
    if not picked:
        st.err(line_no, f"{label}: needs at least one category")
        return None

    return list(dict.fromkeys(picked))

def _p_trains(st, key, value, line_no):

    picked = _parse_tally_list(st, value, line_no, TRAINS_CATEGORIES, "trains",
                               "receiver tallies like got_thrown, got_hit, got_blocked")
    if picked is not None:
        st.trains = picked

def _p_trains_for(st, key, value, line_no):

    picked = _parse_tally_list(st, value, line_no, TRAINS_FOR_CATEGORIES, "trains-for",
                               "giver tallies like anti_air, hit_confirm, perfect_parry")
    if picked is not None:
        st.trains_for = picked

def _p_counter(st, key, value, line_no):

    val = value.strip().lower()
    if val not in COUNTER_VALUES:
        st.err(line_no, f"counter must be one of {', '.join(COUNTER_VALUES)}, got '{value}'")
    else:
        st.counter = val

def _p_repeat_replay(st, key, value, line_no):
    snake = _from_kebab(value)
    if snake not in REPEAT_REPLAY_VALUES:
        st.err(line_no, f"repeat-replay must be one of {', '.join(REPEAT_REPLAY_VALUES)}, got '{value}'")
    else:
        st.repeat_replay = snake

def _p_rev_slot(st, key, value, line_no):
    kind = _KIND_FOR_SLOT_KEY[key]
    if not value.isdigit():
        st.err(line_no, f"{key} needs a slot number, got '{value}'")
        st.current_kind = None
    elif int(value) > SLOT_KIND_MAX_INDEX[kind]:
        st.err(line_no, f"{key} {value} is out of range -- Reversal Settings only has slots 0-{SLOT_KIND_MAX_INDEX[kind]} in-game")
        st.current_kind = None
    else:
        st.current_kind = kind
        st.current_index = int(value)

def _p_rec_slot(st, key, value, line_no):
    if not value.isdigit():
        st.err(line_no, f"rec-slot needs a slot number, got '{value}'")
        st.current_kind = None
    elif int(value) > SLOT_KIND_MAX_INDEX["recording"]:
        st.err(line_no, f"rec-slot {value} is out of range -- Recording Settings only has slots 0-{SLOT_KIND_MAX_INDEX['recording']} in-game")
        st.current_kind = None
    else:
        st.current_kind = "recording"
        st.current_index = int(value)
        st.recording_slots.append({"index": st.current_index})

def _p_action(st, key, value, line_no):

    if st.current_kind == "recording":
        _p_recording_action(st, value, line_no)
    elif st.current_kind not in _REVERSAL_KINDS:
        st.err(line_no, "action: needs an open wake-up-rev-slot:/block-rev-slot:/damage-rev-slot:/rec-slot: above it")
    else:
        _p_reversal_action(st, value, line_no)

def _p_recording_action(st, value, line_no):
    parsed_pattern = _parse_pattern_notation(value, st.errors, line_no)
    if parsed_pattern is None:
        return
    st.recording_slots[-1]["pattern"] = parsed_pattern

    st.recording_slots[-1]["action_text"] = value

def _p_reversal_action(st, value, line_no):
    m = _ACTION_RE.match(value)
    if not m:
        st.err(line_no,
               f"malformed action line: '{value}' (expected 'type=<TYPE> skill=<name-or-n>, <n>f')")
        return
    rtype = m.group("type").upper().replace("-", "_")
    if rtype not in REVERSAL_TYPE_TO_INT:
        st.err(line_no, f"unknown reversal type '{m.group('type')}'")
        return
    skill_idx = _resolve_skill_index(st.data_dir, st.dummy_char, rtype, m.group("skill"),
                                     st.errors, line_no)
    if skill_idx is None:
        return
    delay = int(m.group("delay")) if m.group("delay") else 0
    st.reversal_actioned.add((st.current_kind, st.current_index))
    st.slot_lists[st.current_kind].append({
        "index": st.current_index,
        "type": REVERSAL_TYPE_TO_INT[rtype],
        "skill_index": skill_idx,
        "delay": delay,
    })

def _p_weight(st, key, value, line_no):

    if st.current_kind != "recording":
        st.err(line_no, "weight: needs an open rec-slot: above it")
    elif not value.isdigit() or int(value) <= 0:
        st.err(line_no, f"weight must be a positive integer, got '{value}'")
    else:
        st.recording_slots[-1]["weight"] = int(value)

def _needs_open_slot(st, key, line_no):

    if st.current_kind is None:
        st.err(line_no, f"{key}: needs an open {'/'.join(_SLOT_KEY_FOR_KIND.values())}/rec-slot: above it")
        return False
    if st.current_kind in _REVERSAL_KINDS:
        st.reversal_outcomes.append((st.current_kind, st.current_index, key, line_no))
    return True

def _check_reversal_outcomes(st):

    for kind, index, key, line_no in st.reversal_outcomes:
        if (kind, index) in st.reversal_actioned:
            continue
        message = (f"{key}: {_SLOT_KEY_FOR_KIND[kind]} {index} has no valid action: line, "
                   f"so there is no slot for this outcome")
        at = next((i for i, e in enumerate(st.errors) if e["line"] > line_no), len(st.errors))
        st.errors.insert(at, {"line": line_no, "message": message})

def _p_success(st, key, value, line_no):
    if not _needs_open_slot(st, "success", line_no):
        return
    categories = _parse_categories(value, st.errors, line_no)
    if categories is None:
        return

    entry = st.slot_outcomes.setdefault(str(st.current_index), {})
    entry["expected_response"] = categories

def _valid_combo(st, value, line_no):

    combo_errors = []

    _, combo_body = attack_string.split_mode(value)
    if attack_string.parse_attack_string(combo_body, combo_errors, line_no) is None:
        st.errors.extend(combo_errors)
        return False
    return True

def _p_combo(st, key, value, line_no):

    if not _needs_open_slot(st, "combo", line_no) or not _valid_combo(st, value, line_no):
        return
    entry = st.slot_outcomes.setdefault(str(st.current_index), {})
    entry["expected_combo"] = value

def _p_fixed_combo(st, key, value, line_no):
    if _valid_combo(st, value, line_no):
        st.fixed_expected_combo = value

def _p_survive(st, key, value, line_no):

    try:
        seconds = int(value)
    except ValueError:
        st.err(line_no, f"survive: expected a number of seconds, got '{value}'")
        return
    if seconds < 1 or seconds > 99:
        st.err(line_no, "survive: must be 1-99 seconds (a round is 99 at most)")
    else:
        st.survive_seconds = seconds

def _parse_atoms(st, value, line_no, allowed, label):

    names = [_from_kebab(t.strip()) for t in value.split(",") if t.strip()]
    bad = [n for n in names if n not in allowed]
    if bad:
        st.err(line_no,
               f"{label}: cannot name {bad[0]!r} -- only "
               f"{', '.join(_to_kebab(a) for a in allowed)}")
        return None
    return names

def _p_against(st, key, value, line_no):

    names = _parse_atoms(st, value, line_no, _criteria.AGAINST_ATOMS, "against")
    if names is not None:
        st.against_criteria = names

def _p_setup(st, key, value, line_no):

    names = _parse_atoms(st, value, line_no, _criteria.SETUP_ATOMS, "setup")
    if names is not None:
        st.expected_setup = names

def _p_fixed_success(st, key, value, line_no):
    categories = _parse_categories(value, st.errors, line_no)
    if categories is not None:
        st.fixed_expected_response = categories

_PARSE_HANDLERS = {
    "title": _p_title,
    "belt-drill": _p_belt_drill,
    "difficulty": _p_difficulty,
    "description": _p_description,
    "position": _p_position,
    "cpu-level": _p_cpu_level,
    "cpu_level": _p_cpu_level,
    "block": _p_block,
    "character": _p_character,
    "dummy": _p_dummy,
    "reps": _p_reps,
    attempts.FIELD: _p_attempts,
    "game-speed": _p_game_speed,
    "response-window": _p_response_window,
    "require-slot": _p_require_slot,
    "trains": _p_trains,
    "trains-for": _p_trains_for,
    "trains_for": _p_trains_for,
    "counter": _p_counter,
    "repeat-replay": _p_repeat_replay,
    "wake-up-rev-slot": _p_rev_slot,
    "block-rev-slot": _p_rev_slot,
    "damage-rev-slot": _p_rev_slot,
    "rec-slot": _p_rec_slot,
    "action": _p_action,
    "weight": _p_weight,
    "success": _p_success,
    "combo": _p_combo,
    "fixed-combo": _p_fixed_combo,
    "survive": _p_survive,
    "against": _p_against,
    "setup": _p_setup,
    "fixed-success": _p_fixed_success,
}

def _handler_for(key):
    handler = _PARSE_HANDLERS.get(key)
    if handler is None and _from_kebab(key) in _gauges.PAIR_KEYS:
        handler = _p_gauge
    return handler

def _finish_training_settings(st):
    ts = st.training_settings
    if st.recording_slots:
        ts["recording_slots"] = st.recording_slots
    if st.repeat_replay:
        ts["repeat_replay"] = st.repeat_replay
    if st.counter:
        ts["counter"] = st.counter
    if st.require_slot is not None:
        ts["require_slot"] = st.require_slot
    for kind, field in (("reversal", "reversal_slots"),
                        ("block_reversal", "block_reversal_slots"),
                        ("damage_reversal", "damage_reversal_slots")):
        if st.slot_lists[kind]:
            ts[field] = st.slot_lists[kind]
    return ts

def _finish_drill(st, text):
    drill = {
        "name": st.name,
        "description": st.description,
        "training_settings": _finish_training_settings(st),
        "slot_outcomes": st.slot_outcomes or None,
        "fixed_expected_response": st.fixed_expected_response,
        "expected_setup": st.expected_setup,
        "against_criteria": st.against_criteria,
        "survive_seconds": st.survive_seconds,
        "fixed_expected_combo": st.fixed_expected_combo,
        "response_window_frames": st.response_window_frames,
        "game_speed": st.game_speed,
        "reps": st.reps,
        attempts.FIELD: st.attempt_source,
        "wongscript_text": text,
    }

    drill.update({field: value for field, value in (
        ("character_id", st.character_id),
        ("dummy_character_id", st.dummy_char),
        ("trains", st.trains),
        ("trains_for", st.trains_for),
        ("difficulty", st.difficulty),
        (belts.FIELD, st.belt_drill),
    ) if value})
    return drill

def parse(text: str, data_dir: Path = None):

    st = _ParseState(data_dir)
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            st.err(line_no, f"malformed line (expected 'key: value'): {raw_line}")
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        handler = _handler_for(key)
        if handler is None:
            st.err(line_no, f"unknown key '{key}'")
        else:
            handler(st, key, value.strip(), line_no)
    _check_reversal_outcomes(st)

    if st.name is None or not st.name.strip():
        st.err(0, "missing required 'title:' line")
    if st.errors:
        return None, st.errors
    return _finish_drill(st, text), []

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

_SYNCED_KEYS = ("difficulty", "belt-drill")

def _sync_cached_text(drill: dict) -> str:

    text = drill["wongscript_text"]
    want = {"difficulty": drill.get("difficulty") or None,
            "belt-drill": belts.render_belt_drill(drill.get(belts.FIELD))}
    lines = text.split("\n")
    keyed = [l.split(":", 1)[0].strip().lower() for l in lines]
    for key in _SYNCED_KEYS:
        value = want[key]
        if key in keyed:
            i = keyed.index(key)
            if value:
                lines[i] = f"{key}: {value}"
            else:
                del lines[i]
                del keyed[i]
        elif value:

            after = max((n for n, k in enumerate(keyed)
                         if k in ("title", "description", "character", "difficulty")), default=0)
            lines.insert(after + 1, f"{key}: {value}")
            keyed.insert(after + 1, key)
    return "\n".join(lines)

def _render_position(position):

    if isinstance(position, str) and position in POSITION_PRESETS:
        return f"position: {_to_kebab(position)}"
    if isinstance(position, dict) and "p1_x" in position and "p2_x" in position:

        return f"position: {position['p1_x']}, {position['p2_x']}"
    return None

def _render_header(drill, ts, dummy_char):

    lines = [f"title: {drill.get('name') or ''}"]
    if drill.get("description"):

        escaped = str(drill["description"]).replace("\\", "\\\\").replace("\n", "\\n")
        lines.append(f'description: "{escaped}"')
    position = _render_position(ts.get("position"))
    if position:
        lines.append(position)
    if ts.get("block_setting"):
        lines.append(f"block: {_to_kebab(ts['block_setting'])}")
    if dummy_char:
        lines.append(f"dummy: {_to_kebab(dummy_char)}")
    if drill.get("character_id"):
        lines.append(f"character: {_to_kebab(drill['character_id'])}")
    return lines

def _render_pacing(drill, ts):

    lines = []
    if drill.get("reps") is not None:
        lines.append(f"reps: {drill['reps']}")
    attempt_source = attempts.normalize(drill.get(attempts.FIELD))
    if attempt_source != attempts.DEFAULT:
        lines.append(f"{attempts.FIELD}: {attempt_source}")
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
    return lines

def _render_settings(drill, ts):

    lines = [f"{_to_kebab(gauge)}: {_gauges.render_pair(gauge, ts[gauge])}"
             for gauge in _gauges.PAIR_KEYS if ts.get(gauge)]
    if ts.get("cpu_level") is not None:
        lines.append(f"cpu-level: {ts['cpu_level']}")
    if drill.get("difficulty"):
        lines.append(f"difficulty: {drill['difficulty']}")
    belt_text = belts.render_belt_drill(drill.get(belts.FIELD))
    if belt_text:
        lines.append(f"belt-drill: {belt_text}")
    if ts.get("require_slot") is not None:
        lines.append("require-slot: " + ("yes" if ts["require_slot"] else "no"))
    return lines

def _render_outcome(outcome):

    lines = []
    if outcome and outcome.get("expected_combo"):
        lines.append(f"combo: {outcome['expected_combo']}")
    if outcome and outcome.get("expected_response"):
        lines.append(f"success: {_render_categories(outcome['expected_response'])}")
    return lines

def _render_reversal_slots(ts, slot_outcomes, dummy_char, data_dir):
    lines = []
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
            lines.extend(_render_outcome(slot_outcomes.get(str(cfg["index"]))))
    return lines

def _render_recording_slot(entry, slot_outcomes):

    if isinstance(entry, dict):
        idx, weight, pattern = entry["index"], entry.get("weight"), entry.get("pattern")

        authored = entry.get("action_text")
    else:
        idx, weight, pattern, authored = entry, None, None, None
    lines = ["", f"rec-slot: {idx}"]
    if authored:
        lines.append(f"action: {authored}")
    elif pattern:
        lines.append(f"action: {_render_pattern_notation(pattern)}")

    if weight is not None:
        lines.append(f"weight: {weight}")
    lines.extend(_render_outcome(slot_outcomes.get(str(idx))))
    return lines

def _render_drill_criteria(drill):

    lines = []
    if drill.get("fixed_expected_combo"):
        lines.append("")
        lines.append(f"fixed-combo: {drill['fixed_expected_combo']}")
    if drill.get("fixed_expected_response"):
        lines.append("")
        lines.append(f"fixed-success: {_render_categories(drill['fixed_expected_response'])}")
    if drill.get("survive_seconds"):
        lines.append(f"survive: {drill['survive_seconds']}")
    for field, key in (("against_criteria", "against"), ("expected_setup", "setup")):
        if drill.get(field):
            lines.append(f"{key}: " + ", ".join(_to_kebab(a) for a in drill[field]))
    return lines

def render(drill: dict, dummy_char: str = None, data_dir: Path = None) -> str:

    if drill.get("wongscript_text"):
        return _sync_cached_text(drill)
    dummy_char = dummy_char or drill.get("dummy_character_id")
    ts = drill.get("training_settings") or {}
    slot_outcomes = drill.get("slot_outcomes") or {}

    lines = _render_header(drill, ts, dummy_char)
    lines += _render_pacing(drill, ts)
    lines += _render_settings(drill, ts)
    lines += _render_reversal_slots(ts, slot_outcomes, dummy_char, data_dir)
    for entry in ts.get("recording_slots") or []:
        lines += _render_recording_slot(entry, slot_outcomes)
    lines += _render_drill_criteria(drill)
    return "\n".join(lines) + "\n"
