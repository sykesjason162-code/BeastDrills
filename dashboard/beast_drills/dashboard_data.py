import calendar
import time

from . import deck, game_speed, grader, progress

GRADE_LABELS = {grader.AGAIN: "Again", grader.HARD: "Hard", grader.GOOD: "Good", grader.EASY: "Easy"}

MATURE_STREAK = 5

def bucket_drill(drill: dict, character_id: str | None = None) -> str:

    state = progress.state_for(drill, character_id)
    if not state.get("total_sessions"):
        return "new"
    streak = state.get("streak") or 0
    if streak <= 0:
        return "learning"
    if streak >= MATURE_STREAK:
        return "review_mature"
    return "review_young"

def reviews_to_history_rows(reviews: list) -> list:

    rows = []
    for r in reviews:
        rows.append(
            {
                "date": time.strftime("%Y-%m-%d", time.localtime(r["timestamp"])),
                "attempts": r.get("attempts"),
                "successes": r.get("successes"),
                "final_grade": r.get("final_grade"),

                "character_id": r.get("character_id"),
                "dummy_character_id": r.get("dummy_character_id"),
                "start_side": r.get("start_side"),
            }
        )
    return rows

def compute_grade_stats(history: list) -> dict:

    if not history:
        return {
            "average_grade": None, "last_grade": None, "last_grade_label": None,
            "last_graded_date": None, "total_attempts": 0, "total_successes": 0,
        }

    grades = [h["final_grade"] for h in history if h.get("final_grade") is not None]
    average = round(sum(grades) / len(grades), 2) if grades else None

    total_attempts = sum(h.get("attempts") or 0 for h in history)
    total_successes = sum(h.get("successes") or 0 for h in history)

    last = history[-1]
    last_grade = last.get("final_grade")
    return {
        "average_grade": average,
        "last_grade": last_grade,
        "last_grade_label": GRADE_LABELS.get(last_grade),
        "last_graded_date": last.get("date"),
        "total_attempts": total_attempts,
        "total_successes": total_successes,
    }

def drills_for_character(drills: list, character_id: str | None) -> list:

    if not character_id:
        return list(drills)
    out = []
    for drill in drills:
        if drill.get("character_id") == character_id:
            out.append(drill)
        elif not drill.get("character_id"):
            state = (drill.get("character_progress") or {}).get(character_id)
            if state:
                out.append({**drill, **state})
    return out

def compute_overview(database: dict, now_iso: str, character_id: str | None = None) -> dict:

    drills = drills_for_character(database.get("drills") or [], character_id)
    counts = {"new": 0, "learning": 0, "review_young": 0, "review_mature": 0}
    for drill in drills:
        counts[bucket_drill(drill)] += 1

    return {
        "new": counts["new"],
        "learning": counts["learning"],
        "review_young": counts["review_young"],
        "review_mature": counts["review_mature"],
        "review": counts["review_young"] + counts["review_mature"],
        "due_now": len(deck.get_due_drills(database, now_iso, character_id)),
        "total": len(drills),
    }

def compute_hit_zone_percentages(zone_counts: dict) -> dict:

    high = zone_counts.get("high", 0)
    mid = zone_counts.get("mid", 0)
    low = zone_counts.get("low", 0)
    total = high + mid + low
    if total == 0:
        return {"high": 0.0, "mid": 0.0, "low": 0.0, "total": 0}
    return {
        "high": round(100 * high / total, 1),
        "mid": round(100 * mid / total, 1),
        "low": round(100 * low / total, 1),
        "total": total,
    }

def _sum_zone_counts(*count_dicts) -> dict:
    total = {"high": 0, "mid": 0, "low": 0}
    for counts in count_dicts:
        for key in total:
            total[key] += int((counts or {}).get(key, 0))
    return total

