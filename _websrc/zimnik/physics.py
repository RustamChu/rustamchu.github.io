"""The car: an arcade drift model that still tells the truth about ice.

Velocity is split into forward and lateral parts against the car's heading.
The forward part gets throttle, brake and drag; the lateral part only ever
decays - and the *rate* of that decay is the whole game. Packed snow eats
sideways speed quickly, so the car goes where it points. Black ice barely
eats it at all, so the car goes where it went. The handbrake lowers the
rate on purpose, which is how you throw the tail into a hairpin.

No randomness anywhere: with the same inputs the car drives the same
metre-perfect run, which is what makes ghosts and the co-driver's par
time honest.
"""
from __future__ import annotations

import math

from settings import (ACCEL, BANK_DRAG, BANK_HIT_SPEED, BANK_PUSH,
                      BANK_SLOW_HIT, BRAKE, DRAG, GRIP_HANDBRAKE, GRIP_ICE,
                      GRIP_SNOW, HANDBRAKE_YAW, ICE_ACCEL_SCALE,
                      ICE_STEER_SCALE, REVERSE_MAX, ROLL, STEER_FALLOFF,
                      STEER_RATE, TOP_SPEED)
from track import BANK_W


class Car:
    __slots__ = ("x", "y", "heading", "vx", "vy", "idx", "surface",
                 "slip", "in_bank", "steer_vis")

    def __init__(self, x, y, heading):
        self.x = x
        self.y = y
        self.heading = heading
        self.vx = 0.0
        self.vy = 0.0
        self.idx = 0
        self.surface = "snow"
        self.slip = 0.0
        self.in_bank = False
        self.steer_vis = 0.0

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)


def step(car, track, throttle, brake, steer, handbrake, dt):
    """Advance one fixed step; returns a list of events."""
    events = []
    kind, idx, off = track.surface(car.x, car.y, car.idx)
    car.idx = idx
    car.surface = kind
    on_ice = kind == "ice"

    fx, fy = math.cos(car.heading), math.sin(car.heading)
    nx, ny = -fy, fx
    v_f = car.vx * fx + car.vy * fy
    v_s = car.vx * nx + car.vy * ny

    # ------------------------------------------------------------- forward
    acc = ACCEL * (ICE_ACCEL_SCALE if on_ice else 1.0)
    if throttle > 0.0 and not handbrake:
        v_f += acc * throttle * dt
    if brake > 0.0:
        if v_f > 1.0:
            v_f = max(0.0, v_f - BRAKE * brake * dt)
        else:
            v_f = max(-REVERSE_MAX, v_f - acc * 0.5 * brake * dt)
    v_f -= (DRAG * v_f * abs(v_f) + ROLL * math.copysign(1.0, v_f)
            * min(1.0, abs(v_f) / 8.0)) * dt
    v_f = max(-REVERSE_MAX, min(TOP_SPEED, v_f))

    # ------------------------------------------------------------ steering
    rate = STEER_RATE / (1.0 + abs(v_f) / STEER_FALLOFF)
    if on_ice:
        rate *= ICE_STEER_SCALE
    if handbrake:
        rate *= HANDBRAKE_YAW
    roll_factor = v_f / (abs(v_f) + 10.0)      # no pivoting on the spot
    car.heading += steer * rate * roll_factor * dt
    car.steer_vis += (steer - car.steer_vis) * min(1.0, dt * 10.0)

    # ---------------------------------------------------------------- grip
    grip = GRIP_HANDBRAKE if handbrake else (GRIP_ICE if on_ice
                                             else GRIP_SNOW)
    v_s *= math.exp(-grip * dt)
    car.slip = abs(v_s)

    fx, fy = math.cos(car.heading), math.sin(car.heading)
    nx, ny = -fy, fx
    car.vx = fx * v_f + nx * v_s
    car.vy = fy * v_f + ny * v_s

    # ------------------------------------------------------------ the bank
    was_in_bank = car.in_bank
    car.in_bank = kind == "bank"
    if car.in_bank:
        half = track.half[idx]
        inward = -math.copysign(1.0, off)
        bnx, bny = -track.dirs[idx][1], track.dirs[idx][0]
        if not was_in_bank and car.speed > BANK_HIT_SPEED:
            car.vx *= BANK_SLOW_HIT
            car.vy *= BANK_SLOW_HIT
            events.append(("bank_hit", car.speed))
        elif not was_in_bank:
            events.append(("bank_soft", car.speed))
        car.vx += bnx * inward * BANK_PUSH * dt
        car.vy += bny * inward * BANK_PUSH * dt
        decay = math.exp(-BANK_DRAG * dt)
        car.vx *= decay
        car.vy *= decay
        # nobody drives off through the forest
        overshoot = abs(off) - (half + BANK_W * 2.0)
        if overshoot > 0.0:
            car.x -= bnx * math.copysign(overshoot, off)
            car.y -= bny * math.copysign(overshoot, off)

    car.x += car.vx * dt
    car.y += car.vy * dt
    return events


def place_on_track(track, s):
    """A car standing on the centerline at distance s, facing forward."""
    x, y = track.point_at_s(s)
    i = track.index_at_s(s)
    heading = math.atan2(track.dirs[i][1], track.dirs[i][0])
    car = Car(x, y, heading)
    car.idx = i
    return car
