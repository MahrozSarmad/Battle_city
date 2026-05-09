# """
# Module C — Adversarial Search: Minimax + Alpha-Beta Pruning

# Boss Tank uses Minimax with Alpha-Beta pruning.
# MAX node = Boss Tank (maximises heuristic)
# MIN node = Player (simulates best player response, minimises Boss heuristic)
# """

# from constants import (
#     DIRS, GRID_SIZE, STEEL, WATER, BRICK, FOREST, EAGLE, EMPTY
# )
# from modules.search import manhattan, has_line_of_sight


# # ─── Evaluation Heuristic ─────────────────────────────────────────────────────

# def evaluate_state(boss_pos, boss_hp, player_pos, player_hp, grid, eagle_pos=None):
#     """
#     Heuristic score for the Boss Tank (MAX player).
#     Strictly follows Project_Guide.md weights.
#     """
#     score = 0
#     bx, by = boss_pos
#     px, py = player_pos

#     dist = manhattan(boss_pos, player_pos)

#     # 1. Player Proximity (Manual: +60 if within 3 tiles)
#     if dist <= 3:
#         score += 60
#     else:
#         score -= dist * 2

#     # 2. Line of Sight (Manual: +50)
#     if has_line_of_sight(grid, boss_pos, player_pos):
#         score += 50

#     # 3. Steel Cover (Manual: +30)
#     near_steel = False
#     for dx, dy in DIRS:
#         nx, ny = bx+dx, by+dy
#         if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
#             if grid[ny][nx] == STEEL:
#                 near_steel = True
#                 break
#     if near_steel:
#         score += 30

#     # 4. HP Factors (Manual: Player Hit +20, Boss Hit -40)
#     score += (3 - player_hp) * 20
#     score -= (10 - boss_hp) * 40

#     # 5. Visibility (Manual: -20 if player is in forest)
#     if 0 <= px < GRID_SIZE and 0 <= py < GRID_SIZE:
#         if grid[py][px] == FOREST:
#             score -= 20

#     # 6. Eagle Attraction (Tie-breaker for purposeful movement)
#     if eagle_pos:
#         dist_to_eagle = manhattan(boss_pos, eagle_pos)
#         score -= dist_to_eagle * 3

#     return score


# # ─── State helpers ────────────────────────────────────────────────────────────

# def get_legal_moves(pos, grid):
#     """Return list of (dx,dy) directions from pos that are not blocked."""
#     x, y = pos
#     moves = []
#     for dx, dy in DIRS:
#         nx, ny = x+dx, y+dy
#         if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
#             if grid[ny][nx] not in (STEEL, WATER):
#                 moves.append((dx, dy))
#     if not moves:
#         moves = [(0, 0)]   # stay
#     return moves


# def apply_move(pos, direction):
#     x, y = pos
#     dx, dy = direction
#     return (x+dx, y+dy)


# # ─── Minimax with Alpha-Beta Pruning ──────────────────────────────────────────

# class MinimaxBoss:
#     """
#     Minimax adversarial agent for the Boss Tank.
#     Tracks performance metrics for the project report.
#     """

#     def __init__(self):
#         self.nodes_without_pruning = 0
#         self.nodes_with_pruning    = 0

#     def decide(self, boss_pos, boss_hp, player_pos, player_hp, grid, depth, eagle_pos=None):
#         """
#         Returns (best_action, score) where best_action is a (dx,dy) direction.
#         Internally runs BOTH plain minimax and alpha-beta for metric comparison.
#         """
#         # Measure plain minimax nodes (capped at depth-1 to avoid lag)
#         self.nodes_without_pruning = 0
#         self._minimax_plain(boss_pos, boss_hp, player_pos, player_hp, grid,
#                             min(depth, 2), is_max=True, eagle_pos=eagle_pos)

#         # Run full alpha-beta at real depth
#         self.nodes_with_pruning = 0
#         best_score  = float('-inf')
#         best_action = (0, 0)

#         for move in get_legal_moves(boss_pos, grid):
#             new_boss = apply_move(boss_pos, move)
#             # Clamp to grid
#             new_boss = (
#                 max(0, min(GRID_SIZE-1, new_boss[0])),
#                 max(0, min(GRID_SIZE-1, new_boss[1]))
#             )
#             score = self._alpha_beta(
#                 new_boss, boss_hp, player_pos, player_hp, grid,
#                 depth-1, float('-inf'), float('inf'), is_max=False, eagle_pos=eagle_pos
#             )
#             if score > best_score:
#                 best_score  = score
#                 best_action = move