def compute_hit_zones(database: dict, root: str = "hit_zones") -> dict:

    result = {}
    for character_id, per_dummy in (database.get(root) or {}).items():
        if not isinstance(per_dummy, dict):
            continue

        if any(isinstance(v, (int, float)) for v in per_dummy.values()):
            per_dummy = {"unknown": {"unknown": per_dummy}}

        by_dummy, by_side, all_counts = {}, {}, []
        for dummy_id, per_side in per_dummy.items():
            if not isinstance(per_side, dict):
                continue
            dummy_counts = []
            for side, counts in per_side.items():
                if not isinstance(counts, dict):
                    continue
                all_counts.append(counts)
                dummy_counts.append(counts)
                merged = _sum_zone_counts(by_side.get(side, {}).get("counts"), counts)
                by_side[side] = {"counts": merged,
                                 "percentages": compute_hit_zone_percentages(merged)}
            summed = _sum_zone_counts(*dummy_counts)
            by_dummy[dummy_id] = {
                "counts": summed,
                "percentages": compute_hit_zone_percentages(summed),
                "by_side": {
                    side: {"counts": c, "percentages": compute_hit_zone_percentages(c)}
                    for side, c in per_side.items() if isinstance(c, dict)
                },
            }

        total = _sum_zone_counts(*all_counts)
        result[character_id] = {
            "counts": total,
            "percentages": compute_hit_zone_percentages(total),
            "by_dummy": by_dummy,
            "by_side": by_side,
        }
    return result

