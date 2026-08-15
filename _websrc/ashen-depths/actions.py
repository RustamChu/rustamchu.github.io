"""Actions - one small command object per thing an actor can do.

Both the player's key presses and the monsters' AI produce Action objects, so
combat, movement and item use follow exactly the same path through the
engine. `perform()` returns True when the action consumed a turn.
"""
from __future__ import annotations

import tiles
from components import Impossible
from settings import MSG_BAD, MSG_GOOD, MSG_INFO, MSG_WARN, C_GOLD


class Action:
    def __init__(self, entity):
        self.entity = entity

    @property
    def engine(self):
        return self.entity.gamemap.engine

    def perform(self):
        raise NotImplementedError


class WaitAction(Action):
    def perform(self):
        return True


class MovementAction(Action):
    def __init__(self, entity, dx, dy):
        super().__init__(entity)
        self.dx, self.dy = dx, dy

    def perform(self):
        x = self.entity.x + self.dx
        y = self.entity.y + self.dy
        gamemap = self.entity.gamemap

        if not gamemap.in_bounds(x, y):
            raise Impossible("Тёмный камень не поддаётся.")
        if not gamemap.walkable(x, y):
            raise Impossible("Дорогу преграждает {}.".format(
                tiles.NAMES[gamemap.tiles[y][x]]))
        if gamemap.blocking_entity_at(x, y):
            raise Impossible("Здесь кто-то стоит.")

        self.entity.x, self.entity.y = x, y
        return True


class MeleeAction(Action):
    def __init__(self, entity, dx, dy):
        super().__init__(entity)
        self.dx, self.dy = dx, dy

    def perform(self):
        x = self.entity.x + self.dx
        y = self.entity.y + self.dy
        target = self.entity.gamemap.actor_at(x, y)
        if target is None:
            raise Impossible("Там некого атаковать.")

        damage = self.entity.fighter.power - target.fighter.defense
        by_player = self.entity is self.engine.player

        if damage > 0:
            if by_player:
                text = "Вы бьёте {} — {} урона.".format(target.name_acc, damage)
            else:
                text = "{} бьёт вас — {} урона.".format(
                    self.entity.cap_name, damage)
            self.engine.log.add(text, MSG_GOOD if by_player else MSG_BAD)
            self.engine.spawn_effect(target.x, target.y, "-" + str(damage),
                                     MSG_GOOD if by_player else MSG_BAD)
            target.fighter.take_damage(damage)
        else:
            if by_player:
                text = "Вы бьёте {}, но броня держит.".format(target.name_acc)
            else:
                text = "{} бьёт вас, но броня держит.".format(
                    self.entity.cap_name)
            self.engine.log.add(text, MSG_INFO)
        return True


class BumpAction(Action):
    """Move, or attack whatever stands in the way."""

    def __init__(self, entity, dx, dy):
        super().__init__(entity)
        self.dx, self.dy = dx, dy

    def perform(self):
        x = self.entity.x + self.dx
        y = self.entity.y + self.dy
        if self.entity.gamemap.actor_at(x, y):
            return MeleeAction(self.entity, self.dx, self.dy).perform()
        return MovementAction(self.entity, self.dx, self.dy).perform()


class PickupAction(Action):
    def perform(self):
        gamemap = self.entity.gamemap
        inventory = self.entity.inventory
        here = gamemap.items_at(self.entity.x, self.entity.y)

        if not here:
            raise Impossible("Здесь нечего подбирать.")

        item = here[0]
        if len(inventory.items) >= inventory.capacity:
            raise Impossible("Рюкзак полон.")

        gamemap.entities.remove(item)
        item.gamemap = None
        item.parent_inventory = inventory
        inventory.items.append(item)
        self.engine.log.add("Вы подбираете {}.".format(item.name_acc), MSG_INFO)

        # the Crown ends the run the moment it is lifted
        if item.template == "crown":
            item.consumable.activate(self.entity)
        return True


class DropAction(Action):
    def __init__(self, entity, item):
        super().__init__(entity)
        self.item = item

    def perform(self):
        self.entity.inventory.drop(self.item)
        return True


class UseAction(Action):
    def __init__(self, entity, item, target_xy=None):
        super().__init__(entity)
        self.item = item
        self.target_xy = target_xy

    def perform(self):
        if self.item.equippable:
            self.entity.equipment.toggle(self.item)
            return True
        if self.item.consumable:
            self.item.consumable.activate(self.entity, self.target_xy)
            return True
        raise Impossible("{} ничего не делает.".format(self.item.cap_name))


class DescendAction(Action):
    def perform(self):
        gamemap = self.entity.gamemap
        if gamemap.tiles[self.entity.y][self.entity.x] != tiles.STAIRS_DOWN:
            raise Impossible("Здесь нет лестницы вниз.")
        self.engine.descend()
        return True
