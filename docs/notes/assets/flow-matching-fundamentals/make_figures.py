"""Build the flow matching diagrams using only the Python standard library."""
from pathlib import Path
import base64
import html
import math
import random
import struct
import zlib

ROOT = Path(__file__).resolve().parent
INK, MUTED, TEAL, ORANGE, BLUE = "#223942", "#61747e", "#187c80", "#bd633e", "#426fa4"

def text(x, y, value, size=22, fill=INK, anchor="start", weight=400):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(value))}</text>'

def line(x1, y1, x2, y2, color=MUTED, width=2, arrow=False, dash=False):
    extra = f' marker-end="url(#{color[1:]})"' if arrow else ""
    extra += ' stroke-dasharray="7 6"' if dash else ""
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{width}"{extra}/>'

def dot(x, y, color, r=5, fill=None):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{fill or color}" stroke="{color}" stroke-width="2"/>'

def circle(x, y, r, color, width=2, dash=False):
    extra = ' stroke-dasharray="6 5"' if dash else ""
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="none" stroke="{color}" stroke-width="{width}"{extra}/>'

def polyline(points, color, width=3):
    coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>'

def svg(name, width, height, title, parts):
    markers = "".join(f'<marker id="{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>' for c in [MUTED, TEAL, ORANGE, BLUE, INK])
    result = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{html.escape(title)}</title><defs>{markers}</defs><rect width="100%" height="100%" fill="white"/><g font-family="Arial, Helvetica, sans-serif">{"".join(parts)}</g></svg>'
    (ROOT/name).write_text(result, encoding="utf-8")

def png_url(rgb_rows):
    height, width = len(rgb_rows), len(rgb_rows[0])
    raw = bytearray()
    for row in rgb_rows:
        raw.append(0)
        for r, g, b in row:
            raw += bytes((r, g, b))
    def chunk(kind, data):
        return struct.pack(">I", len(data))+kind+data+struct.pack(">I", zlib.crc32(kind+data) & 0xffffffff)
    blob = b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))+chunk(b"IDAT", zlib.compress(bytes(raw), 9))+chunk(b"IEND", b"")
    return "data:image/png;base64,"+base64.b64encode(blob).decode()

def arc_and_line():
    # The axes are the coefficients on the image and on the noise.
    ox, oy, side = 90, 430, 360
    px = lambda a: ox+a*side
    py = lambda s: oy-s*side
    parts = [line(ox, oy, ox+side+25, oy, MUTED, 1.5, True), line(ox, oy, ox, oy-side-25, MUTED, 1.5, True),
             text(ox+side+20, oy+50, "image coefficient", 17, MUTED, "end"), text(ox-12, oy-side-34, "noise coefficient", 17, MUTED),
             text(ox-8, oy+22, "0", 16, MUTED, "end"), text(px(1), oy+24, "1", 16, MUTED, "middle"), text(ox-10, py(1)+6, "1", 16, MUTED, "end")]
    abar, arc = 1.0, [(1.0, 0.0)]
    for t in range(1, 1001):
        abar *= 1-(.0001+(.02-.0001)*(t-1)/999)
        arc.append((math.sqrt(abar), math.sqrt(1-abar)))
    parts.append(polyline([(px(a), py(s)) for a, s in arc], TEAL, 3.5))
    parts.append(line(px(0), py(1), px(1), py(0), ORANGE, 3.5))
    for t in range(0, 1001, 100):
        a, s = arc[t]
        parts.append(dot(px(a), py(s), TEAL, 4.5))
    for k in range(11):
        t = k/10
        parts.append(dot(px(t), py(1-t), ORANGE, 4.5, "white"))
    a, s = arc[300]
    a_l, s_l = a/(a+s), s/(a+s)
    parts += [line(ox, oy, px(a)+(px(a)-ox)*.08, py(s)+(py(s)-oy)*.08, BLUE, 1.6, dash=True),
              dot(px(a), py(s), BLUE, 6), dot(px(a_l), py(s_l), BLUE, 6, "white"),
              text(px(a)+12, py(s)-10, "diffusion step 300", 15, BLUE), text(px(a_l)+5, py(s_l)+52, "÷ (aₜ + σₜ)", 15, BLUE, "middle")]
    parts += [dot(px(1), py(0), INK, 7), text(px(1)+14, oy-14, "image", 17, INK, "start", 600),
              dot(px(0), py(1), INK, 7), text(ox+14, py(1)-14, "noise", 17, INK, "start", 600)]
    lx = 520
    parts += [line(lx, 120, lx+40, 120, TEAL, 3.5), dot(lx+20, 120, TEAL, 4.5), text(lx+52, 126, "Diffusion: (aₜ, σₜ)", 18),
              text(lx+52, 150, "dots every 100 of 1,000 steps", 15, MUTED),
              line(lx, 200, lx+40, 200, ORANGE, 3.5), dot(lx+20, 200, ORANGE, 4.5, "white"), text(lx+52, 206, "Flow matching: (t, 1 − t)", 18),
              text(lx+52, 230, "dots every 0.1 in t", 15, MUTED)]
    svg("arc-and-line.svg", 860, 500, "The diffusion arc and the flow matching line in image and noise coefficients", parts)
    print(f"arc step 300: a={a:.4f}, sigma={s:.4f}, line t={a_l:.4f}")

