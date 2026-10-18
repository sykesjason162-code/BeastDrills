"""The dashboard's Flask app -- a SEPARATE process from
beast_drills.service (run alongside it, not a thread inside its polling
loop). Only ever reads shared_database.json and the runtime/ files
directly (safe, read-only, as the plugin reads it too) and only
ever WRITES via outbox_writer.write_outbox_event -- never database.save()
-- because beast_drills.service is the sole writer of shared_database.json
(see CLAUDE.md's incident log: every past attempt to write it from
anywhere else raced against that ownership and lost/corrupted data).

Run with: python -m beast_drills.dashboard
The address and data folder come from beast_drills.ini; --port and
--data-dir override it for one run only, the same rule as the launcher.
Needs the optional "dashboard" extra installed: pip install -e ".[dashboard]"
See docs/SERVICE.md and docs/DEVELOPMENT.md.
"""

import argparse
import json
import logging
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, request

from . import (attempts, criteria, dashboard_data, database, deck, drill_search,
               duplicates, matches,
               outbox_writer, response_check, reviews_db, scheduler, wongscript)

from .live_status import player_character
from . import belts, drill_fields, ids, paths, settings
from .service import DEFAULT_INSTALL_DIR

log = logging.getLogger("beast_drills.dashboard")

LIVE_STATUS_STALE_AFTER_SECONDS = 2.0

def _slugify(name: str) -> str:

    s = "".join(c if c.isalnum() else "_" for c in name.lower())
    s = s.strip("_")
    while "__" in s:
        s = s.replace("__", "_")
    return s or "captured_drill"

def _drill_fields(parsed: dict) -> dict:

    fields = {
        "name": parsed["name"],
        "description": parsed.get("description") or "",
        "training_settings": parsed.get("training_settings") or {},
        "slot_outcomes": parsed.get("slot_outcomes"),
        "fixed_expected_response": parsed.get("fixed_expected_response"),
        "expected_setup": parsed.get("expected_setup"),
        "against_criteria": parsed.get("against_criteria"),
        "survive_seconds": parsed.get("survive_seconds"),
        "fixed_expected_combo": parsed.get("fixed_expected_combo"),
        "response_window_frames": parsed.get("response_window_frames"),
        "game_speed": parsed.get("game_speed"),
        "reps": parsed.get("reps"),
        "wongscript_text": parsed.get("wongscript_text"),
    }
    for key in ("character_id", "dummy_character_id", "trains", "trains_for",
                "difficulty"):
        if parsed.get(key):
            fields[key] = parsed[key]

    if attempts.normalize(parsed.get(attempts.FIELD)) != attempts.DEFAULT:
        fields[attempts.FIELD] = attempts.normalize(parsed.get(attempts.FIELD))

    fields[belts.FIELD] = parsed.get(belts.FIELD)
    return fields

_db_cache: dict = {}
_db_cache_lock = threading.Lock()

def _load_db_or_none(db_path: Path):
    try:
        st = Path(db_path).stat()
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        key = None
    with _db_cache_lock:
        hit = _db_cache.get(str(db_path))
        if key is not None and hit and hit[0] == key:
            return hit[1]
    data, err = database.load(db_path)
    if data is None:
        log.warning("could not load database at %s: %s", db_path, err)
        return None
    if key is not None:
        with _db_cache_lock:
            _db_cache[str(db_path)] = (key, data)
    return data

def _read_json_or_none(path: Path):
    import json

    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None

