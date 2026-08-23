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
    raise SystemExit(json.dumps(payload["errors"], indent=2))

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

LIGHT_COLORS = ["#161b22", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
DARK_COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

SECONDS_PER_CELL = 0.20 # Slowed down Pac-Man to make it look relaxed
HOLD_SECONDS = 1.5

# --- ORGANIC RANDOM MAZE GENERATOR ---
def generate_organic_walls(max_weeks=53, rows=7):
    walls_v = set()
    walls_h = set()
    
    all_walls = []
    for y in range(rows):
        for x in range(max_weeks - 1):
            all_walls.append(('v', x, y))
    for y in range(rows - 1):
        for x in range(max_weeks):
            all_walls.append(('h', x, y))
            
    # Seed by today's date so the maze changes uniquely every day!
    random.seed(Date.today().toordinal())
    random.shuffle(all_walls)
    
    parent = {}
    def find(i):
        if parent[i] == i: return i
        parent[i] = find(parent[i])
        return parent[i]
    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j
            return True
        return False
        
    for y in range(rows):
        for x in range(max_weeks):
            parent[(x, y)] = (x, y)
            
    final_walls = []
    for w in all_walls:
        w_type, x, y = w
        if w_type == 'v':
            c1, c2 = (x, y), (x+1, y)
        else:
            c1, c2 = (x, y), (x, y+1)
            
        if union(c1, c2):
            pass # Keep open to guarantee all cells are reachable
        else:
            # 22% chance to keep a wall to make it sparse and open
            if random.random() < 0.22:
                final_walls.append(w)
                
    for w in final_walls:
        if w[0] == 'v': walls_v.add((w[1], w[2]))
        else: walls_h.add((w[1], w[2]))
        
    return walls_v, walls_h

walls_v, walls_h = generate_organic_walls(MAX_WEEKS, 7)

def get_neighbors(x, y):
    n = []
    if x > 0 and (x-1, y) not in walls_v: n.append((x-1, y))
    if x < 52 and (x, y) not in walls_v: n.append((x+1, y))
    if y > 0 and (x, y-1) not in walls_h: n.append((x, y-1))
    if y < 6 and (x, y) not in walls_h: n.append((x, y+1))
    return n

def bfs_closest_coins(start, unvisited_coins):
    queue = deque([[start]])
    visited = set([start])
    found_paths = []
    
    while queue:
        path = queue.popleft()
        x, y = path[-1]
        
        if (x, y) in unvisited_coins:
            found_paths.append(path)
            if len(found_paths) >= 4: # Increased randomness choice
                return found_paths
                
        for n in get_neighbors(x, y):
            if n not in visited:
                visited.add(n)
                queue.append(path + [n])
                
    return found_paths

def bfs_path(start, end):
    if start == end: return [start]
    queue = deque([[start]])
    visited = set([start])
    while queue:
        path = queue.popleft()
        if path[-1] == end:
            return path
        for n in get_neighbors(*path[-1]):
            if n not in visited:
                visited.add(n)
                queue.append(path + [n])
    return None

def generate_pacman_route(coins):
    if not coins:
        return [(0,0)]
    
    unvisited_coins = set(coins)
    current = (0,0)
    route = [(0,0)]
    
    if current in unvisited_coins:
        unvisited_coins.remove(current)
        
    while unvisited_coins:
        paths = bfs_closest_coins(current, unvisited_coins)
        if not paths:
            break
        
        # Pick randomly from closest coins for erratic, hunting movement
        chosen_path = random.choice(paths)
        
        best_coin = chosen_path[-1]
        route.extend(chosen_path[1:])
        unvisited_coins.remove(best_coin)
        current = best_coin
        
    back_path = bfs_path(current, (0,0))
    if back_path:
        route.extend(back_path[1:])
        
    return route

def generate_ghost_route(start, steps=60):
    route = [start]
    curr = start
    for _ in range(steps):
        neighbors = get_neighbors(*curr)
        prev = route[-2] if len(route) > 1 else None
        unvisited = [n for n in neighbors if n != prev]
        
        if unvisited:
            next_step = random.choice(unvisited)
        else:
            next_step = random.choice(neighbors)
            
        route.append(next_step)
        curr = next_step
        
    back_path = bfs_path(curr, start)
    if back_path:
        route.extend(back_path[1:])
    return route

def escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))

