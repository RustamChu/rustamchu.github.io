"""Procedural art - the project ships no image files.

The look is a moonlit polar night done with one multiply-blended light
map: the world is painted fully lit, then dimmed to blue everywhere the
headlights are not. Everything here bakes the actors of that scene: the
car, the trees, the huts, the dashboard, the film grain.
"""
from __future__ import annotations

import math
import random

import pygame as pg

from settings import (C_CAR_BODY, C_CAR_ROOF, C_GHOST, C_HUT, C_TREE_BIRCH,
                      C_TREE_PINE, CAR_LEN, CAR_W, HEIGHT, WIDTH)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def glow(surface, x, y, radius, color, alpha=90, layers=4):
    for i in range(layers, 0, -1):
        r = max(1, int(radius * i / layers))
        veil = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
        pg.draw.circle(veil, (*color, int(alpha / layers)), (r, r), r)
        surface.blit(veil, (int(x) - r, int(y) - r))


# ------------------------------------------------------------------- the car
def make_car(body=C_CAR_BODY, roof=C_CAR_ROOF, ghost=False):
    """Rally hatchback, nose pointing right. Drawn 3x and downscaled so
    the tiny sprite comes out anti-aliased and readable."""
    L, W = 66, 36                       # 3x canvas
    surf = pg.Surface((L + 12, W + 12), pg.SRCALPHA)
    r = pg.Rect(6, 6, L, W)
    if ghost:
        pg.draw.rect(surf, (*C_GHOST, 46), r, border_radius=12)
        pg.draw.rect(surf, (*C_GHOST, 140), r, 3, border_radius=12)
        pg.draw.rect(surf, (*C_GHOST, 90),
                     (r.left + 22, r.top + 5, 20, W - 10), 2,
                     border_radius=5)
        out = pg.transform.smoothscale(
            surf, (int(CAR_LEN * 1.35) + 6, int(CAR_W * 1.5) + 6))
        return out
    dark = _mix(body, (0, 0, 0), 0.4)
    lite = _mix(body, (255, 255, 255), 0.35)
    # tyres
    for tx in (r.left + 8, r.right - 20):
        for ty in (r.top - 3, r.bottom - 5):
            pg.draw.rect(surf, (14, 14, 18), (tx, ty, 13, 8),
                         border_radius=3)
    # body wedge: wide at cabin, tapering to the nose
    pg.draw.polygon(surf, dark, (
        (r.left + 2, r.top + 4), (r.left + 30, r.top),
        (r.right - 10, r.top + 3), (r.right, r.top + 12),
        (r.right, r.bottom - 12), (r.right - 10, r.bottom - 3),
        (r.left + 30, r.bottom), (r.left + 2, r.bottom - 4)))
    pg.draw.polygon(surf, body, (
        (r.left + 4, r.top + 6), (r.left + 30, r.top + 2),
        (r.right - 11, r.top + 5), (r.right - 2, r.top + 13),
        (r.right - 2, r.bottom - 13), (r.right - 11, r.bottom - 5),
        (r.left + 30, r.bottom - 2), (r.left + 4, r.bottom - 6)))
    # rear spoiler
    pg.draw.rect(surf, dark, (r.left, r.top + 5, 5, W - 10),
                 border_radius=2)
    # glass: windscreen (front of roof) and rear window
    pg.draw.polygon(surf, (26, 34, 46), (
        (r.left + 40, r.top + 5), (r.left + 48, r.top + 7),
        (r.left + 48, r.bottom - 7), (r.left + 40, r.bottom - 5)))
    pg.draw.polygon(surf, (26, 34, 46), (
        (r.left + 16, r.top + 6), (r.left + 22, r.top + 5),
        (r.left + 22, r.bottom - 5), (r.left + 16, r.bottom - 6)))
    # roof with the race roundel
    roof_r = pg.Rect(r.left + 22, r.top + 4, 18, W - 8)
    pg.draw.rect(surf, roof, roof_r, border_radius=4)
    pg.draw.circle(surf, (240, 240, 240), roof_r.center, 7)
    num = pg.font.Font(None, 16).render("17", True, (30, 30, 34))
    surf.blit(num, num.get_rect(center=roof_r.center))
    # bonnet stripes
    pg.draw.line(surf, lite, (r.left + 50, r.centery - 5),
                 (r.right - 4, r.centery - 5), 2)
    pg.draw.line(surf, lite, (r.left + 50, r.centery + 5),
                 (r.right - 4, r.centery + 5), 2)
    # lights
    for ly in (r.top + 6, r.bottom - 10):
        pg.draw.rect(surf, (255, 248, 214), (r.right - 6, ly, 4, 5),
                     border_radius=1)
    for ly in (r.top + 7, r.bottom - 11):
        pg.draw.rect(surf, (225, 50, 40), (r.left + 1, ly, 3, 5))
    # mud along the sills
    rng = random.Random(7)
    for _ in range(26):
        mx = rng.randint(r.left + 6, r.left + 44)
        my = rng.choice((r.top + 2, r.top + 3, r.bottom - 3, r.bottom - 4))
        surf.set_at((mx, my), _mix(body, (44, 36, 28), 0.75))
    out = pg.transform.smoothscale(
        surf, (int(CAR_LEN * 1.35) + 6, int(CAR_W * 1.5) + 6))
    return out


