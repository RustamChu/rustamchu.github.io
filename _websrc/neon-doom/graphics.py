"""Procedural art generation - no image assets needed.

Every texture and sprite in the game is drawn with code at startup,
which keeps the project tiny and free of binary files.
"""
import math
import random

import pygame as pg

from settings import (TEXTURE_SIZE, WIDTH, HALF_HEIGHT, HEIGHT, SHADE_LEVELS,
                      FOG_MIN, C_BG_TOP, C_BG_HORIZON, C_FLOOR_NEAR, C_FLOOR_FAR)

T = TEXTURE_SIZE


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------- wall textures
def _brick_texture(base, mortar, glow):
    surf = pg.Surface((T, T))
    surf.fill(mortar)
    bh, bw = T // 8, T // 4
    for row in range(8):
        off = (row % 2) * bw // 2
        for col in range(-1, 5):
            rect = pg.Rect(col * bw + off + 3, row * bh + 3, bw - 6, bh - 6)
            pg.draw.rect(surf, base, rect, border_radius=4)
            pg.draw.rect(surf, glow, rect, 2, border_radius=4)
    return surf


def _panel_texture(base, edge, rivet):
    surf = pg.Surface((T, T))
    surf.fill(base)
    for i in range(2):
        for j in range(2):
            rect = pg.Rect(i * T // 2 + 8, j * T // 2 + 8, T // 2 - 16, T // 2 - 16)
            pg.draw.rect(surf, _lerp(base, (255, 255, 255), 0.12), rect, border_radius=10)
            pg.draw.rect(surf, edge, rect, 3, border_radius=10)
            for (rx, ry) in [rect.topleft, rect.topright, rect.bottomleft, rect.bottomright]:
                pg.draw.circle(surf, rivet, (rx, ry), 6)
    return surf


def _stripe_texture(c1, c2, glow):
    surf = pg.Surface((T, T))
    surf.fill(c1)
    for k in range(-T, T * 2, 48):
        pg.draw.polygon(surf, c2, [(k, T), (k + 48, T), (k + 48 + T, 0), (k + T, 0)])
    for k in range(-T, T * 2, 48):
        pg.draw.line(surf, glow, (k, T), (k + T, 0), 4)
    pg.draw.rect(surf, glow, (0, 0, T, T), 4)
    return surf


def _circuit_texture(base, line, node):
    rnd = random.Random(42)
    surf = pg.Surface((T, T))
    surf.fill(base)
    for _ in range(26):
        x, y = rnd.randrange(10, T - 10), rnd.randrange(10, T - 10)
        length = rnd.randrange(30, 100)
        horizontal = rnd.random() < 0.5
        end = (min(T - 8, x + length), y) if horizontal else (x, min(T - 8, y + length))
        pg.draw.line(surf, line, (x, y), end, 3)
        pg.draw.circle(surf, node, (x, y), 5)
        pg.draw.circle(surf, node, end, 5)
    pg.draw.rect(surf, line, (0, 0, T, T), 5)
    return surf


def _slab_texture(base, crack, glow):
    surf = pg.Surface((T, T))
    surf.fill(base)
    sh = T // 4
    for row in range(4):
        rect = pg.Rect(4, row * sh + 4, T - 8, sh - 8)
        pg.draw.rect(surf, _lerp(base, (0, 0, 0), 0.25), rect, border_radius=6)
        pg.draw.rect(surf, glow, rect, 2, border_radius=6)
        pg.draw.line(surf, crack, (rect.left + 20, rect.centery),
                     (rect.right - 20, rect.centery), 1)
    return surf


def make_shaded_set(texture, levels=SHADE_LEVELS):
    """Pre-bake `levels` darkened copies of a texture.

    Shading every wall column at runtime costs one surface fill per column
    (640 per frame at this resolution). Baking the brightness steps once at
    startup turns that into a plain lookup and roughly doubles the frame rate.
    """
    variants = []
    for k in range(levels):
        t = (k + 0.5) / levels
        v = int(255 - (255 - FOG_MIN) * t)
        shaded = texture.copy()
        shaded.fill((v, v, min(255, v + 30)), special_flags=pg.BLEND_RGB_MULT)
        variants.append(shaded)
    return variants


def make_wall_textures():
    """Returns {texture_id: [brightest ... darkest]}."""
    base = {
        1: _brick_texture((150, 30, 110), (30, 8, 40), (255, 90, 200)),
        2: _panel_texture((20, 60, 90), (80, 240, 255), (160, 250, 255)),
        3: _stripe_texture((120, 50, 10), (230, 120, 20), (255, 210, 90)),
        4: _circuit_texture((10, 50, 35), (60, 230, 130), (180, 255, 190)),
        5: _slab_texture((60, 25, 120), (140, 90, 220), (190, 130, 255)),
    }
    return {key: make_shaded_set(tex) for key, tex in base.items()}


# ---------------------------------------------------------------- sky & floor
def make_sky():
    """Retro-wave sky: gradient, stars and a striped sun. Twice screen width."""
    w, h = WIDTH * 2, HALF_HEIGHT
    sky = pg.Surface((w, h))
    for y in range(h):
        sky.fill(_lerp(C_BG_TOP, C_BG_HORIZON, (y / h) ** 1.6), (0, y, w, 1))
    rnd = random.Random(7)
    for _ in range(220):
        x, y = rnd.randrange(w), rnd.randrange(int(h * 0.75))
        r = rnd.choice((1, 1, 1, 2))
        pg.draw.circle(sky, (255, 255, 255), (x, y), r)
    # two suns so the seam is invisible when the sky wraps
    for cx in (w // 4, w // 4 + w // 2):
        cy, radius = int(h * 0.8), int(h * 0.42)
        sun = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
        for i in range(radius, 0, -1):
            color = _lerp((255, 230, 120), (255, 60, 140), i / radius)
            pg.draw.circle(sun, color, (radius, radius), i)
        # horizontal cut-outs, the classic synthwave sun
        for k in range(6):
            y0 = radius + 8 + k * 14
            pg.draw.rect(sun, (0, 0, 0, 0), (0, y0, radius * 2, 4 + k))
        sky.blit(sun, (cx - radius, cy - radius))
    return sky


def make_floor():
    floor = pg.Surface((WIDTH, HEIGHT - HALF_HEIGHT))
    h = floor.get_height()
    for y in range(h):
        floor.fill(_lerp(C_FLOOR_FAR, C_FLOOR_NEAR, (y / h) ** 1.3), (0, y, WIDTH, 1))
    # neon grid lines fading into the distance
    for k in range(1, 14):
        y = int(h * (k / 14) ** 2.2)
        line_color = _lerp(C_FLOOR_FAR, (90, 60, 160), min(1.0, 0.15 + k / 14))
        pg.draw.line(floor, line_color, (0, y), (WIDTH, y), 1 if k < 8 else 2)
    return floor


# ---------------------------------------------------------------- demon sprites
def _demon_base(size, body_a, body_b, eye_color, frame=0, attack=False, pain=False):
    s = size
    surf = pg.Surface((s, s), pg.SRCALPHA)
    cx, cy = s // 2, int(s * 0.55)
    r = int(s * 0.30)
    cy += int(math.sin(frame * math.pi) * s * 0.02)
    # legs
    leg_off = int(s * 0.05) if frame % 2 else -int(s * 0.05)
    for sign in (-1, 1):
        lx = cx + sign * int(r * 0.55) + (leg_off * sign if not attack else 0)
        pg.draw.ellipse(surf, _lerp(body_b, (0, 0, 0), 0.3),
                        (lx - s // 14, cy + r - s // 20, s // 7, s // 6))
    # body: radial gradient
    for i in range(r, 0, -2):
        pg.draw.circle(surf, _lerp(body_a, body_b, i / r), (cx, cy), i)
    # horns
    for sign in (-1, 1):
        base_x = cx + sign * int(r * 0.6)
        tip = (cx + sign * int(r * 1.05), cy - int(r * 1.35))
        pg.draw.polygon(surf, (90, 250, 255),
                        [(base_x - s // 20, cy - int(r * 0.7)),
                         (base_x + s // 20, cy - int(r * 0.55)), tip])
    # eyes
    er = max(3, s // 16)
    for sign in (-1, 1):
        ex, ey = cx + sign * int(r * 0.42), cy - int(r * 0.25)
        pg.draw.circle(surf, eye_color, (ex, ey), er)
        pg.draw.circle(surf, (20, 0, 20), (ex, ey), max(2, er // 2))
    # mouth
    mouth_h = int(r * (0.55 if attack else 0.28))
    mouth = pg.Rect(0, 0, int(r * 0.9), mouth_h)
    mouth.center = (cx, cy + int(r * 0.45))
    pg.draw.ellipse(surf, (25, 0, 25), mouth)
    for k in range(4):
        tx = mouth.left + 6 + k * (mouth.width - 12) // 3
        pg.draw.polygon(surf, (255, 255, 255),
                        [(tx - 4, mouth.top + 2), (tx + 4, mouth.top + 2),
                         (tx, mouth.top + mouth_h // 2)])
    if attack:
        for sign in (-1, 1):  # claws
            ax = cx + sign * int(r * 1.15)
            ay = cy + int(r * 0.1)
            for k in range(3):
                pg.draw.line(surf, (255, 240, 120), (ax, ay),
                             (ax + sign * s // 10, ay - s // 14 + k * s // 16), 4)
    if pain:
        # white silhouette flash, built from the sprite's own alpha mask
        flash = pg.mask.from_surface(surf).to_surface(
            setcolor=(255, 255, 255, 130), unsetcolor=(0, 0, 0, 0))
        surf.blit(flash, (0, 0))
    return surf


_DEMON_CACHE = {}


def make_demon_frames(scheme=0):
    """Animation frames for one demon colour scheme (cached and shared)."""
    if scheme in _DEMON_CACHE:
        return _DEMON_CACHE[scheme]

    palettes = [
        ((255, 90, 200), (120, 10, 90), (255, 230, 90)),   # pink brute
        ((110, 240, 255), (10, 70, 120), (255, 120, 80)),  # cyan stalker
        ((255, 170, 60), (150, 50, 10), (150, 255, 120)),  # orange imp
    ]
    a, b, eye = palettes[scheme % len(palettes)]
    s = 256
    frames = {
        "walk": [_demon_base(s, a, b, eye, frame=f) for f in (0, 1)],
        "attack": [_demon_base(s, a, b, eye, frame=0, attack=True)],
        "pain": [_demon_base(s, a, b, eye, frame=0, pain=True)],
    }
    death = []
    base = frames["walk"][0]
    for k in range(5):
        t = k / 4
        img = pg.transform.smoothscale(
            base, (int(s * (1 + t * 0.4)), max(8, int(s * (1 - t * 0.85)))))
        canvas = pg.Surface((img.get_width(), s), pg.SRCALPHA)
        canvas.blit(img, (0, s - img.get_height()))
        canvas.set_alpha(int(255 * (1 - t * 0.55)))
        death.append(canvas)
    frames["death"] = death

    _DEMON_CACHE[scheme] = frames
    return frames


# ---------------------------------------------------------------- pickups
def make_gem_frames():
    frames = []
    s = 128
    for k in range(4):
        surf = pg.Surface((s, s), pg.SRCALPHA)
        cx, cy = s // 2, s // 2
        w = int(s * 0.30 * abs(math.cos(k * math.pi / 4)) + s * 0.06)
        h = int(s * 0.38)
        pts = [(cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy)]
        pg.draw.polygon(surf, (60, 235, 255), pts)
        pg.draw.polygon(surf, (200, 255, 255), pts, 3)
        pg.draw.line(surf, (255, 255, 255), (cx, cy - h), (cx, cy + h), 2)
        glow = pg.Surface((s, s), pg.SRCALPHA)
        pg.draw.circle(glow, (60, 235, 255, 40), (cx, cy), int(s * 0.45))
        surf.blit(glow, (0, 0))
        frames.append(surf)
    return frames


def make_health_frames():
    frames = []
    s = 128
    for k in range(2):
        surf = pg.Surface((s, s), pg.SRCALPHA)
        pulse = 1.0 + 0.06 * k
        box = pg.Rect(0, 0, int(s * 0.62 * pulse), int(s * 0.5 * pulse))
        box.center = (s // 2, int(s * 0.62))
        pg.draw.rect(surf, (235, 240, 255), box, border_radius=12)
        pg.draw.rect(surf, (255, 70, 110), box, 4, border_radius=12)
        cw = box.width // 5
        cx, cy = box.center
        pg.draw.rect(surf, (255, 70, 110), (cx - cw // 2, cy - cw * 3 // 2, cw, cw * 3))
        pg.draw.rect(surf, (255, 70, 110), (cx - cw * 3 // 2, cy - cw // 2, cw * 3, cw))
        frames.append(surf)
    return frames


# ---------------------------------------------------------------- weapon
def make_gun_frames():
    """Neon blaster seen from first person. Frame 0 is idle, 1-3 are the shot."""
    w, h = 420, 380
    frames = []
    for stage in range(4):
        surf = pg.Surface((w, h), pg.SRCALPHA)
        recoil = (0, 6, 14, 6)[stage]
        cx = w // 2
        top = 70 + recoil
        # barrel
        pg.draw.polygon(surf, (35, 25, 70),
                        [(cx - 46, h), (cx - 26, top), (cx + 26, top), (cx + 46, h)])
        pg.draw.polygon(surf, (90, 240, 255),
                        [(cx - 46, h), (cx - 26, top), (cx + 26, top), (cx + 46, h)], 4)
        # energy cells
        for k in range(3):
            y = top + 70 + k * 80
            pg.draw.rect(surf, (255, 80, 180), (cx - 34, y, 68, 26), border_radius=8)
            pg.draw.rect(surf, (255, 200, 240), (cx - 34, y, 68, 26), 2, border_radius=8)
        # muzzle
        pg.draw.rect(surf, (20, 15, 45), (cx - 34, top - 16, 68, 26), border_radius=6)
        pg.draw.rect(surf, (90, 240, 255), (cx - 34, top - 16, 68, 26), 3, border_radius=6)
        if stage in (1, 2):
            size = 90 if stage == 1 else 130
            flash = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
            for i, (color, alpha) in enumerate([((255, 255, 200), 230),
                                                ((255, 200, 90), 160),
                                                ((255, 90, 180), 90)]):
                rad = size - i * size // 4
                pts = []
                for a in range(12):
                    ang = a * math.pi / 6
                    rr = rad if a % 2 == 0 else rad // 2
                    pts.append((size + rr * math.cos(ang), size + rr * math.sin(ang)))
                pg.draw.polygon(flash, (*color, alpha), pts)
            surf.blit(flash, (cx - size, top - 30 - size))
        frames.append(surf)
    return frames


# ---------------------------------------------------------------- misc ui
def make_vignette():
    v = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    for i in range(120):
        alpha = int(90 * (i / 120) ** 2)
        pg.draw.rect(v, (10, 0, 25, alpha), (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 1)
    return v
