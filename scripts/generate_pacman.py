import json
import sys
import random
from pathlib import Path
from datetime import date as Date
from collections import deque

INPUT = sys.argv[1]

with open(INPUT, "r", encoding="utf-8") as f:
    payload = json.load(f)

if "errors" in payload:
    sys.exit(f"Error fetching data: {json.dumps(payload['errors'], indent=2)}")

if "data" not in payload or "user" not in payload["data"] or not payload["data"]["user"]:
    sys.exit("Error: Could not parse contribution data.")

calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]

CELL = 13
GAP = 3
STEP = CELL + GAP
LEFT = 40
TOP = 58
MAX_WEEKS = len(weeks)
WIDTH = LEFT + MAX_WEEKS * STEP + 20
HEIGHT = TOP + 7 * STEP + 55

DARK_BG = "#0d1117"

# --- INTENTIONAL ARCADE MAZE DESIGN ---
def generate_walls():
    walls_v = set()
    walls_h = set()

    def mirror(x, y, is_h=False):
        if is_h:
            walls_h.add((x, y))
            walls_h.add((52 - x, y))
        else:
            walls_v.add((x, y))
            walls_v.add((51 - x, y))
            
    # Ghost House (Central Chamber)
    for x in range(24, 29): walls_h.add((x, 1))
    for x in range(24, 29): walls_h.add((x, 4))
    for y in range(2, 4): walls_v.add((23, y))
    walls_v.add((23, 4)) 
    for y in range(2, 4): walls_v.add((28, y))
    walls_v.add((28, 4))
    # Doorway to ghost house
    walls_h.remove((26, 1))
    
    # Symmetrical Arcade Blocks, Corridors, and Dead Ends
    for x in range(2, 6): mirror(x, 1, True)
    for x in range(2, 6): mirror(x, 5, True)
    for y in range(2, 5): mirror(3, y, False)
    
    for x in range(8, 12): mirror(x, 1, True)
    for y in range(2, 4): mirror(8, y, False)
    
    for x in range(14, 18): mirror(x, 4, True)
    for x in range(14, 18): mirror(x, 5, True)
    mirror(13, 5, False)
    mirror(17, 5, False)
    
    for x in range(20, 23): mirror(x, 1, True)
    for x in range(20, 23): mirror(x, 5, True)
    mirror(20, 2, False)
    mirror(20, 4, False)

    return walls_v, walls_h

walls_v, walls_h = generate_walls()

def get_neighbors(x, y):
    n = []
    if x > 0 and (x-1, y) not in walls_v: n.append((x-1, y))
    if x < 52 and (x, y) not in walls_v: n.append((x+1, y))
    if y > 0 and (x, y-1) not in walls_h: n.append((x, y-1))
    if y < 6 and (x, y) not in walls_h: n.append((x, y+1))
    return n

def bfs_path(start, end):
    if start == end: return [start]
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        if path[-1] == end:
            return path
        for n in get_neighbors(*path[-1]):
            if n not in visited:
                visited.add(n)
                queue.append(path + [n])
    return None

def bfs_closest_coins(start, unvisited_coins):
    queue = deque([[start]])
    visited = {start}
    found_paths = []
    
    while queue:
        path = queue.popleft()
        node = path[-1]
        
        if node in unvisited_coins:
            found_paths.append(path)
            if len(found_paths) >= 4:
                return found_paths
                
        for n in get_neighbors(*node):
            if n not in visited:
                visited.add(n)
                queue.append(path + [n])
                
    return found_paths

# Cells & Coins parsing
cells = []
for x, week in enumerate(weeks):
    for day in week["contributionDays"]:
        y, m, d = map(int, day["date"].split("-"))
        weekday = (Date(y, m, d).weekday() + 1) % 7
        cells.append({
            "x": x,
            "y": weekday,
            "date": day["date"],
            "count": day["contributionCount"]
        })

coin_cells = {(c["x"], c["y"]) for c in cells if c["count"] > 0}

