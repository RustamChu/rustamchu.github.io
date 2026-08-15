"""The dungeon floor: tiles, entities, visibility and queries."""
from __future__ import annotations

import tiles
from fov import compute_fov
from pathfinding import SOFT_BLOCK_COST, astar
from settings import LIGHT_LEVELS, TORCH_RADIUS


class GameMap:
    def __init__(self, engine, width, height, depth=1):
        self.engine = engine
        self.width = width
        self.height = height
        self.depth = depth
        self.tiles = [[tiles.WALL] * width for _ in range(height)]
        self.visible = [[False] * width for _ in range(height)]
        self.explored = [[False] * width for _ in range(height)]
        self.light = [[LIGHT_LEVELS - 1] * width for _ in range(height)]
        self.entities = []
        self.downstairs = (0, 0)
        self.player_start = (0, 0)

    # ------------------------------------------------------------- queries
    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def walkable(self, x, y):
        return self.in_bounds(x, y) and tiles.walkable(self.tiles[y][x])

    def transparent(self, x, y):
        return self.in_bounds(x, y) and tiles.transparent(self.tiles[y][x])

    @property
    def actors(self):
        from entity import Actor
        return [e for e in self.entities if isinstance(e, Actor)]

    @property
    def items(self):
        from entity import Item
        return [e for e in self.entities if isinstance(e, Item)]

    def blocking_entity_at(self, x, y):
        for e in self.entities:
            if e.blocks_movement and e.x == x and e.y == y:
                return e
        return None

    def actor_at(self, x, y):
        from entity import Actor
        for e in self.entities:
            if isinstance(e, Actor) and e.is_alive and e.x == x and e.y == y:
                return e
        return None

    def items_at(self, x, y):
        from entity import Item
        return [e for e in self.entities
                if isinstance(e, Item) and e.x == x and e.y == y]

    def names_at(self, x, y):
        if not self.in_bounds(x, y) or not self.visible[y][x]:
            return ""
        found = [e.name for e in self.entities if e.x == x and e.y == y]
        if not found:
            return tiles.NAMES[self.tiles[y][x]]
        return ", ".join(found)

    # ---------------------------------------------------------- navigation
    def path_between(self, start, goal):
        """A* route that treats other actors as expensive but passable."""
        occupied = {(e.x, e.y) for e in self.entities if e.blocks_movement}

        def cost(x, y):
            return SOFT_BLOCK_COST if (x, y) in occupied else 0

        return astar(self.walkable, start, goal, extra_cost=cost)

    # ------------------------------------------------------------- vision
    def update_fov(self, player):
        for row in self.visible:
            for i in range(self.width):
                row[i] = False

        radius = TORCH_RADIUS
        radius_sq = float(radius * radius)
        visible, explored, light = self.visible, self.explored, self.light

        def blocks(x, y):
            return not self.transparent(x, y)

        def mark(x, y, dist_sq):
            if not self.in_bounds(x, y):
                return
            visible[y][x] = True
            explored[y][x] = True
            # brightest step at the feet, dimmest at the edge of the torch
            level = int((dist_sq / radius_sq) ** 0.5 * (LIGHT_LEVELS - 1) + 0.5)
            light[y][x] = min(LIGHT_LEVELS - 1, level)

        compute_fov(blocks, mark, player.x, player.y, radius)


class GameWorld:
    """Owns the current floor and builds the next one on descent.

    The descent is deliberately one-way: only the floor you stand on exists,
    which keeps memory flat and the save file tiny.
    """

    def __init__(self, engine, seed=None):
        self.engine = engine
        self.seed = seed
        self.depth = 0

    def generate_floor(self):
        import procgen
        self.depth += 1
        # a seeded world replays identically, which makes a bug reproducible
        floor_seed = None if self.seed is None else self.seed * 1000 + self.depth
        return procgen.generate_dungeon(self.engine, self.depth, floor_seed)
