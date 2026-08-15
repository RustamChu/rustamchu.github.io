"""First-person neon blaster: hitscan shooting with muzzle flash."""
import math

import pygame as pg

from settings import (HEIGHT, HALF_WIDTH, WEAPON_DAMAGE, WEAPON_COOLDOWN_MS,
                      WEAPON_SPREAD_PX)


class Weapon:
    def __init__(self, game):
        self.game = game
        self.frames = game.assets["gun_frames"]
        self.frame_idx = 0
        self.cooldown = 0
        self.anim_timer = 0
        self.shooting = False
        self.shots = 0
        self.hits = 0
        self.hit_marker = 0     # ms left on the "you connected" crosshair

    @property
    def accuracy(self):
        return 0 if not self.shots else round(self.hits / self.shots * 100)

    def fire(self):
        if self.cooldown > 0 or self.shooting:
            return
        self.shooting = True
        self.frame_idx = 1
        self.anim_timer = 0
        self.cooldown = WEAPON_COOLDOWN_MS
        self.shots += 1
        self.game.sound.play("shot")
        if self._hitscan():
            self.hits += 1
            self.hit_marker = 180

    def _hitscan(self):
        """Damage the closest demon under the crosshair.

        The shot is blocked by geometry: anything further than the wall the
        centre ray hit is simply not there as far as the bullet is concerned.
        """
        wall_depth = self.game.raycasting.center_depth()
        target = None
        for npc in self.game.npcs:
            if not npc.alive or npc.dying:
                continue
            if npc.norm_dist <= 0.3 or npc.norm_dist >= wall_depth:
                continue
            # hitbox is a bit narrower than the drawn sprite
            tolerance = max(WEAPON_SPREAD_PX, npc.sprite_half_width * 0.55)
            if abs(npc.screen_x - HALF_WIDTH) < tolerance:
                if target is None or npc.norm_dist < target.norm_dist:
                    target = npc
        if target is None:
            return False
        target.take_damage(WEAPON_DAMAGE)
        return True

    def update(self):
        if self.cooldown > 0:
            self.cooldown -= self.game.delta_time
        if self.hit_marker > 0:
            self.hit_marker -= self.game.delta_time
        if self.shooting:
            self.anim_timer += self.game.delta_time
            if self.anim_timer > 70:
                self.anim_timer = 0
                self.frame_idx += 1
                if self.frame_idx >= len(self.frames):
                    self.frame_idx = 0
                    self.shooting = False

    def draw(self):
        img = self.frames[self.frame_idx]
        # gentle sway tied to the walk cycle
        sway_x = math.sin(self.game.player.bob) * 14
        sway_y = abs(math.cos(self.game.player.bob)) * 10
        pos = (HALF_WIDTH - img.get_width() // 2 + 60 + sway_x,
               HEIGHT - img.get_height() + sway_y)
        self.game.screen.blit(img, pos)
