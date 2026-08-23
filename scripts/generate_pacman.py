#!/usr/bin/env python3
"""
Pac-Man Contribution Arcade Generator

Generates an animated SVG arcade game from GitHub contribution data.
The maze, pathfinding, rendering, and collision all share one wall model.
"""
import json
import sys
import random
import math
from pathlib import Path
from datetime import date as Date
from collections import deque

# ---------------------------------------------------------------------------
# 1. LOAD & VALIDATE CONTRIBUTION DATA
# ---------------------------------------------------------------------------
INPUT = sys.argv[1]

with open(INPUT, "r", encoding="utf-8") as f:
    payload = json.load(f)

if "errors" in payload:
    sys.exit(f"Error fetching data: {json.dumps(payload['errors'], indent=2)}")
if "data" not in payload or "user" not in payload["data"] or not payload["data"]["user"]:
    sys.exit("Error: Could not parse contribution data.")

calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]

# ---------------------------------------------------------------------------
# 2. GRID CONSTANTS  (53 columns × 7 rows)
# ---------------------------------------------------------------------------
CELL = 13          # cell side length in px
GAP = 3            # gap between cells in px
STEP = CELL + GAP  # centre-to-centre distance = 16 px
LEFT = 16          # left margin (reduced — no internal title)
TOP = 10           # top margin  (reduced — no internal title)
MAX_WEEKS = len(weeks)
COLS = MAX_WEEKS
ROWS = 7
WIDTH = LEFT + COLS * STEP + 10
HEIGHT = TOP + ROWS * STEP + 30  # room for footer

DARK_BG = "#0d1117"

# ---------------------------------------------------------------------------
# 3. MAZE — single source of truth for walls
#
# walls_h: set of (col, row) meaning there is a horizontal wall on the
#          BOTTOM edge of cell (col, row), blocking movement from
#          (col, row) to (col, row+1).
# walls_v: set of (col, row) meaning there is a vertical wall on the
#          RIGHT edge of cell (col, row), blocking movement from
#          (col, row) to (col+1, row).
#
# The visual renderer and the pathfinder both consume these same sets.
# ---------------------------------------------------------------------------
def generate_walls():
    walls_v = set()
    walls_h = set()

    def mirror_v(col, row):
        """Add a vertical wall on the right edge of (col, row) and its mirror."""
        walls_v.add((col, row))
        walls_v.add((COLS - 2 - col, row))

    def mirror_h(col, row):
        """Add a horizontal wall on the bottom edge of (col, row) and its mirror."""
        walls_h.add((col, row))
        walls_h.add((COLS - 1 - col, row))

    # ── Ghost House (centre) ──────────────────────────────────────────────
    # Rectangular chamber cols 24-28, rows 2-4, doorway at col 26 top
    for c in range(24, 29):
        if c != 26:
            walls_h.add((c, 1))   # top wall (bottom edge of row 1)
    for c in range(24, 29):
        walls_h.add((c, 4))      # bottom wall
    for r in range(2, 5):
        walls_v.add((23, r))     # left wall
    for r in range(2, 5):
        walls_v.add((28, r))     # right wall

    # ── Block A: U-shape near edges (cols 2-4, rows 1-2) ─────────────────
    # Sides + bottom, open at top for reachability
    for c in range(2, 5):
        mirror_h(c, 2)           # bottom
    mirror_v(1, 1)               # left side
    mirror_v(1, 2)
    mirror_v(4, 1)               # right side
    mirror_v(4, 2)

    # ── Block B: horizontal bar (cols 7-10, bottom edge of row 0) ────────
    for c in range(7, 11):
        mirror_h(c, 0)

    # ── Block C: horizontal bar (cols 13-15, bottom edge of row 2) ───────
    for c in range(13, 16):
        mirror_h(c, 2)

    # ── Block D: vertical bar (col 7 right edge, rows 3-5) ──────────────
    for r in range(3, 6):
        mirror_v(7, r)

    # ── Block E: horizontal bar (cols 11-14, bottom edge of row 4) ───────
    for c in range(11, 15):
        mirror_h(c, 4)

    # ── Block F: T-shape near centre bottom (cols 18-20, row 4) ──────────
    for c in range(18, 21):
        mirror_h(c, 4)
    mirror_v(17, 5)

    # ── Block G: L-nub top (cols 18-20, bottom edge of row 0) ───────────
    for c in range(18, 21):
        mirror_h(c, 0)
    mirror_v(17, 0)

    # ── Block H: short vertical near ghost house (col 20, rows 2-3) ─────
    mirror_v(20, 2)
    mirror_v(20, 3)

    return walls_v, walls_h

