import json
import time
from pathlib import Path

from . import paths

def write_outbox_event(outbox_dir, event: dict) -> Path:
    outbox_dir = Path(outbox_dir)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    path = outbox_dir / f"dashboard_{time.time_ns()}.json"
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=4)
    paths.atomic_replace(tmp, path)
    return path
