"""Everything that puts pixels on the screen."""
from __future__ import annotations

import pygame as pg

import graphics
import tiles
from settings import (C_ARCANE, C_ASH, C_BLOOD, C_BONE, C_DIM, C_EMBER, C_GOLD,
                      C_PANEL, C_PANEL_EDGE, C_POISON, C_STAIRS, HEIGHT,
                      LIGHT_LEVELS, MAX_DEPTH, PANEL_H, TILE, TITLE, VIEW_H,
                      VIEW_PX_X, VIEW_PX_Y, VIEW_W, WIDTH)

LOG_LINES = 6
LOG_WIDTH = 74


class Renderer:
    def __init__(self, engine, screen):
        self.engine = engine
        self.screen = screen

        self.font_glyph = pg.font.Font(None, TILE + 8)
        self.font_ui = pg.font.Font(None, 24)
        self.font_small = pg.font.Font(None, 20)
        self.font_mid = pg.font.Font(None, 34)
        self.font_big = pg.font.Font(None, 96)

        self.tileset = graphics.build_tileset()
        self.glyphs = graphics.GlyphCache(self.font_glyph)
        self.cam_x = 0
        self.cam_y = 0

    # ------------------------------------------------------------- helpers
    def _text(self, surface, font, text, color, pos, center=False,
              shadow=True):
        if shadow:
            shade = font.render(text, True, (6, 5, 8))
            rect = shade.get_rect()
            if center:
                rect.center = (pos[0] + 2, pos[1] + 2)
            else:
                rect.topleft = (pos[0] + 2, pos[1] + 2)
            surface.blit(shade, rect)
        image = font.render(text, True, color)
        rect = image.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        surface.blit(image, rect)
        return rect

    def update_camera(self):
        gamemap = self.engine.gamemap
        player = self.engine.player
        self.cam_x = max(0, min(player.x - VIEW_W // 2, gamemap.width - VIEW_W))
        self.cam_y = max(0, min(player.y - VIEW_H // 2, gamemap.height - VIEW_H))

    def tile_to_screen(self, x, y):
        return (VIEW_PX_X + (x - self.cam_x) * TILE,
                VIEW_PX_Y + (y - self.cam_y) * TILE)

    def screen_to_tile(self, px, py):
        return ((px - VIEW_PX_X) // TILE + self.cam_x,
                (py - VIEW_PX_Y) // TILE + self.cam_y)

    # ---------------------------------------------------------------- world
    def draw_map(self):
        gamemap = self.engine.gamemap
        blit = self.screen.blit
        tileset = self.tileset
        memory = graphics.MEMORY_LEVEL

        for sy in range(VIEW_H):
            y = self.cam_y + sy
            if y >= gamemap.height:
                break
            row_tiles = gamemap.tiles[y]
            row_vis = gamemap.visible[y]
            row_seen = gamemap.explored[y]
            row_light = gamemap.light[y]
            py = VIEW_PX_Y + sy * TILE
            for sx in range(VIEW_W):
                x = self.cam_x + sx
                if x >= gamemap.width:
                    break
                if not row_seen[x]:
                    continue
                level = row_light[x] if row_vis[x] else memory
                variant = (x * 7 + y * 13) % graphics.VARIANTS
                blit(tileset[row_tiles[x]][level][variant],
                     (VIEW_PX_X + sx * TILE, py))

    def draw_entities(self):
        gamemap = self.engine.gamemap
        for entity in sorted(gamemap.entities, key=lambda e: e.render_order):
            if not gamemap.in_bounds(entity.x, entity.y):
                continue
            if not gamemap.visible[entity.y][entity.x]:
                continue
            px, py = self.tile_to_screen(entity.x, entity.y)
            if not (VIEW_PX_X - TILE < px < WIDTH and -TILE < py < HEIGHT - PANEL_H):
                continue
            level = gamemap.light[entity.y][entity.x]
            glyph = self.glyphs.get(entity.char, entity.color, level)
            rect = glyph.get_rect(center=(px + TILE // 2, py + TILE // 2))
            self.screen.blit(glyph, rect)

        # the player always reads clearly, whatever is underfoot
        player = self.engine.player
        px, py = self.tile_to_screen(player.x, player.y)
        pg.draw.circle(self.screen, (46, 38, 30),
                       (px + TILE // 2, py + TILE // 2), TILE // 2 - 1)
        glyph = self.glyphs.get(player.char, player.color, 0)
        self.screen.blit(glyph, glyph.get_rect(
            center=(px + TILE // 2, py + TILE // 2)))

    def draw_effects(self):
        for effect in self.engine.effects:
            px, py = self.tile_to_screen(effect["x"], effect["y"])
            progress = 1.0 - effect["ttl"] / float(effect["max_ttl"])
            image = self.font_ui.render(effect["text"], True, effect["color"])
            shade = self.font_ui.render(effect["text"], True, (8, 6, 10))
            image.set_alpha(int(255 * (1.0 - progress)))
            shade.set_alpha(int(255 * (1.0 - progress)))
            cx = px + TILE // 2
            cy = py - 4 - int(progress * 20)
            self.screen.blit(shade, shade.get_rect(center=(cx + 2, cy + 2)))
            self.screen.blit(image, image.get_rect(center=(cx, cy)))

    # ----------------------------------------------------------------- hud
    def _bar(self, x, y, w, h, value, maximum, fill, label):
        pg.draw.rect(self.screen, (30, 26, 32), (x, y, w, h), border_radius=4)
        if maximum > 0 and value > 0:
            width = max(2, int(w * value / float(maximum)))
            pg.draw.rect(self.screen, fill, (x, y, width, h), border_radius=4)
        pg.draw.rect(self.screen, C_PANEL_EDGE, (x, y, w, h), 1, border_radius=4)
        self._text(self.screen, self.font_small, label, C_BONE,
                   (x + w // 2, y + h // 2), center=True, shadow=True)

    def draw_panel(self):
        top = HEIGHT - PANEL_H
        pg.draw.rect(self.screen, C_PANEL, (0, top, WIDTH, PANEL_H))
        pg.draw.line(self.screen, C_PANEL_EDGE, (0, top), (WIDTH, top), 2)

        player = self.engine.player
        fighter = player.fighter
        level = player.level

        self._bar(16, top + 14, 240, 22, fighter.hp, fighter.max_hp, C_BLOOD,
                  "ОЗ {} / {}".format(fighter.hp, fighter.max_hp))
        self._bar(16, top + 44, 240, 16, level.current_xp,
                  level.xp_to_next_level, (70, 110, 160),
                  "ОПЫТ {} / {}".format(level.current_xp, level.xp_to_next_level))

        self._text(self.screen, self.font_small,
                   "уровень {}    сила {}    защита {}".format(
                       level.current_level, fighter.power, fighter.defense),
                   C_ASH, (16, top + 68))

        weapon = player.equipment.slots["weapon"]
        armor = player.equipment.slots["armor"]
        self._text(self.screen, self.font_small,
                   "оружие: " + (weapon.name if weapon else "голые руки"),
                   C_DIM, (16, top + 92))
        self._text(self.screen, self.font_small,
                   "броня: " + (armor.name if armor else "лохмотья"),
                   C_DIM, (16, top + 112))

        depth_color = C_STAIRS if self.engine.depth >= MAX_DEPTH else C_EMBER
        self._text(self.screen, self.font_ui,
                   "ГЛУБИНА {} / {}".format(self.engine.depth, MAX_DEPTH),
                   depth_color, (16, top + 136))

        self._text(self.screen, self.font_small,
                   "i рюкзак   g поднять   c герой   > вниз   "
                   "m журнал   ? помощь",
                   C_DIM, (WIDTH - 470, top + 138))

        # message log, newest at the bottom
        lines = []
        for text, color in self.engine.log.wrapped(LOG_WIDTH):
            lines.append((text, color))
            if len(lines) >= LOG_LINES:
                break
        y = top + 14 + (LOG_LINES - 1) * 20
        for text, color in lines:
            self._text(self.screen, self.font_small, text, color, (290, y),
                       shadow=False)
            y -= 20

    def draw_tooltip(self, mouse_pos):
        x, y = self.screen_to_tile(*mouse_pos)
        gamemap = self.engine.gamemap
        if not gamemap.in_bounds(x, y) or not gamemap.visible[y][x]:
            return
        names = gamemap.names_at(x, y)
        if not names:
            return
        image = self.font_small.render(names, True, C_BONE)
        px, py = self.tile_to_screen(x, y)
        box = pg.Rect(px, py - 24, image.get_width() + 12, 22)

        # never let the label sit on top of the player
        player = self.engine.player
        ppx, ppy = self.tile_to_screen(player.x, player.y)
        if box.colliderect(pg.Rect(ppx, ppy, TILE, TILE)):
            box.y = py + TILE + 2
        box.clamp_ip(pg.Rect(0, 0, WIDTH, HEIGHT - PANEL_H))
        pg.draw.rect(self.screen, (16, 14, 20), box, border_radius=4)
        pg.draw.rect(self.screen, C_PANEL_EDGE, box, 1, border_radius=4)
        self.screen.blit(image, (box.x + 6, box.y + 3))

        pg.draw.rect(self.screen, C_EMBER, (px, py, TILE, TILE), 1)

    # ------------------------------------------------------------ overlays
    def dim_screen(self, alpha=190):
        veil = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        veil.fill((6, 5, 9, alpha))
        self.screen.blit(veil, (0, 0))

    def draw_frame(self, rect, title=None):
        pg.draw.rect(self.screen, (14, 12, 18), rect, border_radius=8)
        pg.draw.rect(self.screen, C_PANEL_EDGE, rect, 2, border_radius=8)
        if title:
            self._text(self.screen, self.font_ui, title, C_EMBER,
                       (rect.centerx, rect.y + 20), center=True)

    def draw_targeting(self, tx, ty, radius):
        px, py = self.tile_to_screen(tx, ty)
        if radius > 0:
            size = (radius * 2 + 1) * TILE
            area = pg.Surface((size, size), pg.SRCALPHA)
            pg.draw.rect(area, (255, 150, 60, 40), area.get_rect(),
                         border_radius=6)
            pg.draw.rect(area, (255, 180, 90, 160), area.get_rect(), 2,
                         border_radius=6)
            self.screen.blit(area, (px - radius * TILE, py - radius * TILE))
        pg.draw.rect(self.screen, C_GOLD, (px, py, TILE, TILE), 2)

    def draw_menu(self, selected_slot_exists):
        self.screen.fill((7, 6, 10))
        # ember glow behind the title
        glow = pg.Surface((WIDTH, 320), pg.SRCALPHA)
        for i in range(60):
            alpha = int(60 * (1 - i / 60.0))
            pg.draw.ellipse(glow, (255, 110, 40, alpha),
                            (WIDTH // 2 - 260 - i * 4, 120 - i, 520 + i * 8,
                             120 + i * 2))
        self.screen.blit(glow, (0, 0))

        self._text(self.screen, self.font_big, TITLE, C_EMBER,
                   (WIDTH // 2, 170), center=True)
        self._text(self.screen, self.font_ui,
                   "пошаговый рогалик в засыпанном пеплом городе",
                   C_ASH, (WIDTH // 2, 232), center=True)

        options = ["[n]   новый спуск"]
        options.append("[c]   продолжить" if selected_slot_exists
                       else "[c]   продолжить  (сохранения нет)")
        options.append("[?]   как играть")
        options.append("[esc] выход")

        y = 340
        for i, line in enumerate(options):
            enabled = not (i == 1 and not selected_slot_exists)
            self._text(self.screen, self.font_mid, line,
                       C_BONE if enabled else (78, 74, 80),
                       (WIDTH // 2, y), center=True)
            y += 52

        self._text(self.screen, self.font_small,
                   "восемь этажей вниз, и на последнем лежит "
                   "Пепельная корона",
                   C_DIM, (WIDTH // 2, HEIGHT - 60), center=True)

    def draw_game_over(self, victory):
        self.dim_screen(205)
        title = "КОРОНА ВАША" if victory else "ВЫ ПОГИБЛИ"
        color = C_GOLD if victory else C_BLOOD
        self._text(self.screen, self.font_big, title, color,
                   (WIDTH // 2, HEIGHT // 2 - 110), center=True)

        player = self.engine.player
        stats = [
            "глубина: {} из {}".format(self.engine.depth, MAX_DEPTH),
            "уровень героя: {}".format(player.level.current_level),
            "ходов сделано: {}".format(self.engine.turn_count),
            "убито: {}".format(self.engine.kill_count),
        ]
        y = HEIGHT // 2 - 30
        for line in stats:
            self._text(self.screen, self.font_ui, line, C_BONE,
                       (WIDTH // 2, y), center=True)
            y += 32

        self._text(self.screen, self.font_mid, "[n] новый спуск    [esc] меню",
                   C_EMBER, (WIDTH // 2, y + 30), center=True)

    def draw_help(self):
        self.dim_screen()
        rect = pg.Rect(0, 0, 720, 520)
        rect.center = (WIDTH // 2, HEIGHT // 2)
        self.draw_frame(rect, "КАК ИГРАТЬ")

        rows = [
            ("стрелки, wasd", "идти; шаг в монстра — удар"),
            ("y u b n, нумпад", "идти по диагонали"),
            ("пробел или .", "пропустить ход"),
            ("g", "подобрать то, что под ногами"),
            ("i", "открыть рюкзак"),
            ("   в рюкзаке", "enter применить, d выбросить"),
            ("c", "лист героя"),
            ("shift + .   ( > )", "спуститься по лестнице"),
            ("m", "весь журнал сообщений"),
            ("мышь", "навести — осмотреть, клик — цель"),
            ("f5 / f9", "сохранить / загрузить"),
            ("esc", "назад, из игры — в меню"),
        ]
        y = rect.y + 66
        for key, what in rows:
            self._text(self.screen, self.font_ui, key, C_GOLD, (rect.x + 60, y))
            self._text(self.screen, self.font_ui, what, C_BONE, (rect.x + 260, y))
            y += 32

        self._text(self.screen, self.font_small,
                   "Драться в открытой комнате больно. Отступить в коридор, "
                   "где до вас дотянется только один, — нет.",
                   C_ASH, (rect.centerx, rect.bottom - 34), center=True)

    def draw_inventory(self, title, items, index, equipment):
        self.dim_screen(170)
        height = max(200, 96 + len(items) * 30)
        rect = pg.Rect(0, 0, 620, height)
        rect.center = (WIDTH // 2, HEIGHT // 2)
        self.draw_frame(rect, title)

        if not items:
            self._text(self.screen, self.font_ui, "(рюкзак пуст)",
                       C_DIM, (rect.centerx, rect.centery), center=True)
            return

        y = rect.y + 62
        for i, item in enumerate(items):
            selected = i == index
            if selected:
                pg.draw.rect(self.screen, (36, 30, 26),
                             (rect.x + 16, y - 4, rect.width - 32, 28),
                             border_radius=4)
            label = "{}) {}".format(chr(ord("a") + i), item.name)
            if equipment and equipment.is_equipped(item):
                label += "   (надето)"
            colour = C_BONE if selected else C_ASH
            self._text(self.screen, self.font_ui, label, colour,
                       (rect.x + 32, y))
            hint = ""
            if item.equippable:
                if item.equippable.power_bonus:
                    hint = "+{} к силе".format(item.equippable.power_bonus)
                else:
                    hint = "+{} к защите".format(item.equippable.defense_bonus)
            elif item.consumable:
                hint = "применить"
            self._text(self.screen, self.font_small, hint, C_DIM,
                       (rect.right - 140, y + 4))
            y += 30

    def draw_character(self):
        self.dim_screen()
        rect = pg.Rect(0, 0, 460, 330)
        rect.center = (WIDTH // 2, HEIGHT // 2)
        self.draw_frame(rect, "ГЕРОЙ")

        player = self.engine.player
        rows = [
            ("уровень", player.level.current_level),
            ("опыт", player.level.current_xp),
            ("до уровня", player.level.xp_to_next_level),
            ("здоровье", "{} / {}".format(player.fighter.hp,
                                          player.fighter.max_hp)),
            ("сила", "{}  (свои {})".format(player.fighter.power,
                                            player.fighter.base_power)),
            ("защита", "{}  (свои {})".format(player.fighter.defense,
                                              player.fighter.base_defense)),
            ("глубина", self.engine.depth),
            ("убито", self.engine.kill_count),
        ]
        y = rect.y + 62
        for name, value in rows:
            self._text(self.screen, self.font_ui, name, C_ASH, (rect.x + 34, y))
            self._text(self.screen, self.font_ui, str(value), C_BONE,
                       (rect.right - 150, y))
            y += 32

    def draw_level_up(self, index):
        self.dim_screen()
        rect = pg.Rect(0, 0, 520, 300)
        rect.center = (WIDTH // 2, HEIGHT // 2)
        self.draw_frame(rect, "ВЫ СТАНОВИТЕСЬ СИЛЬНЕЕ")

        options = [
            "a)  телосложение   +{} к здоровью",
            "b)  сила           +{} к урону",
            "c)  стойкость      +{} к защите",
        ]
        from settings import LEVEL_UP_DEFENSE, LEVEL_UP_HP, LEVEL_UP_POWER
        values = (LEVEL_UP_HP, LEVEL_UP_POWER, LEVEL_UP_DEFENSE)

        y = rect.y + 80
        for i, (line, value) in enumerate(zip(options, values)):
            selected = i == index
            if selected:
                pg.draw.rect(self.screen, (36, 30, 26),
                             (rect.x + 24, y - 6, rect.width - 48, 34),
                             border_radius=4)
            self._text(self.screen, self.font_ui, line.format(value),
                       C_BONE if selected else C_ASH, (rect.x + 44, y))
            y += 44

        self._text(self.screen, self.font_small,
                   "выбор — a / b / c или стрелки, затем enter",
                   C_DIM, (rect.centerx, rect.bottom - 30), center=True)

    def draw_log_screen(self, scroll):
        self.dim_screen(215)
        rect = pg.Rect(0, 0, WIDTH - 160, HEIGHT - 140)
        rect.center = (WIDTH // 2, HEIGHT // 2)
        self.draw_frame(rect, "ЖУРНАЛ")

        max_rows = (rect.height - 90) // 22
        lines = list(self.engine.log.wrapped(96))
        window = lines[scroll:scroll + max_rows]
        y = rect.bottom - 46
        for text, color in window:
            self._text(self.screen, self.font_small, text, color,
                       (rect.x + 30, y), shadow=False)
            y -= 22

        self._text(self.screen, self.font_small,
                   "стрелки — прокрутка, esc — закрыть", C_DIM,
                   (rect.centerx, rect.y + 46), center=True)
