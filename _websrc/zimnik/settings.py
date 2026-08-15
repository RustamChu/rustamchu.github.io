"""All constants, balance and palette for ZIMNIK in one place.

Scale: 5 px = 1 metre. Speeds are px/s internally; the dashboard converts
to km/h (v_kmh = v / PX_PER_M * 3.6).
"""

# --- screen -----------------------------------------------------------------
RES = WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "ЗИМНИК"

PANEL_H = 124                      # dashboard at the bottom
VIEW_H = HEIGHT - PANEL_H

PX_PER_M = 5.0
PHYS_DT = 1 / 120.0                # fixed physics step (determinism, ghosts)

# --- stage generation -------------------------------------------------------
STAGE_LEN_M = (2100, 2600)         # target stage length, metres
STEP = 7.0                         # centerline resample step, px
ROAD_HALF = (44.0, 60.0)           # half-width range, px
MIN_RADIUS = 60.0                  # guaranteed minimum corner radius, px
SWING = 560.0                      # lateral wander bound, px
ICE_PATCHES = (8, 13)              # count range
ICE_R = (40.0, 96.0)               # patch radius range
CHECKPOINT_EVERY_M = 400.0

# --- car --------------------------------------------------------------------
CAR_LEN = 23.0
CAR_W = 12.0
ACCEL = 118.0                      # px/s^2 at full throttle, packed snow
BRAKE = 300.0
DRAG = 0.0026                      # quadratic, caps top speed ~ 210 px/s
ROLL = 14.0                        # rolling resistance px/s^2
TOP_SPEED = 215.0                  # hard cap, px/s (~155 km/h)
REVERSE_MAX = 55.0

STEER_RATE = 2.45                  # rad/s at low speed
STEER_FALLOFF = 95.0               # the faster you go, the calmer the wheel
HANDBRAKE_YAW = 1.35               # extra rotation while the lever is up

GRIP_SNOW = 6.8                    # lateral velocity decay, 1/s
GRIP_ICE = 1.55
GRIP_HANDBRAKE = 1.05
ICE_ACCEL_SCALE = 0.55
ICE_STEER_SCALE = 0.72
SLIP_DRIFT = 42.0                  # |lateral v| that counts as drifting, px/s

# snowbanks (leaving the road)
BANK_DRAG = 2.6                    # 1/s extra drag while in the bank
BANK_PUSH = 260.0                  # px/s^2 shove back toward the road
BANK_SLOW_HIT = 0.72               # velocity kept on a hard bank hit
BANK_HIT_SPEED = 120.0             # faster than this = a thud + shake

# --- pace notes -------------------------------------------------------------
NOTE_LEAD_TIME = 2.1               # seconds of warning before a turn
NOTE_MIN_LEAD = 210.0              # px, never later than this
STRAIGHT_MIN = 400.0               # px of low curvature that count as a straight
# category by corner radius, px (rally style: 1 = tightest)
CAT_RADII = ((85.0, 1), (120.0, 2), (170.0, 3), (240.0, 4), (330.0, 5))
HAIRPIN_R = 70.0
LONG_TURN = 330.0                  # arc length that earns "длинный"

# --- run --------------------------------------------------------------------
COUNTDOWN = 3.0
WRONG_WAY_SPEED = -30.0            # ds/dt below this counts as backwards
WRONG_WAY_TIME = 1.4
RESCUE_KEY_COOLDOWN = 2.0
FINISH_MEDALS = (1.0, 1.12)        # gold <= par, silver <= par * 1.12
GHOST_RECORD_HZ = 20               # positions per second stored in the ghost

# --- palette: polar night ---------------------------------------------------
C_SNOW_LIT = (168, 186, 214)       # road under the moon
C_SNOW_DIM = (78, 92, 122)
C_BANK = (120, 136, 168)
C_NIGHT = (16, 22, 38)             # the world beyond the banks
C_NIGHT_DEEP = (8, 12, 24)
C_ICE = (38, 62, 82)               # black ice, glassy
C_ICE_CRACK = (130, 170, 190)
C_TREE_PINE = (20, 30, 42)
C_TREE_BIRCH = (188, 196, 210)
C_HEADLIGHT = (255, 238, 190)
C_TAIL = (255, 70, 60)
C_CAR_BODY = (196, 74, 58)         # rally red, mud-splattered
C_CAR_ROOF = (230, 224, 214)
C_GHOST = (140, 220, 255)
C_AURORA_A = (70, 255, 170)
C_AURORA_B = (150, 100, 235)
C_STAR = (210, 220, 240)
C_TEXT = (222, 228, 238)
C_DIM = (110, 120, 140)
C_AMBER = (255, 190, 96)           # dash backlight
C_GREEN = (150, 240, 170)          # dial glow, soviet dash green
C_DANGER = (255, 92, 84)
C_POST = (235, 130, 60)            # km posts, reflective orange
C_HUT = (255, 196, 110)            # a warm window far from home
