#!/usr/bin/env python3
"""БАТИСФЕРА - sonar horror at the bottom of a nameless trench.

Author: RustamChu
License: MIT
"""
from __future__ import annotations

import random
import sys

import pygame as pg

import savegame
from engine import BLACKBOX_LOGS, DEAD, DIVING, DOCKED, Engine
from renderer import Renderer
from settings import FPS, METERS_PER_PX, RES, TITLE
from sounds import SoundManager

MENU, PLAY, PAUSE, HELP, LOST, SAFE = ("menu", "play", "pause", "help",
                                       "lost", "safe")
AUTOSAVE_EVERY = 6.0


def _make_icon():
    icon = pg.Surface((32, 32), pg.SRCALPHA)
    pg.draw.ellipse(icon, (44, 52, 62), (2, 8, 28, 16))
    pg.draw.circle(icon, (255, 210, 140), (24, 16), 4)
    return icon


class Game:
    def __init__(self):
        pg.init()
        pg.display.set_caption(TITLE)
        pg.display.set_icon(_make_icon())
        self.screen = pg.display.set_mode(RES)
        self.clock = pg.time.Clock()
        self.sound = SoundManager()
        self.renderer = Renderer(self.screen)

        self.engine = None
        self.state = MENU
        self.help_parent = MENU
        self.t = 0.0
        self.running = True
        self.held = set()                  # scancodes held right now
        self.autosave_t = 0.0
        self.creak_t = random.uniform(6, 14)
        self.thump_t = 0.0

    # ------------------------------------------------------------ lifecycle
    def new_game(self, seed=None):
        self.engine = Engine(seed=seed, sound=self.sound)
        self.renderer.cam = None
        self.renderer.bubbles.clear()
        self.renderer.mother_prev = None
        self.state = PLAY
        self.autosave_t = 0.0

    def continue_game(self):
        if not savegame.has_save():
            return False
        try:
            self.engine = savegame.load(sound=self.sound)
        except (OSError, ValueError, KeyError):
            return False
        self.renderer.cam = None
        self.renderer.bubbles.clear()
        self.renderer.mother_prev = None
        self.state = PLAY
        return True

    def to_menu(self, keep_save=True):
        if (self.engine is not None and keep_save
                and self.engine.state == DIVING):
            savegame.save(self.engine)
        self.state = MENU

    def _menu_line(self):
        rec = savegame.load_records()
        bits = []
        if rec.get("best_depth_m"):
            bits.append("рекорд глубины: {} м".format(rec["best_depth_m"]))
        if rec.get("returns"):
            bits.append("возвращений: {}".format(rec["returns"]))
        if savegame.has_save():
            bits.append("C — продолжить прерванный спуск")
        return "   ·   ".join(bits)

    # ---------------------------------------------------------------- input
    def handle_key(self, event):
        sc = event.scancode
        self.held.add(sc)

        if self.state == HELP:
            if sc in (pg.KSCAN_H, pg.KSCAN_ESCAPE, pg.KSCAN_RETURN):
                self.state = self.help_parent
            return

        if self.state == MENU:
            if sc in (pg.KSCAN_RETURN, pg.KSCAN_KP_ENTER):
                self.sound.play("ui")
                self.new_game()
            elif sc == pg.KSCAN_C:
                if self.continue_game():
                    self.sound.play("ui")
            elif sc == pg.KSCAN_H:
                self.help_parent = MENU
                self.state = HELP
            elif sc == pg.KSCAN_ESCAPE:
                self.running = False
            return

        if self.state == PAUSE:
            if sc == pg.KSCAN_ESCAPE:
                self.state = PLAY
            elif sc == pg.KSCAN_Q:
                self.to_menu()
            return

        if self.state in (LOST, SAFE):
            if sc in (pg.KSCAN_RETURN, pg.KSCAN_KP_ENTER):
                self.sound.play("ui")
                self.new_game()
            elif sc == pg.KSCAN_ESCAPE:
                self.to_menu(keep_save=False)
            return

        # ---- diving
        if sc == pg.KSCAN_SPACE:
            self.engine.ping()
        elif sc == pg.KSCAN_F:
            self.engine.toggle_lamp()
        elif sc == pg.KSCAN_H:
            self.help_parent = PLAY
            self.state = HELP
        elif sc == pg.KSCAN_ESCAPE:
            self.state = PAUSE

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                if self.engine is not None and self.state in (PLAY, PAUSE,
                                                              HELP):
                    self.to_menu()
                self.running = False
            elif event.type == pg.KEYDOWN:
                self.handle_key(event)
            elif event.type == pg.KEYUP:
                self.held.discard(event.scancode)

    def _thrust_from_keys(self):
        held = self.held
        tx = ((pg.KSCAN_D in held or pg.KSCAN_RIGHT in held)
              - (pg.KSCAN_A in held or pg.KSCAN_LEFT in held))
        ty = ((pg.KSCAN_S in held or pg.KSCAN_DOWN in held)
              - (pg.KSCAN_W in held or pg.KSCAN_UP in held))
        return tx, ty

    # -------------------------------------------------------------- ambience
    def _ambience(self, dt):
        engine = self.engine
        # pressure creaks, more often the deeper you are
        self.creak_t -= dt * (1.0 + 2.2 * engine.sub.y / 5320.0)
        if self.creak_t <= 0:
            self.creak_t = random.uniform(7, 16)
            self.sound.play("creak")
        # your own pulse when She is close
        if engine.heartbeat > 0.12:
            self.thump_t -= dt
            if self.thump_t <= 0:
                self.thump_t = 1.15 - 0.75 * engine.heartbeat
                self.sound.play("thump")

    # ----------------------------------------------------------------- loop
    def step(self):
        """One frame; separated so the headless test can drive the game."""
        self.handle_events()
        dt = min(self.clock.tick(FPS) / 1000.0, 0.1)
        self.t += dt
        self.dt = dt

        if self.state == PLAY:
            engine = self.engine
            engine.set_thrust(*self._thrust_from_keys())
            engine.update(dt)
            self._ambience(dt)

            if engine.state == DEAD:
                savegame.delete_save()
                savegame.update_records(
                    engine, False, int(engine.max_depth * METERS_PER_PX))
                self.state = LOST
            elif engine.state == DOCKED:
                savegame.delete_save()
                savegame.update_records(
                    engine, True, int(engine.max_depth * METERS_PER_PX))
                self.state = SAFE
            else:
                self.autosave_t += dt
                if self.autosave_t >= AUTOSAVE_EVERY:
                    self.autosave_t = 0.0
                    savegame.save(engine)

        self.draw()

    def draw(self):
        if self.state == MENU or (self.state == HELP
                                  and self.help_parent == MENU):
            self.renderer.draw_menu(self.t, self._menu_line())
            if self.state == HELP:
                self.renderer.draw_help()
            pg.display.flip()
            return

        if self.state == LOST:
            self.renderer.draw_death(self.engine, self.t)
        elif self.state == SAFE:
            self.renderer.draw_docked(self.engine, self.t, BLACKBOX_LOGS)
        else:
            self.renderer.draw_game(
                self.engine,
                getattr(self, "dt", 1 / FPS) if self.state == PLAY else 0.0)
            if self.state == PAUSE:
                self.renderer.draw_pause()
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
