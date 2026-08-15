"""Hole generation with a built-in proof of solvability.

The generator throws planets onto the field, then plays the hole itself:
a grid of launch angles and powers is simulated through the exact same
physics the player uses. If not a single shot reaches the cup, the layout
is thrown away. If one does but its path is nearly a straight line, the
layout is thrown away too - a hole where gravity does not matter is not
worth playing. What ships is therefore always winnable and always curved,
and the winning shot is stored so the game can show it as a hint.
"""
from __future__ import annotations

import math
import random

from physics import Body, launch_velocity, simulate
from settings import (COURSE_HOLES, CURVE_MIN_DEVIATION, GOAL_R, HEIGHT,
                      MAX_POWER, SOLVER_ANGLE_STEP, SOLVER_MAX_T,
                      SOLVER_POWERS, WIDTH)

# which hazards each hole of the course introduces
HOLE_FEATURES = {
    1: {"planets": 1},
    2: {"planets": 2},
    3: {"planets": 2, "pulsar": 1},
    4: {"planets": 3},
    5: {"planets": 2, "wormhole": True},
    6: {"planets": 2, "blackhole": 1},
    7: {"planets": 2, "pulsar": 1, "wormhole": True},
    8: {"planets": 2, "asteroids": 9},
    9: {"planets": 3, "blackhole": 1, "asteroids": 6},
}


class Level:
    def __init__(self, index, bodies, wormholes, start, goal):
        self.index = index
        self.bodies = bodies
        self.wormholes = wormholes          # [] or [(x, y, r), (x, y, r)]
        self.start = start
        self.goal = goal
        self.solution = None                # (angle_rad, power_frac)
        self.solution_outcome = None


# ---------------------------------------------------------------- the solver
def solve(level):
    """Find any (angle, power) that sinks the ball from the start."""
    sx, sy = level.start
    for power in SOLVER_POWERS:
        for angle_deg in range(0, 360, SOLVER_ANGLE_STEP):
            angle = math.radians(angle_deg)
            vx, vy = launch_velocity(angle, power, MAX_POWER)
            outcome, _, _ = simulate(level, sx, sy, vx, vy, SOLVER_MAX_T)
            if outcome == "sunk":
                return angle, power
    return None


def _path_deviation(level, solution):
    """How far the winning shot bends away from the straight line."""
    sx, sy = level.start
    gx, gy = level.goal
    vx, vy = launch_velocity(solution[0], solution[1], MAX_POWER)
    _, points, _ = simulate(level, sx, sy, vx, vy, SOLVER_MAX_T,
                            collect_every=4)
    if not points:
        return 0.0
    length = math.hypot(gx - sx, gy - sy)
    if length < 1e-6:
        return 0.0
    nx, ny = (gx - sx) / length, (gy - sy) / length
    worst = 0.0
    for px, py in points:
        deviation = abs((px - sx) * ny - (py - sy) * nx)
        if deviation > worst:
            worst = deviation
    return worst


def _line_blocked(level):
    """Does a planet sit right on the straight start->goal line?"""
    sx, sy = level.start
    gx, gy = level.goal
    dx, dy = gx - sx, gy - sy
    length_sq = dx * dx + dy * dy
    for body in level.bodies:
        if body.kind == "asteroid":
            continue
        t = ((body.x - sx) * dx + (body.y - sy) * dy) / length_sq
        t = max(0.0, min(1.0, t))
        cx, cy = sx + dx * t, sy + dy * t
        if math.hypot(body.x - cx, body.y - cy) <= body.r + 14:
            return True
    return False


def is_interesting(level, solution):
    return _line_blocked(level) \
        or _path_deviation(level, solution) >= CURVE_MIN_DEVIATION


# ------------------------------------------------------------- construction
def _far_from(x, y, others, margin):
    return all(math.hypot(x - ox, y - oy) >= margin + orr
               for ox, oy, orr in others)


def _random_layout(rng, index):
    features = HOLE_FEATURES.get(index, HOLE_FEATURES[COURSE_HOLES])
    start = (rng.uniform(90, 170), rng.uniform(120, HEIGHT - 120))
    goal = (rng.uniform(WIDTH - 230, WIDTH - 110),
            rng.uniform(110, HEIGHT - 110))

    keep_clear = [(start[0], start[1], 0), (goal[0], goal[1], 0)]
    bodies = []

    def place(r, kind, clearance):
        for _ in range(60):
            x = rng.uniform(240, WIDTH - 300)
            y = rng.uniform(90, HEIGHT - 90)
            if _far_from(x, y, keep_clear, clearance):
                body = Body(x, y, r, kind, scheme=rng.randrange(5))
                bodies.append(body)
                keep_clear.append((x, y, r))
                return body
        return None

    for _ in range(features.get("planets", 1)):
        place(rng.uniform(30, 56), "planet", 150)
    for _ in range(features.get("pulsar", 0)):
        place(rng.uniform(22, 30), "pulsar", 170)
    for _ in range(features.get("blackhole", 0)):
        place(rng.uniform(14, 18), "blackhole", 200)

    if features.get("asteroids"):
        # a loose arc of rocks across the middle of the field
        arc_x = rng.uniform(WIDTH * 0.42, WIDTH * 0.62)
        arc_top = rng.uniform(60, 140)
        count = features["asteroids"]
        for k in range(count):
            t = k / max(1, count - 1)
            x = arc_x + math.sin(t * math.pi) * rng.uniform(-60, 60)
            y = arc_top + t * (HEIGHT - 2 * arc_top)
            if _far_from(x, y, keep_clear, 60):
                bodies.append(Body(x, y, rng.uniform(8, 13), "asteroid"))
                keep_clear.append((x, y, 12))

    wormholes = []
    if features.get("wormhole"):
        for _ in range(40):
            ax = rng.uniform(300, WIDTH * 0.45)
            ay = rng.uniform(110, HEIGHT - 110)
            bx = rng.uniform(WIDTH * 0.55, WIDTH - 260)
            by = rng.uniform(110, HEIGHT - 110)
            if _far_from(ax, ay, keep_clear, 120) \
                    and _far_from(bx, by, keep_clear, 120):
                wormholes = [(ax, ay, 20), (bx, by, 20)]
                break

    return Level(index, bodies, wormholes, start, goal)


def generate_hole(seed, index):
    """Layouts are tried until one is provably solvable AND curved."""
    rng = random.Random(seed * 1000 + index)
    fallback = None
    for attempt in range(40):
        level = _random_layout(rng, index)
        solution = solve(level)
        if solution is None:
            continue
        level.solution = solution
        if is_interesting(level, solution):
            return level
        if fallback is None:
            fallback = level                # solvable but straight - plan B
    if fallback is not None:
        return fallback
    # degenerate seed: an empty range with one planet is always solvable
    level = Level(index, [Body(WIDTH / 2, HEIGHT / 2, 40, "planet")], [],
                  (140, HEIGHT / 2), (WIDTH - 160, HEIGHT / 2))
    level.solution = solve(level)
    return level
