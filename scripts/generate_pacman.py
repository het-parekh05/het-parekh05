import json
import math
import sys
from pathlib import Path


INPUT = sys.argv[1]

with open(INPUT, "r", encoding="utf-8") as f:
    payload = json.load(f)

calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]

# ------------------------------------------------------------
# GitHub contribution grid
# ------------------------------------------------------------

CELL = 13
GAP = 3
STEP = CELL + GAP

LEFT = 40
TOP = 58

MAX_WEEKS = len(weeks)

WIDTH = LEFT + MAX_WEEKS * STEP + 20
HEIGHT = TOP + 7 * STEP + 55

# GitHub contribution colors
LIGHT_COLORS = [
    "#161b22",
    "#9be9a8",
    "#40c463",
    "#30a14e",
    "#216e39",
]

DARK_COLORS = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
]


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


def escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ------------------------------------------------------------
# Month labels
# ------------------------------------------------------------

def month_labels():
    labels = []

    previous_month = None

    for x, week in enumerate(weeks):
        if not week["contributionDays"]:
            continue

        date = week["contributionDays"][0]["date"]
        month = date[:7]

        if month != previous_month:
            month_name = date[5:7]

            months = {
                "01": "Jan",
                "02": "Feb",
                "03": "Mar",
                "04": "Apr",
                "05": "May",
                "06": "Jun",
                "07": "Jul",
                "08": "Aug",
                "09": "Sep",
                "10": "Oct",
                "11": "Nov",
                "12": "Dec",
            }

            labels.append(
                (x, months.get(month_name, month_name))
            )

            previous_month = month

    return labels


# ------------------------------------------------------------
# Build exact GitHub cells
# ------------------------------------------------------------

cells = []

for x, week in enumerate(weeks):
    for day in week["contributionDays"]:
        date = day["date"]

        # Python weekday:
        # Monday = 0
        # Sunday = 6
        from datetime import date as Date

        y, m, d = map(int, date.split("-"))
        weekday = Date(y, m, d).weekday()

        count = day["contributionCount"]
        level = level_from_count(count)

        cells.append(
            {
                "x": x,
                "y": weekday,
                "date": date,
                "count": count,
                "level": level,
            }
        )


# ------------------------------------------------------------
# Pac-Man position
#
# Pac-Man follows the actual contribution grid.
# The path is decorative; contribution cells remain exact.
# ------------------------------------------------------------

pacman_x = 1
pacman_y = 2

if weeks:
    pacman_x = min(weeks.__len__() - 1, 2)

