from __future__ import annotations

import configparser
import logging
from pathlib import Path

log = logging.getLogger(__name__)

FILENAME = "beast_drills.ini"

DEFAULTS: tuple[tuple[str, str, object, str], ...] = (
    ("paths", "data_dir", "",
     "WHERE YOUR OWN DATA LIVES -- your drills, your history, your\n"
     "layout and hotkeys. Everything here is yours, and none of it can\n"
     "be downloaded again.\n"
     "\n"
     "Leave blank for Documents\\Beast Drills, which is created for you\n"
     "the first time the mod runs.\n"
     "\n"
     "IT IS DELIBERATELY OUTSIDE THE GAME FOLDER. Mod managers own that\n"
     "folder, and some of them empty a mod's directory when they update\n"
     "it -- which would take your drills and your whole review history\n"
     "with them. Point this anywhere you like: another drive, a synced\n"
     "folder, as long as your mod manager will not touch it.\n"
     "\n"
     "TO RUN THE DASHBOARD ON ANOTHER COMPUTER: share this folder over\n"
     "your network, then set this on the OTHER machine to the share:\n"
     "  data_dir = //gaming-pc/Beast Drills\n"
     "The game keeps writing to its own disk and the dashboard reads the\n"
     "same files across the network. Set public_url below as well, so the\n"
     "in-game menu opens the right address."),
    ("paths", "install_dir", "",
     "Where the mod's OWN files live -- move names, frame data,\n"
     "translations. These ship with Beast Drills and are replaced when\n"
     "you update it, so nothing here is worth backing up.\n"
     "\n"
     "Leave blank unless the dashboard is on a different computer from\n"
     "the game, in which case point it at that machine's copy:\n"
     "  install_dir = //gaming-pc/BeastDrills_data"),
    ("dashboard", "host", "127.0.0.1",
     "Which address the dashboard listens on.\n"
     "127.0.0.1 means this computer only. Use 0.0.0.0 to reach it from\n"
     "your phone or another PC -- only do that on a network you trust,\n"
     "since it has no password."),
    ("dashboard", "port", 8765,
     "Which port the dashboard uses. Change it if something else on\n"
     "your machine already has 8765."),
    ("dashboard", "open_browser", True,
     "Open the dashboard in your browser when it starts."),
    ("dashboard", "public_url", "",
     "The address the IN-GAME menu should open.\n"
     "Leave blank on a normal single-PC setup -- it is worked out from\n"
     "the host and port above.\n"
     "Set it when the dashboard runs on a DIFFERENT computer from the\n"
     "game, e.g. http://gaming-pc:8765 -- the game cannot guess the\n"
     "other machine's name."),
    ("dashboard", "verbose", False,
     "Write more detail to the log. Turn this on if something is wrong\n"
     "and you want to see why."),
    ("practice", "language", "",
     "Interface language: en or ja. Blank follows what you picked in the\n"
     "dashboard itself."),
    ("practice", "reps", 0,
     "How many attempts a session asks for, when the drill does not say.\n"
     "0 keeps the built-in 10. A drill that sets its own still wins."),
    ("practice", "response_window", 0,
     "How long, in frames at 60fps, Beast Drills waits for your answer\n"
     "before calling the attempt over.\n"
     "0 keeps the built-in 20. Raise it if quick attempts are being\n"
     "closed before you finish them. A drill that sets its own wins."),
    ("practice", "allow_slow_start", True,
     "Some drills start at half speed and work up as you improve.\n"
     "Set this to false to always play at full speed, whatever the\n"
     "drill asks for."),
    ("scrimmage", "rounds_per_set", 3,
     "Rounds in one scrimmage set."),
    ("scrimmage", "max_cpu_level", 6,
     "How high the CPU is allowed to climb.\n"
     "Capped at 6 on purpose: levels 7 and 8 read your inputs rather\n"
     "than reacting, so beating them teaches something that does not\n"
     "transfer to a real opponent. Raise it if you disagree."),
)

MODS_SECTION_TEMPLATE = [
    "# ---------------------------------------------------------------",
    "# OTHER MODS. A mod can put an item on the Beast Drills menu bar by",
    "# shipping a small JSON file and naming it here -- one line per mod,",
    "# any name on the left, the path to their file on the right:",
    "#",
    "#   [mods]",
    "#   frame_trap_finder = reframework/autorun/FrameTraps/beast.json",
    "#",
    "# The path is relative to the Street Fighter 6 folder, so it keeps",
    "# working if you move your Steam library to another drive. A path",
    "# outside that folder is ignored, and so is one whose file is not",
    "# there -- which is what uninstalling that mod looks like, and the",
    "# menu item simply goes away.",
    "#",
    "# A mod can also drop its file straight into BeastDrills_data/mods/",
    "# instead. Naming it here is tidier: the entry belongs to the mod",
    "# and leaves with it. See docs/EXTENSIONS.md.",
    "# ---------------------------------------------------------------",
    "",
]

def _path(data_dir) -> Path:
    return Path(data_dir) / FILENAME

def load(data_dir) -> dict:

    values = {(s, k): d for s, k, d, _ in DEFAULTS}
    path = _path(data_dir)
    if not path.is_file():
        return values

    parser = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
    try:
        parser.read(path, encoding="utf-8")
    except (configparser.Error, OSError) as e:

        log.warning("%s could not be read (%s) -- using defaults", path.name, e)
        return values

    for section, key, default, _comment in DEFAULTS:
        if not parser.has_option(section, key):
            continue
        try:
            if isinstance(default, bool):
                values[(section, key)] = parser.getboolean(section, key)
            elif isinstance(default, int):
                values[(section, key)] = parser.getint(section, key)
            else:
                values[(section, key)] = parser.get(section, key).strip()
        except ValueError:
            log.warning("%s: [%s] %s is not valid -- using %r",
                        path.name, section, key, default)
    return values

def get(data_dir, section: str, key: str):

    return load(data_dir).get((section, key))

def write_example(data_dir) -> Path:

    path = _path(data_dir)
    if path.exists():
        return path

    lines = [
        "# Beast Drills settings.",
        "#",
        "# Every setting below is optional -- delete one and it goes back to",
        "# its default. If this file is missing entirely, all defaults apply.",
        "# Lines starting with # are notes and are ignored.",
        "",
    ]
    current = None
    for section, key, default, comment in DEFAULTS:
        if section != current:
            lines.append(f"[{section}]")
            current = section
        for line in comment.split("\n"):
            lines.append(f"# {line}")
        shown = default
        if isinstance(default, bool):
            shown = "true" if default else "false"
        lines.append(f"{key} = {shown}")
        lines.append("")

    lines.extend(MODS_SECTION_TEMPLATE)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

def dashboard_url(cfg) -> str:

    explicit = (cfg[("dashboard", "public_url")] or "").strip()
    if explicit:
        return explicit.rstrip("/")
    host = cfg[("dashboard", "host")]

    if host in ("0.0.0.0", "::", ""):
        host = "localhost"
    return f"http://{host}:{cfg[('dashboard', 'port')]}"

def resolve_roots(default_install) -> tuple[Path, Path]:

    from . import paths

    cfg = load(default_install)
    write_example(default_install)

    install = Path((cfg[("paths", "install_dir")] or "").strip()
                   or default_install)
    configured = (cfg[("paths", "data_dir")] or "").strip()
    data = Path(configured) if configured else paths.default_player_dir()

    paths.set_install_dir(install)
    return install, data
