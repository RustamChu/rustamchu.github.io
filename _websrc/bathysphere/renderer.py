"""Drawing: the phosphor view of the abyss and the amber instrument board.

The rule the whole look hangs on: light must be *earned*. The ocean renders
as almost nothing - gradient black, a little marine snow. Everything you see
is either your own sonar cooling on the phosphor, your lamp, the creatures'
own dim biology, or the station's far warm porthole. The bottom 148 px is
the opposite world: a riveted steel board of amber dials that is always lit,
always humming - the only cosy place for three kilometres straight down.
"""
from __future__ import annotations

import math
import random

import pygame as pg

from graphics import (glow, make_grain_frames, make_panel_base,
                      make_pulse_vignette, make_sub_sprite, make_vignette)
from settings import (BATTERY_MAX, BLIP_FADE, C_ABYSS_BOTTOM, C_ABYSS_TOP,
                      C_AMBER, C_AMBER_DIM, C_BIO, C_BOX, C_DANGER, C_DIM,
                      C_ECHO, C_ECHO_OLD, C_LAMP, C_SNOW, C_STATION, C_TEXT,
                      COST_PING, ECHO_FADE, GEYSER_LENGTH, HEIGHT, HULL_MAX,
                      METERS_PER_PX, OXYGEN_MAX, PANEL_H, PING_RADIUS, SUB_R,
                      VIEW_H, WIDTH, WORLD_H, WORLD_W)
