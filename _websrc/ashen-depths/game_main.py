#!/usr/bin/env python3
"""ASHEN DEPTHS - a turn-based roguelike.

Author: RustamChu
License: MIT
"""
import sys

import pygame as pg

import input_handlers
import savegame
from components import Impossible
from engine import Engine
from renderer import Renderer
from settings import C_BONE, FPS, MSG_BAD, MSG_SYS, RES, TITLE


class Game:
    def __init__(self):
        pg.init()
        pg.display.set_caption(TITLE)
        self.screen = pg.display.set_mode(RES)
        self.clock = pg.time.Clock()
        self.mouse_pos = (0, 0)
        self.running = True

        self.engine = Engine()
        self.engine.new_game()               # a world must exist to render
        self.renderer = Renderer(self.engine, self.screen)
        self.handler = input_handlers.MenuHandler(self)

    # ------------------------------------------------------------ lifecycle
    def start_new_game(self, seed=None):
        self.engine.new_game(seed)
        self.renderer.engine = self.engine
        self.engine.log.add("Новый спуск начинается.", MSG_SYS)

    def save_game(self):
        try:
            savegame.save(self.engine)
            self.engine.log.add("Игра сохранена.", MSG_SYS)
            return True
        except OSError as error:
            self.engine.log.add("Не удалось сохранить: {}".format(error), MSG_BAD)
            return False

    def load_game(self):
        if not savegame.has_save():
            self.engine.log.add("Сохранения нет.", MSG_BAD)
            return False
        try:
            savegame.load(self.engine)
        except (OSError, ValueError, KeyError) as error:
            self.engine.log.add("Не удалось загрузить: {}".format(error), MSG_BAD)
            return False
        self.engine.log.add("Игра загружена.", MSG_SYS)
        return True

    def quit(self):
        self.running = False

    # --------------------------------------------------------------- turns
    def player_action(self, action):
        """Run a player action, then let the dungeon answer."""
        try:
            consumed_turn = action.perform()
        except Impossible as error:
            self.engine.log.add(str(error), MSG_BAD)
            return input_handlers.MainGameHandler(self)

        if consumed_turn and not self.engine.victory:
            self.engine.advance_turn()
        return self.after_player_turn()

    def after_player_turn(self):
        if self.engine.victory:
            return input_handlers.GameOverHandler(self, victory=True)
        if self.engine.player_died:
            return input_handlers.GameOverHandler(self, victory=False)
        if self.engine.player.level.requires_level_up:
            return input_handlers.LevelUpHandler(self)
        return input_handlers.MainGameHandler(self)

    # ---------------------------------------------------------------- loop
    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()
            elif event.type == pg.KEYDOWN:
                self.handler = self.handler.on_key(event) or self.handler
            elif event.type == pg.MOUSEMOTION:
                self.handler = self.handler.on_mouse_motion(event) or self.handler
            elif event.type == pg.MOUSEBUTTONDOWN:
                self.handler = self.handler.on_mouse_down(event) or self.handler

    def step(self):
        """One frame, kept separate so the tests can drive the game."""
        self.handle_events()
        dt = self.clock.tick(FPS)
        self.engine.update_effects(dt)
        self.screen.fill((7, 6, 10))
        self.handler.render(self.renderer)
        pg.display.flip()

    def run(self):
        while self.running:
            self.step()
        pg.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
