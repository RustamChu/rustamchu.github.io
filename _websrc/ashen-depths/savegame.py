"""Human-readable JSON saves.

Entities are stored as a template key plus whatever changed during play, and
the map as one digit per tile, so a full save of a 72x42 floor is a few
kilobytes of text you can open in any editor. No pickle: a save file should
never be able to execute code when it is loaded.
"""
from __future__ import annotations

import json
import os

import tiles
from entity import make
from gamemap import GameMap
from message_log import MessageLog
from settings import LIGHT_LEVELS

SAVE_VERSION = 2
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "savegame.json")


def has_save(path=SAVE_PATH):
    return os.path.isfile(path)


def delete_save(path=SAVE_PATH):
    try:
        os.remove(path)
    except OSError:
        pass


# --------------------------------------------------------------------------- write
def save(engine, path=SAVE_PATH):
    gamemap = engine.gamemap
    data = {
        "version": SAVE_VERSION,
        "depth": gamemap.depth,
        "turn_count": engine.turn_count,
        "kill_count": engine.kill_count,
        "width": gamemap.width,
        "height": gamemap.height,
        "tiles": ["".join(str(t) for t in row) for row in gamemap.tiles],
        "explored": ["".join("1" if seen else "0" for seen in row)
                     for row in gamemap.explored],
        "downstairs": list(gamemap.downstairs),
        "player": engine.player.state(),
        "entities": [e.state() for e in gamemap.entities
                     if e is not engine.player],
        "log": engine.log.to_dict(),
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    return path


# --------------------------------------------------------------------------- read
def load(engine, path=SAVE_PATH):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("version") != SAVE_VERSION:
        raise ValueError("сохранение от другой версии игры")

    gamemap = GameMap(engine, data["width"], data["height"], data["depth"])
    gamemap.tiles = [[int(c) for c in row] for row in data["tiles"]]
    gamemap.explored = [[c == "1" for c in row] for row in data["explored"]]
    gamemap.light = [[LIGHT_LEVELS - 1] * gamemap.width
                     for _ in range(gamemap.height)]
    gamemap.downstairs = tuple(data["downstairs"])

    player = make("player")
    player.restore(data["player"])
    player.place(player.x, player.y, gamemap)

    for entity_data in data["entities"]:
        entity = make(entity_data["template"])
        entity.restore(entity_data)
        entity.place(entity.x, entity.y, gamemap)

    engine.player = player
    engine.gamemap = gamemap
    engine.world.depth = data["depth"]
    engine.turn_count = data["turn_count"]
    engine.kill_count = data["kill_count"]
    engine.log = MessageLog.from_dict(data["log"])
    engine.effects = []
    engine.player_died = False
    engine.victory = False
    gamemap.update_fov(player)
    return engine
