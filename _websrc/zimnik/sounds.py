"""Procedural audio - the project ships zero sound files.

Three continuous loops carry the drive: the engine (a saw stack whose
pitch band follows a fake gearbox), tyre scrub that swells with lateral
slip, and wind that swells with speed. Loops are baked with a whole number
of periods so they cycle without clicks. Everything else is one-shots.

Degrades to silence when there is no audio device (headless test runs).
"""
from __future__ import annotations

import math
import random
from array import array

import pygame as pg

from settings import SLIP_DRIFT, TOP_SPEED

SAMPLE_RATE = 22050
ENGINE_BANDS = 12
ENGINE_F0, ENGINE_F1 = 54.0, 150.0


def _synth(duration_ms, freq_start, freq_end=None, shape="sine", volume=0.5,
           noise=0.0, decay=1.5, attack=0.0):
    freq_end = freq_end if freq_end is not None else freq_start
    n = int(SAMPLE_RATE * duration_ms / 1000)
    buf = array("h", bytes(2 * n))
    rnd = random.Random(11)
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = freq_start + (freq_end - freq_start) * t
        phase += math.tau * freq / SAMPLE_RATE
        if shape == "square":
            sample = 1.0 if math.sin(phase) >= 0 else -1.0
        elif shape == "saw":
            sample = 2.0 * ((phase / math.tau) % 1.0) - 1.0
        else:
            sample = math.sin(phase)
        if noise:
            sample = (1 - noise) * sample + noise * rnd.uniform(-1, 1)
        env = (1.0 - t) ** decay
        if attack > 0 and t < attack:
            env *= t / attack
        buf[i] = int(30000 * volume * env * sample)
    return buf


def _silence(duration_ms):
    return array("h", bytes(2 * int(SAMPLE_RATE * duration_ms / 1000)))


def _engine_loop(freq):
    """One seamless engine band: saw + octave + sub + grit."""
    periods = max(6, int(freq * 0.16))          # ~160 ms per loop
    n = int(SAMPLE_RATE * periods / freq)
    buf = array("h", bytes(2 * n))
    rnd = random.Random(int(freq))
    for i in range(n):
        ph = (i * freq / SAMPLE_RATE) % 1.0
        ph2 = (i * freq * 2.0 / SAMPLE_RATE) % 1.0
        sub = math.sin(math.tau * i * freq * 0.5 / SAMPLE_RATE)
        sample = (0.52 * (2 * ph - 1) + 0.26 * (2 * ph2 - 1)
                  + 0.28 * sub + 0.10 * rnd.uniform(-1, 1))
        buf[i] = int(26000 * 0.5 * sample)
    return buf


def _noise_loop(seconds, lowpass=0.0, volume=0.5):
    n = int(SAMPLE_RATE * seconds)
    buf = array("h", bytes(2 * n))
    rnd = random.Random(5)
    y = 0.0
    raw = [0.0] * n
    for i in range(n):
        x = rnd.uniform(-1, 1)
        if lowpass > 0.0:
            y += lowpass * (x - y)
            raw[i] = y * (1.0 / max(0.08, lowpass))
        else:
            raw[i] = x
    fade = int(SAMPLE_RATE * 0.05)              # stitch the seam
    for i in range(fade):
        t = i / fade
        raw[i] = raw[i] * t + raw[n - fade + i] * (1 - t)
    for i in range(n):
        buf[i] = int(20000 * volume * max(-1.0, min(1.0, raw[i])))
    return buf


