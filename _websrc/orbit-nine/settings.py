"""All constants and balance for ORBITA-9 in one place."""

# --- screen -----------------------------------------------------------------
RES = WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "ОРБИТА-9"

# --- physics ----------------------------------------------------------------
PHYS_DT = 1.0 / 120            # fixed step; solver and game share it exactly
G = 7500.0                     # gravity constant (mass = radius squared)
ACCEL_CAP = 2600.0             # per-body acceleration clamp near the surface
BALL_R = 6
MAX_POWER = 560.0              # launch speed at a full drag, px/s
DRAG_FULL = 220.0              # drag length that gives full power, px
FLIGHT_MAX = 12.0              # seconds before a flying ball freezes in place
STICK_SPEED = 80.0             # slower impacts land, faster ones bounce
RESTITUTION = 0.62
TANGENT_FRICTION = 0.82
OOB_MARGIN = 70                # how far past the screen edge is "lost in space"
GOAL_R = 15
BLACKHOLE_HORIZON = 1.9        # event horizon = radius * this
WORMHOLE_COOLDOWN = 0.35

# --- course -----------------------------------------------------------------
COURSE_HOLES = 9
PAR = 3                        # every hole; the solver still proves an ace

# --- solver (level generator proves every hole is solvable) ----------------
SOLVER_ANGLE_STEP = 4          # degrees
SOLVER_POWERS = (0.5, 0.75, 1.0)
SOLVER_MAX_T = 6.0
CURVE_MIN_DEVIATION = 70.0     # px a solution must bend, or the hole is dull

PREVIEW_T = 2.4                # seconds of trajectory prediction while aiming

# --- palette ----------------------------------------------------------------
C_BG_TOP = (8, 9, 20)
C_BG_BOTTOM = (14, 10, 30)
C_STAR = (210, 215, 235)
C_TEXT = (230, 232, 244)
C_DIM = (118, 122, 148)
C_ACCENT = (110, 220, 255)
C_GOOD = (130, 235, 150)
C_BAD = (245, 100, 110)
C_GOLD = (250, 205, 100)
C_BALL = (245, 248, 255)
C_TRAIL = (110, 220, 255)
C_PREVIEW = (255, 255, 255)
C_HINT = (250, 205, 100)

PLANET_SCHEMES = (
    ((70, 190, 220), (20, 60, 90)),      # ice teal
    ((240, 150, 90), (110, 40, 30)),     # dusty orange
    ((190, 120, 240), (70, 30, 110)),    # violet gas
    ((120, 220, 140), (25, 80, 55)),     # toxic green
    ((240, 200, 110), (120, 70, 30)),    # sand
)
C_PULSAR = (200, 130, 255)
C_BLACKHOLE = (255, 120, 80)
C_WORMHOLE = (90, 230, 200)
C_ASTEROID = (150, 150, 165)
