import json
import threading
import time
from pathlib import Path

from . import paths

_lock = threading.Lock()
_last = 0

def _next_stamp() -> int:

    global _last
    with _lock:
        _last = max(time.time_ns(), _last + 1)
        return _last

def write_outbox_event(outbox_dir, event: dict) -> Path:
    outbox_dir = Path(outbox_dir)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    path = outbox_dir / f"dashboard_{_next_stamp()}.json"
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=4)
    paths.atomic_replace(tmp, path)
    return path
