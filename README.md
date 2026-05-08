<<<<<<< HEAD
# Battle_city
=======
# Battle City (Tank 1990) — AL2002 AI Lab Project
## Spring 2026 | Python Implementation

---

## Quick Start

```bash
pip install pygame
python main.py
```

---

## Project Structure

```
battle_city/
├── main.py              # Game loop & entry point
├── constants.py         # All constants, tile IDs, colors, timing
├── renderer.py          # Pygame rendering (grid, tanks, bullets, HUD)
├── requirements.txt
├── modules/
│   ├── csp_map.py       # Module A — CSP Map Generator
│   ├── search.py        # Module B — BFS, Greedy Best-First, A*
│   └── minimax.py       # Module C — Minimax + Alpha-Beta Pruning
└── tanks/
    └── tanks.py         # All tank classes (Player, Basic, Fast, Armor, Boss)
```

---

## AI Modules

### Module A — CSP Map Generator (`modules/csp_map.py`)

Generates valid 26×26 maps using **backtracking + forward checking**.

| Constraint | Description |
|---|---|
| Base Safety | Eagle surrounded by ≥1 ring of Brick/Steel |
| Reachability | BFS path from every spawn → Eagle exists |
| Fairness | No spawn within 10 tiles of player |
| Density | ≤ 40% wall tiles |
| Water Safety | Water cannot block the only path to Eagle |

**Level configs:**
- Level 1: Dense brick maze, sparse steel
- Level 2: Mixed brick + steel fortress
- Boss: Small fixed arena

---

### Module B — Search Algorithms (`modules/search.py`)

| Algorithm | Tank | Agent Model | Behaviour |
|---|---|---|---|
| BFS | BasicTank | Simple Reflex | Shortest-hop path. Equal-cost tiles. Predictable. |
| Greedy Best-First | FastTank | Goal-Based | Rushes via Manhattan heuristic. Can get stuck. |
| A* | ArmorTank | Model-Based Reflex | Cost-aware. Shoots through brick (cost 3) vs. long detour (cost 6+). |

**Key demonstration:** Place a 1-tile-wide brick wall in front of all three tank types:
- BFS → takes the long way around (ignores cost)
- Greedy → may get stuck (local minima — intentional)
- A* → shoots through the wall (cheaper than detour)

---

### Module C — Adversarial Search (`modules/minimax.py`)

Boss Tank uses **Minimax with Alpha-Beta Pruning**.

| Phase | HP | Depth | Behaviour |
|---|---|---|---|
| Phase 1 | 10–7 | 2 | Aggressive push |
| Phase 2 | 6–3 | 3 | Attack + seek cover |
| Phase 3 | 2–1 | 4 | Desperate all-out rush |

**Heuristic factors:**
- Player within 3 tiles: **+60**
- Player in line-of-sight: **+50**
- Boss adjacent to steel: **+30**
- Player HP missing: **+20/hit**
- Boss HP missing: **-40/hit**
- Player in forest: **-20**

**Alpha-Beta speedup:** Reduces O(5⁴)=625 nodes → ~O(5²)=25 nodes at depth 4.
The HUD displays real-time node counts and speedup ratio for your report.

---

## Tank Types

| Tank | HP | Speed | Fire Rate | Algorithm |
|---|---|---|---|---|
| Basic | 1 | Slow | 3s | BFS |
| Fast | 1 | Fast | 1.5s | Greedy Best-First |
| Armor | 4 | Medium | 2s | A* (retreats on 3rd hit) |
| Boss | 10 | Variable | Variable | Minimax + Alpha-Beta |

---

## Controls

| Key | Action |
|---|---|
| WASD / Arrow Keys | Move |
| SPACE | Fire |
| ENTER | Start / Restart |
| ESC | Quit |

---

## Win / Lose Conditions

- **Win Level**: Destroy all 20 enemies → advance to next level
- **Win Game**: Defeat Boss Tank
- **Lose A**: Player runs out of lives
- **Lose B**: Any bullet hits the Eagle (base)

---

## Report Notes

For your project report, the HUD displays live Minimax statistics:
- Nodes evaluated **without** Alpha-Beta pruning
- Nodes evaluated **with** Alpha-Beta pruning
- Speedup ratio

These update in real-time during the Boss level. Screenshot or log them for your analysis section.

---

