"""One run down the stage: countdown, timing, notes, ghost, finish.

The engine owns no pixels. It advances the car with a fixed physics step,
feeds the co-driver's notes to the HUD at the right distance-to-corner,
records the run for a future ghost and replays the best one against you.
Par time comes from the AI driver, who drives the identical physics before
you ever see the stage.
"""
from __future__ import annotations

import math

import ai_driver
from physics import place_on_track, step
from settings import (COUNTDOWN, FINISH_MEDALS, GHOST_RECORD_HZ,
                      NOTE_LEAD_TIME, NOTE_MIN_LEAD, PHYS_DT, PX_PER_M,
                      WRONG_WAY_SPEED, WRONG_WAY_TIME)
from track import Track

COUNT, RUN, FIN = "countdown", "run", "finished"

MEDAL_NONE, MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD = (
    "", "бронза", "серебро", "золото")


def seed_code(seed):
    """Human-friendly stage code, base36."""
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    n = seed % (36 ** 5)
    out = ""
    for _ in range(5):
        out = digits[n % 36] + out
        n //= 36
    return out


class Engine:
    def __init__(self, seed, sound=None, ghost=None, best_ms=None):
        self.seed = seed
        self.code = seed_code(seed)
        self.sound = sound
        self.track = Track(seed)

        ai_line = []
        self.par, ok = ai_driver.solve(self.track, record=ai_line)
        if not ok:                              # never on tested seeds
            self.par = self.track.total / 100.0

        # ghost: the player's best run if there is one, else the co-driver
        if ghost:
            self.ghost_line = ghost
            self.ghost_is_ai = False
        else:
            self.ghost_line = ai_line
            self.ghost_is_ai = True
        self.best_ms = best_ms

        self.car = place_on_track(self.track, self.track.start_s)
        self.state = COUNT
        self.count_t = COUNTDOWN
        self.time = 0.0
        self.medal = MEDAL_NONE
        self.is_best = False

        self.recording = []
        self._rec_acc = 0.0
        self._phys_acc = 0.0
        self._count_last = 4

        self.note_ptr = 0
        self.note_current = None
        self.note_next = None
        self.note_hold = 0.0

        self.s_car = self.track.start_s
        self._s_window = []
        self.wrong_way = False
        self.rescues = 0
        self.rescue_cd = 0.0
        self.shake = 0.0
        self.ghost_pos = None
        self._ghost_idx_hint = 0
        self.delta_m = None
        self.cp_passed = 0

    # ------------------------------------------------------------- helpers
    def _snd(self, name):
        if self.sound is not None:
            self.sound.play(name)

    @property
    def progress(self):
        span = self.track.finish_s - self.track.start_s
        return max(0.0, min(1.0, (self.s_car - self.track.start_s) / span))

    def format_time(self, t=None):
        t = self.time if t is None else t
        return "%d:%05.2f" % (int(t // 60), t % 60)

    # -------------------------------------------------------------- rescue
    def rescue(self):
        if self.state != RUN or self.rescue_cd > 0.0:
            return False
        s = min(self.s_car, self.track.finish_s - 60.0)
        self.car = place_on_track(self.track, s)
        self.rescues += 1
        self.rescue_cd = 2.0
        self._snd("rescue")
        return True

    # -------------------------------------------------------------- update
    def update(self, dt, throttle=0.0, brake=0.0, steer=0.0,
               handbrake=False):
        if self.state == FIN:
            return
        if self.rescue_cd > 0.0:
            self.rescue_cd -= dt
        if self.shake > 0.0:
            self.shake = max(0.0, self.shake - dt * 2.6)

        if self.state == COUNT:
            self.count_t -= dt
            remaining = max(0, int(math.ceil(self.count_t)))
            if remaining != self._count_last:
                self._count_last = remaining
                self._snd("go" if remaining == 0 else "beep")
            if self.count_t <= 0.0:
                self.state = RUN
            throttle = brake = steer = 0.0

        self._phys_acc += dt
        while self._phys_acc >= PHYS_DT:
            self._phys_acc -= PHYS_DT
            events = step(self.car, self.track, throttle, brake, steer,
                          handbrake, PHYS_DT)
            for kind, speed in events:
                if kind == "bank_hit":
                    self.shake = min(1.0, 0.35 + speed / 400.0)
                    self._snd("thud")
                else:
                    self._snd("scrape")
            if self.state == RUN:
                self.time += PHYS_DT
                self._record()

        self.s_car = self.track.s[self.car.idx]
        if self.state == RUN:
            self._update_notes()
            self._update_wrong_way(dt)
            self._update_ghost()
            self._update_checkpoints()
            if self.s_car >= self.track.finish_s:
                self._finish()

    def _record(self):
        self._rec_acc += PHYS_DT
        if self._rec_acc >= 1.0 / GHOST_RECORD_HZ:
            self._rec_acc -= 1.0 / GHOST_RECORD_HZ
            self.recording.append((round(self.car.x, 1),
                                   round(self.car.y, 1),
                                   round(self.car.heading, 3)))

    # ---------------------------------------------------------------- notes
    def _update_notes(self):
        lead = max(NOTE_MIN_LEAD, self.car.speed * NOTE_LEAD_TIME)
        notes = self.track.notes
        while (self.note_ptr < len(notes)
               and notes[self.note_ptr]["s"] <= self.s_car + lead):
            note = notes[self.note_ptr]
            self.note_ptr += 1
            if note["end"] < self.s_car:        # already behind us
                continue
            self.note_current = note
            self.note_next = notes[self.note_ptr] \
                if self.note_ptr < len(notes) else None
            self.note_hold = 3.2
            if note["kind"] == "turn" and note["cat"] <= 2:
                self._snd("note2")
            elif note["kind"] == "ice":
                self._snd("ice")
            else:
                self._snd("note")
        if self.note_hold > 0.0:
            self.note_hold -= PHYS_DT * 2       # called per update, roughly
            if self.note_hold <= 0.0 and self.note_current is not None \
                    and self.note_current["end"] < self.s_car:
                self.note_current = None

    def _update_wrong_way(self, dt):
        self._s_window.append((self.time, self.s_car))
        while self._s_window and self.time - self._s_window[0][0] > 1.0:
            self._s_window.pop(0)
        if len(self._s_window) > 3:
            dt_span = self._s_window[-1][0] - self._s_window[0][0]
            ds = self._s_window[-1][1] - self._s_window[0][1]
            if dt_span > 0.4:
                backwards = ds / dt_span < WRONG_WAY_SPEED
                if backwards and not self.wrong_way \
                        and self.time > WRONG_WAY_TIME:
                    self._snd("wrong")
                self.wrong_way = backwards

    def _update_ghost(self):
        if not self.ghost_line:
            self.ghost_pos = None
            return
        idx = int(self.time * GHOST_RECORD_HZ)
        if idx >= len(self.ghost_line):
            self.ghost_pos = self.ghost_line[-1]
            self.delta_m = None
            return
        self.ghost_pos = self.ghost_line[idx]
        hint = self._ghost_idx_hint
        gi = self.track.locate(self.ghost_pos[0], self.ghost_pos[1], hint)
        self._ghost_idx_hint = gi
        ghost_s = self.track.s[gi]
        self.delta_m = (self.s_car - ghost_s) / PX_PER_M

    def _update_checkpoints(self):
        passed = sum(1 for s in self.track.checkpoints if s <= self.s_car)
        if passed > self.cp_passed:
            self.cp_passed = passed
            self._snd("cp")

    # --------------------------------------------------------------- finish
    def _finish(self):
        self.state = FIN
        gold, silver = FINISH_MEDALS
        if self.time <= self.par * gold:
            self.medal = MEDAL_GOLD
        elif self.time <= self.par * silver:
            self.medal = MEDAL_SILVER
        else:
            self.medal = MEDAL_BRONZE
        ms = int(self.time * 1000)
        self.is_best = self.best_ms is None or ms < self.best_ms
        self._snd("finish")

    @property
    def finished(self):
        return self.state == FIN