# ------------------------------------------------------------------ scenery
def make_pine(size, rng):
    h = int(58 * size)
    w = int(38 * size)
    surf = pg.Surface((w, h), pg.SRCALPHA)
    tiers = 5
    base = _mix(C_TREE_PINE, (36, 52, 68), 0.4)
    for i in range(tiers):
        t = i / (tiers - 1)
        tier_w = w * (1.0 - 0.6 * t)
        y0 = h - 7 - (h - 16) * t
        left = (w - tier_w) / 2
        pts = [(left, y0), (left + tier_w, y0), (w / 2, y0 - h * 0.34)]
        pg.draw.polygon(surf, _mix(base, (14, 22, 32), t * 0.3), pts)
        # snow load on every tier
        pg.draw.line(surf, (172, 186, 208), (left + 2, y0 - 1),
                     (w / 2, y0 - h * 0.34 + 3), max(2, int(2.4 * size)))
        pg.draw.line(surf, (140, 154, 180),
                     (left + tier_w - 2, y0 - 1),
                     (w / 2, y0 - h * 0.34 + 3), max(1, int(1.4 * size)))
    pg.draw.circle(surf, (200, 210, 228), (w // 2, int(h * 0.09)),
                   max(2, int(2.2 * size)))
    pg.draw.rect(surf, (26, 20, 16), (w // 2 - 1, h - 8, 3, 8))
    return surf


def make_birch(size, rng):
    h = int(40 * size)
    surf = pg.Surface((16, h), pg.SRCALPHA)
    x = 8
    pg.draw.line(surf, C_TREE_BIRCH, (x, h), (x + rng.randint(-3, 3), 2), 2)
    for _ in range(5):
        y = rng.randint(2, h - 8)
        surf.set_at((x, y), (30, 30, 34))
        surf.set_at((x, y + 1), (30, 30, 34))
    for _ in range(4):
        y = rng.randint(4, h // 2)
        ex = x + rng.randint(-7, 7)
        pg.draw.line(surf, _mix(C_TREE_BIRCH, (0, 0, 0), 0.25),
                     (x, y), (ex, y - rng.randint(3, 8)), 1)
    return surf


def make_drift(size, rng):
    w = int(34 * size)
    surf = pg.Surface((w, w // 2), pg.SRCALPHA)
    pg.draw.ellipse(surf, (108, 122, 152), (0, 3, w, w // 2 - 3))
    pg.draw.ellipse(surf, (134, 148, 178), (3, 0, w - 6, w // 2 - 4))
    pg.draw.ellipse(surf, (156, 170, 198),
                    (6, 1, w - 12, w // 2 - 8))
    return surf


def make_rock(size, rng):
    w = int(22 * size)
    surf = pg.Surface((w, w), pg.SRCALPHA)
    pts = [(rng.uniform(0.0, 0.3) * w, w * 0.8),
           (w * 0.15, w * rng.uniform(0.25, 0.45)),
           (w * 0.5, w * 0.12),
           (w * 0.85, w * rng.uniform(0.3, 0.5)),
           (w * rng.uniform(0.7, 1.0), w * 0.8)]
    pg.draw.polygon(surf, (52, 58, 70), pts)
    pg.draw.line(surf, (150, 162, 186), pts[1], pts[2], 2)
    pg.draw.line(surf, (150, 162, 186), pts[2], pts[3], 2)
    return surf


def make_hut(rng):
    surf = pg.Surface((46, 36), pg.SRCALPHA)
    pg.draw.rect(surf, (34, 28, 24), (4, 14, 38, 20))
    for y in (18, 23, 28):
        pg.draw.line(surf, (24, 19, 16), (4, y), (42, y), 1)
    pg.draw.polygon(surf, (150, 162, 186),
                    ((0, 16), (23, 2), (46, 16)))
    pg.draw.polygon(surf, (110, 122, 148),
                    ((0, 16), (23, 2), (46, 16)), 1)
    pg.draw.rect(surf, (20, 16, 14), (30, 6, 5, 8))       # chimney
    pg.draw.rect(surf, C_HUT, (12, 20, 7, 7))             # the window
    pg.draw.line(surf, (34, 28, 24), (15, 20), (15, 27), 1)
    pg.draw.line(surf, (34, 28, 24), (12, 23), (19, 23), 1)
    return surf


def make_tent(rng):
    surf = pg.Surface((22, 18), pg.SRCALPHA)
    pg.draw.polygon(surf, (60, 72, 96), ((1, 17), (11, 2), (21, 17)))
    pg.draw.polygon(surf, (90, 104, 130), ((1, 17), (11, 2), (21, 17)), 1)
    pg.draw.polygon(surf, (30, 36, 48), ((8, 17), (11, 9), (14, 17)))
    return surf


def make_post():
    surf = pg.Surface((6, 22), pg.SRCALPHA)
    pg.draw.rect(surf, (200, 205, 215), (2, 0, 2, 22))
    pg.draw.rect(surf, (235, 130, 60), (2, 0, 2, 5))
    pg.draw.rect(surf, (235, 130, 60), (2, 9, 2, 5))
    return surf


def make_stick():
    """A roadside marker stick with reflective tape."""
    surf = pg.Surface((3, 14), pg.SRCALPHA)
    pg.draw.rect(surf, (140, 120, 90), (1, 0, 1, 14))
    pg.draw.rect(surf, (250, 250, 255), (0, 1, 3, 3))
    return surf


SCENERY_MAKERS = {"pine": make_pine, "birch": make_birch,
                  "drift": make_drift, "rock": make_rock}


def bake_scenery():
    """A few variants of each kind, keyed for cheap lookup."""
    baked = {}
    for kind, maker in SCENERY_MAKERS.items():
        for variant in range(4):
            rng = random.Random(kind + str(variant))
            for size_i, size in enumerate((0.8, 1.05, 1.3)):
                baked[(kind, variant, size_i)] = maker(size, rng)
    baked["hut"] = make_hut(random.Random(1))
    baked["tent"] = make_tent(random.Random(2))
    baked["post"] = make_post()
    baked["stick"] = make_stick()
    return baked


# ------------------------------------------------------------------ overlays
def make_grain_frames(count=5, alpha=10):
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


def make_vignette(view_h, strength=120):
    veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    cx, cy = WIDTH / 2, view_h / 2
    max_d = math.hypot(cx, cy)
    step = 8
    for y in range(0, HEIGHT, step):
        for x in range(0, WIDTH, step):
            d = math.hypot(x - cx, y - cy) / max_d
            a = int(strength * max(0.0, d - 0.52) / 0.48)
            if a:
                pg.draw.rect(veil, (4, 6, 14, min(200, a)),
                             (x, y, step, step))
    return veil


def make_headlight(reach=300, half_deg=24):
    """Light-map cone for the multiply blend, white-warm, pointing right."""
    size = reach * 2 + 20
    surf = pg.Surface((size, size))
    surf.fill((0, 0, 0))
    cx = cy = size // 2
    half = math.radians(half_deg)
    layers = 8
    for i in range(layers):
        k = 1.0 - i * 0.105
        r = reach * k
        bright = 0.26 + 0.115 * i
        col = _mix((0, 0, 0), (255, 248, 226), min(1.0, bright))
        pts = [(cx - 8, cy)]
        for stp in range(15):
            a = -half * k + 2 * half * k * stp / 14
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        pg.draw.polygon(surf, col, pts)
    # a soft pool right at the bumper
    for i in range(4):
        pg.draw.circle(surf, _mix((0, 0, 0), (185, 182, 176),
                                  0.26 + i * 0.09), (cx, cy), 30 - i * 7)
    return surf


# ---------------------------------------------------------------- dashboard
def make_dash(width, height):
    surf = pg.Surface((width, height))
    for y in range(height):
        t = y / height
        surf.fill(_mix((30, 30, 36), (16, 16, 20), t), (0, y, width, 1))
    pg.draw.line(surf, (90, 94, 106), (0, 0), (width, 0), 2)
    pg.draw.line(surf, (8, 9, 12), (0, 2), (width, 2), 1)
    rng = random.Random(4)
    for x in range(16, width, 52):
        pg.draw.circle(surf, (64, 66, 76), (x, 8), 2)
        pg.draw.circle(surf, (64, 66, 76), (x, height - 7), 2)
    for _ in range(26):
        x = rng.randrange(width)
        y = rng.randrange(6, height - 6)
        pg.draw.line(surf, (40, 41, 48), (x, y),
                     (x + rng.randint(2, 8), y), 1)
    return surf


def make_dial(radius, vmax, red_from=None):
    """A dial face: ticks and numbers for 0..vmax, soviet green backlight."""
    size = radius * 2 + 26
    surf = pg.Surface((size, size), pg.SRCALPHA)
    cx = cy = size // 2
    pg.draw.circle(surf, (12, 16, 14), (cx, cy), radius + 8)
    pg.draw.circle(surf, (70, 76, 86), (cx, cy), radius + 8, 2)
    font = pg.font.Font(None, 17)
    a0, a1 = math.radians(130), math.radians(410)
    major = vmax // 20
    for i in range(major + 1):
        val = i * 20
        a = a0 + (a1 - a0) * val / vmax
        x1 = cx + math.cos(a) * (radius - 2)
        y1 = cy + math.sin(a) * (radius - 2)
        x2 = cx + math.cos(a) * (radius - 9)
        y2 = cy + math.sin(a) * (radius - 9)
        col = (255, 110, 96) if red_from is not None and val >= red_from \
            else (150, 240, 170)
        pg.draw.line(surf, col, (x1, y1), (x2, y2), 2)
        if val % 40 == 0:
            img = font.render(str(val), True, (120, 190, 140))
            tx = cx + math.cos(a) * (radius - 19)
            ty = cy + math.sin(a) * (radius - 19)
            surf.blit(img, img.get_rect(center=(tx, ty)))
        if i < major:
            for sub in (0.5,):
                a = a0 + (a1 - a0) * (val + 20 * sub) / vmax
                x1 = cx + math.cos(a) * (radius - 2)
                y1 = cy + math.sin(a) * (radius - 2)
                x2 = cx + math.cos(a) * (radius - 6)
                y2 = cy + math.sin(a) * (radius - 6)
                pg.draw.line(surf, (90, 140, 104), (x1, y1), (x2, y2), 1)
    return surf
