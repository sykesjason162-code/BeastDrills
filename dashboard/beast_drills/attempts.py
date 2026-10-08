from __future__ import annotations

FIELD = "attempts"

SLOT = "slot"
ACTION = "action"
SUPPORTED = (SLOT, ACTION)

DEFAULT = SLOT

def normalize(value) -> str:

    if isinstance(value, str) and value.strip().lower() in SUPPORTED:
        return value.strip().lower()
    return DEFAULT

def errors(value) -> list[str]:

    if value is None:
        return []
    if not isinstance(value, str) or value.strip().lower() not in SUPPORTED:
        return [f"{FIELD} must be one of: {', '.join(SUPPORTED)}"]
    return []
