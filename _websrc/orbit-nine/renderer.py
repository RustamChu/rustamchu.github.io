"""Everything that puts pixels on the screen."""
from __future__ import annotations

import math

import pygame as pg

import graphics
from settings import (BALL_R, BLACKHOLE_HORIZON, C_ACCENT, C_BAD, C_BALL,
                      C_BLACKHOLE, C_DIM, C_GOLD, C_GOOD, C_HINT, C_PREVIEW,
                      C_PULSAR, C_TEXT, C_TRAIL, C_WORMHOLE, COURSE_HOLES,
                      GOAL_R, HEIGHT, PAR, TITLE, WIDTH)


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_big = pg.font.Font(None, 92)
        self.font_mid = pg.font.Font(None, 40)
        self.font_ui = pg.font.Font(None, 28)
        self.font_small = pg.font.Font(None, 22)
        self.background = None
        self._bg_seed = None
        self.baked = {}
        self._baked_level = None

    # ------------------------------------------------------------- helpers
    def _text(self, font, text, color, pos, center=False, shadow=True,
              alpha=None):
        image = font.render(text, True, color)
        if alpha is not None:
            image.set_alpha(alpha)
        rect = image.get_rect()
        if shadow:
            dark = font.render(text, True, (4, 5, 12))
            drect = dark.get_rect()
            if center:
                drect.center = (pos[0] + 2, pos[1] + 2)
            else:
                drect.topleft = (pos[0] + 2, pos[1] + 2)
            if alpha is not None:
                dark.set_alpha(alpha)
            self.screen.blit(dark, drect)
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        self.screen.blit(image, rect)
        return rect

    def _ensure_level(self, engine):
        if self._bg_seed != engine.seed:
            self.background = graphics.make_background(engine.seed)
            self._bg_seed = engine.seed
        if self._baked_level is not engine.level:
            self.baked = graphics.bake_bodies(engine.level)
            self._baked_level = engine.level

    # ================================================================ field
    def draw_field(self, engine, ui, t):
        self._ensure_level(engine)
        self.screen.blit(self.background, (0, 0))
        level = engine.level

        for wx, wy, wr in level.wormholes:
            self._draw_wormhole(wx, wy, wr, t)
        for body in level.bodies:
            self._draw_body(body, t)
        self._draw_goal(level.goal, t)

        if ui.get("show_hint"):
            self._draw_dots(engine.hint(), C_HINT, alpha=150)

        aim = ui.get("aim")
        if aim and engine.state == "aim":
            self._draw_aim(engine, aim)

        self._draw_trail(engine)
        self._draw_ball(engine, t)

    def _draw_body(self, body, t):
        px, py = int(body.x), int(body.y)
        if body.kind == "pulsar":
            phase = (t * 1.4) % 1.0
            for k in range(3):
                p = (phase + k / 3) % 1.0
                radius = int(body.r + 6 + p * 34)
                alpha = int(120 * (1 - p))
                ring = pg.Surface((radius * 2 + 2, radius * 2 + 2),
                                  pg.SRCALPHA)
                pg.draw.circle(ring, (*C_PULSAR, alpha),
                               (radius + 1, radius + 1), radius, 2)
                self.screen.blit(ring, (px - radius - 1, py - radius - 1))
            graphics.glow(self.screen, px, py, int(body.r * 1.6), C_PULSAR,
                          alpha=100)
            pg.draw.circle(self.screen, (240, 220, 255), (px, py),
                           int(body.r * 0.6))
            pg.draw.circle(self.screen, C_PULSAR, (px, py), int(body.r), 2)
        elif body.kind == "blackhole":
            horizon = int(body.r * BLACKHOLE_HORIZON)
            graphics.glow(self.screen, px, py, horizon + 14, C_BLACKHOLE,
                          alpha=110)
            spin = t * 2.2
            for k in range(2):
                rect = pg.Rect(0, 0, horizon * 2, int(horizon * 0.8))
                rect.center = (px, py)
                pg.draw.arc(self.screen, C_BLACKHOLE, rect,
                            spin + k * math.pi, spin + k * math.pi + 2.2, 2)
            pg.draw.circle(self.screen, (2, 2, 6), (px, py), int(body.r))
            pg.draw.circle(self.screen, (90, 40, 30), (px, py),
                           int(body.r), 1)
        else:
            sprite = self.baked.get(id(body))
            if sprite is not None:
                self.screen.blit(sprite, sprite.get_rect(center=(px, py)))

    def _draw_wormhole(self, wx, wy, wr, t):
        px, py = int(wx), int(wy)
        graphics.glow(self.screen, px, py, wr + 16, C_WORMHOLE, alpha=90)
        for k in range(3):
            angle = t * 2.6 + k * math.tau / 3
            radius = wr - 3
            pg.draw.arc(self.screen, C_WORMHOLE,
                        pg.Rect(px - radius, py - radius, radius * 2,
                                radius * 2),
                        angle, angle + 1.6, 2)
        pg.draw.circle(self.screen, (10, 30, 28), (px, py), wr - 8)
        pg.draw.circle(self.screen, C_WORMHOLE, (px, py), wr - 8, 1)

    def _draw_goal(self, goal, t):
        gx, gy = int(goal[0]), int(goal[1])
        graphics.glow(self.screen, gx, gy, GOAL_R + 18, C_GOLD, alpha=110)
        spin = t * 1.8
        for k in range(6):
            a0 = spin + k * math.tau / 6
            pg.draw.arc(self.screen, C_GOLD,
                        pg.Rect(gx - GOAL_R, gy - GOAL_R, GOAL_R * 2,
                                GOAL_R * 2), a0, a0 + 0.7, 3)
        pg.draw.circle(self.screen, (30, 24, 10), (gx, gy), GOAL_R - 5)
        pulse = 2 + int(1.6 * (1 + math.sin(t * 5)))
        pg.draw.circle(self.screen, C_GOLD, (gx, gy), pulse)
        self._text(self.font_small, "ЛУНКА", C_GOLD, (gx, gy - GOAL_R - 14),
                   center=True, shadow=False)

    def _draw_dots(self, points, color, alpha=255):
        total = len(points)
        for i, (x, y) in enumerate(points):
            fade = 1.0 - i / max(1, total)
            dot = pg.Surface((6, 6), pg.SRCALPHA)
            pg.draw.circle(dot, (*color, int(alpha * (0.35 + 0.65 * fade))),
                           (3, 3), 3 if i % 2 == 0 else 2)
            self.screen.blit(dot, (int(x) - 3, int(y) - 3))

    def _draw_aim(self, engine, aim):
        angle, power = aim
        points, outcome = engine.preview(angle, power)
        self._draw_dots(points, C_PREVIEW, alpha=210)
        # power arc around the ball
        bx, by = engine.ball
        radius = 16
        rect = pg.Rect(int(bx) - radius, int(by) - radius, radius * 2,
                       radius * 2)
        pg.draw.arc(self.screen, C_DIM, rect, 0, math.tau, 2)
        pg.draw.arc(self.screen, C_ACCENT if power < 0.99 else C_BAD, rect,
                    -math.pi / 2, -math.pi / 2 + power * math.tau, 3)

    def _draw_trail(self, engine):
        total = len(engine.trail)
        for i, (x, y) in enumerate(engine.trail):
            fade = (i + 1) / max(1, total)
            size = 1 + int(2.5 * fade)
            dot = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
            pg.draw.circle(dot, (*C_TRAIL, int(140 * fade)), (size, size),
                           size)
            self.screen.blit(dot, (int(x) - size, int(y) - size))

    def _draw_ball(self, engine, t):
        if engine.state in ("hole_done", "done"):
            return
        bx, by = int(engine.ball[0]), int(engine.ball[1])
        graphics.glow(self.screen, bx, by, BALL_R + 10, C_TRAIL, alpha=120)
        pg.draw.circle(self.screen, C_BALL, (bx, by), BALL_R)
        pg.draw.circle(self.screen, (150, 200, 230), (bx, by), BALL_R, 1)

    # ================================================================== hud
    def draw_hud(self, engine, ui, t):
        self._text(self.font_ui,
                   "ЛУНКА {} / {}".format(engine.hole_idx, COURSE_HOLES),
                   C_TEXT, (18, 12))
        self._text(self.font_ui, "ПАР {}".format(PAR), C_DIM, (170, 12))
        self._text(self.font_ui,
                   "УДАРЫ {}".format(engine.strokes[engine.hole_idx]),
                   C_ACCENT, (256, 12))
        self._text(self.font_ui, "ИТОГ {}".format(engine.relative_score),
                   C_GOLD, (400, 12))

        hints = "ЛКМ тяни и отпусти   R заново   H подсказка   TAB счёт   ESC меню"
        self._text(self.font_small, hints, C_DIM, (WIDTH // 2, HEIGHT - 16),
                   center=True, shadow=False)

        for kind, payload in engine.events:
            if kind == "penalty":
                self._penalty_banner = (payload, t)
        engine.events = [e for e in engine.events if e[0] not in
                         ("penalty", "warp", "sunk")]

        if engine.penalty_flash > 0:
            alpha = int(220 * min(1.0, engine.penalty_flash))
            self._text(self.font_mid, getattr(self, "_penalty_banner",
                                              ("штраф +1", 0))[0],
                       C_BAD, (WIDTH // 2, 90), center=True, alpha=alpha)

    # ============================================================= overlays
    def dim(self, alpha=185):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((4, 5, 12, alpha))
        self.screen.blit(veil, (0, 0))

    def draw_menu(self, save_exists, t):
        self.screen.fill((8, 9, 18))
        if self.background is None:
            self.background = graphics.make_background(1)
            self._bg_seed = 1
        self.screen.blit(self.background, (0, 0))
        cx = WIDTH // 2

        # a demo planet with an orbiting ball, just for looks
        graphics.glow(self.screen, cx, 190, 90, (240, 150, 90), alpha=80)
        for i in range(64, 0, -1):
            tt = i / 64
            color = (int(240 - 130 * tt), int(150 - 110 * tt),
                     int(90 - 60 * tt))
            pg.draw.circle(self.screen, color, (cx, 190), i)
        angle = t * 1.1
        ox = cx + int(120 * math.cos(angle))
        oy = 190 + int(46 * math.sin(angle))
        graphics.glow(self.screen, ox, oy, 12, C_TRAIL, alpha=140)
        pg.draw.circle(self.screen, C_BALL, (ox, oy), 5)
        pg.draw.circle(self.screen, (60, 66, 96), (cx, 190), 120, 1)

        self._text(self.font_big, TITLE, C_TEXT, (cx, 330), center=True)
        self._text(self.font_ui, "космический мини-гольф: девять лунок, "
                   "настоящая гравитация", C_DIM, (cx, 382), center=True)

        y = 450
        self._text(self.font_mid, "[n]  новая трасса", C_TEXT, (cx, y),
                   center=True)
        y += 44
        color = C_TEXT if save_exists else (72, 76, 96)
        suffix = "" if save_exists else "  (сохранения нет)"
        self._text(self.font_mid, "[c]  продолжить" + suffix, color, (cx, y),
                   center=True)
        y += 44
        self._text(self.font_mid, "[?]  как играть      [esc] выход", C_DIM,
                   (cx, y), center=True)

    def draw_help(self):
        self.dim()
        rect = pg.Rect(0, 0, 760, 500)
        rect.center = (WIDTH // 2, HEIGHT // 2)
        pg.draw.rect(self.screen, (12, 14, 26), rect, border_radius=12)
        pg.draw.rect(self.screen, (70, 80, 120), rect, 2, border_radius=12)
        self._text(self.font_mid, "КАК ИГРАТЬ", C_GOLD,
                   (rect.centerx, rect.y + 30), center=True)
        rows = [
            ("мышь", "зажмите у шара, оттяните и отпустите — рогатка"),
            ("пунктир", "честный прогноз траектории с учётом гравитации"),
            ("R", "переиграть лунку с нуля"),
            ("H", "подсказка: удар, которым трассу прошёл генератор"),
            ("TAB", "карточка счёта"),
            ("ESC", "в меню — партия сохраняется"),
        ]
        y = rect.y + 76
        for key, what in rows:
            self._text(self.font_ui, key, C_GOLD, (rect.x + 40, y))
            self._text(self.font_ui, what, C_TEXT, (rect.x + 170, y))
            y += 36
        tips = [
            "Планеты притягивают, пульсары отталкивают, чёрная дыра — штраф",
            "и возврат. Червоточины переносят шар, сохраняя скорость.",
            "Улетел за экран — тоже штраф. Пар каждой лунки — {}.".format(PAR),
            "Каждая лунка гарантированно проходится в один удар.",
        ]
        y += 6
        for line in tips:
            self._text(self.font_small, line, C_DIM, (rect.x + 40, y))
            y += 26

    def draw_scorecard(self, engine):
        self.dim(170)
        rect = pg.Rect(0, 0, 640, 420)
        rect.center = (WIDTH // 2, HEIGHT // 2)
        pg.draw.rect(self.screen, (12, 14, 26), rect, border_radius=12)
        pg.draw.rect(self.screen, (70, 80, 120), rect, 2, border_radius=12)
        self._text(self.font_mid, "КАРТОЧКА СЧЁТА", C_GOLD,
                   (rect.centerx, rect.y + 30), center=True)
        y = rect.y + 72
        for hole in range(1, COURSE_HOLES + 1):
            played = engine.done[hole]
            strokes = engine.strokes[hole]
            current = hole == engine.hole_idx and not engine.finished
            name = "лунка {:>2}".format(hole)
            if current:
                name = "> " + name
            value = str(strokes) if (played or strokes) else "—"
            color = C_TEXT if played else (C_ACCENT if current else C_DIM)
            self._text(self.font_ui, name, color, (rect.x + 80, y))
            self._text(self.font_ui, value, color, (rect.x + 320, y))
            if played:
                diff = strokes - PAR
                mark = "E" if diff == 0 else "{:+d}".format(diff)
                mark_color = C_GOOD if diff <= 0 else C_BAD
                self._text(self.font_ui, mark, mark_color, (rect.x + 420, y))
            y += 32
        self._text(self.font_ui,
                   "итог: {}   (пар {})".format(engine.relative_score,
                                                engine.total_par),
                   C_GOLD, (rect.centerx, rect.bottom - 34), center=True)

    def draw_hole_done(self, engine, t):
        strokes = engine.strokes[engine.hole_idx]
        diff = strokes - PAR
        titles = {1: "С ОДНОГО УДАРА!", }
        if strokes == 1:
            title, color = "С ОДНОГО УДАРА!", C_GOLD
        elif diff < 0:
            title, color = "НИЖЕ ПАРА", C_GOOD
        elif diff == 0:
            title, color = "ТОЧНО В ПАР", C_TEXT
        else:
            title, color = "+{} к пару".format(diff), C_BAD
        self.dim(120)
        cx = WIDTH // 2
        self._text(self.font_big, title, color, (cx, HEIGHT // 2 - 60),
                   center=True)
        self._text(self.font_mid, "ударов: {}".format(strokes), C_TEXT,
                   (cx, HEIGHT // 2 + 10), center=True)
        label = "SPACE — следующая лунка" if engine.hole_idx < COURSE_HOLES \
            else "SPACE — итоги трассы"
        blink = 150 + int(100 * (0.5 + 0.5 * math.sin(t * 5)))
        self._text(self.font_ui, label, C_ACCENT, (cx, HEIGHT // 2 + 70),
                   center=True, alpha=blink)

    def draw_course_done(self, engine):
        self.dim(200)
        cx = WIDTH // 2
        diff = engine.total_strokes - engine.total_par
        if diff < 0:
            title, color = "НИЖЕ ПАРА!", C_GOLD
        elif diff == 0:
            title, color = "РОВНО В ПАР", C_GOOD
        else:
            title, color = "ТРАССА ПРОЙДЕНА", C_TEXT
        self._text(self.font_big, title, color, (cx, 150), center=True)
        self._text(self.font_mid,
                   "{} ударов на {} лунках   итог {}".format(
                       engine.total_strokes, COURSE_HOLES,
                       engine.relative_score),
                   C_TEXT, (cx, 220), center=True)

        aces = sum(1 for h in range(1, COURSE_HOLES + 1)
                   if engine.done[h] and engine.strokes[h] == 1)
        if aces:
            self._text(self.font_ui,
                       "лунок с одного удара: {}".format(aces), C_GOLD,
                       (cx, 262), center=True)

        y = 320
        for hole in range(1, COURSE_HOLES + 1):
            strokes = engine.strokes[hole]
            diff = strokes - PAR
            mark = "E" if diff == 0 else "{:+d}".format(diff)
            color = C_GOOD if diff <= 0 else C_BAD
            self._text(self.font_ui,
                       "лунка {}: {} ({})".format(hole, strokes, mark),
                       color, (cx, y), center=True)
            y += 28
        self._text(self.font_mid, "[n] новая трасса      [esc] меню",
                   C_ACCENT, (cx, y + 26), center=True)
