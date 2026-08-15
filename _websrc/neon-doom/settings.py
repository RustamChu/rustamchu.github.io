"""Global game settings for NEON DOOM."""
import math

# --- screen ---
RES = WIDTH, HEIGHT = 1280, 720
HALF_WIDTH = WIDTH // 2
HALF_HEIGHT = HEIGHT // 2
FPS = 60

# --- player ---
PLAYER_POS = 1.5, 1.5
PLAYER_ANGLE = 0.0
PLAYER_SPEED = 0.004
PLAYER_SPRINT_MULT = 1.6
PLAYER_ROT_SPEED = 0.0025
PLAYER_RADIUS = 0.22
PLAYER_MAX_HEALTH = 100

# --- mouse ---
MOUSE_SENSITIVITY = 0.0015
MOUSE_MAX_REL = 60

# --- raycasting ---
FOV = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = WIDTH // 2
HALF_NUM_RAYS = NUM_RAYS // 2
DELTA_ANGLE = FOV / NUM_RAYS
MAX_DEPTH = 22

SCREEN_DIST = HALF_WIDTH / math.tan(HALF_FOV)
SCALE = WIDTH // NUM_RAYS

# --- textures ---
TEXTURE_SIZE = 256
HALF_TEXTURE_SIZE = TEXTURE_SIZE // 2

# --- fog / shading ---
FOG_START = 1.0        # distance where walls start to darken
FOG_FULL = 16.0        # distance of (almost) full darkness
FOG_MIN = 30           # minimum brightness multiplier (0..255)
SHADE_LEVELS = 12      # pre-baked brightness steps (see graphics.make_shaded_set)

# --- weapon ---
WEAPON_DAMAGE = 45
WEAPON_COOLDOWN_MS = 350
WEAPON_SPREAD_PX = 22   # minimum aim tolerance in screen pixels

# --- enemies ---
# Three distinct demons so fights do not feel identical.
ENEMY_TYPES = (
    {"name": "brute",   "health": 130, "speed": 0.0014, "damage": (10, 16),
     "score": 130, "scale": 0.82, "reach": 1.45, "cooldown": 1000},
    {"name": "stalker", "health": 70,  "speed": 0.0027, "damage": (5, 9),
     "score": 110, "scale": 0.62, "reach": 1.20, "cooldown": 650},
    {"name": "imp",     "health": 95,  "speed": 0.0019, "damage": (7, 13),
     "score": 100, "scale": 0.72, "reach": 1.30, "cooldown": 850},
)
ENEMY_SIGHT_RANGE = 13.0

# --- difficulty (chosen in the menu with 1 / 2 / 3) ---
DIFFICULTIES = (
    {"name": "ROOKIE", "dmg": 0.6, "speed": 0.8},
    {"name": "NORMAL", "dmg": 1.0, "speed": 1.0},
    {"name": "NIGHTMARE", "dmg": 1.5, "speed": 1.3},
)

# --- pickups ---
SCORE_PER_GEM = 25
HEALTH_PACK_HEAL = 35
PICKUP_DIST = 0.6

# --- colors (neon palette) ---
C_BG_TOP = (16, 5, 46)
C_BG_HORIZON = (255, 64, 160)
C_FLOOR_NEAR = (20, 60, 70)
C_FLOOR_FAR = (10, 8, 30)
C_UI_PINK = (255, 80, 180)
C_UI_CYAN = (70, 240, 255)
C_UI_YELLOW = (255, 220, 80)
C_UI_RED = (255, 70, 90)
C_UI_GREEN = (110, 255, 140)
C_UI_DARK = (12, 8, 28)
