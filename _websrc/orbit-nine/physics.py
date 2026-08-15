"""The physics core: gravity, integration, collisions, one shared `step`.

Everything that flies in this game - the real ball, the aiming preview and
the level solver - goes through the same step() at the same fixed timestep.
That single decision buys three guarantees at once: the dotted preview never
lies, the solver's proof of solvability replays identically in play, and the
whole simulation is deterministic for the tests.

Integration is semi-implicit Euler (velocity first, then position): for
orbital motion it conserves energy dramatically better than the naive
version, which quietly spirals every orbit outward.
"""
from __future__ import annotations

import math

from settings import (ACCEL_CAP, BALL_R, BLACKHOLE_HORIZON, FLIGHT_MAX, G,
                      GOAL_R, HEIGHT, OOB_MARGIN, PHYS_DT, RESTITUTION,
                      STICK_SPEED, TANGENT_FRICTION, WIDTH,
                      WORMHOLE_COOLDOWN)

SOLID = ("planet", "pulsar", "asteroid")


class Body:
    """A planet, pulsar, black hole or asteroid."""

    def __init__(self, x, y, r, kind="planet", scheme=0):
        self.x = x
        self.y = y
        self.r = r
        self.kind = kind
        self.scheme = scheme
        if kind == "pulsar":
            self.mass = -(r * r) * 1.6        # negative mass pushes away
        elif kind == "blackhole":
            self.mass = (r * r) * 5.0
        elif kind == "asteroid":
            self.mass = 0.0                   # rocks bounce but do not pull
        else:
            self.mass = float(r * r)


class FlightState:
    """A moving ball - the real one or a hypothetical solver/preview one."""

    __slots__ = ("x", "y", "vx", "vy", "t", "warp_cd")

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.t = 0.0
        self.warp_cd = 0.0


def gravity_at(bodies, x, y):
    ax = ay = 0.0
    for body in bodies:
        if body.mass == 0.0:
            continue
        dx = body.x - x
        dy = body.y - y
        dist_sq = dx * dx + dy * dy
        if dist_sq < 1.0:
            continue
        dist = math.sqrt(dist_sq)
        accel = G * body.mass / dist_sq
        if accel > ACCEL_CAP:
            accel = ACCEL_CAP
        elif accel < -ACCEL_CAP:
            accel = -ACCEL_CAP
        ax += accel * dx / dist
        ay += accel * dy / dist
    return ax, ay


def step(level, state, dt=PHYS_DT):
    """Advance one tick. Returns None or an event string:

    "sunk" | "stuck" | "oob" | "swallowed" | "timeout" | "warp"
    """
    ax, ay = gravity_at(level.bodies, state.x, state.y)
    state.vx += ax * dt
    state.vy += ay * dt
    state.x += state.vx * dt
    state.y += state.vy * dt
    state.t += dt
    if state.warp_cd > 0.0:
        state.warp_cd -= dt

    # the cup
    gx, gy = level.goal
    if math.hypot(state.x - gx, state.y - gy) <= GOAL_R:
        return "sunk"

    # lost in space
    if (state.x < -OOB_MARGIN or state.x > WIDTH + OOB_MARGIN
            or state.y < -OOB_MARGIN or state.y > HEIGHT + OOB_MARGIN):
        return "oob"

    # wormholes: jump to the twin, keep the velocity vector
    if level.wormholes and state.warp_cd <= 0.0:
        for i, (wx, wy, wr) in enumerate(level.wormholes):
            if math.hypot(state.x - wx, state.y - wy) <= wr:
                ox, oy, orr = level.wormholes[1 - i]
                speed = math.hypot(state.vx, state.vy)
                if speed > 1e-6:
                    nx, ny = state.vx / speed, state.vy / speed
                else:
                    nx, ny = 1.0, 0.0
                state.x = ox + nx * (orr + BALL_R + 2)
                state.y = oy + ny * (orr + BALL_R + 2)
                state.warp_cd = WORMHOLE_COOLDOWN
                return "warp"

    # bodies
    for body in level.bodies:
        dx = state.x - body.x
        dy = state.y - body.y
        dist = math.hypot(dx, dy)

        if body.kind == "blackhole":
            if dist <= body.r * BLACKHOLE_HORIZON:
                return "swallowed"
            continue

        if body.kind in SOLID and dist <= body.r + BALL_R:
            if dist < 1e-6:
                dx, dy, dist = 1.0, 0.0, 1.0
            nx, ny = dx / dist, dy / dist
            # push out of the surface
            state.x = body.x + nx * (body.r + BALL_R)
            state.y = body.y + ny * (body.r + BALL_R)
            v_normal = state.vx * nx + state.vy * ny
            tx, ty = -ny, nx
            v_tangent = state.vx * tx + state.vy * ty
            if abs(v_normal) < STICK_SPEED and body.kind != "asteroid":
                return "stuck"
            v_normal = -v_normal * RESTITUTION
            v_tangent *= TANGENT_FRICTION
            state.vx = v_normal * nx + v_tangent * tx
            state.vy = v_normal * ny + v_tangent * ty
            if math.hypot(state.vx, state.vy) < STICK_SPEED * 0.6 \
                    and body.kind != "asteroid":
                return "stuck"
            return None

    if state.t >= FLIGHT_MAX:
        return "timeout"
    return None


def simulate(level, x, y, vx, vy, max_t, collect_every=0):
    """Fly a hypothetical ball to its conclusion.

    Returns (outcome, points, state). `outcome` is the terminal event or
    "flying" if max_t ran out first; `points` samples the path every
    `collect_every` steps when it is non-zero.
    """
    state = FlightState(x, y, vx, vy)
    points = []
    steps = int(max_t / PHYS_DT)
    for i in range(steps):
        event = step(level, state)
        if collect_every and i % collect_every == 0:
            points.append((state.x, state.y))
        if event == "warp":
            continue
        if event is not None:
            return event, points, state
    return "flying", points, state


def launch_velocity(angle_rad, power_frac, max_power):
    speed = max(0.05, min(1.0, power_frac)) * max_power
    return math.cos(angle_rad) * speed, math.sin(angle_rad) * speed
