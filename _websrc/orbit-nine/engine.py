"""Course state: the ball, strokes, scoring, hole progression.

Knows nothing about pygame; the headless test drives it directly.
"""
from __future__ import annotations

import math
import random

from level import generate_hole
from physics import FlightState, launch_velocity, simulate, step
from settings import (BALL_R, COURSE_HOLES, MAX_POWER, PAR, PHYS_DT,
                      PREVIEW_T)

AIM, FLYING, HOLE_DONE, COURSE_DONE = "aim", "flying", "hole_done", "done"


class _NoSound:
    def play(self, name):
        pass


class Engine:
    def __init__(self, seed=None, sound=None):
        self.seed = seed if seed is not None else random.randrange(1 << 24)
        self.sound = sound or _NoSound()
        self.hole_idx = 1
        self.strokes = [0] * (COURSE_HOLES + 1)     # index by hole number
        self.done = [False] * (COURSE_HOLES + 1)
        self._levels = {}
        self.state = AIM
        self.flight = None                          # FlightState while flying
        self.trail = []
        self.events = []                            # renderer drains these
        self.penalty_flash = 0.0
        self.save_pending = False
        self.level = self.current_level()
        self.ball = list(self.level.start)
        self.rest_point = tuple(self.ball)

    # ------------------------------------------------------------- course
    def current_level(self):
        if self.hole_idx not in self._levels:
            self._levels[self.hole_idx] = generate_hole(self.seed,
                                                        self.hole_idx)
        return self._levels[self.hole_idx]

    @property
    def total_strokes(self):
        return sum(s for i, s in enumerate(self.strokes) if self.done[i])

    @property
    def total_par(self):
        return PAR * sum(1 for d in self.done if d)

    @property
    def relative_score(self):
        """Classic golf notation: -2, E, +5."""
        diff = self.total_strokes - self.total_par
        if diff == 0:
            return "E"
        return "{:+d}".format(diff)

    @property
    def finished(self):
        return self.state == COURSE_DONE

    def next_hole(self):
        if self.state != HOLE_DONE:
            return False
        if self.hole_idx >= COURSE_HOLES:
            self.state = COURSE_DONE
            self.sound.play("win")
            return True
        self.hole_idx += 1
        self.level = self.current_level()
        self.ball = list(self.level.start)
        self.rest_point = tuple(self.ball)
        self.trail = []
        self.state = AIM
        self.save_pending = True
        return True

    def restart_hole(self):
        if self.state == COURSE_DONE:
            return
        self.strokes[self.hole_idx] = 0
        self.done[self.hole_idx] = False
        self.ball = list(self.level.start)
        self.rest_point = tuple(self.ball)
        self.trail = []
        self.flight = None
        self.state = AIM

    # -------------------------------------------------------------- aiming
    def preview(self, angle, power_frac):
        """The dotted line the player sees - same physics, same timestep."""
        vx, vy = launch_velocity(angle, power_frac, MAX_POWER)
        outcome, points, _ = simulate(self.level, self.ball[0], self.ball[1],
                                      vx, vy, PREVIEW_T, collect_every=6)
        return points, outcome

    def hint(self):
        """The generator's own winning shot, replayed as a path."""
        solution = self.level.solution
        if solution is None:
            return []
        vx, vy = launch_velocity(solution[0], solution[1], MAX_POWER)
        _, points, _ = simulate(self.level, *self.level.start, vx, vy,
                                6.0, collect_every=6)
        return points

    def launch(self, angle, power_frac):
        if self.state != AIM:
            return False
        vx, vy = launch_velocity(angle, power_frac, MAX_POWER)
        self.flight = FlightState(self.ball[0], self.ball[1], vx, vy)
        self.strokes[self.hole_idx] += 1
        self.rest_point = tuple(self.ball)
        self.trail = []
        self.state = FLYING
        self.sound.play("launch")
        return True

    # -------------------------------------------------------------- update
    def update(self, dt):
        if self.state != FLYING:
            if self.penalty_flash > 0:
                self.penalty_flash -= dt
            return
        remaining = dt
        while remaining > 1e-9 and self.state == FLYING:
            event = step(self.level, self.flight, PHYS_DT)
            remaining -= PHYS_DT
            self.ball[0], self.ball[1] = self.flight.x, self.flight.y
            self.trail.append((self.flight.x, self.flight.y))
            if len(self.trail) > 90:
                self.trail.pop(0)
            if event is None:
                continue
            self._handle(event)

    def _handle(self, event):
        if event == "warp":
            self.sound.play("warp")
            self.events.append(("warp", tuple(self.ball)))
            return
        if event == "sunk":
            self.done[self.hole_idx] = True
            self.state = HOLE_DONE
            self.flight = None
            self.sound.play("sunk")
            self.events.append(("sunk", tuple(self.level.goal)))
            self.save_pending = True
            return
        if event in ("stuck", "timeout"):
            self.rest_point = tuple(self.ball)
            self.state = AIM
            self.flight = None
            self.sound.play("bounce")
            return
        if event == "oob":
            self.strokes[self.hole_idx] += 1        # penalty stroke
            self.penalty_flash = 1.0
            self.events.append(("penalty", "улетел в космос  +1"))
            self._return_ball()
            self.sound.play("lost")
            return
        if event == "swallowed":
            self.strokes[self.hole_idx] += 1
            self.penalty_flash = 1.0
            self.events.append(("penalty", "поглощён дырой  +1"))
            self._return_ball()
            self.sound.play("swallow")
            return

    def _return_ball(self):
        self.ball = list(self.rest_point)
        self.flight = None
        self.trail = []
        self.state = AIM

    # ---------------------------------------------------------------- misc
    def drag_to_shot(self, drag_dx, drag_dy):
        """Mouse drag vector -> (angle away from drag, power fraction)."""
        from settings import DRAG_FULL
        length = math.hypot(drag_dx, drag_dy)
        if length < 6:
            return None
        angle = math.atan2(-drag_dy, -drag_dx)      # slingshot: pull back
        power = min(1.0, length / DRAG_FULL)
        return angle, power
