#!/usr/bin/env python3
"""ЗИМНИК - a night time-trial down a frozen river.

Author: RustamChu
License: MIT

    python main.py          random stage
    python main.py 8F3KQ    a specific stage by its code
"""
from __future__ import annotations

import math
import random
import sys

import pygame as pg

import savegame
from engine import COUNT, Engine, FIN, RUN, seed_code
from renderer import Renderer
from settings import FPS, RES, TITLE
from sounds import SoundManager

MENU, PLAY, PAUSE, HELP = "menu", "play", "pause", "help"


def _make_icon():
    icon = pg.Surface((32, 32), pg.SRCALPHA)
    pg.draw.rect(icon, (196, 74, 58), (6, 12, 20, 10), border_radius=3)
    pg.draw.rect(icon, (230, 224, 214), (12, 14, 6, 6), border_radius=2)
    pg.draw.polygon(icon, (255, 238, 190, 120),
                    ((26, 14), (32, 8), (32, 24), (26, 20)))
    return icon


class Game:
    def __init__(self, start_seed=None):
        pg.init()
        pg.display.set_caption(TITLE)
        pg.display.set_icon(_make_icon())
        self.screen = pg.display.set_mode(RES)
        self.clock = pg.time.Clock()
        self.sound = SoundManager()
        self.renderer = Renderer(self.screen)

        self.seed = start_seed if start_seed is not None \
            else random.randrange(36 ** 5)
        self.engine = None
        self.state = MENU
        self.help_parent = MENU
        self.t = 0.0
        self.dt = 1 / FPS
        self.running = True
        self.held = set()
        self._saved_result = False

    # ------------------------------------------------------------ lifecycle
    def new_game(self, seed=None):
        if seed is not None:
            self.seed = seed
        code = seed_code(self.seed)
        best_ms, ghost, _ = savegame.stage_record(code)
        self.engine = Engine(self.seed, sound=self.sound, ghost=ghost,
                             best_ms=best_ms)
        self.renderer.cam = None
        self.renderer.skids.clear()
        self.renderer.spray.clear()
        self._saved_result = False
        self.state = PLAY
        self.sound.start_loops()
        self.sound.play("ignition")

    def to_menu(self):
        self.sound.stop_loops()
        self.state = MENU

    def _menu_lines(self):
        stages, golds = savegame.totals()
        stats = ""
        if stages:
            stats = "проехано трасс: %d   ·   золотых: %d" % (stages, golds)
        best_ms, _, medal = savegame.stage_record(seed_code(self.seed))
        best = ""
        if best_ms is not None:
            best = "ваш рекорд здесь: %d:%05.2f (%s)" % (
                best_ms // 60000, best_ms % 60000 / 1000, medal)
        return stats, best

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
                self.new_game()
            elif sc == pg.KSCAN_N:
                self.seed = random.randrange(36 ** 5)
            elif sc == pg.KSCAN_H:
                self.help_parent = MENU
                self.state = HELP
            elif sc == pg.KSCAN_ESCAPE:
                self.running = False
            return

        if self.state == PAUSE:
            if sc == pg.KSCAN_ESCAPE:
                self.state = PLAY
            elif sc == pg.KSCAN_R:
                self.new_game()
            elif sc == pg.KSCAN_Q:
                self.to_menu()
            return

        # ---- driving
        engine = self.engine
        if engine.state == FIN:
            if sc in (pg.KSCAN_RETURN, pg.KSCAN_KP_ENTER):
                self.new_game()
            elif sc == pg.KSCAN_N:
                self.new_game(random.randrange(36 ** 5))
            elif sc == pg.KSCAN_ESCAPE:
                self.to_menu()
            return
        if sc == pg.KSCAN_T:
            engine.rescue()
        elif sc == pg.KSCAN_R:
            self.new_game()
        elif sc == pg.KSCAN_H:
            self.help_parent = PLAY
            self.state = HELP
        elif sc == pg.KSCAN_ESCAPE:
            self.state = PAUSE

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                self.handle_key(event)
            elif event.type == pg.KEYUP:
                self.held.discard(event.scancode)

    def _controls(self):
        held = self.held
        throttle = 1.0 if (pg.KSCAN_W in held or pg.KSCAN_UP in held) \
            else 0.0
        brake = 1.0 if (pg.KSCAN_S in held or pg.KSCAN_DOWN in held) \
            else 0.0
        steer = ((pg.KSCAN_D in held or pg.KSCAN_RIGHT in held)
                 - (pg.KSCAN_A in held or pg.KSCAN_LEFT in held))
        handbrake = pg.KSCAN_SPACE in held
        return throttle, brake, float(steer), handbrake

    # ----------------------------------------------------------------- loop
    def step(self):
        """One frame; separated so the headless test can drive the game."""
        self.handle_events()
        dt = min(self.clock.tick(FPS) / 1000.0, 0.1)
        self.t += dt
        self.dt = dt

        if self.state == PLAY:
            engine = self.engine
            throttle, brake, steer, handbrake = self._controls()
            engine.update(dt, throttle, brake, steer, handbrake)

            car = engine.car
            v_f = (car.vx * math.cos(car.heading)
                   + car.vy * math.sin(car.heading))
            self.sound.update_drive(v_f, car.slip, throttle,
                                    engine.state in (COUNT, RUN))

            if engine.state == FIN and not self._saved_result:
                self._saved_result = True
                changed = savegame.save_result(
                    engine.code, int(engine.time * 1000), engine.recording,
                    engine.medal)
                if changed:
                    self.sound.play("record")
        else:
            self.sound.update_drive(0.0, 0.0, 0.0, False)

        self.draw()

    def draw(self):
        if self.state == MENU or (self.state == HELP
                                  and self.help_parent == MENU):
            stats, best = self._menu_lines()
            self.renderer.draw_menu(self.t, stats, seed_code(self.seed),
                                    best)
            if self.state == HELP:
                self.renderer.draw_help()
            pg.display.flip()
            return

        self.renderer.draw_game(self.engine,
                                self.dt if self.state == PLAY else 0.0)
        if self.engine.state == FIN:
            self.renderer.draw_finish(self.engine, self.t)
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


def _seed_from_argv():
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1].strip().upper(), 36) % (36 ** 5)
        except ValueError:
            print("Код трассы не понял, беру случайную:", sys.argv[1])
    return None


if __name__ == "__main__":
    Game(_seed_from_argv()).run()
