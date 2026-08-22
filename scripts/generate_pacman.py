import json
import sys
from pathlib import Path
from datetime import date as Date

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

SECONDS_PER_CELL = 0.15
HOLD_SECONDS = 1.5


def escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def level_from_count(count):
    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
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
        if not week["contributionDays"]:
            continue
        date_text = week["contributionDays"][0]["date"]
        month = date_text[:7]
        if month != previous_month:
            labels.append((x, months.get(date_text[5:7], date_text[5:7])))
            previous_month = month
    return labels


def get_cells():
    cells = []
    for x, week in enumerate(weeks):
        for day in week["contributionDays"]:
            y, m, d = map(int, day["date"].split("-"))
            # GitHub renders the contribution calendar Sunday-first.
            # Python weekday() is Monday-first, so convert it.
            weekday = (Date(y, m, d).weekday() + 1) % 7
            cells.append({
                "x": x,
                "y": weekday,
                "date": day["date"],
                "count": day["contributionCount"],
                "level": level_from_count(day["contributionCount"]),
            })
    return cells


cells = get_cells()

# Snake through every calendar cell. This guarantees every green
# contribution cell is visited by Pac-Man.
route = []
for x in range(MAX_WEEKS):
    rows = range(7) if x % 2 == 0 else range(6, -1, -1)
    for y in rows:
        route.append((x, y))

arrival_time = {position: index * SECONDS_PER_CELL
                for index, position in enumerate(route)}

TOTAL_TRAVEL = len(route) * SECONDS_PER_CELL
TOTAL_DURATION = TOTAL_TRAVEL + HOLD_SECONDS


def point_for(x, y):
    return LEFT + x * STEP + CELL / 2, TOP + y * STEP + CELL / 2


def route_path():
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
    start_px, start_py = point_for(*route[0])
    return f"""
    <g>
      <path d="
        M {start_px:.1f} {start_py:.1f}
        L {start_px + 6:.1f} {start_py - 4:.1f}
        A 6 6 0 1 0 {start_px + 6:.1f} {start_py + 4:.1f} Z"
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
    fill = (DARK_COLORS if dark else LIGHT_COLORS)[cell["level"]]

    if cell["count"] <= 0:
        return f"""
        <rect x="{px}" y="{py}" width="{CELL}" height="{CELL}"
              rx="3" fill="{fill}"/>
        """

    t = arrival_time[(cell["x"], cell["y"])]
    consume_at = max(0.01, t + SECONDS_PER_CELL * 0.35)
    consume_key = consume_at / TOTAL_DURATION
    disappear_key = min(1, (consume_at + 0.12) / TOTAL_DURATION)

    return f"""
    <rect x="{px}" y="{py}" width="{CELL}" height="{CELL}"
          rx="3" fill="{fill}">
      <title>{escape(cell["date"])}: {cell["count"]} contributions</title>
      <animate attributeName="opacity"
        values="1;1;0;0"
        keyTimes="0;{consume_key:.6f};{disappear_key:.6f};1"
        dur="{TOTAL_DURATION:.2f}s"
        repeatCount="indefinite"/>
    </rect>
    """


def create_svg(dark=False):
    text_color = "#c9d1d9"
    wall_color = "#f0f6fc"

    parts = [f"""<svg xmlns="http://www.w3.org/2000/svg"
      width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
      <rect width="100%" height="100%" fill="#0d1117" rx="12"/>
      <text x="{WIDTH / 2}" y="27" text-anchor="middle"
        font-family="Arial, Helvetica, sans-serif" font-size="18"
        font-weight="700" fill="{text_color}">Contribution Arcade</text>
    """]

    for x, label in month_labels():
        px = LEFT + x * STEP
        parts.append(f"""
        <text x="{px}" y="45" font-family="Arial, Helvetica, sans-serif"
          font-size="8" fill="#8b949e">{escape(label)}</text>
        """)

    for y, label in {0: "Mon", 2: "Wed", 4: "Fri"}.items():
        py = TOP + y * STEP + 9
        parts.append(f"""
        <text x="2" y="{py}" font-family="Arial, Helvetica, sans-serif"
          font-size="8" fill="#8b949e">{label}</text>
        """)

    # Real GitHub contribution cells.
    for cell in cells:
        parts.append(dot_svg(cell, dark))

    # Decorative maze walls. They do not control the Pac-Man route.
    maze_y = TOP + 1.5 * STEP
    for x in range(1, MAX_WEEKS - 1, 6):
        x1 = LEFT + x * STEP
        x2 = LEFT + min(x + 4, MAX_WEEKS - 1) * STEP
        parts.append(f"""
        <path d="M {x1} {maze_y} H {x2}" fill="none"
          stroke="{wall_color}" stroke-width="1.4"
          stroke-linecap="round" opacity="0.65"/>
        """)

    for x in range(4, MAX_WEEKS - 2, 8):
        px = LEFT + x * STEP
        parts.append(f"""
        <path d="M {px} {TOP + 2 * STEP} V {TOP + 5 * STEP}"
          fill="none" stroke="{wall_color}" stroke-width="1.4"
          stroke-linecap="round" opacity="0.65"/>
        """)

    parts.append(pacman_svg())

    ghost_positions = [
        (max(4, MAX_WEEKS // 3), 2),
        (max(5, MAX_WEEKS // 2), 3),
        (max(6, (MAX_WEEKS * 2) // 3), 3),
    ]
    ghost_colors = ["#ff3b30", "#00c7ff", "#ff6bcb"]

    for index, (x, y) in enumerate(ghost_positions):
        parts.append(ghost(x, y, ghost_colors[index % len(ghost_colors)]))

    parts.append(f"""
      <text x="{WIDTH / 2}" y="{HEIGHT - 16}" text-anchor="middle"
        font-family="Arial, Helvetica, sans-serif" font-size="11"
        font-style="italic" font-weight="700" fill="{text_color}">
        Every contribution leaves a mark.
      </text>
    </svg>
    """)

    return "\n".join(parts)


Path("/tmp").mkdir(exist_ok=True)

with open("/tmp/pacman-contribution-graph.svg", "w", encoding="utf-8") as f:
    f.write(create_svg(False))

with open("/tmp/pacman-contribution-graph-dark.svg", "w", encoding="utf-8") as f:
    f.write(create_svg(True))

print("Generated synchronized Pac-Man contribution graph.")
print("Total contributions:", calendar["totalContributions"])
print("Weeks:", len(weeks))
print("Pac-Man route cells:", len(route))
print("Every contribution cell will be visited.")
