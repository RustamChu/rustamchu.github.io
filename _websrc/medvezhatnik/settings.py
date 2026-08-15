"""All constants, balance and palette for MEDVEZHATNIK in one place."""

# --- screen -----------------------------------------------------------------
RES = WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "МЕДВЕЖАТНИК"

# --- mansion ----------------------------------------------------------------
WORLD_W, WORLD_H = 1700, 1060
WALL = 14                          # wall thickness, px
DOOR_W = 56
MISSION_COUNT = 5
MISSION_SEEDS = (101, 202, 303, 404, 505)

# --- the thief --------------------------------------------------------------
P_R = 11
SPEED_SNEAK = 62.0
SPEED_WALK = 112.0
SPEED_RUN = 178.0
NOISE_RUN = 190.0                  # heard this far
NOISE_WALK = 70.0
INTERACT_R = 34.0

# --- guards -----------------------------------------------------------------
G_R = 12
G_SPEED_PATROL = 68.0
G_SPEED_SUSPICIOUS = 100.0
G_SPEED_ALERT = 158.0
FOV_ANGLE = 1.15                   # radians, full cone ~66°
FOV_RANGE = 235.0
FOV_RANGE_DARK = 118.0             # in an unlit room you must be close
SPOT_TIME = 0.55                   # continuous sight before the shout
SUS_GLIMPSE = 0.12                 # a flicker is enough to go look
SUS_WAIT = 2.6                     # how long he stares at the empty spot
ALERT_TIME = 11.0                  # chase memory after losing you
CATCH_R = 20.0
TURN_RATE = 3.4                    # rad/s, guards turn, not teleport

# --- light ------------------------------------------------------------------
LAMP_R = 190.0                     # a ceiling lamp lights this circle
SWITCH_RELIGHT = 12.0              # guard flips it back after seconds

# --- the safe ---------------------------------------------------------------
SAFE_RINGS = 3
SAFE_SPEED = (2.6, 3.4, 4.4)       # dial speed per ring, rad/s
SAFE_WINDOW = (0.52, 0.42, 0.34)   # release window per ring, rad

# --- solver (the ghost proof) ----------------------------------------------
SOLVE_CELL = 24
SOLVE_DT = 0.25
SOLVE_TMAX = 200.0
SAFE_DWELL = 3.0                   # seconds the ghost must stand at the safe

# --- palette: parquet, brass and night --------------------------------------
C_FLOOR_A = (54, 42, 34)
C_FLOOR_B = (48, 37, 30)
C_CARPET = (70, 32, 36)
C_WALL = (28, 24, 22)
C_WALL_EDGE = (74, 62, 50)
C_DOOR = (96, 72, 44)
C_FURN = (38, 30, 26)
C_FURN_EDGE = (88, 70, 52)
C_LAMP_LIGHT = (255, 214, 150)
C_DARKNESS = (46, 48, 66)          # multiply ambient
C_GUARD = (52, 60, 84)
C_GUARD_ALERT = (150, 60, 54)
C_CONE = (255, 226, 160)
C_CONE_ALERT = (255, 110, 90)
C_THIEF = (24, 26, 30)
C_SAFE = (110, 116, 126)
C_EXIT = (120, 200, 140)
C_TEXT = (222, 216, 200)
C_DIM = (128, 120, 108)
C_GOLD = (255, 205, 100)
C_DANGER = (255, 92, 84)
C_NOISE = (140, 190, 235)
