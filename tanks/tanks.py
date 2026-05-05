"""

Implements all agent models:
  PlayerTank  — Human-controlled
  BasicTank   — Simple Reflex Agent  + BFS
  FastTank    — Goal-Based Agent     + Greedy Best-First
  ArmorTank   — Model-Based Reflex   + A*
  BossTank    — Adversarial Agent    + Minimax + Alpha-Beta
"""

import random
from constants import *
from modules.search import (
    bfs, greedy_best_first_step, astar, bfs_nearest, has_line_of_sight, manhattan
)
from modules.minimax import MinimaxBoss


# ─── Bullet ───────────────────────────────────────────────────────────────────

class Bullet:
    def __init__(self, x, y, direction, owner):
        self.x     = x
        self.y     = y
        self.dir   = direction
        self.owner = owner   # 'player' or 'enemy'
        self.alive = True
        self._just_fired = True  # skip collision on first tile (spawned inside tank)

    def pos(self):
        return (self.x, self.y)

    def update(self, grid):
        """Advance bullet one tile per tick."""
        dx, dy = self.dir
        nx, ny = self.x + dx, self.y + dy

        if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
            self.alive = False
            return

        cell = grid[ny][nx]
        if cell == BRICK:
            grid[ny][nx] = EMPTY
            self.alive = False
        elif cell == STEEL:
            self.alive = False
        elif cell == WATER:
            self.alive = False
        else:
            self.x, self.y = nx, ny
            if cell == EAGLE:
                self.alive = False   # eagle hit — handled by game loop
        self._just_fired = False


# ─── Base Tank ────────────────────────────────────────────────────────────────

class Tank:
    def __init__(self, x, y, direction=UP):
        self.x         = x
        self.y         = y
        self.direction = direction
        self.alive     = True
        self.hp        = 1
        self.bullet    = None
        self.move_timer = 0
        self.fire_timer = 0
        self.move_interval = BASIC_MOVE_TICKS
        self.fire_interval = BASIC_FIRE_TICKS

    def pos(self):
        return (self.x, self.y)

    def take_hit(self):
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False
        return self.alive

    def can_move(self):
        return self.move_timer <= 0

    def can_fire(self):
        return self.fire_timer <= 0 and self.bullet is None

    def tick_timers(self):
        if self.move_timer > 0:
            self.move_timer -= 1
        if self.fire_timer > 0:
            self.fire_timer -= 1

    def try_move(self, direction, grid, other_tanks=None):
        dx, dy = direction
        nx, ny = self.x + dx, self.y + dy
        if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
            return False
        cell = grid[ny][nx]
        if cell in (EMPTY, FOREST):
            # Also check tank-vs-tank collision
            if other_tanks:
                for t in other_tanks:
                    if t is not self and t.alive and t.x == nx and t.y == ny:
                        self.direction = direction
                        return False
            self.x, self.y = nx, ny
            self.direction = direction
            self.move_timer = self.move_interval
            return True
        self.direction = direction
        return False

    def fire(self):
        if self.can_fire():
            # Spawn at tank tile; bullet advances on first update()
            self.bullet = Bullet(self.x, self.y, self.direction, 'enemy')
            self.fire_timer = self.fire_interval
            return self.bullet
        return None


# ─── Player Tank ──────────────────────────────────────────────────────────────

class PlayerTank(Tank):
    def __init__(self, x, y):
        super().__init__(x, y, UP)
        self.hp             = 1
        self.move_interval  = PLAYER_MOVE_TICKS
        self.fire_interval  = PLAYER_FIRE_TICKS
        self.lives          = PLAYER_LIVES
        self.score          = 0
        self.invincible     = 0  # ticks of spawn protection

    def fire(self):
        if self.can_fire():
            b = Bullet(self.x, self.y, self.direction, 'player')
            self.bullet = b
            self.fire_timer = self.fire_interval
            return b
        return None

    def take_hit(self):
        if self.invincible > 0:
            return True
        self.lives -= 1
        self.alive = self.lives > 0
        if self.alive:
            # Respawn
            self.x, self.y = PLAYER_SPAWN
            self.hp = 1
            self.invincible = 90  # 3 seconds
        return self.alive

    def tick_timers(self):
        super().tick_timers()
        if self.invincible > 0:
            self.invincible -= 1