LAMP_RANGE = 220.0
LAMP_HALF_ANGLE = 0.52


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_big = pg.font.Font(None, 96)
        self.font_mid = pg.font.Font(None, 40)
        self.font_ui = pg.font.Font(None, 26)
        self.font_small = pg.font.Font(None, 21)
        self.font_depth = pg.font.Font(None, 54)

        self.grain = make_grain_frames()
        self.vignette = make_vignette()
        self.pulse = make_pulse_vignette()
        self.panel_base = make_panel_base(WIDTH, PANEL_H)
        self.sub_sprite, self.sub_centre, self.prop_x = make_sub_sprite()

        # two baked gradients cross-faded with depth
        self.bg_shallow = self._gradient(C_ABYSS_TOP, C_ABYSS_BOTTOM)
        self.bg_deep = self._gradient((2, 3, 9), (0, 0, 2))
        self.light_top = self._surface_light()

        # marine snow: three parallax layers
        rng = random.Random(21)
        self.snow = []
        for layer, (par, count, size, alpha) in enumerate(
                (((0.35), 70, 1, 40), ((0.6), 55, 1, 60), ((1.0), 40, 2, 85))):
            for _ in range(count):
                self.snow.append([rng.uniform(0, WIDTH),
                                  rng.uniform(0, VIEW_H), par, size, alpha,
                                  rng.uniform(4, 11)])
        self.bubbles = []
        self.cam = None
        self.mother_prev = None
        self.mother_heading = 0.0

    # ----------------------------------------------------------- primitives
    @staticmethod
    def _gradient(top, bottom):
        surf = pg.Surface((WIDTH, VIEW_H))
        for y in range(VIEW_H):
            surf.fill(_mix(top, bottom, y / VIEW_H), (0, y, WIDTH, 1))
        return surf

    @staticmethod
    def _surface_light():
        """The last daylight, dying over the first few hundred metres."""
        surf = pg.Surface((WIDTH, 460), pg.SRCALPHA)
        for y in range(460):
            a = int(60 * (1 - y / 460) ** 1.6)
            surf.fill((70, 105, 135, a), (0, y, WIDTH, 1))
        return surf

    def _text(self, font, text, color, pos, center=False, glow_c=None):
        img = font.render(text, True, color)
        rect = img.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        if glow_c:
            halo = font.render(text, True, glow_c)
            halo.set_alpha(55)
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                self.screen.blit(halo, rect.move(dx, dy))
        self.screen.blit(img, rect)
        return rect

    def _wrap(self, font, text, max_w):
        words, lines, cur = text.split(" "), [], ""
        for w in words:
            probe = (cur + " " + w).strip()
            if font.size(probe)[0] <= max_w:
                cur = probe
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    # -------------------------------------------------------------- camera
    def _update_camera(self, engine, dt):
        tx = engine.sub.x - WIDTH / 2
        ty = engine.sub.y - VIEW_H / 2
        if self.cam is None:
            self.cam = [tx, ty]
        k = min(1.0, dt * 5.0)
        self.cam[0] += (tx - self.cam[0]) * k
        self.cam[1] += (ty - self.cam[1]) * k
        self.cam[0] = max(0, min(WORLD_W - WIDTH, self.cam[0]))
        self.cam[1] = max(0, min(WORLD_H - VIEW_H, self.cam[1]))
        if engine.shake > 0:
            self.cam[0] += random.uniform(-9, 9) * engine.shake
            self.cam[1] += random.uniform(-9, 9) * engine.shake

    def _to_screen(self, x, y):
        return x - self.cam[0], y - self.cam[1]

    # ============================================================ the dive
    def draw_game(self, engine, dt):
        t = engine.time
        self._update_camera(engine, dt)
        scr = self.screen

        # -- water ---------------------------------------------------------
        scr.blit(self.bg_shallow, (0, 0))
        dark = min(1.0, engine.sub.y / (WORLD_H * 0.55))
        deep = self.bg_deep.copy()
        deep.set_alpha(int(235 * dark))
        scr.blit(deep, (0, 0))
        if self.cam[1] < 460:
            self.light_top.set_alpha(int(255 * (1 - self.cam[1] / 460)))
            scr.blit(self.light_top, (0, -self.cam[1]))

        self._draw_snow(engine, dt, back=True)
        self._draw_bio(engine, t)

        layer = pg.Surface((WIDTH, VIEW_H), pg.SRCALPHA)
        self._draw_echoes(engine, layer)
        self._draw_pings(engine, layer)
        self._draw_blips(engine, layer)
        scr.blit(layer, (0, 0))

        self._draw_geysers(engine, t)
        self._draw_station(engine, t)
        self._draw_boxes(engine, t)
        if engine.lamp_on:
            self._draw_lamp(engine)
        self._draw_mother(engine, t)
        self._draw_sub(engine, dt, t)
        self._draw_snow(engine, dt, back=False)

        # -- air, dust, dread ----------------------------------------------
        scr.blit(self.vignette, (0, 0))
        if engine.heartbeat > 0.02:
            rate = 0.9 + 1.8 * engine.heartbeat
            wave = 0.5 + 0.5 * math.sin(t * math.tau * rate)
            self.pulse.set_alpha(int(150 * engine.heartbeat * wave))
            scr.blit(self.pulse, (0, 0))
        scr.blit(self.grain[int(t * 14) % len(self.grain)], (0, 0))

        self._draw_panel(engine, t)

    # ------------------------------------------------------------ ambience
    def _draw_snow(self, engine, dt, back):
        vx = engine.sub.vx * 0.15
        vy = engine.sub.vy * 0.15
        for p in self.snow:
            if back != (p[2] < 0.9):
                continue
            p[0] -= vx * p[2] * dt * 6
            p[1] -= vy * p[2] * dt * 6 - p[5] * dt
            x = p[0] % WIDTH
            y = p[1] % VIEW_H
            c = (*C_SNOW, p[4])
            veil = pg.Surface((p[3] * 2, p[3] * 2), pg.SRCALPHA)
            pg.draw.circle(veil, c, (p[3], p[3]), p[3])
            self.screen.blit(veil, (int(x), int(y)))

    def _draw_bio(self, engine, t):
        for bx, by, phase, size in engine.world.bio_lights:
            x, y = self._to_screen(bx, by)
            if -20 <= x <= WIDTH + 20 and -20 <= y <= VIEW_H + 20:
                pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 1.7 + phase))
                glow(self.screen, x, y, int((5 + 3 * pulse) * size * 0.7),
                     C_BIO, alpha=int(46 * pulse))
                pg.draw.circle(self.screen, _mix((30, 60, 80), C_BIO, pulse),
                               (int(x), int(y)), 1)

    # --------------------------------------------------------------- sonar
    def _draw_echoes(self, engine, layer):
        segs = engine.world.segments
        cx, cy = self.cam
        for idx, age in engine.sonar.echoes.items():
            x1, y1, x2, y2 = segs[idx]
            sx1, sy1 = x1 - cx, y1 - cy
            if not (-60 < sx1 < WIDTH + 60 and -60 < sy1 < VIEW_H + 60):
                continue
            k = age / ECHO_FADE
            color = _mix(C_ECHO, C_ECHO_OLD, k)
            alpha = int(255 * (1 - k) ** 0.85)
            if age < 0.7:                       # fresh echo blooms
                pg.draw.line(layer, (*color, alpha // 3),
                             (sx1, sy1), (x2 - cx, y2 - cy), 5)
            pg.draw.line(layer, (*color, alpha),
                         (sx1, sy1), (x2 - cx, y2 - cy), 2)

    def _draw_pings(self, engine, layer):
        for ping in engine.sonar.pings:
            x, y = self._to_screen(ping.x, ping.y)
            k = ping.r / PING_RADIUS
            alpha = int(130 * (1 - k))
            if alpha > 3 and ping.r > 4:
                pg.draw.circle(layer, (*C_ECHO, alpha), (int(x), int(y)),
                               int(ping.r), 2)
                if ping.r > 26:
                    pg.draw.circle(layer, (*C_ECHO, alpha // 3),
                                   (int(x), int(y)), int(ping.r - 9), 1)

    def _draw_blips(self, engine, layer):
        for blip in engine.sonar.blips:
            x, y = self._to_screen(blip["x"], blip["y"])
            if not (-40 < x < WIDTH + 40 and -40 < y < VIEW_H + 40):
                continue
            k = 1 - blip["age"] / BLIP_FADE
            a = int(230 * k)
            if blip["kind"] == "station":
                pg.draw.polygon(layer, (*C_STATION, a),
                                ((x, y - 8), (x + 8, y), (x, y + 8),
                                 (x - 8, y)), 2)
                label, color = "ГЛАГОЛ", C_STATION
            elif blip["kind"] == "box":
                pg.draw.rect(layer, (*C_BOX, a), (x - 5, y - 5, 10, 10), 2)
                label, color = "САМОПИСЕЦ", C_BOX
            else:
                pg.draw.polygon(layer, (*C_DANGER, a),
                                ((x, y - 9), (x + 9, y + 7), (x - 9, y + 7)),
                                2)
                label, color = "КОНТАКТ", C_DANGER
            img = self.font_small.render(label, True, color)
            img.set_alpha(a)
            layer.blit(img, (x - img.get_width() // 2, y + 12))

    # ------------------------------------------------------------- hazards
    def _draw_geysers(self, engine, t):
        rng = random.Random(int(t * 20))
        for g in engine.world.geysers:
            if not g.get("active"):
                continue
            x, y = self._to_screen(g["x"], g["y"])
            if not (-200 < x < WIDTH + 200 and -200 < y < VIEW_H + 200):
                continue
            ax, ay = math.cos(g["angle"]), math.sin(g["angle"])
            glow(self.screen, x, y, 16, (255, 140, 70), alpha=70)
            for i in range(14):
                d = rng.uniform(0, GEYSER_LENGTH)
                off = rng.uniform(-9, 9) * (d / GEYSER_LENGTH + 0.2)
                px = x + ax * d - ay * off
                py = y + ay * d + ax * off
                heat = 1 - d / GEYSER_LENGTH
                color = _mix((120, 60, 40), (255, 190, 110), heat)
                pg.draw.circle(self.screen, color, (int(px), int(py)),
                               max(1, int(3 * heat + rng.uniform(0, 1.5))))

    # ---------------------------------------------------------------- goal
    def _draw_station(self, engine, t):
        sx, sy = engine.world.station
        x, y = self._to_screen(sx, sy)
        if not (-700 < x < WIDTH + 700 and -700 < y < VIEW_H + 700):
            return
        beat = 0.5 + 0.5 * math.sin(t * 2.2)
        glow(self.screen, x, y - 14, int(60 + 18 * beat), C_STATION,
             alpha=26, layers=5)
        # the dome
        pg.draw.ellipse(self.screen, (26, 26, 30), (x - 46, y - 26, 92, 40))
        pg.draw.ellipse(self.screen, (52, 52, 58), (x - 46, y - 26, 92, 40), 2)
        pg.draw.rect(self.screen, (30, 30, 34), (x - 58, y + 2, 116, 12),
                     border_radius=3)
        for i in range(4):                       # warm portholes
            px = x - 27 + i * 18
            glow(self.screen, px, y - 7, 7, C_STATION, alpha=120)
            pg.draw.circle(self.screen, C_STATION, (int(px), int(y - 7)), 3)
        mast_y = y - 44
        pg.draw.line(self.screen, (52, 52, 58), (x, y - 26), (x, mast_y), 2)
        beacon = _mix((60, 30, 20), (255, 120, 90), beat)
        glow(self.screen, x, mast_y, 10, beacon, alpha=int(90 * beat))
        pg.draw.circle(self.screen, beacon, (int(x), int(mast_y)), 3)

    def _draw_boxes(self, engine, t):
        for box in engine.world.blackboxes:
            if box["found"]:
                continue
            x, y = self._to_screen(box["x"], box["y"])
            if not (-260 < x < WIDTH + 260 and -260 < y < VIEW_H + 260):
                continue
            blink = math.sin(t * 7.5 + box["idx"] * 2) > 0.55
            if blink:
                glow(self.screen, x, y - 4, 8, C_DANGER, alpha=110)
                pg.draw.circle(self.screen, (255, 130, 110),
                               (int(x), int(y - 4)), 2)
            dist = math.hypot(engine.sub.x - box["x"],
                              engine.sub.y - box["y"])
            if dist < 240 or engine.lamp_on and dist < LAMP_RANGE + 60:
                pg.draw.rect(self.screen, (34, 40, 38),
                             (x - 7, y - 5, 14, 10), border_radius=2)
                pg.draw.rect(self.screen, C_BOX, (x - 7, y - 5, 14, 10), 1)

    # ---------------------------------------------------------------- lamp
    def _draw_lamp(self, engine):
        sub = engine.sub
        tx, ty = sub.thrusting
        aim = math.atan2(ty * 0.45, sub.facing)
        x, y = self._to_screen(sub.x, sub.y)
        nose_x = x + math.cos(aim) * SUB_R
        nose_y = y + math.sin(aim) * SUB_R

        cone = pg.Surface((WIDTH, VIEW_H), pg.SRCALPHA)
        for i in range(4):
            reach = LAMP_RANGE * (1 - i * 0.18)
            half = LAMP_HALF_ANGLE * (1 - i * 0.13)
            pts = [(nose_x, nose_y)]
            for step in range(9):
                a = aim - half + (2 * half) * step / 8
                pts.append((nose_x + math.cos(a) * reach,
                            nose_y + math.sin(a) * reach))
            pg.draw.polygon(cone, (*C_LAMP, 15), pts)
        self.screen.blit(cone, (0, 0))

        # the lamp shows the truth: real rock, briefly
        for idx in engine.world.segments_near(sub.x, sub.y, LAMP_RANGE):
            x1, y1, x2, y2 = engine.world.segments[idx]
            mx, my = (x1 + x2) * 0.5, (y1 + y2) * 0.5
            dx, dy = mx - sub.x, my - sub.y
            dist = math.hypot(dx, dy)
            if dist > LAMP_RANGE:
                continue
            spread = abs((math.atan2(dy, dx) - aim + math.pi) % math.tau
                         - math.pi)
            if spread > LAMP_HALF_ANGLE:
                continue
            fade = (1 - dist / LAMP_RANGE) * (1 - spread / LAMP_HALF_ANGLE)
            color = _mix((40, 36, 28), (196, 168, 120), fade)
            pg.draw.line(self.screen, color,
                         self._to_screen(x1, y1), self._to_screen(x2, y2), 2)

    # ------------------------------------------------------------------ Her
    def _draw_mother(self, engine, t):
        m = engine.mother
        if m.state == "dormant":
            return
        if self.mother_prev is not None:
            dx = m.x - self.mother_prev[0]
            dy = m.y - self.mother_prev[1]
            if dx * dx + dy * dy > 0.05:
                self.mother_heading = math.atan2(dy, dx)
        self.mother_prev = (m.x, m.y)

        dist = math.hypot(m.x - engine.sub.x, m.y - engine.sub.y)
        sub = engine.sub
        tx, ty = sub.thrusting
        aim = math.atan2(ty * 0.45, sub.facing)
        spread = abs((math.atan2(m.y - sub.y, m.x - sub.x) - aim + math.pi)
                     % math.tau - math.pi)
        lamp_lit = (engine.lamp_on and dist < LAMP_RANGE + m.radius
                    and spread < LAMP_HALF_ANGLE + 0.35)
        if dist > 420 and not lamp_lit:
            return

        x, y = self._to_screen(m.x, m.y)
        heading = self.mother_heading
        # body: a chain of dark vertebrae behind the skull
        vis = 1.0 if lamp_lit else max(0.0, 1 - dist / 420) * 0.75
        if m.state == "hunt" and not lamp_lit:
            vis = min(1.0, vis + 0.18)     # hunting, she displaces water
        for i in range(10):
            d = i * m.radius * 0.52
            sway = math.sin(t * 3.1 - i * 0.85) * (3 + i * 1.7)
            bx = x - math.cos(heading) * d - math.sin(heading) * sway * 0.2
            by = y - math.sin(heading) * d + math.cos(heading) * sway * 0.2
            r = max(2, int(m.radius * (1 - i * 0.09)))
            body = _mix((6, 9, 12), (22, 30, 36), vis * (1 - i * 0.06))
            pg.draw.circle(self.screen, body, (int(bx), int(by)), r)
            if i in (2, 4, 6) and vis > 0.15:    # her own faint lanterns
                pg.draw.circle(self.screen,
                               _mix((0, 0, 0), C_BIO, vis * 0.8),
                               (int(bx), int(by - r * 0.5)), 1)
        # eyes: pale, forward, wrong
        ex = x + math.cos(heading) * m.radius * 0.55
        ey = y + math.sin(heading) * m.radius * 0.55
        side_x = -math.sin(heading) * 7
        side_y = math.cos(heading) * 7
        eye = _mix((30, 34, 30), (210, 225, 205), vis)
        for sgn in (-1, 1):
            pg.draw.circle(self.screen, eye,
                           (int(ex + side_x * sgn), int(ey + side_y * sgn)),
                           2)
        if lamp_lit:
            glow(self.screen, x, y, m.radius + 18, (120, 140, 130), alpha=26)

    # ------------------------------------------------------------- the sub
    def _draw_sub(self, engine, dt, t):
        sub = engine.sub
        x, y = self._to_screen(sub.x, sub.y)
        tx, ty = sub.thrusting

        if (tx or ty) and engine.battery > 0.5:
            for _ in range(2):
                self.bubbles.append([
                    sub.x - sub.facing * (SUB_R + 4) + random.uniform(-3, 3),
                    sub.y + random.uniform(-4, 4),
                    random.uniform(0.7, 1.6), random.uniform(-14, -30)])
        alive = []
        for b in self.bubbles:
            b[1] += b[3] * dt
            b[0] += math.sin(t * 6 + b[1] * 0.1) * 12 * dt
            b[2] -= dt * 0.55
            if b[2] > 0:
                alive.append(b)
                bx, by = self._to_screen(b[0], b[1])
                pg.draw.circle(self.screen, (90, 120, 140), (int(bx),
                               int(by)), max(1, int(b[2] * 2)), 1)
        self.bubbles = alive[-90:]

        sprite = self.sub_sprite.copy()
        spin = abs(math.sin(t * ((tx or ty) and 26 or 5)))
        blade_h = 3 + spin * 9
        pg.draw.ellipse(sprite, (120, 132, 146),
                        (self.prop_x - 2, self.sub_centre[1] - blade_h,
                         4, blade_h * 2))
        if sub.facing < 0:
            sprite = pg.transform.flip(sprite, True, False)
        tilt = max(-14.0, min(14.0, -sub.vy * 0.07)) * sub.facing
        sprite = pg.transform.rotate(sprite, tilt)
        rect = sprite.get_rect(center=(int(x), int(y)))
        glow(self.screen, x, y, 26, (60, 80, 100), alpha=22)
        self.screen.blit(sprite, rect)

    # ================================================================ panel
    def _dial(self, cx, cy, frac, label, color, low_is_bad=True):
        r = 34
        pg.draw.circle(self.screen, (16, 17, 20), (cx, cy), r)
        pg.draw.circle(self.screen, (60, 64, 74), (cx, cy), r, 2)
        a0, a1 = math.radians(135), math.radians(405)
        for i in range(9):
            a = a0 + (a1 - a0) * i / 8
            x1 = cx + math.cos(a) * (r - 5)
            y1 = cy + math.sin(a) * (r - 5)
            x2 = cx + math.cos(a) * (r - 10)
            y2 = cy + math.sin(a) * (r - 10)
            tick = C_DANGER if (low_is_bad and i < 2) else C_AMBER_DIM
            pg.draw.line(self.screen, tick, (x1, y1), (x2, y2), 2)
        a = a0 + (a1 - a0) * max(0.0, min(1.0, frac))
        danger = low_is_bad and frac < 0.25
        needle = C_DANGER if danger else color
        pg.draw.line(self.screen, needle, (cx, cy),
                     (cx + math.cos(a) * (r - 9),
                      cy + math.sin(a) * (r - 9)), 3)
        pg.draw.circle(self.screen, (90, 96, 108), (cx, cy), 4)
        self._text(self.font_small, label,
                   C_DANGER if danger else C_AMBER_DIM,
                   (cx, cy + r + 11), center=True)

    def _draw_panel(self, engine, t):
        top = VIEW_H
        self.screen.blit(self.panel_base, (0, top))
        mid = top + 58

        self._dial(52, mid, engine.hull / HULL_MAX, "КОРПУС", C_AMBER)
        self._dial(140, mid, engine.oxygen / OXYGEN_MAX, "КИСЛОРОД", C_AMBER)
        self._dial(228, mid, engine.battery / BATTERY_MAX, "БАТАРЕЯ", C_AMBER)

        # depth counter
        metres = int(engine.depth * METERS_PER_PX)
        self._text(self.font_small, "ГЛУБИНА, М", C_AMBER_DIM, (312, top + 18))
        pg.draw.rect(self.screen, (12, 13, 16), (308, top + 36, 132, 44),
                     border_radius=4)
        pg.draw.rect(self.screen, (56, 60, 70), (308, top + 36, 132, 44), 1,
                     border_radius=4)
        self._text(self.font_depth, "{:04d}".format(metres), C_AMBER,
                   (374, top + 59), center=True, glow_c=C_AMBER)
        # blackboxes
        for i in range(3):
            got = i < len(engine.boxes_found)
            color = C_BOX if got else (52, 58, 56)
            x0 = 322 + i * 36
            pg.draw.rect(self.screen, color, (x0, top + 92, 22, 14),
                         0 if got else 1, border_radius=2)
        self._text(self.font_small, "САМОПИСЦЫ", C_AMBER_DIM,
                   (312, top + 114))

        # hydrophone compass
        hx, hy = 512, mid
        pg.draw.circle(self.screen, (10, 14, 13), (hx, hy), 42)
        pg.draw.circle(self.screen, (60, 64, 74), (hx, hy), 42, 2)
        sweep = (t * 0.9) % math.tau
        pg.draw.line(self.screen, (24, 46, 40), (hx, hy),
                     (hx + math.cos(sweep) * 38, hy + math.sin(sweep) * 38),
                     1)
        for a in range(0, 360, 45):
            ar = math.radians(a)
            pg.draw.line(self.screen, (40, 52, 48),
                         (hx + math.cos(ar) * 36, hy + math.sin(ar) * 36),
                         (hx + math.cos(ar) * 40, hy + math.sin(ar) * 40), 1)
        comp = engine.compass
        if comp is not None:
            fade = max(0.0, 1 - comp["age"] / 6.0)
            color = {"mother": C_DANGER, "station": C_STATION,
                     "geyser": (140, 180, 235)}.get(comp["kind"], C_ECHO)
            ln = 12 + 26 * comp["strength"]
            end = (hx + math.cos(comp["angle"]) * ln,
                   hy + math.sin(comp["angle"]) * ln)
            pg.draw.line(self.screen, _mix((10, 14, 13), color, fade),
                         (hx, hy), end, 3)
            glow(self.screen, end[0], end[1], 7, color,
                 alpha=int(90 * fade))
        pg.draw.circle(self.screen, (90, 96, 108), (hx, hy), 3)
        self._text(self.font_small, "ГИДРОФОН", C_AMBER_DIM,
                   (hx, mid + 53), center=True)

        # sonar + lamp status lamps
        ready = engine.sonar.ready and engine.battery >= COST_PING
        for i, (on, color, label) in enumerate((
                (ready, C_ECHO, "СОНАР"),
                (engine.lamp_on, C_LAMP, "ПРОЖЕКТОР"))):
            lx, ly = 610, top + 34 + i * 44
            c = color if on else (44, 48, 52)
            if on:
                glow(self.screen, lx, ly, 9, color, alpha=110)
            pg.draw.circle(self.screen, c, (lx, ly), 5)
            pg.draw.circle(self.screen, (70, 76, 86), (lx, ly), 8, 1)
            self._text(self.font_small, label,
                       C_TEXT if on else C_DIM, (lx + 16, ly - 7))

        # radio
        rx = 736
        rw = WIDTH - rx - 14
        pg.draw.rect(self.screen, (7, 12, 9), (rx, top + 14, rw, PANEL_H - 28),
                     border_radius=5)
        pg.draw.rect(self.screen, (46, 58, 50), (rx, top + 14, rw,
                     PANEL_H - 28), 1, border_radius=5)
        self._text(self.font_small, "РАДИО · СВЯЗЬ С БАЗОЙ", (96, 150, 110),
                   (rx + 12, top + 20))
        line = engine.radio.line
        if line is None:
            hiss = "— эфир чист —" if int(t) % 7 else "— · · — —   ·"
            self._text(self.font_small, hiss, (52, 76, 60),
                       (rx + rw // 2, top + PANEL_H // 2), center=True)
        else:
            for i, ln in enumerate(self._wrap(self.font_ui, line, rw - 28)[:3]):
                self._text(self.font_ui, ln, (150, 232, 170),
                           (rx + 14, top + 42 + i * 27))

    # ============================================================== screens
    def _screen_base(self, t):
        self.screen.blit(self.bg_shallow, (0, 0))
        self.screen.fill((3, 5, 10), (0, VIEW_H, WIDTH, PANEL_H))
        cx, cy = WIDTH // 2, HEIGHT // 2
        for i in range(3):
            r = int(((t * 90 + i * 260) % 780))
            if r > 10:
                a = max(0, int(70 * (1 - r / 780)))
                if a:
                    ring = pg.Surface((r * 2 + 4, r * 2 + 4), pg.SRCALPHA)
                    pg.draw.circle(ring, (*C_ECHO, a), (r + 2, r + 2), r, 2)
                    self.screen.blit(ring, (cx - r - 2, cy - r - 2))
        self.screen.blit(self.vignette, (0, 0))
        self.screen.blit(self.grain[int(t * 12) % len(self.grain)], (0, 0))

    def draw_menu(self, t, best):
        self._screen_base(t)
        cx = WIDTH // 2
        self._text(self.font_big, "БАТИСФЕРА", C_ECHO, (cx, 150),
                   center=True, glow_c=C_ECHO)
        self._text(self.font_ui,
                   "станция «Глагол» замолчала на дне впадины. вас посылают вниз.",
                   C_DIM, (cx, 208), center=True)
        story = ("Сонар — ваши единственные глаза: мир виден лишь как "
                 "остывающее эхо. Но каждый импульс слышен. И внизу есть "
                 "кто-то, кто умеет слушать.")
        for i, ln in enumerate(self._wrap(self.font_ui, story, 640)):
            self._text(self.font_ui, ln, C_TEXT, (cx, 262 + i * 26),
                       center=True)
        rows = (("WASD / стрелки", "двигатели (шумно)"),
                ("ПРОБЕЛ", "импульс сонара (очень шумно)"),
                ("F", "прожектор — свет вблизи, тоже выдаёт"),
                ("H", "справка   ·   ESC — пауза"))
        y = 372
        for key, what in rows:
            self._text(self.font_ui, key, C_AMBER, (cx - 300, y))
            self._text(self.font_ui, what, C_DIM, (cx - 60, y))
            y += 32
        self._text(self.font_ui,
                   "цель: три самописца, затем стыковка со станцией на дне",
                   C_STATION, (cx, y + 18), center=True)
        if best:
            self._text(self.font_ui, best, C_DIM, (cx, y + 52), center=True)
        if int(t * 1.6) % 2:
            self._text(self.font_mid, "ENTER — начать погружение", C_TEXT,
                       (cx, HEIGHT - 96), center=True)

    def draw_help(self):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((2, 4, 8, 216))
        self.screen.blit(veil, (0, 0))
        cx = WIDTH // 2
        self._text(self.font_mid, "СУДОВОЙ ЖУРНАЛ, ПАМЯТКА", C_AMBER,
                   (cx, 96), center=True)
        tips = (
            "Эхо остывает ~6 секунд. Пингуйте, запоминайте, двигайтесь.",
            "Она слышит пинг за полтора километра. Чем чаще звук — тем она злее.",
            "Двигатели и прожектор — шум. Заглушите всё, и она потеряет след.",
            "Стук в гидрофоне — её голос. Стрелка покажет, откуда.",
            "Красная стрелка — она. Янтарная — маяк станции, каждые 5 секунд.",
            "Гейзеры варят корпус. Слышны по гидрофону перед выбросом.",
            "Батарея восполняется динамо-машиной. Кислород — нет.",
            "Стыковка: подойти к шлюзу медленно, почти без хода.")
        y = 156
        for tip in tips:
            self._text(self.font_ui, "— " + tip, C_TEXT, (cx - 430, y))
            y += 42
        self._text(self.font_ui, "H — закрыть", C_DIM, (cx, y + 24),
                   center=True)

    def draw_pause(self):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((2, 4, 8, 190))
        self.screen.blit(veil, (0, 0))
        self._text(self.font_big, "ПАУЗА", C_DIM,
                   (WIDTH // 2, HEIGHT // 2 - 30), center=True)
        self._text(self.font_ui, "ESC — продолжить   ·   Q — в меню",
                   C_DIM, (WIDTH // 2, HEIGHT // 2 + 40), center=True)

    def draw_death(self, engine, t):
        self.screen.fill((2, 2, 4))
        self.screen.blit(self.grain[int(t * 16) % len(self.grain)], (0, 0))
        cx = WIDTH // 2
        self._text(self.font_big, "СВЯЗЬ ПОТЕРЯНА", C_DANGER, (cx, 200),
                   center=True, glow_c=C_DANGER)
        self._text(self.font_mid, engine.death_cause or "тишина",
                   C_TEXT, (cx, 278), center=True)
        stats = "глубина {} м   ·   самописцы {}/3   ·   {} мин {:02d} c".format(
            int(engine.max_depth * METERS_PER_PX), len(engine.boxes_found),
            int(engine.time // 60), int(engine.time % 60))
        self._text(self.font_ui, stats, C_DIM, (cx, 340), center=True)
        self._text(self.font_ui,
                   "наверху ещё долго держали канал открытым",
                   (90, 95, 100), (cx, 400), center=True)
        if int(t * 1.6) % 2:
            self._text(self.font_ui, "ENTER — новое погружение   ·   ESC — меню",
                       C_TEXT, (cx, 470), center=True)

    def draw_docked(self, engine, t, logs):
        self.screen.blit(self.bg_shallow, (0, 0))
        glow(self.screen, WIDTH // 2, HEIGHT - 40, 320, C_STATION, alpha=36,
             layers=6)
        self.screen.blit(self.vignette, (0, 0))
        cx = WIDTH // 2
        self._text(self.font_big, "ШЛЮЗ ПРИНЯТ", C_STATION, (cx, 110),
                   center=True, glow_c=C_STATION)
        stats = "глубина {} м   ·   самописцы {}/3   ·   {} мин {:02d} c".format(
            int(engine.max_depth * METERS_PER_PX), len(engine.boxes_found),
            int(engine.time // 60), int(engine.time % 60))
        self._text(self.font_ui, stats, C_DIM, (cx, 164), center=True)
        y = 220
        if engine.boxes_found:
            for idx in engine.boxes_found:
                for i, ln in enumerate(self._wrap(self.font_ui, logs[idx],
                                                  760)):
                    self._text(self.font_ui, ln, (150, 232, 170),
                               (cx, y + i * 26), center=True)
                y += 26 * len(self._wrap(self.font_ui, logs[idx], 760)) + 18
        else:
            self._text(self.font_ui,
                       "самописцы остались в темноте. станция промолчит об этом.",
                       C_DIM, (cx, y), center=True)
            y += 40
        if int(t * 1.6) % 2:
            self._text(self.font_ui,
                       "ENTER — новое погружение   ·   ESC — меню", C_TEXT,
                       (cx, min(HEIGHT - 60, y + 40)), center=True)
        self.screen.blit(self.grain[int(t * 12) % len(self.grain)], (0, 0))