# Ghosts are deliberately positioned away from contribution cells
ghost_positions = [
    (max(4, MAX_WEEKS // 3), 2),
    (max(5, MAX_WEEKS // 2), 3),
    (max(6, (MAX_WEEKS * 2) // 3), 3),
]


def ghost(x, y, color, dark=False):
    px = LEFT + x * STEP
    py = TOP + y * STEP

    body_y = py + 1

    return f"""
    <g>
      <path
        d="
          M {px + 2} {body_y + 7}
          C {px + 2} {body_y + 2},
            {px + 5} {body_y},
            {px + 8} {body_y}
          C {px + 11} {body_y},
            {px + 12} {body_y + 2},
            {px + 12} {body_y + 7}
          L {px + 12} {body_y + 11}
          L {px + 10} {body_y + 9}
          L {px + 8} {body_y + 11}
          L {px + 6} {body_y + 9}
          L {px + 4} {body_y + 11}
          L {px + 2} {body_y + 9}
          Z"
        fill="{color}"
      />
      <circle cx="{px + 6}" cy="{body_y + 5}" r="1.5" fill="white"/>
      <circle cx="{px + 10}" cy="{body_y + 5}" r="1.5" fill="white"/>
    </g>
    """


def pacman(x, y, dark=False):
    px = LEFT + x * STEP
    py = TOP + y * STEP

    return f"""
    <g>
      <path
        d="
          M {px + 7} {py + 7}
          L {px + 12} {py + 4}
          A 6 6 0 1 0 {px + 12} {py + 10}
          Z"
        fill="#FFD93D"
      />
    </g>
    """


# ------------------------------------------------------------
# SVG renderer
# ------------------------------------------------------------

def create_svg(dark=False):
    colors = DARK_COLORS if dark else LIGHT_COLORS

    background = "#0d1117"
    text_color = "#c9d1d9"
    wall_color = "#f0f6fc"

    parts = []

    parts.append(
        f'''<svg xmlns="http://www.w3.org/2000/svg"
        width="{WIDTH}"
        height="{HEIGHT}"
        viewBox="0 0 {WIDTH} {HEIGHT}">
        <rect width="100%" height="100%" fill="{background}" rx="12"/>'''
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    parts.append(
        f'''
        <text
          x="{WIDTH / 2}"
          y="27"
          text-anchor="middle"
          font-family="Arial, Helvetica, sans-serif"
          font-size="18"
          font-weight="700"
          fill="{text_color}">
          Contribution Arcade
        </text>
        '''
    )

    # --------------------------------------------------------
    # Month labels
    # --------------------------------------------------------

    for x, label in month_labels():
        px = LEFT + x * STEP

        parts.append(
            f'''
            <text
              x="{px}"
              y="45"
              font-family="Arial, Helvetica, sans-serif"
              font-size="8"
              fill="#8b949e">
              {escape(label)}
            </text>
            '''
        )

    # --------------------------------------------------------
    # Weekday labels
    # --------------------------------------------------------

    weekday_names = {
        0: "Mon",
        2: "Wed",
        4: "Fri",
    }

    for y, label in weekday_names.items():
        py = TOP + y * STEP + 9

        parts.append(
            f'''
            <text
              x="2"
              y="{py}"
              font-family="Arial, Helvetica, sans-serif"
              font-size="8"
              fill="#8b949e">
              {label}
            </text>
            '''
        )

    # --------------------------------------------------------
    # EXACT GitHub contribution cells
    # --------------------------------------------------------

    for cell in cells:
        px = LEFT + cell["x"] * STEP
        py = TOP + cell["y"] * STEP

        fill = colors[cell["level"]]

        parts.append(
            f'''
            <rect
              x="{px}"
              y="{py}"
              width="{CELL}"
              height="{CELL}"
              rx="3"
              fill="{fill}">
              <title>{escape(cell["date"])}: {cell["count"]} contributions</title>
            </rect>
            '''
        )

    # --------------------------------------------------------
    # Arcade maze lines
    #
    # These are decorative only.
    # They never replace or move contribution cells.
    # --------------------------------------------------------

    maze_y = TOP + 1.5 * STEP

    for x in range(1, MAX_WEEKS - 1, 6):
        x1 = LEFT + x * STEP
        x2 = LEFT + min(x + 4, MAX_WEEKS - 1) * STEP

        parts.append(
            f'''
            <path
              d="M {x1} {maze_y}
                 H {x2}"
              fill="none"
              stroke="{wall_color}"
              stroke-width="1.4"
              stroke-linecap="round"
              opacity="0.65"/>
            '''
        )

    # Vertical decorative walls

    for x in range(4, MAX_WEEKS - 2, 8):
        px = LEFT + x * STEP

        parts.append(
            f'''
            <path
              d="M {px} {TOP + 2 * STEP}
                 V {TOP + 5 * STEP}"
              fill="none"
              stroke="{wall_color}"
              stroke-width="1.4"
              stroke-linecap="round"
              opacity="0.65"/>
            '''
        )

    # --------------------------------------------------------
    # Pac-Man
    # --------------------------------------------------------

    parts.append(pacman(pacman_x, pacman_y, dark))

    # --------------------------------------------------------
    # Ghosts
    # --------------------------------------------------------

    ghost_colors = [
        "#ff3b30",
        "#00c7ff",
        "#ff6bcb",
    ]

    for index, (x, y) in enumerate(ghost_positions):
        parts.append(
            ghost(
                x,
                y,
                ghost_colors[index % len(ghost_colors)],
                dark
            )
        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    parts.append(
        f'''
        <text
          x="{WIDTH / 2}"
          y="{HEIGHT - 16}"
          text-anchor="middle"
          font-family="Arial, Helvetica, sans-serif"
          font-size="11"
          font-style="italic"
          font-weight="700"
          fill="{text_color}">
          Every contribution leaves a mark.
        </text>
        '''
    )

    parts.append("</svg>")

    return "\n".join(parts)


Path("/tmp").mkdir(exist_ok=True)

with open(
    "/tmp/pacman-contribution-graph.svg",
    "w",
    encoding="utf-8"
) as f:
    f.write(create_svg(dark=False))

with open(
    "/tmp/pacman-contribution-graph-dark.svg",
    "w",
    encoding="utf-8"
) as f:
    f.write(create_svg(dark=True))

print("Generated synchronized contribution arcade.")
print("Total contributions:", calendar["totalContributions"])
print("Weeks:", len(weeks))