# ─── Basic Tank (Simple Reflex Agent + BFS) ───────────────────────────────────

class BasicTank(Tank):
    """
    Simple Reflex Agent: IF-THEN rules only. No memory, no planning.
    BFS path to Eagle. Shoots if player in line-of-sight.
    """

    def __init__(self, x, y):
        super().__init__(x, y, DOWN)
        self.hp            = 1
        self.move_interval = BASIC_MOVE_TICKS
        self.fire_interval = BASIC_FIRE_TICKS
        self._path         = []
        self._bfs_timer    = 0
        self._nodes_searched = 0

    def decide(self, grid, player_pos, eagle_pos):
        """Simple Reflex rules. Returns (action, fire?)."""
        self._bfs_timer -= 1

        # Recompute BFS path if needed
        if not self._path or self._bfs_timer <= 0:
            result = bfs(grid, self.pos(), eagle_pos)
            self._path, self._nodes_searched = result if result else ([], 0)
            self._bfs_timer = BFS_REPLAN_TICKS

        # Rule 1: Shoot if player aligned (Simple Reflex)
        should_fire = False
        px, py = player_pos
        if self.x == px or self.y == py:
            if has_line_of_sight(grid, self.pos(), player_pos):
                # Face player direction
                if px > self.x:   self.direction = RIGHT
                elif px < self.x: self.direction = LEFT
                elif py > self.y: self.direction = DOWN
                else:             self.direction = UP
                should_fire = True

        # Rule 2: Follow BFS path
        move_dir = None
        if self._path:
            next_tile = self._path[0]
            # If path head occupied/changed, replan
            tx, ty = next_tile
            if grid[ty][tx] in (STEEL, WATER):
                self._path = []
            else:
                dx = tx - self.x
                dy = ty - self.y
                move_dir = (dx, dy)
                if (tx, ty) == self.pos():
                    self._path.pop(0)
                    if self._path:
                        nx2, ny2 = self._path[0]
                        move_dir = (nx2-self.x, ny2-self.y)
        else:
            # Random free direction
            free = []
            for d in DIRS:
                ddx, ddy = d
                nx, ny = self.x+ddx, self.y+ddy
                if 0<=nx<GRID_SIZE and 0<=ny<GRID_SIZE and grid[ny][nx] not in (STEEL,WATER):
                    free.append(d)
            move_dir = random.choice(free) if free else None

        # Rule 3: Shoot brick in movement direction
        if move_dir and not should_fire:
            ddx, ddy = move_dir
            nx, ny = self.x+ddx, self.y+ddy
            if 0<=nx<GRID_SIZE and 0<=ny<GRID_SIZE and grid[ny][nx] == BRICK:
                self.direction = move_dir
                should_fire = True

        return move_dir, should_fire

    def update(self, grid, player_pos, eagle_pos):
        self.tick_timers()
        move_dir, should_fire = self.decide(grid, player_pos, eagle_pos)

        bullet = None
        if should_fire and self.can_fire():
            bullet = self.fire()

        if move_dir and self.can_move():
            # Advance path pointer after successful move
            if self.try_move(move_dir, grid) and self._path:
                if self._path and self._path[0] == self.pos():
                    self._path.pop(0)

        return bullet


# ─── Fast Tank (Goal-Based Agent + Greedy Best-First) ─────────────────────────