#         return best_action, best_score

#     def speedup_ratio(self):
#         if self.nodes_with_pruning == 0:
#             return 0
#         plain = max(self.nodes_without_pruning, 1)
#         return round(plain / self.nodes_with_pruning, 2)

#     # ── Alpha-Beta ────────────────────────────────────────────────────────────

#     def _alpha_beta(self, boss_pos, boss_hp, player_pos, player_hp,
#                     grid, depth, alpha, beta, is_max, eagle_pos=None):
#         self.nodes_with_pruning += 1

#         if depth == 0 or boss_hp <= 0 or player_hp <= 0:
#             return evaluate_state(boss_pos, boss_hp, player_pos, player_hp, grid, eagle_pos)

#         if is_max:
#             value = float('-inf')
#             for move in get_legal_moves(boss_pos, grid):
#                 new_boss = apply_move(boss_pos, move)
#                 new_boss = (
#                     max(0, min(GRID_SIZE-1, new_boss[0])),
#                     max(0, min(GRID_SIZE-1, new_boss[1]))
#                 )
#                 child_val = self._alpha_beta(
#                     new_boss, boss_hp, player_pos, player_hp,
#                     grid, depth-1, alpha, beta, False, eagle_pos
#                 )
#                 value = max(value, child_val)
#                 alpha = max(alpha, value)
#                 if alpha >= beta:
#                     break   # β-cutoff (pruning)
#             return value
#         else:
#             value = float('inf')
#             for move in get_legal_moves(player_pos, grid):
#                 new_player = apply_move(player_pos, move)
#                 new_player = (
#                     max(0, min(GRID_SIZE-1, new_player[0])),
#                     max(0, min(GRID_SIZE-1, new_player[1]))
#                 )
#                 child_val = self._alpha_beta(
#                     boss_pos, boss_hp, new_player, player_hp,
#                     grid, depth-1, alpha, beta, True, eagle_pos
#                 )
#                 value = min(value, child_val)
#                 beta = min(beta, value)
#                 if alpha >= beta:
#                     break   # α-cutoff (pruning)
#             return value

#     # ── Plain Minimax (for node-count measurement only) ───────────────────────

#     def _minimax_plain(self, boss_pos, boss_hp, player_pos, player_hp,
#                        grid, depth, is_max, eagle_pos=None):
#         self.nodes_without_pruning += 1

#         if depth == 0 or boss_hp <= 0 or player_hp <= 0:
#             return evaluate_state(boss_pos, boss_hp, player_pos, player_hp, grid, eagle_pos)

#         if is_max:
#             value = float('-inf')
#             for move in get_legal_moves(boss_pos, grid):
#                 new_boss = apply_move(boss_pos, move)
#                 new_boss = (
#                     max(0, min(GRID_SIZE-1, new_boss[0])),
#                     max(0, min(GRID_SIZE-1, new_boss[1]))
#                 )
#                 value = max(value, self._minimax_plain(
#                     new_boss, boss_hp, player_pos, player_hp, grid, depth-1, False, eagle_pos
#                 ))
#             return value
#         else:
#             value = float('inf')
#             for move in get_legal_moves(player_pos, grid):
#                 new_player = apply_move(player_pos, move)
#                 new_player = (
#                     max(0, min(GRID_SIZE-1, new_player[0])),
#                     max(0, min(GRID_SIZE-1, new_player[1]))
#                 )
#                 value = min(value, self._minimax_plain(
#                     boss_pos, boss_hp, new_player, player_hp, grid, depth-1, True, eagle_pos
#                 ))
#             return value


"""
Module C — Adversarial Search: Minimax + Alpha-Beta Pruning

Boss Tank uses Minimax with Alpha-Beta pruning.
MAX node = Boss Tank (maximises heuristic)
MIN node = Player (simulates best player response, minimises Boss heuristic)
"""

from constants import (
    DIRS, GRID_SIZE, STEEL, WATER, BRICK, FOREST, EAGLE, EMPTY
)
from modules.search import manhattan, has_line_of_sight


# ─── Evaluation Heuristic ─────────────────────────────────────────────────────

