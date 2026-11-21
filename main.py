#!/usr/bin/env python3
"""VELMARA - The Poster for a Place That Isn't There.

A pure-stdlib Python program (no network, no third-party packages) that
paints a vintage travel poster for Velmara, the floating isles above the
Amber Sea, and writes it to /output/entry.png (1024x1024 PNG, < 1 MiB).

The poster is drawn procedurally: layered sky gradient, low amber sun,
three floating islands with waterfalls, a crystal spire lighthouse, a
small airship, a sea of clouds, and the place name set in a hand-built
stroke-lettered title. Nothing is fetched or read from disk at runtime.
"""

import os
import struct
import zlib

W = 1024
H = 1024
OUT = "/output/entry.png"

# ---------------------------------------------------------------- palette
CREAM = (251, 243, 223)
CREAM_DIM = (238, 224, 192)
INK = (11, 46, 58)          # deep teal, for title shadow / rules
TEAL_DARK = (14, 58, 74)
TEAL_MID = (20, 88, 107)
TEAL_SOFT = (38, 122, 138)
AMBER = (232, 163, 76)
GOLD = (242, 200, 121)
SUN = (251, 227, 161)
PEACH = (246, 217, 168)
CLOUD_SHADOW = (217, 160, 140)
GRASS = (127, 163, 90)
GRASS_GOLD = (201, 164, 74)
ROCK = (107, 74, 58)
ROCK_DARK = (84, 55, 43)
CLIFF = (138, 90, 68)
CRYSTAL = (207, 234, 242)
CRYSTAL_EDGE = (90, 160, 178)
SHIP_RED = (179, 64, 46)
WINDOW = (255, 214, 130)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def get(self, x, y):
        x = max(0, min(self.w - 1, x))
        y = max(0, min(self.h - 1, y))
        i = (y * self.w + x) * 3
        return (self.px[i], self.px[i + 1], self.px[i + 2])

    def blend(self, x, y, c, a):
        """Alpha-blend colour c (0..1) over the pixel."""
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = int(self.px[i] * (1 - a) + c[0] * a)
            self.px[i + 1] = int(self.px[i + 1] * (1 - a) + c[1] * a)
            self.px[i + 2] = int(self.px[i + 2] * (1 - a) + c[2] * a)

    def rect(self, x0, y0, x1, y1, c):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        for y in range(y0, y1):
            base = y * self.w * 3
            for x in range(x0, x1):
                i = base + x * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def vgrad(self, y0, y1, stops):
        """Vertical gradient through (position 0..1, colour) stops."""
        for y in range(max(0, y0), min(self.h, y1)):
            t = (y - y0) / max(1, (y1 - y0 - 1))
            c = _interp_stops(stops, t)
            base = y * self.w * 3
            for x in range(self.w):
                i = base + x * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def disc(self, cx, cy, r, c, alpha=1.0):
        r2 = r * r
        for y in range(int(cy - r), int(cy + r) + 1):
            dy = y - cy
            dx = int((r2 - dy * dy) ** 0.5) if r2 - dy * dy > 0 else 0
            for x in range(int(cx - dx), int(cx + dx) + 1):
                if alpha >= 1.0:
                    self.set(x, y, c)
                else:
                    self.blend(x, y, c, alpha)

    def ellipse(self, cx, cy, rx, ry, c, alpha=1.0):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dy = (y - cy) / ry
            if abs(dy) >= 1:
                continue
            dx = int(rx * (1 - dy * dy) ** 0.5)
            for x in range(int(cx - dx), int(cx + dx) + 1):
                if alpha >= 1.0:
                    self.set(x, y, c)
                else:
                    self.blend(x, y, c, alpha)

    def poly(self, pts, c):
        """Scanline-fill a polygon (list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = int(min(ys)), int(max(ys))
        n = len(pts)
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            xs = []
            for i in range(n):
                x0, yy0 = pts[i]
                x1, yy1 = pts[(i + 1) % n]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    t = (y - yy0) / (yy1 - yy0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                    self.set(x, y, c)

    def thick_line(self, x0, y0, x1, y1, w, c):
        """A line of width w with round caps, drawn as swept discs."""
        dx, dy = x1 - x0, y1 - y0
        dist = (dx * dx + dy * dy) ** 0.5
        steps = max(1, int(dist))
        r = w / 2.0
        for s in range(steps + 1):
            t = s / steps
            self.disc(x0 + dx * t, y0 + dy * t, r, c)


def _interp_stops(stops, t):
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))
    return stops[-1][1]


def lerp(a, b, f):
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


# ------------------------------------------------------- stroke letterforms
# Each glyph: polylines on a 0..5 (x) by 0..7 (y) grid, y pointing down.
GLYPHS = {
    "A": [[(0, 7), (2.5, 0), (5, 7)], [(1.2, 4.6), (3.8, 4.6)]],
    "B": [[(0, 0), (0, 7)], [(0, 0), (3.2, 0), (4.6, 1.4), (3.2, 3.2), (0, 3.2)],
          [(0, 3.2), (3.2, 3.2), (4.6, 4.8), (3.2, 7), (0, 7)]],
    "E": [[(0, 0), (0, 7)], [(0, 0), (4.6, 0)], [(0, 3.5), (3.4, 3.5)],
          [(0, 7), (4.6, 7)]],
    "F": [[(0, 0), (0, 7)], [(0, 0), (4.6, 0)], [(0, 3.5), (3.4, 3.5)]],
    "H": [[(0, 0), (0, 7)], [(5, 0), (5, 7)], [(0, 3.5), (5, 3.5)]],
    "I": [[(0, 0), (5, 0)], [(2.5, 0), (2.5, 7)], [(0, 7), (5, 7)]],
    "K": [[(0, 0), (0, 7)], [(4.6, 0), (0, 3.8)], [(1.4, 3.8), (4.6, 7)]],
    "L": [[(0, 0), (0, 7)], [(0, 7), (4.6, 7)]],
    "M": [[(0, 7), (0, 0), (2.5, 4), (5, 0), (5, 7)]],
    "N": [[(0, 7), (0, 0), (5, 7), (5, 0)]],
    "O": [[(1, 0), (4, 0), (5, 1.6), (5, 5.4), (4, 7), (1, 7),
           (0, 5.4), (0, 1.6), (1, 0)]],
    "R": [[(0, 0), (0, 7)], [(0, 0), (3.2, 0), (4.6, 1.4), (3.2, 3.2), (0, 3.2)],
          [(2.2, 3.2), (4.6, 7)]],
    "S": [[(4.4, 0.8), (3, 0), (1.2, 0.4), (0.4, 2), (1.4, 3.5),
           (3.6, 3.5), (4.6, 5), (3.6, 7), (1.4, 7), (0.4, 6.2)]],
    "T": [[(0, 0), (5, 0)], [(2.5, 0), (2.5, 7)]],
    "V": [[(0, 0), (2.5, 7), (5, 0)]],
    "W": [[(0, 0), (1.2, 7), (2.5, 2.6), (3.8, 7), (5, 0)]],
    "Y": [[(0, 0), (2.5, 3.6), (5, 0)], [(2.5, 3.6), (2.5, 7)]],
    " ": [],
}


def draw_text(cv, text, cx, top, cap_h, stroke, colour, spacing=None):
    """Draw centred capitals with the stroke font. Returns text width."""
    if spacing is None:
        spacing = cap_h * 0.32
    unit = cap_h / 7.0          # pixels per grid unit (vertical)
    adv = 5 * unit + spacing   # advance per glyph
    total = len(text) * adv - spacing
    x = cx - total / 2.0
    for ch in text:
        for stroke_pts in GLYPHS.get(ch, []):
            for (ax, ay), (bx, by) in zip(stroke_pts, stroke_pts[1:]):
                cv.thick_line(x + ax * unit, top + ay * unit,
                              x + bx * unit, top + by * unit,
                              stroke, colour)
        x += adv
    return total


# ------------------------------------------------------------------ scene
def paint(cv):
    # --- sky: deep teal dawn at top melting into amber at the horizon
    cv.vgrad(0, 1024, [
        (0.00, TEAL_DARK),
        (0.30, TEAL_MID),
        (0.52, TEAL_SOFT),
        (0.66, AMBER),
        (0.80, GOLD),
        (1.00, (244, 214, 150)),
    ])

    # --- sun: low, large disc with one very soft halo, no hard ring
    cv.disc(712, 452, 138, SUN, alpha=0.07)
    cv.disc(712, 452, 108, SUN)
    cv.disc(712, 452, 96, lerp(SUN, (255, 244, 205), 0.5))

    # --- distant haze isles, small and pale amber, for depth
    cv.poly([(110, 440), (165, 424), (225, 440), (205, 460), (135, 460)],
            lerp(GOLD, CREAM, 0.55))
    cv.poly([(880, 400), (920, 388), (962, 400), (945, 416), (898, 416)],
            lerp(GOLD, CREAM, 0.5))

    # --- airship drifting in from the right, clear of the subtitle
    ship_x, ship_y = 868, 322
    cv.ellipse(ship_x, ship_y, 74, 26, SHIP_RED)
    cv.ellipse(ship_x, ship_y - 4, 74, 20, lerp(SHIP_RED, CREAM, 0.25))
    cv.poly([(ship_x - 74, ship_y), (ship_x - 96, ship_y - 8),
             (ship_x - 74, ship_y - 12)], lerp(SHIP_RED, INK, 0.25))
    cv.poly([(ship_x - 18, ship_y + 22), (ship_x + 18, ship_y + 22),
             (ship_x + 12, ship_y + 38), (ship_x - 12, ship_y + 38)],
            (232, 214, 170))
    cv.thick_line(ship_x, ship_y + 26, ship_x, ship_y + 38, 2, INK)

    # --- birds
    for bx, by, s in ((250, 300, 16), (300, 262, 12), (205, 350, 11),
                      (880, 380, 13), (930, 340, 10)):
        cv.thick_line(bx - s, by, bx, by - s * 0.45, 3, INK)
        cv.thick_line(bx, by - s * 0.45, bx + s, by, 3, INK)

    # --- main floating isle (left-centre) with the Crystal Spire
    isle_main(cv)
    # --- second isle (right) and small isle (far left)
    isle_right(cv)
    isle_small(cv)

    # --- sea of clouds, layered scallops rising from the bottom
    cloud_sea(cv)

    # --- waterfalls from the main isle, spilling into the clouds
    for fx, fw in ((330, 14), (470, 18), (560, 11)):
        cv.poly([(fx, 640), (fx + fw, 640), (fx + fw - 6, 800), (fx - 2, 800)],
                lerp(CRYSTAL, CREAM, 0.55))
        cv.poly([(fx + 2, 640), (fx + fw - 3, 640), (fx + fw - 6, 720),
                 (fx - 1, 720)], CREAM)

    # --- title block, set into the sky with a soft shadow
    draw_text(cv, "VELMARA", 512, 96, 118, 17, INK)
    draw_text(cv, "VELMARA", 512, 90, 118, 17, CREAM)
    draw_text(cv, "ISLES ABOVE THE AMBER SEA", 512, 232, 34, 5,
              lerp(CREAM, GOLD, 0.35))

    # --- bottom line on a deep teal ribbon so it stays legible
    cv.rect(18, 926, 1006, 992, INK)
    cv.rect(18, 926, 1006, 929, lerp(INK, GOLD, 0.45))
    draw_text(cv, "WHERE THE SEA FLOATS", 512, 946, 26, 4, CREAM)

    # --- vintage frame
    cv.rect(0, 0, 1024, 18, CREAM)
    cv.rect(0, 1006, 1024, 1024, CREAM)
    cv.rect(0, 0, 18, 1024, CREAM)
    cv.rect(1006, 0, 1024, 1024, CREAM)
    cv.rect(30, 30, 994, 33, lerp(CREAM, INK, 0.35))
    cv.rect(30, 991, 994, 994, lerp(CREAM, INK, 0.35))
    cv.rect(30, 30, 33, 994, lerp(CREAM, INK, 0.35))
    cv.rect(991, 30, 994, 994, lerp(CREAM, INK, 0.35))


def isle_main(cv):
    # rocky underside: an inverted cone with a ragged edge
    cv.poly([(212, 566), (300, 566), (392, 566), (470, 566), (560, 566),
             (600, 566), (520, 660), (470, 712), (430, 668), (380, 700),
             (330, 648), (268, 690), (236, 620)], ROCK)
    cv.poly([(300, 566), (470, 566), (520, 660), (470, 712), (430, 668),
             (380, 700), (330, 648)], ROCK_DARK)
    # grassy top, slightly domed
    cv.poly([(200, 566), (612, 566), (590, 540), (540, 524), (430, 516),
             (300, 524), (222, 542)], GRASS)
    cv.poly([(200, 566), (612, 566), (590, 540), (430, 528), (300, 536)],
            lerp(GRASS, GRASS_GOLD, 0.35))
    # cliff rim highlight
    cv.thick_line(212, 564, 600, 564, 4, lerp(GRASS, CREAM, 0.4))

    # tiny cottages with warm windows along the top
    for hx, hy, hw in ((268, 500, 34), (330, 508, 28), (520, 502, 32)):
        cv.rect(hx, hy, hx + hw, hy + 26, CREAM_DIM)
        cv.poly([(hx - 4, hy), (hx + hw // 2, hy - 14), (hx + hw + 4, hy)],
                SHIP_RED)
        cv.rect(hx + hw // 2 - 4, hy + 10, hx + hw // 2 + 4, hy + 18, WINDOW)

    # --- the Crystal Spire: tall faceted lighthouse, the one landmark
    sx = 430
    cv.poly([(sx - 26, 516), (sx - 12, 330), (sx + 12, 330), (sx + 26, 516)],
            CRYSTAL)
    cv.poly([(sx - 26, 516), (sx - 12, 330), (sx, 330), (sx, 516)],
            lerp(CRYSTAL, CRYSTAL_EDGE, 0.35))
    cv.poly([(sx - 12, 330), (sx + 12, 330), (sx + 20, 300), (sx - 20, 300)],
            CRYSTAL_EDGE)
    cv.disc(sx, 292, 12, SUN)
    cv.disc(sx, 292, 20, SUN, alpha=0.35)
    # facet lines
    cv.thick_line(sx - 18, 470, sx - 8, 350, 2, CRYSTAL_EDGE)
    cv.thick_line(sx + 18, 470, sx + 8, 350, 2, CRYSTAL_EDGE)
    cv.thick_line(sx - 22, 430, sx + 22, 430, 2, CRYSTAL_EDGE)
    # warm light spilling from the spire base
    cv.ellipse(sx, 522, 60, 10, WINDOW, alpha=0.5)


def isle_right(cv):
    cv.poly([(688, 640), (760, 640), (830, 640), (900, 640), (940, 640),
             (880, 716), (820, 760), (780, 706), (730, 736), (700, 676)],
            ROCK)
    cv.poly([(760, 640), (900, 640), (880, 716), (820, 760), (780, 706)],
            ROCK_DARK)
    cv.poly([(680, 640), (948, 640), (920, 618), (830, 606), (720, 616)],
            lerp(GRASS, GRASS_GOLD, 0.45))
    # a lone windmill on the right isle
    wx, wy = 812, 606
    cv.poly([(wx - 8, wy), (wx + 8, wy), (wx + 5, wy - 44), (wx - 5, wy - 44)],
            CREAM_DIM)
    cv.poly([(wx - 4, wy - 44), (wx + 4, wy - 44), (wx, wy - 58)],
            SHIP_RED)
    for ang in (0.3, 1.9, 3.5, 5.1):
        import math
        dx = int(26 * math.cos(ang))
        dy = int(26 * math.sin(ang))
        cv.thick_line(wx, wy - 46, wx + dx, wy - 46 + dy, 4, INK)
    # small waterfall off the right isle
    cv.poly([(700, 640), (712, 640), (708, 730), (698, 730)],
            lerp(CRYSTAL, CREAM, 0.55))


def isle_small(cv):
    cv.poly([(72, 700), (130, 700), (190, 700), (232, 700),
             (200, 762), (160, 792), (120, 748), (88, 762)], ROCK)
    cv.poly([(64, 700), (240, 700), (218, 682), (150, 672), (84, 684)],
            GRASS)
    # a single pine on the small isle
    px, py = 150, 676
    cv.poly([(px - 22, py), (px, py - 44), (px + 22, py)], (46, 96, 62))
    cv.poly([(px - 16, py - 22), (px, py - 58), (px + 16, py - 22)],
            (58, 118, 76))
    cv.rect(px - 3, py, px + 3, py + 8, ROCK_DARK)


def cloud_sea(cv):
    # Three layered bands of scalloped cloud, kept low so the isles stay
    # visible above them; cream over peach over gold.
    bands = [
        (782, 118, lerp(PEACH, GOLD, 0.25), -30),
        (838, 104, PEACH, 40),
        (898, 96, CREAM, -15),
        (956, 88, lerp(CREAM, (255, 255, 255), 0.5), 25),
    ]
    for base_y, r, col, off in bands:
        # rolling base
        cv.rect(0, base_y + r // 2, 1024, 1024, col)
        x = -40 + off
        while x < 1024 + 40:
            cv.disc(x, base_y + r // 3, r, col)
            x += int(r * 1.15)
        # soft shadow scallops tucked under each crest
        x = 20 + off
        while x < 1024 + 40:
            cv.disc(x, base_y + r // 2 + 10, r // 2, CLOUD_SHADOW, alpha=0.22)
            x += int(r * 1.3)


# ------------------------------------------------------------------- png out
def write_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    cv = Canvas(W, H)
    paint(cv)
    n = write_png(cv, OUT)
    print(f"wrote {OUT}: {W}x{H}, {n} bytes")


if __name__ == "__main__":
    main()
