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

def player_character(path: Path) -> str | None:

    return _read(path, "p1_character_id")
