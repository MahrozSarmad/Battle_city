"""
Battle City (Tank 1990) — Main Game Loop
AL2002 Artificial Intelligence Lab | Spring 2026

Orchestrates all modules:
  Module A: CSP Map Generator
  Module B: BFS / Greedy / A* Tank agents
  Module C: Minimax + Alpha-Beta Boss
"""

import sys
import random
import pygame

from constants import *
from modules.csp_map import CSPMapGenerator, generate_boss_arena
from modules.search import manhattan
from tanks.tanks import (
    PlayerTank, BasicTank, FastTank, ArmorTank, BossTank, Bullet
)
from renderer import Renderer


# ─── Level Configuration ──────────────────────────────────────────────────────

LEVEL_ENEMY_POOLS = {
    1: [BasicTank]*7 + [FastTank]*5 + [BasicTank]*8,  # 20 total: 7 basic + 5 fast + 8 more basic
    2: [FastTank]*4  + [ArmorTank]*3 + [FastTank]*2 + [BasicTank]*11,
}

BOSS_SPAWN = (13, 8)
PLAYER_BOSS_SPAWN = (13, 17)


# ─── Game ─────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Battle City — AL2002 AI Lab")
        self.screen   = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock    = pygame.time.Clock()
        self.renderer = Renderer(self.screen)
        self.state    = STATE_MENU
        self.level    = 1
        self.grid     = None
        self.player   = None
        self.enemies  = []
        self.bullets  = []
        self.enemy_pool   = []
        self.spawn_timer  = 0
        self.eagle_destroyed = False
        self.transition_timer = 0
        self.minimax_stats    = None
        self.boss_tank        = None
        self._rng             = random.Random()

    # ── Level Setup ───────────────────────────────────────────────────────────

    def load_level(self, level):
        self.level    = level
        self.enemies  = []
        self.bullets  = []
        self.eagle_destroyed = False
        self.spawn_timer = 60
        self.minimax_stats = None
        self.boss_tank = None

        if level == "boss":
            self.grid  = generate_boss_arena()
            self.player = PlayerTank(*PLAYER_BOSS_SPAWN)
            self.boss_tank = BossTank(*BOSS_SPAWN)
            self.enemies = [self.boss_tank]
            self.enemy_pool = []
        else:
            gen = CSPMapGenerator(level=level, seed=self._rng.randint(0, 99999))
            self.grid  = gen.generate()
            self.player = PlayerTank(*PLAYER_SPAWN)
            pool_classes = LEVEL_ENEMY_POOLS.get(level, LEVEL_ENEMY_POOLS[1])
            self.enemy_pool = list(pool_classes)
            self._rng.shuffle(self.enemy_pool)

        self.state = STATE_PLAYING

    # ── Spawn ─────────────────────────────────────────────────────────────────

    def _try_spawn(self):
        if not self.enemy_pool:
            return
        active = [e for e in self.enemies if e.alive]
        if len(active) >= MAX_ACTIVE_ENEMIES:
            return

        self.spawn_timer -= 1
        if self.spawn_timer > 0:
            return
        self.spawn_timer = 45

        # Pick spawn point (fairness constraint: ≥10 tiles from player)
        valid_spawns = [
            sp for sp in ENEMY_SPAWNS
            if manhattan(sp, self.player.pos()) >= SPAWN_MIN_DIST
        ]
        if not valid_spawns:
            valid_spawns = ENEMY_SPAWNS

        sx, sy = self._rng.choice(valid_spawns)
        # Check not occupied
        occupied = {e.pos() for e in self.enemies if e.alive}
        occupied.add(self.player.pos())
        if (sx, sy) in occupied:
            return

        TankClass = self.enemy_pool.pop(0)
        tank = TankClass(sx, sy)
        self.enemies.append(tank)

    # ── Collision Detection ───────────────────────────────────────────────────

    def _process_bullets(self):
        for b in list(self.bullets):
            if not b.alive:
                continue

            b.update(self.grid)
            if not b.alive:
                continue

            # Skip ALL collision checks on the tick the bullet was just fired
            # (it's still on the tank's tile)
            if b._just_fired:
                continue

            bpos = b.pos()

            # Bullet vs Eagle
            ex, ey = EAGLE_POS
            if bpos == (ex, ey) or self.grid[b.y][b.x] == EAGLE:
                self.eagle_destroyed = True
                b.alive = False
                continue

            # Bullet vs tanks
            for tank in ([self.player] + self.enemies):
                if not tank or not tank.alive:
                    continue
                if tank.pos() == bpos:
                    # Skip friendly fire
                    if b.owner == 'player' and tank == self.player:
                        continue
                    if b.owner == 'enemy' and tank != self.player:
                        continue
                    # Valid hit
                    tank.take_hit()
                    if not isinstance(tank, PlayerTank):
                        if not tank.alive:
                            self.player.score += 100
                    b.alive = False
                    break

            if not b.alive:
                continue

            # Bullet vs bullet
            for other in self.bullets:
                if other is b or not other.alive or other._just_fired:
                    continue
                if other.pos() == bpos:
                    b.alive = False
                    other.alive = False
                    break

        self.bullets = [b for b in self.bullets if b.alive]

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self):
        if self.state != STATE_PLAYING:
            return

        # Player input already handled in event loop; process movement here
        # (handled below in run())

        # Enemy AI updates
        eagle_pos = EAGLE_POS
        for e in self.enemies:
            if not e.alive:
                continue
            bullet = None
            if isinstance(e, BossTank):
                bullet = e.update(self.grid, self.player.pos(), self.player.lives)
                self.minimax_stats = e.minimax_stats()
            elif isinstance(e, ArmorTank):
                bullet = e.update(self.grid, self.player.pos(), eagle_pos)
            elif isinstance(e, FastTank):
                bullet = e.update(self.grid, self.player.pos(), eagle_pos)
            elif isinstance(e, BasicTank):
                bullet = e.update(self.grid, self.player.pos(), eagle_pos)
            if bullet:
                self.bullets.append(bullet)

        # Player bullet tick
        if self.player.bullet and not self.player.bullet.alive:
            self.player.bullet = None

        # Process bullets
        self._process_bullets()

        # Spawn
        if self.level != "boss":
            self._try_spawn()

        # Win/lose checks
        if self.eagle_destroyed:
            self.state = STATE_GAME_OVER
            return

        if not self.player.alive:
            self.state = STATE_GAME_OVER
            return

        active_enemies = [e for e in self.enemies if e.alive]
        if not active_enemies and not self.enemy_pool:
            if self.level == "boss":
                self.state = STATE_VICTORY
            elif self.level < 2:
                self.transition_timer = 90
                self.state = STATE_LEVEL_WIN
            elif self.level == 2:
                self.transition_timer = 90
                self.state = STATE_LEVEL_WIN

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            self.clock.tick(FPS)
            self.renderer.tick_advance()
            tick = self.renderer.tick

            # ── Events ────────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
                    if self.state == STATE_MENU:
                        if event.key == pygame.K_RETURN:
                            self.load_level(1)
                    elif self.state == STATE_LEVEL_WIN:
                        pass  # auto-advance
                    elif self.state in (STATE_GAME_OVER, STATE_VICTORY):
                        if event.key == pygame.K_RETURN:
                            self.__init__()
                            self.state = STATE_MENU

            # ── Player movement (held keys) ───────────────────────────────────
            if self.state == STATE_PLAYING and self.player.alive:
                keys = pygame.key.get_pressed()
                self.player.tick_timers()

                move_dir = None
                if keys[pygame.K_w] or keys[pygame.K_UP]:    move_dir = UP
                elif keys[pygame.K_s] or keys[pygame.K_DOWN]: move_dir = DOWN
                elif keys[pygame.K_a] or keys[pygame.K_LEFT]: move_dir = LEFT
                elif keys[pygame.K_d] or keys[pygame.K_RIGHT]: move_dir = RIGHT

                if move_dir and self.player.can_move():
                    self.player.try_move(move_dir, self.grid)

                if keys[pygame.K_SPACE] and self.player.can_fire():
                    b = self.player.fire()
                    if b:
                        self.bullets.append(b)

                if self.player.bullet and not self.player.bullet.alive:
                    self.player.bullet = None

            # ── Update game state ─────────────────────────────────────────────
            self.update()

            # ── Level transition ──────────────────────────────────────────────
            if self.state == STATE_LEVEL_WIN:
                self.transition_timer -= 1
                if self.transition_timer <= 0:
                    if self.level == 1:
                        self.load_level(2)
                    elif self.level == 2:
                        self.load_level("boss")

            # ── Render ────────────────────────────────────────────────────────
            self.screen.fill(BLACK)

            if self.state == STATE_MENU:
                self.renderer.render_menu()

            elif self.state in (STATE_PLAYING, STATE_LEVEL_WIN):
                self.renderer.render_grid(self.grid)
                if self.eagle_destroyed:
                    self.renderer.render_eagle_destroyed(EAGLE_POS)
                self.renderer.render_bullets(self.bullets)
                self.renderer.render_tanks(
                    self.player,
                    [e for e in self.enemies if e.alive]
                )
                enemies_left = len(self.enemy_pool) + len([e for e in self.enemies if e.alive])
                self.renderer.render_hud(
                    self.player, self.level, enemies_left, self.minimax_stats
                )
                if self.state == STATE_LEVEL_WIN:
                    self.renderer.render_overlay(
                        f"LEVEL {self.level} CLEAR!",
                        "Advancing...",
                        (100, 255, 100)
                    )

            elif self.state == STATE_GAME_OVER:
                self.renderer.render_grid(self.grid)
                self.renderer.render_hud(self.player, self.level, 0)
                self.renderer.render_overlay(
                    "GAME OVER",
                    f"Score: {self.player.score if self.player else 0}  |  ENTER to restart",
                    (255, 60, 60)
                )

            elif self.state == STATE_VICTORY:
                self.renderer.render_grid(self.grid)
                self.renderer.render_hud(self.player, "BOSS", 0, self.minimax_stats)
                self.renderer.render_overlay(
                    "VICTORY!",
                    f"Boss defeated!  Score: {self.player.score}  |  ENTER to restart",
                    EAGLE_GOLD
                )

            pygame.display.flip()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    game = Game()
    game.run()
