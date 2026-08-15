"""All constants, balance and palette for BATHYSPHERE in one place."""

# --- screen -----------------------------------------------------------------
RES = WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "БАТИСФЕРА"

PANEL_H = 148                      # the instrument board at the bottom
VIEW_H = HEIGHT - PANEL_H

# --- world ------------------------------------------------------------------
CELL = 14                          # cave grid cell in px
GRID_W = 168                       # 168 * 14 = 2352 px wide
GRID_H = 380                       # 380 * 14 = 5320 px deep
WORLD_W = GRID_W * CELL
WORLD_H = GRID_H * CELL
SURFACE_Y = 120                    # where the dive begins
CA_STEPS = 4                       # cellular automata smoothing passes

# --- submersible ------------------------------------------------------------
SUB_R = 14
THRUST = 260.0                     # px/s^2
DRAG = 0.55                        # velocity fraction lost per second
MAX_SPEED = 190.0
BUOYANCY = -6.0                    # gentle upward drift, px/s^2
HULL_MAX = 100
IMPACT_MIN_SPEED = 90.0            # softer touches are harmless
IMPACT_DMG_SCALE = 0.22            # damage = (speed - min) * scale
BOUNCE = 0.45

OXYGEN_MAX = 100.0
OXYGEN_PER_SEC = 100.0 / 600.0     # a ten-minute dive on paper

BATTERY_MAX = 100.0
BATTERY_REGEN = 2.6                # per second, the dynamo
COST_THRUST = 3.2                  # per second while burning
COST_LAMP = 1.6                    # per second while on
COST_PING = 7.0                    # per ping

# --- sonar ------------------------------------------------------------------
PING_RADIUS = 560.0
PING_SPEED = 420.0                 # wavefront px/s
PING_COOLDOWN = 1.1
ECHO_FADE = 6.5                    # seconds an echo stays on the phosphor
BLIP_FADE = 7.5

# --- the Mother -------------------------------------------------------------
MOTHER_HOME_DEPTH = 0.45           # she sleeps below this fraction of the map
MOTHER_SPEED_ROAM = 60.0
MOTHER_SPEED_INVESTIGATE = 150.0
MOTHER_SPEED_HUNT = 225.0
MOTHER_HEAR_PING = 1500.0          # she hears an active ping this far
MOTHER_SENSE_LOUD = 300.0          # running thrusters/lamp within this = seen
MOTHER_SENSE_QUIET = 95.0          # dead silent drift: she must nearly touch
MOTHER_AGITATION_PER_PING = 34.0
MOTHER_AGITATION_DECAY = 3.0       # per second
MOTHER_HUNT_THRESHOLD = 60.0
MOTHER_HIT_DMG = 34
MOTHER_RETREAT_TIME = 4.0
MOTHER_CALL_EVERY = (3.5, 7.0)     # she sings; the hydrophone points at her
MOTHER_R = 34

# --- geysers ----------------------------------------------------------------
GEYSER_PERIOD = (5.0, 9.0)
GEYSER_ACTIVE = 2.2
GEYSER_DPS = 26.0
GEYSER_LENGTH = 150.0
GEYSER_WIDTH = 26.0

METERS_PER_PX = 0.6                # bottom of the map ~ 3.1 km down

# --- goals ------------------------------------------------------------------
BLACKBOX_COUNT = 3
DOCK_DIST = 46.0
DOCK_SPEED = 55.0
STATION_PING_EVERY = 5.0

# --- palette: phosphor + amber on the abyss ---------------------------------
C_ABYSS_TOP = (4, 10, 22)
C_ABYSS_BOTTOM = (1, 2, 6)
C_ECHO = (140, 255, 210)           # fresh sonar echo
C_ECHO_OLD = (24, 60, 80)          # what it cools down to
C_WAVE = (90, 220, 190)
C_AMBER = (255, 184, 92)           # instruments
C_AMBER_DIM = (120, 86, 48)
C_TEXT = (222, 226, 220)
C_DIM = (110, 118, 124)
C_DANGER = (255, 92, 84)
C_STATION = (255, 214, 120)
C_BOX = (150, 255, 170)
C_LAMP = (255, 236, 180)
C_SNOW = (70, 90, 110)
C_BIO = (90, 200, 235)
C_HULL_GLASS = (255, 210, 140)
