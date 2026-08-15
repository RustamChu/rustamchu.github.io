"""JSON save between holes: seed, current hole, scorecard. Tiny, because
every hole regenerates identically from the seed."""
from __future__ import annotations

import json
import os

from engine import AIM, Engine

SAVE_VERSION = 1
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "savegame.json")


def has_save(path=SAVE_PATH):
    return os.path.isfile(path)


def delete_save(path=SAVE_PATH):
    try:
        os.remove(path)
    except OSError:
        pass


def save(engine, path=SAVE_PATH):
    data = {
        "version": SAVE_VERSION,
        "seed": engine.seed,
        "hole_idx": engine.hole_idx,
        "strokes": engine.strokes,
        "done": engine.done,
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
    engine.strokes = data["strokes"]
    engine.done = data["done"]
    engine.hole_idx = data["hole_idx"]
    engine.level = engine.current_level()
    engine.ball = list(engine.level.start)
    engine.rest_point = tuple(engine.ball)
    engine.state = AIM
    return engine
