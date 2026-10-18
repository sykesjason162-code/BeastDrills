from __future__ import annotations

import json
import sqlite3
from pathlib import Path

def _connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA busy_timeout = 2000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drill_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            attempts INTEGER NOT NULL,
            successes INTEGER NOT NULL,
            final_grade INTEGER NOT NULL,
            bucket_before TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_drill_id ON reviews(drill_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_timestamp ON reviews(timestamp)")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tallies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            character_id TEXT,
            dummy_character_id TEXT,
            start_side TEXT,
            source TEXT NOT NULL,
            counter TEXT NOT NULL,
            value INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tallies_timestamp ON tallies(timestamp)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tallies_matchup "
        "ON tallies(character_id, dummy_character_id)")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS match_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT NOT NULL,
            round INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            mode INTEGER,
            online INTEGER NOT NULL,
            player_side INTEGER,
            character_id TEXT,
            opponent_id TEXT,
            opponent_kind TEXT,
            won INTEGER,
            finish TEXT,
            score INTEGER,
            exchanges INTEGER,
            worst TEXT,
            worst_count INTEGER,
            mirrored INTEGER NOT NULL,
            tally TEXT NOT NULL,
            UNIQUE (match_id, round)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            timestamp INTEGER NOT NULL,
            mode INTEGER,
            online INTEGER NOT NULL,
            player_side INTEGER,
            character_id TEXT,
            opponent_id TEXT,
            opponent_kind TEXT,
            opponent_cpu_level INTEGER,
            rounds INTEGER NOT NULL,
            rounds_to_win INTEGER,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            won INTEGER,
            completed INTEGER NOT NULL,
            how TEXT,
            score INTEGER,
            detail TEXT NOT NULL,
            favorite INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_timestamp ON matches(timestamp)")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS match_totals (
            character_id TEXT NOT NULL,
            opponent_id TEXT NOT NULL,
            mode INTEGER NOT NULL,
            online INTEGER NOT NULL,
            matches INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            rounds INTEGER NOT NULL,
            rounds_won INTEGER NOT NULL,
            rounds_lost INTEGER NOT NULL,
            tally TEXT NOT NULL,
            first_at INTEGER NOT NULL,
            last_at INTEGER NOT NULL,
            PRIMARY KEY (character_id, opponent_id, mode, online)
        )
        """
    )

    conn.row_factory = sqlite3.Row
    _migrate(conn)
    return conn

_ADDED_COLUMNS = (
    ("character_id", "TEXT"),
    ("dummy_character_id", "TEXT"),
    ("start_side", "TEXT"),
)

def _migrate(conn: sqlite3.Connection) -> None:
    have = {row["name"] for row in conn.execute("PRAGMA table_info(reviews)")}
    for name, decl in _ADDED_COLUMNS:
        if name not in have:
            conn.execute(f"ALTER TABLE reviews ADD COLUMN {name} {decl}")

    have = {row["name"] for row in conn.execute("PRAGMA table_info(matches)")}
    if "favorite" not in have:
        conn.execute("ALTER TABLE matches ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
    conn.commit()

def record_review(
    path,
    drill_id: str,
    timestamp: int,
    attempts: int,
    successes: int,
    final_grade: int,
    bucket_before: str,
    character_id: str | None = None,
    dummy_character_id: str | None = None,
    start_side: str | None = None,
) -> tuple:

    try:
        conn = _connect(path)
        try:
            conn.execute(
                """
                INSERT INTO reviews (
                    drill_id, timestamp, attempts, successes, final_grade,
                    bucket_before, character_id, dummy_character_id, start_side
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (drill_id, timestamp, attempts, successes, final_grade, bucket_before,
                 character_id, dummy_character_id, start_side),
            )
            conn.commit()
        finally:
            conn.close()
        return True, None
    except sqlite3.Error as e:
        return False, str(e)

