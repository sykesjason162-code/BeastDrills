from datetime import datetime, timezone
import math

from . import grader

MIN_EASE_FACTOR = 1.3
MIN_INTERVAL_DAYS = 1
RELEARN_INTERVAL_DAYS = 1
SECONDS_PER_DAY = 86400

STARTING_STATE = {
    "interval_days": MIN_INTERVAL_DAYS,
    "ease_factor": 2.5,
    "streak": 0,
    "total_sessions": 0,

    "speed_level": 0,
}

def _iso8601(epoch_seconds: float) -> str:
    dt = datetime.fromtimestamp(math.floor(epoch_seconds), tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def schedule_next(state: dict, grade: int, now_epoch: float) -> dict:

    base_interval = max(state.get("interval_days") or 0, MIN_INTERVAL_DAYS)
    ease_factor = state["ease_factor"]
    streak = state["streak"]

    speed_level = state.get("speed_level") or 0

    if grade == grader.AGAIN:
        streak = 0
        speed_level = 0
        interval_days = RELEARN_INTERVAL_DAYS
        ease_factor = max(MIN_EASE_FACTOR, ease_factor - 0.2)
    elif grade == grader.HARD:
        streak = streak + 1

        interval_days = base_interval * 1.2
        ease_factor = max(MIN_EASE_FACTOR, ease_factor - 0.15)
    elif grade == grader.GOOD:
        streak = streak + 1
        speed_level = speed_level + 1
        interval_days = base_interval * ease_factor
    elif grade == grader.EASY:
        streak = streak + 1
        speed_level = speed_level + 1
        interval_days = base_interval * ease_factor * 1.3
        ease_factor = ease_factor + 0.15
    else:
        raise ValueError(f"schedule_next: unknown grade {grade!r}")

    return {
        "interval_days": interval_days,
        "ease_factor": ease_factor,
        "streak": streak,
        "speed_level": speed_level,
        "next_review": _iso8601(now_epoch + interval_days * SECONDS_PER_DAY),
    }
