import json
import sys
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

SECONDS_PER_CELL = 0.12
HOLD_SECONDS = 1.5

def is_valid_move(x1, y1, x2, y2, max_weeks):
    if not (0 <= x2 < max_weeks and 0 <= y2 < 7):
        return False
    if x1 == x2:
        y_min = min(y1, y2)
        if y_min == 1:
            for start_x in range(1, max_weeks - 1, 6):
                if start_x <= x1 < start_x + 4:
                    return False
    if y1 == y2:
        x_max = max(x1, x2)
        for wall_x in range(4, max_weeks - 2, 8):
            if x_max == wall_x:
                if 2 <= y1 <= 4:
                    return False
    return True

def bfs_closest_coin(start, unvisited_coins, max_weeks):
    queue = deque([[start]])
    visited = set([start])
    while queue:
        path = queue.popleft()
        x, y = path[-1]
        if (x, y) in unvisited_coins:
            return path
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if is_valid_move(x, y, nx, ny, max_weeks) and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append(path + [(nx, ny)])
    return None

def bfs_path(start, end, max_weeks):
    queue = deque([[start]])
    visited = set([start])
    while queue:
        path = queue.popleft()
        x, y = path[-1]
        if (x, y) == end:
            return path
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if is_valid_move(x, y, nx, ny, max_weeks) and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append(path + [(nx, ny)])
    return None

def generate_pacman_route(max_weeks, coins):
    if not coins:
        return [(0,0)]
    
    unvisited_coins = set(coins)
    current = (0,0)
    route = [(0,0)]
    
    if current in unvisited_coins:
        unvisited_coins.remove(current)
        
    while unvisited_coins:
        path = bfs_closest_coin(current, unvisited_coins, max_weeks)
        if not path:
            break
        
        best_coin = path[-1]
        route.extend(path[1:])
        unvisited_coins.remove(best_coin)
        current = best_coin
        
    back_path = bfs_path(current, (0,0), max_weeks)
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
route = generate_pacman_route(MAX_WEEKS, coin_cells)

arrival_time = {}
for index, position in enumerate(route):
    if position not in arrival_time:
        arrival_time[position] = index * SECONDS_PER_CELL

TOTAL_TRAVEL = len(route) * SECONDS_PER_CELL
TOTAL_DURATION = max(1.0, TOTAL_TRAVEL + HOLD_SECONDS)

def point_for(x, y):
    return LEFT + x * STEP + CELL / 2, TOP + y * STEP + CELL / 2

def route_path():
    if len(route) <= 1: return "M 0 0"
    points = [point_for(x, y) for x, y in route]
    commands = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    commands.extend(f"L {px:.1f} {py:.1f}" for px, py in points[1:])
    return " ".join(commands)

PACMAN_PATH = route_path()

def ghost(x, y, color):
    px = LEFT + x * STEP
    py = TOP + y * STEP
    return f"""
    <g>
      <path d="
        M {px + 2} {py + 8}
        C {px + 2} {py + 3}, {px + 5} {py + 1}, {px + 8} {py + 1}
        C {px + 11} {py + 1}, {px + 12} {py + 3}, {px + 12} {py + 8}
        L {px + 12} {py + 12} L {px + 10} {py + 10}
        L {px + 8} {py + 12} L {px + 6} {py + 10}
        L {px + 4} {py + 12} L {px + 2} {py + 10} Z"
        fill="{color}"/>
      <circle cx="{px + 6}" cy="{py + 6}" r="1.5" fill="white"/>
      <circle cx="{px + 10}" cy="{py + 6}" r="1.5" fill="white"/>
    </g>
    """

def pacman_svg():
    return f"""
    <g>
      <path d="
        M 0 0
        L 6 -4
        A 6 6 0 1 0 6 4 Z"
        fill="#FFD93D">
        <animateMotion dur="{TOTAL_DURATION:.2f}s"
          repeatCount="indefinite"
          path="{PACMAN_PATH}"
          rotate="auto"/>
        <animateTransform attributeName="transform"
          type="scale"
          values="1 1; 1 0.90; 1 1"
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

    # Draw empty background grid
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
    if cell["level"] == 1:
        radius = 2.5
    elif cell["level"] == 2:
        radius = 3.5
    elif cell["level"] == 3:
        radius = 4.5
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
    wall_color = "#f0f6fc"

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

    maze_y = TOP + 1.5 * STEP
    for x in range(1, MAX_WEEKS - 1, 6):
        x1 = LEFT + x * STEP
        x2 = LEFT + min(x + 4, MAX_WEEKS - 1) * STEP
        parts.append(f'<path d="M {x1} {maze_y} H {x2}" fill="none" stroke="{wall_color}" stroke-width="1.4" stroke-linecap="round" opacity="0.65"/>')

    for x in range(4, MAX_WEEKS - 2, 8):
        px = LEFT + x * STEP
        parts.append(f'<path d="M {px} {TOP + 2 * STEP} V {TOP + 5 * STEP}" fill="none" stroke="{wall_color}" stroke-width="1.4" stroke-linecap="round" opacity="0.65"/>')

    parts.append(pacman_svg())

    ghost_positions = [(max(4, MAX_WEEKS // 3), 2), (max(5, MAX_WEEKS // 2), 3), (max(6, (MAX_WEEKS * 2) // 3), 3)]
    ghost_colors = ["#ff3b30", "#00c7ff", "#ff6bcb"]

    for index, (x, y) in enumerate(ghost_positions):
        parts.append(ghost(x, y, ghost_colors[index % len(ghost_colors)]))

    parts.append(f'<text x="{WIDTH / 2}" y="{HEIGHT - 16}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="11" font-style="italic" font-weight="700" fill="{text_color}">Every contribution leaves a mark.</text></svg>')
    return "\n".join(parts)

Path("/tmp").mkdir(exist_ok=True)
with open("/tmp/pacman-contribution-graph.svg", "w", encoding="utf-8") as f: f.write(create_svg(False))
with open("/tmp/pacman-contribution-graph-dark.svg", "w", encoding="utf-8") as f: f.write(create_svg(True))

print("Generated synchronized Pac-Man contribution graph.")
