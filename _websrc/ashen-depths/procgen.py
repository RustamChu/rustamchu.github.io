"""Procedural dungeon generation.

Rooms come from a BSP (binary space partition): the floor is split
recursively into ever smaller regions, each leaf gets a room carved into it,
and corridors then join sibling regions on the way back up the tree. Because
siblings are always neighbours in space, the result is fully connected by
construction - no flood fill or repair pass needed - and rooms are spread
evenly instead of clumping the way random placement does.
"""
from __future__ import annotations

import random

import tiles
from entity import make
from gamemap import GameMap
from settings import (BSP_DEPTH, MAP_H, MAP_W, MAX_DEPTH, MAX_ITEMS_BY_DEPTH,
                      MAX_MONSTERS_BY_DEPTH, ROOM_MIN)

# what may appear, keyed by the first depth it shows up on
MONSTER_CHANCES = {
    1: [("rat", 80)],
    2: [("ghoul", 40)],
    3: [("skeleton", 30), ("rat", 50)],
    4: [("cultist", 25)],
    5: [("wraith", 25), ("ghoul", 30)],
    6: [("ogre", 20)],
    7: [("warden", 15)],
}

ITEM_CHANCES = {
    1: [("potion", 35)],
    2: [("dagger", 12), ("leather", 12)],
    3: [("scroll_confusion", 12)],
    4: [("scroll_lightning", 20), ("sword", 10)],
    5: [("scroll_fireball", 20), ("chain", 12)],
    7: [("axe", 10), ("plate", 8)],
}


class Rect:
    def __init__(self, x, y, w, h):
        self.x1, self.y1 = x, y
        self.x2, self.y2 = x + w, y + h

    @property
    def center(self):
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    def inner_tiles(self):
        for y in range(self.y1 + 1, self.y2 - 1):
            for x in range(self.x1 + 1, self.x2 - 1):
                yield x, y


# --------------------------------------------------------------------------- bsp
def _split(region, depth, rng, rooms):
    """Recursively split a region and carve one room per leaf."""
    x, y, w, h = region
    can_split_h = h >= ROOM_MIN * 2
    can_split_v = w >= ROOM_MIN * 2

    if depth > 0 and (can_split_h or can_split_v):
        if can_split_h and can_split_v:
            horizontal = rng.random() < 0.5
        else:
            horizontal = can_split_h

        if horizontal:
            cut = rng.randint(ROOM_MIN, h - ROOM_MIN)
            left = _split((x, y, w, cut), depth - 1, rng, rooms)
            right = _split((x, y + cut, w, h - cut), depth - 1, rng, rooms)
        else:
            cut = rng.randint(ROOM_MIN, w - ROOM_MIN)
            left = _split((x, y, cut, h), depth - 1, rng, rooms)
            right = _split((x + cut, y, w - cut, h), depth - 1, rng, rooms)
        return (left, right)

    # leaf: place a room somewhere inside the region, with a little margin
    room_w = rng.randint(ROOM_MIN, max(ROOM_MIN, w - 1))
    room_h = rng.randint(ROOM_MIN, max(ROOM_MIN, h - 1))
    room_x = x + rng.randint(0, max(0, w - room_w))
    room_y = y + rng.randint(0, max(0, h - room_h))
    room = Rect(room_x, room_y, room_w, room_h)
    rooms.append(room)
    return room


def _rooms_of(node):
    """Collect every room under a BSP node."""
    if isinstance(node, Rect):
        return [node]
    return _rooms_of(node[0]) + _rooms_of(node[1])


def _connect(node, dungeon, rng):
    """Walk back up the tree joining each pair of sibling regions."""
    if isinstance(node, Rect):
        return
    left, right = node
    _connect(left, dungeon, rng)
    _connect(right, dungeon, rng)

    a = rng.choice(_rooms_of(left)).center
    b = rng.choice(_rooms_of(right)).center
    _carve_corridor(dungeon, a, b, rng)


def _carve_corridor(dungeon, a, b, rng):
    x1, y1 = a
    x2, y2 = b
    if rng.random() < 0.5:
        corner = (x2, y1)
    else:
        corner = (x1, y2)

    for x, y in _line(x1, y1, *corner):
        dungeon.tiles[y][x] = tiles.FLOOR
    for x, y in _line(corner[0], corner[1], x2, y2):
        dungeon.tiles[y][x] = tiles.FLOOR


