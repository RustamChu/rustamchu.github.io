"""First-person player: movement, collisions, health."""
import math

import pygame as pg

from settings import (PLAYER_POS, PLAYER_ANGLE, PLAYER_SPEED, PLAYER_ROT_SPEED,
                      PLAYER_SPRINT_MULT, PLAYER_RADIUS, PLAYER_MAX_HEALTH,
                      MOUSE_SENSITIVITY, MOUSE_MAX_REL)


class Player:
    def __init__(self, game):
        self.game = game
        self.x, self.y = PLAYER_POS
        self.angle = PLAYER_ANGLE
        self.health = PLAYER_MAX_HEALTH
        self.hurt_flash = 0.0
        self.sprinting = False
        self.bob = 0.0  # walk cycle phase, used by the weapon sway

    @property
    def pos(self):
        return self.x, self.y

    @property
    def map_pos(self):
        return int(self.x), int(self.y)

    # ------------------------------------------------------------- damage
    def take_damage(self, amount):
        self.health -= amount
        self.hurt_flash = 1.0
        self.game.sound.play("hurt")
        if self.health <= 0:
            self.health = 0
            self.game.game_over()

    def heal(self, amount):
        self.health = min(PLAYER_MAX_HEALTH, self.health + amount)

    # ------------------------------------------------------------- movement
    def _free(self, x, y):
        return (int(x), int(y)) not in self.game.map.world_map

    def _try_move(self, dx, dy):
        """Move on each axis separately so we slide along walls instead of
        sticking to them. The radius keeps the camera out of the geometry."""
        if dx and self._free(self.x + dx + math.copysign(PLAYER_RADIUS, dx), self.y):
            self.x += dx
        if dy and self._free(self.x, self.y + dy + math.copysign(PLAYER_RADIUS, dy)):
            self.y += dy

    def movement(self):
        sin_a, cos_a = math.sin(self.angle), math.cos(self.angle)
        dx = dy = 0.0

        keys = pg.key.get_pressed()
        self.sprinting = keys[pg.K_LSHIFT] or keys[pg.K_RSHIFT]
        speed = PLAYER_SPEED * self.game.delta_time
        if self.sprinting:
            speed *= PLAYER_SPRINT_MULT
        speed_sin, speed_cos = speed * sin_a, speed * cos_a

        if keys[pg.K_w] or keys[pg.K_UP]:
            dx += speed_cos
            dy += speed_sin
        if keys[pg.K_s] or keys[pg.K_DOWN]:
            dx -= speed_cos
            dy -= speed_sin
        if keys[pg.K_a]:
            dx += speed_sin
            dy -= speed_cos
        if keys[pg.K_d]:
            dx -= speed_sin
            dy += speed_cos

        self._try_move(dx, dy)

        if dx or dy:
            self.bob += 0.008 * self.game.delta_time * (1.5 if self.sprinting else 1.0)

        if keys[pg.K_LEFT]:
            self.angle -= PLAYER_ROT_SPEED * self.game.delta_time
        if keys[pg.K_RIGHT]:
            self.angle += PLAYER_ROT_SPEED * self.game.delta_time
        self.angle %= math.tau

    def mouse_control(self):
        """Relative mouse mode: the cursor is grabbed while playing, so we can
        just read the deltas without warping it back to the centre."""
        if not pg.event.get_grab():
            pg.mouse.get_rel()
            return
        rel = pg.mouse.get_rel()[0]
        rel = max(-MOUSE_MAX_REL, min(MOUSE_MAX_REL, rel))
        self.angle = (self.angle + rel * MOUSE_SENSITIVITY) % math.tau

    def update(self):
        self.movement()
        self.mouse_control()
        if self.hurt_flash > 0:
            self.hurt_flash = max(0.0, self.hurt_flash - 0.003 * self.game.delta_time)
