import json
import time
from pathlib import Path

STALE_AFTER_SECONDS = 5.0

def _read(path: Path, key: str) -> str | None:

    try:
        if not path.exists():
            return None
        if time.time() - path.stat().st_mtime > STALE_AFTER_SECONDS:
            return None
        with open(path, encoding="utf-8") as f:
            return (json.load(f) or {}).get(key) or None
    except (OSError, ValueError):
        return None

def dummy_character(path: Path) -> str | None:

    return _read(path, "p2_character_id")

def running_combo(path: Path) -> tuple | None:

    try:
        if not path.exists() or time.time() - path.stat().st_mtime > STALE_AFTER_SECONDS:
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f) or {}
    except (OSError, ValueError):
        return None
    if str(data.get("session_status") or "") != "running":
        return None
    drill_id, combo = data.get("drill_id"), data.get("expected_combo")
    return (drill_id, combo, data.get("p1_character_id")) if drill_id and combo else None

def player_character(path: Path) -> str | None:

    return _read(path, "p1_character_id")
