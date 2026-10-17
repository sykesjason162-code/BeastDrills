import re

_DRILL_ID = re.compile(r"[\w.\-]{1,120}")

def valid_drill_id(value) -> bool:
    return isinstance(value, str) and _DRILL_ID.fullmatch(value) is not None
