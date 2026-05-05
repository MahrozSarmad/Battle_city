

import pygame
import math
from constants import *


def _draw_brick(surf, rect, tick):
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    pygame.draw.rect(surf, BRICK_DARK, rect)
    # Mortar lines
    mid_x = x + w//2
    mid_y = y + h//2
    pygame.draw.rect(surf, BRICK_LIGHT, (x+1, y+1, w//2-2, h//2-2))
    pygame.draw.rect(surf, BRICK_LIGHT, (mid_x+1, mid_y+1, w//2-2, h//2-2))


def _draw_steel(surf, rect):
    pygame.draw.rect(surf, STEEL_DARK, rect)
    pygame.draw.rect(surf, STEEL_LIGHT, rect.inflate(-6,-6))
    pygame.draw.rect(surf, STEEL_DARK, rect.inflate(-10,-10))


def _draw_water(surf, rect, tick):
    pygame.draw.rect(surf, WATER_DARK, rect)
    offset = (tick // 8) % (rect.width // 2)
    for i in range(3):
        wx = rect.x + offset + i * (rect.width//2) - rect.width//2
        pygame.draw.rect(surf, WATER_LIGHT, (wx, rect.y + rect.height//3, rect.width//3, 3))


def _draw_forest(surf, rect):
    pygame.draw.rect(surf, DARK_GRAY, rect)
    pygame.draw.rect(surf, FOREST_COL, rect.inflate(-4,-4))
    # Tree dots
    cx, cy = rect.centerx, rect.centery
    for dx, dy in [(-5,-5),(5,-5),(0,3),(-5,5),(5,5)]:
        pygame.draw.circle(surf, (10,80,10), (cx+dx, cy+dy), 4)


def _draw_eagle(surf, rect, destroyed=False):
    if destroyed:
        pygame.draw.rect(surf, (60,20,20), rect)
        pygame.draw.line(surf, (180,20,20), rect.topleft, rect.bottomright, 3)
        pygame.draw.line(surf, (180,20,20), rect.topright, rect.bottomleft, 3)
        return
    pygame.draw.rect(surf, EAGLE_DARK, rect)
    cx, cy = rect.centerx, rect.centery
    # Simple eagle shape
    points = [
        (cx, cy - rect.height//2 + 3),
        (cx + rect.width//2 - 3, cy + rect.height//2 - 3),
        (cx, cy),
        (cx - rect.width//2 + 3, cy + rect.height//2 - 3),
    ]
    pygame.draw.polygon(surf, EAGLE_GOLD, points)


def _draw_tank(surf, rect, color, gun_color, direction, flash=False):
    if flash:
        color = WHITE
    cx, cy = rect.centerx, rect.centery
    r = rect.width // 2 - 2

    # Body
    pygame.draw.circle(surf, color, (cx, cy), r)
    pygame.draw.circle(surf, gun_color, (cx, cy), r - 4)

    # Gun barrel
    dx, dy = direction
    gun_len = r + 5
    ex = cx + dx * gun_len
    ey = cy + dy * gun_len
    pygame.draw.line(surf, color, (cx, cy), (int(ex), int(ey)), 4)

    # Tread marks (perpendicular)
    pdx, pdy = -dy, dx  # perpendicular
    tread_r = r - 1
    pygame.draw.arc(surf, gun_color,
                    (cx - tread_r, cy - tread_r, tread_r*2, tread_r*2),
                    math.pi/4, 3*math.pi/4, 2)


def _draw_bullet(surf, bx, by, direction):
    px = bx * TILE_SIZE + TILE_SIZE // 2
    py = by * TILE_SIZE + TILE_SIZE // 2
    dx, dy = direction
    # Elongated bullet in direction of travel
    ex = px + dx * 6
    ey = py + dy * 6
    pygame.draw.line(surf, BULLET_COL, (px - dx*2, py - dy*2), (ex, ey), 3)
    pygame.draw.circle(surf, WHITE, (ex, ey), 3)


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.tick   = 0
        pygame.font.init()
        self.font_sm  = pygame.font.SysFont("Courier New", 14, bold=True)
        self.font_med = pygame.font.SysFont("Courier New", 18, bold=True)
        self.font_lg  = pygame.font.SysFont("Courier New", 28, bold=True)
        self.font_xl  = pygame.font.SysFont("Courier New", 42, bold=True)

    def render_grid(self, grid):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                rect = pygame.Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                cell = grid[y][x]
                if cell == EMPTY:
                    pygame.draw.rect(self.screen, DARK_GRAY, rect)
                elif cell == BRICK:
                    _draw_brick(self.screen, rect, self.tick)
                elif cell == STEEL:
                    _draw_steel(self.screen, rect)
                elif cell == WATER:
                    _draw_water(self.screen, rect, self.tick)
                elif cell == FOREST:
                    _draw_forest(self.screen, rect)
                elif cell == EAGLE:
                    _draw_eagle(self.screen, rect)

    def render_eagle_destroyed(self, pos):
        x, y = pos
        rect = pygame.Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
        _draw_eagle(self.screen, rect, destroyed=True)

    def render_tanks(self, player, enemies):
        # Draw player
        if player and player.alive:
            rect = pygame.Rect(player.x*TILE_SIZE, player.y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
            flash = player.invincible > 0 and (self.tick % 6 < 3)
            _draw_tank(self.screen, rect, PLAYER_COL, PLAYER_GUN, player.direction, flash)

        # Draw enemies
        for e in enemies:
            if not e.alive:
                continue
            rect = pygame.Rect(e.x*TILE_SIZE, e.y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
            from tanks.tanks import BasicTank, FastTank, ArmorTank, BossTank

            if isinstance(e, ArmorTank):
                col = e.hit_color()
                flash = e._hit_flash > 0 and (self.tick % 4 < 2)
                _draw_tank(self.screen, rect, col, DARK_GRAY, e.direction, flash)
                # HP bar
                hp_w = int((e.hp / e.max_hp) * TILE_SIZE)
                pygame.draw.rect(self.screen, (200,20,20),
                                 (e.x*TILE_SIZE, e.y*TILE_SIZE - 5, TILE_SIZE, 3))
                pygame.draw.rect(self.screen, (20,200,20),
                                 (e.x*TILE_SIZE, e.y*TILE_SIZE - 5, hp_w, 3))

            elif isinstance(e, BossTank):
                col = e.phase_color()
                flash = e._hit_flash > 0 and (self.tick % 3 < 1)
                _draw_tank(self.screen, rect, col, BLACK, e.direction, flash)
                # HP bar (wide)
                hp_w = int((e.hp / e.max_hp) * TILE_SIZE)
                pygame.draw.rect(self.screen, (180,20,20),
                                 (e.x*TILE_SIZE, e.y*TILE_SIZE - 6, TILE_SIZE, 4))
                pygame.draw.rect(self.screen, (255,100,20),
                                 (e.x*TILE_SIZE, e.y*TILE_SIZE - 6, hp_w, 4))

            elif isinstance(e, FastTank):
                _draw_tank(self.screen, rect, ENEMY_FAST, DARK_GRAY, e.direction)
            else:
                _draw_tank(self.screen, rect, ENEMY_BASIC, DARK_GRAY, e.direction)

    def render_bullets(self, bullets):
        for b in bullets:
            if b.alive:
                _draw_bullet(self.screen, b.x, b.y, b.dir)

    def render_hud(self, player, level, enemies_left, minimax_stats=None):
        hx = GRID_PIXEL + 10
        # Background
        pygame.draw.rect(self.screen, HUD_BG,
                         (GRID_PIXEL, 0, HUD_WIDTH, SCREEN_H))
        pygame.draw.line(self.screen, HUD_ACCENT,
                         (GRID_PIXEL, 0), (GRID_PIXEL, SCREEN_H), 2)

        y = 20
        def label(text, color=HUD_TEXT, font=None):
            nonlocal y
            f = font or self.font_sm
            surf = f.render(text, True, color)
            self.screen.blit(surf, (hx, y))
            y += surf.get_height() + 4

        # Title
        label("BATTLE CITY", HUD_ACCENT, self.font_med)
        label(f"AL2002 AI Lab", MID_GRAY)
        y += 10

        # Level
        label(f"LEVEL: {level}", WHITE, self.font_med)
        y += 6

        # Player
        if player:
            label(f"LIVES: {'♥ '*player.lives}", (255,100,100))
            label(f"SCORE: {player.score}", HUD_ACCENT)
        y += 10

        # Enemies
        label(f"ENEMIES LEFT:", WHITE)
        label(f"{enemies_left}", (255,200,20), self.font_med)
        y += 10

        # Divider
        pygame.draw.line(self.screen, MID_GRAY, (hx, y), (hx+155, y), 1)
        y += 8

        # AI module info
        label("AI MODULES:", HUD_ACCENT)
        label("BFS  → BasicTank",  (200,200,20))
        label("GBFS → FastTank",   (220,80,20))
        label("A*   → ArmorTank",  (180,60,180))
        if minimax_stats:
            y += 4
            label("MINIMAX BOSS:", (220,20,20), self.font_sm)
            label(f"Phase: {minimax_stats['phase']}", WHITE)
            label(f"Depth: {minimax_stats['depth']}", WHITE)
            label(f"Nodes(plain):", WHITE)
            label(f"  {minimax_stats['nodes_plain']}", (255,150,50))
            label(f"Nodes(pruned):", WHITE)
            label(f"  {minimax_stats['nodes_pruned']}", (100,255,100))
            label(f"Speedup: {minimax_stats['speedup']}x", HUD_ACCENT)

        # Controls hint
        y = SCREEN_H - 110
        pygame.draw.line(self.screen, MID_GRAY, (hx, y), (hx+155, y), 1)
        y += 8
        label("CONTROLS:", HUD_ACCENT)
        label("WASD/Arrows:Move", MID_GRAY)
        label("SPACE: Fire", MID_GRAY)
        label("ESC: Quit", MID_GRAY)

    def render_overlay(self, text, subtext="", color=WHITE):
        """Full-screen overlay for win/lose/level transitions."""
        overlay = pygame.Surface((GRID_PIXEL, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cx = GRID_PIXEL // 2
        surf = self.font_xl.render(text, True, color)
        r = surf.get_rect(center=(cx, SCREEN_H//2 - 30))
        self.screen.blit(surf, r)

        if subtext:
            sub = self.font_med.render(subtext, True, HUD_TEXT)
            sr  = sub.get_rect(center=(cx, SCREEN_H//2 + 30))
            self.screen.blit(sub, sr)

    def render_menu(self):
        self.screen.fill(BLACK)
        CX = GRID_PIXEL // 2  # center on the grid area, not full window

        # Decorative border
        pygame.draw.rect(self.screen, EAGLE_GOLD,
                         (20, 20, GRID_PIXEL - 40, SCREEN_H - 40), 2)
        pygame.draw.rect(self.screen, (80, 60, 0),
                         (24, 24, GRID_PIXEL - 48, SCREEN_H - 48), 1)

        y = 80
        # Title
        title = self.font_xl.render("BATTLE CITY", True, EAGLE_GOLD)
        self.screen.blit(title, title.get_rect(center=(CX, y)))

        sub = self.font_med.render("TANK 1990  —  AI Edition", True, HUD_TEXT)
        self.screen.blit(sub, sub.get_rect(center=(CX, y + 55)))

        course = self.font_sm.render("AL2002 Artificial Intelligence Lab  |  Spring 2026",
                                     True, MID_GRAY)
        self.screen.blit(course, course.get_rect(center=(CX, y + 85)))

        # Divider
        pygame.draw.line(self.screen, (60, 50, 0),
                         (60, y + 108), (GRID_PIXEL - 60, y + 108), 1)

        # Module list — clean two-column layout
        modules = [
            ("Module A", "CSP Map Generator", (100, 200, 255)),
            ("Module B", "BFS / Greedy / A* Search", (100, 255, 100)),
            ("Module C", "Minimax + Alpha-Beta (Boss)", (255, 120, 100)),
        ]
        my = y + 130
        for mod, desc, color in modules:
            # Left: module label
            lsurf = self.font_med.render(mod + ":", True, color)
            self.screen.blit(lsurf, lsurf.get_rect(midright=(CX - 10, my)))
            # Right: description
            dsurf = self.font_sm.render(desc, True, HUD_TEXT)
            self.screen.blit(dsurf, dsurf.get_rect(midleft=(CX + 10, my + 2)))
            my += 46

        # Divider
        pygame.draw.line(self.screen, (60, 50, 0),
                         (60, my + 10), (GRID_PIXEL - 60, my + 10), 1)

        # Pulsing prompt
        pulse = abs(math.sin(self.tick * 0.05))
        col   = (int(255 * pulse), int(200 * pulse), 0)
        start = self.font_lg.render("PRESS  ENTER  TO  START", True, col)
        self.screen.blit(start, start.get_rect(center=(CX, my + 50)))

        # Controls
        controls = self.font_sm.render(
            "WASD / Arrows = Move    SPACE = Fire    ESC = Quit",
            True, MID_GRAY)
        self.screen.blit(controls, controls.get_rect(center=(CX, my + 90)))

        # HUD sidebar even on menu
        pygame.draw.rect(self.screen, HUD_BG, (GRID_PIXEL, 0, HUD_WIDTH, SCREEN_H))
        pygame.draw.line(self.screen, EAGLE_GOLD, (GRID_PIXEL, 0), (GRID_PIXEL, SCREEN_H), 2)
        hx = GRID_PIXEL + 10
        hy = 20
        def hud_label(text, color=HUD_TEXT, font=None):
            nonlocal hy
            f = font or self.font_sm
            s = f.render(text, True, color)
            self.screen.blit(s, (hx, hy))
            hy += s.get_height() + 5
        hud_label("AL2002", EAGLE_GOLD, self.font_med)
        hud_label("AI Lab", MID_GRAY)
        hy += 10
        hud_label("Team Size:", HUD_TEXT)
        hud_label("2 or 1", WHITE)
        hy += 10
        hud_label("Language:", HUD_TEXT)
        hud_label("Python", WHITE)
        hy += 10
        hud_label("Levels:", HUD_TEXT)
        hud_label("1 - Brick Maze", (200, 200, 20))
        hud_label("2 - Steel Fort", (200, 200, 20))
        hud_label("BOSS Level", (255, 80, 80))

    def tick_advance(self):
        self.tick += 1
