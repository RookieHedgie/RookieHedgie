"""Builds the profile stats card SVG (Unity dark editor look).

With STATS_TOKEN set, it reads live data from the GitHub GraphQL API.
Without it, it renders sample data (handy for local previews).

Usage: python3 scripts/make_card.py assets/stats-card.svg
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

TITLE = "Game Designer"
TZ = ZoneInfo("Europe/Istanbul")

SAMPLE = {
    "user": "RookieHedgie",
    "title": TITLE,
    "public": 12,
    "private": 5,
    "streak": 3,
    "last_active": "Nov 7",
    "days": [0,0,1,0,0,0,0,0,1,1,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1,1,1,0],
    "updated": "08 Nov 2026 · 06:00 GMT+3",
}

QUERY = """
query {
  viewer {
    login
    pub: repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
    priv: repositories(ownerAffiliations: OWNER, privacy: PRIVATE) { totalCount }
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-stats-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GitHub API error: {body['errors']}")
    return body["data"]["viewer"]


def summarize(viewer):
    """Turns the API response into the numbers the card shows."""
    days = [d for w in viewer["contributionsCollection"]["contributionCalendar"]["weeks"]
            for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    counts = [d["contributionCount"] for d in days]

    # Streak: consecutive days with contributions, ending today.
    # If nothing yet today, the streak still counts up to yesterday.
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    streak = 0
    while i >= 0 and counts[i] > 0:
        streak += 1
        i -= 1

    active = [d["date"] for d in days if d["contributionCount"] > 0]
    if active:
        last = date.fromisoformat(active[-1])
        last_active = f"{last:%b} {last.day}"
    else:
        last_active = "—"

    return {
        "user": viewer["login"],
        "title": TITLE,
        "public": viewer["pub"]["totalCount"],
        "private": viewer["priv"]["totalCount"],
        "streak": streak,
        "last_active": last_active,
        "days": [1 if c > 0 else 0 for c in counts[-30:]],
        "updated": datetime.now(TZ).strftime("%d %b %Y · %H:%M") + " GMT+3",
    }


# Unity dark editor palette (approximate)
FRAME   = "#191919"
TABBAR  = "#282828"
PANEL   = "#383838"
HEADER  = "#3e3e3e"
FIELD   = "#2a2a2a"
EDGE    = "#212121"
TEXT    = "#d2d2d2"
MUTED   = "#8f8f8f"
BLUE    = "#3a79bb"
SELECT  = "#f7931e"   # Unity selection outline
SCENE   = "#2f2f2f"
GRID    = "#3a3a3a"
FONT = "Inter, Roboto, 'Segoe UI', Helvetica, Arial, 'DejaVu Sans', sans-serif"

W, H = 840, 340
SPLIT = 300            # scene | inspector
TOP = 26               # tab bar height
BODY_END = 258         # end of scene/inspector panels
TL_Y = 260             # timeline panel start
STATUS_Y = 320         # status bar start


def t(x, y, s, size=12, fill=TEXT, weight=400, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


def tab(x, label, icon):
    w = 12 + len(label) * 7 + 22
    return (f'<rect x="{x}" y="0" width="{w}" height="{TOP}" fill="{PANEL}"/>'
            f'<rect x="{x}" y="0" width="{w}" height="2" fill="{BLUE}"/>'
            f'{icon(x + 10, 9)}'
            + t(x + 26, 17, label, 12))


def icon_scene(x, y):
    return (f'<path d="M{x} {y+4} L{x+5} {y} L{x+10} {y+4} L{x+5} {y+8} Z" '
            f'fill="none" stroke="{TEXT}" stroke-width="1"/>')


def icon_info(x, y):
    return (f'<circle cx="{x+5}" cy="{y+4}" r="5" fill="none" stroke="{TEXT}" stroke-width="1"/>'
            f'<rect x="{x+4.4}" y="{y+3}" width="1.2" height="4" fill="{TEXT}"/>'
            f'<rect x="{x+4.4}" y="{y+0.8}" width="1.2" height="1.2" fill="{TEXT}"/>')


def scene():
    """Camera looks down at a grid; the cube sits on that same grid, so both share one perspective."""
    import math
    cx, cy, f = 150, (TOP + BODY_END) / 2 + 14, 250
    cam_h, pitch, dist, yaw = 4.2, math.radians(27), 8.0, math.radians(32)
    fw = (0, -math.sin(pitch), math.cos(pitch))
    up = (0, math.cos(pitch), math.sin(pitch))
    cy_, sy_ = math.cos(yaw), math.sin(yaw)

    def world(x, y, z):            # local (grid/cube) -> world
        return (x * cy_ + z * sy_, y, -x * sy_ + z * cy_ + dist)

    def cam(p):                    # world -> camera space
        r = (p[0], p[1] - cam_h, p[2])
        return (r[0], r[0]*0 + r[1]*up[1] + r[2]*up[2], r[1]*fw[1] + r[2]*fw[2])

    def scr(c):
        return (cx + f * c[0] / c[2], cy - f * c[1] / c[2])

    def P(x, y, z):
        return scr(cam(world(x, y, z)))

    def seg(a, b, near=0.6):       # clip a camera-space segment to the near plane
        if a[2] < near and b[2] < near:
            return None
        if a[2] < near or b[2] < near:
            t_ = (near - a[2]) / (b[2] - a[2])
            m = tuple(a[i] + (b[i] - a[i]) * t_ for i in range(3))
            a, b = (m, b) if a[2] < near else (a, m)
        return scr(a), scr(b), (a[2] + b[2]) / 2

    out = [f'<clipPath id="sc"><rect x="0" y="{TOP}" width="{SPLIT}" height="{BODY_END-TOP}"/></clipPath>',
           f'<rect x="0" y="{TOP}" width="{SPLIT}" height="{BODY_END-TOP}" fill="{SCENE}"/>',
           '<g clip-path="url(#sc)">']
    N = 14
    for k in range(-N, N + 1):
        for a_, b_ in (((k, 0, -N), (k, 0, N)), ((-N, 0, k), (N, 0, k))):
            r = seg(cam(world(*a_)), cam(world(*b_)))
            if r:
                (x1, y1), (x2, y2), _ = r
                op = 0.9 if k == 0 else 0.6
                out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                           f'stroke="{GRID}" stroke-width="1" opacity="{op}"/>')
    out.append('</g>')

    # cube: local [-1,1] x [0,2] x [-1,1]
    V = {(i, j, k): (2 * i - 1, 2 * j, 2 * k - 1) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    S = {q: P(*V[q]) for q in V}
    faces = {  # corner order gives outward normals as counter-clockwise when seen from outside
        "top":   ([(0,1,0), (0,1,1), (1,1,1), (1,1,0)], "#9a9a9a"),
        "front": ([(0,0,0), (0,1,0), (1,1,0), (1,0,0)], "#7a7a7a"),
        "right": ([(1,0,0), (1,1,0), (1,1,1), (1,0,1)], "#5c5c5c"),
        "left":  ([(0,0,1), (0,1,1), (0,1,0), (0,0,0)], "#6c6c6c"),
        "back":  ([(1,0,1), (1,1,1), (0,1,1), (0,0,1)], "#5c5c5c"),
    }
    for keys, color in faces.values():
        p = [S[q] for q in keys]
        area = sum(p[i][0] * p[(i+1) % 4][1] - p[(i+1) % 4][0] * p[i][1] for i in range(4))
        if area > 0:   # facing the camera
            out.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in p)
                       + f'" fill="{color}" stroke="{color}" stroke-width="0.5"/>')
    # selection outline = convex hull of projected corners
    pts = sorted(set(S.values()))
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0: lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0: upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    out.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in hull)
               + f'" fill="none" stroke="{SELECT}" stroke-width="2" stroke-linejoin="round"/>')

    # move gizmo at the cube center, aligned with the grid axes
    c = (0, 1, 0)
    o = P(*c)
    def arrow(d, color):
        e = P(c[0] + d[0], c[1] + d[1], c[2] + d[2])
        dx, dy = e[0] - o[0], e[1] - o[1]
        L = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / L, dy / L
        tip = (e[0] + ux * 8, e[1] + uy * 8)
        l = (e[0] - uy * 4, e[1] + ux * 4)
        r = (e[0] + uy * 4, e[1] - ux * 4)
        return (f'<line x1="{o[0]:.1f}" y1="{o[1]:.1f}" x2="{e[0]:.1f}" y2="{e[1]:.1f}" stroke="{color}" stroke-width="2"/>'
                f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {l[0]:.1f},{l[1]:.1f} {r[0]:.1f},{r[1]:.1f}" fill="{color}"/>')
    out.append(arrow((0, 0, 1.6), "#3d7fe0"))
    out.append(arrow((1.6, 0, 0), "#e0401f"))
    out.append(arrow((0, 1.5, 0), "#8ccf3f"))
    return "\n".join(out)


def icon(kind, x, y, color):
    if kind == "repo":   # open book
        return (f'<path d="M{x} {y+2} h5 a2 2 0 0 1 2 2 v10 a2 2 0 0 0 -2 -2 h-5 Z '
                f'M{x+14} {y+2} h-5 a2 2 0 0 0 -2 2 v10 a2 2 0 0 1 2 -2 h5 Z" '
                f'fill="none" stroke="{color}" stroke-width="1.3" stroke-linejoin="round"/>')
    if kind == "lock":
        return (f'<rect x="{x+1}" y="{y+7}" width="12" height="9" rx="1.5" fill="none" stroke="{color}" stroke-width="1.3"/>'
                f'<path d="M{x+4} {y+7} v-2.5 a3 3 0 0 1 6 0 v2.5" fill="none" stroke="{color}" stroke-width="1.3"/>')
    if kind == "flame":
        return (f'<path d="M{x+7} {y} C{x+9} {y+4} {x+14} {y+6} {x+13} {y+11} '
                f'C{x+12.5} {y+15} {x+9.5} {y+17} {x+7} {y+17} C{x+3.5} {y+17} {x+1} {y+14.5} {x+1.2} {y+11} '
                f'C{x+1.5} {y+8} {x+4} {y+7} {x+5} {y+4} C{x+5.5} {y+6.5} {x+7} {y+7.5} {x+7.5} {y+9} '
                f'C{x+8.5} {y+6} {x+8} {y+3} {x+7} {y} Z" fill="{SELECT}"/>')
    if kind == "clock":
        return (f'<circle cx="{x+7}" cy="{y+9}" r="6.5" fill="none" stroke="{color}" stroke-width="1.3"/>'
                f'<path d="M{x+7} {y+5} v4.5 l3 2" fill="none" stroke="{color}" stroke-width="1.3" stroke-linecap="round"/>')
    return ""


def field_row(y, kind, label, value, override=False):
    x0 = SPLIT + 1
    lab_color = "#ffffff" if override else MUTED
    weight = 700 if override else 400
    out = []
    if override:
        out.append(f'<rect x="{x0}" y="{y-3}" width="3" height="34" fill="{BLUE}"/>')
    out.append(icon(kind, SPLIT + 28, y + 6, lab_color if not override else TEXT))
    out.append(t(SPLIT + 52, y + 20, label, 15, lab_color, weight))
    out.append(f'<rect x="{SPLIT + 190}" y="{y}" width="{W - SPLIT - 210}" height="28" rx="3" '
               f'fill="{"#2f3540" if override else FIELD}" stroke="{BLUE if override else EDGE}" '
               f'stroke-width="{1.5 if override else 1}"/>')
    out.append(t(SPLIT + 200, y + 20, value, 15, "#ffffff" if override else TEXT, weight))
    return "\n".join(out)


def inspector(d):
    x0 = SPLIT + 1
    out = [f'<rect x="{x0}" y="{TOP}" width="{W - x0}" height="{BODY_END-TOP}" fill="{PANEL}"/>']
    # GameObject header: cube icon, name, tag dropdown
    out.append(f'<path d="M{x0+16} {TOP+16} l7 -4 l7 4 v8 l-7 4 l-7 -4 Z M{x0+16} {TOP+16} l7 4 l7 -4 M{x0+23} {TOP+20} v8" '
               f'fill="none" stroke="{TEXT}" stroke-width="1"/>')
    out.append(t(x0 + 40, TOP + 26, d["user"], 14, TEXT, 700))
    out.append(t(W - 172, TOP + 26, "Tag", 12, MUTED))
    out.append(f'<rect x="{W - 140}" y="{TOP + 12}" width="124" height="20" rx="3" fill="{HEADER}" stroke="{EDGE}"/>')
    out.append(t(W - 132, TOP + 26, d["title"], 12, TEXT))
    out.append(f'<path d="M{W-28} {TOP+20} l4 4 l4 -4" fill="none" stroke="{TEXT}" stroke-width="1.2"/>')
    # component header
    cy = TOP + 44
    out.append(f'<rect x="{x0}" y="{cy}" width="{W - x0}" height="24" fill="{HEADER}"/>'
               f'<line x1="{x0}" y1="{cy}" x2="{W}" y2="{cy}" stroke="{EDGE}"/>'
               f'<line x1="{x0}" y1="{cy+24}" x2="{W}" y2="{cy+24}" stroke="{EDGE}"/>')
    out.append(f'<path d="M{x0+12} {cy+9} l4 6 l4 -6 Z" fill="{TEXT}"/>')
    out.append(f'<rect x="{x0+28}" y="{cy+6}" width="12" height="12" rx="2" fill="{BLUE}"/>'
               f'<path d="M{x0+31} {cy+12} l2 3 l5 -6" fill="none" stroke="#fff" stroke-width="1.4"/>')
    out.append(t(x0 + 48, cy + 16, "Profile Stats", 12, TEXT, 700))
    out.append(t(x0 + 140, cy + 16, "(Script)", 12, MUTED))
    # fields
    fy = cy + 38
    rows = [
        ("flame", "Streak", f'{d["streak"]} {"day" if d["streak"] == 1 else "days"}', True),
        ("repo", "Public Repos", d["public"], False),
        ("lock", "Private Repos", d["private"], False),
        ("clock", "Last Active", d["last_active"], False),
    ]
    for i, (kind, label, value, ov) in enumerate(rows):
        out.append(field_row(fy + i * 38, kind, label, value, ov))
    return "\n".join(out)


def timeline(d):
    days = d["days"]
    y0 = TL_Y
    out = [f'<rect x="0" y="{y0}" width="{W}" height="{STATUS_Y - y0}" fill="{PANEL}"/>',
           f'<rect x="0" y="{y0}" width="{W}" height="20" fill="{TABBAR}"/>',
           t(12, y0 + 14, "Last 30 Days", 11, MUTED),
           t(W - 12, y0 + 14, f'{sum(days)} active days', 11, MUTED, anchor="end")]
    x_start, x_end = 120, W - 24
    step = (x_end - x_start) / (len(days) - 1)
    ky = y0 + 40
    out.append(f'<line x1="{x_start}" y1="{ky}" x2="{x_end}" y2="{ky}" stroke="{GRID}" stroke-width="1"/>')
    out.append(t(12, ky + 4, "Contributions", 11, TEXT))
    for i, a in enumerate(days):
        x = x_start + i * step
        if a:
            out.append(f'<path d="M{x:.1f} {ky-6} l6 6 l-6 6 l-6 -6 Z" fill="{TEXT}" stroke="{FRAME}" stroke-width="1"/>')
        else:
            out.append(f'<rect x="{x-1:.1f}" y="{ky-1}" width="2" height="2" fill="{MUTED}" opacity="0.5"/>')
    # playhead on today
    px = x_end
    out.append(f'<line x1="{px}" y1="{y0+20}" x2="{px}" y2="{STATUS_Y}" stroke="#e0401f" stroke-width="1.5"/>')
    return "\n".join(out)


def build(d):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<clipPath id="r"><rect width="{W}" height="{H}" rx="6"/></clipPath>
<g clip-path="url(#r)">
<rect width="{W}" height="{H}" fill="{FRAME}"/>
<rect width="{W}" height="{TOP}" fill="{TABBAR}"/>
{tab(0, "Scene", icon_scene)}
{tab(SPLIT + 1, "Inspector", icon_info)}
{scene()}
{inspector(d)}
{timeline(d)}
<rect x="0" y="{STATUS_Y}" width="{W}" height="{H - STATUS_Y}" fill="{TABBAR}"/>
{t(12, STATUS_Y + 14, "updated " + d["updated"], 10, MUTED)}
</g>
<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="6" fill="none" stroke="{FRAME}"/>
</svg>'''


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "stats-card.svg"
    token = os.environ.get("STATS_TOKEN")
    card_data = summarize(fetch(token)) if token else SAMPLE
    svg = build(card_data)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out}: {card_data['public']} public, {card_data['private']} private, "
          f"streak {card_data['streak']}, last active {card_data['last_active']}")
