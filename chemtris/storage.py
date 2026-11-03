"""Saves settings and the progress record parents can review, as JSON.

Files live in the per-user data folder so they survive updates and the game
works from a read-only install. A damaged file is set aside and replaced
rather than stopping the game.
"""
import json
import os
import sys
import tempfile
import time

SESSIONS_KEPT = 50
ERRORS_KEPT = 100


def data_dir():
    override = os.environ.get("CHEMTRIS_DATA")
    if override:
        path = override
    elif sys.platform == "win32":
        path = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "ChemTris")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        path = os.path.join(base, "chemtris")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = os.path.join(tempfile.gettempdir(), "chemtris")
        os.makedirs(path, exist_ok=True)
    return path


def _load(name, default):
    path = os.path.join(data_dir(), name)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, type(default)):
            return data
        raise ValueError("unexpected structure")
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        try:
            os.replace(path, path + ".corrupt")
        except OSError:
            pass
        return default


def _save(name, data):
    path = os.path.join(data_dir(), name)
    temp = path + ".tmp"
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, ensure_ascii=False)
        os.replace(temp, path)
    except OSError as error:
        print(f"Could not save {name}: {error}", file=sys.stderr)


# ---- Settings -------------------------------------------------------------

DEFAULT_SETTINGS = {"music": True, "sound": True, "fullscreen": False, "language": "en"}


def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    settings.update({k: v for k, v in _load("settings.json", {}).items() if k in DEFAULT_SETTINGS})
    return settings


def save_settings(settings):
    _save("settings.json", settings)


# ---- Progress -------------------------------------------------------------

def empty_progress():
    return {"high_score": 0, "best_level": 0, "games": 0, "seconds": 0.0, "molecules": 0,
            "errors": 0, "rows": 0, "per_molecule": {}, "sessions": [], "error_log": []}


def load_progress():
    progress = empty_progress()
    data = _load("progress.json", {})
    for key, default in progress.items():
        value = data.get(key, default)
        if isinstance(value, type(default)) or (isinstance(default, float) and isinstance(value, int)):
            progress[key] = value
    return progress


def record_game(game, reason="gameover"):
    """Add one finished game to the record. Returns (progress, new_high_score)."""
    p = load_progress()
    st = game.stats
    new_best = game.score > p["high_score"] and game.score > 0
    p["high_score"] = max(p["high_score"], game.score)
    p["best_level"] = max(p["best_level"], game.level)
    p["games"] += 1
    p["seconds"] = round(p["seconds"] + st.seconds, 1)
    p["molecules"] += st.molecules
    p["errors"] += st.errors
    p["rows"] += st.rows
    for mid in set(st.built) | set(st.wrong):
        row = p["per_molecule"].get(mid) or {"built": 0, "errors": 0, "best": None}
        row["built"] = int(row.get("built", 0)) + st.built[mid]
        row["errors"] = int(row.get("errors", 0)) + st.wrong[mid]
        if mid in st.best_times:
            old = row.get("best")
            row["best"] = round(st.best_times[mid] if old is None else min(old, st.best_times[mid]), 1)
        p["per_molecule"][mid] = row
    stamp = time.strftime("%Y-%m-%d %H:%M")
    p["sessions"].append({"date": stamp, "score": game.score, "level": game.level,
                          "molecules": st.molecules, "errors": st.errors, "rows": st.rows,
                          "seconds": round(st.seconds, 1), "end": reason})
    p["sessions"] = p["sessions"][-SESSIONS_KEPT:]
    for level, mid, made in st.error_log:
        p["error_log"].append({"date": stamp, "level": level, "target": mid, "made": made})
    p["error_log"] = p["error_log"][-ERRORS_KEPT:]
    _save("progress.json", p)
    return p, new_best


def reset_progress():
    _save("progress.json", empty_progress())
