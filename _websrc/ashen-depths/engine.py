"""Game state and the turn scheduler."""
from __future__ import annotations

from entity import make
from gamemap import GameWorld
from message_log import MessageLog
from settings import (C_BONE, C_EMBER, MAX_DEPTH, MSG_SYS, MSG_WARN)

EFFECT_TTL = 420          # milliseconds a floating number stays on screen


class Engine:
    def __init__(self):
        self.log = MessageLog()
        self.effects = []
        self.player = None
        self.gamemap = None
        self.world = GameWorld(self)
        self.turn_count = 0
        self.kill_count = 0
        self.player_died = False
        self.victory = False

    # ---------------------------------------------------------------- setup
    @property
    def depth(self):
        return self.gamemap.depth if self.gamemap else 0

    def new_game(self, seed=None):
        self.log = MessageLog()
        self.effects = []
        self.turn_count = 0
        self.kill_count = 0
        self.player_died = False
        self.victory = False
        self.world = GameWorld(self, seed)

        self.player = make("player")
        self.gamemap = self.world.generate_floor()
        self.player.place(*self.gamemap.player_start, gamemap=self.gamemap)

        # a scavenged kit so the first floor is survivable
        for key in ("dagger", "leather", "potion", "potion"):
            item = make(key)
            item.parent_inventory = self.player.inventory
            self.player.inventory.items.append(item)
        for item in self.player.inventory.items:
            if item.equippable:
                self.player.equipment.slots[item.equippable.slot] = item

        self.log.add("Вы спускаетесь в засыпанный пеплом город. Где-то "
                     "внизу всё ещё горит.", C_EMBER, stack=False)
        self.log.add("Клавиша ? — управление.", MSG_SYS)
        self.gamemap.update_fov(self.player)

    def descend(self):
        self.gamemap = self.world.generate_floor()
        self.player.gamemap = None
        self.player.place(*self.gamemap.player_start, gamemap=self.gamemap)
        self.player.energy = 0
        self.effects = []
        if self.gamemap.depth >= MAX_DEPTH:
            self.log.add("Воздух становится горячим пеплом. Корона на этом "
                         "этаже.", MSG_WARN, stack=False)
        else:
            self.log.add("Вы спускаетесь на глубину {}.".format(
                self.gamemap.depth), C_BONE, stack=False)
        self.gamemap.update_fov(self.player)

    # ---------------------------------------------------------------- turns
    def advance_turn(self):
        """Called once after the player acts: everyone else gets energy."""
        self.turn_count += 1

        for actor in list(self.gamemap.actors):
            if actor is self.player or not actor.is_alive:
                continue
            actor.energy += actor.speed
            while actor.energy >= 100:
                actor.energy -= 100
                if not actor.is_alive:
                    break
                if actor.ai is not None:
                    actor.ai.perform()
                if self.player_died:
                    break
            if self.player_died:
                break

        self.gamemap.update_fov(self.player)

    # -------------------------------------------------------------- effects
    def spawn_effect(self, x, y, text, color):
        self.effects.append({"x": x, "y": y, "text": text, "color": color,
                             "ttl": EFFECT_TTL, "max_ttl": EFFECT_TTL})

    def update_effects(self, dt):
        for effect in self.effects:
            effect["ttl"] -= dt
        self.effects = [e for e in self.effects if e["ttl"] > 0]
