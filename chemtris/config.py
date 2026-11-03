"""Screen layout, colours and gameplay tuning in one place."""

TITLE = "ChemTris"
WIDTH, HEIGHT = 1280, 720
FPS = 60

# Playing field
COLS, ROWS = 10, 16
CELL = 40
FIELD_X = (WIDTH - COLS * CELL) // 2
FIELD_Y = 48
FIELD_W, FIELD_H = COLS * CELL, ROWS * CELL

# Side panels
LEFT_PANEL = (24, 24, 380, 672)
RIGHT_PANEL = (FIELD_X + FIELD_W + 24, 24, WIDTH - (FIELD_X + FIELD_W + 24) - 24, 672)

# Falling speed. A piece falls the whole field in FALL_TIME_START seconds on level 1,
# and that time drops by FALL_TIME_STEP every level: 1.25 s every 5 levels.
FALL_TIME_START = 16.0
FALL_TIME_STEP = 0.25
FALL_TIME_MIN = 1.0
LOCK_DELAY = 0.5
LOCK_RESETS = 15
SOFT_DROP_INTERVAL = 0.035

# Hint tiers: how much help the target card gives
FULL_HINT_LEVELS = 17      # levels 1-17 introduce every molecule with a full diagram
NAME_HINT_LEVELS = 29      # levels 18-29 show the picture and the name; after that, picture only

# Colours
BG_TOP = (14, 22, 52)
BG_BOTTOM = (6, 10, 24)
PANEL = (20, 30, 64)
PANEL_EDGE = (80, 120, 210)
FIELD_BG = (8, 14, 34)
GRID_LINE = (28, 42, 82)
TEXT = (236, 242, 255)
TEXT_DIM = (150, 168, 210)
ACCENT = (110, 220, 255)
GOLD = (255, 214, 90)
GOOD = (110, 240, 150)
BAD = (255, 96, 96)
RUBBLE = (96, 96, 106)

# Atom colours follow the CPK convention chemists use
ELEMENT_COLORS = {
    "H": (238, 240, 246),
    "O": (232, 62, 52),
    "C": (72, 74, 84),
    "N": (66, 108, 236),
    "Na": (164, 96, 226),
    "Cl": (70, 206, 92),
    "S": (244, 212, 56),
}
ELEMENT_TEXT = {"H": (40, 44, 60), "S": (70, 56, 10)}
ELEMENTS = tuple(ELEMENT_COLORS)
