"""The co-driver's own run: pure pursuit plus an honest speed budget.

Steering: aim at a point on the centerline a bit ahead (further ahead the
faster we go), turn toward it. Speed: for every point of the next 500 px,
the tightest survivable speed follows from the steering model itself -
v(1 + v/F) = RATE * R - then a braking curve pulls that limit back to the
present. The driver obeys whichever limit is nearest.

He drives the same physics step as the player, every stage, before the
countdown even starts. His time is the stage's par: beat the man who can
see the whole river in his head, and the medal is gold.
"""
from __future__ import annotations

import math

from physics import place_on_track, step
from settings import (ICE_STEER_SCALE, PHYS_DT, STEER_FALLOFF, STEER_RATE,
                      TOP_SPEED)

A_BRAKE = 210.0                    # comfortable braking, px/s^2
MARGIN = 0.93                      # fraction of the theoretical corner speed
HORIZON = 520.0                    # how far ahead the budget looks, px
SCAN = 5                           # centerline points per budget sample


def corner_speed(radius, on_ice=False):
    """Max speed the steering model can hold on this radius."""
    rate = STEER_RATE * (ICE_STEER_SCALE if on_ice else 1.0)
    f = STEER_FALLOFF
    v = (-f + math.sqrt(f * f + 4.0 * f * rate * radius)) / 2.0
    return min(TOP_SPEED, v * MARGIN)


def solve(track, max_time=480.0, record=None):
    """Drive the whole stage headless. Returns (time, finished)."""
    car = place_on_track(track, track.start_s)
    t = 0.0
    stuck = 0.0
    n = len(track.pts)
    while t < max_time:
        i = car.idx
        s_here = track.s[i]
        if s_here >= track.finish_s:
            return t, True

        v = car.speed
        look = max(80.0, min(300.0, 55.0 + v * 0.62))
        ti = track.index_at_s(s_here + look)
        tx, ty = track.pts[ti]
        want = math.atan2(ty - car.y, tx - car.x)
        err = (want - car.heading + math.pi) % math.tau - math.pi
        steer = max(-1.0, min(1.0, err * 2.8))

        # speed budget over the horizon
        target = TOP_SPEED
        j = i
        while j < n and track.s[j] - s_here < HORIZON:
            kappa = abs(track.curv[j])
            if kappa > 1e-6:
                limit = corner_speed(1.0 / kappa,
                                     track.on_ice(*track.pts[j]))
                dist = max(0.0, track.s[j] - s_here - 30.0)
                limit = math.sqrt(limit * limit + 2.0 * A_BRAKE * dist)
                target = min(target, limit)
            j += SCAN
        if car.surface == "ice":
            target = min(target, max(70.0, v))  # no throttle spikes on ice

        throttle = 1.0 if v < target else 0.0
        brake = 1.0 if v > target * 1.05 else 0.0
        step(car, track, throttle, brake, steer, False, PHYS_DT)
        t += PHYS_DT
        if record is not None and int(t / PHYS_DT) % 6 == 0:
            record.append((car.x, car.y, car.heading))

        stuck = stuck + PHYS_DT if car.speed < 10.0 and t > 3.0 else 0.0
        if stuck > 4.0:
            return t, False
    return t, False
