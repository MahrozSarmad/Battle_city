# Battle City (Tank 1990) — AL2002 AI Lab Project
## Spring 2026 | Python & Pygame Implementation

---

## 🎮 Quick Start

```bash
pip install pygame
python main.py
```

---

## 🛠️ Project Architecture

```text
battle_city/
├── main.py              # Game orchestrator, event loop, and level management
├── constants.py         # Global configuration (timing, colors, tile IDs)
├── renderer.py          # Graphics engine and UI overlays (HUD, Menus)
├── modules/
│   ├── csp_map.py       # Module A: Map Generator (Backtracking + Forward Checking)
│   ├── search.py        # Module B: Search Algorithms (BFS, Greedy, A*)
│   └── minimax.py       # Module C: Adversarial AI (Minimax + Alpha-Beta)
└── tanks/
    └── tanks.py         # Tank agent definitions and behavior state machines
```

---

## 🧠 Design Decisions

### **1. 30 FPS Synchronized Tick-Rate**
Unlike standard games that run as fast as possible, this implementation uses a strict **30 FPS tick-rate** to ensure AI decision-making is synchronized with game physics. All speeds are defined as "ticks per move," allowing us to precisely control the "intelligence vs. speed" balance across different tank phases.

### **2. Grid-Based Abstraction**
The game world is mapped to a **26×26 logical grid**. While the renderer handles smooth pixel movement, the AI agents perceive the world as discrete tiles. This allows for clean implementations of search algorithms (BFS/A*) without the overhead of continuous collision geometry.

### **3. Phase-Driven State Machines**
The **Armor Tank** and **Boss Tank** use internal state machines. 
- **Armor Tank**: Switches from "Attack" to "Retreat" based on a hit-counter.
- **Boss Tank**: Dynamically updates its search depth and speed as its HP drops, simulating an "enraged" state.

---

## 🔬 Algorithm Analysis & Comparison

This project serves as a live demonstration of the hierarchy of AI agent architectures.

| Algorithm | Agent Architecture | Cost Awareness | Goal Priority | Typical Failure Mode |
|---|---|:---:|:---:|---|
| **BFS** | Simple Reflex | No | High | Inefficient (takes long routes). |
| **Greedy** | Goal-Based | No | Absolute | Local Minima (gets stuck in U-walls). |
| **A*** | Model-Based | Yes | High | Optimal but computationally heavier. |
| **Minimax** | Adversarial | Relative | Dynamic | Computationally expensive without pruning. |

### **Search Comparison: The "Brick Wall" Test**
A key design feature of this lab is the **A* Cost Model**. 
- **BFS** treats all paths as equal; it will walk 10 tiles around a wall to reach the eagle.
- **A*** is programmed with costs: `Empty=1`, `Brick=3`. A* identifies that it is mathematically "cheaper" to spend 3 ticks shooting through a single brick than to walk 4+ tiles around it.

---

## ⚔️ Adversarial AI (Boss Level)

The final level features a **Boss Tank** running a **Minimax** algorithm with **Alpha-Beta Pruning**.

### **Alpha-Beta Performance**
The Boss calculates the best move by simulating your potential responses up to **Depth 4**. 
- **Without Pruning**: $O(b^d)$ nodes — significant lag.
- **With Alpha-Beta**: $O(b^{d/2})$ nodes — enables real-time decision making.

**Heuristic Weights used for Evaluation:**
- Player Proximity (3 tiles): **+60**
- Line-of-Sight: **+50**
- Adjacent to Steel Cover: **+30**
- Eagle Proximity: **Tie-breaker pull**

---

## 📊 Results & Observations

### **Map Generation (CSP)**
The map generator successfully uses **Constraint Satisfaction** to ensure that every generated level is:
1. **Passable**: A BFS path always exists from the player to the eagle.
2. **Fair**: No enemy can spawn within 10 tiles of the player.
3. **Safe**: The eagle is always protected by at least one layer of walls.

### **Behavioral Differences**
- **Basic Tanks** are purely reactive and easily baited into traps.
- **Fast Tanks** are deadly if left alone but can be "tricked" into getting stuck on corners due to the greedy heuristic's lack of backtracking.
- **Armor Tanks** demonstrate high intelligence by retreating behind steel walls to wait out their cooldowns after taking heavy damage.

---

## ⌨️ Controls

- **WASD / Arrow Keys**: Move Tank
- **SPACE**: Fire Bullet
- **ESC**: Pause Game / Exit to Menu
- **ENTER**: Start Game / Continue

---

*Developed for the AL2002 Artificial Intelligence Lab — Spring 2026.*