def level_from_count(count):
    if count <= 0: return 0
    if count <= 2: return 1
    if count <= 5: return 2
    if count <= 9: return 3
    return 4

def month_labels():
    labels = []
    previous_month = None
    months = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    }
    for x, week in enumerate(weeks):
        if not week["contributionDays"]: continue
        date_text = week["contributionDays"][0]["date"]
        month = date_text[:7]
        if month != previous_month:
            labels.append((x, months.get(date_text[5:7], date_text[5:7])))
            previous_month = month
    return labels

cells = []
for x, week in enumerate(weeks):
    for day in week["contributionDays"]:
        y, m, d = map(int, day["date"].split("-"))
        weekday = (Date(y, m, d).weekday() + 1) % 7
        cells.append({
            "x": x,
            "y": weekday,
            "date": day["date"],
            "count": day["contributionCount"],
            "level": level_from_count(day["contributionCount"]),
        })

coin_cells = [(c["x"], c["y"]) for c in cells if c["count"] > 0]
route = generate_pacman_route(coin_cells)

arrival_time = {}
for index, position in enumerate(route):
    if position not in arrival_time:
        arrival_time[position] = index * SECONDS_PER_CELL

TOTAL_TRAVEL = len(route) * SECONDS_PER_CELL
TOTAL_DURATION = max(1.0, TOTAL_TRAVEL + HOLD_SECONDS)

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
    g_route = generate_ghost_route(start_pos, steps)
    g_path = route_path(g_route)
    dur = len(g_route) * SECONDS_PER_CELL * dur_multiplier
    
    return f"""
    <g>
      <path d="
        M -6 2
        C -6 -3, -3 -5, 0 -5
        C 3 -5, 6 -3, 6 2
        L 6 6 L 4 4
        L 2 6 L 0 4
        L -2 6 L -4 4
        L -6 6 Z"
        fill="{color}">
        <animateMotion dur="{dur:.2f}s"
          repeatCount="indefinite"
          path="{g_path}" />
      </path>
      <circle cx="-2" cy="0" r="1.5" fill="white">
        <animateMotion dur="{dur:.2f}s" repeatCount="indefinite" path="{g_path}" />
      </circle>
      <circle cx="2" cy="0" r="1.5" fill="white">
        <animateMotion dur="{dur:.2f}s" repeatCount="indefinite" path="{g_path}" />
      </circle>
    </g>
    """

def pacman_svg():
    return f"""
    <g>
      <path d="M 0 0 L 5 -5 A 7 7 0 1 0 5 5 Z" fill="#FFD93D">
        <animateMotion dur="{TOTAL_DURATION:.2f}s"
          repeatCount="indefinite"
          path="{PACMAN_PATH}"
          rotate="auto"/>
        <animateTransform attributeName="transform"
          type="scale"
          values="1 1; 1 0.85; 1 1"
          dur="0.16s"
          repeatCount="indefinite"
          additive="sum"/>
      </path>
    </g>
    """

