"""JSON persistence: the interrupted dive and the logbook of records.

Plain JSON on purpose - a savegame should never be able to execute code.
The dive save is small because the whole cave regenerates from the seed.
"""
from __future__ import annotations

import json
import os

from engine import DIVING, Engine

SAVE_VERSION = 1
_HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(_HERE, "savegame.json")
RECORDS_PATH = os.path.join(_HERE, "records.json")


def has_save(path=SAVE_PATH):
    return os.path.isfile(path)


def delete_save(path=SAVE_PATH):
    try:
        os.remove(path)
    except OSError:
        pass


def save(engine, path=SAVE_PATH):
    sub = engine.sub
    data = {
        "version": SAVE_VERSION,
        "seed": engine.seed,
        "time": engine.time,
        "sub": {"x": sub.x, "y": sub.y, "vx": sub.vx, "vy": sub.vy,
                "facing": sub.facing},
        "hull": engine.hull,
        "oxygen": engine.oxygen,
        "battery": engine.battery,
        "lamp_on": engine.lamp_on,
        "max_depth": engine.max_depth,
        "boxes_found": engine.boxes_found,
        "mother": {"x": engine.mother.x, "y": engine.mother.y,
                   "state": engine.mother.state,
                   "agitation": engine.mother.agitation},
        "radio_fired": sorted(engine.radio.fired),
        "first_ping": engine._first_ping_done,
        "mother_called": engine._mother_called,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    return path


def load(path=SAVE_PATH, sound=None):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("version") != SAVE_VERSION:
        raise ValueError("сохранение от другой версии игры")

    engine = Engine(seed=data["seed"], sound=sound)
    sub = data["sub"]
    engine.sub.x, engine.sub.y = sub["x"], sub["y"]
    engine.sub.vx, engine.sub.vy = sub["vx"], sub["vy"]
    engine.sub.facing = sub["facing"]
    engine.hull = data["hull"]
    engine.oxygen = data["oxygen"]
    engine.battery = data["battery"]
    engine.lamp_on = data["lamp_on"]
    engine.time = data["time"]
    engine.max_depth = data["max_depth"]
    engine.boxes_found = list(data["boxes_found"])
    for box in engine.world.blackboxes:
        box["found"] = box["idx"] in engine.boxes_found
    mother = data["mother"]
    engine.mother.x, engine.mother.y = mother["x"], mother["y"]
    engine.mother.state = mother["state"]
    engine.mother.agitation = mother["agitation"]
    engine.radio.fired = set(data["radio_fired"])
    engine.radio.queue.clear()
    engine._first_ping_done = data["first_ping"]
    engine._mother_called = data["mother_called"]
    engine.state = DIVING
    return engine


# ------------------------------------------------------------------ records
def load_records(path=RECORDS_PATH):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (OSError, ValueError):
        return {"dives": 0, "returns": 0, "best_depth_m": 0,
                "best_time": None, "boxes_total": 0}


def update_records(engine, won, metres, path=RECORDS_PATH):
    rec = load_records(path)
    rec["dives"] = rec.get("dives", 0) + 1
    rec["best_depth_m"] = max(rec.get("best_depth_m", 0), metres)
    rec["boxes_total"] = rec.get("boxes_total", 0) + len(engine.boxes_found)
    if won:
        rec["returns"] = rec.get("returns", 0) + 1
        best = rec.get("best_time")
        if best is None or engine.time < best:
            rec["best_time"] = round(engine.time, 1)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rec, handle, ensure_ascii=False, indent=1)
    return rec
