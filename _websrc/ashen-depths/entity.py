"""Entities and the template registry used to build them.

Every kind of monster or item is described once, in TEMPLATES. Saving an
entity therefore only needs its template key plus whatever changed during
play (position, hp, inventory), which keeps the save format small and
readable.

Russian needs two forms of every name: the nominative for "the skeleton
dies" and the accusative for "you hit the skeleton", so each template
carries both.
"""
from __future__ import annotations

import math

import components as comp
from settings import (BASE_SPEED, C_ARCANE, C_BONE, C_GOLD, C_POISON,
                      C_STAIRS, INVENTORY_SIZE, PLAYER_DEFENSE, PLAYER_HP,
                      PLAYER_POWER)

RENDER_CORPSE = 1
RENDER_ITEM = 2
RENDER_ACTOR = 3


class Entity:
    def __init__(self, template, char, color, name, name_acc=None,
                 blocks_movement=False, render_order=RENDER_ITEM, x=0, y=0):
        self.template = template
        self.char = char
        self.color = color
        self.name = name                       # именительный падеж
        self.name_acc = name_acc or name       # винительный падеж
        self.blocks_movement = blocks_movement
        self.render_order = render_order
        self.x = x
        self.y = y
        self.gamemap = None

    @property
    def cap_name(self):
        """Nominative with a capital letter, for the start of a sentence."""
        return self.name[:1].upper() + self.name[1:]

    # ------------------------------------------------------------- geometry
    def distance_to(self, other):
        return self.distance_to_xy(other.x, other.y)

    def distance_to_xy(self, x, y):
        return math.hypot(x - self.x, y - self.y)

    def place(self, x, y, gamemap):
        self.x, self.y = x, y
        if self.gamemap is not None and self in self.gamemap.entities:
            self.gamemap.entities.remove(self)
        self.gamemap = gamemap
        gamemap.entities.append(self)
        return self

    # --------------------------------------------------------------- saving
    def state(self):
        return {"template": self.template, "x": self.x, "y": self.y}

    def restore(self, data):
        self.x, self.y = data["x"], data["y"]


class Actor(Entity):
    def __init__(self, template, char, color, name, name_acc, fighter, ai_cls,
                 speed=BASE_SPEED, xp_reward=0, inventory=None,
                 equipment=None, level=None):
        super().__init__(template, char, color, name, name_acc,
                         blocks_movement=True, render_order=RENDER_ACTOR)
        self.fighter = fighter
        self.fighter.entity = self
        self.ai = ai_cls() if ai_cls else None
        if self.ai:
            self.ai.entity = self
        self.speed = speed
        self.energy = 0
        self.xp_reward = xp_reward
        self.inventory = inventory
        self.equipment = equipment
        self.level = level
        self.dead = False
        for component in (inventory, equipment, level):
            if component is not None:
                component.entity = self

    @property
    def is_alive(self):
        return not self.dead

    # --------------------------------------------------------------- saving
    def state(self):
        data = super().state()
        data["hp"] = self.fighter.hp
        data["max_hp"] = self.fighter.max_hp
        data["power"] = self.fighter.base_power
        data["defense"] = self.fighter.base_defense
        data["energy"] = self.energy
        data["dead"] = not self.is_alive
        data["name"] = self.name
        data["name_acc"] = self.name_acc
        data["char"] = self.char
        data["color"] = list(self.color)
        if isinstance(self.ai, comp.ConfusedEnemy):
            data["confused"] = self.ai.turns_remaining
        if self.level is not None:
            data["level"] = self.level.current_level
            data["xp"] = self.level.current_xp
        if self.inventory is not None:
            data["inventory"] = [item.state() for item in self.inventory.items]
            data["equipped_templates"] = [
                item.template for item in self.equipment.slots.values() if item
            ] if self.equipment else []
        return data

    def restore(self, data):
        super().restore(data)
        self.fighter.max_hp = data["max_hp"]
        self.fighter._hp = data["hp"]
        self.fighter.base_power = data["power"]
        self.fighter.base_defense = data["defense"]
        self.energy = data.get("energy", 0)
        self.name = data.get("name", self.name)
        self.name_acc = data.get("name_acc", self.name_acc)
        self.char = data.get("char", self.char)
        self.color = tuple(data.get("color", self.color))
        if data.get("dead"):
            self.dead = True
            self.ai = None
            self.blocks_movement = False
            self.render_order = RENDER_CORPSE
        elif "confused" in data:
            self.ai = comp.ConfusedEnemy(comp.HostileEnemy(), data["confused"])
            self.ai.entity = self
            self.ai.previous_ai.entity = self
        if self.level is not None and "level" in data:
            self.level.current_level = data["level"]
            self.level.current_xp = data["xp"]
        if self.inventory is not None:
            self.inventory.items = []
            for item_data in data.get("inventory", []):
                item = make(item_data["template"])
                item.restore(item_data)
                item.parent_inventory = self.inventory
                self.inventory.items.append(item)
            for template in data.get("equipped_templates", []):
                for item in self.inventory.items:
                    if item.template == template and item.equippable:
                        self.equipment.slots[item.equippable.slot] = item
                        break


