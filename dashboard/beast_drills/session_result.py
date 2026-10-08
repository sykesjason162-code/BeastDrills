from . import grader

EASY_RATIO = 0.8
GOOD_RATIO = 0.5

EXTRA_CREDIT_PER_HIT = 0.01

def extra_credit_hits(snapshot: dict | None) -> int:

    if not isinstance(snapshot, dict):
        return 0
    total = snapshot.get("p1_hit_count") or 0
    marks = snapshot.get("combo_at")
    if not isinstance(marks, dict) or not marks:

        return 0
    at_success = min(int(v) for v in marks.values())
    return max(0, int(total) - at_success)

def aggregate_session(grades: list, range_points: list | None = None,
                      combo_hits: list | None = None,
                      rep_avoided: list | None = None,
                      self_grade: int | None = None) -> tuple:

    attempts = len(grades)
    if attempts == 0:
        return grader.AGAIN, 0, 0

    successes = sum(1 for grade in grades if grade > grader.AGAIN)

    if range_points is None:
        range_points = [None] * attempts
    if combo_hits is None:
        combo_hits = [None] * attempts
    earned = 0.0
    for i, grade in enumerate(grades):
        if grade <= grader.AGAIN:
            continue
        point = range_points[i] if i < len(range_points) else None
        earned += 1.0 if point is None else float(point)
        hits = combo_hits[i] if i < len(combo_hits) else None
        if hits:
            earned += int(hits) * EXTRA_CREDIT_PER_HIT

    ratio = earned / attempts

    if rep_avoided is not None and attempts:
        clean = sum(1 for ok in rep_avoided if ok) / attempts
        ratio = 0.5 * ratio + 0.5 * clean

    if self_grade is not None:
        felt = max(0.0, min(1.0, (int(self_grade) - grader.AGAIN) / 3.0))
        ratio = (2.0 * ratio + felt) / 3.0

    if ratio == 0:
        overall_grade = grader.AGAIN
    elif ratio >= EASY_RATIO:
        overall_grade = grader.EASY
    elif ratio >= GOOD_RATIO:
        overall_grade = grader.GOOD
    else:
        overall_grade = grader.HARD

    return overall_grade, successes, attempts
