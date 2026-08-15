"""Drawing: the moonlit river, the light map, the dashboard.

The night is one multiply blend: the world is painted as if it were day,
then a light map dims it - pale blue where only the moon reaches, warm
white in the headlight cone, a red breath behind the tail lights. Roadside
marker sticks answer the cone with true retroreflector sparks (drawn
additively only when the cone actually reaches them), and the aurora
breathes over everything at its own pace.
"""
from __future__ import annotations

import math
import random

import pygame as pg

from engine import COUNT, FIN, MEDAL_GOLD, MEDAL_SILVER, RUN
from graphics import (bake_scenery, glow, make_car, make_dash, make_dial,
                      make_grain_frames, make_headlight, make_vignette,
                      _mix)
from settings import (C_AMBER, C_AURORA_A, C_AURORA_B, C_DANGER, C_DIM,
                      C_GHOST, C_GREEN, C_HUT, C_ICE, C_ICE_CRACK, C_NIGHT,
                      C_NIGHT_DEEP, C_SNOW_DIM, C_SNOW_LIT, C_TEXT, CAR_LEN,
                      CAR_W, HEIGHT, PANEL_H, PX_PER_M, SLIP_DRIFT,
                      TOP_SPEED, VIEW_H, WIDTH)
from track import BANK_W

