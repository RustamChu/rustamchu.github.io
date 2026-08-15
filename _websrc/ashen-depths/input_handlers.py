"""Input handling as a small stack of UI states.

Each screen is a handler that owns its own key map and its own drawing, and
returns the handler that should be active next. Adding a screen never
touches the main loop.
"""
from __future__ import annotations

import pygame as pg

import savegame
from actions import (BumpAction, DescendAction, DropAction, PickupAction,
                     UseAction, WaitAction)
from components import Impossible
from settings import (C_BONE, LEVEL_UP_DEFENSE, LEVEL_UP_HP, LEVEL_UP_POWER,
                      MSG_BAD, MSG_SYS)

MOVE_KEYS = {
    pg.K_UP: (0, -1), pg.K_w: (0, -1), pg.K_KP8: (0, -1), pg.K_k: (0, -1),
    pg.K_DOWN: (0, 1), pg.K_s: (0, 1), pg.K_KP2: (0, 1), pg.K_j: (0, 1),
    pg.K_LEFT: (-1, 0), pg.K_a: (-1, 0), pg.K_KP4: (-1, 0), pg.K_h: (-1, 0),
    pg.K_RIGHT: (1, 0), pg.K_d: (1, 0), pg.K_KP6: (1, 0), pg.K_l: (1, 0),
    pg.K_y: (-1, -1), pg.K_KP7: (-1, -1),
    pg.K_u: (1, -1), pg.K_KP9: (1, -1),
    pg.K_b: (-1, 1), pg.K_KP1: (-1, 1),
    pg.K_n: (1, 1), pg.K_KP3: (1, 1),
}

WAIT_KEYS = (pg.K_PERIOD, pg.K_SPACE, pg.K_KP5, pg.K_CLEAR)
CONFIRM_KEYS = (pg.K_RETURN, pg.K_KP_ENTER)


class Handler:
    def __init__(self, game):
        self.game = game

    @property
    def engine(self):
        return self.game.engine

    def on_key(self, event):
        return self

    def on_mouse_down(self, event):
        return self

    def on_mouse_motion(self, event):
        return self

    def render(self, renderer):
        raise NotImplementedError


# =========================================================================== menu
class MenuHandler(Handler):
    def on_key(self, event):
        if event.key == pg.K_n:
            self.game.start_new_game()
            return MainGameHandler(self.game)
        if event.key == pg.K_c and savegame.has_save():
            if self.game.load_game():
                return MainGameHandler(self.game)
            return self
        if event.key in (pg.K_QUESTION, pg.K_SLASH, pg.K_h):
            return HelpHandler(self.game, self)
        if event.key == pg.K_ESCAPE:
            self.game.quit()
        return self

    def render(self, renderer):
        renderer.draw_menu(savegame.has_save())


# =========================================================================== play
class MainGameHandler(Handler):
    def on_key(self, event):
        player = self.engine.player
        key = event.key

        # ">" is shift+period on most layouts, so it must be tested first
        if key == pg.K_GREATER or (key == pg.K_PERIOD
                                   and event.mod & pg.KMOD_SHIFT):
            return self.game.player_action(DescendAction(player))
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            return self.game.player_action(BumpAction(player, dx, dy))
        if key in WAIT_KEYS:
            return self.game.player_action(WaitAction(player))
        if key == pg.K_g:
            return self.game.player_action(PickupAction(player))
        if key == pg.K_i:
            return InventoryHandler(self.game)
        if key == pg.K_c:
            return CharacterHandler(self.game)
        if key == pg.K_m:
            return LogHandler(self.game)
        if key in (pg.K_QUESTION, pg.K_SLASH):
            return HelpHandler(self.game, self)
        if key == pg.K_F5:
            self.game.save_game()
            return self
        if key == pg.K_F9:
            if self.game.load_game():
                return MainGameHandler(self.game)
            return self
        if key == pg.K_ESCAPE:
            self.game.save_game()
            return MenuHandler(self.game)
        return self

    def on_mouse_motion(self, event):
        self.game.mouse_pos = event.pos
        return self

    def render(self, renderer):
        renderer.update_camera()
        renderer.draw_map()
        renderer.draw_entities()
        renderer.draw_effects()
        renderer.draw_panel()
        renderer.draw_tooltip(self.game.mouse_pos)


# =========================================================================== pack
class InventoryHandler(Handler):
    title = "РЮКЗАК   —   enter применить, d выбросить, esc закрыть"

    def __init__(self, game):
        super().__init__(game)
        self.index = 0

    @property
    def items(self):
        return self.engine.player.inventory.items

    def on_key(self, event):
        key = event.key
        items = self.items

        if key == pg.K_ESCAPE or key == pg.K_i:
            return MainGameHandler(self.game)
        if not items:
            return self

        if key in (pg.K_UP, pg.K_k):
            self.index = (self.index - 1) % len(items)
            return self
        if key in (pg.K_DOWN, pg.K_j):
            self.index = (self.index + 1) % len(items)
            return self
        if key == pg.K_d:                       # drop beats letter selection
            return self.game.player_action(
                DropAction(self.engine.player, items[self.index]))
        if key in CONFIRM_KEYS:
            return self._activate(items[self.index])
        if pg.K_a <= key <= pg.K_z:
            picked = key - pg.K_a
            if picked < len(items):
                self.index = picked
                return self._activate(items[picked])
        return self

    def _activate(self, item):
        player = self.engine.player
        consumable = item.consumable
        if consumable is not None and consumable.targeting:
            return TargetingHandler(self.game, item, consumable.targeting,
                                    consumable.targeting_radius)
        return self.game.player_action(UseAction(player, item))

    def render(self, renderer):
        MainGameHandler(self.game).render(renderer)
        self.index = min(self.index, max(0, len(self.items) - 1))
        renderer.draw_inventory(self.title, self.items, self.index,
                                self.engine.player.equipment)