walls_v, walls_h = generate_walls()

# ---------------------------------------------------------------------------
# 4. GRAPH — adjacency from the SAME wall sets
# ---------------------------------------------------------------------------
def get_neighbors(col, row):
    """Return walkable neighbors of (col, row) that do not cross any wall."""
    n = []
    if col > 0 and (col - 1, row) not in walls_v:
        n.append((col - 1, row))
    if col < COLS - 1 and (col, row) not in walls_v:
        n.append((col + 1, row))
    if row > 0 and (col, row - 1) not in walls_h:
        n.append((col, row - 1))
    if row < ROWS - 1 and (col, row) not in walls_h:
        n.append((col, row + 1))
    return n

def bfs_path(start, end):
    """Shortest path from start to end through walkable cells, or None."""
    if start == end:
        return [start]
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        if path[-1] == end:
            return path
        for nb in get_neighbors(*path[-1]):
            if nb not in visited:
                visited.add(nb)
                queue.append(path + [nb])
    return None

def bfs_reachable(start):
    """Return the set of all cells reachable from start."""
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nb in get_neighbors(*node):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return visited

# ---------------------------------------------------------------------------
# 5. VALIDATE maze connectivity — every cell must be reachable
# ---------------------------------------------------------------------------
reachable = bfs_reachable((0, 0))
total_cells = COLS * ROWS
if len(reachable) != total_cells:
    isolated = [(c, r) for r in range(ROWS) for c in range(COLS) if (c, r) not in reachable]
    sys.exit(f"Error: Maze has {len(isolated)} isolated cells: {isolated[:10]}...")

# ---------------------------------------------------------------------------
# 6. PARSE CONTRIBUTION DATA → coins
# ---------------------------------------------------------------------------
cells = []
for x, week in enumerate(weeks):
    for day in week["contributionDays"]:
        y_date, m, d = map(int, day["date"].split("-"))
        weekday = (Date(y_date, m, d).weekday() + 1) % 7   # Sun=0 .. Sat=6
        cells.append({
            "col": x,
            "row": weekday,
            "date": day["date"],
            "count": day["contributionCount"],
        })

coin_cells = {(c["col"], c["row"]) for c in cells if c["count"] > 0}
coin_count_map = {}
for c in cells:
    if c["count"] > 0:
        coin_count_map[(c["col"], c["row"])] = c["count"]

# ---------------------------------------------------------------------------
# 7. VALIDATE every coin is reachable
# ---------------------------------------------------------------------------
for coin in coin_cells:
    if coin not in reachable:
        sys.exit(f"Error: Contribution coin at {coin} is unreachable from (0,0).")

# ---------------------------------------------------------------------------
# 8. PAC-MAN ROUTE — greedy nearest-neighbour through BFS corridors
# ---------------------------------------------------------------------------
def bfs_closest_coins(start, unvisited):
    """BFS from start, return paths to up to 4 nearest unvisited coins."""
    queue = deque([[start]])
    visited = {start}
    found = []
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node in unvisited:
            found.append(path)
            if len(found) >= 4:
                return found
        for nb in get_neighbors(*node):
            if nb not in visited:
                visited.add(nb)
                queue.append(path + [nb])
    return found

def generate_route(coins):
    if not coins:
        return [(0, 0)]
    unvisited = set(coins)
    current = (0, 0)
    route = [(0, 0)]
    if current in unvisited:
        unvisited.remove(current)
    while unvisited:
        paths = bfs_closest_coins(current, unvisited)
        if not paths:
            sys.exit("Error: Cannot reach remaining coins from current position.")
        chosen = random.choice(paths)
        coin = chosen[-1]
        route.extend(chosen[1:])
        unvisited.remove(coin)
        current = coin
    back = bfs_path(current, (0, 0))
    if back:
        route.extend(back[1:])
    return route

route = generate_route(coin_cells)