def create_app(data_dir) -> Flask:
    data_dir = Path(data_dir)
    outbox_dir = data_dir / "outbox"
    db_path = paths.database(data_dir)
    stats_db_path = paths.stats_db(data_dir)

    def _no_database():

        if db_path.exists():
            _data, err = database.load(db_path)
            if _data is None:
                return jsonify({"error": "database_unreadable: " + database.unreadable_message(
                    db_path, paths.backups_dir(data_dir), err)}), 503
        return jsonify({"error": "database_not_found: start beast_drills.service first"}), 503
    live_status_path = paths.live_status(data_dir)
    last_rep_result_path = paths.last_rep_result(data_dir)
    last_session_result_path = paths.last_session_result(data_dir)

    app = Flask(__name__)

    app.config["TEMPLATES_AUTO_RELOAD"] = True

    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

    app.config.setdefault("BD_LOCAL_ONLY", True)

    _LOOPBACK = {"127.0.0.1", "localhost", "::1"}

    @app.before_request
    def _refuse_cross_site():
        raw = request.host or ""

        if raw.startswith("[") and "]" in raw:
            hostname = raw[1:raw.index("]")]
        else:
            hostname = raw.rsplit(":", 1)[0]
        if app.config["BD_LOCAL_ONLY"] and hostname not in _LOOPBACK:
            return jsonify({"error": "host_not_allowed"}), 403
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        origin = request.headers.get("Origin")
        if origin and origin != "null":
            from urllib.parse import urlsplit
            if urlsplit(origin).netloc != request.host:
                return jsonify({"error": "cross_origin_refused"}), 403
        elif origin == "null":
            return jsonify({"error": "cross_origin_refused"}), 403
        if (request.content_length or 0) > 0 and not request.is_json:
            return jsonify({"error": "json_required"}), 415
        return None

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/drills")
    def drills_page():
        return render_template("drills.html")

    @app.get("/help")
    def help_page():
        return render_template("help.html")

    @app.get("/stats")
    def stats_page():

        return render_template("stats.html")

    @app.get("/matches")
    def matches_page():

        return render_template("matches.html")

    @app.get("/scrimmage")
    def scrimmage_page():

        return redirect("/matches", code=301)

    @app.get("/profile")
    def profile_page():

        return render_template("profile.html")

    LIST_OMITS = ("wongscript_text",)

    def _with_belt(drill):
        tag = belts.tag(drill)
        return {**drill, "_belt": tag} if tag else drill

    @app.get("/api/drills/facets")
    def drill_facets():

        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()

        drills = db.get("drills") or []
        types = set()
        for d in drills:
            types |= drill_search.drill_types(d)
        return jsonify({
            "total": len(drills),
            "types": sorted(types),
            "characters": sorted({d["character_id"] for d in drills if d.get("character_id")}),
            "dummies": sorted({d["dummy_character_id"] for d in drills if d.get("dummy_character_id")}),

            "characters_unset": any(not d.get("character_id") for d in drills),
            "dummies_unset": any(not d.get("dummy_character_id") for d in drills),

            "belts": sorted({t["belt"] for t in (belts.tag(d) for d in drills) if t},
                            key=lambda b: belts.BELT_INDEX[b]),
        })

    @app.get("/api/drills")
    def list_drills():

        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        all_drills = [_with_belt(d) for d in (db.get("drills") or [])]

        query = (request.args.get("q") or "").strip()
        matched = drill_search.search(all_drills, query, now=now_iso) if query else all_drills

        matched = sorted(matched, key=lambda d: not d.get("favorite"))

        try:
            limit = int(request.args.get("limit", 0))
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            limit, offset = 0, 0
        page = matched[offset:offset + limit] if limit > 0 else matched[offset:]

        played_as = player_character(live_status_path)
        due_ids = {d["id"] for d in deck.get_due_drills(db, now_iso, played_as)}

        reviews_by_drill: dict = {}
        for row in reviews_db.all_reviews(stats_db_path):
            reviews_by_drill.setdefault(row["drill_id"], []).append(row)

        full = request.args.get("fields") == "full"

        locked = not paths.is_dev_install()
        drills = []
        for drill in page:
            entry = {k: v for k, v in drill.items()
                     if (full or k not in LIST_OMITS) and k != "_belt"}
            entry["official"] = bool(drill.get("_belt"))
            entry["locked"] = locked and entry["official"]
            entry["belt"] = drill.get("_belt")
            entry["bucket"] = dashboard_data.bucket_drill(drill, played_as)
            entry["is_due"] = drill.get("id") in due_ids
            history = dashboard_data.reviews_to_history_rows(reviews_by_drill.get(drill.get("id"), []))
            entry.update(dashboard_data.compute_grade_stats(history))
            drills.append(entry)

        if not query and not limit and not offset:
            return jsonify(drills)
        return jsonify({"drills": drills, "total": len(all_drills),
                        "matched": len(matched),
                        "offset": offset, "limit": limit})

    @app.get("/api/drills/<drill_id>")
    def get_drill(drill_id):
        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()

        for drill in db.get("drills") or []:
            if drill.get("id") == drill_id:
                entry = dict(drill)

                entry["history"] = dashboard_data.reviews_to_history_rows(
                    reviews_db.reviews_for_drill(stats_db_path, drill_id)
                )
                return jsonify(entry)
        return jsonify({"error": f"drill_id_not_found: {drill_id}"}), 404

    @app.get("/api/drills/<drill_id>/wong")
    def get_drill_wong(drill_id):

        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        for drill in db.get("drills") or []:
            if drill.get("id") == drill_id:
                dummy_char = request.args.get("dummy") or None
                text = wongscript.render(drill, dummy_char=dummy_char, data_dir=data_dir)
                return jsonify({"wong": text})
        return jsonify({"error": f"drill_id_not_found: {drill_id}"}), 404

    @app.get("/api/reversal-skills")
    def reversal_skills():

        rtype = (request.args.get("type") or "").upper()
        dummy = request.args.get("dummy") or None
        if rtype not in wongscript.REVERSAL_TYPE_TO_INT:
            return jsonify({"skills": []})
        return jsonify({"skills": wongscript.skill_names_for(data_dir, dummy, rtype)})

    @app.post("/api/pattern/parse")
    def parse_pattern_notation():

        body = request.get_json(force=True, silent=True) or {}
        text = body.get("text") or ""
        errors = []
        pattern = wongscript._parse_pattern_notation(text, errors, 1)
        if errors:
            return jsonify({"pattern": None, "errors": errors}), 200
        return jsonify({"pattern": pattern, "errors": []})

    @app.post("/api/pattern/render")
    def render_pattern_notation():

        body = request.get_json(force=True, silent=True) or {}
        pattern = body.get("pattern") or []
        return jsonify({"text": wongscript._render_pattern_notation(pattern)})

    @app.post("/api/wongscript/parse")
    def parse_wongscript():

        body = request.get_json(force=True, silent=True) or {}
        text = body.get("text") or ""
        drill, errors = wongscript.parse(text, data_dir=data_dir)
        if errors:
            return jsonify({"drill": None, "errors": errors}), 200

        return jsonify({"drill": drill, "errors": [], "belt": belts.tag(drill)})

    @app.post("/api/wongscript/render")
    def render_wongscript():

        body = request.get_json(force=True, silent=True) or {}
        drill = body.get("drill")
        if not isinstance(drill, dict):
            return jsonify({"error": "drill_required"}), 400
        dummy_char = body.get("dummy") or None
        try:
            text = wongscript.render(drill, dummy_char=dummy_char, data_dir=data_dir)
        except Exception as exc:

            return jsonify({"error": f"render_failed: {exc}"}), 200
        return jsonify({"wong": text})

    @app.get("/api/wongscript/export")
    def export_wongscript():

        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        dummy = request.args.get("dummy") or None
        drills = db.get("drills") or []
        dummy_chars = {}
        if dummy:
            for d in drills:
                if (d.get("training_settings") or {}).get("reversal_slots"):
                    dummy_chars[d.get("id")] = dummy
        text = wongscript.render_bundle(drills, dummy_chars=dummy_chars, data_dir=data_dir)
        return Response(
            text, mimetype="text/plain",
            headers={"Content-Disposition": "attachment; filename=beast_drills.wong"},
        )

    @app.post("/api/wongscript/import")
    def import_wongscript():

        body = request.get_json(force=True, silent=True) or {}
        text = body.get("text") or ""
        mode = (body.get("mode") or "append").strip().lower()
        if mode not in ("append", "override"):
            return jsonify({"error": "mode_invalid: expected 'append' or 'override'"}), 400
        drills, errors = wongscript.parse_bundle(text, data_dir=data_dir)

        db = _load_db_or_none(db_path) or {"drills": []}
        stored = db.get("drills") or []
        existing_ids = {d.get("id") for d in stored}
        existing_ids.update(db.get("deleted_drill_ids") or [])

        by_name = {duplicates.name_key(d): d for d in stored}
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        imported_ids, updated_ids, skipped = [], [], []
        for parsed in drills:
            existing = by_name.get(duplicates.name_key(parsed))
            if existing is not None:
                if mode == "append":
                    skipped.append(existing.get("id"))
                    continue
                outbox_writer.write_outbox_event(outbox_dir, {
                    "event": "update_drill_request",
                    "drill_id": existing.get("id"),
                    "patch": _drill_fields(parsed),
                })
                updated_ids.append(existing.get("id"))
                continue

            base_id = _slugify(parsed["name"])
            final_id, n = base_id, 2
            while final_id in existing_ids:
                final_id = f"{base_id}_{n}"
                n += 1
            existing_ids.add(final_id)

            drill = dict(_drill_fields(parsed), **{
                "id": final_id,
                "source": "Imported via WongScript bundle",

                **scheduler.STARTING_STATE,
                "next_review": now_iso,
            })
            outbox_writer.write_outbox_event(outbox_dir, {"event": "create_drill_request", "drill": drill})
            by_name[duplicates.name_key(parsed)] = drill
            imported_ids.append(final_id)

        return jsonify({"imported": imported_ids, "updated": updated_ids,
                        "skipped": skipped, "errors": errors}), 202

    @app.post("/api/criteria/validate")
    def validate_criteria():

        body = request.get_json(force=True, silent=True) or {}
        errors = []
        out = {}

        success = (body.get("success") or "").strip()
        if success:
            parsed = wongscript._parse_categories(success, errors, 1)
            if parsed is not None:
                out["fixed_expected_response"] = parsed

        for key, allowed in (("against", criteria.AGAINST_ATOMS),
                             ("setup", criteria.SETUP_ATOMS)):
            raw = (body.get(key) or "").strip()
            if not raw:
                continue
            names = [wongscript._from_kebab(t.strip()) for t in raw.split(",") if t.strip()]
            bad = [n for n in names if n not in allowed]
            if bad:
                errors.append({"line": 1, "message": f"{key}: cannot name '{bad[0]}' -- only "
                               + ", ".join(wongscript._to_kebab(a) for a in allowed)})
            else:
                out[key] = names

        return jsonify({"ok": not errors, "errors": errors, "parsed": out})

    @app.post("/api/drills")
    def create_drill():
        body = request.get_json(force=True, silent=True) or {}
        name = (body.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name_required"}), 400

        drill_id = body.get("id") or _slugify(name)
        if not ids.valid_drill_id(drill_id):
            return jsonify({"error": "invalid_id: letters, digits, _ . - only"}), 400
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        drill = {

            **drill_fields.from_body(body),
            "id": drill_id,
            "name": name,
            "description": body.get("description") or "",
            "training_settings": body.get("training_settings") or {},

            "source": "Created from the dashboard",
            **scheduler.STARTING_STATE,
            "next_review": now_iso,
        }
        outbox_writer.write_outbox_event(outbox_dir, {"event": "create_drill_request", "drill": drill})
        return jsonify({"queued": True, "proposed_id": drill["id"]}), 202

    @app.get("/api/response_categories")
    def response_categories():

        return jsonify({
            "categories": response_check.SUPPORTED,

            "trains": wongscript.TRAINS_CATEGORIES,
            "trains_for": wongscript.TRAINS_FOR_CATEGORIES,
        })

    def _official(drill_id):

        if paths.is_dev_install():
            return False
        db = _load_db_or_none(db_path) or {}
        drill = next((d for d in db.get("drills") or [] if d.get("id") == drill_id), None)
        return bool(drill) and belts.is_belt_drill(drill)

    @app.patch("/api/drills/<drill_id>")
    def update_drill(drill_id):

        if _official(drill_id):
            return jsonify({"error": "belt_drill_read_only"}), 409
        body = request.get_json(force=True, silent=True) or {}

        patch = drill_fields.from_body(body)
        outbox_writer.write_outbox_event(
            outbox_dir, {"event": "update_drill_request", "drill_id": drill_id, "patch": patch}
        )
        return jsonify({"queued": True}), 202

    @app.post("/api/matches/<match_id>/favorite")
    def favorite_match(match_id):

        body = request.get_json(silent=True) or {}
        outbox_writer.write_outbox_event(outbox_dir, {
            "event": "favorite_match_request", "match_id": match_id,
            "favorite": bool(body.get("favorite", True))})
        return jsonify({"queued": True}), 202

    @app.delete("/api/drills/<drill_id>")
    def delete_drill(drill_id):
        if _official(drill_id):
            return jsonify({"error": "belt_drill_read_only"}), 409
        outbox_writer.write_outbox_event(outbox_dir, {"event": "delete_drill_request", "drill_id": drill_id})
        return jsonify({"queued": True}), 202

    @app.patch("/api/drills/<drill_id>/selection")
    def set_drill_selection(drill_id):
        body = request.get_json(force=True, silent=True) or {}
        selected = bool(body.get("selected"))
        outbox_writer.write_outbox_event(
            outbox_dir,
            {"event": "set_drill_selection_request", "drill_id": drill_id, "selected": selected},
        )
        return jsonify({"queued": True}), 202

    @app.patch("/api/drills/selection")
    def set_drill_selection_bulk():

        body = request.get_json(force=True, silent=True) or {}
        drill_ids = body.get("drill_ids") or []
        selected = bool(body.get("selected"))
        outbox_writer.write_outbox_event(
            outbox_dir,
            {"event": "set_drill_selection_bulk_request", "drill_ids": drill_ids, "selected": selected},
        )
        return jsonify({"queued": True}), 202

    @app.patch("/api/drills/<drill_id>/favorite")
    def set_drill_favorite(drill_id):
        body = request.get_json(force=True, silent=True) or {}
        outbox_writer.write_outbox_event(
            outbox_dir,
            {"event": "set_drill_favorite_request", "drill_id": drill_id,
             "favorite": bool(body.get("favorite"))},
        )
        return jsonify({"queued": True}), 202

    @app.get("/api/live")
    def live_status():
        live = _read_json_or_none(live_status_path)
        age = None
        if live_status_path.exists():
            age = max(0.0, time.time() - live_status_path.stat().st_mtime)
        return jsonify(
            {
                "live_status": live,
                "live_status_age_seconds": age,
                "is_stale": age is None or age > LIVE_STATUS_STALE_AFTER_SECONDS,
                "last_rep_result": _read_json_or_none(last_rep_result_path),
                "last_session_result": _read_json_or_none(last_session_result_path),
            }
        )

    def _character_arg():

        value = (request.args.get("character") or "").strip()
        return None if value in ("", "all") else value

    def _dummy_arg():

        value = (request.args.get("dummy") or "").strip()
        return None if value in ("", "all") else value

    @app.get("/api/duplicates")
    def duplicate_drills():

        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        drills = db.get("drills") or []

        return jsonify({"summary": duplicates.summarise(drills),
                        "groups": duplicates.find_groups(
                            drills, reviews_db.last_reviewed(stats_db_path))})

    @app.post("/api/duplicates/merge")
    def merge_duplicates():

        body = request.get_json(silent=True) or {}
        keep_id = body.get("keep_id")
        merge_ids = [i for i in (body.get("merge_ids") or []) if i != keep_id]
        if not keep_id or not merge_ids:
            return jsonify({"error": "keep_id and merge_ids are both required"}), 400
        outbox_writer.write_outbox_event(outbox_dir, {
            "event": "merge_duplicates_request",
            "keep_id": keep_id,
            "merge_ids": merge_ids,
        })
        return jsonify({"queued": {"keep_id": keep_id, "merge_ids": merge_ids}})

    @app.get("/api/stats/hit_zones_dealt")
    def stats_hit_zones_dealt():

        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        return jsonify(dashboard_data.compute_hit_zones(db, "hit_zones_dealt"))

    @app.get("/api/stats/overview")
    def stats_overview():
        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return jsonify(dashboard_data.compute_overview(db, now_iso, _character_arg()))

    @app.get("/api/matches")
    def matches_state():

        try:
            limit = max(1, min(500, int(request.args.get("limit") or 100)))
        except ValueError:
            limit = 100
        rows = reviews_db.recent_matches(stats_db_path, limit, _character_arg())

        return jsonify({"matches": matches.view(rows),
                        "overall": matches.overall(reviews_db.match_totals(stats_db_path))})

    @app.get("/api/profile/belt")
    def profile_belt():

        character = (request.args.get("character") or "").strip()
        if not character:
            return jsonify({"error": "character_required"}), 400
        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        reviews = reviews_db.all_reviews(stats_db_path, character)
        return jsonify(belts.belt_for(db.get("drills") or [], reviews, character))

    @app.get("/api/matches/roster")
    def matches_roster():

        player = request.args.get("player") or None
        return jsonify(matches.roster(reviews_db.match_totals(stats_db_path), player))

    @app.get("/api/locales")
    def locales():

        found = ["en"]
        folder = Path(app.static_folder or "") / "locales"
        if folder.is_dir():
            found += sorted(p.stem for p in folder.glob("*.json") if p.stem != "en")
        return jsonify(found)

    @app.get("/api/profile/export")
    def profile_export():

        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        payload = dashboard_data.build_profile_export(
            db,
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            reviews_db.all_reviews(stats_db_path),
        )
        name = "beast-drills-profile-" + time.strftime("%Y-%m-%d", time.gmtime()) + ".json"
        return app.response_class(
            json.dumps(payload, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )

    @app.get("/api/stats/tally")
    def stats_tally():

        return jsonify({
            "totals": reviews_db.tally_totals(
                stats_db_path, _character_arg(), _dummy_arg()),
            "matchups": reviews_db.tally_matchups(stats_db_path),
        })

    @app.get("/api/stats/hit_zones")
    def stats_hit_zones():
        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        return jsonify(dashboard_data.compute_hit_zones(db))

    @app.get("/api/stats/reviews")
    def stats_reviews():
        return jsonify(dashboard_data.compute_review_days(
            reviews_db.all_reviews(stats_db_path, _character_arg(), _dummy_arg())))

    @app.get("/api/stats/forecast")
    def stats_forecast():
        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return jsonify(dashboard_data.compute_forecast(
            dashboard_data.drills_for_character(db.get("drills") or [], _character_arg()), now_iso))

    @app.get("/api/stats/hourly")
    def stats_hourly():
        return jsonify(dashboard_data.compute_hourly_breakdown(
            reviews_db.all_reviews(stats_db_path, _character_arg(), _dummy_arg())))

    @app.get("/api/stats/answer_buttons")
    def stats_answer_buttons():
        return jsonify(dashboard_data.compute_answer_buttons(
            reviews_db.all_reviews(stats_db_path, _character_arg(), _dummy_arg())))

    @app.get("/api/stats/retention")
    def stats_retention():
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return jsonify(dashboard_data.compute_retention(
            reviews_db.all_reviews(stats_db_path, _character_arg(), _dummy_arg()), now_iso))

    @app.get("/api/stats/added")
    def stats_added():
        db = _load_db_or_none(db_path)
        if db is None:
            return _no_database()
        return jsonify(dashboard_data.compute_added(
            dashboard_data.drills_for_character(db.get("drills") or [], _character_arg())))

    return app

def main() -> None:

    cfg = settings.load(DEFAULT_INSTALL_DIR)
    _install_dir, data_default = settings.resolve_roots(DEFAULT_INSTALL_DIR)

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--data-dir", type=Path, default=data_default,
                        help="BeastDrills_data directory (default from beast_drills.ini)")

    parser.add_argument("--port", type=int, default=cfg[("dashboard", "port")])
    parser.add_argument(
        "--host",
        default=cfg[("dashboard", "host")],
        help="Loopback-only by default -- this is the project's first network listener; "
        "not meant to be LAN-reachable.",
    )
    parser.add_argument("--verbose", action="store_true",
                        default=cfg[("dashboard", "verbose")],
                        help="more detail in the log (also settable in beast_drills.ini)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    paths.ensure(args.data_dir)

    for moved in paths.migrate(args.data_dir):
        log.info("tidied: %s", moved)
    for moved in paths.relocate(_install_dir, args.data_dir):
        log.info("moved out of the game folder: %s", moved)

    app = create_app(args.data_dir)

    app.config["BD_LOCAL_ONLY"] = args.host in ("127.0.0.1", "localhost", "::1")
    log.info("beast_drills.dashboard running against %s", args.data_dir)
    if args.host != "127.0.0.1":

        log.warning("listening on %s -- reachable from the network, and there is "
                    "no password. Only do this on a network you trust.", args.host)
    app.run(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
