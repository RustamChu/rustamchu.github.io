"""The ghost: A* through space AND time.

A stealth route is not a path on a map - it is a path through a
timetable. The solver expands nodes (cell_x, cell_y, tick) where a tick
is 0.25 s of the guards' fully deterministic patrol schedule, and a node
is legal only if nobody's cone covers it AT THAT MOMENT - checked with
the guards' own `can_see`, widened by a safety margin, so "the ghost was
never seen" is a statement in the guards' arithmetic, not the solver's.

The route it returns: sneak from the entrance to the safe without one
sound, stand at the dial for three unseen seconds, sneak out. The test
replays it through the live engine step by step and the engine must
agree: never seen, never suspected, escaped.
"""
from __future__ import annotations

import heapq
import math

from guards import can_see
from settings import (INTERACT_R, P_R, SAFE_DWELL, SOLVE_CELL, SOLVE_DT,
                      SOLVE_TMAX, WORLD_H, WORLD_W)

MARGIN_R = 22.0                     # extra cone reach the ghost respects
MARGIN_A = 0.10                     # extra cone width, radians


class GhostSolver:
    def __init__(self, mansion):
        self.m = mansion
        self.cw = int(WORLD_W // SOLVE_CELL)
        self.ch = int(WORLD_H // SOLVE_CELL)
        self.tmax = int(SOLVE_TMAX / SOLVE_DT)
        self.walk = [[not mansion.solid_circle(
            (cx + 0.5) * SOLVE_CELL, (cy + 0.5) * SOLVE_CELL, P_R + 2)
            for cy in range(self.ch)] for cx in range(self.cw)]
        # the timetable, tabulated once
        self.sched = []
        for ti in range(self.tmax + 1):
            t = ti * SOLVE_DT
            self.sched.append([mansion.guard_schedule(g, t)
                               for g in range(len(mansion.patrols))])

    # ------------------------------------------------------------ helpers
    def _cell_of(self, pos):
        return (int(pos[0] // SOLVE_CELL), int(pos[1] // SOLVE_CELL))

    def _center(self, cell):
        return ((cell[0] + 0.5) * SOLVE_CELL,
                (cell[1] + 0.5) * SOLVE_CELL)

    def unseen(self, x, y, ti):
        if ti > self.tmax:
            return False
        for gx, gy, facing in self.sched[ti]:
            if can_see(self.m, gx, gy, facing, x, y,
                       margin_r=MARGIN_R, margin_a=MARGIN_A):
                return False
        return True

    def _near_walkable(self, pos):
        """The walkable cell closest to a world position."""
        c0 = self._cell_of(pos)
        best, best_d = None, 1e18
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                cx, cy = c0[0] + dx, c0[1] + dy
                if 0 <= cx < self.cw and 0 <= cy < self.ch \
                        and self.walk[cx][cy]:
                    px, py = self._center((cx, cy))
                    d = (px - pos[0]) ** 2 + (py - pos[1]) ** 2
                    if d < best_d:
                        best, best_d = (cx, cy), d
        return best

    # --------------------------------------------------------------- A*
    def _search(self, start_cell, t0, goal_cell):
        """Min-time route start->goal, never entering a cone."""
        # moves: (dx, dy, ticks) - 2 ticks per cardinal cell keeps the
        # implied speed inside the silent sneak speed
        moves = ((0, 0, 1), (1, 0, 2), (-1, 0, 2), (0, 1, 2), (0, -1, 2),
                 (1, 1, 3), (-1, -1, 3), (1, -1, 3), (-1, 1, 3))
        gx, gy = goal_cell

        def h(cell):
            return (abs(cell[0] - gx) + abs(cell[1] - gy)) * 2

        openq = [(h(start_cell), t0, start_cell)]
        best = {(start_cell, t0 % 4): t0}
        came = {(start_cell, t0): None}
        while openq:
            _, ti, cell = heapq.heappop(openq)
            if cell == goal_cell:
                path = []
                key = (cell, ti)
                while key is not None:
                    path.append(key)
                    key = came.get(key)
                return path[::-1]
            if ti >= self.tmax - 4:
                continue
            for dx, dy, dt_ticks in moves:
                nx, ny = cell[0] + dx, cell[1] + dy
                if not (0 <= nx < self.cw and 0 <= ny < self.ch):
                    continue
                if not self.walk[nx][ny]:
                    continue
                nt = ti + dt_ticks
                # every intermediate tick must be unseen
                x0, y0 = self._center(cell)
                x1, y1 = self._center((nx, ny))
                ok = True
                for s in range(1, dt_ticks + 1):
                    k = s / dt_ticks
                    if not self.unseen(x0 + (x1 - x0) * k,
                                       y0 + (y1 - y0) * k, ti + s):
                        ok = False
                        break
                if not ok:
                    continue
                bkey = ((nx, ny), nt % 4)
                if best.get(bkey, 1 << 30) <= nt:
                    continue
                best[bkey] = nt
                came[((nx, ny), nt)] = (cell, ti)
                heapq.heappush(openq, (nt + h((nx, ny)), nt, (nx, ny)))
        return None

    def solve(self):
        """Full job: entrance -> safe (+3 s of quiet) -> exit.
        Returns a list of (x, y, t) or None."""
        start = self._near_walkable(self.m.start)
        safe = self._near_walkable(self.m.safe_pos)
        exit_c = self._near_walkable(self.m.exit_pos)
        if not (start and safe and exit_c):
            return None

        leg1 = self._search(start, 0, safe)
        if leg1 is None:
            return None
        t_arrive = leg1[-1][1]

        # find a quiet window at the dial
        sx, sy = self._center(safe)
        dwell = int(SAFE_DWELL / SOLVE_DT)
        t_open = None
        ti = t_arrive
        while ti + dwell < self.tmax - 40:
            if all(self.unseen(sx, sy, ti + k)
                   for k in range(dwell + 1)):
                t_open = ti + dwell
                break
            ti += 1
        if t_open is None:
            return None

        leg2 = self._search(safe, t_open, exit_c)
        if leg2 is None:
            return None

        route = []
        for cell, ti2 in leg1:
            x, y = self._center(cell)
            route.append((x, y, ti2 * SOLVE_DT))
        for k in range(t_arrive + 1, t_open + 1):
            route.append((sx, sy, k * SOLVE_DT))
        for cell, ti2 in leg2[1:]:
            x, y = self._center(cell)
            route.append((x, y, ti2 * SOLVE_DT))
        return route


def make_solvable(mission, max_attempts=24):
    """The generator's contract: only a mansion the ghost has personally
    walked ships to the player. Returns (mansion, route)."""
    from mansion import Mansion
    for attempt in range(max_attempts):
        man = Mansion(mission, attempt)
        route = GhostSolver(man).solve()
        if route is not None:
            return man, route
    raise RuntimeError("mission %d refuses to be robbed" % (mission + 1))