def evaluate_state(boss_pos, boss_hp, player_pos, player_hp, grid, eagle_pos=None, phase=1):
    """
    Heuristic score for the Boss Tank (MAX player).
    Phase-aware — each phase has a distinct strategic priority per Project_Guide.md:

      Phase 1 (HP 10-7): Aggressive push. Close distance to player. No cover bonus.
      Phase 2 (HP 6-3):  Balanced. Cover bonus active. Moderate aggression.
      Phase 3 (HP 2-1):  Desperate rush. Maximum aggression. Ignore self-preservation.
    """
    score = 0
    bx, by = boss_pos
    px, py = player_pos

    dist = manhattan(boss_pos, player_pos)

    # ── 1. Player Proximity ───────────────────────────────────────────────────
    # Guide: +60 if within 3 tiles. This is the primary driver in all phases.
    if dist <= 3:
        score += 60
    else:
        # FIX: Scale penalty by phase aggression so the boss actively closes in.
        # Phase 1 = strongest pull toward player; Phase 3 = also strong (desperate rush).
        aggression = {1: 6, 2: 4, 3: 8}
        score -= dist * aggression.get(phase, 4)

    # ── 2. Line of Sight (Guide: +50) ────────────────────────────────────────
    if has_line_of_sight(grid, boss_pos, player_pos):
        score += 50

    # ── 3. Steel Cover (Guide: +30) — Phase 2 only ───────────────────────────
    # FIX: The guide says Phase 2 uses "cover bonus in heuristic". Phase 1 is
    # "aggressive push" and Phase 3 is "ignore self-preservation". Applying the
    # cover bonus unconditionally caused the boss to park beside steel walls in
    # Phase 1 and oscillate there instead of pursuing the player.
    if phase == 2:
        for dx, dy in DIRS:
            nx, ny = bx + dx, by + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                if grid[ny][nx] == STEEL:
                    score += 30
                    break

    # ── 4. HP Factors (Guide: Player Hit +20, Boss Hit -40) ──────────────────
    score += (3 - player_hp) * 20

    # Phase 3: "ignore self-preservation" — suppress the self-HP penalty
    if phase != 3:
        score -= (10 - boss_hp) * 40

    # ── 5. Visibility Penalty (Guide: -20 if player in forest) ───────────────
    if 0 <= px < GRID_SIZE and 0 <= py < GRID_SIZE:
        if grid[py][px] == FOREST:
            score -= 20

    # ── 6. Eagle Attraction (tie-breaker) ────────────────────────────────────
    # FIX: Reduce weight so it never overpowers the player-proximity signal.
    # Previously at *3 it competed with the distance penalty and confused Phase 1.
    if eagle_pos:
        dist_to_eagle = manhattan(boss_pos, eagle_pos)
        score -= dist_to_eagle * 1

    return score


# ─── State helpers ────────────────────────────────────────────────────────────

def get_legal_moves(pos, grid):
    """
    Return list of (dx,dy) directions the tank can actually move to.

    FIX: Previously allowed BRICK as a legal destination. The game engine's
    try_move() only permits EMPTY and FOREST, so minimax was simulating moves
    into brick tiles that the engine would refuse — making the boss appear stuck.
    BRICK is now excluded, matching actual game movement rules.
    """
    x, y = pos
    moves = []
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            cell = grid[ny][nx]
            # Match Tank.try_move(): only EMPTY and FOREST are traversable
            if cell in (EMPTY, FOREST):
                moves.append((dx, dy))
    if not moves:
        moves = [(0, 0)]   # stay in place if completely surrounded
    return moves


def apply_move(pos, direction):
    x, y = pos
    dx, dy = direction
    return (x + dx, y + dy)


# ─── Minimax with Alpha-Beta Pruning ──────────────────────────────────────────

