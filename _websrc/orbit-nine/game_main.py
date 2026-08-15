#!/usr/bin/env python3
"""ORBITA-9 - cosmic mini-golf.

Author: RustamChu
License: MIT
"""
from __future__ import annotations

import math
import sys

import pygame as pg

import savegame
from engine import AIM, COURSE_DONE, Engine, FLYING, HOLE_DONE
from renderer import Renderer
from settings import FPS, RES, TITLE
from sounds import SoundManager

MENU, PLAY, HELP, SCORE = "menu", "play", "help", "score"


class Game:
    def __init__(self):
        pg.init()
        pg.display.set_caption(TITLE)
        self.screen = pg.display.set_mode(RES)
        self.clock = pg.time.Clock()
        self.sound = SoundManager()
        self.renderer = Renderer(self.screen)

        self.engine = Engine(sound=self.sound)
        self.state = MENU
        self.help_parent = MENU
        self.t = 0.0
        self.running = True
        self.drag_from = None
        self.ui = {"aim": None, "show_hint": False}

    # ------------------------------------------------------------ lifecycle
    def new_game(self, seed=None):
        self.engine = Engine(seed=seed, sound=self.sound)
        self.ui.update(aim=None, show_hint=False)
        self.drag_from = None
        self.state = PLAY

    def continue_game(self):
        if not savegame.has_save():
            return False
        try:
            self.engine = savegame.load(sound=self.sound)
        except (OSError, ValueError, KeyError):
            return False
        self.ui.update(aim=None, show_hint=False)
        self.state = PLAY
        return True

    def to_menu(self):
        if self.state == PLAY and not self.engine.finished:
            savegame.save(self.engine)
        self.state = MENU

    # ---------------------------------------------------------------- input
    def handle_key(self, event):
        sc = event.scancode

        if self.state == HELP:
            if sc in (pg.KSCAN_ESCAPE, pg.KSCAN_SLASH, pg.KSCAN_RETURN):
                self.state = self.help_parent
            return
        if self.state == SCORE:
            if sc in (pg.KSCAN_ESCAPE, pg.KSCAN_TAB, pg.KSCAN_RETURN):
                self.state = PLAY
            return

        if self.state == MENU:
            if sc == pg.KSCAN_N:
                self.new_game()
            elif sc == pg.KSCAN_C:
                self.continue_game()
            elif sc == pg.KSCAN_SLASH:
                self.help_parent = MENU
                self.state = HELP
            elif sc == pg.KSCAN_ESCAPE:
                self.running = False
            return

        # ---- playing
        engine = self.engine
        if engine.state == COURSE_DONE:
            if sc == pg.KSCAN_N:
                savegame.delete_save()
                self.new_game()
            elif sc == pg.KSCAN_ESCAPE:
                savegame.delete_save()
                self.state = MENU
            return

        if sc == pg.KSCAN_SPACE and engine.state == HOLE_DONE:
            engine.next_hole()
        elif sc == pg.KSCAN_R:
            engine.restart_hole()
        elif sc == pg.KSCAN_H:
            self.ui["show_hint"] = not self.ui["show_hint"]
        elif sc == pg.KSCAN_TAB:
            self.state = SCORE
        elif sc == pg.KSCAN_SLASH:
            self.help_parent = PLAY
            self.state = HELP
        elif sc == pg.KSCAN_ESCAPE:
            self.to_menu()

    def handle_mouse_down(self, event):
        if self.state != PLAY or event.button != 1:
            return
        if self.engine.state != AIM:
            return
        bx, by = self.engine.ball
        if math.hypot(event.pos[0] - bx, event.pos[1] - by) < 70:
            self.drag_from = event.pos

    def handle_mouse_up(self, event):
        if event.button != 1 or self.drag_from is None:
            return
        shot = self.engine.drag_to_shot(event.pos[0] - self.drag_from[0],
                                        event.pos[1] - self.drag_from[1])
        self.drag_from = None
        self.ui["aim"] = None
        if shot is not None and self.state == PLAY:
            self.engine.launch(*shot)
            self.ui["show_hint"] = False

    def handle_mouse_move(self, event):
        if self.drag_from is None:
            self.ui["aim"] = None
            return
        shot = self.engine.drag_to_shot(event.pos[0] - self.drag_from[0],
                                        event.pos[1] - self.drag_from[1])
        self.ui["aim"] = shot

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                self.handle_key(event)
            elif event.type == pg.MOUSEBUTTONDOWN:
                self.handle_mouse_down(event)
            elif event.type == pg.MOUSEBUTTONUP:
                self.handle_mouse_up(event)
            elif event.type == pg.MOUSEMOTION:
                self.handle_mouse_move(event)

    # ----------------------------------------------------------------- loop
    def step(self):
        """One frame; separated so the headless test can drive the game."""
        self.handle_events()
        dt = min(self.clock.tick(FPS) / 1000.0, 0.1)
        self.t += dt

        if self.state in (PLAY, SCORE):
            self.engine.update(dt)
            if self.engine.save_pending:
                if self.engine.finished:
                    savegame.delete_save()
                else:
                    savegame.save(self.engine)
                self.engine.save_pending = False

        self.draw()

    def draw(self):
        if self.state == MENU or (self.state == HELP
                                  and self.help_parent == MENU):
            self.renderer.draw_menu(savegame.has_save(), self.t)
            if self.state == HELP:
                self.renderer.draw_help()
            pg.display.flip()
            return

        self.renderer.draw_field(self.engine, self.ui, self.t)
        self.renderer.draw_hud(self.engine, self.ui, self.t)
        if self.engine.state == HOLE_DONE:
            self.renderer.draw_hole_done(self.engine, self.t)
        elif self.engine.state == COURSE_DONE:
            self.renderer.draw_course_done(self.engine)
        if self.state == SCORE:
            self.renderer.draw_scorecard(self.engine)
        elif self.state == HELP:
            self.renderer.draw_help()
        pg.display.flip()

    def run(self):
        while self.running:
            self.step()
        pg.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
