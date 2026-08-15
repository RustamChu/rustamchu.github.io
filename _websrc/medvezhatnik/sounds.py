"""Procedural audio - zero sound files, same synth family as the rest
of the series. Night burglary wants QUIET sounds: soft steps, dial
clicks, a guard's questioning hum - and two loud ones you never want
to hear."""
from __future__ import annotations

import math
import random
from array import array

import pygame as pg

SAMPLE_RATE = 22050


def _synth(ms, f0, f1=None, shape="sine", vol=0.5, noise=0.0, decay=1.5,
           attack=0.0):
    f1 = f1 if f1 is not None else f0
    n = int(SAMPLE_RATE * ms / 1000)
    buf = array("h", bytes(2 * n))
    rnd = random.Random(11)
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f0 + (f1 - f0) * t
        phase += math.tau * freq / SAMPLE_RATE
        if shape == "square":
            s = 1.0 if math.sin(phase) >= 0 else -1.0
        elif shape == "saw":
            s = 2.0 * ((phase / math.tau) % 1.0) - 1.0
        else:
            s = math.sin(phase)
        if noise:
            s = (1 - noise) * s + noise * rnd.uniform(-1, 1)
        env = (1.0 - t) ** decay
        if attack > 0 and t < attack:
            env *= t / attack
        buf[i] = int(30000 * vol * env * s)
    return buf


def _silence(ms):
    return array("h", bytes(2 * int(SAMPLE_RATE * ms / 1000)))


class SoundManager:
    def __init__(self):
        self.enabled = True
        try:
            pg.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
            pg.mixer.init(SAMPLE_RATE, -16, 1, 512)
            mk = self._make
            self.sounds = {
                "step": mk(_synth(45, 90, 60, "sine", 0.10, 0.6, 2.2)),
                "step_run": mk(_synth(60, 110, 70, "sine", 0.2, 0.6, 2.0)),
                "hm": mk(_synth(160, 190, 240, "sine", 0.16, 0.05, 1.4)),
                "shout": mk(_synth(240, 320, 210, "saw", 0.4, 0.2, 1.2)),
                "switch": mk(_synth(30, 1800, 1200, "square", 0.14, 0.1,
                                    3.0)),
                "safe_open": mk(_synth(180, 240, 160, "sine", 0.2, 0.3,
                                       1.6)),
                "tick": mk(_synth(18, 2400, 2200, "square", 0.08, 0.0,
                                  3.0)),
                "click_good": mk(_synth(60, 1400, 1500, "sine", 0.22, 0.0,
                                        2.0)
                                 + _synth(90, 1900, 1900, "sine", 0.18,
                                          0.0, 2.2)),
                "click_bad": mk(_synth(120, 300, 180, "saw", 0.2, 0.4,
                                       1.6)),
                "loot": mk(_synth(90, 660, 660, "sine", 0.2)
                           + _synth(90, 880, 880, "sine", 0.2)
                           + _synth(180, 1320, 1320, "sine", 0.22)),
                "escape": mk(_synth(120, 523, 523, "triangle", 0.2)
                             + _synth(120, 659, 659, "triangle", 0.2)
                             + _synth(300, 784, 784, "triangle", 0.22)),
                "caught": mk(_synth(700, 220, 60, "saw", 0.4, 0.25, 1.0)),
                "alarm": mk(_synth(150, 700, 900, "square", 0.2)
                            + _synth(150, 900, 700, "square", 0.2)),
            }
        except pg.error:
            self.enabled = False

    @staticmethod
    def _make(buf):
        return pg.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()
