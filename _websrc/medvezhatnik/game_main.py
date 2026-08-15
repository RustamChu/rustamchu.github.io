#!/usr/bin/env python3
"""МЕДВЕЖАТНИК - a stealth burglary in five mansions.

Author: RustamChu
License: MIT
"""
from __future__ import annotations

import json
import os
import sys

import pygame as pg

from engine import CASING, CAUGHT, CRACKING, ESCAPED, Engine, LOOTED
from renderer import Renderer
from settings import FPS, MISSION_COUNT, RES, TITLE
from sounds import SoundManager

MENU, PLAY, PAUSE, HELP, END = "menu", "play", "pause", "help", "end"
RECORDS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "records.json")


def load_records():
    try:
        with open(RECORDS, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_records(rec):
    with open(RECORDS, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False)


class Game:
    def __init__(self):
        pg.init()
        pg.display.set_caption(TITLE)
        self.screen = pg.display.set_mode(RES)
        self.clock = pg.time.Clock()
        self.sound = SoundManager()
        self.renderer = Renderer(self.screen)
        self.engine = None
        self.state = MENU
        self.help_parent = MENU
        self.cursor = 0
        self.records = load_records()
        self.t = 0.0
        self.running = True
        self.held = set()
        self.step_t = 0.0

    def start_mission(self, mission):
        self.engine = Engine(mission, sound=self.sound)
        self.renderer.cam = None
        self.state = PLAY

    # ---------------------------------------------------------------- input
    def handle_key(self, event):
        sc = event.scancode
        self.held.add(sc)
        if self.state == HELP:
            if sc in (pg.KSCAN_H, pg.KSCAN_ESCAPE, pg.KSCAN_RETURN):
                self.state = self.help_parent
            return
        if self.state == MENU:
            if sc in (pg.KSCAN_UP, pg.KSCAN_W):
                self.cursor = max(0, self.cursor - 1)
            elif sc in (pg.KSCAN_DOWN, pg.KSCAN_S):
                self.cursor = min(MISSION_COUNT - 1, self.cursor + 1)
            elif sc in (pg.KSCAN_RETURN, pg.KSCAN_KP_ENTER):
                unlocked = self.cursor == 0 or \
                    self.records.get(str(self.cursor - 1)) is not None
                if unlocked:
                    self.start_mission(self.cursor)
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
                self.state = MENU
            return
        if self.state == END:
            if sc in (pg.KSCAN_RETURN, pg.KSCAN_KP_ENTER):
                if self.engine.state == ESCAPED \
                        and self.engine.mission + 1 < MISSION_COUNT:
                    self.cursor = self.engine.mission + 1
                    self.start_mission(self.cursor)
                else:
                    self.state = MENU
            elif sc == pg.KSCAN_R:
                self.start_mission(self.engine.mission)
            elif sc == pg.KSCAN_ESCAPE:
                self.state = MENU
            return
        # ---- playing
        engine = self.engine
        if engine.state == CRACKING:
            if sc == pg.KSCAN_SPACE:
                engine.dial_press()
            elif sc == pg.KSCAN_ESCAPE:
                engine.abort_crack()
            return
        if sc == pg.KSCAN_E:
            engine.interact()
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
                if event.scancode == pg.KSCAN_SPACE \
                        and self.state == PLAY \
                        and self.engine.state == CRACKING:
                    self.engine.dial_release()

    def _movement(self, dt):
        held = self.held
        dx = ((pg.KSCAN_D in held or pg.KSCAN_RIGHT in held)
              - (pg.KSCAN_A in held or pg.KSCAN_LEFT in held))
        dy = ((pg.KSCAN_S in held or pg.KSCAN_DOWN in held)
              - (pg.KSCAN_W in held or pg.KSCAN_UP in held))
        sneak = pg.KSCAN_LSHIFT in held or pg.KSCAN_RSHIFT in held
        run = pg.KSCAN_SPACE in held and not sneak
        gait = 0 if sneak else 2 if run else 1
        self.engine.move(dx, dy, gait, dt)
        if (dx or dy) and self.engine.state in (CASING, LOOTED):
            self.step_t -= dt * (1 + gait)
            if self.step_t <= 0:
                self.step_t = 0.42
                self.sound.play("step_run" if gait == 2 else "step")

    # ----------------------------------------------------------------- loop
    def step(self):
        self.handle_events()
        dt = min(self.clock.tick(FPS) / 1000.0, 0.1)
        self.t += dt
        if self.state == PLAY:
            engine = self.engine
            if engine.state != CRACKING:
                self._movement(dt)
            engine.update(dt)
            if engine.state == CAUGHT:
                self.state = END
            elif engine.state == ESCAPED:
                key = str(engine.mission)
                old = self.records.get(key)
                rec = {"time": int(engine.time),
                       "ghost": not engine.spotted_ever}
                if old is None or rec["time"] < old.get("time", 1 << 30) \
                        or (rec["ghost"] and not old.get("ghost")):
                    self.records[key] = rec
                    save_records(self.records)
                self.state = END
        self.draw()

    def draw(self):
        if self.state == MENU or (self.state == HELP
                                  and self.help_parent == MENU):
            self.renderer.draw_menu(self.t, self.records, self.cursor)
            if self.state == HELP:
                self.renderer.draw_help()
            pg.display.flip()
            return
        self.renderer.draw_game(self.engine, self.t)
        if self.state == END:
            self.renderer.draw_end(self.engine, self.t,
                                   self.engine.state == ESCAPED)
        elif self.state == PAUSE:
            veil = pg.Surface(RES, pg.SRCALPHA)
            veil.fill((4, 4, 6, 190))
            self.screen.blit(veil, (0, 0))
            img = self.renderer.font_big.render("ПАУЗА", True,
                                                (128, 120, 108))
            self.screen.blit(img, img.get_rect(center=(RES[0] // 2,
                                                       RES[1] // 2 - 20)))
            img = self.renderer.font_ui.render(
                "Esc — продолжить · Q — в меню", True, (128, 120, 108))
            self.screen.blit(img, img.get_rect(center=(RES[0] // 2,
                                                       RES[1] // 2 + 40)))
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