class FastTank(Tank):
    """
    Goal-Based Agent: Single goal = destroy Eagle. Ignores player.
    Greedy Best-First: always moves toward tile with lowest Manhattan(→Eagle).
    Intentionally gets stuck in local minima — shows greedy's limits.
    """

    def __init__(self, x, y):
        super().__init__(x, y, DOWN)
        self.hp            = 1
        self.move_interval = FAST_MOVE_TICKS
        self.fire_interval = FAST_FIRE_TICKS
        self._nodes_searched = 0
        self._stuck_counter = 0
        self._last_pos = None

    def update(self, grid, player_pos, eagle_pos):
        self.tick_timers()
        bullet = None

        # Single-step greedy decision (re-computed every tick)
        next_tile, nodes = greedy_best_first_step(grid, self.pos(), eagle_pos)
        self._nodes_searched = nodes

        # Detect stuck (local minima)
        if self._last_pos == self.pos():
            self._stuck_counter += 1
        else:
            self._stuck_counter = 0
        self._last_pos = self.pos()

        should_fire = False
        move_dir = None

        if next_tile:
            tx, ty = next_tile
            move_dir = (tx - self.x, ty - self.y)

            # Rule: shoot brick in path (never detour!)
            if grid[ty][tx] == BRICK:
                self.direction = move_dir
                should_fire = True
            else:
                move_dir = move_dir

        # If stuck for a while, try random move (escape heuristic)
        if self._stuck_counter > 10:
            free = [d for d in DIRS if 0<=self.x+d[0]<GRID_SIZE
                    and 0<=self.y+d[1]<GRID_SIZE
                    and grid[self.y+d[1]][self.x+d[0]] not in (STEEL,WATER)]
            if free:
                move_dir = random.choice(free)
                self._stuck_counter = 0

        if should_fire and self.can_fire():
            bullet = self.fire()
        if move_dir and self.can_move():
            self.try_move(move_dir, grid)

        return bullet


# ─── Armor Tank (Model-Based Reflex + A*) ─────────────────────────────────────

class ArmorTank(Tank):
    """
    Model-Based Reflex Agent: Maintains internal state (hitCount).
    A* navigation with brick-shooting cost model.
    Retreats to nearest steel wall on 3rd hit.
    """

    STATE_ATTACK  = "attack"
    STATE_RETREAT = "retreat"
    STATE_COVER   = "cover"

    def __init__(self, x, y):
        super().__init__(x, y, DOWN)
        self.hp            = 4
        self.max_hp        = 4
        self.move_interval = ARMOR_MOVE_TICKS
        self.fire_interval = ARMOR_FIRE_TICKS
        self._path         = []
        self._state        = self.STATE_ATTACK
        self._cover_timer  = 0
        self._nodes_searched = 0
        self._hit_flash    = 0  # visual flash timer

    def take_hit(self):
        self.hp -= 1
        self._hit_flash = 15  # flash for 0.5s
        if self.hp <= 0:
            self.alive = False
            return False
        # On 3rd hit (hp=1) → retreat
        if self.hp == 1 and self._state == self.STATE_ATTACK:
            self._state = self.STATE_RETREAT
            self._path  = []
        return True

    def _replan_astar(self, grid, goal):
        result = astar(grid, self.pos(), goal)
        self._path, self._nodes_searched = result if result else ([], 0)

    def update(self, grid, player_pos, eagle_pos):
        self.tick_timers()
        if self._hit_flash > 0:
            self._hit_flash -= 1

        bullet   = None
        move_dir = None

        # ── State: RETREAT — find nearest steel ───────────────────────────────
        if self._state == self.STATE_RETREAT:
            if not self._path:
                steel_tile = bfs_nearest(grid, self.pos(), [STEEL])
                if steel_tile:
                    # Navigate adjacent to steel
                    stx, sty = steel_tile
                    # Find adjacent empty tile next to steel
                    for d in DIRS:
                        cx, cy = stx+d[0], sty+d[1]
                        if 0<=cx<GRID_SIZE and 0<=cy<GRID_SIZE and grid[cy][cx] in (EMPTY,FOREST):
                            result = bfs(grid, self.pos(), (cx,cy))
                            self._path = result[0] if result else []
                            break
                if not self._path:
                    self._state = self.STATE_COVER
                    self._cover_timer = ARMOR_RETREAT_WAIT

            if self._path:
                next_tile = self._path[0]
                tx, ty = next_tile
                move_dir = (tx-self.x, ty-self.y)
                if self.can_move() and self.try_move(move_dir, grid):
                    if self._path and self._path[0] == self.pos():
                        self._path.pop(0)
                if not self._path:
                    self._state = self.STATE_COVER
                    self._cover_timer = ARMOR_RETREAT_WAIT

        # ── State: COVER — wait behind steel ──────────────────────────────────
        elif self._state == self.STATE_COVER:
            self._cover_timer -= 1
            if self._cover_timer <= 0:
                self._state = self.STATE_ATTACK
                self._path  = []

        # ── State: ATTACK — navigate to Eagle via A* ──────────────────────────
        elif self._state == self.STATE_ATTACK:
            if not self._path:
                self._replan_astar(grid, eagle_pos)

            # Shoot player if in line-of-sight
            if has_line_of_sight(grid, self.pos(), player_pos):
                px, py = player_pos
                if px > self.x:   self.direction = RIGHT
                elif px < self.x: self.direction = LEFT
                elif py > self.y: self.direction = DOWN
                else:             self.direction = UP
                if self.can_fire():
                    bullet = self.fire()

            if self._path:
                next_tile = self._path[0]
                tx, ty = next_tile
                # Replan if tile changed
                if grid[ty][tx] in (STEEL, WATER):
                    self._path = []
                    self._replan_astar(grid, eagle_pos)
                else:
                    move_dir = (tx-self.x, ty-self.y)
                    # Shoot brick in path
                    if grid[ty][tx] == BRICK and self.can_fire() and not bullet:
                        self.direction = move_dir
                        bullet = self.fire()
                    elif self.can_move():
                        if self.try_move(move_dir, grid):
                            if self._path and self._path[0] == self.pos():
                                self._path.pop(0)

        return bullet

    def hit_color(self):
        """Return color based on HP stage for visual feedback."""
        idx = self.max_hp - self.hp
        return ENEMY_ARMOR_HIT[min(idx, 3)]