AMBIENT = (86, 96, 132)            # moonlight, in light-map terms
STICK_EVERY = 8                    # centerline indices between marker sticks
LIGHT_REACH = 315.0


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_big = pg.font.Font(None, 96)
        self.font_mid = pg.font.Font(None, 42)
        self.font_ui = pg.font.Font(None, 26)
        self.font_small = pg.font.Font(None, 21)
        self.font_time = pg.font.Font(None, 52)
        self.font_note = pg.font.Font(None, 44)

        self.car_img = make_car()
        self.ghost_img = make_car(ghost=True)
        self.scenery = bake_scenery()
        self.headlight = make_headlight(int(LIGHT_REACH), 23)
        self.grain = make_grain_frames()
        self.vignette = make_vignette(VIEW_H)
        self.dash = make_dash(WIDTH, PANEL_H)
        self.dial_speed = make_dial(46, 160, red_from=120)

        self.world = pg.Surface((WIDTH, VIEW_H))
        self.light = pg.Surface((WIDTH, VIEW_H))
        self.bg_tile = self._bake_tundra()

        rng = random.Random(21)
        self.snow = []
        for par, count, size in ((0.3, 60, 1), (0.6, 50, 1), (1.0, 45, 2)):
            for _ in range(count):
                self.snow.append([rng.uniform(0, WIDTH),
                                  rng.uniform(0, VIEW_H), par, size,
                                  rng.uniform(26, 60)])
        self.cam = None
        self.prev_cam = (0.0, 0.0)
        self.skids = []
        self.spray = []
        self._shade = {}

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _bake_tundra():
        rng = random.Random(3)
        tile = pg.Surface((256, 256))
        tile.fill(C_NIGHT)
        for _ in range(260):
            x, y = rng.randrange(256), rng.randrange(256)
            c = _mix(C_NIGHT, C_NIGHT_DEEP, rng.random())
            pg.draw.circle(tile, c, (x, y), rng.randint(1, 3))
        for _ in range(40):
            x, y = rng.randrange(256), rng.randrange(256)
            pg.draw.circle(tile, _mix(C_NIGHT, (60, 72, 100), 0.5),
                           (x, y), 1)
        return tile

    def _text(self, font, text, color, pos, center=False, glow_c=None,
              surface=None):
        surf = surface or self.screen
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
                surf.blit(halo, rect.move(dx, dy))
        surf.blit(img, rect)
        return rect

    def _update_camera(self, engine, dt):
        car = engine.car
        tx = car.x + car.vx * 0.55 - WIDTH / 2
        ty = car.y + car.vy * 0.55 - VIEW_H / 2
        if self.cam is None:
            self.cam = [tx, ty]
        k = min(1.0, dt * 3.6)
        self.cam[0] += (tx - self.cam[0]) * k
        self.cam[1] += (ty - self.cam[1]) * k
        if engine.shake > 0:
            self.cam[0] += random.uniform(-8, 8) * engine.shake
            self.cam[1] += random.uniform(-8, 8) * engine.shake

    def _to_screen(self, x, y):
        return x - self.cam[0], y - self.cam[1]

    def _visible_runs(self, track):
        """Sorted consecutive centerline index runs near the camera."""
        cx = self.cam[0] + WIDTH / 2
        cy = self.cam[1] + VIEW_H / 2
        idxs = sorted(set(track.near_indices(cx, cy, 860.0)))
        runs = []
        for i in idxs:
            if runs and i == runs[-1][-1] + 1:
                runs[-1].append(i)
            else:
                runs.append([i])
        return runs

    # ============================================================== the run
    def draw_game(self, engine, dt):
        t = engine.time if engine.state != COUNT else -engine.count_t
        self._update_camera(engine, dt)
        world = self.world

        # -- tundra beyond the banks ---------------------------------------
        ox = -int(self.cam[0]) % 256 - 256
        oy = -int(self.cam[1]) % 256 - 256
        for gy in range(oy, VIEW_H + 256, 256):
            for gx in range(ox, WIDTH + 256, 256):
                world.blit(self.bg_tile, (gx, gy))

        track = engine.track
        runs = self._visible_runs(track)
        self._draw_road(track, runs, world)
        self._draw_ice(track, world)
        self._draw_gates(engine, world)
        self._draw_skids(engine, dt, world)
        sticks = self._draw_scenery(engine, track, runs, world)
        self._draw_ghost(engine, world)
        self._draw_spray(engine, dt, world)
        self._draw_car(engine, world)

        # -- the light map -------------------------------------------------
        light = self.light
        light.fill(AMBIENT)
        car = engine.car
        cx, cy = self._to_screen(car.x, car.y)
        beam = pg.transform.rotate(self.headlight,
                                   -math.degrees(car.heading))
        rect = beam.get_rect(center=(cx + math.cos(car.heading) * 8,
                                     cy + math.sin(car.heading) * 8))
        light.blit(beam, rect, special_flags=pg.BLEND_RGB_MAX)
        tail = _mix((0, 0, 0), (200, 90, 80), 0.5)
        bx = cx - math.cos(car.heading) * 16
        by = cy - math.sin(car.heading) * 16
        pg.draw.circle(light, tail, (int(bx), int(by)), 13)
        for sx, sy, kind in sticks:
            if kind == "hut":
                pg.draw.circle(light, (210, 170, 120), (int(sx), int(sy)),
                               30)
        world.blit(light, (0, 0), special_flags=pg.BLEND_RGB_MULT)

        # -- additive life on top ------------------------------------------
        self._draw_reflectors(engine, sticks, world)
        self.screen.blit(world, (0, 0))
        self._draw_aurora(t)
        self._draw_snowfall(engine, dt)
        self.screen.blit(self.vignette, (0, 0))
        self.screen.blit(self.grain[int(abs(t) * 14) % len(self.grain)],
                         (0, 0))

        self._draw_hud(engine, t)
        if engine.state == COUNT:
            self._draw_countdown(engine)

    # ---------------------------------------------------------------- road
    def _draw_road(self, track, runs, world):
        for run in runs:
            if len(run) < 2:
                continue
            left, right = [], []
            for i in run:
                x, y = self._to_screen(*track.pts[i])
                nx, ny = -track.dirs[i][1], track.dirs[i][0]
                half = track.half[i]
                left.append((x - nx * (half + BANK_W),
                             y - ny * (half + BANK_W)))
                right.append((x + nx * (half + BANK_W),
                              y + ny * (half + BANK_W)))
            pg.draw.polygon(world, (146, 160, 190),
                            left + right[::-1])
        for run in runs:
            if len(run) < 2:
                continue
            left, right = [], []
            for i in run:
                x, y = self._to_screen(*track.pts[i])
                nx, ny = -track.dirs[i][1], track.dirs[i][0]
                half = track.half[i]
                left.append((x - nx * half, y - ny * half))
                right.append((x + nx * half, y + ny * half))
            pg.draw.polygon(world, C_SNOW_LIT, left + right[::-1])
            # the polished twin ruts everybody before you drove
            mid = []
            for i in run:
                x, y = self._to_screen(*track.pts[i])
                mid.append((x, y))
            if len(mid) > 1:
                pg.draw.lines(world, _mix(C_SNOW_LIT, C_SNOW_DIM, 0.45),
                              False, mid, 22)
                pg.draw.lines(world, C_SNOW_LIT, False, mid, 8)

    def _draw_ice(self, track, world):
        for x, y, r, var in track.ice:
            sx, sy = self._to_screen(x, y)
            if not (-r - 40 < sx < WIDTH + r + 40
                    and -r - 40 < sy < VIEW_H + r + 40):
                continue
            pg.draw.circle(world, _mix(C_ICE, C_SNOW_LIT, 0.30),
                           (int(sx), int(sy)), int(r))
            pg.draw.circle(world, _mix(C_ICE, (120, 165, 185), 0.45),
                           (int(sx), int(sy)), int(r), 2)
            rng = random.Random(int(var * 10000))
            for _ in range(3):
                a = rng.uniform(0, math.tau)
                ln = r * rng.uniform(0.4, 0.9)
                x2 = sx + math.cos(a) * ln
                y2 = sy + math.sin(a) * ln
                mx = (sx + x2) / 2 + rng.uniform(-6, 6)
                my = (sy + y2) / 2 + rng.uniform(-6, 6)
                pg.draw.lines(world, C_ICE_CRACK, False,
                              ((sx, sy), (mx, my), (x2, y2)), 1)

    def _draw_gates(self, engine, world):
        track = engine.track
        for s, kind in ([(track.start_s, "start"),
                         (track.finish_s, "finish")]
                        + [(c, "cp") for c in track.checkpoints]):
            i = track.index_at_s(s)
            x, y = self._to_screen(*track.pts[i])
            if not (-80 < x < WIDTH + 80 and -80 < y < VIEW_H + 80):
                continue
            nx, ny = -track.dirs[i][1], track.dirs[i][0]
            half = track.half[i]
            ax, ay = x - nx * half, y - ny * half
            bx, by = x + nx * half, y + ny * half
            if kind == "cp":
                for px, py in ((ax, ay), (bx, by)):
                    pg.draw.line(world, (200, 60, 50), (px, py),
                                 (px, py - 14), 2)
                    pg.draw.polygon(world, (230, 80, 60),
                                    ((px, py - 14), (px + 9, py - 11),
                                     (px, py - 8)))
            else:
                cells = int(half * 2 / 8)
                for c in range(cells):
                    t0 = c / cells
                    col = (230, 234, 240) if (c % 2 == 0) else (30, 32, 40)
                    pg.draw.line(world, col,
                                 (ax + (bx - ax) * t0, ay + (by - ay) * t0),
                                 (ax + (bx - ax) * (t0 + 1 / cells),
                                  ay + (by - ay) * (t0 + 1 / cells)), 6)
                for px, py in ((ax, ay), (bx, by)):
                    pg.draw.line(world, (70, 74, 86), (px, py),
                                 (px, py - 26), 3)
                if kind == "finish":
                    fx, fy = x, y - 30
                    pg.draw.rect(world, (40, 42, 52),
                                 (fx - 34, fy - 14, 68, 16))
                    self._text(self.font_small, "ФИНИШ", (230, 234, 240),
                               (fx, fy - 6), center=True, surface=world)

    # ------------------------------------------------------------ cosmetics
    def _draw_skids(self, engine, dt, world):
        car = engine.car
        if (engine.state == RUN and car.slip > SLIP_DRIFT
                and car.surface == "snow"):
            fx, fy = math.cos(car.heading), math.sin(car.heading)
            nx, ny = -fy, fx
            for side in (-1, 1):
                wx = car.x - fx * CAR_LEN * 0.32 + nx * side * CAR_W * 0.34
                wy = car.y - fy * CAR_LEN * 0.32 + ny * side * CAR_W * 0.34
                self.skids.append([wx, wy, wx - car.vx * 0.03,
                                   wy - car.vy * 0.03, 0.0])
        alive = []
        for mark in self.skids:
            mark[4] += dt
            if mark[4] < 11.0:
                alive.append(mark)
                a = 1.0 - mark[4] / 11.0
                x1, y1 = self._to_screen(mark[0], mark[1])
                if -40 < x1 < WIDTH + 40 and -40 < y1 < VIEW_H + 40:
                    x2, y2 = self._to_screen(mark[2], mark[3])
                    pg.draw.line(world, _mix(C_SNOW_LIT, (60, 70, 96), a),
                                 (x1, y1), (x2, y2), 3)
        self.skids = alive[-1000:]

    def _draw_spray(self, engine, dt, world):
        car = engine.car
        active = (engine.state == RUN
                  and (car.slip > SLIP_DRIFT or car.in_bank)
                  and car.speed > 40.0)
        if active:
            fx, fy = math.cos(car.heading), math.sin(car.heading)
            for _ in range(3 if car.in_bank else 2):
                self.spray.append([
                    car.x - fx * CAR_LEN * 0.4 + random.uniform(-4, 4),
                    car.y - fy * CAR_LEN * 0.4 + random.uniform(-4, 4),
                    -car.vx * 0.25 + random.uniform(-28, 28),
                    -car.vy * 0.25 + random.uniform(-28, 28),
                    random.uniform(0.35, 0.8)])
        alive = []
        for p in self.spray:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] > 0:
                alive.append(p)
                x, y = self._to_screen(p[0], p[1])
                r = max(1, int(p[4] * 5))
                pg.draw.circle(world, _mix(C_SNOW_DIM, (225, 232, 244),
                                           p[4]), (int(x), int(y)), r)
        self.spray = alive[-160:]

    def _draw_scenery(self, engine, track, runs, world):
        """Draws trees & co, returns light emitters + reflector sticks."""
        emitters = []
        cx = self.cam[0] + WIDTH / 2
        cy = self.cam[1] + VIEW_H / 2
        items = []
        for idx in track.scenery_near(cx, cy, 820.0):
            x, y, kind, var, size = track.scenery[idx]
            sx, sy = self._to_screen(x, y)
            if -60 < sx < WIDTH + 60 and -80 < sy < VIEW_H + 60:
                items.append((sy, sx, kind, var, size))
        for run in runs:                        # marker sticks line the road
            for i in run:
                if i % STICK_EVERY:
                    continue
                nx, ny = -track.dirs[i][1], track.dirs[i][0]
                half = track.half[i] + 6.0
                for side in (-1.0, 1.0):
                    px = track.pts[i][0] + nx * half * side
                    py = track.pts[i][1] + ny * half * side
                    sx, sy = self._to_screen(px, py)
                    if -20 < sx < WIDTH + 20 and -20 < sy < VIEW_H + 20:
                        world.blit(self.scenery["stick"], (sx - 1, sy - 12))
                        emitters.append((sx, sy - 10, "stick"))
        items.sort()
        for sy, sx, kind, var, size in items:
            if kind == "post":
                img = self.scenery["post"]
                world.blit(img, (sx - 3, sy - 20))
                self._text(self.font_small, str(int(var)),
                           (220, 200, 170), (sx + 5, sy - 20),
                           surface=world)
            elif kind in ("hut", "tent"):
                img = self.scenery[kind]
                world.blit(img, (sx - img.get_width() // 2,
                                 sy - img.get_height()))
                if kind == "hut":
                    emitters.append((sx - 8, sy - 13, "hut"))
                    emitters.append((sx - 8, sy - 13, "window"))
            else:
                variant = int(var * 4) % 4
                size_i = 0 if size < 0.95 else (1 if size < 1.2 else 2)
                img = self.scenery[(kind, variant, size_i)]
                world.blit(img, (sx - img.get_width() // 2,
                                 sy - img.get_height() + 4))
        return emitters

    def _draw_reflectors(self, engine, emitters, world):
        car = engine.car
        ccx, ccy = self._to_screen(car.x, car.y)
        for sx, sy, kind in emitters:
            if kind == "window":
                pg.draw.rect(world, C_HUT, (sx - 3, sy - 3, 7, 7))
                glow(world, sx, sy, 12, C_HUT, alpha=90)
                continue
            if kind != "stick":
                continue
            dx, dy = sx - ccx, sy - ccy
            dist = math.hypot(dx, dy)
            if dist > LIGHT_REACH + 30 or dist < 6:
                continue
            spread = abs((math.atan2(dy, dx) - car.heading + math.pi)
                         % math.tau - math.pi)
            if spread < 0.5:
                a = (1.0 - dist / (LIGHT_REACH + 30)) \
                    * (1.0 - spread / 0.5)
                glow(world, sx, sy, 6, (255, 255, 240),
                     alpha=int(200 * a))
                pg.draw.circle(world, (255, 255, 250), (int(sx), int(sy)),
                               1)

    def _draw_ghost(self, engine, world):
        if engine.ghost_pos is None or engine.state == COUNT:
            return
        gx, gy, gh = engine.ghost_pos
        sx, sy = self._to_screen(gx, gy)
        if not (-60 < sx < WIDTH + 60 and -60 < sy < VIEW_H + 60):
            return
        img = pg.transform.rotate(self.ghost_img, -math.degrees(gh))
        world.blit(img, img.get_rect(center=(sx, sy)))

    def _draw_car(self, engine, world):
        car = engine.car
        sx, sy = self._to_screen(car.x, car.y)
        img = pg.transform.rotate(self.car_img, -math.degrees(car.heading))
        world.blit(img, img.get_rect(center=(sx, sy)))

    # ------------------------------------------------------------------ sky
    def _draw_aurora(self, t):
        veil = pg.Surface((WIDTH, 240), pg.SRCALPHA)
        for color, speed, base, amp, ph in (
                (C_AURORA_A, 0.21, 52.0, 34.0, 0.0),
                (C_AURORA_B, 0.13, 88.0, 26.0, 2.1)):
            for x in range(0, WIDTH, 16):
                y0 = base + amp * math.sin(x * 0.0043 + t * speed + ph) \
                    + 14 * math.sin(x * 0.011 - t * speed * 1.7)
                h = 80 + 34 * math.sin(x * 0.0071 + t * speed * 0.6 + ph)
                a = int(27 + 12 * math.sin(x * 0.017 + t * 0.5 + ph))
                for seg in range(3):
                    aa = max(0, a - seg * 6)
                    if aa:
                        pg.draw.rect(veil, (*color, aa),
                                     (x, y0 + seg * h / 3, 16, h / 3))
        self.screen.blit(veil, (0, 0))

    def _draw_snowfall(self, engine, dt):
        dcx = self.cam[0] - self.prev_cam[0]
        dcy = self.cam[1] - self.prev_cam[1]
        self.prev_cam = (self.cam[0], self.cam[1])
        for p in self.snow:
            p[0] -= dcx * p[2] - math.sin(p[1] * 0.02) * 14 * dt
            p[1] += -dcy * p[2] + p[4] * dt
            x = p[0] % WIDTH
            y = p[1] % VIEW_H
            ln = min(18.0, 2.0 + math.hypot(dcx, dcy) * p[2] * 1.1)
            ex = x + (dcx * p[2]) / max(1.0, ln) * -ln
            ey = y + (-p[4] * 0.06 - dcy * p[2]) / max(1.0, ln) * -ln
            col = _mix(C_SNOW_DIM, (235, 240, 250), p[2])
            pg.draw.line(self.screen, col, (x, y), (ex, ey), p[3])

    # ------------------------------------------------------------------ HUD
    def _arrow(self, cx, cy, note):
        """The co-driver's arrow, drawn with polygons - no font glyphs."""
        kind, cat = note["kind"], note["cat"]
        color = C_GREEN
        if kind == "ice":
            color = (150, 220, 240)
            for a in range(6):
                ang = a * math.tau / 6
                pg.draw.line(self.screen, color, (cx, cy),
                             (cx + math.cos(ang) * 15,
                              cy + math.sin(ang) * 15), 2)
            pg.draw.circle(self.screen, color, (cx, cy), 4)
            return
        if kind != "turn":
            pg.draw.line(self.screen, C_GREEN, (cx, cy + 16), (cx, cy - 12),
                         4)
            pg.draw.polygon(self.screen, C_GREEN,
                            ((cx - 7, cy - 10), (cx + 7, cy - 10),
                             (cx, cy - 22)))
            return
        if cat <= 1:
            color = C_DANGER
        elif cat <= 3:
            color = C_AMBER
        right = "прав" in note["text"] or "вправо" in note["text"]
        bend = math.radians((170, 120, 95, 75, 55, 38)[min(5, cat)])
        pts = [(cx, cy + 18), (cx, cy - 2)]
        steps = 5
        for i in range(1, steps + 1):
            a = -math.pi / 2 + (bend * i / steps) * (1 if right else -1)
            pts.append((pts[1][0] + math.cos(a) * 14 * i / steps * 1.6,
                        pts[1][1] + 14 * i / steps * 1.6 * math.sin(a)
                        + 14 * i / steps * 0.0))
        pg.draw.lines(self.screen, color, False, pts, 4)
        ex, ey = pts[-1]
        a_end = -math.pi / 2 + bend * (1 if right else -1)
        pg.draw.polygon(self.screen, color,
                        ((ex + math.cos(a_end) * 10,
                          ey + math.sin(a_end) * 10),
                         (ex + math.cos(a_end + 2.5) * 7,
                          ey + math.sin(a_end + 2.5) * 7),
                         (ex + math.cos(a_end - 2.5) * 7,
                          ey + math.sin(a_end - 2.5) * 7)))

    def _draw_hud(self, engine, t):
        top = VIEW_H
        self.screen.blit(self.dash, (0, top))
        car = engine.car

        # speedometer
        dial_c = (70, top + PANEL_H // 2)
        img = self.dial_speed
        self.screen.blit(img, img.get_rect(center=dial_c))
        kmh = car.speed / PX_PER_M * 3.6
        a0, a1 = math.radians(130), math.radians(410)
        a = a0 + (a1 - a0) * min(1.0, kmh / 160.0)
        pg.draw.line(self.screen, (255, 170, 150), dial_c,
                     (dial_c[0] + math.cos(a) * 38,
                      dial_c[1] + math.sin(a) * 38), 3)
        pg.draw.circle(self.screen, (200, 205, 215), dial_c, 4)
        self._text(self.font_small, "%d км/ч" % int(kmh), C_GREEN,
                   (dial_c[0], top + PANEL_H - 14), center=True)

        # surface lamp
        on_ice = car.surface == "ice"
        lx, ly = 150, top + 30
        if on_ice:
            glow(self.screen, lx, ly, 10, (150, 220, 240), alpha=120)
        pg.draw.circle(self.screen, (150, 220, 240) if on_ice
                       else (40, 46, 52), (lx, ly), 6)
        self._text(self.font_small, "ГОЛОЛЁД",
                   (150, 220, 240) if on_ice else C_DIM, (lx + 14, ly - 7))
        in_bank = car.in_bank
        by = ly + 30
        if in_bank:
            glow(self.screen, lx, by, 10, C_AMBER, alpha=120)
        pg.draw.circle(self.screen, C_AMBER if in_bank else (40, 46, 52),
                       (lx, by), 6)
        self._text(self.font_small, "СУГРОБ  (T — на трассу)",
                   C_AMBER if in_bank else C_DIM, (lx + 14, by - 7))

        # time and delta
        self._text(self.font_time, engine.format_time(), C_TEXT,
                   (WIDTH // 2, top + 34), center=True, glow_c=(90, 96, 120))
        if engine.delta_m is not None and engine.state == RUN:
            ahead = engine.delta_m >= 0
            col = C_GREEN if ahead else C_DANGER
            label = "%s%d м %s" % ("+" if ahead else "",
                                   int(engine.delta_m),
                                   "к призраку" if not engine.ghost_is_ai
                                   else "к штурману")
            self._text(self.font_ui, label, col, (WIDTH // 2, top + 66),
                       center=True)

        # progress strip
        px0, px1 = WIDTH // 2 - 170, WIDTH // 2 + 170
        py = top + 96
        pg.draw.line(self.screen, (52, 56, 66), (px0, py), (px1, py), 4)
        for cp in engine.track.checkpoints:
            frac = (cp - engine.track.start_s) \
                / (engine.track.finish_s - engine.track.start_s)
            x = px0 + (px1 - px0) * frac
            pg.draw.line(self.screen, (90, 96, 110), (x, py - 4),
                         (x, py + 4), 1)
        x = px0 + (px1 - px0) * engine.progress
        pg.draw.line(self.screen, C_GREEN, (px0, py), (x, py), 4)
        pg.draw.polygon(self.screen, C_TEXT,
                        ((x, py - 7), (x + 5, py - 13), (x - 5, py - 13)))
        pg.draw.line(self.screen, (230, 234, 240), (px1, py - 6),
                     (px1, py + 6), 3)

        # the co-driver's board
        nx = WIDTH - 250
        pg.draw.rect(self.screen, (14, 16, 20),
                     (nx - 60, top + 12, 296, PANEL_H - 24),
                     border_radius=6)
        pg.draw.rect(self.screen, (60, 64, 76),
                     (nx - 60, top + 12, 296, PANEL_H - 24), 1,
                     border_radius=6)
        note = engine.note_current
        if note is not None:
            self._arrow(nx - 26, top + PANEL_H // 2 - 6, note)
            self._text(self.font_note, note["text"],
                       C_TEXT, (nx + 8, top + 34), glow_c=(70, 76, 96))
            if engine.note_next is not None \
                    and engine.note_next["kind"] == "turn":
                self._text(self.font_small,
                           "потом: " + engine.note_next["text"], C_DIM,
                           (nx + 8, top + 78))
        else:
            self._text(self.font_ui, "штурман молчит,", C_DIM,
                       (nx - 40, top + PANEL_H // 2 - 22))
            self._text(self.font_ui, "держите темп", C_DIM,
                       (nx - 40, top + PANEL_H // 2 + 2))
        self._text(self.font_small, "ТРАССА " + engine.code, C_DIM,
                   (nx - 52, top + PANEL_H - 32))

        # wrong way
        if engine.wrong_way and int(t * 3) % 2 == 0:
            self._text(self.font_big, "РАЗВОРОТ", C_DANGER,
                       (WIDTH // 2, VIEW_H // 2 - 40), center=True,
                       glow_c=C_DANGER)

    def _draw_countdown(self, engine):
        n = max(0, int(math.ceil(engine.count_t)))
        cx, cy = WIDTH // 2, VIEW_H // 2 - 40
        for i in range(3):
            on = n <= 3 - i and n > 0
            col = (200, 60, 50) if on else (46, 40, 40)
            if on:
                glow(self.screen, cx - 44 + i * 44, cy - 60, 14, col,
                     alpha=110)
            pg.draw.circle(self.screen, col, (cx - 44 + i * 44, cy - 60),
                           10)
        if n > 0:
            self._text(self.font_big, str(n), C_TEXT, (cx, cy + 12),
                       center=True, glow_c=(120, 126, 150))
        else:
            self._text(self.font_big, "СТАРТ", C_GREEN, (cx, cy + 12),
                       center=True, glow_c=C_GREEN)
        line = "штурман: %s. норматив %s." % (
            "трасса " + engine.code, engine.format_time(engine.par))
        self._text(self.font_ui, line, C_DIM, (cx, cy + 74), center=True)

    # ============================================================== screens
    def draw_menu(self, t, stats_line, code, best_line):
        self.screen.fill(C_NIGHT_DEEP)
        rng = random.Random(8)
        for _ in range(90):
            x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
            c = rng.randint(90, 180)
            self.screen.fill((c, c, min(255, c + 20)), (x, y, 1, 1))
        self._draw_aurora(t)
        cx = WIDTH // 2
        self._text(self.font_big, "З И М Н И К", C_TEXT, (cx, 150),
                   center=True, glow_c=C_AURORA_A)
        self._text(self.font_ui,
                   "ночной спецучасток по замёрзшей реке", C_DIM,
                   (cx, 208), center=True)
        story = ("Штурман читает повороты вслух, фары выхватывают вешки, "
                 "под колёсами то укатанный снег, то чёрный лёд. Против "
                 "вас — только время и призрак лучшего заезда.")
        words, line, y = story.split(), "", 258
        for w in words:
            probe = (line + " " + w).strip()
            if self.font_ui.size(probe)[0] > 640:
                self._text(self.font_ui, line, C_TEXT, (cx, y), center=True)
                line, y = w, y + 26
            else:
                line = probe
        if line:
            self._text(self.font_ui, line, C_TEXT, (cx, y), center=True)
        rows = (("W / стрелка вверх", "газ"),
                ("S / стрелка вниз", "тормоз, задний ход"),
                ("A, D / стрелки", "руль"),
                ("ПРОБЕЛ", "ручник — хвост в занос"),
                ("T", "вытащить из сугроба   ·   R — рестарт"),
                ("H", "справка   ·   ESC — пауза"))
        y += 46
        for key, what in rows:
            self._text(self.font_ui, key, C_AMBER, (cx - 300, y))
            self._text(self.font_ui, what, C_DIM, (cx - 20, y))
            y += 30
        self._text(self.font_ui, "трасса " + code
                   + "   ·   N — другая трасса", C_GREEN, (cx, y + 16),
                   center=True)
        if best_line:
            self._text(self.font_ui, best_line, C_DIM, (cx, y + 46),
                       center=True)
        if stats_line:
            self._text(self.font_small, stats_line, C_DIM,
                       (cx, HEIGHT - 40), center=True)
        if int(t * 1.6) % 2:
            self._text(self.font_mid, "ENTER — на старт", C_TEXT,
                       (cx, HEIGHT - 96), center=True)

    def draw_finish(self, engine, t):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((6, 8, 16, 205))
        self.screen.blit(veil, (0, 0))
        cx = WIDTH // 2
        self._text(self.font_big, "ФИНИШ", C_TEXT, (cx, 130), center=True,
                   glow_c=C_AURORA_A)
        self._text(self.font_time, engine.format_time(), C_TEXT,
                   (cx, 200), center=True)
        medal_col = {MEDAL_GOLD: (255, 205, 90),
                     MEDAL_SILVER: (205, 212, 224)}.get(engine.medal,
                                                        (196, 124, 80))
        my = 268
        pg.draw.circle(self.screen, medal_col, (cx - 70, my), 17)
        pg.draw.circle(self.screen, _mix(medal_col, (0, 0, 0), 0.35),
                       (cx - 70, my), 17, 3)
        pg.draw.polygon(self.screen, (120, 30, 40),
                        ((cx - 78, my - 15), (cx - 62, my - 15),
                         (cx - 70, my - 28)))
        self._text(self.font_mid, engine.medal, medal_col, (cx - 40, my - 14))
        diff = engine.time - engine.par
        self._text(self.font_ui,
                   "норматив штурмана %s   ·   %s%0.2f c" % (
                       engine.format_time(engine.par),
                       "+" if diff >= 0 else "−", abs(diff)),
                   C_DIM, (cx, my + 44), center=True)
        y = my + 84
        if engine.is_best:
            self._text(self.font_ui, "рекорд трассы! призрак перезаписан",
                       C_GREEN, (cx, y), center=True)
            y += 30
        if engine.rescues:
            self._text(self.font_ui,
                       "сугробов посчитано: %d" % engine.rescues, C_DIM,
                       (cx, y), center=True)
            y += 30
        if int(t * 1.6) % 2:
            self._text(self.font_ui,
                       "ENTER — ещё раз против призрака   ·   "
                       "N — новая трасса   ·   ESC — меню",
                       C_TEXT, (cx, y + 40), center=True)

    def draw_help(self):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((4, 6, 12, 216))
        self.screen.blit(veil, (0, 0))
        cx = WIDTH // 2
        self._text(self.font_mid, "ПАМЯТКА ШТУРМАНА", C_AMBER, (cx, 92),
                   center=True)
        tips = (
            "Цифра в подсказке — крутизна: 1 почти разворот, 5 едва изгиб.",
            "«Шпилька» — сбросьте до 60 и дёрните ручник на входе.",
            "Чёрный лёд не держит: не газуйте, не тормозите, не рулите резко.",
            "Сугроб мягкий, но жадный. Вязнете — T вернёт на дорогу.",
            "Вешки со светоотражайкой показывают дорогу раньше фар.",
            "Призрак — ваш лучший заезд. Первый раз вместо него едет штурман.",
            "Норматив штурмана бьётся: он аккуратен, вы можете быть смелее.",
            "Код трассы вида 8F3KQ — одна и та же трасса у всех одинакова.")
        y = 150
        for tip in tips:
            self._text(self.font_ui, "— " + tip, C_TEXT, (cx - 430, y))
            y += 40
        self._text(self.font_ui, "H — закрыть", C_DIM, (cx, y + 22),
                   center=True)

    def draw_pause(self):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((4, 6, 12, 190))
        self.screen.blit(veil, (0, 0))
        self._text(self.font_big, "ПАУЗА", C_DIM,
                   (WIDTH // 2, HEIGHT // 2 - 30), center=True)
        self._text(self.font_ui,
                   "ESC — продолжить   ·   R — рестарт   ·   Q — в меню",
                   C_DIM, (WIDTH // 2, HEIGHT // 2 + 40), center=True)