# Validate Reachability Requirement
for coin in coin_cells:
    if not bfs_path((0, 0), coin):
        sys.exit(f"Error: Contribution coin at {coin} is mathematically unreachable from start (0,0).")

# Pac-Man Route Generation (Ensures EVERY coin is consumed using actual corridors)
def generate_pacman_route(coins_set):
    if not coins_set:
        return [(0,0)]
    
    unvisited = set(coins_set)
    current = (0,0)
    route = [(0,0)]
    
    if current in unvisited:
        unvisited.remove(current)
        
    while unvisited:
        paths = bfs_closest_coins(current, unvisited)
        if not paths:
            sys.exit("Error: Could not find path to remaining coins despite reachability validation.")
        
        chosen_path = random.choice(paths)
        best_coin = chosen_path[-1]
        route.extend(chosen_path[1:])
        unvisited.remove(best_coin)
        current = best_coin
        
    back_path = bfs_path(current, (0,0))
    if back_path:
        route.extend(back_path[1:])
        
    return route

route = generate_pacman_route(coin_cells)

# Dynamic Pacing (Target 75 seconds total)
TARGET_DURATION = 75.0 
SECONDS_PER_CELL = TARGET_DURATION / max(1, len(route))
TOTAL_TRAVEL = len(route) * SECONDS_PER_CELL
HOLD_SECONDS = 1.5
TOTAL_DURATION = max(1.0, TOTAL_TRAVEL + HOLD_SECONDS)

arrival_time = {}
for index, position in enumerate(route):
    if position not in arrival_time:
        arrival_time[position] = index * SECONDS_PER_CELL

# SVG Generation functions
def point_for(x, y):
    return LEFT + x * STEP + CELL / 2, TOP + y * STEP + CELL / 2

def route_path(r):
    if len(r) <= 1: return "M 0 0"
    points = [point_for(x, y) for x, y in r]
    commands = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    commands.extend(f"L {px:.1f} {py:.1f}" for px, py in points[1:])
    return " ".join(commands)

PACMAN_PATH = route_path(route)

def ghost_svg(start_pos, color, steps, dur_multiplier=1.0):
    g_route = [start_pos]
    curr = start_pos
    for _ in range(steps):
        neighbors = get_neighbors(*curr)
        prev = g_route[-2] if len(g_route) > 1 else None
        unvisited = [n for n in neighbors if n != prev]
        next_step = random.choice(unvisited) if unvisited else random.choice(neighbors)
        g_route.append(next_step)
        curr = next_step
        
    back = bfs_path(curr, start_pos)
    if back:
        g_route.extend(back[1:])
        
    g_path = route_path(g_route)
    dur = len(g_route) * SECONDS_PER_CELL * dur_multiplier
    
    return f"""
    <g>
      <path d="M -6 2 C -6 -3, -3 -5, 0 -5 C 3 -5, 6 -3, 6 2 L 6 6 L 4 4 L 2 6 L 0 4 L -2 6 L -4 4 L -6 6 Z" fill="{color}">
        <animateMotion dur="{dur:.2f}s" repeatCount="indefinite" path="{g_path}" />
      </path>
      <circle cx="-2" cy="0" r="1.5" fill="white"><animateMotion dur="{dur:.2f}s" repeatCount="indefinite" path="{g_path}" /></circle>
      <circle cx="2" cy="0" r="1.5" fill="white"><animateMotion dur="{dur:.2f}s" repeatCount="indefinite" path="{g_path}" /></circle>
    </g>
    """

def pacman_svg():
    return f"""
    <g>
      <path d="M 0 0 L 5 -5 A 7 7 0 1 0 5 5 Z" fill="#FFD93D">
        <animateMotion dur="{TOTAL_DURATION:.2f}s" repeatCount="indefinite" path="{PACMAN_PATH}" rotate="auto"/>
        <animateTransform attributeName="transform" type="scale" values="1 1; 1 0.85; 1 1" dur="0.16s" repeatCount="indefinite" additive="sum"/>
      </path>
    </g>
    """

