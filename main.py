#!/usr/bin/env python3
"""THE WORLD IN A DAY -- front page for Monday 23 November 2026.

A single Python program (standard library only, no files read, no
network) paints a whole newspaper front page from code and writes it
to $MAKEFUN_OUTPUT_DIR/entry.png. The page is drawn by a small
software canvas: rectangles, lines, discs and filled polygons, plus a
hand-built 5x7 bitmap typeface rendered at several scales, and a
built-in PNG writer on top of zlib. Everything is deterministic, so
two runs write byte-identical output.

The front page sums up Monday 23 November 2026 as reported that day:
the COP31 climate summit in Antalya collapsing without a deal, the
Strait of Hormuz tanker crisis, Houthi strikes on Riyadh for a third
straight day, a Russian drone strike on a Kyiv-region apartment
block, the South Korean education minister resigning over an AI
exam-cheating scandal, and Nepal's prime minister holding talks with
India's prime minister in New Delhi.
"""

import math
import os
import struct
import zlib

PAGE_W = 1024
PAGE_H = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 231)     # warm newsprint
INK = (26, 24, 22)          # body ink
RED = (178, 32, 28)         # accent red
NAVY = (30, 64, 128)        # section navy
GOLD = (196, 150, 36)       # badge gold
GREY = (112, 110, 102)      # caption grey
RULE = (206, 202, 190)      # pale rule
SKY = (172, 200, 220)       # scene sky
SEA = (46, 96, 140)         # deep sea
SEALIGHT = (120, 168, 200)  # light sea
LAND = (56, 132, 70)        # globe landmass
SMOKE = (150, 148, 142)     # smoke grey
FLAME = (226, 106, 26)      # fire orange
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
SAND = (214, 190, 148)      # desert sand
GREEN = (34, 120, 60)
SAFFRON = (255, 153, 51)


# ------------------------------------------------------------------ canvas
class Canvas:
    """A flat RGB pixel buffer with primitive drawing operations."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        self.fill(0, 0, w, h, bg)

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = c[0]
            self.buf[i + 1] = c[1]
            self.buf[i + 2] = c[2]

    def fill(self, x, y, w, h, c):
        xa = max(0, x)
        ya = max(0, y)
        xb = min(self.w, x + w)
        yb = min(self.h, y + h)
        if xa >= xb or ya >= yb:
            return
        row = bytes(c) * (xb - xa)
        for yy in range(ya, yb):
            s = (yy * self.w + xa) * 3
            self.buf[s:s + len(row)] = row

    def outline(self, x, y, w, h, c, t=2):
        self.fill(x, y, w, t, c)
        self.fill(x, y + h - t, w, t, c)
        self.fill(x, y, t, h, c)
        self.fill(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            if t <= 1:
                self.px(x, y, c)
            else:
                self.fill(x - t // 2, y - t // 2, t, t, c)
            if x == x1 and y == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, c):
        r2 = r * r
        for dy in range(-r, r + 1):
            span = int(math.sqrt(max(0, r2 - dy * dy)))
            self.fill(cx - span, cy + dy, span * 2 + 1, 1, c)

    def circle(self, cx, cy, r, c, t=2):
        for k in range(t):
            rr = r - k
            steps = max(24, rr * 6)
            for s in range(steps):
                a = 2.0 * math.pi * s / steps
                self.px(cx + int(rr * math.cos(a)),
                        cy + int(rr * math.sin(a)), c)

    def ellipse(self, cx, cy, rx, ry, c):
        for dy in range(-ry, ry + 1):
            span = int(rx * math.sqrt(max(0.0, 1.0 - (dy * dy) / float(ry * ry))))
            self.fill(cx - span, cy + dy, span * 2 + 1, 1, c)

    def poly(self, pts, c):
        """Scanline fill, even-odd rule."""
        top = max(0, min(p[1] for p in pts))
        bot = min(self.h - 1, max(p[1] for p in pts))
        for y in range(top, bot + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                xa = int(math.ceil(xs[j]))
                xb = int(math.floor(xs[j + 1]))
                if xb >= xa:
                    self.fill(xa, y, xb - xa + 1, 1, c)


# -------------------------------------------------------------- PNG writer
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, canvas):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.buf[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.w, canvas.h,
                                       8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# --------------------------------------------------------------- bitmap font
# Each glyph is 7 rows of 5 cells; '#' is ink, '.' is blank.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "|": ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    "^": ("00100", "01010", "10001", "00000", "00000", "00000", "00000"),
    "~": ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
    "{": ("00010", "00100", "00100", "01100", "00100", "00100", "00010"),
    "}": ("01000", "00100", "00100", "00110", "00100", "00100", "01000"),
    "\\": ("10000", "01000", "01000", "00100", "00010", "00010", "00001"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "00010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11110", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "\u00b0": ("00100", "01010", "00100", "00000", "00000", "00000", "00000"),
    "\u2014": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "\u2019": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "\u201c": ("01010", "01010", "00100", "00000", "00000", "00000", "00000"),
    "\u201d": ("01010", "01010", "00100", "00000", "00000", "00000", "00000"),
    "\u00e9": ("00010", "00100", "01110", "10001", "11111", "10000", "01110"),
}

CHAR_W = 5
CHAR_H = 7


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_char(cv, x, y, ch, scale, color):
    glyph = FONT.get(ch)
    if glyph is None:
        return
    for row in range(CHAR_H):
        bits = glyph[row]
        for col in range(CHAR_W):
            if bits[col] == "1":
                cv.fill(x + col * scale, y + row * scale, scale, scale, color)


def draw_text(cv, x, y, text, scale, color):
    cx = x
    for ch in text:
        draw_char(cv, cx, y, ch, scale, color)
        cx += 6 * scale
    return cx


def draw_centered(cv, cx, y, text, scale, color):
    draw_text(cv, cx - text_width(text, scale) // 2, y, text, scale, color)


def wrap_lines(text, max_w, scale):
    """Greedy word wrap into lines that fit max_w pixels at scale."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, text, max_w, scale, color, leading=None):
    if leading is None:
        leading = 9 * scale
    for line in wrap_lines(text, max_w, scale):
        draw_text(cv, x, y, line, scale, color)
        y += leading
    return y