class Item(Entity):
    def __init__(self, template, char, color, name, name_acc=None,
                 consumable=None, equippable=None):
        super().__init__(template, char, color, name, name_acc,
                         render_order=RENDER_ITEM)
        self.consumable = consumable
        self.equippable = equippable
        self.parent_inventory = None
        for component in (consumable, equippable):
            if component is not None:
                component.entity = self


# ===========================================================================
#  Templates
# ===========================================================================
def _player():
    return Actor(
        "player", "@", C_BONE, "вы", "вас",
        fighter=comp.Fighter(PLAYER_HP, PLAYER_DEFENSE, PLAYER_POWER),
        ai_cls=None,                # the player is driven by the input handler
        speed=BASE_SPEED,
        inventory=comp.Inventory(INVENTORY_SIZE),
        equipment=comp.Equipment(),
        level=comp.Level(),
    )


def _monster(key, char, color, name, name_acc, hp, defense, power, xp,
             speed=BASE_SPEED):
    def factory():
        return Actor(key, char, color, name, name_acc,
                     fighter=comp.Fighter(hp, defense, power),
                     ai_cls=comp.HostileEnemy, speed=speed, xp_reward=xp)
    return factory


def _item(key, char, color, name, name_acc=None, consumable=None,
          equippable=None):
    def factory():
        return Item(key, char, color, name, name_acc,
                    consumable=consumable() if consumable else None,
                    equippable=equippable() if equippable else None)
    return factory


TEMPLATES = {
    "player": _player,

    # --- монстры ----------------------------------------------------------
    "rat": _monster("rat", "r", (150, 120, 96),
                    "чумная крыса", "чумную крысу",
                    hp=6, defense=0, power=3, xp=8, speed=130),
    "ghoul": _monster("ghoul", "g", (150, 190, 140),
                      "упырь", "упыря",
                      hp=12, defense=0, power=4, xp=20),
    "skeleton": _monster("skeleton", "s", (218, 214, 200),
                         "скелет", "скелета",
                         hp=16, defense=1, power=5, xp=35),
    "cultist": _monster("cultist", "c", (198, 96, 150),
                        "пепельный культист", "пепельного культиста",
                        hp=20, defense=1, power=6, xp=55),
    "wraith": _monster("wraith", "w", (140, 170, 230),
                       "призрак", "призрака",
                       hp=18, defense=2, power=7, xp=80, speed=140),
    "ogre": _monster("ogre", "O", (196, 132, 70),
                     "тлеющий огр", "тлеющего огра",
                     hp=40, defense=3, power=10, xp=160, speed=70),
    "warden": _monster("warden", "W", (255, 120, 60),
                       "страж углей", "стража углей",
                       hp=60, defense=4, power=13, xp=320),

    # --- расходники -------------------------------------------------------
    "potion": _item("potion", "!", C_POISON, "целебный отвар",
                    consumable=lambda: comp.HealingConsumable(12)),
    "scroll_lightning": _item("scroll_lightning", "~", C_ARCANE,
                              "свиток молнии",
                              consumable=lambda: comp.LightningConsumable(22, 5)),
    "scroll_fireball": _item("scroll_fireball", "~", C_GOLD,
                             "свиток огненного шара",
                             consumable=lambda: comp.FireballConsumable(14, 3)),
    "scroll_confusion": _item("scroll_confusion", "~", (200, 140, 255),
                              "свиток смятения",
                              consumable=lambda: comp.ConfusionConsumable(8)),

    # --- снаряжение -------------------------------------------------------
    "dagger": _item("dagger", "/", (190, 190, 200), "ржавый кинжал",
                    equippable=lambda: comp.Equippable("weapon", power_bonus=2)),
    "sword": _item("sword", "/", (220, 220, 235), "железный меч",
                   equippable=lambda: comp.Equippable("weapon", power_bonus=4)),
    "axe": _item("axe", "/", (240, 190, 120), "тлеющий топор",
                 equippable=lambda: comp.Equippable("weapon", power_bonus=7)),
    "leather": _item("leather", "[", (170, 130, 90), "кожаный доспех",
                     equippable=lambda: comp.Equippable("armor", defense_bonus=1)),
    "chain": _item("chain", "[", (190, 195, 210), "кольчуга", "кольчугу",
                   equippable=lambda: comp.Equippable("armor", defense_bonus=3)),
    "plate": _item("plate", "[", (225, 230, 245), "латы из пепельной стали",
                   equippable=lambda: comp.Equippable("armor", defense_bonus=5)),

    # --- цель спуска ------------------------------------------------------
    "crown": _item("crown", "$", C_STAIRS, "Пепельная корона",
                   "Пепельную корону",
                   consumable=lambda: comp.CrownConsumable()),
}


def make(template_key):
    """Build a fresh entity from its template key."""
    return TEMPLATES[template_key]()
