"""JSON records: best time and best-run ghost per stage code.

Plain JSON on purpose - a savegame should never be able to execute code.
Ghosts are 20 Hz position triplets; a minute-and-a-half run is ~30 KB.
"""
from __future__ import annotations

import json
import os

RECORDS_VERSION = 1
_HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS_PATH = os.path.join(_HERE, "records.json")


def _load(path=RECORDS_PATH):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) \
                or data.get("version") != RECORDS_VERSION:
            raise ValueError
        return data
    except (OSError, ValueError):
        return {"version": RECORDS_VERSION, "stages": {}}


def stage_record(code, path=RECORDS_PATH):
    """(best_ms, ghost_line, medal) for a stage code, or (None, None, "")."""
    entry = _load(path)["stages"].get(code)
    if not entry:
        return None, None, ""
    ghost = [tuple(p) for p in entry.get("ghost", [])]
    return entry.get("best_ms"), ghost or None, entry.get("medal", "")


def save_result(code, ms, ghost_line, medal, path=RECORDS_PATH):
    """Store a finished run if it beats the stored best. Returns True if
    the record table changed."""
    data = _load(path)
    entry = data["stages"].get(code)
    if entry and entry.get("best_ms") is not None \
            and entry["best_ms"] <= ms:
        return False
    data["stages"][code] = {
        "best_ms": ms,
        "medal": medal,
        "ghost": [list(p) for p in ghost_line],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)
    return True


def totals(path=RECORDS_PATH):
    """(stages_finished, golds) for the menu."""
    stages = _load(path)["stages"]
    golds = sum(1 for e in stages.values() if e.get("medal") == "золото")
    return len(stages), golds
