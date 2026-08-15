"""Drawing: parquet by lamplight, cones of suspicion, the dial.

The night is the zimnik trick turned indoors: rooms are painted lit,
then a multiply light-map darkens everything the lamps don't reach.
Vision cones are drawn by raycasting the guards' own sightlines, so
what you SEE painted on the floor is exactly what can_see computes.
"""
from __future__ import annotations

import math
import random

import pygame as pg

from engine import CASING, CAUGHT, CRACKING, ESCAPED, LOOTED
from guards import ALERT, PATROL, SUSPICIOUS
from settings import (C_CARPET, C_CONE, C_CONE_ALERT, C_DANGER, C_DARKNESS,
                      C_DIM, C_DOOR, C_EXIT, C_FLOOR_A, C_FLOOR_B, C_FURN,
                      C_FURN_EDGE, C_GOLD, C_GUARD, C_GUARD_ALERT,
                      C_LAMP_LIGHT, C_NOISE, C_SAFE, C_TEXT, C_THIEF,
                      C_WALL, C_WALL_EDGE, FOV_ANGLE, FOV_RANGE,
                      FOV_RANGE_DARK, HEIGHT, LAMP_R, SAFE_RINGS,
                      SAFE_WINDOW, WIDTH, WORLD_H, WORLD_W)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_big = pg.font.Font(None, 88)
        self.font_mid = pg.font.Font(None, 40)
        self.font_ui = pg.font.Font(None, 26)
        self.font_small = pg.font.Font(None, 21)
        self.cam = None
        self.parquet = self._bake_parquet()
        self.lamp_disc = self._bake_lamp()
        self.world = pg.Surface((WIDTH, HEIGHT))
        self.light = pg.Surface((WIDTH, HEIGHT))

    # ---------------------------------------------------------------- bakes
    @staticmethod
    def _bake_parquet():
        tile = pg.Surface((128, 128))
        rng = random.Random(5)
        tile.fill(C_FLOOR_A)
        for y in range(0, 128, 16):
            for x in range(0, 128, 32):
                off = 16 if (y // 16) % 2 else 0
                c = _mix(C_FLOOR_A, C_FLOOR_B, rng.random())
                pg.draw.rect(tile, c, (x + off, y, 30, 14))
                pg.draw.line(tile, _mix(c, (0, 0, 0), 0.3),
                             (x + off, y + 14), (x + off + 30, y + 14))
        return tile

    @staticmethod
    def _bake_lamp():
        r = int(LAMP_R * 1.15)
        disc = pg.Surface((r * 2, r * 2))
        for i in range(r, 0, -2):
            k = i / r
            c = _mix((255, 232, 190), (0, 0, 0), k ** 1.4)
            pg.draw.circle(disc, c, (r, r), i)
        return disc

    def _to_screen(self, x, y):
        return x - self.cam[0], y - self.cam[1]

    # ================================================================ game
    def draw_game(self, engine, t):
        thief = engine.thief
        target = [thief.x - WIDTH / 2, thief.y - HEIGHT / 2]
        if self.cam is None:
            self.cam = target
        self.cam[0] += (target[0] - self.cam[0]) * 0.1
        self.cam[1] += (target[1] - self.cam[1]) * 0.1
        self.cam[0] = max(-60, min(WORLD_W - WIDTH + 60, self.cam[0]))
        self.cam[1] = max(-60, min(WORLD_H - HEIGHT + 60, self.cam[1]))
        w = self.world
        w.fill((8, 8, 10))
        m = engine.m

        # floors
        for i, (rx, ry, rw, rh) in enumerate(m.rooms):
            sx, sy = self._to_screen(rx, ry)
            if sx > WIDTH or sy > HEIGHT or sx + rw < 0 or sy + rh < 0:
                continue
            area = pg.Rect(sx, sy, rw, rh)
            for ty in range(int(ry) // 128, int(ry + rh) // 128 + 1):
                for tx in range(int(rx) // 128, int(rx + rw) // 128 + 1):
                    px, py = self._to_screen(tx * 128, ty * 128)
                    w.blit(self.parquet, (px, py),)
            if i % 3 == 0:                        # a carpet here and there
                pg.draw.rect(w, C_CARPET,
                             (sx + 24, sy + 24, rw - 48, rh - 48),
                             border_radius=6)
                pg.draw.rect(w, _mix(C_CARPET, (0, 0, 0), 0.35),
                             (sx + 24, sy + 24, rw - 48, rh - 48), 2,
                             border_radius=6)
            # re-mask outside room (parquet bleed): draw walls later anyway
        # doors (light wood strips under the walls layer)
        for d in m.doors:
            dx, dy, dw, dh = d["rect"]
            sx, sy = self._to_screen(dx, dy)
            pg.draw.rect(w, C_DOOR, (sx, sy, dw, dh))
        # walls
        for rx, ry, rw, rh in m.walls:
            sx, sy = self._to_screen(rx, ry)
            pg.draw.rect(w, C_WALL, (sx, sy, rw, rh))
            pg.draw.rect(w, C_WALL_EDGE, (sx, sy, rw, rh), 1)
        # furniture
        for f in m.furniture:
            fx, fy, fw, fh = f["rect"]
            sx, sy = self._to_screen(fx, fy)
            pg.draw.rect(w, C_FURN, (sx, sy, fw, fh), border_radius=4)
            pg.draw.rect(w, C_FURN_EDGE, (sx, sy, fw, fh), 2,
                         border_radius=4)
            if f["kind"] == "plant":
                pg.draw.circle(w, (40, 70, 44),
                               (sx + fw / 2, sy + fh / 2),
                               min(fw, fh) * 0.45)
        # switches, safe, exit
        for lamp in m.lamps:
            sx, sy = self._to_screen(*lamp["switch"])
            pg.draw.rect(w, (180, 172, 150), (sx - 4, sy - 6, 8, 12),
                         border_radius=2)
            pg.draw.circle(w, (60, 56, 48), (sx, sy), 2)
        sx, sy = self._to_screen(*m.safe_pos)
        pg.draw.rect(w, C_SAFE, (sx - 18, sy - 16, 36, 32),
                     border_radius=4)
        pg.draw.circle(w, _mix(C_SAFE, (0, 0, 0), 0.4), (sx, sy), 9)
        pg.draw.circle(w, (200, 205, 215), (sx, sy), 9, 2)
        ex, ey = self._to_screen(*m.exit_pos)
        pg.draw.rect(w, C_EXIT, (ex - 24, ey - 4, 48, 8), border_radius=3)

        # ------------------------------------------------- light multiply
        light = self.light
        light.fill(C_DARKNESS)
        for i, lamp in enumerate(m.lamps):
            if not lamp["lit"]:
                continue
            lx, ly = self._to_screen(*lamp["pos"])
            r = self.lamp_disc.get_width() // 2
            light.blit(self.lamp_disc, (lx - r, ly - r),
                       special_flags=pg.BLEND_RGB_MAX)
        # the thief's night eyes: a small pool so you always see yourself
        tx, ty = self._to_screen(thief.x, thief.y)
        pg.draw.circle(light, (110, 112, 132), (int(tx), int(ty)), 105)
        pg.draw.circle(light, (150, 150, 168), (int(tx), int(ty)), 58)
        w.blit(light, (0, 0), special_flags=pg.BLEND_RGB_MULT)

        # ------------------------------------------------- cones over all
        cones = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        for g in engine.guards:
            self._draw_cone(cones, engine, g, t)
        w.blit(cones, (0, 0))

        # actors above the darkness so the game stays readable
        for lamp in m.lamps:                      # ceiling roses
            lx, ly = self._to_screen(*lamp["pos"])
            on = lamp["lit"]
            pg.draw.circle(w, (30, 28, 24), (int(lx), int(ly)), 7)
            pg.draw.circle(w, C_LAMP_LIGHT if on else (70, 66, 58),
                           (int(lx), int(ly)), 3)
        for g in engine.guards:
            self._draw_guard(w, g, t)
        self._draw_thief(w, engine, t)

        # noise ring
        if engine.noise > 0:
            k = (t * 2.2) % 1.0
            pg.draw.circle(w, C_NOISE, (int(tx), int(ty)),
                           int(engine.noise * k), 1)

        self.screen.blit(w, (0, 0))
        self._draw_hud(engine, t)
        if engine.state == CRACKING:
            self._draw_dial(engine, t)

    def _draw_cone(self, layer, engine, g, t):
        m = engine.m
        alert = g.state == ALERT
        sus = g.state == SUSPICIOUS
        color = C_CONE_ALERT if alert else C_CONE
        pulse = 0.5 + 0.5 * math.sin(t * (9 if alert else 3))
        alpha = int(34 + (26 if alert else 10) * pulse)
        pts = [self._to_screen(g.x, g.y)]
        rays = 22
        for i in range(rays + 1):
            a = g.facing - FOV_ANGLE / 2 + FOV_ANGLE * i / rays
            # march the ray to the first wall
            reach_lit = FOV_RANGE
            step = 14.0
            dist = step
            hit = FOV_RANGE_DARK
            while dist <= FOV_RANGE:
                px = g.x + math.cos(a) * dist
                py = g.y + math.sin(a) * dist
                if m.blocked(g.x, g.y, px, py):
                    break
                hit = dist if not m.is_lit(px, py) \
                    and dist <= FOV_RANGE_DARK else dist
                if not m.is_lit(px, py) and dist >= FOV_RANGE_DARK:
                    break
                dist += step
            pts.append(self._to_screen(g.x + math.cos(a) * min(hit, dist),
                                       g.y + math.sin(a) * min(hit, dist)))
        if len(pts) > 2:
            pg.draw.polygon(layer, (*color, alpha), pts)
            pg.draw.polygon(layer, (*color, min(120, alpha + 40)), pts, 1)
        if sus or alert:
            x, y = self._to_screen(g.x, g.y)
            img = self.font_mid.render("!" if alert else "?", True,
                                       C_DANGER if alert else C_GOLD)
            layer.blit(img, (x - 6, y - 44))

    def _draw_guard(self, w, g, t):
        x, y = self._to_screen(g.x, g.y)
        body = C_GUARD_ALERT if g.state == ALERT else C_GUARD
        pg.draw.circle(w, (0, 0, 0), (int(x) + 2, int(y) + 3), 12)
        pg.draw.circle(w, body, (int(x), int(y)), 12)
        pg.draw.circle(w, _mix(body, (255, 255, 255), 0.25),
                       (int(x), int(y)), 12, 2)
        hx = x + math.cos(g.facing) * 7
        hy = y + math.sin(g.facing) * 7
        pg.draw.circle(w, _mix(body, (0, 0, 0), 0.4),
                       (int(hx), int(hy)), 5)

    def _draw_thief(self, w, engine, t):
        thief = engine.thief
        x, y = self._to_screen(thief.x, thief.y)
        bob = math.sin(t * 10) * thief.moving * 0.8
        pg.draw.circle(w, (0, 0, 0), (int(x) + 2, int(y) + 3), 11)
        pg.draw.circle(w, C_THIEF, (int(x), int(y + bob)), 11)
        pg.draw.circle(w, (86, 90, 100), (int(x), int(y + bob)), 11, 2)
        hx = x + math.cos(thief.face) * 6
        hy = y + bob + math.sin(thief.face) * 6
        pg.draw.circle(w, (200, 180, 150), (int(hx), int(hy)), 3)

    # ----------------------------------------------------------------- HUD
    def _draw_hud(self, engine, t):
        scr = self.screen
        pg.draw.rect(scr, (12, 11, 10), (0, HEIGHT - 54, WIDTH, 54))
        pg.draw.line(scr, (60, 54, 46), (0, HEIGHT - 54),
                     (WIDTH, HEIGHT - 54))
        y = HEIGHT - 34
        # the eye: how close you are to being made
        k = engine.seen_now
        eye_c = _mix((70, 76, 66), C_DANGER, k)
        pg.draw.ellipse(scr, eye_c, (24, y - 9, 34, 18), 2)
        pg.draw.circle(scr, eye_c, (41, y), 5 + int(3 * k))
        label = "ЗАМЕТИЛИ!" if k >= 1.0 else "тихо"
        scr.blit(self.font_small.render(label, True, eye_c), (68, y - 8))
        # noise
        scr.blit(self.font_small.render("шум", True, C_NOISE),
                 (170, y - 8))
        for i in range(int(engine.noise / 48)):
            pg.draw.rect(scr, C_NOISE, (212 + i * 12, y - 6, 9, 12))
        # objective
        goal = ("вскройте сейф" if engine.state == CASING
                else "крутите диск" if engine.state == CRACKING
                else "УХОДИТЕ К ВЫХОДУ")
        scr.blit(self.font_ui.render(goal, True,
                                     C_GOLD if engine.state == LOOTED
                                     else C_TEXT), (320, y - 10))
        stats = "дело %d/5  ·  %d:%02d  ·  призрак прошёл за %d:%02d" % (
            engine.mission + 1, engine.time // 60, engine.time % 60,
            engine.ghost_time // 60, engine.ghost_time % 60)
        scr.blit(self.font_small.render(stats, True, C_DIM), (620, y - 8))
        scr.blit(self.font_small.render(
            "Shift красться · Space бег · E действие", True, C_DIM),
            (WIDTH - 300, y - 8))
        if engine.alarm > 0:
            img = self.font_ui.render("ТРЕВОГА %.0f" % engine.alarm, True,
                                      C_DANGER)
            scr.blit(img, (WIDTH // 2 - 50, 16))

    def _draw_dial(self, engine, t):
        scr = self.screen
        cx, cy = WIDTH // 2, HEIGHT // 2 - 40
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((6, 6, 8, 140))
        scr.blit(veil, (0, 0))
        pg.draw.circle(scr, (26, 27, 32), (cx, cy), 120)
        pg.draw.circle(scr, (120, 126, 138), (cx, cy), 120, 3)
        for ring in range(SAFE_RINGS):
            r = 100 - ring * 26
            done = ring < engine.safe_ring
            cur = ring == engine.safe_ring
            col = C_GOLD if done else (90, 94, 104) if not cur \
                else (170, 176, 190)
            pg.draw.circle(scr, col, (cx, cy), r, 3 if cur else 2)
            if cur:
                sweet = (engine.m.seed * (ring + 3) * 0.618) % math.tau
                win = SAFE_WINDOW[ring]
                pts = [(cx, cy)]
                for i in range(9):
                    a = sweet - win / 2 + win * i / 8
                    pts.append((cx + math.cos(a) * r,
                                cy + math.sin(a) * r))
                lay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
                pg.draw.polygon(lay, (255, 205, 100, 60), pts)
                scr.blit(lay, (0, 0))
        a = engine.dial
        pg.draw.line(scr, C_DANGER, (cx, cy),
                     (cx + math.cos(a) * 104, cy + math.sin(a) * 104), 3)
        pg.draw.circle(scr, (200, 205, 215), (cx, cy), 6)
        scr.blit(self.font_ui.render(
            "SPACE — крутить, отпустить в жёлтой зоне · Esc — отойти",
            True, C_TEXT), (cx - 250, cy + 150))

    # ================================================================ menus
    def draw_menu(self, t, records, cursor):
        self.screen.fill((10, 9, 8))
        rng = random.Random(3)
        for i in range(90):
            x, y = rng.randrange(WIDTH), rng.randrange(HEIGHT)
            self.screen.fill((16 + rng.randrange(8),) * 3, (x, y, 2, 2))
        cx = WIDTH // 2
        img = self.font_big.render("МЕДВЕЖАТНИК", True, C_GOLD)
        self.screen.blit(img, img.get_rect(center=(cx, 120)))
        sub = self.font_ui.render(
            "пять особняков, одна ночь, ни одного лишнего звука", True,
            C_DIM)
        self.screen.blit(sub, sub.get_rect(center=(cx, 172)))
        y = 250
        for i in range(5):
            rec = records.get(str(i))
            unlocked = i == 0 or records.get(str(i - 1)) is not None
            sel = i == cursor
            color = C_TEXT if unlocked else (70, 66, 60)
            if sel:
                pg.draw.rect(self.screen, (36, 32, 26),
                             (cx - 330, y - 8, 660, 40), border_radius=6)
                pg.draw.rect(self.screen, C_GOLD,
                             (cx - 330, y - 8, 660, 40), 1,
                             border_radius=6)
            name = "Дело %d" % (i + 1)
            if not unlocked:
                name += "   (сначала предыдущее)"
            img = self.font_ui.render(name, True, color)
            self.screen.blit(img, (cx - 310, y))
            if rec:
                extra = "%d:%02d" % (rec["time"] // 60, rec["time"] % 60)
                if rec.get("ghost"):
                    extra += "  ПРИЗРАК"
                img = self.font_ui.render(extra, True,
                                          C_GOLD if rec.get("ghost")
                                          else C_DIM)
                self.screen.blit(img, (cx + 150, y))
            y += 52
        hint = self.font_ui.render(
            "стрелки — выбрать · Enter — на дело · H — как работать · "
            "Esc — уйти", True, C_DIM)
        self.screen.blit(hint, hint.get_rect(center=(cx, HEIGHT - 70)))

    def draw_help(self):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((5, 5, 6, 225))
        self.screen.blit(veil, (0, 0))
        cx = WIDTH // 2
        img = self.font_mid.render("ПАМЯТКА МЕДВЕЖАТНИКА", True, C_GOLD)
        self.screen.blit(img, img.get_rect(center=(cx, 80)))
        tips = (
            "Конус — это взгляд. В освещённой комнате он длинный, в тёмной — короткий.",
            "Мелькнули на краю — охранник пойдёт проверить. Смотрел на вас полсекунды — погоня.",
            "Бег слышно через стены: круг на полу — это ваш шум. Крадучись вы беззвучны.",
            "Выключатель гасит комнату. Охранник заметит и пойдёт включать — этим и пользуйтесь.",
            "Сейф: держите SPACE, стрелка крутится; отпустите в жёлтой зоне. Промах — щелчок на весь дом.",
            "После вскрытия дом просыпается. Дорога назад всегда страшнее дороги туда.",
            "Поимка — это касание. Пока есть стены и темнота, вас не существует.",
            "Призрак — маршрут решателя: он прошёл ни разу не мелькнув. Его время — ваш норматив.")
        y = 140
        for tip in tips:
            img = self.font_ui.render("— " + tip, True, C_TEXT)
            self.screen.blit(img, (cx - 470, y))
            y += 40
        img = self.font_ui.render("H — закрыть", True, C_DIM)
        self.screen.blit(img, img.get_rect(center=(cx, y + 24)))

    def draw_end(self, engine, t, won):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((4, 4, 6, 210))
        self.screen.blit(veil, (0, 0))
        cx = WIDTH // 2
        title = "УШЁЛ КРАСИВО" if won else "ВЗЯЛИ С ПОЛИЧНЫМ"
        color = C_GOLD if won else C_DANGER
        img = self.font_big.render(title, True, color)
        self.screen.blit(img, img.get_rect(center=(cx, 200)))
        if won:
            ghost = not engine.spotted_ever
            lines = ["время %d:%02d — призрак прошёл за %d:%02d" % (
                engine.time // 60, engine.time % 60,
                engine.ghost_time // 60, engine.ghost_time % 60)]
            lines.append("вас не видели ни разу — чистый ПРИЗРАК"
                         if ghost else "вас замечали: в следующий раз тише")
        else:
            lines = ["сейф остался при хозяевах",
                     "R — той же ночью ещё раз"]
        y = 280
        for ln in lines:
            img = self.font_ui.render(ln, True, C_TEXT)
            self.screen.blit(img, img.get_rect(center=(cx, y)))
            y += 34
        if int(t * 1.6) % 2:
            img = self.font_ui.render(
                "Enter — дальше · R — заново · Esc — в меню", True, C_DIM)
            self.screen.blit(img, img.get_rect(center=(cx, y + 40)))
