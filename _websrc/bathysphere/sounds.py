"""Tiny procedural synthesizer - the project ships zero audio files.

Every effect is math written straight into a sample buffer at start-up.
The palette here is deliberately narrow and wet: low sines, slow vibrato,
filtered noise. Nothing bright lives at this depth except the sonar.

Degrades to silence when there is no audio device (headless test runs).
"""
from __future__ import annotations

import math
import random
from array import array

import pygame as pg

SAMPLE_RATE = 22050


def _synth(duration_ms, freq_start, freq_end=None, shape="sine", volume=0.5,
           noise=0.0, decay=1.5, attack=0.0, vibrato=(0.0, 0.0)):
    """One tone: linear frequency sweep, optional vibrato and noise blend.

    `attack` is the fraction of the sound spent ramping up (kills clicks on
    long swells), `vibrato` is (rate_hz, depth_hz).
    """
    freq_end = freq_end if freq_end is not None else freq_start
    n = int(SAMPLE_RATE * duration_ms / 1000)
    buf = array("h", bytes(2 * n))
    rnd = random.Random(11)
    vib_rate, vib_depth = vibrato
    phase = 0.0
    for i in range(n):
        t = i / n
        sec = i / SAMPLE_RATE
        freq = freq_start + (freq_end - freq_start) * t
        if vib_depth:
            freq += vib_depth * math.sin(math.tau * vib_rate * sec)
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


def _overlay(*bufs):
    """Mix several buffers into one (clipped), length of the longest."""
    out = array("h", bytes(2 * max(len(b) for b in bufs)))
    for buf in bufs:
        for i, v in enumerate(buf):
            out[i] = max(-32000, min(32000, out[i] + v))
    return out


class SoundManager:
    def __init__(self):
        self.enabled = True
        try:
            pg.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
            pg.mixer.init(SAMPLE_RATE, -16, 1, 512)
            self.sounds = {
                # controls
                "switch": self._make(_synth(28, 2100, 1500, "square", 0.16,
                                            0.1, 3.0)),
                "ui": self._make(_synth(30, 840, 760, "sine", 0.18, 0.0, 2.5)),
                # the voice of the instrument: an active ping
                "ping": self._make(_overlay(
                    _synth(650, 1280, 1180, "sine", 0.34, 0.0, 2.8),
                    _synth(650, 640, 590, "sine", 0.12, 0.0, 2.4))),
                # hull
                "impact": self._make(_overlay(
                    _synth(220, 88, 42, "sine", 0.55, 0.35, 1.7),
                    _synth(120, 400, 180, "saw", 0.18, 0.6, 2.2))),
                "scrape": self._make(_synth(260, 320, 210, "saw", 0.2,
                                            0.85, 1.1)),
                "creak": self._make(_synth(1300, 58, 47, "sine", 0.3, 0.22,
                                           0.9, attack=0.3,
                                           vibrato=(2.2, 7.0))),
                "thump": self._make(_synth(110, 62, 38, "sine", 0.5,
                                           0.08, 2.6)),
                # Her
                "call": self._make(_overlay(
                    _synth(1900, 150, 66, "sine", 0.34, 0.04, 1.0,
                           attack=0.22, vibrato=(4.6, 11.0)),
                    _synth(1900, 226, 100, "sine", 0.12, 0.04, 1.2,
                           attack=0.3, vibrato=(4.6, 14.0)))),
                "strike": self._make(_overlay(
                    _synth(520, 230, 46, "saw", 0.5, 0.4, 1.3),
                    _synth(220, 90, 40, "sine", 0.55, 0.3, 1.6))),
                # goals and signals
                "beacon": self._make(
                    _synth(160, 624, 618, "sine", 0.3, 0.0, 1.8)
                    + _silence(90)
                    + _synth(260, 468, 462, "sine", 0.3, 0.0, 1.8)),
                "pickup": self._make(
                    _synth(90, 520, 520, "sine", 0.3, 0.0, 1.6)
                    + _synth(90, 660, 660, "sine", 0.3, 0.0, 1.6)
                    + _synth(200, 880, 880, "sine", 0.3, 0.0, 1.8)),
                "dock": self._make(
                    _synth(500, 300, 120, "saw", 0.16, 0.85, 1.0)
                    + _synth(140, 523, 523, "sine", 0.3, 0.0, 1.5)
                    + _synth(140, 659, 659, "sine", 0.3, 0.0, 1.5)
                    + _synth(420, 784, 784, "sine", 0.32, 0.0, 1.6)),
                # radio and the end
                "static": self._make(_synth(320, 900, 500, "sine", 0.16,
                                            0.95, 1.1)),
                "dead": self._make(_overlay(
                    _synth(2100, 108, 27, "saw", 0.4, 0.16, 0.9),
                    _synth(2100, 54, 22, "sine", 0.4, 0.05, 0.8))),
            }
        except pg.error:
            self.enabled = False

    @staticmethod
    def _make(buf):
        return pg.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()