def dot_svg(cell, dark):
    px = LEFT + cell["x"] * STEP
    py = TOP + cell["y"] * STEP
    cx = px + CELL / 2
    cy = py + CELL / 2

    bg_fill = DARK_COLORS[0] if dark else LIGHT_COLORS[0]
    result = f'<rect x="{px}" y="{py}" width="{CELL}" height="{CELL}" rx="3" fill="{bg_fill}"/>\n'

    if cell["count"] <= 0:
        return result

    t = arrival_time.get((cell["x"], cell["y"]), 0)
    consume_at = max(0.01, t + SECONDS_PER_CELL * 0.35)
    consume_key = consume_at / TOTAL_DURATION
    disappear_key = min(1, (consume_at + 0.12) / TOTAL_DURATION)

    coin_color = "#FDE047"
    glow = ""
    if cell["level"] == 1: radius = 2.5
    elif cell["level"] == 2: radius = 3.5
    elif cell["level"] == 3: radius = 4.5
    else:
        radius = 5.5
        glow = f'<circle cx="{cx}" cy="{cy}" r="8" fill="#FDE047" opacity="0.4" />'

    result += f"""
    <g>
      <title>{escape(cell["date"])}: {cell["count"]} contributions</title>
      <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{consume_key:.6f};{disappear_key:.6f};1" dur="{TOTAL_DURATION:.2f}s" repeatCount="indefinite"/>
      {glow}
      <circle cx="{cx}" cy="{cy}" r="{radius}" fill="{coin_color}" />
    </g>
    """
    return result

def create_svg(dark=False):
    text_color = "#c9d1d9"
    
    parts = [f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
      <rect width="100%" height="100%" fill="#0d1117" rx="12"/>
      <text x="{WIDTH / 2}" y="27" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="{text_color}">Contribution Arcade</text>
    """]

    for x, label in month_labels():
        px = LEFT + x * STEP
        parts.append(f'<text x="{px}" y="45" font-family="Arial, Helvetica, sans-serif" font-size="8" fill="#8b949e">{escape(label)}</text>')

    for y, label in {0: "Mon", 2: "Wed", 4: "Fri"}.items():
        py = TOP + y * STEP + 9
        parts.append(f'<text x="2" y="{py}" font-family="Arial, Helvetica, sans-serif" font-size="8" fill="#8b949e">{label}</text>')

    for cell in cells:
        parts.append(dot_svg(cell, dark))

    for (x, y) in walls_h:
        y_line = TOP + y * STEP - GAP/2
        x_start = LEFT + x * STEP - GAP/2
        x_end = LEFT + x * STEP + CELL + GAP/2
        parts.append(f'<line x1="{x_start}" y1="{y_line}" x2="{x_end}" y2="{y_line}" stroke="#0284c7" stroke-width="3" stroke-linecap="round" opacity="0.5"/>')
        parts.append(f'<line x1="{x_start}" y1="{y_line}" x2="{x_end}" y2="{y_line}" stroke="#38bdf8" stroke-width="1.2" stroke-linecap="round" />')

    for (x, y) in walls_v:
        x_line = LEFT + (x + 1) * STEP - GAP/2
        y_start = TOP + y * STEP - GAP/2
        y_end = TOP + y * STEP + CELL + GAP/2
        parts.append(f'<line x1="{x_line}" y1="{y_start}" x2="{x_line}" y2="{y_end}" stroke="#0284c7" stroke-width="3" stroke-linecap="round" opacity="0.5"/>')
        parts.append(f'<line x1="{x_line}" y1="{y_start}" x2="{x_line}" y2="{y_end}" stroke="#38bdf8" stroke-width="1.2" stroke-linecap="round" />')

    parts.append(pacman_svg())

    # Spread ghosts out so they roam everywhere
    ghost_starts = [(10, 3), (25, 3), (40, 3)] 
    ghost_colors = ["#ff3b30", "#00c7ff", "#ff6bcb"]
    steps = [60, 75, 90]

    for index, start_pos in enumerate(ghost_starts):
        parts.append(ghost_svg(start_pos, ghost_colors[index], steps[index]))

    parts.append(f'<text x="{WIDTH / 2}" y="{HEIGHT - 16}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="11" font-style="italic" font-weight="700" fill="{text_color}">Every contribution leaves a mark.</text></svg>')
    return "\n".join(parts)

Path("/tmp").mkdir(exist_ok=True)
with open("/tmp/pacman-contribution-graph.svg", "w", encoding="utf-8") as f: f.write(create_svg(False))
with open("/tmp/pacman-contribution-graph-dark.svg", "w", encoding="utf-8") as f: f.write(create_svg(True))

print("Generated random organic Pac-Man graph!")