def dot_svg(cell):
    if cell["count"] <= 0: return ""

    px, py = LEFT + cell["x"] * STEP, TOP + cell["y"] * STEP
    cx, cy = px + CELL / 2, py + CELL / 2

    t = arrival_time.get((cell["x"], cell["y"]), 0)
    consume_at = max(0.01, t + SECONDS_PER_CELL * 0.35)
    consume_key = consume_at / TOTAL_DURATION
    disappear_key = min(1, (consume_at + 0.12) / TOTAL_DURATION)

    # Size based on intensity
    if cell["count"] <= 2: radius = 2.5
    elif cell["count"] <= 5: radius = 3.5
    elif cell["count"] <= 9: radius = 4.5
    else: radius = 5.5

    glow = f'<circle cx="{cx}" cy="{cy}" r="{radius+2.5}" fill="#FDE047" opacity="0.3" />' if cell["count"] > 5 else ""

    return f"""
    <g>
      <title>{cell["date"]}: {cell["count"]} contributions</title>
      <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{consume_key:.6f};{disappear_key:.6f};1" dur="{TOTAL_DURATION:.2f}s" repeatCount="indefinite"/>
      {glow}
      <circle cx="{cx}" cy="{cy}" r="{radius}" fill="#FDE047" />
    </g>
    """

def create_svg():
    parts = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
      <rect width="100%" height="100%" fill="{DARK_BG}" rx="12"/>
      <text x="{WIDTH / 2}" y="27" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="#c9d1d9">Contribution Arcade</text>
    """]

    # Only draw coins. No green squares!
    for cell in cells:
        parts.append(dot_svg(cell))

    # Draw rounded neon walls
    for (x, y) in walls_h:
        y_line = TOP + y * STEP - GAP/2
        x_start = LEFT + x * STEP - GAP/2
        x_end = LEFT + x * STEP + CELL + GAP/2
        parts.append(f'<line x1="{x_start}" y1="{y_line}" x2="{x_end}" y2="{y_line}" stroke="#0284c7" stroke-width="4" stroke-linecap="round" opacity="0.5"/>')
        parts.append(f'<line x1="{x_start}" y1="{y_line}" x2="{x_end}" y2="{y_line}" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round" />')

    for (x, y) in walls_v:
        x_line = LEFT + (x + 1) * STEP - GAP/2
        y_start = TOP + y * STEP - GAP/2
        y_end = TOP + y * STEP + CELL + GAP/2
        parts.append(f'<line x1="{x_line}" y1="{y_start}" x2="{x_line}" y2="{y_end}" stroke="#0284c7" stroke-width="4" stroke-linecap="round" opacity="0.5"/>')
        parts.append(f'<line x1="{x_line}" y1="{y_start}" x2="{x_line}" y2="{y_end}" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round" />')

    parts.append(pacman_svg())

    # 4 distinct ghosts
    ghosts = [
        {"start": (25, 3), "color": "#ff3b30", "steps": 60, "dur": 1.1}, # Blinky (Red)
        {"start": (26, 3), "color": "#ff6bcb", "steps": 75, "dur": 1.3}, # Pinky (Pink)
        {"start": (27, 3), "color": "#00c7ff", "steps": 80, "dur": 1.2}, # Inky (Cyan)
        {"start": (10, 3), "color": "#ff9500", "steps": 90, "dur": 1.4}  # Clyde (Orange)
    ]
    for g in ghosts:
        parts.append(ghost_svg(g["start"], g["color"], g["steps"], g["dur"]))

    parts.append(f'<text x="{WIDTH / 2}" y="{HEIGHT - 16}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="11" font-style="italic" font-weight="700" fill="#8b949e">Every contribution leaves a mark.</text></svg>')
    return "\n".join(parts)

Path("/tmp").mkdir(exist_ok=True)
svg_content = create_svg()

with open("/tmp/pacman-contribution-graph.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)
with open("/tmp/pacman-contribution-graph-dark.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)

print("Game generated and mathematically validated successfully!")
