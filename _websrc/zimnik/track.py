"""Stage generation: the frozen river, its ice, its scenery, its pace notes.

A stage is a wandering polyline resampled to a uniform 7 px step. Everything
else - road width, curvature, ice patches, checkpoints, the co-driver's
notes - hangs off that centerline. Two hard guarantees, both tested:

* no corner is tighter than MIN_RADIUS (an iterative smoother enforces it,
  so every stage is drivable by construction);
* the road never crosses itself (checked with a spatial hash; a bad roll
  regenerates from the next sub-seed).
"""
from __future__ import annotations

import math
import random
from bisect import bisect_right

from settings import (CAT_RADII, CHECKPOINT_EVERY_M, HAIRPIN_R, ICE_PATCHES,
                      ICE_R, LONG_TURN, MIN_RADIUS, PX_PER_M, ROAD_HALF,
                      STAGE_LEN_M, STEP, STRAIGHT_MIN, SWING)

BUCKET = 180.0
BANK_W = 30.0


def _circumradius(a, b, c):
    """Radius through three points; None for collinear (= straight)."""
    abx, aby = b[0] - a[0], b[1] - a[1]
    acx, acy = c[0] - a[0], c[1] - a[1]
    cross = abx * acy - aby * acx
    if abs(cross) < 1e-9:
        return None, 0.0
    la = math.hypot(abx, aby)
    lb = math.hypot(c[0] - b[0], c[1] - b[1])
    lc = math.hypot(acx, acy)
    return (la * lb * lc) / (2.0 * abs(cross)), cross


class TrackError(Exception):
    pass


