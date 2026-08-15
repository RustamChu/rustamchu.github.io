"""Entity components: stats, AI, inventory, equipment, consumables.

Behaviour lives in small components that are bolted onto an entity instead of
in a deep class hierarchy, so a "confused giant rat holding a sword" needs no
new class - just a different set of parts.
"""
from __future__ import annotations

import random

from settings import (C_ARCANE, C_BLOOD, C_BONE, C_GOLD, C_POISON, MSG_BAD,
                      MSG_GOOD, MSG_INFO, MSG_MAGIC, MSG_WARN, LEVEL_UP_BASE,
                      LEVEL_UP_FACTOR)


class Impossible(Exception):
    """Raised when an action cannot be performed; shown to the player."""


# --------------------------------------------------------------------------- base
class Component:
    entity = None

    @property
    def engine(self):
        """Reach the engine through the owner - items in a pack have no map."""
        entity = self.entity
        gamemap = getattr(entity, "gamemap", None)
        if gamemap is None:
            inventory = getattr(entity, "parent_inventory", None)
            if inventory is not None:
                gamemap = inventory.entity.gamemap
        if gamemap is None:
            raise RuntimeError("{} is not attached to a map".format(entity))
        return gamemap.engine


# --------------------------------------------------------------------------- fighter
class Fighter(Component):
    def __init__(self, hp, base_defense, base_power):
        self.max_hp = hp
        self._hp = hp
        self.base_defense = base_defense
        self.base_power = base_power

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value):
        self._hp = max(0, min(value, self.max_hp))
        if self._hp == 0 and not self.entity.dead:
            self.die()

    @property
    def defense(self):
        bonus = self.entity.equipment.defense_bonus if self.entity.equipment else 0
        return self.base_defense + bonus

    @property
    def power(self):
        bonus = self.entity.equipment.power_bonus if self.entity.equipment else 0
        return self.base_power + bonus

    def heal(self, amount):
        if self.hp == self.max_hp:
            return 0
        healed = min(amount, self.max_hp - self.hp)
        self.hp += healed
        return healed

    def take_damage(self, amount):
        self.hp -= amount

    def die(self):
        engine = self.engine
        self.entity.dead = True
        if engine.player is self.entity:
            engine.log.add("Вы умираете во тьме.", MSG_BAD, stack=False)
            engine.player_died = True
        else:
            engine.log.add("{} погибает.".format(self.entity.cap_name), MSG_WARN)
            engine.kill_count += 1
            if engine.player.level:
                engine.player.level.add_xp(self.entity.xp_reward)

        self.entity.char = "%"
        self.entity.color = C_BLOOD
        self.entity.blocks_movement = False
        self.entity.ai = None
        self.entity.name = "останки: {}".format(self.entity.name)
        self.entity.name_acc = self.entity.name
        self.entity.render_order = 1
        engine.spawn_effect(self.entity.x, self.entity.y, "*", C_BLOOD)


# --------------------------------------------------------------------------- progression
class Level(Component):
    def __init__(self):
        self.current_level = 1
        self.current_xp = 0

    @property
    def xp_to_next_level(self):
        return LEVEL_UP_BASE + self.current_level * LEVEL_UP_FACTOR

    @property
    def requires_level_up(self):
        return self.current_xp >= self.xp_to_next_level

    def add_xp(self, xp):
        if xp <= 0:
            return
        self.current_xp += xp
        self.engine.log.add("Вы получаете {} опыта.".format(xp), MSG_INFO)
        if self.requires_level_up:
            self.engine.log.add(
                "Вы становитесь сильнее — уровень {}!".format(self.current_level + 1),
                C_GOLD, stack=False)

    def increase_level(self):
        self.current_xp -= self.xp_to_next_level
        self.current_level += 1


# --------------------------------------------------------------------------- inventory
class Inventory(Component):
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = []

    def drop(self, item):
        self.items.remove(item)
        if self.entity.equipment and self.entity.equipment.is_equipped(item):
            self.entity.equipment.unequip(item, quiet=True)
        item.place(self.entity.x, self.entity.y, self.entity.gamemap)
        self.engine.log.add("Вы бросаете {}.".format(item.name_acc), MSG_INFO)


# --------------------------------------------------------------------------- equipment
class Equippable(Component):
    def __init__(self, slot, power_bonus=0, defense_bonus=0):
        self.slot = slot              # "weapon" or "armor"
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus


class Equipment(Component):
    def __init__(self):
        self.slots = {"weapon": None, "armor": None}

    @property
    def power_bonus(self):
        return sum(i.equippable.power_bonus for i in self.slots.values() if i)

    @property
    def defense_bonus(self):
        return sum(i.equippable.defense_bonus for i in self.slots.values() if i)

    def is_equipped(self, item):
        return item in self.slots.values()

    def unequip(self, item, quiet=False):
        slot = item.equippable.slot
        self.slots[slot] = None
        if not quiet:
            verb = "убираете" if slot == "weapon" else "снимаете"
            self.engine.log.add("Вы {} {}.".format(verb, item.name_acc),
                                MSG_INFO)

    def equip(self, item):
        slot = item.equippable.slot
        current = self.slots[slot]
        if current is item:
            self.unequip(item)
            return
        if current is not None:
            self.unequip(current, quiet=True)
        self.slots[slot] = item
        verb = "берёте в руки" if slot == "weapon" else "надеваете"
        self.engine.log.add("Вы {} {}.".format(verb, item.name_acc), MSG_GOOD)

    def toggle(self, item):
        self.equip(item)


# --------------------------------------------------------------------------- ai
class BaseAI(Component):
    def perform(self):
        raise NotImplementedError


