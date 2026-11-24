"""Render an animated trail across Alex Brito's public GitHub contributions."""

from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import time
from urllib.request import Request, urlopen

PROFILE = "alexbritodev"
CALENDAR = f"https://github.com/users/{PROFILE}/contributions"
OUTPUT = Path(__file__).resolve().parents[1] / "assets/contribution-trail.svg"
WEEKS = 52
DAYS = 7
STEP = 13
GRID_X = 42
GRID_Y = 60
CELL_SIZE = 10
WIDTH = GRID_X + (WEEKS - 1) * STEP + CELL_SIZE + 24
HEIGHT = 179


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.levels = {}

    def handle_starttag(self, tag, attributes):
        if tag != "td":
            return
        attributes = dict(attributes)
        day = attributes.get("data-date")
        level = attributes.get("data-level")
        if day and level in {"0", "1", "2", "3", "4"}:
            self.levels[date.fromisoformat(day)] = int(level)


def sunday(day):
    return day - timedelta(days=(day.weekday() + 1) % DAYS)


def get_calendar():
    for attempt in range(3):
        try:
            parser = CalendarParser()
            request = Request(CALENDAR, headers={"User-Agent": "AlexBritoDev contribution trail"})
            with urlopen(request, timeout=20) as response:
                parser.feed(response.read(2_000_000).decode())
            if len(parser.levels) < 350:
                raise ValueError("The public contribution calendar is incomplete.")
            last = max(parser.levels)
            if abs((datetime.now(timezone.utc).date() - last).days) > 2:
                raise ValueError("The public contribution calendar is stale.")
            first = sunday(last) - timedelta(weeks=WEEKS - 1)
            if any(first + timedelta(days=i) not in parser.levels for i in range((last - first).days + 1)):
                raise ValueError("Some contribution dates are missing from the selected year.")
            return parser.levels, first, last
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))


def cell_position(week, day):
    return GRID_X + week * STEP, GRID_Y + day * STEP


