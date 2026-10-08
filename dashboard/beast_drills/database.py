import json
from pathlib import Path

from . import paths

def load(path) -> tuple:

    p = Path(path)
    if not p.exists():
        return None, f"file not found: {path}"
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f), None
    except (OSError, json.JSONDecodeError) as e:
        return None, str(e)

def save(path, data: dict) -> tuple:

    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, sort_keys=True)
        paths.atomic_replace(tmp, p)
        return True, None
    except OSError as e:
        return False, str(e)
