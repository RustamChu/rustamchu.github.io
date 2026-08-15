"""Tiny procedural synthesizer - all SFX are generated in code,
so the repo ships zero binary audio assets."""
import math
import random
from array import array

import pygame as pg

SAMPLE_RATE = 44100


def _synth(duration_ms, freq_start, freq_end=None, shape="square",
           volume=0.5, noise=0.0, decay=True):
    freq_end = freq_end or freq_start
    n = int(SAMPLE_RATE * duration_ms / 1000)
    buf = array("h", [0] * n)
    rnd = random.Random(1)
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = freq_start + (freq_end - freq_start) * t
        phase += math.tau * freq / SAMPLE_RATE
        if shape == "square":
            sample = 1.0 if math.sin(phase) >= 0 else -1.0
        elif shape == "saw":
            sample = 2.0 * ((phase / math.tau) % 1.0) - 1.0
        else:  # sine
            sample = math.sin(phase)
        if noise:
            sample = (1 - noise) * sample + noise * rnd.uniform(-1, 1)
        env = (1.0 - t) ** 1.5 if decay else 1.0
        buf[i] = int(32000 * volume * env * sample)
    return buf


class SoundManager:
    """Plays synthesized SFX; degrades to silence if no audio device."""

    def __init__(self):
        self.enabled = True
        try:
            pg.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
            pg.mixer.init(SAMPLE_RATE, -16, 1, 512)
        except pg.error:
            self.enabled = False
            return
        try:
            self.sounds = {
                "shot": self._make(_synth(140, 850, 130, "square", 0.5, noise=0.45)),
                "pain": self._make(_synth(110, 260, 180, "square", 0.35)),
                "death": self._make(_synth(450, 420, 60, "saw", 0.45, noise=0.2)),
                "hurt": self._make(_synth(180, 120, 60, "sine", 0.6, noise=0.3)),
                "gem": self._make(_synth(90, 880, 1320, "sine", 0.4, decay=False)
                                  + _synth(90, 1320, 1760, "sine", 0.35)),
                "heal": self._make(_synth(110, 523, 523, "sine", 0.4)
                                   + _synth(140, 784, 784, "sine", 0.4)),
                "win": self._make(_synth(150, 523, 523, "square", 0.35)
                                  + _synth(150, 659, 659, "square", 0.35)
                                  + _synth(300, 784, 784, "square", 0.35)),
            }
        except pg.error:
            self.enabled = False

    @staticmethod
    def _make(buf):
        return pg.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()
