"""The main service loop: watches the outbox directory Lua writes to,
grades reps and finalizes sessions using the ported core/*.py logic, owns
shared_database.json, and keeps the inbox file (next due drill + a
heartbeat) fresh for Lua to read.

Run manually before playing -- REFramework can't spawn this itself (no
`io.popen` in its Lua bindings, confirmed in
_reference/REFramework/src/mods/bindings/FS.cpp). See docs/SERVICE.md.

File protocol (all paths relative to the BeastDrills_data directory REFramework
resolves reframework/data/ paths against):
  outbox/*.json   -- Lua writes one file per event (rep_result,
                     session_concluded), never overwritten -- durable
                     queue, nothing lost if this service is slow/down.
                     This service deletes each file after processing.
  _inbox.json     -- this service writes the current due drill + a
                     heartbeat timestamp; Lua reads it fresh each time
                     it wants to start a session and fails closed if the
                     heartbeat is stale (see session.lua).
  shared_database.json -- owned entirely by this service now (drill
                     definitions + CURRENT scheduling state). Lua no
                     longer reads or writes it.
  stats.db  -- owned entirely by this service (2026-08-15). The
                     append-only per-session review log -- one row per
                     concluded session -- that used to live as each
                     drill's own `history` array inside
                     shared_database.json, moved out to SQLite so the
                     dashboard's Stats panels can do real day/hour/
                     grade-bucketed aggregation. See reviews_db.py.
"""

import argparse
import json
import logging
import logging.handlers
import time
from pathlib import Path

from . import attempts, gauges, mods, paths, settings

from . import (
    combo_check,
    criteria,
    session_breakdown,
    session_progress,
    dashboard_data,
    database,
    deck,
    difficulty,
    duplicates,
    game_speed,
    grader,
    response_check,
    attack_string,
    live_status,
    move_catalog,
    progress,
    wongscript,
    response_window,
    reviews_db,
    scrimmage,
    scheduler,
    session_result,
)

DASHBOARD_PORT = 8765

log = logging.getLogger("beast_drills")

POLL_SECONDS = 0.5
HEARTBEAT_STALE_AFTER_SECONDS = 5

_DEV_INSTALL = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Street Fighter 6\reframework\data\BeastDrills_data"
)

def _default_install(here: Path | None = None) -> Path:

    here = here or Path(__file__).resolve().parent
    if here.parent.name == "dashboard":
        shipped = here.parent.parent / "reframework" / "data" / "BeastDrills_data"
        if shipped.is_dir():
            return shipped
    return _DEV_INSTALL

DEFAULT_DATA_DIR = _default_install()

def _recording_slot_index(entry):

    if isinstance(entry, dict):
        return entry.get("index")
    return entry

def _preserve_recorded_patterns(old_training_settings, new_training_settings):

    if not isinstance(new_training_settings, dict):
        return new_training_settings
    new_slots = new_training_settings.get("recording_slots")
    if not isinstance(new_slots, list) or not new_slots:
        return new_training_settings

    carried = ("pattern", "action_text")
    old_slots = (old_training_settings or {}).get("recording_slots") or []
    old_values = {}
    for entry in old_slots:
        idx = _recording_slot_index(entry)
        if idx is None or not isinstance(entry, dict):
            continue
        kept = {k: entry[k] for k in carried if entry.get(k)}
        if kept:
            old_values[idx] = kept

    if not old_values:
        return new_training_settings

    merged_slots = []
    changed = False
    for entry in new_slots:
        idx = _recording_slot_index(entry)
        for key in carried:
            if isinstance(entry, dict) and key not in entry and key in old_values.get(idx, {}):
                entry = dict(entry)
                entry[key] = old_values[idx][key]
                changed = True
        merged_slots.append(entry)

    if not changed:
        return new_training_settings
    merged = dict(new_training_settings)
    merged["recording_slots"] = merged_slots
    return merged

