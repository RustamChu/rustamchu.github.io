"""Tile ids and their properties.

Tiles are plain ints stored in a 2-D list, which keeps the map cheap to copy
and trivial to serialise into a save file.
"""

WALL = 0
FLOOR = 1
STAIRS_DOWN = 2
PILLAR = 3
RUBBLE = 4

# walkable / transparent lookups, indexed by tile id
WALKABLE = (False, True, True, False, True)
TRANSPARENT = (False, True, True, False, True)

NAMES = ("каменная стена", "пол", "лестница вниз", "колонна", "щебень")


def walkable(tile):
    return WALKABLE[tile]


def transparent(tile):
    return TRANSPARENT[tile]
