"""Billboard sprites: pickups and enemy demons."""
import math
import random

import pygame as pg

import graphics
from raycasting import fog_multiplier
from settings import (HALF_NUM_RAYS, DELTA_ANGLE, SCALE, SCREEN_DIST, WIDTH,
                      HALF_HEIGHT, ENEMY_TYPES, ENEMY_SIGHT_RANGE,
                      SCORE_PER_GEM, HEALTH_PACK_HEAL, PICKUP_DIST,
                      PLAYER_MAX_HEALTH)


class SpriteObject:
    """A flat image in the world that always faces the player."""

    def __init__(self, game, pos, image, scale=0.7, height_shift=0.27):
        self.game = game
        self.x, self.y = pos
        self.image = image
        self.SPRITE_SCALE = scale
        self.SPRITE_HEIGHT_SHIFT = height_shift
        self.IMAGE_WIDTH = image.get_width()
        self.IMAGE_HALF_WIDTH = self.IMAGE_WIDTH // 2
        self.IMAGE_RATIO = self.IMAGE_WIDTH / image.get_height()
        self.theta = self.screen_x = 0.0
        self.dist = self.norm_dist = 1.0
        self.sprite_half_width = 0.0

    def get_sprite_projection(self):
        proj = SCREEN_DIST / self.norm_dist * self.SPRITE_SCALE
        proj_width, proj_height = proj * self.IMAGE_RATIO, proj

        image = pg.transform.scale(self.image, (int(proj_width), int(proj_height)))
        v = fog_multiplier(self.norm_dist)
        image.fill((v, v, min(255, v + 30)), special_flags=pg.BLEND_RGB_MULT)

        height_shift = proj_height * self.SPRITE_HEIGHT_SHIFT
        pos = (self.screen_x - proj_width // 2,
               HALF_HEIGHT - proj_height // 2 + height_shift)
        self.game.renderer.objects_to_render.append((self.norm_dist, image, pos))

    def get_sprite(self):
        dx = self.x - self.game.player.x
        dy = self.y - self.game.player.y
        self.theta = math.atan2(dy, dx)

        delta = self.theta - self.game.player.angle
        if (dx > 0 and self.game.player.angle > math.pi) or (dx < 0 and dy < 0):
            delta += math.tau

        self.screen_x = (HALF_NUM_RAYS + delta / DELTA_ANGLE) * SCALE
        self.dist = math.hypot(dx, dy)
        self.norm_dist = max(0.01, self.dist * math.cos(delta))
        # half width the sprite would occupy on screen (needed for aiming)
        self.sprite_half_width = (SCREEN_DIST / self.norm_dist
                                  * self.SPRITE_SCALE * self.IMAGE_RATIO) / 2

        on_screen = -self.sprite_half_width < self.screen_x < WIDTH + self.sprite_half_width
        if on_screen and self.norm_dist > 0.35:
            self.get_sprite_projection()

    def update(self):
        self.get_sprite()


class Pickup(SpriteObject):
    """Animated collectible: 'gem' (score) or 'health'."""

    def __init__(self, game, pos, kind):
        self.kind = kind
        if kind == "gem":
            self.frames = game.assets["gem_frames"]
            scale, shift = 0.35, 0.6
        else:
            self.frames = game.assets["health_frames"]
            scale, shift = 0.4, 0.55
        super().__init__(game, pos, self.frames[0], scale, shift)
        self.frame_idx = 0
        self.anim_timer = 0
        self.collected = False

    def update(self):
        if self.collected:
            return
        self.anim_timer += self.game.delta_time
        if self.anim_timer > 140:
            self.anim_timer = 0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)
            self.image = self.frames[self.frame_idx]

        if math.hypot(self.x - self.game.player.x,
                      self.y - self.game.player.y) < PICKUP_DIST:
            if self.kind == "health" and self.game.player.health >= PLAYER_MAX_HEALTH:
                self.get_sprite()   # leave full-health players a pack for later
                return
            self.collected = True
            if self.kind == "gem":
                self.game.score += SCORE_PER_GEM
                self.game.sound.play("gem")
            else:
                self.game.player.heal(HEALTH_PACK_HEAL)
                self.game.sound.play("heal")
            return
        self.get_sprite()


