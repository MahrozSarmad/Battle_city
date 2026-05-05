"""
Module C — Adversarial Search: Minimax + Alpha-Beta Pruning
AL2002 Artificial Intelligence Lab | Spring 2026

Boss Tank uses Minimax with Alpha-Beta pruning.
MAX node = Boss Tank (maximises heuristic)
MIN node = Player (simulates best player response, minimises Boss heuristic)
"""

from constants import (
    DIRS, GRID_SIZE, STEEL, WATER, BRICK, FOREST, EAGLE, EMPTY
)
from modules.search import manhattan, has_line_of_sight


# ─── Evaluation Heuristic ─────────────────────────────────────────────────────

def evaluate_state(boss_pos, boss_hp, player_pos, player_hp, grid):
    """
    Heuristic score for the Boss Tank (MAX player).

    Factor                    Score
    Player within 3 tiles     +60
    Player in line-of-sight   +50
    Boss adjacent to steel    +30
    Player HP missing/hit     +20
    Boss HP missing (per HP)  -40
    Player in forest tile     -20
    """
    score = 0
    bx, by = boss_pos
    px, py = player_pos

    dist = manhattan(boss_pos, player_pos)

    # Proximity
    if dist <= 3:
        score += 60
    else:
        score -= dist * 2   # farther → worse

    # Line of sight
    if has_line_of_sight(grid, boss_pos, player_pos):
        score += 50

    # Boss near steel cover
    for dx, dy in DIRS:
        nx, ny = bx+dx, by+dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            if grid[ny][nx] == STEEL:
                score += 30
                break

    # Player HP damage (player health reduces from 1, treated as bool hit)
    score += (1 - player_hp) * 20

    # Boss HP cost
    score -= (10 - boss_hp) * 40

    # Player in forest → visibility penalty
    if 0 <= px < GRID_SIZE and 0 <= py < GRID_SIZE:
        if grid[py][px] == FOREST:
            score -= 20

    return score


# ─── State helpers ────────────────────────────────────────────────────────────

def get_legal_moves(pos, grid):
    """Return list of (dx,dy) directions from pos that are not blocked."""
    x, y = pos
    moves = []
    for dx, dy in DIRS:
        nx, ny = x+dx, y+dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            if grid[ny][nx] not in (STEEL, WATER):
                moves.append((dx, dy))
    if not moves:
        moves = [(0, 0)]   # stay
    return moves


def apply_move(pos, direction):
    x, y = pos
    dx, dy = direction
    return (x+dx, y+dy)


# ─── Minimax with Alpha-Beta Pruning ──────────────────────────────────────────

class MinimaxBoss:
    """
    Minimax adversarial agent for the Boss Tank.
    Tracks performance metrics for the project report.
    """

    def __init__(self):
        self.nodes_without_pruning = 0
        self.nodes_with_pruning    = 0

    def decide(self, boss_pos, boss_hp, player_pos, player_hp, grid, depth):
        """
        Returns (best_action, score) where best_action is a (dx,dy) direction.
        Internally runs BOTH plain minimax and alpha-beta for metric comparison.
        """
        # Measure plain minimax nodes (capped at depth-1 to avoid lag)
        self.nodes_without_pruning = 0
        self._minimax_plain(boss_pos, boss_hp, player_pos, player_hp, grid,
                            min(depth, 2), is_max=True)

        # Run full alpha-beta at real depth
        self.nodes_with_pruning = 0
        best_score  = float('-inf')
        best_action = (0, 0)

        for move in get_legal_moves(boss_pos, grid):
            new_boss = apply_move(boss_pos, move)
            # Clamp to grid
            new_boss = (
                max(0, min(GRID_SIZE-1, new_boss[0])),
                max(0, min(GRID_SIZE-1, new_boss[1]))
            )
            score = self._alpha_beta(
                new_boss, boss_hp, player_pos, player_hp, grid,
                depth-1, float('-inf'), float('inf'), is_max=False
            )
            if score > best_score:
                best_score  = score
                best_action = move

        return best_action, best_score

    def speedup_ratio(self):
        if self.nodes_with_pruning == 0:
            return 0
        plain = max(self.nodes_without_pruning, 1)
        return round(plain / self.nodes_with_pruning, 2)

    # ── Alpha-Beta ────────────────────────────────────────────────────────────

    def _alpha_beta(self, boss_pos, boss_hp, player_pos, player_hp,
                    grid, depth, alpha, beta, is_max):
        self.nodes_with_pruning += 1

        if depth == 0 or boss_hp <= 0 or player_hp <= 0:
            return evaluate_state(boss_pos, boss_hp, player_pos, player_hp, grid)

        if is_max:
            value = float('-inf')
            for move in get_legal_moves(boss_pos, grid):
                new_boss = apply_move(boss_pos, move)
                new_boss = (
                    max(0, min(GRID_SIZE-1, new_boss[0])),
                    max(0, min(GRID_SIZE-1, new_boss[1]))
                )
                child_val = self._alpha_beta(
                    new_boss, boss_hp, player_pos, player_hp,
                    grid, depth-1, alpha, beta, False
                )
                value = max(value, child_val)
                alpha = max(alpha, value)
                if alpha >= beta:
                    break   # β-cutoff (pruning)
            return value
        else:
            value = float('inf')
            for move in get_legal_moves(player_pos, grid):
                new_player = apply_move(player_pos, move)
                new_player = (
                    max(0, min(GRID_SIZE-1, new_player[0])),
                    max(0, min(GRID_SIZE-1, new_player[1]))
                )
                child_val = self._alpha_beta(
                    boss_pos, boss_hp, new_player, player_hp,
                    grid, depth-1, alpha, beta, True
                )
                value = min(value, child_val)
                beta = min(beta, value)
                if alpha >= beta:
                    break   # α-cutoff (pruning)
            return value

    # ── Plain Minimax (for node-count measurement only) ───────────────────────

    def _minimax_plain(self, boss_pos, boss_hp, player_pos, player_hp,
                       grid, depth, is_max):
        self.nodes_without_pruning += 1

        if depth == 0 or boss_hp <= 0 or player_hp <= 0:
            return evaluate_state(boss_pos, boss_hp, player_pos, player_hp, grid)

        if is_max:
            value = float('-inf')
            for move in get_legal_moves(boss_pos, grid):
                new_boss = apply_move(boss_pos, move)
                new_boss = (
                    max(0, min(GRID_SIZE-1, new_boss[0])),
                    max(0, min(GRID_SIZE-1, new_boss[1]))
                )
                value = max(value, self._minimax_plain(
                    new_boss, boss_hp, player_pos, player_hp, grid, depth-1, False
                ))
            return value
        else:
            value = float('inf')
            for move in get_legal_moves(player_pos, grid):
                new_player = apply_move(player_pos, move)
                new_player = (
                    max(0, min(GRID_SIZE-1, new_player[0])),
                    max(0, min(GRID_SIZE-1, new_player[1]))
                )
                value = min(value, self._minimax_plain(
                    boss_pos, boss_hp, new_player, player_hp, grid, depth-1, True
                ))
            return value
