MIN_SPEED = 0
MAX_SPEED = 5
FULL_TAPER_LEVEL = 5

def compute_game_speed(drill: dict, allow_slow_start: bool = True) -> int:

    manual = drill.get("game_speed")
    if manual is not None:
        return manual

    if not allow_slow_start or not drill.get("slow_start"):
        return MAX_SPEED

    level = max(0, drill.get("speed_level") or 0)
    t = min(level / FULL_TAPER_LEVEL, 1.0)
    return round(MIN_SPEED + t * (MAX_SPEED - MIN_SPEED))
