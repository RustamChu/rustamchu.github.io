"""All tunable constants for ASHEN DEPTHS in one place."""

# --- screen -----------------------------------------------------------------
RES = WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "ПЕПЕЛЬНЫЕ ГЛУБИНЫ"

TILE = 24
PANEL_H = 168                      # bottom HUD height
VIEW_W = 53                        # viewport size in tiles
VIEW_H = (HEIGHT - PANEL_H) // TILE
VIEW_PX_X = (WIDTH - VIEW_W * TILE) // 2
VIEW_PX_Y = 0

# --- dungeon ----------------------------------------------------------------
MAP_W, MAP_H = 72, 42
MAX_DEPTH = 8                      # the Ember Crown waits here
BSP_DEPTH = 4                      # recursion depth of the room splitter
ROOM_MIN = 6                       # minimum room side (including walls)

# --- vision -----------------------------------------------------------------
TORCH_RADIUS = 8
LIGHT_LEVELS = 6                   # pre-baked brightness steps for lit tiles

# --- turns ------------------------------------------------------------------
BASE_SPEED = 100                   # energy gained per turn; 100 = one action

# --- player -----------------------------------------------------------------
PLAYER_HP = 30
PLAYER_DEFENSE = 1
PLAYER_POWER = 4
INVENTORY_SIZE = 20
LEVEL_UP_BASE = 40
LEVEL_UP_FACTOR = 25
LEVEL_UP_HP = 12
LEVEL_UP_POWER = 1
LEVEL_UP_DEFENSE = 1

# --- how many monsters / items may appear, by depth -------------------------
# (depth, amount) - the value used is the last entry whose depth <= floor
MAX_MONSTERS_BY_DEPTH = [(1, 2), (3, 3), (5, 5), (7, 6)]
MAX_ITEMS_BY_DEPTH = [(1, 1), (2, 2), (4, 3)]

# --- palette ----------------------------------------------------------------
C_BG = (9, 8, 12)
C_PANEL = (18, 16, 22)
C_PANEL_EDGE = (58, 48, 44)

C_WALL = (96, 80, 68)
C_WALL_EDGE = (146, 118, 90)
C_FLOOR = (58, 50, 46)
C_FLOOR_DOT = (82, 72, 64)
C_PILLAR = (122, 108, 96)
C_RUBBLE = (78, 68, 60)
C_STAIRS = (240, 190, 90)

C_MEMORY = (34, 38, 54)            # tint of remembered, unlit tiles

C_EMBER = (255, 150, 60)
C_BONE = (232, 224, 205)
C_BLOOD = (206, 62, 62)
C_POISON = (132, 200, 90)
C_ARCANE = (146, 146, 255)
C_GOLD = (240, 200, 90)
C_ASH = (150, 146, 140)
C_DIM = (96, 92, 96)

# --- message colors ---------------------------------------------------------
MSG_INFO = C_ASH
MSG_GOOD = C_POISON
MSG_BAD = C_BLOOD
MSG_WARN = C_GOLD
MSG_MAGIC = C_ARCANE
MSG_SYS = (120, 160, 200)
