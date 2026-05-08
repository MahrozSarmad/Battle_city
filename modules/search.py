"""
Module B — Search Algorithms

Three algorithms, three agent types:
  BFS           → Basic Tank   (Simple Reflex Agent)
  Greedy BFS    → Fast Tank    (Goal-Based Agent)
  A*            → Armor Tank   (Model-Based Reflex Agent)
"""

from collections import deque
import heapq
from constants import (
    GRID_SIZE, EMPTY, BRICK, STEEL, WATER, FOREST, EAGLE,
    ASTAR_COST, DIRS
)


def _neighbors(x, y, grid):
    """Return (nx, ny) neighbors that are not out-of-bounds."""
    for dx, dy in DIRS:
        nx, ny = x+dx, y+dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            yield nx, ny


def _passable_bfs(cell_type):
    """BFS treats brick as passable (tank will shoot through it)."""
    return cell_type not in (STEEL, WATER)


def _passable_strict(cell_type):
    """Strict passability: only empty + forest."""
    return cell_type in (EMPTY, FOREST, EAGLE)


def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


# ─── BFS ──────────────────────────────────────────────────────────────────────

def bfs(grid, start, goal):
    """
    BFS: Shortest-hop path from start to goal.
    Treats Brick tiles as passable (tank will shoot to destroy).
    Returns list of (x,y) tiles from start→goal (exclusive of start),
    or [] if no path found.

    Used by: Basic Tank (Simple Reflex Agent)
    """
    sx, sy = start
    gx, gy = goal
    if (sx, sy) == (gx, gy):
        return []

    visited  = {(sx, sy): None}
    queue    = deque([(sx, sy)])
    nodes_visited = 0

    while queue:
        x, y = queue.popleft()
        nodes_visited += 1

        if (x, y) == (gx, gy):
            # Reconstruct path
            path = []
            cur = (gx, gy)
            while cur != (sx, sy):
                path.append(cur)
                cur = visited[cur]
            path.reverse()
            return path, nodes_visited

        for nx, ny in _neighbors(x, y, grid):
            if (nx, ny) not in visited and _passable_bfs(grid[ny][nx]):
                visited[(nx, ny)] = (x, y)
                queue.append((nx, ny))

    return [], nodes_visited


# ─── Greedy Best-First Search ─────────────────────────────────────────────────

def greedy_best_first_step(grid, pos, goal, exclude_list=None):
    """
    Greedy Best-First: single-step decision.
    Returns the neighbor tile with lowest Manhattan distance to goal.
    Supports a 'memory' (exclude_list) to avoid local minima/loops.
    """
    x, y = pos
    gx, gy = goal
    nodes_visited = 0

    best_tile   = None
    best_h      = float('inf')
    
    # Ensure exclude_list is a set for O(1) lookups
    excludes = set(exclude_list) if exclude_list else set()

    for nx, ny in _neighbors(x, y, grid):
        nodes_visited += 1
        if (nx, ny) in excludes:
            continue
            
        cell = grid[ny][nx]
        if cell in (STEEL, WATER):
            continue
            
        h = manhattan((nx, ny), (gx, gy))
        if h < best_h:
            best_h    = h
            best_tile = (nx, ny)

    # Fallback: if trapped, try moving even to excluded positions (but not Steel/Water)
    if best_tile is None and excludes:
        return greedy_best_first_step(grid, pos, goal, None)

    return best_tile, nodes_visited


# ─── A* Search ────────────────────────────────────────────────────────────────

def astar(grid, start, goal):
    """
    A*: Optimal cost-aware path from start to goal.
    Uses ASTAR_COST tile weights: brick=3, steel=∞, water=∞, empty/forest=1.

    Used by: Armor Tank (Model-Based Reflex Agent)
    Key insight: A* prefers shooting through 1 brick wall (cost 3) over
                 walking 6+ empty tiles around it (cost 6+).
    """
    sx, sy = start
    gx, gy = goal
    if (sx, sy) == (gx, gy):
        return [], 0

    # (f, g, (x,y), parent)
    open_heap = []
    heapq.heappush(open_heap, (0 + manhattan(start, goal), 0, (sx, sy), None))

    came_from = {}
    g_score   = {(sx, sy): 0}
    nodes_visited = 0

    while open_heap:
        f, g, (x, y), parent = heapq.heappop(open_heap)
        nodes_visited += 1

        if (x, y) in came_from:
            continue
        came_from[(x, y)] = parent

        if (x, y) == (gx, gy):
            # Reconstruct
            path = []
            cur  = (gx, gy)
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return path[1:], nodes_visited   # exclude start

        for nx, ny in _neighbors(x, y, grid):
            if (nx, ny) in came_from:
                continue
            cell_cost = ASTAR_COST.get(grid[ny][nx], float('inf'))
            if cell_cost == float('inf'):
                continue
            new_g = g + cell_cost
            if new_g < g_score.get((nx, ny), float('inf')):
                g_score[(nx, ny)] = new_g
                h = manhattan((nx, ny), (gx, gy))
                heapq.heappush(open_heap, (new_g + h, new_g, (nx, ny), (x, y)))

    return [], nodes_visited


# ─── BFS for finding nearest tile of a given type ─────────────────────────────

def bfs_nearest(grid, start, target_types):
    """
    Find nearest tile of any type in target_types using BFS.
    Used by Armor Tank to find nearest Steel wall for retreat.
    Returns (x, y) or None.
    """
    sx, sy = start
    visited = {(sx, sy)}
    queue   = deque([(sx, sy)])

    while queue:
        x, y = queue.popleft()
        if grid[y][x] in target_types and (x, y) != (sx, sy):
            return (x, y)
        for nx, ny in _neighbors(x, y, grid):
            if (nx, ny) not in visited:
                cell = grid[ny][nx]
                if cell not in (STEEL, WATER) or cell in target_types:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
    return None


# ─── Line-of-sight check ──────────────────────────────────────────────────────

def has_line_of_sight(grid, pos_a, pos_b):
    """
    Return True if there is a clear horizontal or vertical line-of-sight
    between pos_a and pos_b (no STEEL/BRICK/WATER blocking).
    """
    ax, ay = pos_a
    bx, by = pos_b

    if ax == bx:
        for y in range(min(ay, by)+1, max(ay, by)):
            if grid[y][ax] in (STEEL, BRICK, WATER):
                return False
        return True
    elif ay == by:
        for x in range(min(ax, bx)+1, max(ax, bx)):
            if grid[ay][x] in (STEEL, BRICK, WATER):
                return False
        return True
    return False


def has_soft_los(grid, pos_a, pos_b):
    """
    Similar to line-of-sight, but ignores BRICKS.
    Used to make tanks shoot bricks to reach the player.
    """
    ax, ay = pos_a
    bx, by = pos_b

    if ax == bx:
        for y in range(min(ay, by)+1, max(ay, by)):
            if grid[y][ax] in (STEEL, WATER):
                return False
        return True
    elif ay == by:
        for x in range(min(ax, bx)+1, max(ax, bx)):
            if grid[ay][x] in (STEEL, WATER):
                return False
        return True
    return False