def _line(x1, y1, x2, y2):
    if x1 == x2:
        step = 1 if y2 >= y1 else -1
        for y in range(y1, y2 + step, step):
            yield x1, y
    else:
        step = 1 if x2 >= x1 else -1
        for x in range(x1, x2 + step, step):
            yield x, y1


# --------------------------------------------------------------------------- decor
def _decorate(dungeon, room, rng):
    """Small touches so rooms are not identical rectangles."""
    if room.width >= 9 and room.height >= 7 and rng.random() < 0.45:
        # a ring of pillars
        for x in (room.x1 + 2, room.x2 - 3):
            for y in (room.y1 + 2, room.y2 - 3):
                dungeon.tiles[y][x] = tiles.PILLAR
    if rng.random() < 0.5:
        for _ in range(rng.randint(2, 7)):
            x = rng.randint(room.x1 + 1, room.x2 - 2)
            y = rng.randint(room.y1 + 1, room.y2 - 2)
            if dungeon.tiles[y][x] == tiles.FLOOR:
                dungeon.tiles[y][x] = tiles.RUBBLE


# --------------------------------------------------------------------------- spawning
def _table_for_depth(table, depth):
    """Accumulate every entry whose depth is at or below the current floor."""
    weights = {}
    for floor, entries in sorted(table.items()):
        if floor > depth:
            break
        for key, weight in entries:
            weights[key] = weight
    return weights


def _amount_for_depth(pairs, depth):
    amount = 0
    for floor, value in pairs:
        if floor > depth:
            break
        amount = value
    return amount


def _weighted_choice(weights, rng):
    total = sum(weights.values())
    if total <= 0:
        return None
    roll = rng.uniform(0, total)
    upto = 0.0
    for key, weight in weights.items():
        upto += weight
        if roll <= upto:
            return key
    return key


def _populate(dungeon, rooms, depth, rng):
    monsters = _table_for_depth(MONSTER_CHANCES, depth)
    loot = _table_for_depth(ITEM_CHANCES, depth)
    max_monsters = _amount_for_depth(MAX_MONSTERS_BY_DEPTH, depth)
    max_items = _amount_for_depth(MAX_ITEMS_BY_DEPTH, depth)

    occupied = set()
    for room in rooms[1:]:                      # never in the starting room
        free = [(x, y) for x, y in room.inner_tiles()
                if dungeon.tiles[y][x] in (tiles.FLOOR, tiles.RUBBLE)]
        if not free:
            continue
        rng.shuffle(free)

        for _ in range(rng.randint(0, max_monsters)):
            if not free:
                break
            x, y = free.pop()
            if (x, y) in occupied:
                continue
            key = _weighted_choice(monsters, rng)
            if key:
                make(key).place(x, y, dungeon)
                occupied.add((x, y))

        for _ in range(rng.randint(0, max_items)):
            if not free:
                break
            x, y = free.pop()
            key = _weighted_choice(loot, rng)
            if key:
                make(key).place(x, y, dungeon)


# --------------------------------------------------------------------------- entry
def generate_dungeon(engine, depth, seed=None):
    rng = random.Random(seed)
    dungeon = GameMap(engine, MAP_W, MAP_H, depth)

    rooms = []
    tree = _split((1, 1, MAP_W - 2, MAP_H - 2), BSP_DEPTH, rng, rooms)

    for room in rooms:
        for x, y in room.inner_tiles():
            dungeon.tiles[y][x] = tiles.FLOOR

    # decorate first, connect second: corridors then carve straight through
    # any pillar that would otherwise seal a doorway
    for room in rooms:
        _decorate(dungeon, room, rng)

    _connect(tree, dungeon, rng)

    rng.shuffle(rooms)
    dungeon.player_start = rooms[0].center

    # the exit goes as far from the entrance as the layout allows
    last = max(rooms[1:], key=lambda r: (r.center[0] - rooms[0].center[0]) ** 2
               + (r.center[1] - rooms[0].center[1]) ** 2)
    ex, ey = last.center
    if depth >= MAX_DEPTH:
        make("crown").place(ex, ey, dungeon)
        dungeon.tiles[ey][ex] = tiles.FLOOR
    else:
        dungeon.tiles[ey][ex] = tiles.STAIRS_DOWN
    dungeon.downstairs = (ex, ey)

    # keep the start tile clean
    sx, sy = dungeon.player_start
    dungeon.tiles[sy][sx] = tiles.FLOOR

    _populate(dungeon, rooms, depth, rng)
    return dungeon
