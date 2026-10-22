"""The main service loop: watches the outbox the plugin and the dashboard
write to, grades reps and finalizes sessions, owns shared_database.json,
and keeps the inbox file (next due drill + a heartbeat) fresh for the
plugin to read.

Started with the game: the plugin runs the shipped launcher the first time
it finds no service (csharp/src/AutoStart.cs), and Start Beast Drills.bat
does the same by hand. See docs/SERVICE.md.

File protocol (paths under the PLAYER folder, Documents/Beast Drills by
default -- paths.py owns the layout):
  outbox/*.json   -- the plugin (C#, csharp/src/Outbox.cs) and the
                     dashboard (outbox_writer.py) write one file per
                     event, never overwritten -- a durable queue, nothing
                     lost if this service is slow or down. This service
                     deletes each file once its change is on disk (see
                     _process_outbox).
  runtime/inbox.json -- this service writes the current due drill, a
                     heartbeat timestamp and the dashboard address; the
                     plugin reads it, and refuses to start a session when
                     the heartbeat is stale (Outbox.cs).
  shared_database.json -- written only by this service (drill
                     definitions + CURRENT scheduling state). The plugin
                     READS it for its drill list, and never writes it.
  stats.db  -- owned entirely by this service (2026-08-15). The
                     append-only per-session review log -- one row per
                     concluded session -- that used to live as each
                     drill's own `history` array inside
                     shared_database.json, moved out to SQLite so the
                     dashboard's Stats panels can do real day/hour/
                     grade-bucketed aggregation. See reviews_db.py.
"""

import argparse
import contextlib
import copy
import json
import logging
import logging.handlers
import re
import sqlite3
import time
from pathlib import Path

from . import attempts, belts, gauges, ids, mods, paths, settings

from . import (
    combo_check,
    combo_plan,
    combo_save,
    criteria,
    session_breakdown,
    session_progress,
    dashboard_data,
    database,
    deck,
    duplicates,
    matches,
    game_speed,
    grader,
    response_check,
    attack_string,
    live_status,
    move_catalog,
    move_timing,
    progress,
    wongscript,
    response_window,
    reviews_db,
    scheduler,
    scoring,
    session_result,
)

log = logging.getLogger("beast_drills")

POLL_SECONDS = 0.5

PENDING_HISTORY_MOVES = "pending_history_moves"

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

