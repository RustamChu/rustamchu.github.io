"""Procedurally drawn tiles and glyphs - the project ships no image files.

Every tile is baked once at start-up into a small surface, for each of the
LIGHT_LEVELS torch brightness steps plus a "remembered" variant, and three
random variations so long corridors do not look like wallpaper. During play
the renderer only blits from that table, which keeps a full-screen redraw at
roughly 1200 blits per frame with no per-pixel work at all.
"""
from __future__ import annotations

import random

import pygame as pg

import tiles
from settings import (C_EMBER, C_FLOOR, C_FLOOR_DOT, C_MEMORY, C_PILLAR,
                      C_RUBBLE, C_STAIRS, C_WALL, C_WALL_EDGE, LIGHT_LEVELS,
                      TILE)

VARIANTS = 3
MEMORY_LEVEL = LIGHT_LEVELS          # index of the "explored but dark" set


def _mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def _shade(color, level):
    """Darken a colour for a torch level; the last level is cold memory.

    Remembered tiles keep their shape but lose their warmth: the eye reads
    them instantly as "seen earlier, not lit now".
    """
    if level >= MEMORY_LEVEL:
        grey = (color[0] + color[1] + color[2]) // 3
        cold = (int(grey * 0.42), int(grey * 0.46), int(grey * 0.62) + 8)
        return _mix(cold, C_MEMORY, 0.35)
    t = level / float(LIGHT_LEVELS - 1)
    warm = _mix(color, C_EMBER, 0.22 * (1.0 - t))       # firelight near you
    return _mix(warm, (12, 10, 14), 0.52 * t)


def _draw_wall(surf, rng, level):
    body = _shade(C_WALL, level)
    edge = _shade(C_WALL_EDGE, level)
    surf.fill(body)
    pg.draw.line(surf, edge, (0, 0), (TILE - 1, 0))
    pg.draw.line(surf, _shade((40, 34, 30), level), (0, TILE - 1),
                 (TILE - 1, TILE - 1))
    # a couple of block seams so walls read as masonry
    seam = _shade((58, 48, 42), level)
    y = TILE // 2
    pg.draw.line(surf, seam, (0, y), (TILE - 1, y))
    x = rng.randrange(4, TILE - 4)
    pg.draw.line(surf, seam, (x, 0), (x, y))
    x2 = rng.randrange(4, TILE - 4)
    pg.draw.line(surf, seam, (x2, y), (x2, TILE - 1))


def _draw_floor(surf, rng, level):
    surf.fill(_shade(C_FLOOR, level))
    dot = _shade(C_FLOOR_DOT, level)
    for _ in range(rng.randint(2, 5)):
        x, y = rng.randrange(2, TILE - 2), rng.randrange(2, TILE - 2)
        surf.set_at((x, y), dot)


def _draw_rubble(surf, rng, level):
    _draw_floor(surf, rng, level)
    chunk = _shade(C_RUBBLE, level)
    for _ in range(rng.randint(2, 4)):
        x, y = rng.randrange(3, TILE - 6), rng.randrange(3, TILE - 6)
        pg.draw.rect(surf, chunk, (x, y, rng.randint(2, 4), rng.randint(2, 3)))


def _draw_pillar(surf, rng, level):
    _draw_floor(surf, rng, level)
    body = _shade(C_PILLAR, level)
    dark = _shade((52, 44, 40), level)
    pg.draw.ellipse(surf, dark, (3, TILE - 8, TILE - 6, 6))
    pg.draw.rect(surf, body, (5, 3, TILE - 10, TILE - 7), border_radius=3)
    pg.draw.line(surf, _shade(C_WALL_EDGE, level), (6, 4), (6, TILE - 6))


def _draw_stairs(surf, rng, level):
    _draw_floor(surf, rng, level)
    gold = _shade(C_STAIRS, level)
    for i in range(3):
        w = TILE - 6 - i * 4
        pg.draw.rect(surf, gold, (3 + i * 2, 5 + i * 5, w, 3))


_DRAW = {
    tiles.WALL: _draw_wall,
    tiles.FLOOR: _draw_floor,
    tiles.STAIRS_DOWN: _draw_stairs,
    tiles.PILLAR: _draw_pillar,
    tiles.RUBBLE: _draw_rubble,
}


def build_tileset():
    """tileset[tile_id][light_level][variant] -> Surface."""
    tileset = {}
    for tile_id, draw in _DRAW.items():
        levels = []
        for level in range(LIGHT_LEVELS + 1):     # +1 for the memory variant
            variants = []
            for v in range(VARIANTS):
                rng = random.Random(tile_id * 977 + v * 31)
                surf = pg.Surface((TILE, TILE)).convert()
                draw(surf, rng, level)
                variants.append(surf)
            levels.append(variants)
        tileset[tile_id] = levels
    return tileset


# --------------------------------------------------------------------------- glyphs
class GlyphCache:
    """Renders and caches entity characters, dimmed to the torch level."""

    def __init__(self, font):
        self.font = font
        self._cache = {}

    def get(self, char, color, level=0):
        key = (char, color, level)
        cached = self._cache.get(key)
        if cached is None:
            shaded = _shade(color, level)
            cached = self.font.render(char, True, shaded)
            self._cache[key] = cached
        return cached
