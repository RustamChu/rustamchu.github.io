"""Procedural art - the project ships no image files.

Film grain, vignette, the little submersible with its warm porthole - all
drawn once at start-up. The atmosphere of the game is mostly *absence*: a
near-black screen where anything that glows earns its light.
"""
from __future__ import annotations

import math
import random

import pygame as pg

from settings import (C_HULL_GLASS, HEIGHT, SUB_R, VIEW_H, WIDTH)


def _mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def glow(surface, x, y, radius, color, alpha=90, layers=4):
    for i in range(layers, 0, -1):
        r = max(1, int(radius * i / layers))
        veil = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
        pg.draw.circle(veil, (*color, int(alpha / layers)), (r, r), r)
        surface.blit(veil, (int(x) - r, int(y) - r))


# ------------------------------------------------------------------ overlays
def make_grain_frames(count=5, alpha=13):
    """Coarse photographic noise, cycled per frame."""
    frames = []
    rng = random.Random(9)
    for _ in range(count):
        small = pg.Surface((WIDTH // 4, HEIGHT // 4))
        for y in range(small.get_height()):
            for x in range(small.get_width()):
                v = rng.randrange(0, 255)
                small.set_at((x, y), (v, v, v))
        frame = pg.transform.scale(small, (WIDTH, HEIGHT))
        frame.set_alpha(alpha)
        frames.append(frame)
    return frames


def make_vignette(strength=150):
    veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    cx, cy = WIDTH / 2, VIEW_H / 2
    max_d = math.hypot(cx, cy)
    step = 8
    for y in range(0, HEIGHT, step):
        for x in range(0, WIDTH, step):
            d = math.hypot(x - cx, y - cy) / max_d
            a = int(strength * max(0.0, d - 0.45) / 0.55)
            if a:
                pg.draw.rect(veil, (0, 0, 0, min(230, a)),
                             (x, y, step, step))
    return veil


def make_pulse_vignette():
    """A red-tinted ring used when She is near; alpha is set per frame."""
    veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    cx, cy = WIDTH / 2, VIEW_H / 2
    max_d = math.hypot(cx, cy)
    step = 8
    for y in range(0, HEIGHT, step):
        for x in range(0, WIDTH, step):
            d = math.hypot(x - cx, y - cy) / max_d
            a = int(140 * max(0.0, d - 0.35) / 0.65)
            if a:
                pg.draw.rect(veil, (120, 10, 16, min(150, a)),
                             (x, y, step, step))
    return veil


# ---------------------------------------------------------------------- sub
def make_sub_sprite():
    """The bathysphere, facing right. A steel teardrop with one warm eye."""
    w, h = SUB_R * 4 + 8, SUB_R * 3
    surf = pg.Surface((w, h), pg.SRCALPHA)
    cx, cy = w // 2, h // 2

    body = pg.Rect(0, 0, SUB_R * 3, SUB_R * 2)
    body.center = (cx, cy)
    pg.draw.ellipse(surf, (44, 52, 62), body)
    pg.draw.ellipse(surf, (70, 82, 96), body, 2)
    # top fin and keel
    pg.draw.polygon(surf, (38, 46, 56),
                    [(cx - 6, body.top + 2), (cx + 4, body.top - 7),
                     (cx + 10, body.top + 3)])
    pg.draw.rect(surf, (38, 46, 56),
                 (cx - 10, body.bottom - 3, 20, 5), border_radius=2)
    # rivet line
    for i in range(5):
        pg.draw.circle(surf, (86, 98, 112),
                       (body.left + 8 + i * 9, cy - 2), 1)
    # the porthole: the only warm thing in the whole ocean
    eye_x = body.right - 13
    glow(surf, eye_x, cy, 12, C_HULL_GLASS, alpha=150)
    pg.draw.circle(surf, (28, 30, 34), (eye_x, cy), 7)
    pg.draw.circle(surf, C_HULL_GLASS, (eye_x, cy), 5)
    pg.draw.circle(surf, (255, 250, 230), (eye_x - 1, cy - 1), 2)
    # propeller hub (blades are drawn live so they can spin)
    pg.draw.rect(surf, (60, 70, 82), (body.left - 6, cy - 3, 8, 6),
                 border_radius=2)
    return surf, (cx, cy), body.left - 4        # sprite, centre, prop x


# ------------------------------------------------------------------- panel
def make_panel_base(width, height):
    """Steel instrument board with rivets and a worn top edge."""
    surf = pg.Surface((width, height))
    for y in range(height):
        t = y / height
        surf.fill(_mix((26, 28, 33), (14, 15, 18), t), (0, y, width, 1))
    pg.draw.line(surf, (74, 80, 92), (0, 0), (width, 0), 2)
    pg.draw.line(surf, (8, 9, 11), (0, 2), (width, 2), 1)
    rng = random.Random(4)
    for x in range(14, width, 46):
        pg.draw.circle(surf, (58, 62, 70), (x, 10), 2)
        pg.draw.circle(surf, (58, 62, 70), (x, height - 8), 2)
    # a few scuffs
    for _ in range(30):
        x = rng.randrange(width)
        y = rng.randrange(6, height - 6)
        pg.draw.line(surf, (34, 37, 43), (x, y),
                     (x + rng.randint(2, 9), y), 1)
    return surf
