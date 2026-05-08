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
    bfs, greedy_best_first_step, astar, bfs_nearest, 
    has_line_of_sight, has_soft_los, manhattan
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
        self.spawn_pos      = (x, y)
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
            self.x, self.y = self.spawn_pos
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

        # Recompute BFS path to EAGLE
        if not self._path or self._bfs_timer <= 0:
            result = bfs(grid, self.pos(), eagle_pos)
            self._path, self._nodes_searched = result if result else ([], 0)
            self._bfs_timer = BFS_REPLAN_TICKS

        # Rule 1: Shoot if player aligned (Simple Reflex)
        should_fire = False
        px, py = player_pos
        if self.x == px or self.y == py:
            if has_soft_los(grid, self.pos(), player_pos):
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
            if 0<=nx<GRID_SIZE and 0<=ny<GRID_SIZE and grid[ny][nx] in (BRICK, EAGLE):
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
        self._memory = []  # Last 8 tiles visited to break loops

    def update(self, grid, player_pos, eagle_pos):
        self.tick_timers()
        bullet = None

        # 1. Greedy Decision (Use breadcrumb memory to avoid loops)
        next_tile, nodes = greedy_best_first_step(grid, self.pos(), eagle_pos, self._memory)
        self._nodes_searched = nodes

        # Update memory (keep last 8 positions)
        self._memory.append(self.pos())
        if len(self._memory) > 8:
            self._memory.pop(0)

        # Detect stuck (no movement)
        if self._last_pos == self.pos():
            self._stuck_counter += 1
        else:
            self._stuck_counter = 0
        
        # Update last position after check
        old_pos = self.pos()
        
        should_fire = False
        move_dir = None

        if next_tile:
            tx, ty = next_tile
            move_dir = (tx - self.x, ty - self.y)

            # Rule: shoot brick or eagle in path (never detour!)
            # If we see a target, we LOCK this direction until it's gone
            if grid[ty][tx] in (BRICK, EAGLE):
                self.direction = move_dir
                should_fire = True
            
        # 2. Apply Decision
        if should_fire and self.can_fire():
            bullet = self.fire()
            
        if move_dir and self.can_move() and not should_fire:
            if not self.try_move(move_dir, grid):
                # If move blocked by target, shoot it
                tx, ty = self.x + move_dir[0], self.y + move_dir[1]
                if 0<=tx<GRID_SIZE and 0<=ty<GRID_SIZE and grid[ty][tx] in (BRICK, EAGLE):
                    if self.can_fire() and not bullet:
                        self.direction = move_dir
                        bullet = self.fire()

        # 3. Aggression: REMOVED (Guide says FastTank "Ignores player")
        # 4. Escape: If stuck for too long, try a random move
        if self._stuck_counter > 20:
            free = [d for d in DIRS if 0<=self.x+d[0]<GRID_SIZE
                    and 0<=self.y+d[1]<GRID_SIZE
                    and grid[self.y+d[1]][self.x+d[0]] not in (STEEL,WATER)]
            if free:
                self.try_move(random.choice(free), grid)
                self._stuck_counter = 0

        self._last_pos = old_pos
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

        # Always shoot player if in line-of-sight (Reflex)
        if has_soft_los(grid, self.pos(), player_pos):
            px, py = player_pos
            if px > self.x:   self.direction = RIGHT
            elif px < self.x: self.direction = LEFT
            elif py > self.y: self.direction = DOWN
            else:             self.direction = UP
            if self.can_fire():
                bullet = self.fire()
        
        # Also shoot Eagle if in line-of-sight
        if not bullet and has_soft_los(grid, self.pos(), eagle_pos):
            ex, ey = eagle_pos
            if ex > self.x:   self.direction = RIGHT
            elif ex < self.x: self.direction = LEFT
            elif ey > self.y: self.direction = DOWN
            else:             self.direction = UP
            if self.can_fire():
                bullet = self.fire()

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


# ─── Power Tank (Utility-Based Agent) ─────────────────────────────────────────

