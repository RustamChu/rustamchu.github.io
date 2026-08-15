"""Procedural space art - the project ships no image files.

The starfield with its nebulae is baked once per course seed; planets are
baked per level. Glow is layered translucent circles - cheap, and it reads
beautifully on a dark background.
"""
from __future__ import annotations

import math
import random

import pygame as pg

from settings import (C_ASTEROID, C_BG_BOTTOM, C_BG_TOP, C_BLACKHOLE,
                      C_PULSAR, C_STAR, C_WORMHOLE, HEIGHT, PLANET_SCHEMES,
                      WIDTH)


def _mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def glow(surface, x, y, radius, color, alpha=90, layers=4):
    """Soft halo out of a few translucent circles."""
    for i in range(layers, 0, -1):
        r = int(radius * i / layers)
        veil = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
        pg.draw.circle(veil, (*color, int(alpha / layers)), (r, r), r)
        surface.blit(veil, (int(x) - r, int(y) - r))


# ------------------------------------------------------------------ starfield
def make_background(seed):
    surf = pg.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        surf.fill(_mix(C_BG_TOP, C_BG_BOTTOM, y / HEIGHT), (0, y, WIDTH, 1))
    rng = random.Random(seed)

    # nebulae: big soft blobs of faint colour
    for _ in range(5):
        color = rng.choice(((60, 40, 110), (30, 70, 110), (100, 40, 90)))
        cx, cy = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        glow(surf, cx, cy, rng.randint(140, 300), color, alpha=38, layers=5)

    # three depths of stars
    for count, size, bright in ((160, 1, 0.5), (70, 1, 0.85), (26, 2, 1.0)):
        for _ in range(count):
            x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
            color = _mix((90, 95, 130), C_STAR, bright)
            pg.draw.circle(surf, color, (x, y), size)
    # a couple of tiny crosses for the brightest stars
    for _ in range(8):
        x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        pg.draw.line(surf, C_STAR, (x - 4, y), (x + 4, y))
        pg.draw.line(surf, C_STAR, (x, y - 4), (x, y + 4))
    return surf


# -------------------------------------------------------------------- bodies
def bake_planet(body):
    """A shaded ball with bands and a rim glow, on an SRCALPHA canvas."""
    r = int(body.r)
    pad = r + 26
    surf = pg.Surface((pad * 2, pad * 2), pg.SRCALPHA)
    light, dark = PLANET_SCHEMES[body.scheme % len(PLANET_SCHEMES)]
    glow(surf, pad, pad, r + 22, light, alpha=70)

    rng = random.Random(int(body.x * 31 + body.y * 7))
    for i in range(r, 0, -1):
        t = i / r
        pg.draw.circle(surf, _mix(light, dark, t * t), (pad, pad), i)
    # latitude bands
    band_count = rng.randint(2, 4)
    for _ in range(band_count):
        band_y = rng.uniform(-0.7, 0.7)
        half = int(math.sqrt(max(0.0, 1 - band_y * band_y)) * r)
        y = pad + int(band_y * r)
        shade = _mix(dark, (0, 0, 0), 0.25)
        pg.draw.line(surf, shade, (pad - half, y), (pad + half, y),
                     rng.randint(2, 4))
    # terminator shadow on the right
    shadow = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
    pg.draw.circle(shadow, (8, 8, 18, 110), (int(r * 1.5), r), r)
    surf.blit(shadow, (pad - r, pad - r))
    pg.draw.circle(surf, _mix(light, (255, 255, 255), 0.35), (pad, pad), r, 2)
    return surf


def bake_asteroid(body):
    r = int(body.r)
    pad = r + 6
    surf = pg.Surface((pad * 2, pad * 2), pg.SRCALPHA)
    rng = random.Random(int(body.x * 13 + body.y * 5))
    points = []
    for k in range(8):
        angle = k * math.tau / 8
        rr = r * rng.uniform(0.75, 1.1)
        points.append((pad + rr * math.cos(angle), pad + rr * math.sin(angle)))
    pg.draw.polygon(surf, C_ASTEROID, points)
    pg.draw.polygon(surf, _mix(C_ASTEROID, (255, 255, 255), 0.3), points, 1)
    pg.draw.circle(surf, _mix(C_ASTEROID, (0, 0, 0), 0.35),
                   (pad - r // 3, pad + r // 4), max(2, r // 4))
    return surf


def bake_bodies(level):
    """{id(body): (Surface, offset)} for every solid thing on the level."""
    baked = {}
    for body in level.bodies:
        if body.kind == "planet":
            sprite = bake_planet(body)
        elif body.kind == "asteroid":
            sprite = bake_asteroid(body)
        else:
            continue                    # pulsars/holes are animated live
        baked[id(body)] = sprite
    return baked