# ─── Boss Tank (Adversarial Agent + Minimax + Alpha-Beta) ─────────────────────

class BossTank(Tank):
    """
    Adversarial Agent: Minimax with Alpha-Beta Pruning.
    3-phase system — gets more aggressive as HP drops.
    """

    def __init__(self, x, y):
        super().__init__(x, y, DOWN)
        self.hp            = 10
        self.max_hp        = 10
        self.move_interval = 4   # Phase 1: slow
        self.fire_interval = 15  # Phase 1: ~0.5s
        self._ai           = MinimaxBoss()
        self._hit_flash    = 0
        self._phase        = 1

    def _update_phase(self):
        if self.hp >= 7:
            self._phase = 1
            self.move_interval = 4
            self.fire_interval = 15
            self._depth = 2
        elif self.hp >= 3:
            self._phase = 2
            self.move_interval = 3
            self.fire_interval = 10
            self._depth = 3
        else:
            self._phase = 3
            self.move_interval = 2
            self.fire_interval = 7
            self._depth = 4

    def take_hit(self):
        self.hp -= 1
        self._hit_flash = 20
        self._update_phase()
        if self.hp <= 0:
            self.alive = False
            return False
        return True

    def update(self, grid, player_pos, player_hp):
        self.tick_timers()
        if self._hit_flash > 0:
            self._hit_flash -= 1

        self._update_phase()
        bullet = None

        # Minimax decision
        action, score = self._ai.decide(
            self.pos(), self.hp, player_pos, player_hp, grid, self._depth
        )

        # Apply move
        if self.can_move():
            self.try_move(action, grid)

        # Shoot decision: if player in line-of-sight
        if self.can_fire() and has_line_of_sight(grid, self.pos(), player_pos):
            px, py = player_pos
            if px > self.x:   self.direction = RIGHT
            elif px < self.x: self.direction = LEFT
            elif py > self.y: self.direction = DOWN
            else:             self.direction = UP
            bullet = self.fire()

        # Phase 3: also shoot randomly for unpredictability
        if self._phase == 3 and self.can_fire() and random.random() < 0.3:
            if not bullet:
                self.direction = random.choice(DIRS)
                bullet = self.fire()

        return bullet

    def phase_color(self):
        if self._phase == 1: return BOSS_COL
        if self._phase == 2: return BOSS_PHASE2
        return BOSS_PHASE3

    def minimax_stats(self):
        return {
            "phase": self._phase,
            "depth": self._depth,
            "nodes_plain": self._ai.nodes_without_pruning,
            "nodes_pruned": self._ai.nodes_with_pruning,
            "speedup": self._ai.speedup_ratio(),
        }
