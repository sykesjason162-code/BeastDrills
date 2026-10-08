from __future__ import annotations

import shutil
from pathlib import Path

RUNTIME = "runtime"
PLAYER = "player"
LOGS = "logs"
DEBUG = "debug"
BACKUPS = "backups"
OUTBOX = "outbox"

SETTINGS_FILE = "beast_drills.ini"
DATABASE_FILE = "shared_database.json"
EXAMPLE_DB_FILE = "shared_database.example.json"
STATS_DB_FILE = "stats.db"
DEV_MARKER = "_dev_mode"

MOVED: dict[str, str] = {
    "_inbox.json": f"{RUNTIME}/inbox.json",
    "_live_status.json": f"{RUNTIME}/live_status.json",
    "_last_rep_result.json": f"{RUNTIME}/last_rep_result.json",
    "_last_session_result.json": f"{RUNTIME}/last_session_result.json",
    "_last_scrimmage_round.json": f"{RUNTIME}/last_scrimmage_round.json",
    "_last_scrimmage_set.json": f"{RUNTIME}/last_scrimmage_set.json",
    "_layout.json": f"{PLAYER}/layout.json",
    "_drill_hotkeys.json": f"{PLAYER}/drill_hotkeys.json",
    "_service.log": f"{LOGS}/service.log",

    "fgsrs_stats.db": STATS_DB_FILE,
    "fgsrs_stats.db-journal": STATS_DB_FILE + "-journal",
    "fgsrs_stats.db-wal": STATS_DB_FILE + "-wal",
    "fgsrs_stats.db-shm": STATS_DB_FILE + "-shm",
}

RENAME_ATTEMPTS = 6
RENAME_BACKOFF = 0.05

def atomic_replace(tmp, target) -> None:

    import time

    delay = RENAME_BACKOFF
    for attempt in range(RENAME_ATTEMPTS):
        try:
            Path(tmp).replace(target)
            return
        except PermissionError:
            if attempt == RENAME_ATTEMPTS - 1:
                raise
            time.sleep(delay)
            delay *= 2

def _p(data_dir, *parts) -> Path:
    return Path(data_dir).joinpath(*parts)

def settings_file(data_dir) -> Path:
    return _p(data_dir, SETTINGS_FILE)

def database(data_dir) -> Path:
    return _p(data_dir, DATABASE_FILE)

def example_database(data_dir) -> Path:
    return _p(data_dir, EXAMPLE_DB_FILE)

def stats_db(data_dir) -> Path:
    return _p(data_dir, STATS_DB_FILE)

def outbox(data_dir) -> Path:
    return _p(data_dir, OUTBOX)

def inbox(data_dir) -> Path:
    return _p(data_dir, RUNTIME, "inbox.json")

def live_status(data_dir) -> Path:
    return _p(data_dir, RUNTIME, "live_status.json")

def session_progress(data_dir) -> Path:

    return _p(data_dir, RUNTIME, "session_in_progress.json")

def last_rep_result(data_dir) -> Path:
    return _p(data_dir, RUNTIME, "last_rep_result.json")

def last_session_result(data_dir) -> Path:
    return _p(data_dir, RUNTIME, "last_session_result.json")

def last_scrimmage_round(data_dir) -> Path:
    return _p(data_dir, RUNTIME, "last_scrimmage_round.json")

def last_scrimmage_set(data_dir) -> Path:
    return _p(data_dir, RUNTIME, "last_scrimmage_set.json")

def service_log(data_dir) -> Path:
    return _p(data_dir, LOGS, "service.log")

def debug_dir(data_dir) -> Path:
    return _p(data_dir, DEBUG)

def backups_dir(data_dir) -> Path:
    return _p(data_dir, BACKUPS)

def ensure(data_dir) -> None:

    for name in (RUNTIME, PLAYER, LOGS, DEBUG, BACKUPS, OUTBOX):
        _p(data_dir, name).mkdir(parents=True, exist_ok=True)

def migrate(data_dir) -> list[str]:

    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        return []
    ensure(data_dir)
    moved = []

    for old_name, new_rel in MOVED.items():
        old = data_dir / old_name
        new = data_dir / new_rel
        if not old.is_file() or new.exists():
            continue
        try:
            old.replace(new)
            moved.append(f"{old_name} -> {new_rel}")
        except OSError:

            continue

    for f in data_dir.glob("_debug_*"):
        if f.is_file():
            target = data_dir / DEBUG / f.name[len("_debug_"):]
            if not target.exists():
                try:
                    f.replace(target)
                    moved.append(f"{f.name} -> {DEBUG}/{target.name}")
                except OSError:
                    pass
    for pattern in ("*.backup-*", "_service.log.*"):
        for f in data_dir.glob(pattern):
            if not f.is_file():
                continue
            folder = LOGS if f.name.startswith("_service.log") else BACKUPS
            target = data_dir / folder / f.name.lstrip("_")
            if not target.exists():
                try:
                    f.replace(target)
                    moved.append(f"{f.name} -> {folder}/{target.name}")
                except OSError:
                    pass
    return moved

REFERENCE_FOLDERS = (
    "action_names",
    "enum_names",
    "frame_data",
    "frame_data_connected",
    "locales",
    "mods",
    "reversal_skills",
)

PLAYER_FOLDERS = (RUNTIME, PLAYER, LOGS, DEBUG, BACKUPS, OUTBOX,
                  "character_data")

PLAYER_FILES = (DATABASE_FILE, STATS_DB_FILE)

PLAYER_DIR_NAME = "Beast Drills"

def _windows_documents() -> Path | None:

    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            if buf.value:
                return Path(buf.value)
    except Exception:
        pass
    return None

def default_player_dir() -> Path:
    docs = _windows_documents() or (Path.home() / "Documents")
    return docs / PLAYER_DIR_NAME

def reference(install_dir, *parts) -> Path:

    return Path(install_dir).joinpath(*parts)

def relocate(install_dir, player_dir) -> list[str]:

    install_dir, player_dir = Path(install_dir), Path(player_dir)
    if install_dir.resolve() == player_dir.resolve():
        return []
    if not install_dir.is_dir():
        return []

    ensure(player_dir)
    moved: list[str] = []

    for name in PLAYER_FILES:
        src, dst = install_dir / name, player_dir / name
        if not src.exists() or dst.exists():
            continue
        try:
            shutil.copy2(src, dst)
            src.replace(src.with_name(src.name + ".moved"))
            moved.append(name)
        except OSError:
            continue

    for folder in PLAYER_FOLDERS:
        src = install_dir / folder
        if not src.is_dir():
            continue
        for f in src.rglob("*"):
            if not f.is_file():
                continue
            dst = player_dir / folder / f.relative_to(src)
            if dst.exists():
                continue
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                moved.append(f"{folder}/{f.relative_to(src)}")
            except OSError:
                continue
    return moved

_INSTALL_DIR: Path | None = None

def set_install_dir(path) -> None:
    global _INSTALL_DIR
    _INSTALL_DIR = Path(path) if path else None

def is_dev_install() -> bool:

    return _INSTALL_DIR is not None and (_INSTALL_DIR / DEV_MARKER).exists()

def reference_dir(data_dir, name) -> Path:

    given = Path(data_dir) / name
    if given.exists() or _INSTALL_DIR is None:
        return given
    return _INSTALL_DIR / name
