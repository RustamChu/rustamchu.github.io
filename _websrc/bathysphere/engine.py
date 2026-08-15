"""The dive itself: the submersible, resources, hazards, the goal.

Pure simulation, no pygame - the headless test drives it directly.
"""
from __future__ import annotations

import math
import random

from creature import Mother
from radio import Radio
from sonar import Sonar
from worldgen import World
from settings import (BATTERY_MAX, BATTERY_REGEN, BOUNCE, BUOYANCY,
                      COST_LAMP, COST_PING, COST_THRUST, DOCK_DIST,
                      DOCK_SPEED, DRAG, GEYSER_ACTIVE, GEYSER_DPS,
                      GEYSER_LENGTH, GEYSER_WIDTH, HULL_MAX,
                      IMPACT_DMG_SCALE, IMPACT_MIN_SPEED, MAX_SPEED,
                      OXYGEN_MAX, OXYGEN_PER_SEC, STATION_PING_EVERY, SUB_R,
                      THRUST, WORLD_H)

DIVING, DOCKED, DEAD = "diving", "docked", "dead"

BLACKBOX_LOGS = (
    "Самописец 1. «...двигатели глохли по очереди. Командир запретил сонар. "
    "Мы шли вниз наощупь, по стуку собственного сердца.»",
    "Самописец 2. «Она не нападает первой. Она отвечает. Каждый наш пинг "
    "она считала словом и подошла ближе — послушать.»",
    "Самописец 3. «Если кто-то это слышит: маяк на станции жив. Пять секунд "
    "тишины, потом голос. Идите на голос, а не на песню.»",
)


class Sub:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = SUB_R
        self.facing = 1                        # 1 right, -1 left
        self.thrusting = (0, 0)