class Track:
    def __init__(self, seed):
        self.seed = seed
        last_error = None
        for attempt in range(24):
            rng = random.Random(seed * 1000003 + attempt)
            try:
                self._build(rng)
                self.attempts = attempt + 1
                break
            except TrackError as err:
                last_error = err
        else:
            raise RuntimeError("track generation failed: %s" % last_error)
        self.par = None                     # filled by the AI driver

    # ------------------------------------------------------------ pipeline
    def _build(self, rng):
        line = self._compose(rng)
        line = self._enforce_radius(line)
        self._finalize(line, rng)
        self._check_self_intersection()
        self._widths(rng)
        self._ice(rng)
        self._checkpoints()
        self._scenery(rng)
        self._pace_notes()

    def _compose(self, rng):
        """The stage is a sentence of rally moves: straights and arcs.

        Arcs start tangent to the current heading, so the line is C1 by
        construction; radii are chosen from note categories directly.
        """
        target = rng.uniform(*STAGE_LEN_M) * PX_PER_M
        x, y = 0.0, 0.0
        heading = -math.pi / 2                 # north, screen up
        line = [(x, y)]
        total = 0.0

        def emit_straight(length):
            nonlocal x, y, total
            steps = max(2, int(length / (STEP * 0.8)))
            for _ in range(steps):
                x += math.cos(heading) * length / steps
                y += math.sin(heading) * length / steps
                line.append((x, y))
            total += length

        def emit_arc(radius, angle, sign):
            nonlocal x, y, heading, total
            length = radius * angle
            steps = max(4, int(length / (STEP * 0.8)))
            for _ in range(steps):
                heading += sign * angle / steps
                x += math.cos(heading) * length / steps
                y += math.sin(heading) * length / steps
                line.append((x, y))
            total += length

        emit_straight(420.0)                   # launch runway
        while total < target:
            dev = (heading + math.pi / 2 + math.pi) % math.tau - math.pi
            move = rng.choices(("straight", "corner", "tight", "chicane"),
                               weights=(0.30, 0.42, 0.13, 0.15))[0]
            # pick the turn direction that keeps the river going north
            if x > SWING or dev > 0.9:
                sign = -1.0
            elif x < -SWING or dev < -0.9:
                sign = 1.0
            else:
                sign = rng.choice((-1.0, 1.0))

            if move == "straight":
                emit_straight(rng.uniform(190.0, 520.0))
            elif move == "corner":
                radius = rng.uniform(95.0, 320.0)
                emit_arc(radius, rng.uniform(0.55, 1.5), sign)
            elif move == "tight":
                radius = rng.uniform(66.0, 95.0)
                emit_arc(radius, rng.uniform(1.1, 2.6), sign)
            else:                              # chicane
                radius = rng.uniform(120.0, 230.0)
                angle = rng.uniform(0.5, 0.85)
                emit_arc(radius, angle, sign)
                emit_straight(rng.uniform(30.0, 90.0))
                emit_arc(radius * rng.uniform(0.8, 1.2), angle, -sign)
            # a corrective nudge back toward due north after wild moves
            dev = (heading + math.pi / 2 + math.pi) % math.tau - math.pi
            if abs(dev) > 1.35:
                emit_arc(rng.uniform(130.0, 210.0),
                         min(1.6, abs(dev) - 0.7), -math.copysign(1.0, dev))
        emit_straight(480.0)                   # flying finish + runoff
        return self._resample(line)

    @staticmethod
    def _resample(line):
        out = [line[0]]
        carry = 0.0
        for i in range(1, len(line)):
            ax, ay = line[i - 1]
            bx, by = line[i]
            seg = math.hypot(bx - ax, by - ay)
            if seg < 1e-9:
                continue
            while carry + seg >= STEP:
                t = (STEP - carry) / seg
                ax, ay = ax + (bx - ax) * t, ay + (by - ay) * t
                out.append((ax, ay))
                seg = math.hypot(bx - ax, by - ay)
                carry = 0.0
            carry += seg
        return out

    def _enforce_radius(self, line):
        line = [list(p) for p in line]
        n = len(line)
        for _ in range(900):
            bad = 0
            for i in range(2, n - 2):
                radius, _ = _circumradius(line[i - 2], line[i], line[i + 2])
                if radius is not None and radius < MIN_RADIUS * 1.15:
                    bad += 1
                    line[i][0] += 0.5 * ((line[i - 2][0] + line[i + 2][0]) / 2
                                         - line[i][0])
                    line[i][1] += 0.5 * ((line[i - 2][1] + line[i + 2][1]) / 2
                                         - line[i][1])
            if not bad:
                break
        else:
            raise TrackError("smoother did not converge")
        return self._resample([tuple(p) for p in line])

    def _finalize(self, line, rng):
        self.pts = line
        n = len(line)
        self.dirs = []
        self.curv = [0.0] * n
        for i in range(n):
            a = line[max(0, i - 1)]
            b = line[min(n - 1, i + 1)]
            d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            self.dirs.append(((b[0] - a[0]) / d, (b[1] - a[1]) / d))
        for i in range(2, n - 2):
            radius, cross = _circumradius(line[i - 2], line[i], line[i + 2])
            if radius is not None:
                self.curv[i] = math.copysign(1.0 / radius, cross)
        # light smoothing so notes do not flicker between categories
        smoothed = self.curv[:]
        for i in range(2, n - 2):
            smoothed[i] = sum(self.curv[i - 2:i + 3]) / 5.0
        self.curv = smoothed

        self.s = [0.0] * n
        for i in range(1, n):
            self.s[i] = self.s[i - 1] + math.hypot(
                line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1])
        self.total = self.s[-1]
        self.start_s = 140.0
        self.finish_s = self.total - 320.0
        if self.finish_s < 2000.0:
            raise TrackError("stage came out too short")

        self.buckets = {}
        for i, (x, y) in enumerate(line):
            key = (int(x // BUCKET), int(y // BUCKET))
            self.buckets.setdefault(key, []).append(i)

    def _check_self_intersection(self):
        for i, (x, y) in enumerate(self.pts):
            for j in self.near_indices(x, y, 130.0):
                if abs(self.s[i] - self.s[j]) > 420.0:
                    dx, dy = self.pts[j][0] - x, self.pts[j][1] - y
                    if math.hypot(dx, dy) < 128.0:
                        raise TrackError("river folded onto itself")

    def _widths(self, rng):
        n = len(self.pts)
        base = rng.uniform(*ROAD_HALF)
        p1, p2 = rng.uniform(0, 9), rng.uniform(0, 9)
        self.half = [
            max(ROAD_HALF[0], min(ROAD_HALF[1],
                base + 7.0 * math.sin(self.s[i] / 690.0 + p1)
                + 5.0 * math.sin(self.s[i] / 273.0 + p2)))
            for i in range(n)]

    def _ice(self, rng):
        self.ice = []
        count = rng.randint(*ICE_PATCHES)
        tries = 0
        while len(self.ice) < count and tries < 400:
            tries += 1
            s = rng.uniform(self.start_s + 300.0, self.finish_s - 200.0)
            i = self.index_at_s(s)
            r = rng.uniform(*ICE_R)
            off = rng.uniform(-0.5, 0.5) * self.half[i]
            nx, ny = -self.dirs[i][1], self.dirs[i][0]
            x = self.pts[i][0] + nx * off
            y = self.pts[i][1] + ny * off
            if all(math.hypot(x - ix, y - iy) > r + ir + 40.0
                   for ix, iy, ir, _ in self.ice):
                self.ice.append((x, y, r, rng.random()))

    def _checkpoints(self):
        every = CHECKPOINT_EVERY_M * PX_PER_M
        self.checkpoints = []
        s = self.start_s + every
        while s < self.finish_s - every * 0.5:
            self.checkpoints.append(s)
            s += every

    def _scenery(self, rng):
        self.scenery = []
        i = 0
        n = len(self.pts)
        while i < n:
            for side in (-1.0, 1.0):
                if rng.random() < 0.62:
                    kind = rng.choices(
                        ("pine", "birch", "drift", "rock"),
                        weights=(0.46, 0.26, 0.18, 0.10))[0]
                    off = self.half[i] + BANK_W + rng.uniform(14.0, 150.0)
                    nx, ny = -self.dirs[i][1], self.dirs[i][0]
                    self.scenery.append(
                        (self.pts[i][0] + nx * off * side,
                         self.pts[i][1] + ny * off * side,
                         kind, rng.random(),
                         rng.uniform(0.75, 1.35)))
            i += rng.randint(3, 6)
        # km/100 posts down the right bank
        post_s = 500.0
        num = 1
        while post_s < self.finish_s:
            i = self.index_at_s(post_s)
            nx, ny = -self.dirs[i][1], self.dirs[i][0]
            off = self.half[i] + 14.0
            self.scenery.append((self.pts[i][0] + nx * off,
                                 self.pts[i][1] + ny * off,
                                 "post", float(num), 1.0))
            post_s += 500.0
            num += 1
        # somebody lives out here
        for kind in ("hut", "tent", "tent"):
            s = rng.uniform(self.total * 0.2, self.total * 0.9)
            i = self.index_at_s(s)
            nx, ny = -self.dirs[i][1], self.dirs[i][0]
            side = rng.choice((-1.0, 1.0))
            off = self.half[i] + BANK_W + rng.uniform(60.0, 130.0)
            self.scenery.append((self.pts[i][0] + nx * off * side,
                                 self.pts[i][1] + ny * off * side,
                                 kind, rng.random(), 1.0))

        self.scenery_buckets = {}
        for idx, item in enumerate(self.scenery):
            key = (int(item[0] // BUCKET), int(item[1] // BUCKET))
            self.scenery_buckets.setdefault(key, []).append(idx)

    # ---------------------------------------------------------- pace notes
    def _pace_notes(self):
        thresh = 1.0 / CAT_RADII[-1][0]
        n = len(self.pts)
        regions = []
        i = 0
        while i < n:
            if abs(self.curv[i]) >= thresh:
                sign = 1.0 if self.curv[i] > 0 else -1.0
                j = i
                gap = 0
                peak = 0.0
                while j < n and gap <= 4:
                    if abs(self.curv[j]) >= thresh \
                            and (self.curv[j] > 0) == (sign > 0):
                        gap = 0
                        peak = max(peak, abs(self.curv[j]))
                    else:
                        gap += 1
                    j += 1
                regions.append((self.s[i], self.s[min(j, n - 1)], sign, peak))
                i = j
            else:
                i += 1

        notes = []
        for s0, s1, sign, peak in regions:
            if s1 < self.start_s or s0 > self.finish_s:
                continue
            radius = 1.0 / peak
            word = "правый" if sign > 0 else "левый"
            if radius < HAIRPIN_R:
                text = "шпилька " + ("вправо" if sign > 0 else "влево")
                cat = 0
            else:
                cat = 6
                for r_lim, c in CAT_RADII:
                    if radius < r_lim:
                        cat = c
                        break
                if cat == 6:
                    continue                     # flat-out kink, no call
                text = "%s %d" % (word, cat)
            if s1 - s0 > LONG_TURN:
                text += ", длинный"
            notes.append({"s": s0, "end": s1, "text": text,
                          "kind": "turn", "cat": cat})

        # straights between calls, and ice warnings
        notes.sort(key=lambda note: note["s"])
        extras = []
        prev_end = self.start_s
        for note in notes:
            gap = note["s"] - prev_end
            if gap > STRAIGHT_MIN:
                metres = int(gap / PX_PER_M // 10 * 10)
                extras.append({"s": prev_end + 40.0, "end": note["s"],
                               "text": "прямая %d" % metres,
                               "kind": "straight", "cat": 9})
            prev_end = max(prev_end, note["end"])
        big_ice = sorted((p for p in self.ice if p[2] > 78.0),
                         key=lambda p: -p[2])[:4]
        for x, y, r, _ in big_ice:
            idx = self.locate(x, y)
            extras.append({"s": max(0.0, self.s[idx] - 60.0),
                           "end": self.s[idx] + r,
                           "text": "лёд!", "kind": "ice", "cat": 0})
        notes += extras
        notes.append({"s": self.finish_s - 900.0, "end": self.finish_s,
                      "text": "финиш через 180", "kind": "straight",
                      "cat": 9})
        notes.sort(key=lambda note: note["s"])

        # tight sequences get the co-driver's "сразу"
        for a, b in zip(notes, notes[1:]):
            if (a["kind"] == "turn" and b["kind"] == "turn"
                    and 0.0 < b["s"] - a["end"] < 110.0):
                b["text"] = "сразу " + b["text"]
        self.notes = notes

    # -------------------------------------------------------------- queries
    def near_indices(self, x, y, radius):
        out = []
        r = int(radius // BUCKET) + 1
        bx, by = int(x // BUCKET), int(y // BUCKET)
        for gy in range(by - r, by + r + 1):
            for gx in range(bx - r, bx + r + 1):
                out.extend(self.buckets.get((gx, gy), ()))
        return out

    def scenery_near(self, x, y, radius):
        out = []
        r = int(radius // BUCKET) + 1
        bx, by = int(x // BUCKET), int(y // BUCKET)
        for gy in range(by - r, by + r + 1):
            for gx in range(bx - r, bx + r + 1):
                out.extend(self.scenery_buckets.get((gx, gy), ()))
        return out

    def locate(self, x, y, hint=None):
        """Nearest centerline index; `hint` makes it O(1) frame to frame."""
        n = len(self.pts)
        if hint is not None:
            lo, hi = max(0, hint - 60), min(n, hint + 61)
            best, best_d = hint, float("inf")
            for i in range(lo, hi):
                d = ((self.pts[i][0] - x) ** 2 + (self.pts[i][1] - y) ** 2)
                if d < best_d:
                    best, best_d = i, d
            if best not in (lo, hi - 1) or best in (0, n - 1):
                return best
        cands = self.near_indices(x, y, 240.0) or range(0, n, 6)
        best, best_d = 0, float("inf")
        for i in cands:
            d = (self.pts[i][0] - x) ** 2 + (self.pts[i][1] - y) ** 2
            if d < best_d:
                best, best_d = i, d
        return best

    def index_at_s(self, s):
        i = bisect_right(self.s, s) - 1
        return max(0, min(len(self.pts) - 1, i))

    def point_at_s(self, s):
        i = self.index_at_s(s)
        if i >= len(self.pts) - 1:
            return self.pts[-1]
        t = (s - self.s[i]) / max(1e-9, self.s[i + 1] - self.s[i])
        ax, ay = self.pts[i]
        bx, by = self.pts[i + 1]
        return (ax + (bx - ax) * t, ay + (by - ay) * t)

    def offset(self, x, y, idx):
        """Signed lateral offset from the centerline at index idx."""
        nx, ny = -self.dirs[idx][1], self.dirs[idx][0]
        return (x - self.pts[idx][0]) * nx + (y - self.pts[idx][1]) * ny

    def on_ice(self, x, y):
        for ix, iy, r, _ in self.ice:
            if (x - ix) ** 2 + (y - iy) ** 2 < r * r:
                return True
        return False

    def surface(self, x, y, hint=None):
        """(kind, idx, signed_offset). kind: 'snow' | 'ice' | 'bank'."""
        idx = self.locate(x, y, hint)
        off = self.offset(x, y, idx)
        if abs(off) > self.half[idx]:
            return "bank", idx, off
        if self.on_ice(x, y):
            return "ice", idx, off
        return "snow", idx, off
