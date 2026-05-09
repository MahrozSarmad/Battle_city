"""
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
    PlayerTank, BasicTank, FastTank, ArmorTank, PowerTank, BossTank, Bullet
)
from renderer import Renderer


# ─── Level Configuration ──────────────────────────────────────────────────────

LEVEL_ENEMY_POOLS = {
    # Level 1: 7x Basic + 5x Fast = 12 total
    1: [BasicTank]*7 + [FastTank]*5, 
    # Level 2: 4x Fast + 3x Armor + 2x Power = 9 total
    2: [FastTank]*4 + [ArmorTank]*3 + [PowerTank]*2,
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
        self.kills_this_level = 0
        self.current_eagle_pos = None
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
        self.kills_this_level = 0

        if level == "boss":
            self.grid  = generate_boss_arena()
            # Boss Level: Special spawns inside the 18x18 arena (offset 4,4)
            self.player = PlayerTank(12, 20)
            self.boss_tank = BossTank(12, 5)
            self.enemies = [self.boss_tank]
            self.enemy_pool = []
        else:
            gen = CSPMapGenerator(level=level, seed=self._rng.randint(0, 99999))
            self.grid  = gen.generate()
            self.player = PlayerTank(*PLAYER_SPAWN)
            pool_classes = LEVEL_ENEMY_POOLS.get(level, LEVEL_ENEMY_POOLS[1])
            self.enemy_pool = list(pool_classes)
            # Do NOT shuffle Level 1 pool to maintain the 7-then-5 sequence
            if level != 1:
                self._rng.shuffle(self.enemy_pool)

        # ─── Universal Eagle Detection ────────────────────────────────────────
        self.current_eagle_pos = None
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.grid[y][x] == EAGLE:
                    self.current_eagle_pos = (x, y)
                    break
            if self.current_eagle_pos: break

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

    # ── Level 1 Special Rule ──────────────────────────────────────────────────
    def _apply_special_rules(self):
        if self.level == 1:
            # Rule: Fast tanks spawn after 10 kills
            if self.kills_this_level == 10:
                # Inject 5 Fast tanks into the front of the pool
                # (We do this only once)
                if not any(issubclass(c, FastTank) for c in self.enemy_pool):
                    fast_tanks = [FastTank] * 5
                    self.enemy_pool = fast_tanks + self.enemy_pool
                    # Visual/Console feedback for the rule
                    print("Rule Activated: Fast tanks charging!")

    # ── Collision Detection ───────────────────────────────────────────────────

    def _process_bullets(self):
        for b in list(self.bullets):
            if not b.alive:
                continue

            b.update(self.grid)
            bpos = b.pos()

            # Bullet vs Eagle (Check this FIRST before continuing)
            ex, ey = self.current_eagle_pos or EAGLE_POS
            if bpos == (ex, ey) or (0 <= b.y < GRID_SIZE and 0 <= b.x < GRID_SIZE and self.grid[b.y][b.x] == EAGLE):
                self.eagle_destroyed = True
                b.alive = False
                continue

            if not b.alive:
                continue

            # Skip ALL collision checks on the tick the bullet was just fired
            if b._just_fired:
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
                            self.kills_this_level += 1
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

        # AI updates
        eagle_pos = self.current_eagle_pos or EAGLE_POS
        for e in self.enemies:
            if not e.alive:
                continue
            bullet = None
            if isinstance(e, BossTank):
                bullet = e.update(self.grid, self.player.pos(), self.player.lives, eagle_pos)
                self.minimax_stats = e.minimax_stats()
            elif isinstance(e, ArmorTank):
                bullet = e.update(self.grid, self.player.pos(), eagle_pos)
            elif isinstance(e, FastTank):
                bullet = e.update(self.grid, self.player.pos(), eagle_pos)
            elif isinstance(e, BasicTank):
                bullet = e.update(self.grid, self.player.pos(), eagle_pos)
            elif isinstance(e, PowerTank):
                bullet = e.update(self.grid, self.player.pos(), eagle_pos)
            if bullet:
                self.bullets.append(bullet)

        # Reset bullet references so tanks can fire again
        if self.player.bullet and not self.player.bullet.alive:
            self.player.bullet = None
        for e in self.enemies:
            if e.bullet and not e.bullet.alive:
                e.bullet = None

        # Process bullets
        self._process_bullets()

        # Spawn
        if self.level != "boss":
            self._apply_special_rules()
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
                    if self.state == STATE_PLAYING:
                        if event.key == pygame.K_ESCAPE:
                            self.state = STATE_PAUSED
                    elif self.state == STATE_PAUSED:
                        if event.key == pygame.K_RETURN:
                            self.state = STATE_PLAYING
                        elif event.key == pygame.K_q:
                            self.__init__()
                            self.state = STATE_MENU
                    elif self.state == STATE_MENU:
                        if event.key == pygame.K_ESCAPE:
                            pygame.quit(); sys.exit()
                        if event.key == pygame.K_RETURN or event.key == pygame.K_1:
                            self.load_level(1)
                        elif event.key == pygame.K_2:
                            self.load_level(2)
                        elif event.key == pygame.K_3:
                            self.load_level("boss")
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
            if self.state not in (STATE_PAUSED, STATE_MENU):
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
                    eagle_loc = self.current_eagle_pos or EAGLE_POS
                    self.renderer.render_eagle_destroyed(eagle_loc)
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

            elif self.state == STATE_PAUSED:
                # Render the game state but dim it with the pause overlay
                self.renderer.render_grid(self.grid)
                self.renderer.render_tanks(self.player, [e for e in self.enemies if e.alive])
                enemies_left = len(self.enemy_pool) + len([e for e in self.enemies if e.alive])
                self.renderer.render_hud(self.player, self.level, enemies_left, self.minimax_stats)
                self.renderer.render_pause()

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
