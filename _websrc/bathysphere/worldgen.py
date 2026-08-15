"""Cave generation: drunkard's walk + cellular automata + marching squares.

Three stages. A drunkard's walk first staggers from the surface down to the
station, carving the guaranteed main shaft - so the dive is winnable by
construction. Random noise is then smoothed by a few passes of cellular
automata into organic-looking caverns that hang off that shaft. Finally
marching squares turns the cell grid into line segments: the sonar needs
actual wall *edges* to echo from, not filled cells, and drawing thin
segments is exactly how a phosphor screen would trace them.

Segments are bucketed into a coarse spatial hash so a ping only tests the
walls near its expanding wavefront.
"""
from __future__ import annotations

import math
import random
from collections import deque

from settings import (BLACKBOX_COUNT, CA_STEPS, CELL, GRID_H, GRID_W,
                      SURFACE_Y, WORLD_H, WORLD_W)

BUCKET = 112                        # spatial hash cell, px


class World:
    def __init__(self, seed):
        self.seed = seed
        rng = random.Random(seed)
        self.solid = [[True] * GRID_W for _ in range(GRID_H)]
        self._carve_main_shaft(rng)
        self._noise_caverns(rng)
        self._smooth()
        self._open_surface()
        self.station = self._place_station()
        self._ensure_connected()

        self.segments = []          # [(x1, y1, x2, y2), ...]
        self._march()
        self.buckets = {}
        self._bucketize()

        self.start = (self.shaft_top_x * CELL, SURFACE_Y)
        self.blackboxes = self._place_blackboxes(rng)
        self.geysers = self._place_geysers(rng)
        self.bio_lights = self._place_bio(rng)

    # ------------------------------------------------------------- carving
    def _carve_main_shaft(self, rng):
        x = rng.randint(GRID_W // 3, GRID_W * 2 // 3)
        self.shaft_top_x = x
        y = 0
        self.shaft = []
        while y < GRID_H - 6:
            self._carve_disc(x, y, rng.randint(3, 5))
            self.shaft.append((x, y))
            y += rng.randint(1, 2)
            x += rng.randint(-2, 2)
            x = max(6, min(GRID_W - 7, x))
        self.shaft_bottom = (x, y)

    def _carve_disc(self, cx, cy, r):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    x, y = cx + dx, cy + dy
                    if 1 <= x < GRID_W - 1 and 1 <= y < GRID_H - 1:
                        self.solid[y][x] = False

    def _noise_caverns(self, rng):
        for y in range(1, GRID_H - 1):
            # deeper water is tighter: less open noise near the bottom
            openness = 0.46 - 0.12 * (y / GRID_H)
            for x in range(1, GRID_W - 1):
                if rng.random() < openness:
                    self.solid[y][x] = False

    def _smooth(self):
        for _ in range(CA_STEPS):
            nxt = [row[:] for row in self.solid]
            for y in range(1, GRID_H - 1):
                row_a = self.solid[y - 1]
                row_b = self.solid[y]
                row_c = self.solid[y + 1]
                for x in range(1, GRID_W - 1):
                    walls = (row_a[x - 1] + row_a[x] + row_a[x + 1]
                             + row_b[x - 1] + row_b[x + 1]
                             + row_c[x - 1] + row_c[x] + row_c[x + 1])
                    if walls >= 5:
                        nxt[y][x] = True
                    elif walls <= 2:
                        nxt[y][x] = False
            self.solid = nxt
        # hard border so nothing leaks off the map
        for x in range(GRID_W):
            self.solid[0][x] = self.solid[GRID_H - 1][x] = True
        for y in range(GRID_H):
            self.solid[y][0] = self.solid[y][GRID_W - 1] = True

    def _open_surface(self):
        top_cells = SURFACE_Y // CELL + 4
        for y in range(1, top_cells):
            for x in range(self.shaft_top_x - 5, self.shaft_top_x + 6):
                if 1 <= x < GRID_W - 1:
                    self.solid[y][x] = False

    def _place_station(self):
        bx, by = self.shaft_bottom
        self._carve_disc(bx, min(GRID_H - 8, by + 2), 6)
        return (bx * CELL, min(GRID_H - 8, by + 2) * CELL)

    def _ensure_connected(self):
        """BFS from the surface must reach the station; else carve the shaft
        wider. The walk guarantees it in practice - this is the seatbelt."""
        for _ in range(3):
            if self._reaches_station():
                return
            for (x, y) in self.shaft:
                self._carve_disc(x, y, 4)
        # last resort: a straight drop
        sx = self.shaft_top_x
        for y in range(1, self.station[1] // CELL + 1):
            self._carve_disc(sx, y, 3)

    def _reaches_station(self):
        start = (self.shaft_top_x, SURFACE_Y // CELL + 1)
        goal = (int(self.station[0] // CELL), int(self.station[1] // CELL))
        seen = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            if abs(x - goal[0]) + abs(y - goal[1]) <= 3:
                return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen or not (0 <= nx < GRID_W
                                            and 0 <= ny < GRID_H):
                    continue
                if self.solid[ny][nx]:
                    continue
                seen.add((nx, ny))
                queue.append((nx, ny))
        self._reachable = seen
        return False

    # ------------------------------------------------------ marching squares
    _EDGES = {
        1: ((0.0, 0.5), (0.5, 1.0)), 2: ((0.5, 1.0), (1.0, 0.5)),
        3: ((0.0, 0.5), (1.0, 0.5)), 4: ((0.5, 0.0), (1.0, 0.5)),
        5: ((0.0, 0.5), (0.5, 0.0), (0.5, 1.0), (1.0, 0.5)),
        6: ((0.5, 0.0), (0.5, 1.0)), 7: ((0.0, 0.5), (0.5, 0.0)),
        8: ((0.0, 0.5), (0.5, 0.0)), 9: ((0.5, 0.0), (0.5, 1.0)),
        10: ((0.0, 0.5), (0.5, 1.0), (0.5, 0.0), (1.0, 0.5)),
        11: ((0.5, 0.0), (1.0, 0.5)), 12: ((0.0, 0.5), (1.0, 0.5)),
        13: ((0.5, 1.0), (1.0, 0.5)), 14: ((0.0, 0.5), (0.5, 1.0)),
    }

    def _march(self):
        solid = self.solid
        for y in range(GRID_H - 1):
            row0, row1 = solid[y], solid[y + 1]
            for x in range(GRID_W - 1):
                case = (row0[x] << 3 | row0[x + 1] << 2
                        | row1[x + 1] << 1 | row1[x])
                pairs = self._EDGES.get(case)
                if not pairs:
                    continue
                px, py = x * CELL, y * CELL
                for i in range(0, len(pairs), 2):
                    (ax, ay), (bx, by) = pairs[i], pairs[i + 1]
                    self.segments.append((px + ax * CELL, py + ay * CELL,
                                          px + bx * CELL, py + by * CELL))

    def _bucketize(self):
        for idx, (x1, y1, x2, y2) in enumerate(self.segments):
            bx = int(((x1 + x2) * 0.5) // BUCKET)
            by = int(((y1 + y2) * 0.5) // BUCKET)
            self.buckets.setdefault((bx, by), []).append(idx)

    def segments_near(self, x, y, radius):
        """Indices of wall segments within radius (via the spatial hash)."""
        result = []
        b0x = int((x - radius) // BUCKET)
        b1x = int((x + radius) // BUCKET)
        b0y = int((y - radius) // BUCKET)
        b1y = int((y + radius) // BUCKET)
        for by in range(b0y, b1y + 1):
            for bx in range(b0x, b1x + 1):
                result.extend(self.buckets.get((bx, by), ()))
        return result

    # ------------------------------------------------------------- queries
    def is_solid_at(self, x, y):
        cx, cy = int(x // CELL), int(y // CELL)
        if not (0 <= cx < GRID_W and 0 <= cy < GRID_H):
            return True
        return self.solid[cy][cx]

    def free_spot_near(self, x, y, rng, tries=200):
        for _ in range(tries):
            px = x + rng.uniform(-260, 260)
            py = y + rng.uniform(-260, 260)
            if not self.is_solid_at(px, py) \
                    and not self.is_solid_at(px + 20, py) \
                    and not self.is_solid_at(px - 20, py) \
                    and not self.is_solid_at(px, py + 20):
                return px, py
        return x, y

    # ------------------------------------------------------------ placement
    def _place_blackboxes(self, rng):
        boxes = []
        for k in range(BLACKBOX_COUNT):
            frac = 0.22 + 0.24 * k
            gx, gy = self.shaft[min(len(self.shaft) - 1,
                                    int(len(self.shaft) * frac))]
            x, y = self.free_spot_near(gx * CELL, gy * CELL, rng)
            boxes.append({"x": x, "y": y, "found": False, "idx": k})
        return boxes

    def _place_geysers(self, rng):
        geysers = []
        for _ in range(7):
            gx, gy = rng.choice(self.shaft[len(self.shaft) // 3:])
            x, y = self.free_spot_near(gx * CELL, gy * CELL, rng)
            geysers.append({"x": x, "y": y,
                            "period": rng.uniform(*(5.0, 9.0)),
                            "phase": rng.uniform(0, 9.0),
                            "angle": rng.uniform(-0.5, 0.5) - math.pi / 2})
        return geysers

    def _place_bio(self, rng):
        """Colonies cling to rock, so they outline the caves faintly."""
        lights = []
        attempts = 0
        while len(lights) < 90 and attempts < 6000:
            attempts += 1
            x = rng.uniform(0, WORLD_W)
            y = rng.uniform(SURFACE_Y + 400, WORLD_H - 60)
            if self.is_solid_at(x, y):
                continue
            near_rock = any(self.is_solid_at(x + dx, y + dy)
                            for dx, dy in ((CELL * 2, 0), (-CELL * 2, 0),
                                           (0, CELL * 2), (0, -CELL * 2)))
            if not near_rock:
                continue
            lights.append((x, y, rng.uniform(0, math.tau),
                           rng.uniform(1.5, 4.0)))
        return lights