def render_grid(levels, first, last):
    months, cells, route = [], [], []
    previous_month = None
    for week in range(WEEKS):
        start = first + timedelta(weeks=week)
        if start.month != previous_month:
            if week > 0 or (start + timedelta(weeks=1)).month == start.month:
                months.append(f'<text class="muted" x="{GRID_X + week * STEP}" y="51">{start:%b}</text>')
            previous_month = start.month
        strongest = 0
        point = None
        for day in range(DAYS):
            current = start + timedelta(days=day)
            if current > last:
                break
            x, y = cell_position(week, day)
            level = levels[current]
            cells.append(f'<rect class="level-{level}" x="{x}" y="{y}" width="10" height="10" rx="2"/>')
            if level > strongest:
                strongest = level
                point = (x + CELL_SIZE // 2, y + CELL_SIZE // 2)
        if point is not None:
            route.append(point)
    return "\n".join(months + cells), route


def render_route(waypoints):
    if not waypoints:
        return ""
    if len(waypoints) == 1:
        x, y = waypoints[0]
        return f'<circle class="checkpoint" cx="{x}" cy="{y}" r="3"/>'
    start, *destinations = waypoints
    path = f"M{start[0]} {start[1]}"
    previous = start
    for x, y in destinations:
        middle = (previous[0] + x) / 2
        path += f" C{middle:g} {previous[1]} {middle:g} {y} {x} {y}"
        previous = x, y
    checkpoints = "\n".join(
        f'<circle class="checkpoint" cx="{x}" cy="{y}" r="2"/>' for x, y in waypoints
    )
    return f'''
  <path class="route" d="{path}"/>
  {checkpoints}
  <g class="motion">
    <path class="sweep" d="{path}" pathLength="1" stroke-dasharray="1">
      <animate attributeName="stroke-dashoffset" from="1" to="0" begin="0s" dur="4.5s" fill="freeze"/>
    </path>
    <g class="ship">
      <animateMotion path="{path}" rotate="auto" begin="0s" dur="4.5s" fill="freeze"/>
      <circle class="halo" r="8"/>
      <path class="spark" d="M-14 0h6m-4-3h5m-5 6h5"/>
      <path class="craft" d="M8 0-5 5-2 0-5-5Z"/>
    </g>
  </g>'''


def render(levels, first, last):
    grid, waypoints = render_grid(levels, first, last)
    route = render_route(waypoints)
    active = sum(first <= day <= last and level > 0 for day, level in levels.items())
    period = f"{first:%b %Y} – {last:%b %Y}"
    summary = f"{active} active {'day' if active == 1 else 'days'}"
    legend = "\n".join(
        f'<rect class="level-{level}" x="{WIDTH - 108 + level * 13}" y="154" width="10" height="10" rx="2"/>'
        for level in range(5)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title description">
  <title id="title">Contribution trail</title>
  <desc id="description">Alex Brito's public GitHub activity from {first.isoformat()} through {last.isoformat()}. {summary}. An animated ship follows a trail of active days.</desc>
  <style>
    .canvas {{ fill: #fbfafd; stroke: #e3dcef; }}
    .strong {{ fill: #312248; font-weight: 650; }}
    .muted {{ fill: #665b77; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    text {{ font: 10px system-ui, sans-serif; }}
    .level-0 {{ fill: #eeeaf3; }}
    .level-1 {{ fill: #a8e5b6; }}
    .level-2 {{ fill: #68c886; }}
    .level-3 {{ fill: #319957; }}
    .level-4 {{ fill: #1d6e3b; }}
    .route {{ fill: none; stroke: #8262b8; stroke-width: 1; stroke-opacity: .46; stroke-dasharray: 2 3; }}
    .checkpoint {{ fill: #623aab; }}
    .sweep {{ fill: none; stroke: #8b5cda; stroke-width: 1.8; stroke-linecap: round; stroke-opacity: .75; stroke-dashoffset: 1; }}
    .halo {{ fill: #b18cf0; fill-opacity: .25; }}
    .spark {{ fill: none; stroke: #a970ed; stroke-width: 1.5; stroke-linecap: round; }}
    .craft {{ fill: #6f35c4; stroke: #fff; stroke-width: 1; stroke-linejoin: round; }}
    .motion {{ display: none; }}
    @media (prefers-color-scheme: dark) {{
      .canvas {{ fill: #171321; stroke: #3e334e; }}
      .strong {{ fill: #f1eaff; }}
      .muted {{ fill: #b9abc9; }}
      .level-0 {{ fill: #292235; }}
      .level-1 {{ fill: #174e37; }}
      .level-2 {{ fill: #236c46; }}
      .level-3 {{ fill: #3b9c61; }}
      .level-4 {{ fill: #71d98f; }}
      .route {{ stroke: #ac8ce4; }}
      .checkpoint {{ fill: #b898f0; }}
      .sweep, .spark {{ stroke: #c3a0ff; }}
      .craft {{ fill: #b78cf5; stroke: #231439; }}
    }}
    @media (prefers-reduced-motion: no-preference) {{ .motion {{ display: inline; }} }}
  </style>
  <rect class="canvas" x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="12"/>
  <text class="strong mono" x="19" y="25">PUBLIC CONTRIBUTIONS</text>
  <text class="muted" x="{WIDTH-22}" y="25" text-anchor="end">{period}</text>
  <text class="muted" x="14" y="81">Mon</text>
  <text class="muted" x="14" y="107">Wed</text>
  <text class="muted" x="14" y="133">Fri</text>
  {grid}
  {route}
  <text class="muted" x="19" y="162">{summary}</text>
  <text class="muted" x="{WIDTH-134}" y="162">Less</text>
  {legend}
  <text class="muted" x="{WIDTH-38}" y="162">More</text>
</svg>
'''


def main():
    levels, first, last = get_calendar()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(levels, first, last), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