# ---------------------------------------------------------------------------
# 9. VALIDATE route integrity
# ---------------------------------------------------------------------------
visited_coins = set()
for i, cell in enumerate(route):
    # verify every step is a valid walkable cell
    c, r = cell
    if c < 0 or c >= COLS or r < 0 or r >= ROWS:
        sys.exit(f"Error: Route step {i} is out of bounds: {cell}")
    # verify adjacency (no teleporting)
    if i > 0:
        prev = route[i - 1]
        dc, dr = abs(c - prev[0]), abs(r - prev[1])
        if dc + dr != 1 and cell != prev:
            sys.exit(f"Error: Route step {i} is not adjacent to previous: {prev} → {cell}")
        # verify no wall crossing
        if dc == 1 and dr == 0:
            wall_col = min(c, prev[0])
            if (wall_col, r) in walls_v:
                sys.exit(f"Error: Route crosses vertical wall at step {i}: {prev} → {cell}")
        if dr == 1 and dc == 0:
            wall_row = min(r, prev[1])
            if (c, wall_row) in walls_h:
                sys.exit(f"Error: Route crosses horizontal wall at step {i}: {prev} → {cell}")
    # track coin visits
    if cell in coin_cells:
        visited_coins.add(cell)

missing = coin_cells - visited_coins
if missing:
    sys.exit(f"Error: Route misses {len(missing)} coins: {list(missing)[:10]}")

# ---------------------------------------------------------------------------
# 10. TIMING — cell-based movement
# ---------------------------------------------------------------------------
SECONDS_PER_CELL = 0.12   # each cell-to-cell step takes 120 ms
TOTAL_TRAVEL = len(route) * SECONDS_PER_CELL
HOLD_SECONDS = 1.5
TOTAL_DURATION = max(1.0, TOTAL_TRAVEL + HOLD_SECONDS)

# Exact arrival time at each route step (in seconds)
step_arrival = [i * SECONDS_PER_CELL for i in range(len(route))]

# For each coin position, record the exact time Pac-Man first reaches it
coin_arrival = {}
for i, pos in enumerate(route):
    if pos in coin_cells and pos not in coin_arrival:
        coin_arrival[pos] = step_arrival[i]

# ---------------------------------------------------------------------------
# 11. COORDINATE HELPERS
# ---------------------------------------------------------------------------
def cell_centre(col, row):
    """Pixel centre of a grid cell."""
    return LEFT + col * STEP + CELL / 2, TOP + row * STEP + CELL / 2

# ---------------------------------------------------------------------------
# 12. SVG BUILDERS
# ---------------------------------------------------------------------------
def route_to_svg_path(r):
    """Convert a list of grid cells into an SVG path string."""
    if len(r) <= 1:
        cx, cy = cell_centre(*r[0]) if r else (LEFT, TOP)
        return f"M {cx:.1f} {cy:.1f}"
    pts = [cell_centre(*c) for c in r]
    parts = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
    parts.extend(f"L {px:.1f} {py:.1f}" for px, py in pts[1:])
    return " ".join(parts)

PACMAN_PATH = route_to_svg_path(route)

def pacman_svg():
    """Pac-Man with animateMotion, rotate="auto", and mouth animation."""
    # Pac-Man shape: radius 7px, fits well inside 16px corridor width
    return f"""
    <g>
      <path d="M 0 0 L 5 -5 A 7 7 0 1 0 5 5 Z" fill="#FFD93D">
        <animateMotion dur="{TOTAL_DURATION:.2f}s"
          repeatCount="indefinite"
          path="{PACMAN_PATH}"
          rotate="auto" />
        <animateTransform attributeName="transform"
          type="scale"
          values="1 1; 1 0.85; 1 1"
          dur="0.18s"
          repeatCount="indefinite"
          additive="sum" />
      </path>
    </g>"""

