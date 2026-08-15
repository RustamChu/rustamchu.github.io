"""Her.

A state machine with four moods. DORMANT below her home depth until the
first ping wakes her. ROAM - slow drifting between waypoints, singing every
few seconds so the hydrophone always vaguely knows where she is. Every ping
she hears feeds agitation; past the threshold she goes to INVESTIGATE and
swims to the exact spot of the last sound. If she gets close to something
loud - thrusters burning, lamp on - she HUNTS, and she is faster than you.
Go silent and drift, and she loses the scent.

The dread loop of the whole game lives in this file: the sonar is your only
sight, and using it is the one thing that draws her in.
"""
from __future__ import annotations

import math
import random

from settings import (MOTHER_AGITATION_DECAY, MOTHER_AGITATION_PER_PING,
                      MOTHER_CALL_EVERY, MOTHER_HEAR_PING,
                      MOTHER_HIT_DMG, MOTHER_HOME_DEPTH,
                      MOTHER_HUNT_THRESHOLD, MOTHER_R, MOTHER_RETREAT_TIME,
                      MOTHER_SENSE_LOUD, MOTHER_SENSE_QUIET,
                      MOTHER_SPEED_HUNT, MOTHER_SPEED_INVESTIGATE,
                      MOTHER_SPEED_ROAM, WORLD_H, WORLD_W)

DORMANT, ROAM, INVESTIGATE, HUNT, RETREAT = (
    "dormant", "roam", "investigate", "hunt", "retreat")


class Mother:
    def __init__(self, world, rng=None):
        self.world = world
        self.rng = rng or random.Random(world.seed * 7 + 1)
        self.home_y = WORLD_H * MOTHER_HOME_DEPTH
        self.x, self.y = world.free_spot_near(
            world.station[0], min(WORLD_H - 200.0, self.home_y + 900.0),
            self.rng)
        self.state = DORMANT
        self.agitation = 0.0
        self.target = None
        self.waypoint = None
        self.retreat_t = 0.0
        self.call_t = self.rng.uniform(*MOTHER_CALL_EVERY)
        self.radius = MOTHER_R

    # ------------------------------------------------------------- hearing
    def hear_ping(self, x, y):
        if math.hypot(x - self.x, y - self.y) > MOTHER_HEAR_PING:
            return
        if self.state == DORMANT:
            self.state = ROAM
        self.agitation = min(100.0, self.agitation
                             + MOTHER_AGITATION_PER_PING)
        self.target = (x, y)
        if self.agitation >= MOTHER_HUNT_THRESHOLD \
                and self.state in (ROAM, INVESTIGATE):
            self.state = INVESTIGATE

    # -------------------------------------------------------------- update
    def update(self, dt, sub, loud, events):
        """`sub` is the submersible, `loud` whether it is making noise,
        `events` collects ("call", x, y) hydrophone contacts."""
        if self.state == DORMANT:
            return

        self.agitation = max(0.0, self.agitation
                             - MOTHER_AGITATION_DECAY * dt)
        self.call_t -= dt
        if self.call_t <= 0:
            self.call_t = self.rng.uniform(*MOTHER_CALL_EVERY)
            events.append(("call", self.x, self.y))

        dist_to_sub = math.hypot(sub.x - self.x, sub.y - self.y)
        sense = MOTHER_SENSE_LOUD if loud else MOTHER_SENSE_QUIET
        if self.state != RETREAT and dist_to_sub < sense:
            self.state = HUNT

        if self.state == RETREAT:
            self.retreat_t -= dt
            self._swim_towards(self.waypoint or (self.x, self.home_y + 400),
                               MOTHER_SPEED_INVESTIGATE, dt)
            if self.retreat_t <= 0:
                self.state = ROAM
            return

        if self.state == HUNT:
            self._swim_towards((sub.x, sub.y), MOTHER_SPEED_HUNT, dt)
            if dist_to_sub > 480 and not loud:
                self.state = INVESTIGATE       # lost you in the dark
                self.target = (sub.x, sub.y)
            return

        if self.state == INVESTIGATE:
            if self.target is None:
                self.state = ROAM
                return
            self._swim_towards(self.target, MOTHER_SPEED_INVESTIGATE, dt)
            if math.hypot(self.target[0] - self.x,
                          self.target[1] - self.y) < 40:
                self.target = None
                if self.agitation < MOTHER_HUNT_THRESHOLD * 0.5:
                    self.state = ROAM
            return

        # ROAM
        if self.waypoint is None or math.hypot(
                self.waypoint[0] - self.x, self.waypoint[1] - self.y) < 60:
            self.waypoint = (self.rng.uniform(200, WORLD_W - 200),
                             self.rng.uniform(self.home_y, WORLD_H - 250))
        self._swim_towards(self.waypoint, MOTHER_SPEED_ROAM, dt)

    def _swim_towards(self, target, speed, dt):
        dx, dy = target[0] - self.x, target[1] - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        step = min(dist, speed * dt)
        nx = self.x + dx / dist * step
        ny = self.y + dy / dist * step
        # she flows around rock rather than through it
        if not self.world.is_solid_at(nx, ny):
            self.x, self.y = nx, ny
        elif not self.world.is_solid_at(self.x, ny):
            self.y = ny
        elif not self.world.is_solid_at(nx, self.y):
            self.x = nx
        else:
            self.waypoint = None
            self.target = None

    # --------------------------------------------------------------- touch
    def try_strike(self, sub):
        """Contact: damage, knockback, then she backs off for a moment."""
        if self.state == RETREAT:
            return 0
        if math.hypot(sub.x - self.x, sub.y - self.y) \
                > self.radius + sub.radius:
            return 0
        dx, dy = sub.x - self.x, sub.y - self.y
        dist = math.hypot(dx, dy) or 1.0
        sub.vx += dx / dist * 420.0
        sub.vy += dy / dist * 420.0
        self.state = RETREAT
        self.retreat_t = MOTHER_RETREAT_TIME
        self.waypoint = (self.x - dx * 8, self.y - dy * 8)
        self.agitation = 40.0
        return MOTHER_HIT_DMG
