"""Level map.

Legend:
    1-5  -> wall with texture id
    .    -> empty floor
    E    -> enemy spawn
    H    -> health pack
    G    -> score gem
"""

MINI_MAP = [
    "111111111111111111111111",
    "1......................1",
    "1.2222..G........3333..1",
    "1.2..............3..3..1",
    "1.2...E.......E.....3..1",
    "1......................1",
    "1...44.....55....44....1",
    "1...4.......5.....4..H.1",
    "1.H.4.......5.....4....1",
    "1...44.....55....44....1",
    "1......................1",
    "1.3..3..........2...2..1",
    "1.3...E......E......2..1",
    "1.3333..H......G2222...1",
    "1..........G......E....1",
    "111111111111111111111111",
]


class Map:
    def __init__(self, game):
        self.game = game
        self.mini_map = MINI_MAP
        self.rows = len(self.mini_map)
        self.cols = len(self.mini_map[0])
        assert all(len(r) == self.cols for r in self.mini_map), "map rows must be equal length"
        self.world_map = {}
        self.enemy_spawns = []
        self.health_spawns = []
        self.gem_spawns = []
        self._parse()

    def _parse(self):
        for j, row in enumerate(self.mini_map):
            for i, char in enumerate(row):
                pos = (i + 0.5, j + 0.5)
                if char in "12345":
                    self.world_map[(i, j)] = int(char)
                elif char == "E":
                    self.enemy_spawns.append(pos)
                elif char == "H":
                    self.health_spawns.append(pos)
                elif char == "G":
                    self.gem_spawns.append(pos)

    def is_wall(self, x, y):
        return (int(x), int(y)) in self.world_map