class NPC(SpriteObject):
    """Colorful demon: hunts the player, bites, dies loudly.

    Three types (see settings.ENEMY_TYPES) differ in health, speed, reach and
    damage, so a room full of them does not fight as one blob.
    """

    def __init__(self, game, pos, kind=0):
        self.kind = kind % len(ENEMY_TYPES)
        self.stats = ENEMY_TYPES[self.kind]
        self.frames = graphics.make_demon_frames(self.kind)
        super().__init__(game, pos, self.frames["walk"][0],
                         scale=self.stats["scale"], height_shift=0.24)

        diff = game.difficulty
        self.max_health = self.stats["health"]
        self.health = self.max_health
        self.speed = self.stats["speed"] * diff["speed"]
        self.damage_range = self.stats["damage"]
        self.reach = self.stats["reach"]
        self.attack_cooldown = self.stats["cooldown"]

        self.alive = True
        self.dying = False
        self.state = "walk"
        self.frame_idx = 0
        self.anim_timer = 0
        self.pain_timer = 0
        self.attack_timer = 0
        self.sees_player = False

    @property
    def active(self):
        return self.alive or self.dying

    # --------------------------------------------------------------- combat
    def take_damage(self, amount):
        if not self.alive or self.dying:
            return
        self.health -= amount
        if self.health <= 0:
            self.dying = True
            self.state = "death"
            self.frame_idx = 0
            self.anim_timer = 0
            self.game.score += self.stats["score"]
            self.game.sound.play("death")
        else:
            self.state = "pain"
            self.pain_timer = 220
            self.game.sound.play("pain")

    # --------------------------------------------------------------- ai
    def _line_of_sight(self):
        """Walk the straight line to the player; any wall tile blocks it."""
        steps = int(self.dist / 0.1)
        if steps <= 0:
            return True
        sx = (self.game.player.x - self.x) / steps
        sy = (self.game.player.y - self.y) / steps
        x, y = self.x, self.y
        world_map = self.game.map.world_map
        for _ in range(steps):
            x += sx
            y += sy
            if (int(x), int(y)) in world_map:
                return False
        return True

    def _free(self, x, y):
        return (int(x), int(y)) not in self.game.map.world_map

    def _move_towards_player(self):
        angle = math.atan2(self.game.player.y - self.y, self.game.player.x - self.x)
        step = self.speed * self.game.delta_time
        dx, dy = math.cos(angle) * step, math.sin(angle) * step
        margin = 0.25
        moved = False
        if self._free(self.x + dx + math.copysign(margin, dx), self.y):
            self.x += dx
            moved = True
        if self._free(self.x, self.y + dy + math.copysign(margin, dy)):
            self.y += dy
            moved = True
        if not moved:
            # cornered: slide sideways so demons do not grind into a wall
            self.x += -dy
            self.y += dx

    def _logic(self):
        self.sees_player = self.dist < ENEMY_SIGHT_RANGE and self._line_of_sight()

        if self.pain_timer > 0:
            self.pain_timer -= self.game.delta_time
            if self.pain_timer <= 0:
                self.state = "walk"
            return

        if self.sees_player and self.dist < self.reach:
            self.state = "attack"
            self.attack_timer += self.game.delta_time
            if self.attack_timer >= self.attack_cooldown:
                self.attack_timer = 0
                low, high = self.damage_range
                damage = random.randint(low, high) * self.game.difficulty["dmg"]
                self.game.player.take_damage(max(1, int(damage)))
        elif self.sees_player:
            self.state = "walk"
            self.attack_timer = self.attack_cooldown * 0.6
            self._move_towards_player()
        else:
            self.state = "walk"

    # --------------------------------------------------------------- anim
    def _animate(self):
        frames = self.frames[self.state]
        self.anim_timer += self.game.delta_time
        interval = 120 if self.state == "death" else 160
        if self.anim_timer > interval:
            self.anim_timer = 0
            if self.state == "death":
                if self.frame_idx < len(frames) - 1:
                    self.frame_idx += 1
                else:
                    self.alive = False
            else:
                self.frame_idx = (self.frame_idx + 1) % len(frames)

        self.frame_idx = min(self.frame_idx, len(frames) - 1)
        self.image = frames[self.frame_idx]
        self.IMAGE_WIDTH = self.image.get_width()
        self.IMAGE_HALF_WIDTH = self.IMAGE_WIDTH // 2
        self.IMAGE_RATIO = self.IMAGE_WIDTH / self.image.get_height()

    def update(self):
        if not self.active:
            return
        self.get_sprite()
        if self.dying:
            self._animate()
            if not self.alive:
                self.dying = False
            return
        self._logic()
        self._animate()
