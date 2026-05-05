

import pygame

# ─── Window & Grid ────────────────────────────────────────────────────────────
GRID_SIZE   = 26          # 26×26 tile grid
TILE_SIZE   = 28          # pixels per tile
GRID_PIXEL  = GRID_SIZE * TILE_SIZE   # 728
HUD_WIDTH   = 180
SCREEN_W    = GRID_PIXEL + HUD_WIDTH  # 908
SCREEN_H    = GRID_PIXEL              # 728
FPS         = 30

# ─── Terrain IDs ──────────────────────────────────────────────────────────────
EMPTY  = 0
BRICK  = 1
STEEL  = 2
WATER  = 3
FOREST = 4
EAGLE  = 5

# ─── A* Movement Costs ────────────────────────────────────────────────────────
ASTAR_COST = {
    EMPTY:  1,
    FOREST: 1,
    BRICK:  3,
    STEEL:  float('inf'),
    WATER:  float('inf'),
    EAGLE:  0,
}

# ─── Colors (retro CRT palette) ───────────────────────────────────────────────
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
DARK_GRAY   = (30,  30,  30)
MID_GRAY    = (80,  80,  80)

BRICK_DARK  = (140,  50,  10)
BRICK_LIGHT = (200,  80,  20)
STEEL_DARK  = (60,   80,  100)
STEEL_LIGHT = (120, 160,  200)
WATER_DARK  = (20,   60,  140)
WATER_LIGHT = (40,  120,  220)
FOREST_COL  = (20,  100,  20)
EAGLE_GOLD  = (255, 200,   0)
EAGLE_DARK  = (180, 120,   0)

PLAYER_COL  = (80,  220,  80)
PLAYER_GUN  = (60,  180,  60)

ENEMY_BASIC   = (220, 200,  20)
ENEMY_FAST    = (220,  80,  20)
ENEMY_ARMOR   = (180,  60, 180)
ENEMY_ARMOR_HIT = [(220,200,20),(200,100,20),(180,60,180),(240,20,20)]

BOSS_COL    = (220,  20,  20)
BOSS_PHASE2 = (220, 100,  20)
BOSS_PHASE3 = (255,  20, 100)

BULLET_COL  = (255, 255, 100)
HUD_BG      = (15,  15,  25)
HUD_TEXT    = (200, 200, 200)
HUD_ACCENT  = (255, 200,   0)
SCANLINE    = (0,   0,   0,  40)

# ─── Fixed Positions ──────────────────────────────────────────────────────────
EAGLE_POS        = (12, 24)
PLAYER_SPAWN     = (4,  24)
ENEMY_SPAWNS     = [(0,0), (12,0), (24,0)]
BOSS_ARENA_SIZE  = 12   # 12×12 arena

# ─── Timing (ticks at 30 FPS) ─────────────────────────────────────────────────
BASIC_MOVE_TICKS  = 4
FAST_MOVE_TICKS   = 2
ARMOR_MOVE_TICKS  = 3
PLAYER_MOVE_TICKS = 3

BASIC_FIRE_TICKS  = 90   # ~3s
FAST_FIRE_TICKS   = 45   # ~1.5s
ARMOR_FIRE_TICKS  = 60   # ~2s
PLAYER_FIRE_TICKS = 20

BULLET_SPEED_TICKS = 1   # moves every tick

BFS_REPLAN_TICKS  = 150  # ~5s
ARMOR_RETREAT_WAIT = 60  # 2s wait behind cover

MAX_ACTIVE_ENEMIES = 3
TOTAL_ENEMIES_PER_LEVEL = 20
PLAYER_LIVES = 10
SPAWN_MIN_DIST = 10      # fairness constraint

# ─── Directions ───────────────────────────────────────────────────────────────
UP    = (0, -1)
DOWN  = (0,  1)
LEFT  = (-1, 0)
RIGHT = (1,  0)
DIRS  = [UP, DOWN, LEFT, RIGHT]
DIR_NAMES = {UP:"UP", DOWN:"DOWN", LEFT:"LEFT", RIGHT:"RIGHT"}

# ─── Game States ──────────────────────────────────────────────────────────────
STATE_MENU      = "menu"
STATE_PLAYING   = "playing"
STATE_LEVEL_WIN = "level_win"
STATE_GAME_OVER = "game_over"
STATE_BOSS      = "boss"
STATE_VICTORY   = "victory"