def ghost_svg(start, color, steps, speed_mult=1.0):
    """Ghost that wanders valid corridors and loops back to start."""
    g_route = [start]
    curr = start
    for _ in range(steps):
        nbs = get_neighbors(*curr)
        prev = g_route[-2] if len(g_route) > 1 else None
        forward = [n for n in nbs if n != prev]
        nxt = random.choice(forward) if forward else random.choice(nbs)
        g_route.append(nxt)
        curr = nxt
    back = bfs_path(curr, start)
    if back:
        g_route.extend(back[1:])
    g_path = route_to_svg_path(g_route)
    dur = len(g_route) * SECONDS_PER_CELL * speed_mult
    return f"""
    <g>
      <path d="M -6 2 C -6 -3,-3 -5,0 -5 C 3 -5,6 -3,6 2
               L 6 6 L 4 4 L 2 6 L 0 4 L -2 6 L -4 4 L -6 6 Z"
            fill="{color}">
        <animateMotion dur="{dur:.2f}s" repeatCount="indefinite" path="{g_path}" />
      </path>
      <circle cx="-2" cy="0" r="1.5" fill="white">
        <animateMotion dur="{dur:.2f}s" repeatCount="indefinite" path="{g_path}" />
      </circle>
      <circle cx="2" cy="0" r="1.5" fill="white">
        <animateMotion dur="{dur:.2f}s" repeatCount="indefinite" path="{g_path}" />
      </circle>
    </g>"""

def coin_svg(cell):
    """Gold coin with exact-arrival collection animation + sparkle."""
    if cell["count"] <= 0:
        return ""

    col, row = cell["col"], cell["row"]
    cx, cy = cell_centre(col, row)
    count = cell["count"]

    if count <= 2:
        radius, glow_r = 2.5, 0
    elif count <= 5:
        radius, glow_r = 3.5, 0
    elif count <= 9:
        radius, glow_r = 4.5, 6.5
    else:
        radius, glow_r = 5.5, 8.5

    # Exact arrival time — coin stays fully visible until Pac-Man reaches it
    arrive = coin_arrival.get((col, row), 0)
    flash_dur = 0.3  # seconds for the collection flash
    t_arrive = arrive / TOTAL_DURATION
    t_flash_end = min(1.0, (arrive + flash_dur) / TOTAL_DURATION)

    # Clamp to valid keyTimes
    t_arrive = max(0.001, min(t_arrive, 0.998))
    t_flash_end = max(t_arrive + 0.001, min(t_flash_end, 0.999))

    parts = []
    parts.append(f'<g>')
    parts.append(f'  <title>{cell["date"]}: {count} contributions</title>')

    # Opacity animation: 1 → 1 → 0 → 0 (visible until arrival, then vanish)
    parts.append(
        f'  <animate attributeName="opacity"'
        f' values="1;1;0;0"'
        f' keyTimes="0;{t_arrive:.6f};{t_flash_end:.6f};1"'
        f' dur="{TOTAL_DURATION:.2f}s"'
        f' repeatCount="indefinite" />'
    )

    if glow_r > 0:
        parts.append(
            f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{glow_r:.1f}"'
            f' fill="#FDE047" opacity="0.25" />'
        )

    parts.append(
        f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}"'
        f' fill="#FDE047" />'
    )

    # Sparkle: a tiny white flash that appears briefly exactly at collection
    sparkle_start = max(0.001, t_arrive - 0.001)
    sparkle_end = min(0.999, t_flash_end)
    parts.append(
        f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius + 1:.1f}"'
        f' fill="white" opacity="0">'
        f'    <animate attributeName="opacity"'
        f' values="0;0;0.6;0"'
        f' keyTimes="0;{sparkle_start:.6f};{t_arrive:.6f};{sparkle_end:.6f}"'
        f' dur="{TOTAL_DURATION:.2f}s"'
        f' repeatCount="indefinite" />'
        f'    <animate attributeName="r"'
        f' values="{radius:.1f};{radius:.1f};{radius + 3:.1f};{radius + 4:.1f}"'
        f' keyTimes="0;{sparkle_start:.6f};{t_arrive:.6f};{sparkle_end:.6f}"'
        f' dur="{TOTAL_DURATION:.2f}s"'
        f' repeatCount="indefinite" />'
        f'  </circle>'
    )

    parts.append('</g>')
    return "\n    ".join(parts)

