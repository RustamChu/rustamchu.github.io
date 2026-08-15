"""Classic grid raycaster (the same technique the 90s shooters used) with
textured walls and distance fog."""
import math

import pygame as pg

from settings import (NUM_RAYS, HALF_FOV, DELTA_ANGLE, MAX_DEPTH, SCREEN_DIST,
                      SCALE, TEXTURE_SIZE, HALF_TEXTURE_SIZE, HEIGHT,
                      HALF_HEIGHT, FOG_START, FOG_FULL, FOG_MIN, SHADE_LEVELS)

_FOG_RANGE = FOG_FULL - FOG_START


def fog_multiplier(depth):
    """Brightness 0..255 for a wall or sprite at the given distance."""
    t = (depth - FOG_START) / _FOG_RANGE
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return int(255 - (255 - FOG_MIN) * t)


def shade_index(depth):
    """Which pre-baked brightness step a wall column at `depth` should use."""
    t = (depth - FOG_START) / _FOG_RANGE
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    idx = int(t * SHADE_LEVELS)
    return SHADE_LEVELS - 1 if idx >= SHADE_LEVELS else idx


class RayCasting:
    def __init__(self, game):
        self.game = game
        self.ray_casting_result = []
        self.textures = None  # {id: [brightest..darkest]}, set by Game

    # ------------------------------------------------------------- rendering
    def get_objects_to_render(self):
        objects = self.game.renderer.objects_to_render
        append = objects.append
        scale_col = pg.transform.scale
        textures = self.textures
        max_shade = SHADE_LEVELS - 1
        column_span = TEXTURE_SIZE - SCALE

        for ray, (depth, proj_height, texture, offset) in enumerate(self.ray_casting_result):
            # inline shade lookup - this runs once per screen column
            t = (depth - FOG_START) / _FOG_RANGE
            shade = 0 if t < 0.0 else (max_shade if t >= 1.0 else int(t * SHADE_LEVELS))
            tex = textures[texture][shade]
            column_x = int(offset * column_span)

            if proj_height < HEIGHT:
                column = tex.subsurface(column_x, 0, SCALE, TEXTURE_SIZE)
                column = scale_col(column, (SCALE, proj_height))
                pos = (ray * SCALE, HALF_HEIGHT - proj_height // 2)
            else:
                # wall is taller than the screen: sample only the visible slice
                tex_height = TEXTURE_SIZE * HEIGHT / proj_height
                column = tex.subsurface(
                    column_x, int(HALF_TEXTURE_SIZE - tex_height // 2),
                    SCALE, int(tex_height))
                column = scale_col(column, (SCALE, HEIGHT))
                pos = (ray * SCALE, 0)

            append((depth, column, pos))

    # ------------------------------------------------------------- the cast
    def ray_cast(self):
        result = []
        append = result.append
        ox, oy = self.game.player.pos
        x_map, y_map = self.game.player.map_pos
        world_map = self.game.map.world_map
        player_angle = self.game.player.angle
        sin, cos = math.sin, math.cos

        texture_vert = texture_hor = 1
        ray_angle = player_angle - HALF_FOV + 0.0001
        for _ in range(NUM_RAYS):
            sin_a = sin(ray_angle)
            cos_a = cos(ray_angle)

            # --- horizontal grid lines
            y_hor, dy = (y_map + 1, 1) if sin_a > 0 else (y_map - 1e-6, -1)
            depth_hor = (y_hor - oy) / sin_a
            x_hor = ox + depth_hor * cos_a
            delta_depth = dy / sin_a
            dx = delta_depth * cos_a
            for _ in range(MAX_DEPTH):
                tile_hor = int(x_hor), int(y_hor)
                if tile_hor in world_map:
                    texture_hor = world_map[tile_hor]
                    break
                x_hor += dx
                y_hor += dy
                depth_hor += delta_depth

            # --- vertical grid lines
            x_vert, dx = (x_map + 1, 1) if cos_a > 0 else (x_map - 1e-6, -1)
            depth_vert = (x_vert - ox) / cos_a
            y_vert = oy + depth_vert * sin_a
            delta_depth = dx / cos_a
            dy = delta_depth * sin_a
            for _ in range(MAX_DEPTH):
                tile_vert = int(x_vert), int(y_vert)
                if tile_vert in world_map:
                    texture_vert = world_map[tile_vert]
                    break
                x_vert += dx
                y_vert += dy
                depth_vert += delta_depth

            # --- closest hit wins
            if depth_vert < depth_hor:
                depth, texture = depth_vert, texture_vert
                y_vert %= 1
                offset = y_vert if cos_a > 0 else (1 - y_vert)
            else:
                depth, texture = depth_hor, texture_hor
                x_hor %= 1
                offset = (1 - x_hor) if sin_a > 0 else x_hor

            # remove the fisheye distortion
            depth *= cos(player_angle - ray_angle)
            proj_height = int(SCREEN_DIST / (depth + 0.0001))

            append((depth, proj_height, texture, offset))
            ray_angle += DELTA_ANGLE

        self.ray_casting_result = result

    def center_depth(self):
        """Distance to the wall straight ahead - used for shooting."""
        if not self.ray_casting_result:
            return MAX_DEPTH
        return self.ray_casting_result[NUM_RAYS // 2][0]

    def update(self):
        self.ray_cast()
        self.get_objects_to_render()