class HostileEnemy(BaseAI):
    """Walks toward the player with A* and attacks when adjacent."""

    def __init__(self):
        self.path = []

    def perform(self):
        from actions import MeleeAction, MovementAction, WaitAction

        entity = self.entity
        target = self.engine.player
        dx = target.x - entity.x
        dy = target.y - entity.y
        distance = max(abs(dx), abs(dy))

        if entity.gamemap.visible[entity.y][entity.x]:
            if distance <= 1:
                return MeleeAction(entity, dx, dy).perform()
            self.path = entity.gamemap.path_between((entity.x, entity.y),
                                                    (target.x, target.y))

        if self.path:
            nx, ny = self.path.pop(0)
            if entity.gamemap.walkable(nx, ny) and not \
                    entity.gamemap.blocking_entity_at(nx, ny):
                return MovementAction(entity, nx - entity.x, ny - entity.y).perform()
            self.path = []

        return WaitAction(entity).perform()


class ConfusedEnemy(BaseAI):
    """Staggers in random directions, then hands control back."""

    def __init__(self, previous_ai, turns):
        self.previous_ai = previous_ai
        self.turns_remaining = turns

    def perform(self):
        from actions import BumpAction

        entity = self.entity
        if self.turns_remaining <= 0:
            self.engine.log.add(
                "{} приходит в себя.".format(entity.cap_name), MSG_INFO)
            entity.ai = self.previous_ai
            return

        self.turns_remaining -= 1
        dx, dy = random.choice([(-1, -1), (0, -1), (1, -1), (-1, 0),
                                (1, 0), (-1, 1), (0, 1), (1, 1)])
        try:
            BumpAction(entity, dx, dy).perform()
        except Impossible:
            pass


# --------------------------------------------------------------------------- consumables
class Consumable(Component):
    #: set by subclasses that need the player to pick a spot first
    targeting = None
    targeting_radius = 0

    def activate(self, consumer, target_xy=None):
        raise NotImplementedError

    def consume(self):
        inventory = self.entity.parent_inventory
        if inventory is not None and self.entity in inventory.items:
            inventory.items.remove(self.entity)


class HealingConsumable(Consumable):
    def __init__(self, amount):
        self.amount = amount

    def activate(self, consumer, target_xy=None):
        healed = consumer.fighter.heal(self.amount)
        if healed <= 0:
            raise Impossible("Раны уже затянулись.")
        self.engine.log.add(
            "Вы выпиваете {} и восстанавливаете {} ОЗ.".format(
                self.entity.name_acc, healed), MSG_GOOD)
        self.engine.spawn_effect(consumer.x, consumer.y, "+" + str(healed), C_POISON)
        self.consume()


class LightningConsumable(Consumable):
    def __init__(self, damage, max_range):
        self.damage = damage
        self.max_range = max_range

    def activate(self, consumer, target_xy=None):
        target = None
        closest = self.max_range + 1.0
        for actor in self.engine.gamemap.actors:
            if actor is consumer or not actor.is_alive:
                continue
            if not self.engine.gamemap.visible[actor.y][actor.x]:
                continue
            distance = consumer.distance_to(actor)
            if distance < closest:
                target, closest = actor, distance

        if target is None:
            raise Impossible("Поблизости нет подходящей цели.")

        self.engine.log.add(
            "Молния бьёт в {} — {} урона!".format(
                target.name_acc, self.damage), MSG_MAGIC, stack=False)
        self.engine.spawn_effect(target.x, target.y, "-" + str(self.damage), C_ARCANE)
        target.fighter.take_damage(self.damage)
        self.consume()


class FireballConsumable(Consumable):
    targeting = "area"

    def __init__(self, damage, radius):
        self.damage = damage
        self.targeting_radius = radius

    def activate(self, consumer, target_xy=None):
        if target_xy is None:
            raise Impossible("Нужно выбрать цель.")
        x, y = target_xy
        if not self.engine.gamemap.visible[y][x]:
            raise Impossible("Туда не видно.")

        self.engine.log.add("Свиток вспыхивает пламенем!", C_GOLD, stack=False)
        hit_anything = False
        for actor in list(self.engine.gamemap.actors):
            if not actor.is_alive:
                continue
            if actor.distance_to_xy(x, y) <= self.targeting_radius:
                self.engine.log.add(
                    "Пламя охватывает {} — {} урона.".format(
                        actor.name_acc, self.damage), MSG_BAD)
                self.engine.spawn_effect(actor.x, actor.y,
                                         "-" + str(self.damage), C_GOLD)
                actor.fighter.take_damage(self.damage)
                hit_anything = True

        if not hit_anything:
            self.engine.log.add("Пламя находит только камень.", MSG_INFO)
        self.consume()


class ConfusionConsumable(Consumable):
    targeting = "single"

    def __init__(self, turns):
        self.turns = turns

    def activate(self, consumer, target_xy=None):
        if target_xy is None:
            raise Impossible("Нужно выбрать цель.")
        x, y = target_xy
        if not self.engine.gamemap.visible[y][x]:
            raise Impossible("Туда не видно.")

        target = self.engine.gamemap.actor_at(x, y)
        if target is None:
            raise Impossible("Там никого нет.")
        if target is consumer:
            raise Impossible("Свой рассудок вам ещё пригодится.")

        self.engine.log.add(
            "{} теряет рассудок.".format(target.cap_name), MSG_MAGIC)
        target.ai = ConfusedEnemy(target.ai, self.turns)
        target.ai.entity = target
        self.engine.spawn_effect(target.x, target.y, "?", C_ARCANE)
        self.consume()


class CrownConsumable(Consumable):
    """Picking this up ends the run - it is the whole point of the descent."""

    def activate(self, consumer, target_xy=None):
        self.engine.log.add("Пепельная корона пылает в ваших руках.", C_GOLD,
                            stack=False)
        self.engine.victory = True