def wall_svg():
    """Render neon maze walls from the canonical wall sets."""
    parts = []

    for (col, row) in walls_h:
        # Horizontal wall on bottom edge of (col, row)
        y_line = TOP + (row + 1) * STEP - STEP + CELL + GAP / 2
        x_start = LEFT + col * STEP - GAP / 2
        x_end = LEFT + col * STEP + CELL + GAP / 2
        parts.append(
            f'<line x1="{x_start:.1f}" y1="{y_line:.1f}"'
            f' x2="{x_end:.1f}" y2="{y_line:.1f}"'
            f' stroke="#0284c7" stroke-width="4"'
            f' stroke-linecap="round" opacity="0.45" />'
        )
        parts.append(
            f'<line x1="{x_start:.1f}" y1="{y_line:.1f}"'
            f' x2="{x_end:.1f}" y2="{y_line:.1f}"'
            f' stroke="#38bdf8" stroke-width="1.5"'
            f' stroke-linecap="round" />'
        )

    for (col, row) in walls_v:
        # Vertical wall on right edge of (col, row)
        x_line = LEFT + (col + 1) * STEP - GAP / 2
        y_start = TOP + row * STEP - GAP / 2
        y_end = TOP + row * STEP + CELL + GAP / 2
        parts.append(
            f'<line x1="{x_line:.1f}" y1="{y_start:.1f}"'
            f' x2="{x_line:.1f}" y2="{y_end:.1f}"'
            f' stroke="#0284c7" stroke-width="4"'
            f' stroke-linecap="round" opacity="0.45" />'
        )
        parts.append(
            f'<line x1="{x_line:.1f}" y1="{y_start:.1f}"'
            f' x2="{x_line:.1f}" y2="{y_end:.1f}"'
            f' stroke="#38bdf8" stroke-width="1.5"'
            f' stroke-linecap="round" />'
        )

    return "\n    ".join(parts)

def create_svg():
    """Assemble the full SVG document."""
    parts = []

    # SVG header — NO internal title
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{WIDTH}" height="{HEIGHT}"'
        f' viewBox="0 0 {WIDTH} {HEIGHT}">'
    )
    parts.append(f'  <rect width="100%" height="100%" fill="{DARK_BG}" rx="12" />')

    # Coins (drawn first so walls and characters render on top)
    for cell in cells:
        svg = coin_svg(cell)
        if svg:
            parts.append(f"    {svg}")

    # Maze walls
    parts.append(f"    {wall_svg()}")

    # Pac-Man
    parts.append(f"    {pacman_svg()}")

    # Ghosts — 4 distinct colours
    ghosts = [
        {"start": (25, 3), "color": "#ff3b30", "steps": 80, "speed": 1.1},
        {"start": (26, 3), "color": "#ff6bcb", "steps": 90, "speed": 1.3},
        {"start": (27, 3), "color": "#00c7ff", "steps": 100, "speed": 1.2},
        {"start": (10, 3), "color": "#ff9500", "steps": 110, "speed": 1.4},
    ]
    for g in ghosts:
        parts.append(f"    {ghost_svg(g['start'], g['color'], g['steps'], g['speed'])}")

    # Footer
    parts.append(
        f'  <text x="{WIDTH / 2}" y="{HEIGHT - 8}"'
        f' text-anchor="middle"'
        f' font-family="Arial, Helvetica, sans-serif"'
        f' font-size="11" font-style="italic" font-weight="700"'
        f' fill="#8b949e">Every contribution leaves a mark.</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# 13. GENERATE & FINAL VALIDATION
# ---------------------------------------------------------------------------
svg_content = create_svg()

# Validate no GitHub green contribution colours leaked in
GREEN_COLOURS = ["#216e39", "#30a14e", "#40c463", "#9be9a8",
                 "#0e4429", "#006d32", "#26a641", "#39d353"]
for gc in GREEN_COLOURS:
    if gc.lower() in svg_content.lower():
        sys.exit(f"Error: GitHub green colour {gc} found in SVG output.")

# Validate SVG is non-empty and well-formed
if not svg_content.strip().startswith("<svg"):
    sys.exit("Error: Generated SVG does not start with <svg>.")
if not svg_content.strip().endswith("</svg>"):
    sys.exit("Error: Generated SVG does not end with </svg>.")

# Write output
Path("/tmp").mkdir(exist_ok=True)
with open("/tmp/pacman-contribution-graph.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)
with open("/tmp/pacman-contribution-graph-dark.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)

print(f"Generated successfully. Route: {len(route)} steps, "
      f"Coins: {len(coin_cells)}, Duration: {TOTAL_DURATION:.1f}s, "
      f"Walls: {len(walls_v)}v + {len(walls_h)}h")
