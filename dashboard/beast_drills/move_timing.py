import json
import re
from pathlib import Path

from . import paths
from .move_catalog import _normalize

_FRAME_DATA_DIR_NAME = "frame_data"

_CONNECTED_DIR_NAME = "frame_data_connected"

_cache: dict = {}

_RANGE_ONLY = re.compile(r"^\s*(\d+)\s*~\s*(\d+)\s*$")
_LEADING_INT = re.compile(r"^\s*(\d+)")

def _frames(raw, numeric):

    if isinstance(numeric, int):
        return numeric
    if not isinstance(raw, str):
        return None
    ranged = _RANGE_ONLY.match(raw)
    if ranged:
        return max(int(ranged.group(1)), int(ranged.group(2)))
    lead = _LEADING_INT.match(raw)
    return int(lead.group(1)) if lead else None

def _load(character_id: str, data_dir: Path) -> dict:

    key = (character_id, str(data_dir))
    if key in _cache:
        return _cache[key]
    path = paths.reference_dir(data_dir, _FRAME_DATA_DIR_NAME) / f"{character_id}.json"
    table: dict = {}
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        for move in payload.get("moves") or []:
            notation = move.get("input")
            if not notation:
                continue

            table.setdefault(_normalize(notation), move)
    except (OSError, ValueError):
        table = {}
    _cache[key] = table
    return table

def _load_connected(character_id: str, data_dir: Path) -> dict:
    key = ("connected", character_id, str(data_dir))
    if key in _cache:
        return _cache[key]

    path = paths.reference_dir(data_dir, _CONNECTED_DIR_NAME) / f"{character_id}.json"
    table: dict = {}
    try:
        with open(path, encoding="utf-8") as f:
            for notation, frames in (json.load(f) or {}).items():
                if not isinstance(frames, int) or frames <= 0:
                    continue

                canonical = _normalize(notation)
                if frames > table.get(canonical, 0):
                    table[canonical] = frames
    except (OSError, ValueError, AttributeError):
        table = {}
    _cache[key] = table
    return table

def connected_duration(character_id: str, notation: str, data_dir: Path):

    if not character_id or not notation:
        return None
    return _load_connected(character_id, data_dir).get(_normalize(notation))

def tape_duration(character_id: str, notation: str, data_dir: Path):

    connected = connected_duration(character_id, notation, data_dir)
    whiff = duration(character_id, notation, data_dir)
    if connected is None:
        return whiff
    if whiff is None:
        return connected
    return max(connected, whiff)

def find(character_id: str, notation: str, data_dir: Path):

    if not character_id or not notation:
        return None
    return _load(character_id, data_dir).get(_normalize(notation))

def duration(character_id: str, notation: str, data_dir: Path):

    move = find(character_id, notation, data_dir)
    if move is None:
        return None
    total = _frames(move.get("total"), move.get("total_n"))
    if isinstance(total, int) and total > 0:
        return total
    parts = [_frames(move.get(k), move.get(k + "_n"))
             for k in ("startup", "active", "recovery")]
    if all(isinstance(p, int) for p in parts):
        return sum(parts)
    return None

def connected_duration_known(character_id: str, notation: str, data_dir: Path):

    move = find(character_id, notation, data_dir)
    if move is None:
        return None
    return (move.get("moveType") or "").lower() != "throw"