# =========================================================================== targeting
class TargetingHandler(Handler):
    def __init__(self, game, item, mode, radius):
        super().__init__(game)
        self.item = item
        self.mode = mode
        self.radius = radius
        player = game.engine.player
        self.tx, self.ty = player.x, player.y
        game.engine.log.add("Выберите цель: стрелки или мышь, enter — "
                            "применить, esc — отмена.", MSG_SYS, stack=False)

    def _clamp(self):
        gamemap = self.engine.gamemap
        self.tx = max(0, min(self.tx, gamemap.width - 1))
        self.ty = max(0, min(self.ty, gamemap.height - 1))

    def on_key(self, event):
        key = event.key
        if key == pg.K_ESCAPE:
            self.engine.log.add("Вы убираете свиток.", MSG_SYS)
            return MainGameHandler(self.game)
        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            step = 5 if event.mod & pg.KMOD_SHIFT else 1
            self.tx += dx * step
            self.ty += dy * step
            self._clamp()
            return self
        if key in CONFIRM_KEYS:
            return self._fire()
        return self

    def on_mouse_motion(self, event):
        self.game.mouse_pos = event.pos
        tx, ty = self.game.renderer.screen_to_tile(*event.pos)
        self.tx, self.ty = tx, ty
        self._clamp()
        return self

    def on_mouse_down(self, event):
        if event.button == 1:
            return self._fire()
        if event.button == 3:
            return MainGameHandler(self.game)
        return self

    def _fire(self):
        return self.game.player_action(
            UseAction(self.engine.player, self.item, (self.tx, self.ty)))

    def render(self, renderer):
        MainGameHandler(self.game).render(renderer)
        renderer.draw_targeting(self.tx, self.ty, self.radius)


# =========================================================================== info screens
class CharacterHandler(Handler):
    def on_key(self, event):
        if event.key in (pg.K_ESCAPE, pg.K_c) or event.key in CONFIRM_KEYS:
            return MainGameHandler(self.game)
        return self

    def render(self, renderer):
        MainGameHandler(self.game).render(renderer)
        renderer.draw_character()


class HelpHandler(Handler):
    def __init__(self, game, parent):
        super().__init__(game)
        self.parent = parent

    def on_key(self, event):
        if event.key in (pg.K_ESCAPE, pg.K_QUESTION, pg.K_SLASH) \
                or event.key in CONFIRM_KEYS:
            return self.parent
        return self

    def render(self, renderer):
        self.parent.render(renderer)
        renderer.draw_help()


class LogHandler(Handler):
    def __init__(self, game):
        super().__init__(game)
        self.scroll = 0

    def on_key(self, event):
        if event.key in (pg.K_ESCAPE, pg.K_m):
            return MainGameHandler(self.game)
        total = len(list(self.engine.log.wrapped(96)))
        if event.key in (pg.K_DOWN, pg.K_j):
            self.scroll = max(0, self.scroll - 1)
        elif event.key in (pg.K_UP, pg.K_k):
            self.scroll = min(max(0, total - 1), self.scroll + 1)
        elif event.key == pg.K_PAGEUP:
            self.scroll = min(max(0, total - 1), self.scroll + 10)
        elif event.key == pg.K_PAGEDOWN:
            self.scroll = max(0, self.scroll - 10)
        return self

    def render(self, renderer):
        MainGameHandler(self.game).render(renderer)
        renderer.draw_log_screen(self.scroll)


class LevelUpHandler(Handler):
    def __init__(self, game):
        super().__init__(game)
        self.index = 0

    def on_key(self, event):
        key = event.key
        if key in (pg.K_UP, pg.K_k):
            self.index = (self.index - 1) % 3
            return self
        if key in (pg.K_DOWN, pg.K_j):
            self.index = (self.index + 1) % 3
            return self
        if key in (pg.K_a, pg.K_b, pg.K_c):
            self.index = {pg.K_a: 0, pg.K_b: 1, pg.K_c: 2}[key]
            return self._choose()
        if key in CONFIRM_KEYS:
            return self._choose()
        return self

    def _choose(self):
        player = self.engine.player
        fighter = player.fighter
        if self.index == 0:
            fighter.max_hp += LEVEL_UP_HP
            fighter.hp += LEVEL_UP_HP
            self.engine.log.add("Ваше тело крепнет.", C_BONE)
        elif self.index == 1:
            fighter.base_power += LEVEL_UP_POWER
            self.engine.log.add("Ваши удары тяжелеют.", C_BONE)
        else:
            fighter.base_defense += LEVEL_UP_DEFENSE
            self.engine.log.add("Ваша защита крепнет.", C_BONE)
        player.level.increase_level()
        return self.game.after_player_turn()

    def render(self, renderer):
        MainGameHandler(self.game).render(renderer)
        renderer.draw_level_up(self.index)


class GameOverHandler(Handler):
    def __init__(self, game, victory):
        super().__init__(game)
        self.victory = victory
        savegame.delete_save()

    def on_key(self, event):
        if event.key == pg.K_n:
            self.game.start_new_game()
            return MainGameHandler(self.game)
        if event.key == pg.K_ESCAPE:
            return MenuHandler(self.game)
        return self

    def render(self, renderer):
        renderer.update_camera()
        renderer.draw_map()
        renderer.draw_entities()
        renderer.draw_panel()
        renderer.draw_game_over(self.victory)
