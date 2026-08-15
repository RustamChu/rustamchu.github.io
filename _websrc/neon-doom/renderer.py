"""Rendering: background, world objects, HUD and the menu screens."""
import math
from operator import itemgetter

import pygame as pg

import graphics
from settings import (WIDTH, HEIGHT, HALF_WIDTH, HALF_HEIGHT, PLAYER_MAX_HEALTH,
                      DIFFICULTIES, C_UI_PINK, C_UI_CYAN, C_UI_YELLOW, C_UI_RED,
                      C_UI_GREEN, C_UI_DARK)

MINIMAP_COLORS = {1: C_UI_PINK, 2: C_UI_CYAN, 3: C_UI_YELLOW,
                  4: C_UI_GREEN, 5: (190, 130, 255)}


class Renderer:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.objects_to_render = []

        self.wall_textures = graphics.make_wall_textures()
        self.sky = graphics.make_sky()
        self.floor = graphics.make_floor()
        self.vignette = graphics.make_vignette()

        self.font_big = pg.font.Font(None, 110)
        self.font_mid = pg.font.Font(None, 52)
        self.font_small = pg.font.Font(None, 34)

        self.minimap_scale = 9
        self.minimap_bg = None
        self.build_minimap()

    def build_minimap(self):
        """(Re)draw the static part of the minimap. Called on every new game."""
        game_map = self.game.map
        s = self.minimap_scale
        self.minimap_bg = pg.Surface((game_map.cols * s, game_map.rows * s), pg.SRCALPHA)
        self.minimap_bg.fill((10, 5, 25, 160))
        for (i, j), tex in game_map.world_map.items():
            pg.draw.rect(self.minimap_bg, MINIMAP_COLORS[tex], (i * s, j * s, s, s))

    # ------------------------------------------------------------ background
    def draw_background(self):
        # the sky scrolls with the view angle
        offset = int((self.game.player.angle / math.tau) * WIDTH * 2) % (WIDTH * 2)
        self.screen.blit(self.sky, (-offset, 0))
        self.screen.blit(self.sky, (WIDTH * 2 - offset, 0))
        self.screen.blit(self.floor, (0, HALF_HEIGHT))

    # ------------------------------------------------------------ world
    def draw_world(self):
        # painter's algorithm: far things first, so sprites hide behind walls
        self.objects_to_render.sort(key=itemgetter(0), reverse=True)
        blit = self.screen.blit
        for _, image, pos in self.objects_to_render:
            blit(image, pos)
        self.objects_to_render = []

    # ------------------------------------------------------------ helpers
    def _text(self, font, text, color, center=None, topleft=None, shadow=True):
        if shadow:
            sh = font.render(text, True, (10, 0, 20))
            rect = sh.get_rect()
            if center:
                rect.center = (center[0] + 3, center[1] + 3)
            else:
                rect.topleft = (topleft[0] + 3, topleft[1] + 3)
            self.screen.blit(sh, rect)
        img = font.render(text, True, color)
        rect = img.get_rect()
        if center:
            rect.center = center
        else:
            rect.topleft = topleft
        self.screen.blit(img, rect)

    def _crosshair(self):
        hit = self.game.weapon.hit_marker > 0
        color = C_UI_RED if hit else C_UI_CYAN
        if hit:
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                pg.draw.line(self.screen, color,
                             (HALF_WIDTH + sx * 6, HALF_HEIGHT + sy * 6),
                             (HALF_WIDTH + sx * 16, HALF_HEIGHT + sy * 16), 3)
            return
        for dx, dy in ((-14, 0), (14, 0), (0, -14), (0, 14)):
            pg.draw.line(self.screen, color,
                         (HALF_WIDTH + dx * 0.4, HALF_HEIGHT + dy * 0.4),
                         (HALF_WIDTH + dx, HALF_HEIGHT + dy), 3)

    # ------------------------------------------------------------ hud
    def draw_hud(self):
        self._crosshair()

        # health bar
        bar = pg.Rect(24, HEIGHT - 56, 300, 30)
        pg.draw.rect(self.screen, C_UI_DARK, bar.inflate(8, 8), border_radius=8)
        hp = self.game.player.health / PLAYER_MAX_HEALTH
        color = C_UI_GREEN if hp > 0.55 else (C_UI_YELLOW if hp > 0.25 else C_UI_RED)
        if hp > 0:
            fill = bar.copy()
            fill.width = max(6, int(bar.width * hp))
            pg.draw.rect(self.screen, color, fill, border_radius=8)
        pg.draw.rect(self.screen, C_UI_PINK, bar.inflate(8, 8), 2, border_radius=8)
        self._text(self.font_small, f"HP {self.game.player.health}",
                   (255, 255, 255), center=bar.center, shadow=False)

        # score, remaining demons, difficulty
        alive = sum(1 for n in self.game.npcs if n.active)
        self._text(self.font_mid, f"SCORE {self.game.score}", C_UI_YELLOW,
                   topleft=(WIDTH - 340, HEIGHT - 62))
        self._text(self.font_small, f"DEMONS LEFT: {alive}", C_UI_PINK,
                   topleft=(WIDTH - 340, HEIGHT - 100))
        self._text(self.font_small, self.game.difficulty["name"], C_UI_CYAN,
                   topleft=(WIDTH - 340, HEIGHT - 136))

        self.draw_minimap()

        # damage flash
        if self.game.player.hurt_flash > 0:
            flash = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            flash.fill((255, 30, 60, int(110 * self.game.player.hurt_flash)))
            self.screen.blit(flash, (0, 0))

        self.screen.blit(self.vignette, (0, 0))

    def draw_minimap(self):
        mm_x, mm_y = 20, 20
        self.screen.blit(self.minimap_bg, (mm_x, mm_y))
        s = self.minimap_scale
        for npc in self.game.npcs:
            if npc.alive and not npc.dying:
                # demons that have spotted you glow brighter
                color = C_UI_RED if npc.sees_player else (150, 60, 80)
                pg.draw.circle(self.screen, color,
                               (mm_x + int(npc.x * s), mm_y + int(npc.y * s)), 3)
        for pickup in self.game.pickups:
            if not pickup.collected:
                color = C_UI_CYAN if pickup.kind == "gem" else (255, 235, 240)
                pg.draw.circle(self.screen, color,
                               (mm_x + int(pickup.x * s), mm_y + int(pickup.y * s)), 2)
        px = mm_x + int(self.game.player.x * s)
        py = mm_y + int(self.game.player.y * s)
        a = self.game.player.angle
        pg.draw.circle(self.screen, (255, 255, 255), (px, py), 4)
        pg.draw.line(self.screen, (255, 255, 255), (px, py),
                     (px + int(10 * math.cos(a)), py + int(10 * math.sin(a))), 2)

    # ------------------------------------------------------------ screens
    def _overlay(self, tint):
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill(tint)
        self.screen.blit(overlay, (0, 0))

    def draw_menu(self):
        self.draw_background()
        self._overlay((10, 0, 30, 170))
        self._text(self.font_big, "NEON DOOM", C_UI_PINK,
                   center=(HALF_WIDTH, HALF_HEIGHT - 165))
        self._text(self.font_mid, "a colorful retro shooter", C_UI_CYAN,
                   center=(HALF_WIDTH, HALF_HEIGHT - 95))

        # difficulty picker
        self._text(self.font_small, "difficulty  (1 / 2 / 3)", (200, 200, 220),
                   center=(HALF_WIDTH, HALF_HEIGHT - 30))
        spacing = 220
        start = HALF_WIDTH - spacing
        for i, diff in enumerate(DIFFICULTIES):
            selected = i == self.game.difficulty_idx
            color = C_UI_YELLOW if selected else (130, 130, 160)
            label = f"[{diff['name']}]" if selected else diff["name"]
            self._text(self.font_small, label, color,
                       center=(start + i * spacing, HALF_HEIGHT + 15))

        self._text(self.font_mid, "ENTER - play", (255, 255, 255),
                   center=(HALF_WIDTH, HALF_HEIGHT + 85))
        self._text(self.font_small,
                   "WASD move | mouse or arrows look | LMB / SPACE shoot | SHIFT sprint",
                   C_UI_YELLOW, center=(HALF_WIDTH, HALF_HEIGHT + 145))
        self._text(self.font_small, "Kill every demon. Collect gems. Survive.",
                   (200, 200, 220), center=(HALF_WIDTH, HALF_HEIGHT + 185))

    def _result_screen(self, tint, title, title_color):
        self._overlay(tint)
        self._text(self.font_big, title, title_color,
                   center=(HALF_WIDTH, HALF_HEIGHT - 80))
        self._text(self.font_mid, f"score: {self.game.score}", (255, 255, 255),
                   center=(HALF_WIDTH, HALF_HEIGHT + 5))
        self._text(self.font_small,
                   f"accuracy: {self.game.weapon.accuracy}%   "
                   f"time: {self.game.elapsed_seconds():.0f}s", C_UI_CYAN,
                   center=(HALF_WIDTH, HALF_HEIGHT + 55))
        self._text(self.font_mid, "R - play again | ESC - menu", C_UI_YELLOW,
                   center=(HALF_WIDTH, HALF_HEIGHT + 120))

    def draw_game_over(self):
        self._result_screen((60, 0, 10, 160), "YOU DIED", C_UI_RED)

    def draw_victory(self):
        self._result_screen((0, 30, 20, 160), "VICTORY!", C_UI_GREEN)
