from . import grader

def grade_combo_attempt(final_combo_cnt: int, target_hits: int) -> int:

    if final_combo_cnt >= target_hits:
        return grader.GOOD
    return grader.AGAIN