class Engine:
    def __init__(self, seed=None, sound=None):
        self.seed = seed if seed is not None else random.randrange(1 << 24)
        self.sound = sound
        self.world = World(self.seed)
        self.sub = Sub(*self.world.start)
        self.sonar = Sonar(self.world)
        self.mother = Mother(self.world)
        self.radio = Radio()
        self.radio.trigger_event("start")

        self.hull = HULL_MAX
        self.oxygen = OXYGEN_MAX
        self.battery = BATTERY_MAX
        self.lamp_on = False
        self.state = DIVING
        self.time = 0.0
        self.depth = 0.0
        self.max_depth = 0.0
        self.boxes_found = []                  # indices, in pickup order
        self.compass = None                    # (angle, strength, kind, age)
        self.station_t = 0.0
        self.shake = 0.0
        self.heartbeat = 0.0                   # 0..1 proximity dread
        self.hydro_events = []
        self.death_cause = ""
        self._first_ping_done = False
        self._mother_called = False

    # ------------------------------------------------------------- helpers
    def _snd(self, name):
        if self.sound is not None:
            self.sound.play(name)

    @property
    def finished(self):
        return self.state != DIVING

    @property
    def loud(self):
        tx, ty = self.sub.thrusting
        return bool(tx or ty) or self.lamp_on

    # -------------------------------------------------------------- inputs
    def set_thrust(self, tx, ty):
        self.sub.thrusting = (tx, ty)
        if tx:
            self.sub.facing = 1 if tx > 0 else -1

    def toggle_lamp(self):
        self.lamp_on = not self.lamp_on
        self._snd("switch")

    def ping(self):
        if self.state != DIVING or self.battery < COST_PING:
            return False
        if not self.sonar.ping(self.sub.x, self.sub.y):
            return False
        self.battery -= COST_PING
        self.mother.hear_ping(self.sub.x, self.sub.y)
        self._snd("ping")
        if not self._first_ping_done:
            self._first_ping_done = True
            self.radio.trigger_event("first_ping")
        return True

    # -------------------------------------------------------------- update
    def update(self, dt):
        if self.state != DIVING:
            return
        self.time += dt

        self._update_sub(dt)
        self._update_resources(dt)
        self._update_sonar(dt)
        self._update_mother(dt)
        self._update_geysers(dt)
        self._update_pickups()
        self._update_station(dt)
        self._update_radio(dt)

        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 3.0)

    def _update_sub(self, dt):
        sub = self.sub
        tx, ty = sub.thrusting
        burning = (tx or ty) and self.battery > 0.5
        if burning:
            norm = math.hypot(tx, ty) or 1.0
            sub.vx += THRUST * tx / norm * dt
            sub.vy += THRUST * ty / norm * dt
        sub.vy += BUOYANCY * dt
        drag = max(0.0, 1.0 - DRAG * dt)
        sub.vx *= drag
        sub.vy *= drag
        speed = math.hypot(sub.vx, sub.vy)
        if speed > MAX_SPEED:
            sub.vx *= MAX_SPEED / speed
            sub.vy *= MAX_SPEED / speed

        self._move_collide(sub, sub.vx * dt, 0.0, axis=0)
        self._move_collide(sub, 0.0, sub.vy * dt, axis=1)

        self.depth = max(0.0, sub.y - self.world.start[1])
        self.max_depth = max(self.max_depth, self.depth)

    def _move_collide(self, sub, dx, dy, axis):
        nx, ny = sub.x + dx, sub.y + dy
        r = sub.radius
        probes = ((nx + r, ny), (nx - r, ny), (nx, ny + r), (nx, ny - r))
        if any(self.world.is_solid_at(px, py) for px, py in probes):
            speed = abs(sub.vx if axis == 0 else sub.vy)
            if speed > IMPACT_MIN_SPEED:
                dmg = (speed - IMPACT_MIN_SPEED) * IMPACT_DMG_SCALE
                self._hull_damage(dmg, "разбились о скалы")
                self.shake = min(1.0, 0.4 + dmg * 0.02)
                self._snd("impact")
            else:
                self._snd("scrape")
            if axis == 0:
                sub.vx = -sub.vx * BOUNCE
            else:
                sub.vy = -sub.vy * BOUNCE
            return
        sub.x, sub.y = nx, ny

    def _hull_damage(self, dmg, cause):
        self.hull -= dmg
        if self.hull <= HULL_MAX * 0.4:
            self.radio.trigger_event("hull_low")
        if self.hull <= 0:
            self.hull = 0
            self.state = DEAD
            self.death_cause = cause
            self._snd("dead")

    def _update_resources(self, dt):
        self.oxygen -= OXYGEN_PER_SEC * dt
        if self.oxygen <= OXYGEN_MAX * 0.25:
            self.radio.trigger_event("oxygen_low")
        if self.oxygen <= 0:
            self.oxygen = 0
            self.state = DEAD
            self.death_cause = "кончился кислород"
            self._snd("dead")
            return

        drain = 0.0
        tx, ty = self.sub.thrusting
        if tx or ty:
            drain += COST_THRUST
        if self.lamp_on:
            drain += COST_LAMP
        self.battery = max(0.0, min(BATTERY_MAX,
                                    self.battery + (BATTERY_REGEN - drain)
                                    * dt))
        if self.battery < COST_LAMP:
            self.lamp_on = False

    def _update_sonar(self, dt):
        targets = [(self.world.station[0], self.world.station[1], "station")]
        for box in self.world.blackboxes:
            if not box["found"]:
                targets.append((box["x"], box["y"], "box"))
        if self.mother.state != "dormant":
            targets.append((self.mother.x, self.mother.y, "mother"))
        self.sonar.update(dt, targets)

    def _update_mother(self, dt):
        events = []
        self.mother.update(dt, self.sub, self.loud, events)
        for kind, x, y in events:
            self._hydrophone(x, y, "mother")
            if not self._mother_called:
                self._mother_called = True
                self.radio.trigger_event("mother_first_call")

        dmg = self.mother.try_strike(self.sub)
        if dmg:
            self._hull_damage(dmg, "она была быстрее")
            self.shake = 1.0
            self._snd("strike")

        dist = math.hypot(self.mother.x - self.sub.x,
                          self.mother.y - self.sub.y)
        if self.mother.state == "dormant":
            self.heartbeat = 0.0
        else:
            self.heartbeat = max(0.0, min(1.0, 1.0 - dist / 700.0))

    def _hydrophone(self, x, y, kind):
        dx, dy = x - self.sub.x, y - self.sub.y
        dist = math.hypot(dx, dy)
        strength = max(0.0, 1.0 - dist / 2400.0)
        if strength <= 0.02:
            return
        self.compass = {"angle": math.atan2(dy, dx), "strength": strength,
                        "kind": kind, "age": 0.0}
        self.hydro_events.append((kind, strength))
        if kind == "mother":
            self._snd("call")
        elif kind == "station":
            self._snd("beacon")

    def _update_geysers(self, dt):
        for geyser in self.world.geysers:
            phase = (self.time + geyser["phase"]) % geyser["period"]
            active = phase < GEYSER_ACTIVE
            geyser["active"] = active
            if not active:
                continue
            if phase < 0.1:
                self._hydrophone(geyser["x"], geyser["y"], "geyser")
            # a hot column along the geyser's angle
            gx, gy = geyser["x"], geyser["y"]
            ax = math.cos(geyser["angle"])
            ay = math.sin(geyser["angle"])
            relx, rely = self.sub.x - gx, self.sub.y - gy
            along = relx * ax + rely * ay
            across = abs(-relx * ay + rely * ax)
            if 0 <= along <= GEYSER_LENGTH and across <= GEYSER_WIDTH:
                self._hull_damage(GEYSER_DPS * dt, "сварились в гейзере")
                self.shake = max(self.shake, 0.3)

    def _update_pickups(self):
        for box in self.world.blackboxes:
            if box["found"]:
                continue
            if math.hypot(box["x"] - self.sub.x,
                          box["y"] - self.sub.y) < 34:
                box["found"] = True
                self.boxes_found.append(box["idx"])
                self._snd("pickup")
                if len(self.boxes_found) == 1:
                    self.radio.trigger_event("first_box")

    def _update_station(self, dt):
        self.station_t += dt
        if self.station_t >= STATION_PING_EVERY:
            self.station_t = 0.0
            self._hydrophone(*self.world.station, "station")

        dist = math.hypot(self.world.station[0] - self.sub.x,
                          self.world.station[1] - self.sub.y)
        speed = math.hypot(self.sub.vx, self.sub.vy)
        if dist < DOCK_DIST and speed < DOCK_SPEED:
            self.state = DOCKED
            self.radio.trigger_event("docked")
            self._snd("dock")

    def _update_radio(self, dt):
        self.radio.trigger_depth(self.sub.y)
        if self.radio.update(dt):
            self._snd("static")
        if self.compass is not None:
            self.compass["age"] += dt
            if self.compass["age"] > 6.0:
                self.compass = None