def reviews_for_drill(path, drill_id: str) -> list:

    if not Path(path).exists():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            "SELECT * FROM reviews WHERE drill_id = ? ORDER BY timestamp ASC, id ASC",
            (drill_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def rekey_drill(path, from_id: str, to_id: str) -> int:

    return rekey_drills(path, [from_id], to_id).get(from_id, 0)

def rekey_drills(path, from_ids, to_id: str) -> dict:

    if not Path(path).exists():
        return {}
    conn = _connect(path)
    try:
        with conn:
            return {
                from_id: conn.execute("UPDATE reviews SET drill_id = ? WHERE drill_id = ?",
                                      (to_id, from_id)).rowcount or 0
                for from_id in from_ids
            }
    finally:
        conn.close()

def last_reviewed(path) -> dict:

    if not Path(path).exists():
        return {}
    conn = _connect(path)
    try:
        rows = conn.execute(
            "SELECT drill_id, MAX(timestamp) AS last FROM reviews GROUP BY drill_id"
        ).fetchall()
        return {r["drill_id"]: r["last"] for r in rows}
    finally:
        conn.close()

def all_reviews(path, character_id: str | None = None,
                dummy_character_id: str | None = None) -> list:

    if not Path(path).exists():
        return []
    conn = _connect(path)
    try:
        where, args = [], []
        if character_id:
            where.append("character_id = ?")
            args.append(character_id)
        if dummy_character_id:
            where.append("dummy_character_id = ?")
            args.append(dummy_character_id)
        sql = "SELECT * FROM reviews"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY timestamp ASC, id ASC"
        return [dict(r) for r in conn.execute(sql, tuple(args)).fetchall()]
    finally:
        conn.close()

def record_tally(
    path,
    timestamp: int,
    counts: dict,
    character_id: str | None = None,
    dummy_character_id: str | None = None,
    start_side: str | None = None,
    source: str = "free_play",
) -> tuple:

    rows = [(timestamp, character_id, dummy_character_id, start_side,
             source, str(k), int(v))
            for k, v in (counts or {}).items()
            if isinstance(v, (int, float)) and int(v) > 0]
    if not rows:
        return True, None
    try:
        conn = _connect(path)
        try:
            conn.executemany(
                """
                INSERT INTO tallies (
                    timestamp, character_id, dummy_character_id,
                    start_side, source, counter, value
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        finally:
            conn.close()
        return True, None
    except sqlite3.Error as e:
        return False, str(e)

def tally_totals(path, character_id: str | None = None,
                 dummy_character_id: str | None = None) -> dict:

    if not Path(path).exists():
        return {}
    conn = _connect(path)
    try:
        where, args = [], []
        if character_id:
            where.append("character_id = ?")
            args.append(character_id)
        if dummy_character_id:
            where.append("dummy_character_id = ?")
            args.append(dummy_character_id)
        sql = "SELECT counter, SUM(value) AS total FROM tallies"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY counter ORDER BY total DESC"
        return {r["counter"]: r["total"] for r in conn.execute(sql, tuple(args))}
    finally:
        conn.close()

def tally_matchups(path) -> list:

    if not Path(path).exists():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            """
            SELECT character_id, dummy_character_id,
                   MAX(timestamp) AS last_seen, COUNT(DISTINCT timestamp) AS tallies
            FROM tallies
            GROUP BY character_id, dummy_character_id
            ORDER BY last_seen DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def _bool_or_none(v):
    return None if v is None else int(bool(v))

def record_match_round(path, timestamp: int, graded: dict) -> tuple:

    try:
        conn = _connect(path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO match_rounds (
                    match_id, round, timestamp, mode, online, player_side,
                    character_id, opponent_id, opponent_kind, won, finish,
                    score, exchanges, worst, worst_count, mirrored, tally
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (graded["match_id"], graded["round"], timestamp, graded.get("mode"),
                 int(bool(graded.get("online"))), graded.get("player_side"),
                 graded.get("character_id"), graded.get("opponent_id"),
                 graded.get("opponent_kind"), _bool_or_none(graded.get("won")),
                 graded.get("finish"), graded.get("score"), graded.get("exchanges"),
                 graded.get("worst"), graded.get("worst_count"),
                 int(bool(graded.get("mirrored"))),
                 json.dumps(graded.get("tally") or {}, sort_keys=True)),
            )
            conn.commit()
        finally:
            conn.close()
        return True, None
    except sqlite3.Error as e:
        return False, str(e)

def _round_row(r) -> dict:
    d = dict(r)
    d["tally"] = json.loads(d.get("tally") or "{}")
    for k in ("online", "mirrored"):
        d[k] = bool(d[k])
    if d.get("won") is not None:
        d["won"] = bool(d["won"])
    return d

def match_rounds(path, match_id: str) -> list:

    if not Path(path).exists():
        return []
    conn = _connect(path)
    try:
        rows = conn.execute(
            "SELECT * FROM match_rounds WHERE match_id = ? ORDER BY round ASC",
            (match_id,)).fetchall()
        return [_round_row(r) for r in rows]
    finally:
        conn.close()

def record_match(path, timestamp: int, graded: dict, rounds=None) -> tuple:

    detail = {k: graded.get(k) for k in
              ("weaknesses", "recommendations", "unaddressed", "tally", "mode_name")}
    try:
        conn = _connect(path)
        try:
            if conn.execute("SELECT 1 FROM matches WHERE match_id = ?",
                            (graded["match_id"],)).fetchone():
                return True, None
            conn.execute(
                """
                INSERT INTO matches (
                    match_id, timestamp, mode, online, player_side,
                    character_id, opponent_id, opponent_kind, opponent_cpu_level,
                    rounds, rounds_to_win, wins, losses, won, completed, how,
                    score, detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (graded["match_id"], timestamp, graded.get("mode"),
                 int(bool(graded.get("online"))), graded.get("player_side"),
                 graded.get("character_id"), graded.get("opponent_id"),
                 graded.get("opponent_kind"), graded.get("opponent_cpu_level"),
                 int(graded.get("rounds") or 0), graded.get("rounds_to_win"),
                 int(graded.get("wins") or 0), int(graded.get("losses") or 0),
                 _bool_or_none(graded.get("won")), int(bool(graded.get("completed"))),
                 graded.get("how"), graded.get("score"),
                 json.dumps(detail, sort_keys=True)),
            )
            if graded.get("player_side") is not None and graded.get("character_id"):
                _add_to_totals(conn, timestamp, graded, rounds or [])
            conn.commit()
        finally:
            conn.close()
        return True, None
    except sqlite3.Error as e:
        return False, str(e)

def _add_to_totals(conn, timestamp: int, graded: dict, rounds: list) -> None:
    key = (graded["character_id"], graded.get("opponent_id") or "unknown",
           int(graded.get("mode") or 0), int(bool(graded.get("online"))))
    row = conn.execute(
        "SELECT * FROM match_totals WHERE character_id = ? AND opponent_id = ? "
        "AND mode = ? AND online = ?", key).fetchone()
    tally = json.loads(row["tally"]) if row else {}
    for k, v in (graded.get("tally") or {}).items():
        tally[k] = tally.get(k, 0) + int(v or 0)
    add = {
        "matches": 1,
        "wins": 1 if graded.get("won") is True else 0,
        "losses": 1 if graded.get("won") is False else 0,
        "rounds": len(rounds) or int(graded.get("rounds") or 0),
        "rounds_won": sum(1 for r in rounds if r.get("won") is True),
        "rounds_lost": sum(1 for r in rounds if r.get("won") is False),
    }
    if row:
        conn.execute(
            """
            UPDATE match_totals SET matches = matches + ?, wins = wins + ?,
                losses = losses + ?, rounds = rounds + ?, rounds_won = rounds_won + ?,
                rounds_lost = rounds_lost + ?, tally = ?,
                first_at = MIN(first_at, ?), last_at = MAX(last_at, ?)
            WHERE character_id = ? AND opponent_id = ? AND mode = ? AND online = ?
            """,
            (add["matches"], add["wins"], add["losses"], add["rounds"],
             add["rounds_won"], add["rounds_lost"], json.dumps(tally, sort_keys=True),
             timestamp, timestamp, *key))
    else:
        conn.execute(
            """
            INSERT INTO match_totals (character_id, opponent_id, mode, online,
                matches, wins, losses, rounds, rounds_won, rounds_lost, tally,
                first_at, last_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*key, add["matches"], add["wins"], add["losses"], add["rounds"],
             add["rounds_won"], add["rounds_lost"], json.dumps(tally, sort_keys=True),
             timestamp, timestamp))

def match_totals(path, character_id: str | None = None) -> list:

    if not Path(path).exists():
        return []
    conn = _connect(path)
    try:
        sql, args = "SELECT * FROM match_totals", ()
        if character_id:
            sql, args = sql + " WHERE character_id = ?", (character_id,)
        out = []
        for r in conn.execute(sql + " ORDER BY last_at DESC", args):
            d = dict(r)
            d["tally"] = json.loads(d["tally"] or "{}")
            d["online"] = bool(d["online"])
            out.append(d)
        return out
    finally:
        conn.close()

def set_match_favorite(path, match_id: str, favorite: bool) -> tuple:

    try:
        conn = _connect(path)
        try:
            cur = conn.execute("UPDATE matches SET favorite = ? WHERE match_id = ?",
                               (int(bool(favorite)), match_id))
            conn.commit()
            if cur.rowcount == 0:
                return False, f"no stored match {match_id!r}"
        finally:
            conn.close()
        return True, None
    except sqlite3.Error as e:
        return False, str(e)

def recent_matches(path, limit: int = 50, character_id: str | None = None) -> list:

    if not Path(path).exists():
        return []
    conn = _connect(path)
    try:
        where, args = "", ()
        if character_id:
            where, args = " WHERE character_id = ?", (character_id,)
        out = []
        for r in conn.execute(
                "SELECT * FROM matches" + where + " ORDER BY timestamp DESC LIMIT ?",
                (*args, int(limit))):
            d = dict(r)
            d.update(json.loads(d.pop("detail") or "{}"))
            for k in ("online", "completed", "favorite"):
                d[k] = bool(d[k])
            if d.get("won") is not None:
                d["won"] = bool(d["won"])
            d["finished"] = True
            d["rounds_list"] = []
            out.append(d)
        by_id = {d["match_id"]: d for d in out}

        unfinished: dict = {}
        for r in conn.execute(
                "SELECT * FROM match_rounds"
                + (" WHERE character_id = ?" if character_id else "")
                + " ORDER BY round ASC", args):
            rd = _round_row(r)
            if rd["match_id"] in by_id:
                by_id[rd["match_id"]]["rounds_list"].append(rd)
                continue
            if conn.execute("SELECT 1 FROM matches WHERE match_id = ?",
                            (rd["match_id"],)).fetchone():
                continue
            m = unfinished.setdefault(rd["match_id"], {
                "match_id": rd["match_id"], "timestamp": rd["timestamp"],
                "mode": rd["mode"], "online": rd["online"],
                "player_side": rd["player_side"], "character_id": rd["character_id"],
                "opponent_id": rd["opponent_id"], "opponent_kind": rd["opponent_kind"],
                "finished": False, "favorite": False, "rounds_list": []})
            m["timestamp"] = max(m["timestamp"], rd["timestamp"])
            m["rounds_list"].append(rd)
        for m in unfinished.values():
            m["rounds"] = len(m["rounds_list"])
            m["wins"] = sum(1 for x in m["rounds_list"] if x.get("won") is True)
            m["losses"] = sum(1 for x in m["rounds_list"] if x.get("won") is False)
            out.append(m)
        out.sort(key=lambda d: d["timestamp"], reverse=True)
        return out[:int(limit)]
    finally:
        conn.close()

_ROW_OVERHEAD = 200

def match_bytes(path) -> int:

    if not Path(path).exists():
        return 0
    conn = _connect(path)
    try:
        return _match_bytes_open(conn)
    finally:
        conn.close()

def prune_matches(path, max_bytes: int) -> int:

    if max_bytes <= 0 or match_bytes(path) <= max_bytes:
        return 0
    target = int(max_bytes * 0.9)
    removed = 0
    conn = _connect(path)
    try:

        ids = [row[0] for row in conn.execute(
            """
            SELECT match_id FROM (
                SELECT match_id, timestamp FROM matches WHERE favorite = 0
                UNION ALL
                SELECT match_id, MAX(timestamp) FROM match_rounds
                WHERE match_id NOT IN (SELECT match_id FROM matches)
                GROUP BY match_id
            ) ORDER BY timestamp ASC
            """)]
        for match_id in ids:
            if _match_bytes_open(conn) <= target:
                break
            conn.execute("DELETE FROM match_rounds WHERE match_id = ?", (match_id,))
            conn.execute("DELETE FROM matches WHERE match_id = ?", (match_id,))
            removed += 1
        conn.commit()
        if removed:
            conn.execute("VACUUM")
        return removed
    finally:
        conn.close()

def _match_bytes_open(conn) -> int:
    r = conn.execute("SELECT COALESCE(SUM(LENGTH(tally)), 0) + COUNT(*) * ? FROM match_rounds",
                     (_ROW_OVERHEAD,)).fetchone()[0]
    m = conn.execute("SELECT COALESCE(SUM(LENGTH(detail)), 0) + COUNT(*) * ? FROM matches",
                     (_ROW_OVERHEAD,)).fetchone()[0]
    return int(r) + int(m)