class SoundManager:
    def __init__(self):
        self.enabled = True
        try:
            pg.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
            pg.mixer.init(SAMPLE_RATE, -16, 1, 512)
            pg.mixer.set_num_channels(12)
        except pg.error:
            self.enabled = False
            return

        make = self._make
        self.engine_bands = []
        for b in range(ENGINE_BANDS):
            f = ENGINE_F0 * (ENGINE_F1 / ENGINE_F0) ** (b / (ENGINE_BANDS - 1))
            self.engine_bands.append(make(_engine_loop(f)))
        self.scrub = make(_noise_loop(1.3, 0.0, 0.5))
        self.wind = make(_noise_loop(1.7, 0.06, 0.6))

        self.sounds = {
            "beep": make(_synth(140, 620, 620, "square", 0.25, 0.0, 1.6)),
            "go": make(_synth(300, 930, 930, "square", 0.3, 0.0, 1.4)),
            "note": make(_synth(90, 740, 700, "sine", 0.3, 0.0, 1.8)),
            "note2": make(_synth(80, 780, 780, "sine", 0.32, 0.0, 1.6)
                          + _silence(40)
                          + _synth(110, 880, 860, "sine", 0.32, 0.0, 1.8)),
            "ice": make(_synth(240, 1420, 1180, "sine", 0.26, 0.12, 2.4)),
            "cp": make(_synth(110, 660, 660, "sine", 0.26, 0.0, 1.6)
                       + _synth(180, 880, 880, "sine", 0.26, 0.0, 1.8)),
            "thud": make(_synth(200, 84, 40, "sine", 0.6, 0.4, 1.7)),
            "scrape": make(_synth(220, 300, 210, "saw", 0.2, 0.85, 1.2)),
            "wrong": make(_synth(160, 230, 230, "square", 0.3, 0.1, 1.0)
                          + _silence(70)
                          + _synth(220, 210, 200, "square", 0.3, 0.1, 1.2)),
            "rescue": make(_synth(420, 420, 180, "saw", 0.22, 0.25, 1.1)),
            "ignition": make(_synth(650, 40, 118, "saw", 0.4, 0.5, 0.6,
                                    attack=0.35)),
            "finish": make(_synth(140, 523, 523, "square", 0.28)
                           + _synth(140, 659, 659, "square", 0.28)
                           + _synth(140, 784, 784, "square", 0.28)
                           + _synth(420, 1047, 1047, "square", 0.3)),
            "record": make(_synth(90, 1175, 1175, "sine", 0.3)
                           + _synth(90, 1319, 1319, "sine", 0.3)
                           + _synth(260, 1568, 1568, "sine", 0.32)),
        }

        self.ch_engine = pg.mixer.Channel(0)
        self.ch_scrub = pg.mixer.Channel(1)
        self.ch_wind = pg.mixer.Channel(2)
        self._band = -1
        self._loops_on = False

    @staticmethod
    def _make(buf):
        return pg.mixer.Sound(buffer=buf.tobytes())

    # ------------------------------------------------------------- one-shots
    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    # ----------------------------------------------------------------- loops
    def start_loops(self):
        if not self.enabled or self._loops_on:
            return
        self._loops_on = True
        self._band = 0
        self.ch_engine.play(self.engine_bands[0], loops=-1)
        self.ch_engine.set_volume(0.0)
        self.ch_scrub.play(self.scrub, loops=-1)
        self.ch_scrub.set_volume(0.0)
        self.ch_wind.play(self.wind, loops=-1)
        self.ch_wind.set_volume(0.0)

    def stop_loops(self):
        if not self.enabled or not self._loops_on:
            return
        self._loops_on = False
        for ch in (self.ch_engine, self.ch_scrub, self.ch_wind):
            ch.fadeout(300)

    def update_drive(self, v_forward, slip, throttle, running):
        """Called every frame with the car's state."""
        if not self.enabled or not self._loops_on:
            return
        v = abs(v_forward)
        # fake gearbox: rpm saws up three times over the speed range
        gear_pos = (v / TOP_SPEED * 3.0) % 1.0 if v > 2.0 else 0.0
        rev = min(1.0, v / TOP_SPEED * 0.35 + gear_pos * 0.6
                  + throttle * 0.12)
        band = min(ENGINE_BANDS - 1, int(rev * ENGINE_BANDS))
        if band != self._band:
            self._band = band
            vol = self.ch_engine.get_volume()
            self.ch_engine.play(self.engine_bands[band], loops=-1)
            self.ch_engine.set_volume(vol)
        target = (0.14 + 0.30 * throttle + 0.10 * min(1.0, v / 80.0)) \
            if running else 0.0
        self.ch_engine.set_volume(target)
        scrub = max(0.0, min(1.0, (slip - SLIP_DRIFT * 0.6) / 70.0))
        self.ch_scrub.set_volume(0.42 * scrub)
        self.ch_wind.set_volume(0.30 * min(1.0, v / TOP_SPEED) ** 1.6)