class PowerTank(Tank):
    """
    Utility-Based Agent: Evaluates U(s, a) for possible moves/shots.
    Utility = f(player proximity, line-of-sight, destruction potential).
    """

    def __init__(self, x, y):
        super().__init__(x, y, DOWN)
        self.hp            = 2
        self.move_interval = 4
        self.fire_interval = 30  # Shoots fast!
        self.color         = (255, 150, 0)

    def _utility(self, action, grid, player_pos, eagle_pos):
        """Simple utility function: higher score = better action."""
        # Action is (dx, dy) move or 'fire'
        if action == 'fire':
            u = 0
            # Is player in LoS? Huge utility.
            if has_soft_los(grid, self.pos(), player_pos):
                u += 100
            # Is eagle in LoS? High utility.
            if has_line_of_sight(grid, self.pos(), eagle_pos):
                u += 80
            # Is a brick in front? Medium utility.
            nx, ny = self.x + self.direction[0], self.y + self.direction[1]
            if 0<=nx<GRID_SIZE and 0<=ny<GRID_SIZE and grid[ny][nx] == BRICK:
                u += 40
            return u
        else:
            # Move utility: how much closer does it get us to the player/eagle?
            dx, dy = action
            nx, ny = self.x + dx, self.y + dy
            if not (0<=nx<GRID_SIZE and 0<=ny<GRID_SIZE) or grid[ny][nx] in (STEEL, WATER):
                return -100
            
            d_player = manhattan((nx, ny), player_pos)
            d_eagle  = manhattan((nx, ny), eagle_pos)
            # Preference: close distance to player mostly, then eagle
            return 50 - d_player - (d_eagle * 0.5)

    def update(self, grid, player_pos, eagle_pos):
        self.tick_timers()
        bullet = None

        # 1. Evaluate "Fire" utility
        if self.can_fire():
            u_fire = self._utility('fire', grid, player_pos, eagle_pos)
            if u_fire > 50: # Threshold
                bullet = self.fire()
        
        # 2. Evaluate "Move" utilities
        if self.can_move() and not bullet:
            best_move = None
            best_u = -999
            for d in DIRS:
                u = self._utility(d, grid, player_pos, eagle_pos)
                if u > best_u:
                    best_u = u
                    best_move = d
            
            if best_move:
                self.try_move(best_move, grid)

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
            self.move_interval = 8   # Slow (Original 4 doubled)
            self.fire_interval = 60  # 2.0s
            self._depth = 2
        elif self.hp >= 3:
            self._phase = 2
            self.move_interval = 6   # Medium (Original 3 doubled)
            self.fire_interval = 45  # 1.5s
            self._depth = 3
        else:
            self._phase = 3
            self.move_interval = 4   # Fast (Original 2 doubled)
            self.fire_interval = 24  # 0.8s
            self._depth = 4

    def take_hit(self):
        self.hp -= 1
        self._hit_flash = 20
        self._update_phase()
        if self.hp <= 0:
            self.alive = False
            return False
        return True

    def update(self, grid, player_pos, player_hp, eagle_pos=None):
        self.tick_timers()
        if self._hit_flash > 0:
            self._hit_flash -= 1

        self._update_phase()
        bullet = None

        # 1. Apply move (Only run Minimax when ready to move)
        if self.can_move():
            action, score = self._ai.decide(
                self.pos(), self.hp, player_pos, player_hp, grid, self._depth, eagle_pos
            )
            self.try_move(action, grid)

        # Shoot decision: if player in line-of-sight (even through bricks)
        if self.can_fire() and has_soft_los(grid, self.pos(), player_pos):
            px, py = player_pos
            if px > self.x:   self.direction = RIGHT
            elif px < self.x: self.direction = LEFT
            elif py > self.y: self.direction = DOWN
            else:             self.direction = UP
            bullet = self.fire()
        
        # Also target Eagle if player not in sight
        if not bullet and self.can_fire() and has_soft_los(grid, self.pos(), EAGLE_POS):
            ex, ey = EAGLE_POS
            if ex > self.x:   self.direction = RIGHT
            elif ex < self.x: self.direction = LEFT
            elif ey > self.y: self.direction = DOWN
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
