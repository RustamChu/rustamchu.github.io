"""One burglary: movement, noise, light, the safe, the way out.

Pure simulation - the headless test and the ghost replay drive this
directly. States: CASING (walking the job) -> CRACKING (the dial
minigame) -> LOOTED (get out) -> ESCAPED / CAUGHT.
"""
from __future__ import annotations

import math
import random

from guards import ALERT, Guard, can_see
from mansion import Mansion
from settings import (INTERACT_R, NOISE_RUN, NOISE_WALK, P_R, SAFE_RINGS,
                      SAFE_SPEED, SAFE_WINDOW, SPEED_RUN, SPEED_SNEAK,
                      SPEED_WALK, SWITCH_RELIGHT)

CASING, CRACKING, LOOTED, ESCAPED, CAUGHT = (
    "casing", "cracking", "looted", "escaped", "caught")


class Thief:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hidden = False            # ducked behind low furniture
        self.moving = 0.0
        self.face = 0.0


class Engine:
    def __init__(self, mission, sound=None):
        self.mission = mission
        self.sound = sound
        from solver import make_solvable
        self.m, self.ghost_route = make_solvable(mission)
        self.ghost_time = self.ghost_route[-1][2]
        self.thief = Thief(*self.m.start)
        self.guards = [Guard(self.m, g)
                       for g in range(len(self.m.patrols))]
        self.state = CASING
        self.time = 0.0
        self.noise = 0.0               # current noise radius, for the HUD
        self.noise_events = []
        self.spotted_ever = False
        self.seen_now = 0.0            # 0..1 danger meter for the HUD
        self.safe_ring = 0
        self.dial = 0.0
        self.dial_hold = False
        self.dial_result = None
        self.rng = random.Random(self.m.seed * 13 + 7)
        self.alarm = 0.0

    # ------------------------------------------------------------ helpers
    def _snd(self, name):
        if self.sound is not None:
            self.sound.play(name)

    @property
    def finished(self):
        return self.state in (ESCAPED, CAUGHT)

    def near(self, pos):
        return math.hypot(self.thief.x - pos[0],
                          self.thief.y - pos[1]) < INTERACT_R

    # ------------------------------------------------------------- inputs
    def move(self, dx, dy, gait, dt):
        """gait: 0 sneak, 1 walk, 2 run."""
        if self.state not in (CASING, LOOTED):
            return
        t = self.thief
        norm = math.hypot(dx, dy)
        if norm < 1e-6:
            t.moving = 0.0
            self.noise = 0.0
            return
        speed = (SPEED_SNEAK, SPEED_WALK, SPEED_RUN)[gait]
        radius = (0.0, NOISE_WALK, NOISE_RUN)[gait]
        step = speed * dt
        nx = t.x + dx / norm * step
        ny = t.y + dy / norm * step
        if not self.m.solid_circle(nx, ny, P_R):
            t.x, t.y = nx, ny
        elif not self.m.solid_circle(t.x, ny, P_R):
            t.y = ny
        elif not self.m.solid_circle(nx, t.y, P_R):
            t.x = nx
        t.face = math.atan2(dy, dx)
        t.moving = gait + 1.0
        self.noise = radius
        if radius > 0:
            self.noise_events.append((t.x, t.y, radius))

    def interact(self):
        """E: safe, light switch, or the exit door."""
        if self.state == CRACKING:
            return "already"
        m = self.m
        if self.state == CASING and self.near(m.safe_pos):
            self.state = CRACKING
            self.safe_ring = 0
            self.dial = 0.0
            self._snd("safe_open")
            return "safe"
        for lamp in m.lamps:
            if self.near(lamp["switch"]):
                lamp["lit"] = not lamp["lit"]
                if not lamp["lit"]:
                    lamp["relight"] = SWITCH_RELIGHT
                    lamp["player_off"] = True
                self._snd("switch")
                return "switch"
        if self.state == LOOTED and self.near(m.exit_pos):
            self.state = ESCAPED
            self._snd("escape")
            return "exit"
        if self.state == CASING and self.near(m.exit_pos):
            return "need_loot"
        return None

    # ----------------------------------------------------------- the dial
    def dial_press(self):
        if self.state == CRACKING:
            self.dial_hold = True

    def dial_release(self):
        if self.state != CRACKING or not self.dial_hold:
            return None
        self.dial_hold = False
        window = SAFE_WINDOW[self.safe_ring]
        # the sweet spot sits at a seeded angle per ring
        sweet = (self.m.seed * (self.safe_ring + 3) * 0.618) % math.tau
        diff = abs((self.dial - sweet + math.pi) % math.tau - math.pi)
        if diff <= window / 2:
            self.safe_ring += 1
            self.dial = 0.0
            self._snd("click_good")
            if self.safe_ring >= SAFE_RINGS:
                self.state = LOOTED
                self._snd("loot")
                # cracking a safe is loud enough to wake the house
                self.noise_events.append((self.thief.x, self.thief.y, 260))
                return "cracked"
            return "ring"
        self._snd("click_bad")
        self.noise_events.append((self.thief.x, self.thief.y, 150))
        self.safe_ring = max(0, self.safe_ring - 1)
        return "slip"

    def abort_crack(self):
        if self.state == CRACKING:
            self.state = CASING

    # -------------------------------------------------------------- update
    def update(self, dt):
        if self.finished:
            return
        self.time += dt

        if self.state == CRACKING and self.dial_hold:
            self.dial = (self.dial
                         + SAFE_SPEED[self.safe_ring] * dt) % math.tau

        for lamp in self.m.lamps:
            if lamp["relight"] > 0:
                lamp["relight"] -= dt

        caught = False
        self.seen_now = 0.0
        for g in self.guards:
            if g.update(dt, self.time, self.thief, self.noise_events):
                caught = True
            if g.state == ALERT:
                self.seen_now = 1.0
            else:
                self.seen_now = max(self.seen_now,
                                    min(1.0, g.spot / 0.55))
            if g.said:
                self._snd(g.said)
                if g.said == "shout":
                    self.spotted_ever = True
        self.alarm = max((g.alert_t for g in self.guards
                          if g.state == ALERT), default=0.0)
        self.noise_events = []

        if caught:
            self.state = CAUGHT
            self._snd("caught")

    # ----------------------------------------------- ghost replay support
    def teleport(self, x, y):
        """Used by the test to walk the solver's route step by step."""
        self.thief.x, self.thief.y = x, y

    def ghost_seen(self):
        """Is the thief inside anyone's cone right now?"""
        for g in self.guards:
            if can_see(self.m, g.x, g.y, g.facing,
                       self.thief.x, self.thief.y):
                return True
        return False
