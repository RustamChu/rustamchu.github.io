#!/usr/bin/env python3
"""NEON DOOM - a colorful retro raycasting shooter.

Author: RustamChu
License: MIT
"""
import sys

import pygame as pg

import graphics
from map import Map
from player import Player
from raycasting import RayCasting
from renderer import Renderer
from sounds import SoundManager
from sprites import NPC, Pickup
from weapon import Weapon
from settings import RES, FPS, DIFFICULTIES

MENU, PLAY, DEAD, WIN = "menu", "play", "dead", "win"


class Game:
    def __init__(self):
        pg.init()
        self.sound = SoundManager()
        pg.display.set_caption("NEON DOOM")
        self.screen = pg.display.set_mode(RES)
        self.clock = pg.time.Clock()
        self.delta_time = 16
        self.state = MENU
        self.difficulty_idx = 1

        # heavy procedural assets are generated once and shared by everything
        self.assets = {
            "gem_frames": graphics.make_gem_frames(),
            "health_frames": graphics.make_health_frames(),
            "gun_frames": graphics.make_gun_frames(),
        }

        self.map = Map(self)
        self.player = Player(self)
        self.renderer = Renderer(self)
        self.raycasting = RayCasting(self)
        self.raycasting.textures = self.renderer.wall_textures
        self.new_game()

    @property
    def difficulty(self):
        return DIFFICULTIES[self.difficulty_idx]

    # ------------------------------------------------------------- lifecycle
    def new_game(self):
        self.score = 0
        self.map = Map(self)
        self.player = Player(self)
        self.npcs = [NPC(self, pos, kind=i)
                     for i, pos in enumerate(self.map.enemy_spawns)]
        self.pickups = ([Pickup(self, pos, "gem") for pos in self.map.gem_spawns]
                        + [Pickup(self, pos, "health") for pos in self.map.health_spawns])
        self.weapon = Weapon(self)
        self.renderer.build_minimap()
        self.start_ticks = pg.time.get_ticks()
        self.finish_ticks = None

    def elapsed_seconds(self):
        end = self.finish_ticks if self.finish_ticks is not None else pg.time.get_ticks()
        return (end - self.start_ticks) / 1000

    def _grab_mouse(self, grab):
        """Relative mouse mode while playing, normal cursor in the menus."""
        pg.mouse.set_visible(not grab)
        try:
            pg.event.set_grab(grab)
        except pg.error:
            pass
        pg.mouse.get_rel()

    def game_over(self):
        self.state = DEAD
        self.finish_ticks = pg.time.get_ticks()
        self._grab_mouse(False)

    def victory(self):
        self.state = WIN
        self.finish_ticks = pg.time.get_ticks()
        self.sound.play("win")
        self._grab_mouse(False)

    def to_menu(self):
        self.state = MENU
        self._grab_mouse(False)

    def start_round(self):
        self.new_game()
        self.state = PLAY
        self._grab_mouse(True)

    # ------------------------------------------------------------- input
    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()

            elif event.type == pg.KEYDOWN:
                self._on_key(event.key)

            elif (event.type == pg.MOUSEBUTTONDOWN and event.button == 1):
                if self.state == PLAY:
                    self.weapon.fire()
                elif self.state == MENU:
                    self.start_round()

    def _on_key(self, key):
        if key == pg.K_ESCAPE:
            if self.state == MENU:
                self.quit()
            else:
                self.to_menu()
        elif key in (pg.K_RETURN, pg.K_KP_ENTER) and self.state == MENU:
            self.start_round()
        elif key == pg.K_r and self.state in (DEAD, WIN):
            self.start_round()
        elif key == pg.K_SPACE and self.state == PLAY:
            self.weapon.fire()
        elif self.state == MENU and key in (pg.K_1, pg.K_2, pg.K_3):
            self.difficulty_idx = {pg.K_1: 0, pg.K_2: 1, pg.K_3: 2}[key]

    @staticmethod
    def quit():
        pg.quit()
        sys.exit()

    # ------------------------------------------------------------- loop
    def update(self):
        if self.state in (DEAD, WIN):
            # keep drawing the frozen scene behind the result overlay
            self.raycasting.update()
            for pickup in self.pickups:
                if not pickup.collected:
                    pickup.get_sprite()
            for npc in self.npcs:
                if npc.active:
                    npc.get_sprite()
            return
        if self.state != PLAY:
            return

        self.player.update()
        self.raycasting.update()
        for pickup in self.pickups:
            pickup.update()
        for npc in self.npcs:
            npc.update()
        self.weapon.update()

        if self.state == PLAY and not any(npc.active for npc in self.npcs):
            self.victory()

    def draw(self):
        if self.state == MENU:
            self.renderer.draw_menu()
        else:
            self.renderer.draw_background()
            self.renderer.draw_world()
            self.weapon.draw()
            self.renderer.draw_hud()
            if self.state == DEAD:
                self.renderer.draw_game_over()
            elif self.state == WIN:
                self.renderer.draw_victory()
        pg.display.flip()

    def step(self):
        """One frame of the game, kept separate so tests can drive it."""
        self.handle_events()
        self.update()
        self.draw()
        # cap the step so a stutter cannot teleport the player through a wall
        self.delta_time = min(self.clock.tick(FPS), 50)

    def run(self):
        while True:
            self.step()


if __name__ == "__main__":
    Game().run()