class Service:
    def __init__(self, data_dir: Path, install_dir: Path | None = None):
        self.data_dir = data_dir

        self.install_dir = install_dir or data_dir

        paths.ensure(data_dir)

        for moved in paths.migrate(data_dir):
            log.info("tidied: %s", moved)

        for moved in paths.relocate(self.install_dir, data_dir):
            log.info("moved out of the game folder: %s", moved)

        legacy = paths.outbox(self.install_dir)
        self.legacy_outbox_dir = (
            legacy if legacy.resolve() != paths.outbox(data_dir).resolve() else None)
        self.outbox_dir = paths.outbox(data_dir)
        self.inbox_path = paths.inbox(data_dir)
        self.live_status_path = paths.live_status(data_dir)
        self.db_path = paths.database(data_dir)
        self.example_db_path = paths.example_database(data_dir)

        self.stats_db_path = paths.stats_db(data_dir)
        cfg = settings.load(DEFAULT_DATA_DIR)

        self.dashboard_url = settings.dashboard_url(cfg)

        self.default_response_window = cfg[("practice", "response_window")]
        self.allow_slow_start = cfg[("practice", "allow_slow_start")]
        self.default_reps = cfg[("practice", "reps")]

        scrimmage.configure(
            rounds_per_set=cfg[("scrimmage", "rounds_per_set")],
            max_cpu_level=cfg[("scrimmage", "max_cpu_level")])

        self._sessions_in_progress: dict[str, list[int]] = {}

        self._session_range_points: dict[str, list] = {}

        self._session_combo_hits: dict[str, list] = {}
        self._session_rep_avoided: dict[str, list] = {}
        self._session_reps: dict[str, list] = {}

        self._progress_path = paths.session_progress(self.data_dir)
        self._restore_progress()

        self._scrimmage_rounds: dict[str, list] = {}

    def _load_db(self) -> dict:
        data, err = database.load(self.db_path)
        if data is not None:
            return data
        example, ex_err = database.load(self.example_db_path)
        if example is None:
            raise RuntimeError(f"no database and no example to bootstrap from: {ex_err}")
        ok, save_err = database.save(self.db_path, example)
        if not ok:
            raise RuntimeError(f"bootstrap save failed: {save_err}")
        log.info("Seeded shared_database.json from the example file (first run).")
        return example

    def _find_drill(self, db: dict, drill_id: str) -> dict | None:
        for d in db.get("drills") or []:
            if d.get("id") == drill_id:
                return d
        return None

    def _retime_for_dummy(self, drill: dict, dummy_character_id: str | None) -> bool:

        if drill.get("dummy_character_id") or not dummy_character_id:
            return False
        settings = drill.get("training_settings")
        if not isinstance(settings, dict):
            return False
        slots = settings.get("recording_slots")
        if not isinstance(slots, list) or not slots:
            return False

        changed = False
        for slot in slots:
            if isinstance(slot, dict) and slot.get("action_text"):
                frames = wongscript.retime_pattern(
                    slot["action_text"], dummy_character_id, self.data_dir)

                if frames and frames != slot.get("pattern"):
                    slot["pattern"] = frames
                    changed = True
        return changed

    def _retime_stored_patterns(self, db: dict) -> None:

        dummy = live_status.dummy_character(self.live_status_path)
        if not dummy:
            return
        changed = False
        for drill in db.get("drills") or []:
            if self._retime_for_dummy(drill, dummy):
                changed = True
        if not changed:
            return
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving retimed patterns: %s", err)
        else:
            log.info("retimed recorded tapes for dummy=%s", dummy)

    def _prepare_due(self, drill: dict | None) -> dict | None:
        if drill is None:
            return None

        drill = dict(drill)

        if self.default_reps and not drill.get("reps"):
            drill["reps"] = self.default_reps
        drill["response_window_frames"] = response_window.compute_response_window_frames(
            drill, self.default_response_window)
        drill["game_speed"] = game_speed.compute_game_speed(
            drill, self.allow_slow_start)

        settings_copy = dict(drill.get("training_settings") or {})
        for gauge in gauges.PAIR_KEYS:
            if gauge not in settings_copy:
                continue

            problems = gauges.errors(gauge, settings_copy[gauge])
            if problems:
                log.warning("drill=%s %s -- using the default instead",
                            drill.get("id"), "; ".join(problems))
                settings_copy.pop(gauge)
                continue
            settings_copy[gauge] = gauges.resolved(gauge, settings_copy[gauge])
        if gauges.cpu_level_errors(settings_copy.get("cpu_level")):
            log.warning("drill=%s cpu_level %r is out of range -- ignored",
                        drill.get("id"), settings_copy.get("cpu_level"))
            settings_copy.pop("cpu_level", None)
        drill["training_settings"] = settings_copy

        return drill

    def _write_inbox(self, db: dict) -> None:
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        played_as = live_status.player_character(self.live_status_path)

        dummy = live_status.dummy_character(self.live_status_path)
        next_drill = deck.select_next_drill(
            deck.get_due_drills(db, now_iso, played_as, dummy))

        next_favorite = deck.select_next_drill(
            deck.get_due_drills(db, now_iso, played_as, dummy, favorites_only=True))

        payload = {
            "heartbeat": time.time(),
            "due_drill": self._prepare_due(next_drill),
            "due_favorite": self._prepare_due(next_favorite),
            "scrimmage_cpu_level": scrimmage.level_for(
                db.get("scrimmage"), played_as or "", dummy or ""),

            "scrimmage_difficulty": difficulty.parameters_for(
                scrimmage.level_for(db.get("scrimmage"), played_as or "", dummy or ""),
                ((db.get("scrimmage") or {}).get(played_as or "", {})
                 .get(dummy or "", {}).get("handicap") or 0)),

            "dashboard_url": self.dashboard_url,
        }
        tmp = self.inbox_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        paths.atomic_replace(tmp, self.inbox_path)

    def _record_rep(self, session_id: str, grade: int, event: dict,
                    against=None, setup=None, outcome=None) -> int:

        self._sessions_in_progress.setdefault(session_id, []).append(grade)
        self._session_range_points.setdefault(session_id, []).append(event.get("range_point"))

        try:
            avoided = criteria.rep_avoided(event.get("snapshot") or {}, against)
        except ValueError as exc:
            log.warning("bad against_criteria (%s) -- counting the rep as not clean", exc)
            avoided = False
        self._session_rep_avoided.setdefault(session_id, []).append(avoided)

        expected = event.get("expected_response")
        if expected is not None:
            outcome, _ = response_check.check_response(
                expected, event.get("snapshot") or {}, setup)
        self._session_reps.setdefault(session_id, []).append({
            "slot": event.get("slot"),
            "expected_response": expected,
            "expected_combo": event.get("expected_combo"),
            "snapshot": event.get("snapshot") or {},
            "outcome": outcome,
        })

        is_combo_drill = event.get("drill_type") == "combo"
        self._session_combo_hits.setdefault(session_id, []).append(
            None if is_combo_drill
            else session_result.extra_credit_hits(event.get("snapshot")))

        self._save_progress()
        return len(self._sessions_in_progress[session_id])

    def _lists_for(self, session_id: str) -> dict:
        return {
            "grades": self._sessions_in_progress.get(session_id, []),
            "range_points": self._session_range_points.get(session_id, []),
            "combo_hits": self._session_combo_hits.get(session_id, []),
            "rep_avoided": self._session_rep_avoided.get(session_id, []),
            "reps": self._session_reps.get(session_id, []),
        }

    def _save_progress(self) -> None:

        state = {sid: self._lists_for(sid) for sid in self._sessions_in_progress}
        ok, err = session_progress.save(self._progress_path, state)
        if not ok:
            log.warning("could not save session progress (%s) -- a restart "
                        "before this session ends would lose it", err)

    def _restore_progress(self) -> None:
        restored = session_progress.load(self._progress_path)
        for session_id, lists in restored.items():
            self._sessions_in_progress[session_id] = lists["grades"]
            self._session_range_points[session_id] = lists["range_points"]
            self._session_combo_hits[session_id] = lists["combo_hits"]
            self._session_rep_avoided[session_id] = lists["rep_avoided"]
            self._session_reps[session_id] = lists["reps"]
            log.info("resumed session %s with %d rep(s) already recorded",
                     session_id, len(lists["grades"]))

    def _handle_rep_result(self, event: dict, db: dict) -> None:
        session_id = event["session_id"]
        drill_id = event["drill_id"]
        drill = self._find_drill(db, drill_id)
        if drill is None:
            log.warning("rep_result for unknown drill_id=%s, ignoring", drill_id)
            return

        verdict = None

        if drill.get("drill_type") == "combo":
            grade = combo_check.grade_combo_attempt(
                event["final_combo_cnt"], drill.get("target_combo_hits", 0)
            )

            verdict = "hit" if grade != grader.AGAIN else "miss"
        else:
            expected_response = event.get("expected_response")
            snapshot = event.get("snapshot", {})

            expected_combo = event.get("expected_combo")
            if expected_combo:
                spec_errors = []
                spec = attack_string.parse_attack_string(expected_combo, spec_errors)
                if spec is None:
                    log.warning(
                        "unparseable expected_combo=%r for drill_id=%s (%s) -- grading AGAIN",
                        expected_combo, drill_id, spec_errors,
                    )
                    grade = grader.AGAIN
                else:

                    move_ids = snapshot.get("p1_move_ids")
                    char = drill.get("character_id")
                    spec_sets, cat_err = (None, None)
                    combo_mode, combo_text = attack_string.split_mode(expected_combo)
                    if move_ids is not None and char:

                        spec_sets, cat_err = move_catalog.resolve_all(
                            char, [attack_string.strip_movement_prefix(t)
                                   for t in combo_text.split(",")
                                   if t.strip() and not attack_string.is_movement(t)],
                            self.data_dir,
                        )
                    if spec_sets:

                        moves = move_catalog.filter_to_moves(char, move_ids, self.data_dir)
                        landed = moves
                        ok, why = attack_string.check_move_ids(spec_sets, moves, combo_mode)
                        log.info("combo %s (move-id, %s) drill=%s moves=%s raw=%s%s",
                                 "HIT" if ok else "miss", combo_mode, drill_id, moves,
                                 (move_ids or [])[:12], "" if ok else f" -- {why}")
                        total = self._record_rep(
                            session_id, grader.GOOD if ok else grader.AGAIN, event,
                            outcome="hit" if ok else "miss")
                        log.info("graded rep for session=%s drill=%s -> %s (total this session: %d)",
                                 session_id, drill_id,
                                 grader.GOOD if ok else grader.AGAIN, total)
                        return
                    if cat_err:
                        log.warning("combo catalog: %s (falling back)", cat_err)
                    inputs = snapshot.get("p1_attack_inputs")
                    if inputs is not None:
                        landed = inputs

                        ok, why = attack_string.check_attack_inputs(
                            spec, inputs, snapshot.get("p1_hit_count") or 0,
                            combo_mode,
                        )
                    else:
                        landed = snapshot.get("p1_landed_attacks") or []
                        ok, why = attack_string.check_attack_string(spec, landed)
                    grade = grader.GOOD if ok else grader.AGAIN
                    verdict = "hit" if ok else "miss"

                    readable = ", ".join(
                        wongscript._bits_to_code(
                            e.get("bits", 0) if isinstance(e, dict) else e
                        )
                        + ("" if not (isinstance(e, dict) and e.get("comboed_from_previous")) else "*")
                        for e in landed
                    ) or "(nothing)"
                    log.info(
                        "combo %s for drill_id=%s: landed [%s] vs spec %r%s",
                        "HIT" if ok else "miss", drill_id, readable, expected_combo,
                        "" if ok else f" -- {why}",
                    )
            elif expected_response is None and drill.get("against_criteria"):

                try:
                    ok = criteria.rep_avoided(snapshot, drill["against_criteria"])
                except ValueError as exc:
                    log.warning("bad against_criteria on drill_id=%s (%s) -- grading AGAIN",
                                drill_id, exc)
                    ok = False
                grade = grader.GOOD if ok else grader.AGAIN
                verdict = "hit" if ok else "miss"
            elif expected_response is None:
                grade = grader.AGAIN
            else:
                grade, reason = response_check.grade_response(
                    expected_response, snapshot, drill.get("expected_setup"))
                if grade is None:
                    log.warning(
                        "unsupported expected_response=%r for drill_id=%s (%s) -- grading AGAIN",
                        expected_response, drill_id, reason,
                    )
                    grade = grader.AGAIN

        total = self._record_rep(session_id, grade, event,
                                 drill.get("against_criteria"),
                                 drill.get("expected_setup"),
                                 outcome=verdict)
        log.info(
            "graded rep for session=%s drill=%s -> %s (total this session: %d)",
            session_id, drill_id, grade, total,
        )

        result_payload = {"session_id": session_id, "drill_id": drill_id, "grade": grade}
        tmp = paths.last_rep_result(self.data_dir).with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, indent=4)
        paths.atomic_replace(tmp, paths.last_rep_result(self.data_dir))

    def _handle_session_concluded(self, event: dict, db: dict) -> None:
        session_id = event["session_id"]
        drill_id = event["drill_id"]
        grades = self._sessions_in_progress.pop(session_id, [])
        range_points = self._session_range_points.pop(session_id, [])
        combo_hits = self._session_combo_hits.pop(session_id, [])
        rep_avoided = self._session_rep_avoided.pop(session_id, [])
        reps = self._session_reps.pop(session_id, [])
        self._save_progress()
        drill = self._find_drill(db, drill_id)
        if drill is None:
            log.warning("session_concluded for unknown drill_id=%s, ignoring", drill_id)
            return

        claimed = event.get("attempt_count")
        if isinstance(claimed, int) and claimed > len(grades):
            log.error(
                "session %s for %s is incomplete: the plugin counted %d attempt(s) "
                "and this side has %d -- NOT grading or rescheduling, because a "
                "partial session would write a real interval off a fragment",
                session_id, drill_id, claimed, len(grades))
            self._write_session_result({
                "session_id": session_id,
                "drill_id": drill_id,
                "attempts": len(grades),
                "successes": 0,
                "final_grade": None,
                "self_grade": event.get("self_grade"),
                "incomplete": True,
                "counted_by_plugin": claimed,
                "breakdown_lines": [
                    "Session incomplete -- NOT graded.",
                    f"You played {claimed}, but only {len(grades)} reached the service.",
                    "Nothing was rescheduled.",
                ],
            })
            return

        mixed = bool(drill.get("against_criteria")) and bool(
            drill.get("fixed_expected_response") or drill.get("slot_outcomes"))

        self_grade = event.get("self_grade")
        overall_grade, successes, attempts = session_result.aggregate_session(
            grades, range_points, combo_hits,
            rep_avoided if mixed else None,
            self_grade)
        now_epoch = time.time()

        played_as = event.get("character_id") or drill.get("character_id")
        bucket_before = dashboard_data.bucket_drill(drill, played_as)
        prior = progress.state_for(drill, played_as)
        new_state = scheduler.schedule_next(
            {
                "interval_days": prior.get("interval_days"),
                "ease_factor": prior.get("ease_factor"),
                "streak": prior.get("streak") or 0,
            },
            overall_grade,
            now_epoch,
        )
        new_state["total_sessions"] = (prior.get("total_sessions") or 0) + 1
        progress.apply_state(drill, played_as, new_state)

        review_ok, review_err = reviews_db.record_review(
            self.stats_db_path, drill_id, now_epoch, attempts, successes, overall_grade,
            bucket_before,
            character_id=played_as,
            dummy_character_id=event.get("dummy_character_id") or drill.get("dummy_character_id"),
            start_side=event.get("start_side"),
        )
        if not review_ok:
            log.error("failed recording review in %s: %s", self.stats_db_path, review_err)
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after session_concluded: %s", err)
        log.info(
            "session concluded: drill=%s attempts=%d successes=%d grade=%s next_review=%s",
            drill_id, attempts, successes, overall_grade, new_state["next_review"],
        )

        breakdown = session_breakdown.summarise(reps)
        result_payload = {
            "session_id": session_id,
            "drill_id": drill_id,
            "attempts": attempts,
            "successes": successes,
            "final_grade": overall_grade,
            "self_grade": self_grade,
            "breakdown": breakdown,
            "breakdown_lines": session_breakdown.lines(breakdown),
        }
        self._write_session_result(result_payload)

    def _write_session_result(self, payload: dict) -> None:

        tmp = (paths.last_session_result(self.data_dir)).with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        paths.atomic_replace(tmp, paths.last_session_result(self.data_dir))

    def _handle_update_drill(self, event: dict, db: dict) -> None:

        drill_id = event["drill_id"]
        patch = event.get("patch", {})
        drill = self._find_drill(db, drill_id)
        if drill is None:
            log.warning("update_drill_request for unknown drill_id=%s, ignoring", drill_id)
            return
        drill["name"] = patch.get("name")
        drill["description"] = patch.get("description")
        drill["training_settings"] = _preserve_recorded_patterns(
            drill.get("training_settings"), patch.get("training_settings")
        )
        drill["slot_outcomes"] = self._preserve_slot_combos(
            drill.get("slot_outcomes"), patch.get("slot_outcomes")
        )
        drill["fixed_expected_response"] = patch.get("fixed_expected_response")

        if "fixed_expected_combo" in patch:
            drill["fixed_expected_combo"] = patch["fixed_expected_combo"]

        drill["response_window_frames"] = patch.get("response_window_frames")
        drill["game_speed"] = patch.get("game_speed")

        drill["reps"] = patch.get("reps")

        if patch.get("character_id"):
            drill["character_id"] = patch["character_id"]
        else:
            drill.pop("character_id", None)

        if patch.get("dummy_character_id"):
            drill["dummy_character_id"] = patch["dummy_character_id"]
        else:
            drill.pop("dummy_character_id", None)

        if patch.get("difficulty"):
            drill["difficulty"] = patch["difficulty"]
        else:
            drill.pop("difficulty", None)

        if patch.get("expected_setup"):
            drill["expected_setup"] = patch["expected_setup"]
        else:
            drill.pop("expected_setup", None)
        if patch.get("against_criteria"):
            drill["against_criteria"] = patch["against_criteria"]
        else:
            drill.pop("against_criteria", None)
        if patch.get("survive_seconds"):
            drill["survive_seconds"] = patch["survive_seconds"]
        else:
            drill.pop("survive_seconds", None)
        if patch.get("trains"):
            drill["trains"] = patch["trains"]
        else:
            drill.pop("trains", None)

        if patch.get("trains_for"):
            drill["trains_for"] = patch["trains_for"]
        else:
            drill.pop("trains_for", None)

        if attempts.normalize(patch.get(attempts.FIELD)) != attempts.DEFAULT:
            drill[attempts.FIELD] = attempts.normalize(patch.get(attempts.FIELD))
        else:
            drill.pop(attempts.FIELD, None)

        if patch.get("wongscript_text"):
            drill["wongscript_text"] = patch["wongscript_text"]
        else:
            drill.pop("wongscript_text", None)
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after update_drill_request: %s", err)
        else:
            log.info("updated drill=%s", drill_id)

    @staticmethod
    def _preserve_slot_combos(old_outcomes, new_outcomes):

        if not isinstance(old_outcomes, dict) or not isinstance(new_outcomes, dict):
            return new_outcomes
        for slot_key, new_entry in new_outcomes.items():
            old_entry = old_outcomes.get(slot_key)
            if not isinstance(old_entry, dict) or not isinstance(new_entry, dict):
                continue
            for field in ("expected_combo", "note"):
                if field not in new_entry and old_entry.get(field):
                    new_entry[field] = old_entry[field]
        return new_outcomes

    def _handle_set_drill_selection(self, event: dict, db: dict) -> None:

        drill_id = event["drill_id"]
        drill = self._find_drill(db, drill_id)
        if drill is None:
            log.warning("set_drill_selection_request for unknown drill_id=%s, ignoring", drill_id)
            return
        drill["selected"] = bool(event.get("selected"))
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after set_drill_selection_request: %s", err)
        else:
            log.info("set selected=%s for drill=%s", drill["selected"], drill_id)

    def _handle_character_data_update(self, event: dict) -> None:

        character_id = event.get("character_id")
        moves = event.get("moves")
        if not character_id or not isinstance(moves, list):
            log.warning("character_data_update with no character_id/moves, ignoring")
            return

        by_notation: dict = {}
        by_action_id: dict = {}
        for move in moves:
            if not isinstance(move, dict):
                continue
            action_id = move.get("action_id")
            record = {k: move.get(k) for k in ("total_frames", "startup", "active", "reach")
                      if move.get(k) is not None}
            if not record or action_id is None:
                continue
            by_action_id[str(action_id)] = record
            notation = move_catalog.notation_for(character_id, action_id)
            if notation:

                prior = by_notation.get(notation)
                if prior is None or (record.get("total_frames") or 0) > (prior.get("total_frames") or 0):
                    by_notation[notation] = record

        observed = event.get("observed_totals")
        if isinstance(observed, list) and observed:
            self._merge_observed_totals(character_id, observed)

        out_dir = self.data_dir / "character_data"
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "character_id": character_id,
            "source": event.get("source") or "game",
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "by_notation": by_notation,
            "by_action_id": by_action_id,
        }
        path = out_dir / f"{character_id}.json"
        tmp = path.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            paths.atomic_replace(tmp, path)
        except OSError as err:
            log.error("failed writing %s: %s", path, err)
            return
        log.info("character data updated: %s -- %d moves, %d named %s",
                 character_id, len(by_action_id), len(by_notation),
                 event.get("shape") or "")

    def _merge_observed_totals(self, character_id: str | None, rows: list) -> None:

        if not character_id or not rows:
            return
        path = self.install_dir / "frame_data_connected" / f"{character_id}.json"
        existing: dict = {}
        try:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    existing = json.load(f) or {}
        except (OSError, ValueError):
            existing = {}

        added = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            action_id, frames = row.get("action_id"), row.get("frames")
            if action_id is None or not isinstance(frames, int) or frames <= 0:
                continue
            notation = move_catalog.notation_for(character_id, action_id)
            if not notation:
                continue

            notation = move_catalog._normalize(notation)
            if frames > int(existing.get(notation) or 0):
                existing[notation] = frames
                added += 1

        if not added:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, sort_keys=True)
            paths.atomic_replace(tmp, path)
            log.info("observed move timings: %s -- %d updated, %d known",
                     character_id, added, len(existing))
        except OSError as err:
            log.error("failed writing %s: %s", path, err)

    def _handle_open_dashboard(self) -> None:

        import webbrowser
        url = f"http://localhost:{DASHBOARD_PORT}"
        try:
            webbrowser.open(url)
            log.info("opened the dashboard: %s", url)
        except Exception as err:
            log.error("could not open %s: %s", url, err)

    def _handle_set_drill_favorite(self, event: dict, db: dict) -> None:

        drill_id = event["drill_id"]
        drill = self._find_drill(db, drill_id)
        if drill is None:
            log.warning("set_drill_favorite_request for unknown drill_id=%s, ignoring", drill_id)
            return
        drill["favorite"] = bool(event.get("favorite"))
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after set_drill_favorite_request: %s", err)
        else:
            log.info("set favorite=%s for drill=%s", drill["favorite"], drill_id)

    def _handle_set_drill_selection_bulk(self, event: dict, db: dict) -> None:

        drill_ids = set(event.get("drill_ids") or [])
        selected = bool(event.get("selected"))
        changed = 0
        for drill in db.get("drills") or []:
            if drill.get("id") in drill_ids:
                drill["selected"] = selected
                changed += 1
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after set_drill_selection_bulk_request: %s", err)
        else:
            log.info("set selected=%s for %d drill(s)", selected, changed)

    def _handle_merge_duplicates(self, event: dict, db: dict) -> None:

        keep_id = event.get("keep_id")
        merge_ids = [i for i in (event.get("merge_ids") or []) if i != keep_id]
        drills = db.get("drills") or []
        by_id = {d.get("id"): d for d in drills}

        keep = by_id.get(keep_id)
        missing = [i for i in [keep_id] + merge_ids if i not in by_id]
        if keep is None or missing:
            log.warning("merge_duplicates_request names unknown drill(s) %s, ignoring", missing)
            return
        if not merge_ids:
            log.warning("merge_duplicates_request for %s has nothing to merge", keep_id)
            return

        members = [keep] + [by_id[i] for i in merge_ids]
        plan = duplicates.merge_plan(
            members, reviews_db.last_reviewed(self.stats_db_path))
        if plan is None:

            plan = {"merged": {"total_sessions": sum(
                d.get("total_sessions") or 0 for d in members)}}
        keep.update(plan["merged"])

        for drill_id in merge_ids:
            reviews_db.rekey_drill(self.stats_db_path, drill_id, keep_id)
        db["drills"] = [d for d in drills if d.get("id") not in set(merge_ids)]
        deleted_ids = db.setdefault("deleted_drill_ids", [])
        for drill_id in merge_ids:
            if drill_id not in deleted_ids:
                deleted_ids.append(drill_id)

        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after merge_duplicates_request: %s", err)
        else:
            log.info("merged %s into %s (sessions now %s)", merge_ids, keep_id,
                     keep.get("total_sessions"))

    def _handle_delete_drill(self, event: dict, db: dict) -> None:

        drill_id = event["drill_id"]
        drills = db.get("drills") or []
        found = any(d.get("id") == drill_id for d in drills)
        if not found:
            log.warning("delete_drill_request for unknown drill_id=%s, ignoring", drill_id)
            return
        db["drills"] = [d for d in drills if d.get("id") != drill_id]
        deleted_ids = db.setdefault("deleted_drill_ids", [])
        if drill_id not in deleted_ids:
            deleted_ids.append(drill_id)
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after delete_drill_request: %s", err)
        else:
            log.info("deleted drill=%s", drill_id)

    UNKNOWN_BUCKET = "unknown"

    @classmethod
    def _migrate_hit_zones(cls, hit_zones: dict) -> dict:

        for character_id, value in list(hit_zones.items()):
            if not isinstance(value, dict):
                continue

            if any(isinstance(v, (int, float)) for v in value.values()):
                hit_zones[character_id] = {
                    cls.UNKNOWN_BUCKET: {cls.UNKNOWN_BUCKET: value}
                }
        return hit_zones

    def _handle_tally_recorded(self, event: dict) -> None:

        ok, err = reviews_db.record_tally(
            self.stats_db_path,
            timestamp=int(event.get("timestamp") or time.time()),
            counts=event.get("tally") or {},
            character_id=event.get("character_id"),
            dummy_character_id=event.get("dummy_character_id"),
            start_side=event.get("start_side"),
            source=event.get("source") or "free_play",
        )
        if not ok:
            log.error("failed recording tally: %s", err)

    def _handle_hit_zone_delta(self, event: dict, db: dict) -> None:

        character_id = event["character_id"]
        dummy_id = event.get("dummy_character_id") or self.UNKNOWN_BUCKET
        side = event.get("start_side") or self.UNKNOWN_BUCKET
        delta = event.get("delta") or {}

        root = "hit_zones_dealt" if event.get("role") == "dealt" else "hit_zones"
        hit_zones = db.setdefault(root, {})
        if root == "hit_zones":
            hit_zones = self._migrate_hit_zones(hit_zones)
        zones = (
            hit_zones.setdefault(character_id, {})
            .setdefault(dummy_id, {})
            .setdefault(side, {"high": 0, "mid": 0, "low": 0})
        )
        for key in ("high", "mid", "low"):
            zones[key] = zones.get(key, 0) + int(delta.get(key, 0))
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after hit_zone_delta: %s", err)
        else:
            log.info("hit_zone_delta(%s) character=%s vs=%s side=%s delta=%s",
                     "dealt" if root == "hit_zones_dealt" else "taken",
                     character_id, dummy_id, side, delta)

    SCRIMMAGE_HISTORY_LIMIT = 20

    def _handle_scrimmage_round(self, event: dict, db: dict) -> None:

        session_id = event.get("session_id") or "scrimmage"
        character_id = event.get("character_id") or "unknown"
        tally = event.get("tally") or {}
        won = event.get("won")

        analysis = scrimmage.analyse_round(
            tally, db.get("drills") or [], character_id, won)
        rounds = self._scrimmage_rounds.setdefault(session_id, [])
        rounds.append({"tally": tally, "won": bool(won),
                       "score": analysis["score"],

                       "exchanges": analysis["exchanges"],
                       "worst": analysis["worst"],
                       "worst_count": analysis["worst_count"]})
        analysis["round"] = len(rounds)
        analysis["rounds_total"] = scrimmage.ROUNDS_PER_SET
        analysis["session_id"] = session_id

        tmp = (paths.last_scrimmage_round(self.data_dir)).with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=4)
        paths.atomic_replace(tmp, paths.last_scrimmage_round(self.data_dir))
        log.info("scrimmage round %d/%d for %s: won=%s score=%s worst=%s",
                 len(rounds), scrimmage.ROUNDS_PER_SET, character_id,
                 won, analysis["score"], analysis["worst"])

    def _handle_scrimmage_concluded(self, event: dict, db: dict) -> None:

        character_id = event.get("character_id") or "unknown"
        session_id = event.get("session_id") or "scrimmage"

        rounds = self._scrimmage_rounds.pop(session_id, [])
        if rounds:
            summary = scrimmage.summarise_set(
                rounds, db.get("drills") or [], character_id)
            tally = summary["tally"]
            results = summary["results"]
        else:
            summary = None
            tally = event.get("tally") or {}
            results = event.get("match_results") or event.get("round_results") or []

        dummy_id = event.get("dummy_character_id") or "unknown"
        state = (db.setdefault("scrimmage", {})
                   .setdefault(character_id, {})
                   .setdefault(dummy_id,
                               {"difficulty": scrimmage.MIN_DIFFICULTY, "sessions": []}))
        before = int(state.get("difficulty") or scrimmage.MIN_DIFFICULTY)
        before_handicap = int(state.get("handicap") or 0)

        outcomes = list(results)[:scrimmage.ROUNDS_PER_SET]
        wins = sum(1 for r in outcomes if r)
        if len(outcomes) < scrimmage.ROUNDS_PER_SET:
            after, after_handicap, outcome = before, before_handicap, "incomplete"
        elif wins == scrimmage.ROUNDS_PER_SET:
            after, after_handicap = difficulty.harder(before, before_handicap)
            outcome = "advanced"
        elif wins == 0:
            after, after_handicap = difficulty.easier(before, before_handicap)
            outcome = "dropped"
        else:
            after, after_handicap, outcome = before, before_handicap, "held"
        if (after, after_handicap) == (before, before_handicap) and outcome != "incomplete":
            outcome = "held"

        scored = scrimmage.score_tally(
            tally,
            giver_keys=event.get("giver_keys"),
            receiver_keys=event.get("receiver_keys"),
        )
        drills = db.get("drills") or []
        assigned = scrimmage.recommend_drills(tally, drills, character_id=character_id)
        unmet = scrimmage.unaddressed_weaknesses(tally, drills, character_id=character_id)

        state["difficulty"] = after
        state["handicap"] = after_handicap
        state["sessions"].append({
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "match_results": list(results),
            "round_results": list(results),
            "per_round_scores": (summary or {}).get("per_round_scores"),
            "difficulty_before": before,
            "difficulty_after": after,
            "handicap_before": before_handicap,
            "handicap_after": after_handicap,
            "outcome": outcome,
            "score": scored["score"],
            "buckets": scored["buckets"],
            "exchanges": scored["exchanges"],

            "giver_events": scored["giver_events"],
            "receiver_events": scored["receiver_events"],
            "weaknesses": [{"weakness": k, "count": n}
                           for k, n in scrimmage.rank_weaknesses(tally)],

            "rounds": [{"round": i + 1, "won": r.get("won"),
                        "score": r.get("score"),
                        "exchanges": r.get("exchanges"),
                        "worst": r.get("worst"),
                        "worst_count": r.get("worst_count"),
                        "weaknesses": [{"weakness": k, "count": n}
                                       for k, n in scrimmage.rank_weaknesses(
                                           r.get("tally") or {})][:5]}
                       for i, r in enumerate(rounds)],
            "recommendations": assigned,
            "unaddressed": [{"weakness": k, "count": n} for k, n in unmet],
        })

        state["sessions"] = state["sessions"][-self.SCRIMMAGE_HISTORY_LIMIT:]

        payload = {
            "session_id": session_id,
            "character_id": character_id,
            "dummy_character_id": dummy_id,
            "rounds": len(results),
            "won": sum(1 for r in results if r),
            "score": scored["score"],
            "difficulty_before": before,
            "difficulty_after": after,
            "handicap_before": before_handicap,
            "handicap_after": after_handicap,
            "outcome": outcome,
            "recommendations": assigned,
            "lines": scrimmage.set_lines(
                summary or {"rounds": len(results),
                            "won": sum(1 for r in results if r),
                            "score": scored["score"],
                            "per_round_scores": None,
                            "weaknesses": scrimmage.rank_weaknesses(tally),
                            "recommendations": assigned,
                            "unaddressed": [(k, n) for k, n in unmet]},
                before, after, before_handicap, after_handicap, outcome),
        }
        tmp = (paths.last_scrimmage_set(self.data_dir)).with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        paths.atomic_replace(tmp, paths.last_scrimmage_set(self.data_dir))

        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after scrimmage_concluded: %s", err)
        else:
            log.info("scrimmage %s vs %s score=%s %s %d->%d assigned=%d",
                     character_id, dummy_id, scored["score"], outcome,
                     before, after, len(assigned))

    def _handle_create_drill(self, event: dict, db: dict) -> None:

        drill = dict(event.get("drill") or {})
        base_id = drill.get("id") or "captured_drill"
        existing_ids = {d.get("id") for d in (db.get("drills") or [])}
        existing_ids.update(db.get("deleted_drill_ids") or [])
        final_id, n = base_id, 2
        while final_id in existing_ids:
            final_id = f"{base_id}_{n}"
            n += 1
        drill["id"] = final_id
        drill.setdefault("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        db.setdefault("drills", []).append(drill)
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after create_drill_request: %s", err)
        else:
            log.info("created drill=%s", final_id)

    def _handle_reset_drill_schedule(self, event: dict, db: dict) -> None:

        drill_id = event["drill_id"]
        drill = self._find_drill(db, drill_id)
        if drill is None:
            log.warning("reset_drill_schedule_request for unknown drill_id=%s, "
                        "ignoring", drill_id)
            return

        characters = list((drill.get("character_progress") or {}).keys())
        if not characters:
            characters = [drill.get("character_id")]
        for character in characters:
            prior = progress.state_for(drill, character)
            state = dict(scheduler.STARTING_STATE)
            state["next_review"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            state["total_sessions"] = prior.get("total_sessions") or 0
            progress.apply_state(drill, character, state)

        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after "
                      "reset_drill_schedule_request: %s", err)
            return
        log.info("reset scheduling for drill=%s (characters: %s) -- due now",
                 drill_id, ", ".join(str(c) for c in characters) or "none")

    def _handle_reset_deck(self, event: dict, db: dict) -> dict:

        example, ex_err = database.load(self.example_db_path)
        if example is None:
            log.error("reset_deck_request failed loading example db: %s", ex_err)
            return db

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        deleted_ids = {id_ for id_ in (db.get("deleted_drill_ids") or [])}

        USER_OWNED_FIELDS = ("trains", "trains_for",
                             "character_id", "dummy_character_id")
        existing_by_id = {d.get("id"): d for d in (db.get("drills") or [])}

        merged_drills = []
        seen = set()
        for drill in example.get("drills") or []:
            if drill["id"] not in deleted_ids:
                seen.add(drill["id"])
                drill["next_review"] = now_iso
                drill["total_sessions"] = 0
                previous = existing_by_id.get(drill["id"])
                if previous is not None:
                    for field in USER_OWNED_FIELDS:
                        if field in previous:
                            drill[field] = previous[field]
                        else:
                            drill.pop(field, None)
                merged_drills.append(drill)
        for drill in db.get("drills") or []:
            if drill["id"] not in seen and drill["id"] not in deleted_ids:
                drill["next_review"] = now_iso
                drill["total_sessions"] = 0
                drill["streak"] = 0
                merged_drills.append(drill)

        example["drills"] = merged_drills
        example["deleted_drill_ids"] = db.get("deleted_drill_ids")

        example["hit_zones"] = db.get("hit_zones")
        ok, err = database.save(self.db_path, example)
        if not ok:
            log.error("failed saving database after reset_deck_request: %s", err)
        else:
            log.info("deck reset (%d drills)", len(merged_drills))
        return example

    def _process_outbox(self, db: dict) -> dict:

        dirs = [self.outbox_dir]
        if self.legacy_outbox_dir is not None and self.legacy_outbox_dir.exists():
            dirs.append(self.legacy_outbox_dir)
        if not any(d.exists() for d in dirs):
            return db

        for path in sorted((f for d in dirs for f in d.glob("*.json")),
                           key=lambda f: f.name):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    event = json.load(f)
                kind = event.get("event")
                if kind == "rep_result":
                    self._handle_rep_result(event, db)
                elif kind == "session_concluded":
                    self._handle_session_concluded(event, db)
                elif kind == "create_drill_request":
                    self._handle_create_drill(event, db)
                elif kind == "update_drill_request":
                    self._handle_update_drill(event, db)
                elif kind == "delete_drill_request":
                    self._handle_delete_drill(event, db)
                elif kind == "merge_duplicates_request":
                    self._handle_merge_duplicates(event, db)
                elif kind == "set_drill_selection_request":
                    self._handle_set_drill_selection(event, db)
                elif kind == "set_drill_selection_bulk_request":
                    self._handle_set_drill_selection_bulk(event, db)
                elif kind == "set_drill_favorite_request":
                    self._handle_set_drill_favorite(event, db)
                elif kind == "open_dashboard_request":
                    self._handle_open_dashboard()
                elif kind == "character_data_update":
                    self._handle_character_data_update(event)
                elif kind == "move_timing_observed":

                    self._merge_observed_totals(
                        event.get("character_id"), event.get("observed_totals") or [])
                elif kind == "reset_deck_request":
                    db = self._handle_reset_deck(event, db)
                elif kind == "reset_drill_schedule_request":
                    self._handle_reset_drill_schedule(event, db)
                elif kind == "hit_zone_delta":
                    self._handle_hit_zone_delta(event, db)
                elif kind == "tally_recorded":
                    self._handle_tally_recorded(event)
                elif kind == "scrimmage_round":
                    self._handle_scrimmage_round(event, db)
                elif kind == "scrimmage_concluded":
                    self._handle_scrimmage_concluded(event, db)
                else:
                    log.warning("unknown outbox event kind=%r in %s, discarding", kind, path.name)
            except (OSError, json.JSONDecodeError, KeyError) as e:
                log.error("failed processing outbox file %s: %s -- discarding", path.name, e)
            finally:
                try:
                    path.unlink()
                except OSError:
                    pass
        return db

    def run_forever(self) -> None:

        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        log.info("beast_drills running against %s", self.data_dir)
        try:
            while True:
                try:
                    db = self._load_db()
                    db = self._process_outbox(db)
                    self._retime_stored_patterns(db)
                    self._write_inbox(db)
                except Exception:
                    log.exception("poll cycle failed -- continuing")
                time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            log.info("beast_drills stopping (interrupted)")
            raise
        finally:
            log.info("beast_drills loop exited")

def main() -> None:

    cfg = settings.load(DEFAULT_DATA_DIR)
    install_dir, data_default = settings.resolve_roots(DEFAULT_DATA_DIR)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=data_default,
        help="where YOUR drills and history live (default from "
             "beast_drills.ini, else Documents/Beast Drills)",
    )
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=install_dir,
        help="where the mod's own shipped data lives",
    )
    parser.add_argument("--verbose", action="store_true",
                        default=cfg[("dashboard", "verbose")],
                        help="more detail in the log (also settable in beast_drills.ini)")
    args = parser.parse_args()

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:

        paths.ensure(args.data_dir)
        log_path = paths.service_log(args.data_dir)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_path, maxBytes=2_000_000, backupCount=2, encoding="utf-8"
            )
        )
    except OSError:
        pass

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )

    try:
        registered = mods.sync(args.install_dir)
        if registered:
            log.info("mod settings resolved for %s", ", ".join(sorted(registered)))
    except Exception:

        log.exception("could not sync mod settings")

    Service(args.data_dir, args.install_dir).run_forever()

if __name__ == "__main__":
    main()
