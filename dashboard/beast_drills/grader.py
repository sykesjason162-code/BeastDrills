AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4

EASY_FRACTION = 0.5

def grade_attempt(attempt: dict) -> int:
    if attempt.get("outcome") != "hit":
        return AGAIN

    optimal = attempt.get("optimal_frame_window")
    maximum = attempt.get("maximum_frame_window")
    if optimal is None or maximum is None:
        raise ValueError(
            "grade_attempt: attempt with outcome 'hit' requires "
            "optimal_frame_window and maximum_frame_window"
        )

    frame_diff = attempt.get("frame_diff")
    if frame_diff is None:
        raise ValueError("grade_attempt: attempt with outcome 'hit' requires frame_diff")

    if frame_diff > maximum:
        return AGAIN
    elif frame_diff > optimal:
        return HARD
    elif frame_diff <= optimal * EASY_FRACTION:
        return EASY
    else:
        return GOOD