# ------------------------------------------------------------- illustrations
def draw_globe_crack(cv, x, y, w, h):
    """A warming globe: blue sphere, green land, a red crack, a rising
    thermometer bar at its side."""
    cv.fill(x, y, w, h, SKY)
    cx, cy = x + w // 2 - 20, y + h // 2
    r = min(w, h) // 2 - 14
    cv.disc(cx, cy, r, SEA)
    cv.ellipse(cx - r // 2, cy - r // 3, r // 3, r // 5, LAND)
    cv.ellipse(cx + r // 4, cy + r // 4, r // 4, r // 6, LAND)
    cv.ellipse(cx + r // 5, cy - r // 2, r // 5, r // 7, LAND)
    cv.ellipse(cx - r // 3, cy + r // 2, r // 5, r // 8, LAND)
    # white polar caps
    cv.ellipse(cx, cy - r + 6, r // 2, 8, WHITE)
    cv.ellipse(cx, cy + r - 6, r // 3, 7, WHITE)
    cv.circle(cx, cy, r, INK, 2)
    # red crack down the globe
    cv.line(cx - 6, cy - r + 8, cx + 4, cy - 10, RED, 3)
    cv.line(cx + 4, cy - 10, cx - 8, cy + 12, RED, 3)
    cv.line(cx - 8, cy + 12, cx + 2, cy + r - 8, RED, 3)
    # thermometer at the right edge
    tx = x + w - 26
    cv.fill(tx, y + 14, 10, h - 40, WHITE)
    cv.outline(tx, y + 14, 10, h - 40, INK, 1)
    cv.fill(tx + 2, y + h - 46, 6, 14, RED)
    cv.disc(tx + 5, y + h - 26, 9, RED)
    cv.circle(tx + 5, y + h - 26, 9, INK, 1)
    cv.fill(tx + 2, y + 20, 6, 26, RED)
    draw_text(cv, x + 6, y + h - 18, "ANTALYA, TURKIYE", 1, GREY)


def draw_tanker_sea(cv, x, y, w, h):
    """A tanker on a grey-blue sea, a sea mine bobbing beside it."""
    cv.fill(x, y, w, h, SKY)
    # sea
    cv.fill(x, y + h // 2, w, h - h // 2, SEA)
    for k in range(3):
        yy = y + h // 2 + 14 + k * 16
        cv.fill(x + 8 + k * 30, yy, w - 60 - k * 20, 3, SEALIGHT)
    # tanker hull
    hy = y + h // 2 - 8
    cv.poly([(x + 14, hy), (x + w - 30, hy), (x + w - 44, hy + 34),
             (x + 26, hy + 34)], RED)
    # deck containers as separate coloured boxes
    cv.fill(x + 20, hy - 22, w - 110, 22, (40, 40, 44))
    cv.fill(x + 26, hy - 18, 18, 14, WHITE)
    cv.fill(x + 50, hy - 18, 18, 14, GOLD)
    cv.fill(x + 74, hy - 18, 18, 14, (200, 60, 50))
    cv.fill(x + 98, hy - 18, 18, 14, SEALIGHT)
    # small sun in the sky strip above the deck
    cv.disc(x + 44, y + 10, 9, GOLD)
    # funnel with smoke
    cv.fill(x + w - 66, hy - 34, 12, 14, INK)
    cv.disc(x + w - 60, hy - 44, 8, SMOKE)
    cv.disc(x + w - 48, hy - 54, 10, SMOKE)
    cv.disc(x + w - 34, hy - 62, 7, SMOKE)
    # sea mine, clear of the caption at the left
    mx, my = x + w - 46, y + h - 26
    cv.disc(mx, my, 9, INK)
    for a in range(0, 360, 45):
        rad = math.radians(a)
        cv.line(mx, my, mx + int(13 * math.cos(rad)),
                my + int(13 * math.sin(rad)), INK, 2)
    draw_text(cv, x + 6, y + h - 16, "STRAIT OF HORMUZ", 1, WHITE)


def draw_riyadh_skyline(cv, x, y, w, h):
    """A desert-city skyline at dusk, a missile arc intercepted above it."""
    cv.fill(x, y, w, h, (232, 196, 150))
    cv.disc(x + w - 36, y + 24, 15, (240, 120, 40))
    # skyline blocks, heights scaled to fit inside the panel
    base = y + h - 26
    max_h = h - 40
    heights = [52, 84, 64, 110, 74, 96, 58, 120, 70, 88]
    bw = w // len(heights)
    for i, hh0 in enumerate(heights):
        hh = int(hh0 * max_h / 120)
        bx = x + i * bw + 3
        cv.fill(bx, base - hh, bw - 6, hh, (96, 78, 66))
        cv.fill(bx + 3, base - hh - 8, bw - 12, 8, (96, 78, 66))
        for wy in range(base - hh + 8, base - 6, 12):
            cv.fill(bx + 5, wy, 4, 6, GOLD)
    cv.fill(x, base, w, 26, SAND)
    # missile arc and intercept burst
    cv.line(x + 12, y + 18, x + w // 2, y + h // 2 - 30, INK, 2)
    cv.line(x + w // 2, y + h // 2 - 30, x + w - 40, y + 30, INK, 2)
    bx, by = x + w // 2, y + h // 2 - 30
    for a in range(0, 360, 30):
        rad = math.radians(a)
        cv.line(bx, by, bx + int(18 * math.cos(rad)),
                by + int(18 * math.sin(rad)), FLAME, 2)
    cv.disc(bx, by, 6, GOLD)
    draw_text(cv, x + 6, y + h - 16, "RIYADH", 1, INK)


def draw_kyiv_block(cv, x, y, w, h):
    """An apartment block struck by a drone: smoke, broken windows,
    rescue lights below."""
    cv.fill(x, y, w, h, SKY)
    bx, by = x + 18, y + 22
    bw, bh = w - 36, h - 52
    cv.fill(bx, by, bw, bh, (150, 138, 122))
    cv.fill(bx, by, bw, 8, (110, 100, 88))
    for r in range(3):
        for c in range(4):
            wx = bx + 10 + c * ((bw - 20) // 4)
            wy = by + 16 + r * ((bh - 30) // 3)
            if r == 0 and c == 2:
                cv.fill(wx, wy, 18, 14, BLACK)  # shattered window
                cv.line(wx, wy, wx + 18, wy + 14, BLACK, 2)
                cv.line(wx + 18, wy, wx, wy + 14, BLACK, 2)
            else:
                cv.fill(wx, wy, 18, 14, GOLD)
    # smoke plume from the roof
    cv.disc(bx + bw - 30, by - 6, 12, SMOKE)
    cv.disc(bx + bw - 14, by - 18, 16, SMOKE)
    cv.disc(bx + bw + 4, by - 30, 12, SMOKE)
    cv.fill(x, y + h - 30, w, 30, (60, 60, 58))
    cv.disc(x + 30, y + h - 15, 5, FLAME)
    cv.disc(x + w - 30, y + h - 15, 5, RED)


def draw_seoul_podium(cv, x, y, w, h):
    """A government podium with a flag, papers scattered: a resignation."""
    cv.fill(x, y, w, h, (226, 228, 232))
    # flag pole and flag
    cv.fill(x + 24, y + 12, 4, 66, INK)
    cv.poly([(x + 28, y + 12), (x + 84, y + 22), (x + 28, y + 34)],
            WHITE)
    cv.disc(x + 52, y + 23, 6, RED)
    cv.disc(x + 52, y + 23, 3, NAVY)
    # podium
    cv.fill(x + w // 2 - 34, y + h - 62, 68, 62, NAVY)
    cv.fill(x + w // 2 - 40, y + h - 68, 80, 8, INK)
    # scattered papers
    cv.poly([(x + 20, y + h - 18), (x + 44, y + h - 24),
             (x + 40, y + h - 8), (x + 18, y + h - 4)], WHITE)
    cv.poly([(x + w - 46, y + h - 14), (x + w - 22, y + h - 22),
             (x + w - 26, y + h - 6), (x + w - 48, y + h - 2)], WHITE)
    draw_text(cv, x + 6, y + 6, "SEOUL", 1, GREY)


def draw_flags_talk(cv, x, y, w, h):
    """Two flags side by side above a handshake table: India and Nepal."""
    cv.fill(x, y, w, h, (232, 228, 214))
    # India flag
    fx, fy, fw, fh = x + 16, y + 16, 74, 46
    cv.fill(fx, fy, fw, fh // 3, SAFFRON)
    cv.fill(fx, fy + fh // 3, fw, fh // 3, WHITE)
    cv.fill(fx, fy + 2 * fh // 3, fw, fh // 3, GREEN)
    cv.circle(fx + fw // 2, fy + fh // 2, 8, NAVY, 1)
    # Nepal flag (crimson double pennant, simplified)
    nx, ny = x + w - 96, y + 14
    cv.poly([(nx, ny), (nx + 62, ny + 18), (nx, ny + 30)], RED)
    cv.poly([(nx, ny + 30), (nx + 52, ny + 46), (nx, ny + 56)], RED)
    cv.disc(nx + 14, ny + 16, 4, WHITE)
    # table and hands
    cv.fill(x + 14, y + h - 26, w - 28, 8, (120, 84, 50))
    cv.fill(x + 14, y + h - 18, 8, 18, (120, 84, 50))
    cv.fill(x + w - 22, y + h - 18, 8, 18, (120, 84, 50))
    cv.line(x + w // 2 - 26, y + h - 34, x + w // 2, y + h - 46, INK, 3)
    cv.line(x + w // 2 + 26, y + h - 34, x + w // 2, y + h - 46, INK, 3)
    draw_text(cv, x + 6, y + h - 12, "NEW DELHI", 1, GREY)

# -------------------------------------------------------------------- layout
MARGIN = 28


def draw_masthead(cv):
    draw_centered(cv, PAGE_W // 2, 24, "THE WORLD IN A DAY", 5, INK)
    draw_text(cv, MARGIN, 30, "VOL. I - No. 327", 1, GREY)
    draw_text(cv, PAGE_W - MARGIN - text_width("PRICE: ONE DAY", 1), 30,
              "PRICE: ONE DAY", 1, GREY)
    cv.fill(MARGIN, 74, PAGE_W - 2 * MARGIN, 3, INK)
    cv.fill(MARGIN, 80, PAGE_W - 2 * MARGIN, 1, INK)
    draw_centered(cv, PAGE_W // 2, 92, "MONDAY 23 NOVEMBER 2026", 3, RED)
    cv.fill(MARGIN, 122, PAGE_W - 2 * MARGIN, 2, INK)


def draw_lead(cv):
    y = 136
    draw_text(cv, MARGIN, y, "CLIMATE  -  ANTALYA, TURKIYE", 2, RED)
    draw_text(cv, MARGIN, y + 24, "COP31 COLLAPSES", 6, INK)
    draw_text(cv, MARGIN, y + 72, "WITHOUT A DEAL", 6, INK)
    sub = ("194 nations leave Antalya with no climate pact as "
           "fossil-fuel language sinks the talks.")
    draw_para(cv, MARGIN, y + 132, sub, 560, 2, INK)
    body = ("UN chief Antonio Guterres said he was deeply disappointed. "
            "The draft deal never once named fossil fuels, and the EU, "
            "Britain and island states refused to sign it. Talks ran two "
            "days over time and still ended with no pact.")
    draw_para(cv, MARGIN, y + 172, body, 560, 2, INK)
    draw_globe_crack(cv, 620, y + 128, PAGE_W - MARGIN - 620, 150)
    cv.fill(MARGIN, 462, PAGE_W - 2 * MARGIN, 2, INK)


def draw_middle(cv):
    y = 478
    # left: Hormuz
    draw_text(cv, MARGIN, y, "THE GULF", 2, RED)
    draw_text(cv, MARGIN, y + 22, "TANKERS UNDER FIRE", 3, INK)
    draw_tanker_sea(cv, MARGIN, y + 50, 464, 96)
    draw_para(cv, MARGIN, y + 156,
              "At least 25 tankers have been hit in and around the Strait "
              "of Hormuz in a week, choking Gulf oil flows.",
              464, 2, INK)
    # divider
    cv.fill(512, y, 1, 212, RULE)
    # right: Riyadh
    draw_text(cv, 532, y, "SAUDI ARABIA", 2, RED)
    draw_text(cv, 532, y + 22, "RIYADH HIT FOR THIRD DAY", 3, INK)
    draw_riyadh_skyline(cv, 532, y + 50, 464, 96)
    draw_para(cv, 532, y + 156,
              "Houthi drones and missiles struck Riyadh for a third "
              "straight day. Saudi defences said the attack was "
              "intercepted.",
              464, 2, INK)
    cv.fill(MARGIN, 706, PAGE_W - 2 * MARGIN, 2, INK)


def draw_brief(cv, x, w, kicker, color, headline, body):
    y = 722
    cv.fill(x, y, w, 22, color)
    draw_text(cv, x + 8, y + 4, kicker, 2, WHITE)
    draw_para(cv, x, y + 34, headline, w, 2, INK, leading=18)
    n_head_lines = len(wrap_lines(headline, w, 2))
    by = y + 34 + n_head_lines * 18 + 6
    draw_para(cv, x, by, body, w, 2, INK, leading=18)


def draw_bottom(cv):
    draw_brief(cv, MARGIN, 312, "UKRAINE", NAVY,
               "DRONE HITS KYIV FLATS",
               "A Russian drone hit a block of flats outside Kyiv. "
               "At least 14 people are missing, President Zelenskyy said.")
    draw_brief(cv, 358, 312, "SOUTH KOREA", RED,
               "MINISTER QUITS OVER AI CHEATING",
               "South Korea's education minister resigned over an AI "
               "exam-cheating scandal.")
    draw_brief(cv, 688, 312, "INDIA - NEPAL", GREEN,
               "NEPAL PM MEETS MODI",
               "Nepal PM Balendra Shah held talks with PM Modi in New "
               "Delhi on trade and ties.")


def draw_ticker(cv):
    y = 926
    cv.fill(MARGIN, y, PAGE_W - 2 * MARGIN, 40, NAVY)
    draw_text(cv, MARGIN + 10, y + 5,
              "ALSO TODAY: BepiColombo in orbit around Mercury after "
              "eight years.", 2, WHITE)
    draw_text(cv, MARGIN + 10, y + 23,
              "Russian cargo ship ablaze off Finland. Lisbon marches "
              "over living costs.", 2, WHITE)
    draw_centered(cv, PAGE_W // 2, 978,
                  "Drawn entirely in code. Sources: UN News, AP, Reuters, "
                  "ESA - 23 November 2026.", 1, GREY)


def draw_page():
    cv = Canvas(PAGE_W, PAGE_H, PAPER)
    # paper edge
    cv.outline(0, 0, PAGE_W, PAGE_H, RULE, 1)
    draw_masthead(cv)
    draw_lead(cv)
    draw_middle(cv)
    draw_bottom(cv)
    draw_ticker(cv)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, draw_page())
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
