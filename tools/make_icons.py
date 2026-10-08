#!/usr/bin/env python3
"""Draw the Room Reset cat mascot and write it out as the app's PNG icons.

Pure standard library: no Pillow, no numpy. The cat is described as a stack of
math shapes (ellipses, triangles, stroked arcs); every pixel is sampled on a
3x3 grid so the edges come out smooth. The 512px master is then area-averaged
down to the smaller sizes.

Run:  python3 tools/make_icons.py
"""
import math, os, struct, zlib

PINK   = (255, 211, 220, 255)
DEEP   = (255, 194, 207, 255)
PAPER  = (255, 253, 251, 255)
INK    = (30, 27, 28, 255)
PEACH  = (255, 220, 196, 255)
CLEAR  = (0, 0, 0, 0)

S = 512          # master size
SS = 3           # supersample grid per axis
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")


# ---------- shape helpers (each returns a predicate: is this point inside?) ----------

def ellipse(cx, cy, rx, ry):
    return lambda x, y: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0


def ring(cx, cy, rx, ry, w):
    """Outline of an ellipse, w px thick."""
    inner = ellipse(cx, cy, rx - w / 2, ry - w / 2)
    outer = ellipse(cx, cy, rx + w / 2, ry + w / 2)
    return lambda x, y: outer(x, y) and not inner(x, y)


def _side(ax, ay, bx, by, x, y):
    return (bx - ax) * (y - ay) - (by - ay) * (x - ax)


def triangle(a, b, c):
    def inside(x, y):
        d1 = _side(a[0], a[1], b[0], b[1], x, y)
        d2 = _side(b[0], b[1], c[0], c[1], x, y)
        d3 = _side(c[0], c[1], a[0], a[1], x, y)
        return (d1 >= 0 and d2 >= 0 and d3 >= 0) or (d1 <= 0 and d2 <= 0 and d3 <= 0)
    return inside


def arc(cx, cy, r, w, a0, a1):
    """A stroked circular arc, angles in degrees, 0 = east, growing clockwise
    (screen coords, y down)."""
    a0, a1 = math.radians(a0), math.radians(a1)

    def inside(x, y):
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy)
        if abs(d - r) > w / 2:
            return False
        a = math.atan2(dy, dx) % (2 * math.pi)
        lo, hi = a0 % (2 * math.pi), a1 % (2 * math.pi)
        return lo <= a <= hi if lo <= hi else (a >= lo or a <= hi)
    return inside


def rounded_rect(x0, y0, x1, y1, r):
    def inside(x, y):
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        cx = min(max(x, x0 + r), x1 - r)
        cy = min(max(y, y0 + r), y1 - r)
        return math.hypot(x - cx, y - cy) <= r
    return inside


# ---------- the mascot ----------

def build(bg):
    """Painting order, back to front. bg=None leaves the corners transparent."""
    layers = []
    if bg is not None:
        layers.append((rounded_rect(0, 0, S - 1, S - 1, S * 0.22), bg))

    # ears: black wedge first, then a smaller pink wedge tucked inside it
    for sign in (-1, 1):
        tip   = (256 + sign * 138,  52)
        outer = (256 + sign * 152, 198)
        inner = (256 + sign *  58, 150)
        layers.append((triangle(tip, outer, inner), INK))
        layers.append((triangle((256 + sign * 136, 82),
                                (256 + sign * 138, 176),
                                (256 + sign * 84, 146)), DEEP))

    # head
    layers.append((ellipse(256, 300, 158, 140), INK))
    layers.append((ellipse(256, 300, 146, 128), PAPER))

    # nose
    layers.append((triangle((238, 292), (274, 292), (256, 312)), PEACH))
    layers.append((arc(256, 292, 18, 5, 0, 180), INK))

    # cheeks
    layers.append((ellipse(152, 338, 28, 17), DEEP))
    layers.append((ellipse(360, 338, 28, 17), DEEP))

    # eyes
    layers.append((ellipse(200, 282, 18, 18), INK))
    layers.append((ellipse(312, 282, 18, 18), INK))

    # two-humped smile
    layers.append((arc(242, 330, 18, 9, 10, 170), INK))
    layers.append((arc(278, 330, 18, 9, 10, 170), INK))
    return layers


# ---------- rasterise ----------

def render(bg):
    layers = build(bg)
    step = 1.0 / SS
    off = step / 2
    rows = []
    for py in range(S):
        row = bytearray()
        for px in range(S):
            r = g = b = a = 0
            for sy in range(SS):
                y = py + off + sy * step
                for sx in range(SS):
                    x = px + off + sx * step
                    col = CLEAR
                    for inside, c in layers:
                        if inside(x, y):
                            col = c
                    r += col[0] * col[3]
                    g += col[1] * col[3]
                    b += col[2] * col[3]
                    a += col[3]
            n = SS * SS
            if a:
                row += bytes((round(r / a), round(g / a), round(b / a), round(a / n)))
            else:
                row += b"\0\0\0\0"
        rows.append(bytes(row))
    return rows


def downscale(rows, size):
    """Area-average the master down to `size` px, premultiplying so that
    transparent pixels don't bleed dark edges into the result."""
    scale = len(rows) / size
    out = []
    for y in range(size):
        y0, y1 = int(y * scale), max(int(y * scale) + 1, int((y + 1) * scale))
        row = bytearray()
        for x in range(size):
            x0, x1 = int(x * scale), max(int(x * scale) + 1, int((x + 1) * scale))
            r = g = b = a = 0
            n = 0
            for yy in range(y0, y1):
                src = rows[yy]
                for xx in range(x0, x1):
                    i = xx * 4
                    sa = src[i + 3]
                    r += src[i] * sa
                    g += src[i + 1] * sa
                    b += src[i + 2] * sa
                    a += sa
                    n += 1
            if a:
                row += bytes((round(r / a), round(g / a), round(b / a), round(a / n)))
            else:
                row += b"\0\0\0\0"
        out.append(bytes(row))
    return out


def write_png(path, rows):
    size = len(rows)
    raw = b"".join(b"\0" + r for r in rows)

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    print(f"  {os.path.basename(path)}  {size}x{size}  {len(png) / 1024:.1f} KB")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)

    print("drawing the cat on pink (app + home screen icons)…")
    solid = render(PINK)
    write_png(os.path.join(OUT, "icon-512.png"), solid)
    write_png(os.path.join(OUT, "icon-192.png"), downscale(solid, 192))
    write_png(os.path.join(OUT, "apple-touch-icon.png"), downscale(solid, 180))
    write_png(os.path.join(OUT, "favicon-32.png"), downscale(solid, 32))

    # Android masks icons to a circle and crops ~10% off every edge, so the
    # maskable version keeps the cat small inside a full-bleed pink square.
    print("drawing the padded maskable version (Android)…")
    pad = render(None)
    canvas = []
    inset = round(S * 0.14)
    inner = downscale(pad, S - inset * 2)
    for y in range(S):
        row = bytearray()
        for x in range(S):
            sx, sy = x - inset, y - inset
            if 0 <= sx < len(inner) and 0 <= sy < len(inner):
                i = sx * 4
                src = inner[sy]
                px = (src[i], src[i + 1], src[i + 2], src[i + 3])
            else:
                px = CLEAR
            a = px[3] / 255
            row += bytes((round(px[0] * a + PINK[0] * (1 - a)),
                          round(px[1] * a + PINK[1] * (1 - a)),
                          round(px[2] * a + PINK[2] * (1 - a)), 255))
        canvas.append(bytes(row))
    write_png(os.path.join(OUT, "icon-maskable-512.png"), canvas)
    print("done ♡")