def _iso_to_epoch(iso_str: str) -> float:

    return calendar.timegm(time.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ"))

def compute_review_days(reviews: list) -> dict:

    days: dict = {}
    total_attempts = 0
    for r in reviews:
        date = time.strftime("%Y-%m-%d", time.localtime(r["timestamp"]))
        bucket = days.setdefault(date, {"attempts": 0, "successes": 0, "sessions": 0})
        bucket["attempts"] += r.get("attempts") or 0
        bucket["successes"] += r.get("successes") or 0
        bucket["sessions"] += 1
        total_attempts += r.get("attempts") or 0
    return {
        "days": days,
        "total_attempts": total_attempts,
        "total_sessions": len(reviews),
        "days_studied": len(days),
    }

def compute_forecast(drills: list, now_iso: str) -> dict:

    today = time.strftime("%Y-%m-%d", time.localtime(_iso_to_epoch(now_iso)))
    days: dict = {}
    backlog = 0
    for drill in drills:
        next_review = drill.get("next_review")
        if not next_review:
            continue
        try:
            date = time.strftime("%Y-%m-%d", time.localtime(_iso_to_epoch(next_review)))
        except ValueError:
            continue
        if date < today:
            backlog += 1
        else:
            days[date] = days.get(date, 0) + 1
    return {"days": days, "backlog": backlog, "total": backlog + sum(days.values())}

def compute_hourly_breakdown(reviews: list) -> dict:

    hours = [{"hour": h, "attempts": 0, "successes": 0, "success_rate": None} for h in range(24)]
    for r in reviews:
        bucket = hours[time.localtime(r["timestamp"]).tm_hour]
        bucket["attempts"] += r.get("attempts") or 0
        bucket["successes"] += r.get("successes") or 0
    for bucket in hours:
        if bucket["attempts"] > 0:
            bucket["success_rate"] = round(100 * bucket["successes"] / bucket["attempts"], 1)
    return {"hours": hours}

_GRADE_KEYS = [str(g) for g in (grader.AGAIN, grader.HARD, grader.GOOD, grader.EASY)]
_MATURITY_BUCKETS = ("new", "learning", "review_young", "review_mature")

def compute_answer_buttons(reviews: list) -> dict:

    by_grade = {k: 0 for k in _GRADE_KEYS}
    by_bucket = {b: {k: 0 for k in _GRADE_KEYS} for b in _MATURITY_BUCKETS}
    for r in reviews:
        grade_key = str(r.get("final_grade"))
        if grade_key not in by_grade:
            continue
        by_grade[grade_key] += 1
        bucket = r.get("bucket_before")
        if bucket in by_bucket:
            by_bucket[bucket][grade_key] += 1
    return {"by_grade": by_grade, "by_bucket": by_bucket}

def _pass_rate(rows: list) -> dict:
    if not rows:
        return None
    passed = sum(1 for r in rows if (r.get("final_grade") or 0) > grader.AGAIN)
    return round(100 * passed / len(rows), 1)

def compute_retention(reviews: list, now_iso: str) -> dict:

    reviewed = [r for r in reviews if r.get("bucket_before") in ("review_young", "review_mature")]
    now_epoch = _iso_to_epoch(now_iso)
    today_str = time.strftime("%Y-%m-%d", time.localtime(now_epoch))
    yesterday_str = time.strftime("%Y-%m-%d", time.localtime(now_epoch - 86400))

    def date_of(r):
        return time.strftime("%Y-%m-%d", time.localtime(r["timestamp"]))

    def bucket(predicate):
        young = [r for r in reviewed if r["bucket_before"] == "review_young" and predicate(r)]
        mature = [r for r in reviewed if r["bucket_before"] == "review_mature" and predicate(r)]
        combined = young + mature
        return {
            "young": _pass_rate(young),
            "mature": _pass_rate(mature),
            "total": _pass_rate(combined),
            "count": len(combined),
        }

    return {
        "today": bucket(lambda r: date_of(r) == today_str),
        "yesterday": bucket(lambda r: date_of(r) == yesterday_str),
        "last_week": bucket(lambda r: r["timestamp"] >= now_epoch - 7 * 86400),
        "last_month": bucket(lambda r: r["timestamp"] >= now_epoch - 30 * 86400),
        "last_year": bucket(lambda r: r["timestamp"] >= now_epoch - 365 * 86400),
        "all_time": bucket(lambda r: True),
    }

def compute_added(drills: list) -> dict:

    days: dict = {}
    total = 0
    for drill in drills:
        created_at = drill.get("created_at")
        if not created_at:
            continue
        try:
            date = time.strftime("%Y-%m-%d", time.localtime(_iso_to_epoch(created_at)))
        except ValueError:
            continue
        days[date] = days.get(date, 0) + 1
        total += 1
    average = round(total / len(days), 1) if days else 0.0
    return {"days": days, "total": total, "average_per_day": average}

PROFILE_EXPORT_VERSION = 1

def build_profile_export(database: dict, exported_at: str, reviews: list | None = None) -> dict:

    drills = database.get("drills") or []
    by_drill: dict = {}
    for row in (reviews or []):
        by_drill.setdefault(row["drill_id"], []).append(row)

    drills = [
        {**d, **compute_grade_stats(reviews_to_history_rows(by_drill.get(d.get("id"), [])))}
        for d in drills
    ]
    zones = compute_hit_zones(database)
    zones_dealt = compute_hit_zones(database, "hit_zones_dealt")

    characters = {}

    for character_id in sorted(set(
            [d.get("character_id") for d in drills if d.get("character_id")]
            + list(zones) + list(zones_dealt)) - {"unknown"}):
        mine = drills_for_character(drills, character_id)
        summary = summarise_drills(mine, character_id)
        zone_counts = (zones.get(character_id) or {}).get("counts") or {}
        dealt_counts = (zones_dealt.get(character_id) or {}).get("counts") or {}

        if not summary["sessions"] and not zone_counts and not dealt_counts:
            continue
        characters[character_id] = {
            "summary": summary,
            "hit_zones": zone_counts,
            "hit_zones_dealt": dealt_counts,
        }

    return {
        "format": "beast_drills_profile",
        "version": PROFILE_EXPORT_VERSION,
        "exported_at": exported_at,
        "characters": characters,
    }

def summarise_drills(drills: list, character_id: str | None = None) -> dict:

    total = lambda key: sum(d.get(key) or 0 for d in drills)
    attempts = total("total_attempts")
    successes = total("total_successes")
    graded = [d["average_grade"] for d in drills if d.get("average_grade")]
    buckets: dict = {}
    for d in drills:
        b = bucket_drill(d, character_id)
        buckets[b] = buckets.get(b, 0) + 1
    return {
        "drills": len(drills),
        "sessions": total("total_sessions"),
        "attempts": attempts,
        "successes": successes,
        "rate": round(successes / attempts * 100) if attempts else None,
        "average_grade": round(sum(graded) / len(graded), 1) if graded else None,
        "best_streak": max((d.get("streak") or 0 for d in drills), default=0),
        "buckets": buckets,
    }
