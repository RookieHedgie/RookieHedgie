"""Builds the Unity-style "Project" panel shown under the stats card.

An SVG inside a README is just an image, so links inside it cannot be clicked.
To make each asset tile clickable, the panel is drawn once and then sliced into
vertical strips (same drawing, different viewBox). The README places the strips
side by side and wraps each tile strip in its own link.

Usage: python3 scripts/make_project.py assets
"""
import os
import sys

W, H = 840, 170
SPLIT = 300          # matches the Scene | Inspector split of the stats card
TOP = 26             # tab bar
BAR = 22             # breadcrumb bar
FOOT = 20            # bottom bar of the right pane
TILE_W = 120

LINKS = [  # name, accent color, url
    ("LinkedIn", "#0a66c2", "https://www.linkedin.com/in/faruk-yıldırım/"),
    ("ArtStation", "#13aff0", "https://www.artstation.com/rookiehedgie"),
]

FRAME, TABBAR, PANEL, GRIDBG = "#191919", "#282828", "#383838", "#313131"
TEXT, MUTED, BLUE, SELECT_ROW = "#d2d2d2", "#8f8f8f", "#3a79bb", "#2c5d87"
FONT = "Inter, Roboto, 'Segoe UI', Helvetica, Arial, 'DejaVu Sans', sans-serif"


def t(x, y, s, size=12, fill=TEXT, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{s}</text>')


def folder(x, y, open_=False, color="#b5b5b5"):
    if open_:
        return (f'<path d="M{x} {y+2} h5 l2 2 h7 v2 h-11 l-3 7 Z" fill="{color}"/>'
                f'<path d="M{x+3} {y+6} h13 l-3 7 h-13 Z" fill="{color}" opacity="0.8"/>')
    return (f'<path d="M{x} {y+2} h5 l2 2 h7 v9 h-14 Z" fill="{color}"/>')


def link_icon(cx, cy, color):
    s = 56
    x, y = cx - s / 2, cy - s / 2
    # rounded asset tile in the platform color with a white "open link" glyph
    return (f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="8" fill="{color}"/>'
            f'<g fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M{cx-3} {cy-12} h-7 a3 3 0 0 0 -3 3 v19 a3 3 0 0 0 3 3 h19 a3 3 0 0 0 3 -3 v-7"/>'
            f'<path d="M{cx+3} {cy-15} h12 v12"/>'
            f'<path d="M{cx+15} {cy-15} l-15 15"/>'
            f'</g>')


def build():
    o = []
    o.append(f'<clipPath id="r"><rect width="{W}" height="{H}" rx="6"/></clipPath><g clip-path="url(#r)">')
    o.append(f'<rect width="{W}" height="{H}" fill="{FRAME}"/>')
    # tab bar with one active tab
    o.append(f'<rect width="{W}" height="{TOP}" fill="{TABBAR}"/>')
    o.append(f'<rect x="0" y="0" width="84" height="{TOP}" fill="{PANEL}"/>'
             f'<rect x="0" y="0" width="84" height="2" fill="{BLUE}"/>')
    o.append(folder(10, 7, color=TEXT))
    o.append(t(30, 17, "Project"))
    # left tree pane
    o.append(f'<rect x="0" y="{TOP}" width="{SPLIT}" height="{H-TOP}" fill="{PANEL}"/>')
    rows = [  # indent, arrow, open, label, selected
        (0, "▾", True, "Assets", False),
        (1, "▾", True, "Find Me", True),
    ]
    y = TOP + 12
    for indent, arrow, op, label, sel in rows:
        if sel:
            o.append(f'<rect x="0" y="{y}" width="{SPLIT}" height="20" fill="{SELECT_ROW}"/>')
        x = 12 + indent * 16
        o.append(t(x, y + 14, arrow, 10, TEXT if sel else MUTED))
        o.append(folder(x + 14, y + 3, open_=op, color="#e6e6e6" if sel else "#b5b5b5"))
        o.append(t(x + 36, y + 14, label, 12, "#ffffff" if sel else TEXT, 600 if sel else 400))
        y += 22
    # right pane: breadcrumb, grid, footer
    o.append(f'<rect x="{SPLIT+1}" y="{TOP}" width="{W-SPLIT-1}" height="{H-TOP}" fill="{GRIDBG}"/>')
    o.append(f'<rect x="{SPLIT+1}" y="{TOP}" width="{W-SPLIT-1}" height="{BAR}" fill="{PANEL}"/>')
    o.append(t(SPLIT + 14, TOP + 15, f'Assets  <tspan fill="{MUTED}">›</tspan>  Find Me', 12))
    for i, (name, color, _url) in enumerate(LINKS):
        cx = SPLIT + TILE_W * i + TILE_W / 2
        o.append(link_icon(cx, TOP + BAR + 44, color))
        o.append(t(cx, TOP + BAR + 92, name, 12, TEXT, anchor="middle"))
    fy = H - FOOT
    o.append(f'<rect x="{SPLIT+1}" y="{fy}" width="{W-SPLIT-1}" height="{FOOT}" fill="{TABBAR}"/>')
    o.append(t(SPLIT + 14, fy + 14, "Assets/Find Me", 10, MUTED))
    sx = W - 90
    o.append(f'<rect x="{sx}" y="{fy+9}" width="70" height="2" rx="1" fill="#5a5a5a"/>'
             f'<circle cx="{sx+46}" cy="{fy+10}" r="5" fill="{TEXT}"/>')
    # thin dividers exactly on the strip boundaries: browsers leave a faint seam
    # where two images meet, so a deliberate line there keeps it looking intended
    for i in range(1, len(LINKS) + 1):
        bx = SPLIT + TILE_W * i
        o.append(f'<rect x="{bx-0.5}" y="0" width="1" height="{H}" fill="#222222"/>')
    o.append('</g>')
    o.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="6" fill="none" stroke="{FRAME}"/>')
    return "\n".join(o)


def slices():
    """x ranges of the strips: left part, one strip per tile, right filler."""
    xs = [0, SPLIT] + [SPLIT + TILE_W * (i + 1) for i in range(len(LINKS))] + [W]
    return list(zip(xs[:-1], xs[1:]))


def svg(body, x0=0, x1=W):
    w = x1 - x0
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{H}" '
            f'viewBox="{x0} 0 {w} {H}">\n{body}\n</svg>')


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "assets"
    os.makedirs(out_dir, exist_ok=True)
    body = build()
    with open(os.path.join(out_dir, "project-full.svg"), "w", encoding="utf-8") as f:
        f.write(svg(body))
    for i, (a, b) in enumerate(slices()):
        with open(os.path.join(out_dir, f"project-{i}.svg"), "w", encoding="utf-8") as f:
            f.write(svg(body, a, b))
        print(f"project-{i}.svg  x={a}-{b}  width={100*(b-a)/W:.4f}%")
