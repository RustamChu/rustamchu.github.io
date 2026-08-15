"""The sonar model - the game's eyes.

An active ping is an expanding circular wavefront. Every wall segment it
sweeps across "lights up" on the phosphor with age zero and then cools for
several seconds; the world is therefore visible only as a memory of your own
sound. Objects touched by the front leave typed blips (the station, a black
box, Her), which is how you navigate.

The passive channel is the hydrophone: anything loud in the water - Her
calls, geyser bursts, the station's beacon - files a bearing that the
compass needle on the instrument board swings toward.
"""
from __future__ import annotations

import math

from settings import (BLIP_FADE, ECHO_FADE, PING_COOLDOWN, PING_RADIUS,
                      PING_SPEED)


class Ping:
    __slots__ = ("x", "y", "r", "prev_r", "done")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.r = 0.0
        self.prev_r = 0.0
        self.done = False


class Sonar:
    def __init__(self, world):
        self.world = world
        self.pings = []
        self.echoes = {}            # segment index -> age (seconds)
        self.blips = []             # {"x","y","kind","age"}
        self.cooldown = 0.0

    @property
    def ready(self):
        return self.cooldown <= 0.0

    def ping(self, x, y):
        if not self.ready:
            return False
        self.pings.append(Ping(x, y))
        self.cooldown = PING_COOLDOWN
        return True

    def add_blip(self, x, y, kind):
        self.blips.append({"x": x, "y": y, "kind": kind, "age": 0.0})

    # ------------------------------------------------------------- update
    def update(self, dt, targets=()):
        """`targets` are (x, y, kind) triples the wavefront can reveal."""
        if self.cooldown > 0.0:
            self.cooldown -= dt

        for ping in self.pings:
            ping.prev_r = ping.r
            ping.r += PING_SPEED * dt
            if ping.r >= PING_RADIUS:
                ping.done = True
            self._sweep(ping)
            for tx, ty, kind in targets:
                dist = math.hypot(tx - ping.x, ty - ping.y)
                if ping.prev_r < dist <= ping.r:
                    self.add_blip(tx, ty, kind)
        self.pings = [p for p in self.pings if not p.done]

        gone = []
        for idx in self.echoes:
            self.echoes[idx] += dt
            if self.echoes[idx] > ECHO_FADE:
                gone.append(idx)
        for idx in gone:
            del self.echoes[idx]

        for blip in self.blips:
            blip["age"] += dt
        self.blips = [b for b in self.blips if b["age"] < BLIP_FADE]

    def _sweep(self, ping):
        segments = self.world.segments
        for idx in self.world.segments_near(ping.x, ping.y, ping.r + 20):
            if self.echoes.get(idx, 99.0) < 0.25:
                continue                        # just lit, skip the math
            x1, y1, x2, y2 = segments[idx]
            mx, my = (x1 + x2) * 0.5, (y1 + y2) * 0.5
            dist = math.hypot(mx - ping.x, my - ping.y)
            if ping.prev_r < dist <= ping.r:
                self.echoes[idx] = 0.0
