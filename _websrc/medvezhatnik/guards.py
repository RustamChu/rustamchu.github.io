"""The guards: patrol, suspicion, alarm - and one shared pair of eyes.

`can_see(mansion, gx, gy, facing, tx, ty)` is THE vision function: the
live guards use it, and the ghost solver uses it too (with a safety
margin). If the solver says a route is unseen, it is unseen by exactly
the same math that would catch you.
"""
from __future__ import annotations

import math

from settings import (ALERT_TIME, CATCH_R, FOV_ANGLE, FOV_RANGE,
                      FOV_RANGE_DARK, G_SPEED_ALERT, G_SPEED_PATROL,
                      G_SPEED_SUSPICIOUS, SPOT_TIME, SUS_GLIMPSE, SUS_WAIT,
                      TURN_RATE)

PATROL, SUSPICIOUS, ALERT, RETURNING = ("patrol", "suspicious", "alert",
                                        "returning")


def can_see(mansion, gx, gy, facing, tx, ty, margin_r=0.0, margin_a=0.0):
    dx, dy = tx - gx, ty - gy
    dist = math.hypot(dx, dy)
    limit = (FOV_RANGE if mansion.is_lit(tx, ty) else FOV_RANGE_DARK)
    limit += margin_r
    if dist > limit:
        return False
    if dist > 1e-6:
        spread = abs((math.atan2(dy, dx) - facing + math.pi)
                     % math.tau - math.pi)
        if spread > FOV_ANGLE / 2 + margin_a:
            return False
    return not mansion.blocked(gx, gy, tx, ty)


class Guard:
    def __init__(self, mansion, gidx):
        self.m = mansion
        self.gidx = gidx
        x, y, facing = mansion.guard_schedule(gidx, 0.0)
        self.x, self.y = x, y
        self.facing = facing
        self.state = PATROL
        self.spot = 0.0                 # continuous-sight accumulator
        self.target = None              # investigate point
        self.wait = 0.0
        self.alert_t = 0.0
        self.chore = None               # ("switch", room) errand
        self.said = None                # one-frame voice line for sfx

    # --------------------------------------------------------------- brain
    def update(self, dt, t, thief, noise_events):
        """Move FIRST, look SECOND. The order matters: after moving, a
        patrolling guard's pose equals guard_schedule(t) exactly, and his
        eyes judge the thief's position of the same instant - which is
        precisely the world the ghost solver plans against."""
        self.said = None
        m = self.m

        # ------------------------------------------------------- movement
        if self.state == ALERT:
            self.alert_t -= dt
            self._chase(dt, G_SPEED_ALERT)
            if self.alert_t <= 0:
                self.state = RETURNING
        elif self.state == SUSPICIOUS:
            if self._chase(dt, G_SPEED_SUSPICIOUS):
                self.wait -= dt
                self._scan(dt, t)
                if self.wait <= 0:
                    self.state = RETURNING
        elif self.chore is not None:
            room = self.chore[1]
            sx, sy = m.lamps[room]["switch"]
            self.target = (sx, sy)
            if self._chase(dt, G_SPEED_SUSPICIOUS):
                m.lamps[room]["lit"] = True
                m.lamps[room]["relight"] = 0.0
                m.lamps[room]["player_off"] = False
                self.chore = None
                self.said = "switch"
                self.state = RETURNING
        else:                            # PATROL / RETURNING
            sx, sy, sfacing = m.guard_schedule(self.gidx, t)
            if self.state == RETURNING:
                self.target = (sx, sy)
                if self._chase(dt, G_SPEED_SUSPICIOUS):
                    self.state = PATROL
            else:
                # on patrol the guard IS the timetable
                self.x, self.y = sx, sy
                self.facing = sfacing

        # ------------------------------------------------------ perception
        sees = can_see(m, self.x, self.y, self.facing,
                       thief.x, thief.y) and not thief.hidden
        if sees:
            self.spot += dt
        else:
            self.spot = max(0.0, self.spot - dt * 1.6)

        if self.state != ALERT and sees and self.spot >= SPOT_TIME:
            self.state = ALERT
            self.alert_t = ALERT_TIME
            self.target = (thief.x, thief.y)
            self.said = "shout"
        elif self.state == PATROL and sees and self.spot >= SUS_GLIMPSE:
            self.state = SUSPICIOUS
            self.target = (thief.x, thief.y)
            self.wait = SUS_WAIT
            self.said = "hm"
        if self.state == ALERT and sees:
            self.target = (thief.x, thief.y)
            self.alert_t = ALERT_TIME

        # noises pull patrol/suspicious guards
        for nx, ny, nr in noise_events:
            if math.hypot(nx - self.x, ny - self.y) <= nr \
                    and self.state in (PATROL, SUSPICIOUS, RETURNING):
                self.state = SUSPICIOUS
                self.target = (nx, ny)
                self.wait = SUS_WAIT
                self.said = self.said or "hm"

        # a lamp the THIEF switched off: after a while, go flip it back.
        # (rooms dark by the owner's habit stay dark - an untouched house
        # keeps its timetable, which is what the ghost solver plans on)
        if self.state == PATROL and self.chore is None:
            room = m.room_at(self.x, self.y)
            if room is not None and not m.lamps[room]["lit"] \
                    and m.lamps[room].get("player_off") \
                    and m.lamps[room]["relight"] <= 0.0:
                self.chore = ("switch", room)
                self.said = self.said or "hm"

        # caught?
        return (math.hypot(thief.x - self.x, thief.y - self.y) < CATCH_R
                and not thief.hidden)

    def _chase(self, dt, speed):
        """Walk toward self.target, sliding along walls. True if there."""
        if self.target is None:
            return True
        tx, ty = self.target
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 6.0:
            return True
        self._turn_to(math.atan2(dy, dx), dt)
        step = speed * dt
        nx = self.x + dx / dist * step
        ny = self.y + dy / dist * step
        if not self.m.solid_circle(nx, ny, 10):
            self.x, self.y = nx, ny
        elif not self.m.solid_circle(self.x, ny, 10):
            self.y = ny
        elif not self.m.solid_circle(nx, self.y, 10):
            self.x = nx
        else:
            return True                 # wedged: give up gracefully
        return False

    def _turn_to(self, angle, dt):
        diff = (angle - self.facing + math.pi) % math.tau - math.pi
        step = TURN_RATE * dt
        if abs(diff) <= step:
            self.facing = angle
        else:
            self.facing += math.copysign(step, diff)

    def _scan(self, dt, t):
        self.facing += math.sin(t * 1.7 + self.gidx) * dt * 1.2