DEFAULT_INSTALL_DIR = _default_install()

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

        self.example_db_path = paths.example_database(self.install_dir)

        self.stats_db_path = paths.stats_db(data_dir)
        cfg = settings.load(DEFAULT_INSTALL_DIR)

        self.dashboard_url = settings.dashboard_url(cfg)

        self.default_response_window = cfg[("practice", "response_window")]
        self.allow_slow_start = cfg[("practice", "allow_slow_start")]
        self.default_reps = cfg[("practice", "reps")]

        self.match_limit_bytes = max(0, cfg[("matches", "max_size_mb")]) * 1024 * 1024

        self._sessions_in_progress: dict[str, list[int]] = {}

        self._session_range_points: dict[str, list] = {}

        self._session_combo_hits: dict[str, list] = {}
        self._session_rep_avoided: dict[str, list] = {}
        self._session_reps: dict[str, list] = {}

        self._progress_path = paths.session_progress(self.data_dir)
        self._restore_progress()

        self._in_batch = False
        self._batch_dirty = False
        self._batch_changes = 0
        self._batch_pending = []

        self._db_cache = None
        self._db_cache_key = None

    def _load_db(self) -> dict:

        try:
            stat = self.db_path.stat()
            key = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            key = None
        if key is not None and key == self._db_cache_key and self._db_cache is not None:
            return self._db_cache
        data, err = database.load(self.db_path)
        if data is not None:
            self._db_cache, self._db_cache_key = data, key
            return data

        if self.db_path.exists():

            raise RuntimeError(database.unreadable_message(
                self.db_path, paths.backups_dir(self.data_dir), err))
        example, ex_err = database.load(self.example_db_path)
        if example is None:
            raise RuntimeError(f"no database and no example to bootstrap from: {ex_err}")

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for drill in example.get("drills") or []:
            _fresh_schedule(drill, now)
        ok, save_err = database.save(self.db_path, example)
        if not ok:
            raise RuntimeError(f"bootstrap save failed: {save_err}")
        log.info("Seeded shared_database.json from the example file (first run).")
        return example

    def _forget_db(self) -> None:

        self._db_cache = self._db_cache_key = None

    def _changed(self, db: dict, what: str) -> bool:

        if self._in_batch:
            self._batch_dirty = True
            self._batch_changes += 1
            return True
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("failed saving database after %s: %s", what, err)
        return ok

    def _save_now(self, db: dict) -> tuple:

        ok, err = database.save(self.db_path, db)
        if ok and self._in_batch:
            self._batch_dirty = False
            self._delete_events(self._batch_pending)
            self._batch_pending = []
        return ok, err

    @staticmethod
    def _delete_events(event_paths) -> None:
        for path in event_paths:
            with contextlib.suppress(OSError):
                path.unlink()

    def _refuse_belt_drills(self, kind: str, db: dict, drill_ids) -> bool:
        if paths.is_dev_install():
            return False
        locked = [i for i in drill_ids
                  if belts.is_belt_drill(self._find_drill(db, i) or {})]
        if locked:
            log.warning("%s refused: %s %s a belt drill, read-only outside a dev install",
                        kind, ", ".join(locked), "is" if len(locked) == 1 else "are")
        return bool(locked)

    def _add_shipped_drills(self) -> int:

        if paths.is_dev_install():
            return 0
        example, _err = database.load(self.example_db_path)
        if not example:
            return 0
        db = self._load_db()
        have_ids = {d.get("id") for d in db.get("drills") or []}
        gone = set(db.get("deleted_drill_ids") or [])

        shipped_ids = {d.get("id") for d in example.get("drills") or []}
        have_names = {duplicates.name_key(d) for d in db.get("drills") or []
                      if d.get("id") not in shipped_ids}
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        added = []
        for shipped in example.get("drills") or []:
            drill_id = shipped.get("id")
            if (not drill_id or drill_id in have_ids or drill_id in gone
                    or duplicates.name_key(shipped) in have_names):
                continue
            drill = dict(shipped)
            drill.pop("selected", None)
            _fresh_schedule(drill, now)
            added.append(drill)
            have_ids.add(drill_id)
        if not added:
            return 0

        nothing_selected = not any(d.get("selected") for d in db.get("drills") or [])
        db.setdefault("drills", []).extend(added)
        if nothing_selected:
            starters = {d.get("id") for d in example.get("drills") or [] if d.get("selected")}
            picked = [d for d in db["drills"] if d.get("id") in starters]
            for drill in picked:
                drill["selected"] = True
            if picked:
                log.info("nothing was selected: selected the %d starter drill(s)", len(picked))
        ok, err = database.save(self.db_path, db)
        if not ok:
            log.error("could not add %d shipped drill(s): %s", len(added), err)
            return 0
        log.info("added %d drill(s) that shipped since this deck was made", len(added))
        return len(added)

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
            self._forget_db()
            log.error("failed saving retimed patterns: %s", err)
        else:
            log.info("retimed recorded tapes for dummy=%s", dummy)

    @staticmethod
    def _with_reason(drill, db, played_as, dummy):

        if drill is not None:
            why = scoring.reason_for(db, drill.get("id"), played_as, dummy)
            if why:
                drill["match_reason"] = why
        return drill

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

        recommended = scoring.latest_recommendations(db, played_as, dummy)
        due = deck.get_due_drills(db, now_iso, played_as, dummy)
        next_drill = deck.select_next_drill(due, recommended)

        next_favorite = deck.select_next_drill(
            [d for d in due if d.get("favorite")], recommended)
        payload = {
            "heartbeat": time.time(),
            "due_drill": self._with_reason(self._prepare_due(next_drill), db, played_as, dummy),
            "due_favorite": self._with_reason(self._prepare_due(next_favorite), db, played_as, dummy),

            "dashboard_url": self.dashboard_url,

            "dashboard_installed": paths.web_dashboard_installed(),
        }
        tmp = self.inbox_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        paths.atomic_replace(tmp, self.inbox_path)

    def _record_rep(self, session_id: str, grade: int, event: dict,
                    against=None, setup=None, outcome=None) -> int:

        if event.get("practice"):
            return 0
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

        graded = self._grade_rep(event, drill, session_id, drill_id)
        if graded is None:
            return
        grade, verdict = graded

        total = self._record_rep(session_id, grade, event,
                                 drill.get("against_criteria"),
                                 drill.get("expected_setup"),
                                 outcome=verdict)
        log.info(
            "graded rep for session=%s drill=%s -> %s (total this session: %d)",
            session_id, drill_id, grade, total,
        )
        self._write_last_rep_result(session_id, drill_id, grade, event)

    def _grade_rep(self, event: dict, drill: dict, session_id: str, drill_id: str):

        if drill.get("drill_type") == "combo":
            return self._grade_combo_count(event, drill)
        snapshot = event.get("snapshot", {})

        if event.get("expected_combo"):
            return self._grade_attack_string(event, drill, snapshot, session_id, drill_id)
        return self._grade_by_criteria(event, drill, snapshot, drill_id)

    @staticmethod
    def _grade_combo_count(event: dict, drill: dict) -> tuple:
        grade = combo_check.grade_combo_attempt(
            event["final_combo_cnt"], drill.get("target_combo_hits", 0)
        )

        return grade, ("hit" if grade != grader.AGAIN else "miss")

    @staticmethod
    def _grade_by_criteria(event: dict, drill: dict, snapshot, drill_id: str) -> tuple:

        expected_response = event.get("expected_response")
        if expected_response is None and drill.get("against_criteria"):

            try:
                ok = criteria.rep_avoided(snapshot, drill["against_criteria"])
            except ValueError as exc:
                log.warning("bad against_criteria on drill_id=%s (%s) -- grading AGAIN",
                            drill_id, exc)
                ok = False
            return (grader.GOOD if ok else grader.AGAIN), ("hit" if ok else "miss")
        if expected_response is None:
            return grader.AGAIN, None
        grade, reason = response_check.grade_response(
            expected_response, snapshot, drill.get("expected_setup"))
        if grade is None:
            log.warning(
                "unsupported expected_response=%r for drill_id=%s (%s) -- grading AGAIN",
                expected_response, drill_id, reason,
            )
            grade = grader.AGAIN
        return grade, None

    def _grade_attack_string(self, event: dict, drill: dict, snapshot,
                             session_id: str, drill_id: str):

        expected_combo = event.get("expected_combo")
        spec_errors = []
        spec = attack_string.parse_attack_string(expected_combo, spec_errors)
        if spec is None:
            log.warning(
                "unparseable expected_combo=%r for drill_id=%s (%s) -- grading AGAIN",
                expected_combo, drill_id, spec_errors,
            )
            return grader.AGAIN, None
        recorded, combo_mode = self._grade_by_move_ids(
            event, drill, snapshot, expected_combo, session_id, drill_id)
        if recorded:
            return None
        ok, why, landed = self._check_attack_inputs(spec, snapshot, combo_mode)

        log.info(
            "combo %s for drill_id=%s: landed [%s] vs spec %r%s",
            "HIT" if ok else "miss", drill_id, self._describe_landed(landed),
            expected_combo, "" if ok else f" -- {why}",
        )
        return (grader.GOOD if ok else grader.AGAIN), ("hit" if ok else "miss")

    def _grade_by_move_ids(self, event: dict, drill: dict, snapshot, expected_combo,
                           session_id: str, drill_id: str) -> tuple:

        move_ids = snapshot.get("p1_move_ids")

        char = (drill.get("character_id")
                or live_status.player_character(self.live_status_path))
        spec_sets, cat_err = (None, None)
        combo_mode, combo_text = attack_string.split_mode(expected_combo)
        if move_ids is not None and char:

            spec_sets, cat_err = move_catalog.resolve_all(
                char, [attack_string.strip_movement_prefix(t)
                       for t in combo_text.split(",")
                       if t.strip() and not attack_string.is_movement(t)],
                self.data_dir,
            )
        if not spec_sets:
            if cat_err:
                log.warning("combo catalog: %s (falling back)", cat_err)
            return False, combo_mode

        moves = move_catalog.filter_to_moves(char, move_ids, self.data_dir)
        ok, why = attack_string.check_move_ids(spec_sets, moves, combo_mode)
        log.info("combo %s (move-id, %s) drill=%s moves=%s raw=%s%s",
                 "HIT" if ok else "miss", combo_mode, drill_id, moves,
                 (move_ids or [])[:12], "" if ok else f" -- {why}")

        grade = grader.GOOD if ok else grader.AGAIN
        total = self._record_rep(
            session_id, grade, event, drill.get("against_criteria"),
            drill.get("expected_setup"), outcome="hit" if ok else "miss")
        log.info("graded rep for session=%s drill=%s -> %s (total this session: %d)",
                 session_id, drill_id, grade, total)
        self._write_last_rep_result(session_id, drill_id, grade, event)
        return True, combo_mode

    @staticmethod
    def _check_attack_inputs(spec, snapshot, combo_mode) -> tuple:

        inputs = snapshot.get("p1_attack_inputs")
        if inputs is not None:

            ok, why = attack_string.check_attack_inputs(
                spec, inputs, snapshot.get("p1_hit_count") or 0,
                combo_mode,
            )
            return ok, why, inputs
        landed = snapshot.get("p1_landed_attacks") or []
        ok, why = attack_string.check_attack_string(spec, landed)
        return ok, why, landed

    @staticmethod
    def _describe_landed(landed) -> str:
        return ", ".join(
            wongscript._bits_to_code(
                e.get("bits", 0) if isinstance(e, dict) else e
            )
            + ("" if not (isinstance(e, dict) and e.get("comboed_from_previous")) else "*")
            for e in landed
        ) or "(nothing)"

    def _write_last_rep_result(self, session_id: str, drill_id: str, grade,
                               event: dict | None = None) -> None:

        result_payload = {"session_id": session_id, "drill_id": drill_id, "grade": grade}

        if event is not None:
            if event.get("attempt") is not None:
                result_payload["attempt"] = event["attempt"]
            if event.get("practice"):
                result_payload["practice"] = True
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

        ok, err = self._save_now(db)
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
        if self._refuse_belt_drills("update_drill_request", db, [drill_id]):
            return
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

        if belts.FIELD in patch:
            value = patch[belts.FIELD]
            if value and not paths.is_dev_install():
                log.warning("update_drill_request for %s tried to make it a belt drill "
                            "outside a dev install -- ignored", drill_id)
            elif belts.is_belt_drill({belts.FIELD: value}):
                drill[belts.FIELD] = value
            else:
                drill.pop(belts.FIELD, None)

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
        if self._changed(db, "update_drill_request"):
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
        if self._changed(db, "set_drill_selection_request"):
            log.info("set selected=%s for drill=%s", drill["selected"], drill_id)

    def _handle_character_data_update(self, event: dict) -> None:

        character_id = event.get("character_id")
        moves = event.get("moves")
        if not character_id or not isinstance(moves, list):
            log.warning("character_data_update with no character_id/moves, ignoring")
            return

        if not isinstance(character_id, str) or not re.fullmatch(r"[a-z0-9_]{1,32}", character_id):
            log.warning("character_data_update with an invalid character_id %r -- discarded",
                        character_id)
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

        if not isinstance(character_id, str) or not re.fullmatch(r"[a-z0-9_]{1,32}", character_id):
            log.warning("observed move timings with an invalid character_id %r -- discarded",
                        character_id)
            return

        path = paths.observed_timings(self.data_dir, character_id)
        legacy = self.install_dir / "frame_data_connected" / f"{character_id}.json"
        existing: dict = {}
        try:
            source = path if path.exists() else legacy
            if source.exists():
                with open(source, encoding="utf-8") as f:
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
            move_timing.forget(character_id)
            log.info("observed move timings: %s -- %d updated, %d known",
                     character_id, added, len(existing))
        except OSError as err:
            log.error("failed writing %s: %s", path, err)

    def _handle_open_dashboard(self) -> None:

        if not paths.web_dashboard_installed():

            log.info("open_dashboard_request: the web dashboard is not installed")
            return
        import webbrowser

        url = self.dashboard_url
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
        if self._changed(db, "set_drill_favorite_request"):
            log.info("set favorite=%s for drill=%s", drill["favorite"], drill_id)

    def _handle_set_belt_drills(self, event: dict, db: dict) -> None:

        if not paths.is_dev_install():
            log.warning("set_belt_drills_request refused outside a dev install")
            return
        labels = event.get("labels") or {}
        by_id = {d.get("id"): d for d in db.get("drills") or []}
        set_n = cleared = skipped = 0
        for drill_id, value in labels.items():
            drill = by_id.get(drill_id)
            if drill is None:
                skipped += 1
            elif value is None:
                cleared += drill.pop(belts.FIELD, None) is not None
            elif belts.is_belt_drill({belts.FIELD: value}):
                drill[belts.FIELD] = value
                set_n += 1
            else:
                skipped += 1
        if self._changed(db, "set_belt_drills_request"):
            log.info("belt drills: %d labelled, %d cleared, %d skipped", set_n, cleared, skipped)

    def _handle_set_drill_selection_bulk(self, event: dict, db: dict) -> None:

        drill_ids = set(event.get("drill_ids") or [])
        selected = bool(event.get("selected"))
        changed = 0
        for drill in db.get("drills") or []:
            if drill.get("id") in drill_ids:
                drill["selected"] = selected
                changed += 1
        if self._changed(db, "set_drill_selection_bulk_request"):
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

        if self._refuse_belt_drills("merge_duplicates_request", db, [keep_id] + merge_ids):
            return

        members = [keep] + [by_id[i] for i in merge_ids]
        plan = duplicates.merge_plan(
            members, reviews_db.last_reviewed(self.stats_db_path))
        if plan is None:

            plan = {"merged": {"total_sessions": sum(
                d.get("total_sessions") or 0 for d in members)}}

        merged = copy.deepcopy(db)
        merged_keep = next(d for d in merged["drills"] if d.get("id") == keep_id)
        merged_keep.update(plan["merged"])
        merged["drills"] = [d for d in merged["drills"] if d.get("id") not in set(merge_ids)]
        deleted_ids = merged.setdefault("deleted_drill_ids", [])
        for drill_id in merge_ids:
            if drill_id not in deleted_ids:
                deleted_ids.append(drill_id)

        merged.setdefault(PENDING_HISTORY_MOVES, []).append(
            {"from_ids": list(merge_ids), "to_id": keep_id})

        ok, err = self._save_now(merged)
        if not ok:
            log.error("failed saving database after merge_duplicates_request: %s -- "
                      "nothing was merged and no review history moved", err)
            return
        db.clear()
        db.update(merged)
        log.info("merged %s into %s (sessions now %s)", merge_ids, keep_id,
                 merged_keep.get("total_sessions"))

        error = self._retry_history_moves(db)
        if error is not None:

            log.error("the review history of %s could not be moved onto %s yet (%s) -- "
                      "it is queued and will be moved automatically", merge_ids,
                      keep_id, error)

    def _retry_history_moves(self, db: dict) -> str | None:

        queue = db.get(PENDING_HISTORY_MOVES)
        if not queue:
            return None
        remaining, error = [], None
        for move in queue:
            if error is not None:
                remaining.append(move)
                continue
            if not (isinstance(move, dict) and isinstance(move.get("from_ids"), list)
                    and isinstance(move.get("to_id"), str)):
                log.warning("dropping a malformed queued history move: %r", move)
                continue
            try:
                moved = reviews_db.rekey_drills(self.stats_db_path, move["from_ids"],
                                                move["to_id"])
            except sqlite3.Error as exc:
                error = str(exc)
                remaining.append(move)
                continue
            log.info("moved the review history of %s onto %s (%d session(s))",
                     move["from_ids"], move["to_id"], sum(moved.values()))
        if len(remaining) != len(queue):
            if remaining:
                db[PENDING_HISTORY_MOVES] = remaining
            else:
                db.pop(PENDING_HISTORY_MOVES, None)
            self._changed(db, "a queued history move")
        if error is not None:
            log.debug("queued history move still waiting: %s", error)
        return error

    def _handle_delete_drill(self, event: dict, db: dict) -> None:

        drill_id = event["drill_id"]
        if self._refuse_belt_drills("delete_drill_request", db, [drill_id]):
            return
        drills = db.get("drills") or []
        found = any(d.get("id") == drill_id for d in drills)
        if not found:
            log.warning("delete_drill_request for unknown drill_id=%s, ignoring", drill_id)
            return
        db["drills"] = [d for d in drills if d.get("id") != drill_id]
        deleted_ids = db.setdefault("deleted_drill_ids", [])
        if drill_id not in deleted_ids:
            deleted_ids.append(drill_id)
        if self._changed(db, "delete_drill_request"):
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
        if self._changed(db, "hit_zone_delta"):
            log.info("hit_zone_delta(%s) character=%s vs=%s side=%s delta=%s",
                     "dealt" if root == "hit_zones_dealt" else "taken",
                     character_id, dummy_id, side, delta)

    def _handle_match_round(self, event: dict, db: dict) -> None:

        if not event.get("match_id"):
            log.warning("match_round without a match_id, discarding")
            return
        graded = matches.grade_round(event, db.get("drills") or [])
        ok, err = reviews_db.record_match_round(
            self.stats_db_path, int(event.get("timestamp") or time.time()), graded)
        if not ok:
            log.error("failed recording match round: %s", err)
            return
        log.info("match %s round %d (%s): you=%s side=%s by=%s self=%s members=%s "
                 "won=%s score=%s worst=%s%s",
                 graded["match_id"], graded["round"], matches.mode_name(graded["mode"]),
                 graded["character_id"], graded["player_side"], graded["side_by"],
                 event.get("self_member"), event.get("members"),
                 graded["won"], graded["score"], graded["worst"],
                 " (right side, mirrored)" if graded["mirrored"] else "")

    def _handle_favorite_match(self, event: dict) -> None:

        ok, err = reviews_db.set_match_favorite(
            self.stats_db_path, str(event.get("match_id") or ""),
            bool(event.get("favorite", True)))
        if not ok:
            log.warning("could not change match favourite: %s", err)

    def _prune_matches(self) -> None:

        try:
            removed = reviews_db.prune_matches(self.stats_db_path, self.match_limit_bytes)
        except Exception as e:
            log.error("could not trim old matches: %s", e)
            return
        if removed:
            log.info("match log over %d MB: removed the %d oldest match(es)",
                     self.match_limit_bytes // (1024 * 1024), removed)

    def _handle_match_end(self, event: dict, db: dict) -> None:

        match_id = event.get("match_id")
        if not match_id:
            log.warning("match_end without a match_id, discarding")
            return
        rounds = reviews_db.match_rounds(self.stats_db_path, match_id)
        graded = matches.grade_match(event, rounds, db.get("drills") or [])
        ok, err = reviews_db.record_match(
            self.stats_db_path, int(event.get("timestamp") or time.time()), graded, rounds)
        if not ok:
            log.error("failed recording match: %s", err)
            return
        self._prune_matches()

        exchanges = sum(int(r.get("exchanges") or 0) for r in rounds)
        if graded["player_side"] is not None and graded["character_id"] and exchanges > 0:
            slot = (db.setdefault("matches", {})
                      .setdefault(graded["character_id"], {})
                      .setdefault(graded["opponent_id"] or "unknown", {}))
            slot["latest"] = {
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "match_id": match_id,
                "mode": graded["mode"],
                "won": graded["won"],
                "score": graded["score"],
                "recommendations": graded["recommendations"],
            }

            ok, err = self._save_now(db)
            if not ok:
                log.error("failed saving match feedback: %s", err)
        log.info("match %s over (%s, %s): %d-%d won=%s score=%s, %d recommended",
                 match_id, matches.mode_name(graded["mode"]), graded["how"],
                 graded["wins"], graded["losses"], graded["won"], graded["score"],
                 len(graded["recommendations"]))

    def _handle_save_combo(self, event: dict, db: dict) -> None:

        drill, why = combo_save.drill_from_combo(
            event.get("character_id"), event.get("move_ids"), event.get("hits"), self.data_dir)
        if drill is None:
            log.warning("save_combo_request not saved: %s", why)
        else:
            self._handle_create_drill({"drill": drill}, db)

        result = {"request_id": event.get("request_id"), "ok": drill is not None,
                  "name": drill["name"] if drill else None, "reason": why}
        path = paths.save_combo_result(self.data_dir)
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(result), encoding="utf-8")
            paths.atomic_replace(tmp, path)
        except OSError as exc:
            log.warning("could not write the save-combo result (%s)", exc)

    def _handle_create_drill(self, event: dict, db: dict) -> None:

        drill = dict(event.get("drill") or {})

        if drill.get(belts.FIELD) and not paths.is_dev_install():
            log.info("create_drill_request: belt-drill dropped outside a dev install")
            drill.pop(belts.FIELD, None)
        elif not belts.is_belt_drill(drill):
            drill.pop(belts.FIELD, None)
        base_id = drill.get("id") or "captured_drill"
        if not ids.valid_drill_id(base_id):

            log.warning("create_drill_request with an invalid id %r -- discarded", base_id)
            return
        existing_ids = {d.get("id") for d in (db.get("drills") or [])}
        existing_ids.update(db.get("deleted_drill_ids") or [])
        final_id, n = base_id, 2
        while final_id in existing_ids:
            final_id = f"{base_id}_{n}"
            n += 1
        drill["id"] = final_id
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        drill.setdefault("created_at", now)

        for key, value in scheduler.STARTING_STATE.items():
            drill.setdefault(key, value)
        drill.setdefault("next_review", now)
        db.setdefault("drills", []).append(drill)
        if self._changed(db, "create_drill_request"):
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

        if not self._changed(db, "reset_drill_schedule_request"):
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

        for drill in merged_drills:
            for state in (drill.get(progress.PROGRESS_KEY) or {}).values():
                if isinstance(state, dict):
                    state["next_review"] = now_iso
                    state["total_sessions"] = 0
                    state["streak"] = 0

        example.update({key: value for key, value in db.items() if key != "drills"})
        example["drills"] = merged_drills
        if self._changed(example, "reset_deck_request"):
            log.info("deck reset (%d drills)", len(merged_drills))
        return example

    def _process_outbox(self, db: dict) -> dict:

        dirs = [self.outbox_dir]
        if self.legacy_outbox_dir is not None and self.legacy_outbox_dir.exists():
            dirs.append(self.legacy_outbox_dir)
        if not any(d.exists() for d in dirs):
            return db

        self._in_batch, self._batch_dirty, self._batch_pending = True, False, []
        try:
            db = self._process_events(dirs, db)
            if self._batch_dirty:
                ok, err = self._save_now(db)
                if not ok:
                    log.error("failed saving database after %d outbox event(s): %s -- "
                              "kept in the outbox to replay", len(self._batch_pending), err)

                    raise RuntimeError(f"outbox batch not saved: {err}")
        except BaseException:

            self._forget_db()
            raise
        finally:
            self._in_batch, self._batch_dirty, self._batch_pending = False, False, []
        return db

    def _process_events(self, dirs, db: dict) -> dict:

        for path in sorted((f for d in dirs for f in d.glob("*.json")),
                           key=lambda f: f.name):
            try:
                with open(path, encoding="utf-8") as f:
                    event = json.load(f)
                if not isinstance(event, dict):
                    raise ValueError("not a JSON object")
            except (OSError, ValueError) as e:

                self._quarantine(path, e)
                continue
            changes_before = self._batch_changes
            try:
                kind = event.get("event")
                if kind == "rep_result":
                    self._handle_rep_result(event, db)
                elif kind == "session_concluded":
                    self._handle_session_concluded(event, db)
                elif kind == "create_drill_request":
                    self._handle_create_drill(event, db)
                elif kind == "save_combo_request":
                    self._handle_save_combo(event, db)
                elif kind == "update_drill_request":
                    self._handle_update_drill(event, db)
                elif kind == "delete_drill_request":
                    self._handle_delete_drill(event, db)
                elif kind == "merge_duplicates_request":
                    self._handle_merge_duplicates(event, db)
                elif kind == "set_drill_selection_request":
                    self._handle_set_drill_selection(event, db)
                elif kind == "set_belt_drills_request":
                    self._handle_set_belt_drills(event, db)
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
                elif kind == "match_round":
                    self._handle_match_round(event, db)
                elif kind == "match_end":
                    self._handle_match_end(event, db)
                elif kind == "favorite_match_request":
                    self._handle_favorite_match(event)
                else:
                    log.warning("unknown outbox event kind=%r in %s, discarding", kind, path.name)
            except Exception as e:

                self._quarantine(path, e)
                raise
            if self._batch_changes != changes_before and self._batch_dirty:
                self._batch_pending.append(path)
            else:
                self._delete_events([path])
        return db

    def _quarantine(self, path: Path, error: Exception) -> None:
        failed = path.parent / "failed"
        try:
            failed.mkdir(exist_ok=True)
            target = failed / path.name
            path.replace(target)
            log.error("outbox event %s failed (%s: %s) -- kept in %s",
                      path.name, type(error).__name__, error, target)
        except OSError as move_error:

            log.error("outbox event %s failed (%s) and could not be moved aside (%s)",
                      path.name, error, move_error)

    _combo_plan_key = None

    def _write_combo_plan(self, db: dict) -> None:

        running = live_status.running_combo(self.live_status_path)
        if running is None:
            return
        drill_id, combo, played = running
        drill = self._find_drill(db, drill_id) or {}
        character = drill.get("character_id") or played
        key = (drill_id, character, combo)
        if key == self._combo_plan_key:
            return
        plan = combo_plan.build(drill_id, character, combo, self.data_dir)
        if plan is None:
            return
        path = paths.combo_plan(self.data_dir)
        tmp = path.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(plan, f)
            paths.atomic_replace(tmp, path)
            self._combo_plan_key = key
        except OSError as err:
            log.warning("could not write the combo plan: %s", err)

    def _poll_once(self) -> None:

        db = self._load_db()
        db = self._process_outbox(db)

        self._retry_history_moves(db)
        self._retime_stored_patterns(db)
        self._write_inbox(db)
        self._write_combo_plan(db)

    def run_forever(self) -> None:

        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        log.info("beast_drills running against %s", self.data_dir)

        self._prune_matches()
        try:
            self._add_shipped_drills()
        except Exception:

            log.exception("adding shipped drills failed -- continuing")
        try:
            while True:
                try:
                    self._poll_once()
                except Exception:
                    self._forget_db()
                    log.exception("poll cycle failed -- continuing")
                time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            log.info("beast_drills stopping (interrupted)")
            raise
        finally:
            log.info("beast_drills loop exited")

def _fresh_schedule(drill: dict, now: str) -> None:

    for key, value in scheduler.STARTING_STATE.items():
        drill.setdefault(key, value)
    drill.setdefault("next_review", now)
    drill.setdefault("created_at", now)

def main() -> None:

    cfg = settings.load(DEFAULT_INSTALL_DIR)
    install_dir, data_default = settings.resolve_roots(DEFAULT_INSTALL_DIR)

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
