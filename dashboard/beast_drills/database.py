import hashlib
import json
import os
import time
from pathlib import Path

from . import paths

def load(path) -> tuple:

    p = Path(path)
    if not p.exists():
        return None, f"file not found: {path}"
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f), None
    except (OSError, json.JSONDecodeError) as e:
        return None, str(e)

def save(path, data: dict) -> tuple:

    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        paths.atomic_replace(tmp, p)
        return True, None
    except OSError as e:
        return False, str(e)

def back_up_unreadable(path, backups_dir) -> tuple:

    p = Path(path)
    try:
        content = p.read_bytes()
    except OSError as e:
        return None, str(e)
    try:
        json.loads(content.decode("utf-8"))
        return None, "it parses now"
    except ValueError:
        pass

    folder = Path(backups_dir)
    digest = hashlib.sha256(content).hexdigest()[:12]
    for existing in sorted(folder.glob(f"{p.stem}.unreadable-*-{digest}{p.suffix}")):
        if existing.read_bytes() == content:
            return existing, None
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    copy = folder / f"{p.stem}.unreadable-{stamp}-{digest}{p.suffix}"
    tmp = copy.with_suffix(copy.suffix + ".tmp")
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with open(tmp, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        paths.atomic_replace(tmp, copy)
    except OSError as e:
        return None, str(e)
    return copy, None

def unreadable_message(path, backups_dir, err) -> str:

    copy, copy_err = back_up_unreadable(path, backups_dir)
    text = f"{Path(path).name} exists but could not be read, and was left untouched: {err}."
    if copy:
        text += (f" The broken file was also kept as {copy}, so nothing is lost. To recover,"
                 f" fix {Path(path).name} by hand or put back an older copy from {Path(backups_dir)}.")
    return text