def conditional_path():
    # One destination image in 2D; the cloud is N(t*x1, (1-t)^2 I).
    x1 = (4.0, 2.4)
    scale, ox, oy = 72, 220, 330
    P = lambda x, y: (ox+x*scale, oy-y*scale)
    parts = [line(*P(-2.8, 0), *P(4.8, 0), "#e4ebee", 1), line(*P(0, -2.8), *P(0, 3.4), "#e4ebee", 1)]
    rng = random.Random(3393)
    starts = [(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(7)]
    for x, y in starts:
        parts.append(line(*P(x, y), *P(*x1), "#c9d6db", 1.4))
    colors = [(0, BLUE), (.5, TEAL), (.9, ORANGE)]
    for t, c in colors:
        cx, cy = P(t*x1[0], t*x1[1])
        parts.append(circle(cx, cy, (1-t)*scale, c, 2.4))
        parts.append(dot(cx, cy, c, 3.5))
    for x, y in starts:
        parts.append(dot(*P(x, y), MUTED, 3.5, "white"))
    parts.append(line(*P(0, 0), *P(*x1), INK, 1.6, dash=True))
    parts += [dot(*P(*x1), INK, 6.5), text(P(*x1)[0]+12, P(*x1)[1]-10, "x₁", 20, INK, weight=600)]
    lx = 600
    for i, (t, c) in enumerate(colors):
        y = 90+i*42
        parts += [circle(lx+14, y-6, 11, c, 2.4), text(lx+36, y, f"t = {t:g}", 18, c)]
    parts += [text(lx, 230, "circles: 1 std of", 15, MUTED),
              text(lx, 256, "N(t·x₁, (1 − t)² I)", 15, MUTED),
              dot(lx+6, 296, MUTED, 3.5, "white"), text(lx+18, 301, "noise draws x₀ and their", 15, MUTED),
              text(lx+18, 321, "straight paths to x₁", 15, MUTED)]
    svg("conditional-path.svg", 860, 560, "The conditional probability path toward one image", parts)

def marginal_path():
    # Three equally likely data points in 2D; p_t is a mixture of N(t*x1, (1-t)^2 I).
    data = [(-2.0, 1.6), (2.2, 1.2), (0.4, -2.1)]
    lo, hi, n, size = -3.2, 3.2, 150, 280
    def components(x, y, t):
        s2 = (1-t)**2
        return [math.exp(-((x-t*a)**2+(y-t*b)**2)/(2*s2))/(2*math.pi*s2)/3 for a, b in data]
    parts = []
    for panel, t in enumerate([0, .5, .9]):
        x0, y0 = 30+panel*(size+30), 70
        dens = [[0.0]*n for _ in range(n)]
        for r in range(n):
            for c in range(n):
                x, y = lo+(c+.5)*(hi-lo)/n, hi-(r+.5)*(hi-lo)/n
                dens[r][c] = sum(components(x, y, t))
        peak = max(max(row) for row in dens)
        rows = []
        for row in dens:
            out = []
            for d in row:
                w = min(1.0, (d/peak)**.6)
                out.append(tuple(round(255+(v-255)*w) for v in (24, 124, 128)))
            rows.append(out)
        parts.append(f'<image x="{x0}" y="{y0}" width="{size}" height="{size}" href="{png_url(rows)}"/>')
        parts.append(f'<rect x="{x0}" y="{y0}" width="{size}" height="{size}" fill="none" stroke="#d3e1e4"/>')
        P = lambda x, y: (x0+(x-lo)/(hi-lo)*size, y0+(hi-y)/(hi-lo)*size)
        # Average velocity u_t(x) = sum_i w_i (x1_i - x)/(1 - t); arrows show direction only.
        for gx in range(-3, 4):
            for gy in range(-3, 4):
                x, y = gx*.85, gy*.85
                comp = components(x, y, t)
                total = sum(comp)
                if total < 1e-300:
                    continue
                ux = sum(w*(a-x) for w, (a, b) in zip(comp, data))/total/(1-t)
                uy = sum(w*(b-y) for w, (a, b) in zip(comp, data))/total/(1-t)
                norm = math.hypot(ux, uy)
                if norm < 1e-9:
                    continue
                sx, sy = P(x, y)
                parts.append(line(sx, sy, sx+ux/norm*17, sy-uy/norm*17, INK, 1.3, True))
        for a, b in data:
            parts.append(dot(*P(a, b), ORANGE, 5))
        parts.append(text(x0+size/2, y0-18, f"t = {t:g}", 20, INK, "middle", 600))
    mean = (sum(a for a, _ in data)/3, sum(b for _, b in data)/3)
    svg("marginal-path.svg", 960, 380, "The marginal probability path and average velocity for three data points", parts)
    print(f"data mean={mean}")

arc_and_line()
conditional_path()
marginal_path()
