from __future__ import annotations

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

    if not Path(path).exists():
        return 0
    conn = _connect(path)
    try:
        cur = conn.execute("UPDATE reviews SET drill_id = ? WHERE drill_id = ?",
                           (to_id, from_id))
        conn.commit()
        return cur.rowcount or 0
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