class MinimaxBoss:
    """
    Minimax adversarial agent for the Boss Tank.
    Tracks performance metrics for the project report.
    """

    def __init__(self):
        self.nodes_without_pruning = 0
        self.nodes_with_pruning    = 0

    def decide(self, boss_pos, boss_hp, player_pos, player_hp, grid, depth, eagle_pos=None):
        """
        Returns (best_action, score) where best_action is a (dx,dy) direction.
        Internally runs BOTH plain minimax and alpha-beta for metric comparison.
        Phase is derived from boss_hp to feed the heuristic correctly.
        """
        # Derive phase from HP so the heuristic gets the right context
        phase = self._phase_from_hp(boss_hp)

        # Measure plain minimax nodes (capped at depth 2 to avoid lag)
        self.nodes_without_pruning = 0
        self._minimax_plain(boss_pos, boss_hp, player_pos, player_hp, grid,
                            min(depth, 2), is_max=True, eagle_pos=eagle_pos, phase=phase)

        # Run full alpha-beta at real depth
        self.nodes_with_pruning = 0
        best_score  = float('-inf')
        best_action = (0, 0)

        for move in get_legal_moves(boss_pos, grid):
            new_boss = apply_move(boss_pos, move)
            new_boss = (
                max(0, min(GRID_SIZE - 1, new_boss[0])),
                max(0, min(GRID_SIZE - 1, new_boss[1]))
            )
            score = self._alpha_beta(
                new_boss, boss_hp, player_pos, player_hp, grid,
                depth - 1, float('-inf'), float('inf'),
                is_max=False, eagle_pos=eagle_pos, phase=phase
            )
            if score > best_score:
                best_score  = score
                best_action = move

        return best_action, best_score

    @staticmethod
    def _phase_from_hp(boss_hp):
        if boss_hp >= 7:
            return 1
        elif boss_hp >= 3:
            return 2
        else:
            return 3

    def speedup_ratio(self):
        if self.nodes_with_pruning == 0:
            return 0
        plain = max(self.nodes_without_pruning, 1)
        return round(plain / self.nodes_with_pruning, 2)

    # ── Alpha-Beta ────────────────────────────────────────────────────────────

    def _alpha_beta(self, boss_pos, boss_hp, player_pos, player_hp,
                    grid, depth, alpha, beta, is_max, eagle_pos=None, phase=1):
        self.nodes_with_pruning += 1

        if depth == 0 or boss_hp <= 0 or player_hp <= 0:
            return evaluate_state(boss_pos, boss_hp, player_pos, player_hp,
                                  grid, eagle_pos, phase)

        if is_max:
            value = float('-inf')
            for move in get_legal_moves(boss_pos, grid):
                new_boss = apply_move(boss_pos, move)
                new_boss = (
                    max(0, min(GRID_SIZE - 1, new_boss[0])),
                    max(0, min(GRID_SIZE - 1, new_boss[1]))
                )
                child_val = self._alpha_beta(
                    new_boss, boss_hp, player_pos, player_hp,
                    grid, depth - 1, alpha, beta, False, eagle_pos, phase
                )
                value = max(value, child_val)
                alpha = max(alpha, value)
                if alpha >= beta:
                    break   # β-cutoff
            return value
        else:
            value = float('inf')
            for move in get_legal_moves(player_pos, grid):
                new_player = apply_move(player_pos, move)
                new_player = (
                    max(0, min(GRID_SIZE - 1, new_player[0])),
                    max(0, min(GRID_SIZE - 1, new_player[1]))
                )
                child_val = self._alpha_beta(
                    boss_pos, boss_hp, new_player, player_hp,
                    grid, depth - 1, alpha, beta, True, eagle_pos, phase
                )
                value = min(value, child_val)
                beta = min(beta, value)
                if alpha >= beta:
                    break   # α-cutoff
            return value

    # ── Plain Minimax (for node-count measurement only) ───────────────────────

    def _minimax_plain(self, boss_pos, boss_hp, player_pos, player_hp,
                       grid, depth, is_max, eagle_pos=None, phase=1):
        self.nodes_without_pruning += 1

        if depth == 0 or boss_hp <= 0 or player_hp <= 0:
            return evaluate_state(boss_pos, boss_hp, player_pos, player_hp,
                                  grid, eagle_pos, phase)

        if is_max:
            value = float('-inf')
            for move in get_legal_moves(boss_pos, grid):
                new_boss = apply_move(boss_pos, move)
                new_boss = (
                    max(0, min(GRID_SIZE - 1, new_boss[0])),
                    max(0, min(GRID_SIZE - 1, new_boss[1]))
                )
                value = max(value, self._minimax_plain(
                    new_boss, boss_hp, player_pos, player_hp,
                    grid, depth - 1, False, eagle_pos, phase
                ))
            return value
        else:
            value = float('inf')
            for move in get_legal_moves(player_pos, grid):
                new_player = apply_move(player_pos, move)
                new_player = (
                    max(0, min(GRID_SIZE - 1, new_player[0])),
                    max(0, min(GRID_SIZE - 1, new_player[1]))
                )
                value = min(value, self._minimax_plain(
                    boss_pos, boss_hp, new_player, player_hp,
                    grid, depth - 1, True, eagle_pos, phase
                ))
            return value