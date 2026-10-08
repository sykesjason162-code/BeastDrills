import configparser
import json
import logging
import re
from pathlib import Path

from . import settings

log = logging.getLogger(__name__)

API_VERSION = 1

SECTION_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
RESERVED_SECTIONS = frozenset({"paths", "dashboard", "session",
                               "scrimmage", "ui", "mods"})

def _game_root(install_dir) -> Path:

    return Path(install_dir).resolve().parents[2]

def registration_paths(install_dir) -> list:

    install = Path(install_dir)
    found = []
    seen = set()

    folder = install / "mods"
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            if path.stem.startswith("_"):
                continue
            found.append((path.stem, path))
            seen.add(path.stem.lower())

    try:
        root = _game_root(install)
    except IndexError:
        return found

    for name, value in _ini_mods_section(install).items():
        if name.lower() in seen:
            continue
        try:
            full = Path(value)
            full = (full if full.is_absolute() else root / full).resolve()
            full.relative_to(root)
        except (ValueError, OSError):
            continue
        if not full.is_file():
            continue
        found.append((name, full))
        seen.add(name.lower())
    return found

def _ini_mods_section(install_dir) -> dict:
    parser = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
    try:
        parser.read(Path(install_dir) / settings.FILENAME, encoding="utf-8")
    except (configparser.Error, OSError):
        return {}
    if not parser.has_section("mods"):
        return {}
    return {k: v.strip() for k, v in parser["mods"].items() if v.strip()}

def declared_settings(path) -> list:

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict) or data.get("api_version") != API_VERSION:
        return []
    out = []
    for entry in data.get("settings") or []:
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        if not isinstance(key, str) or not SECTION_PATTERN.match(key):
            continue
        if "default" not in entry:
            continue
        default = entry["default"]
        if not isinstance(default, (str, int, float, bool)):
            continue
        note = entry.get("note")
        out.append({"key": key, "default": default,
                    "note": note if isinstance(note, str) else None})
    return out

def _format(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)

def _coerce(raw: str, default):
    try:
        if isinstance(default, bool):
            return raw.strip().lower() in ("1", "true", "yes", "on")
        if isinstance(default, int):
            return int(raw)
        if isinstance(default, float):
            return float(raw)
    except ValueError:
        return default
    return raw

def sync(install_dir) -> dict:

    install = Path(install_dir)
    ini = install / settings.FILENAME
    resolved = {}

    registrations = registration_paths(install)
    if not registrations:
        return resolved

    parser = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
    try:
        if ini.is_file():
            parser.read(ini, encoding="utf-8")
    except (configparser.Error, OSError) as e:
        log.warning("%s could not be read (%s) -- mod settings left alone",
                    ini.name, e)
        return resolved

    additions = {}
    for name, path in registrations:
        declared = declared_settings(path)
        if not declared:
            continue
        if not SECTION_PATTERN.match(name) or name.lower() in RESERVED_SECTIONS:

            log.warning("mod %r cannot use that name as a settings section", name)
            continue

        values, missing = {}, []
        for entry in declared:
            key, default = entry["key"], entry["default"]
            if parser.has_option(name, key):

                values[key] = _coerce(parser.get(name, key).strip(), default)
            else:
                values[key] = default
                missing.append(entry)
        resolved[name] = values

        if missing:
            lines = []
            for entry in missing:
                if entry["note"]:
                    for line in entry["note"].split("\n"):
                        lines.append("# " + line)
                lines.append("{} = {}".format(entry["key"],
                                              _format(entry["default"])))
                lines.append("")
            additions[name] = lines

    if additions:

        try:
            text = ini.read_text(encoding="utf-8") if ini.is_file() else ""
            ini.write_text(_insert(text, additions), encoding="utf-8")
        except OSError as e:
            log.warning("could not add mod settings to %s: %s", ini.name, e)

    _write_resolved(install, resolved)
    return resolved

def _insert(text: str, additions: dict) -> str:

    lines = text.splitlines()

    ends = {}
    current, last_content = None, None
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current is not None:
                ends[current] = last_content
            current = stripped[1:-1].strip().lower()
            last_content = i
        elif stripped:
            last_content = i
    if current is not None:
        ends[current] = last_content

    for name in sorted(additions, key=lambda n: ends.get(n.lower(), len(lines)),
                       reverse=True):
        body = additions[name]
        at = ends.get(name.lower())
        if at is None:
            lines.extend([""] + ["[" + name + "]"] + body)
        else:
            lines[at + 1:at + 1] = body
    return "\n".join(lines) + "\n"

def _write_resolved(install_dir, resolved: dict) -> None:

    out = Path(install_dir) / "mods" / "_settings"
    try:
        out.mkdir(parents=True, exist_ok=True)
        for name, values in resolved.items():
            (out / (name + ".json")).write_text(
                json.dumps(values, indent=2), encoding="utf-8")
    except OSError as e:
        log.warning("could not write resolved mod settings: %s", e)
