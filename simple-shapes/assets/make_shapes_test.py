#!/usr/bin/env python3
"""Generate an independent simple-shapes test 'photo' — a clean flat sticker-sheet of
bold vector icons in a small PURE-PRIMARY palette (red heart, yellow star, blue
arrow) on white. This is NOT derived from a reference VP3; it is a fresh photo that
simulates what the simple-shapes category produces, so the recipe can be proven on
novel input and the output compared back to this source."""
import math
from PIL import Image, ImageDraw

PXMM = 8
W_MM, H_MM = 150, 70
W, H = W_MM * PXMM, H_MM * PXMM
img = Image.new("RGB", (W, H), (255, 255, 255))
dr = ImageDraw.Draw(img)

RED = (227, 30, 36)     # heart  (pure-ish primary red)
YELLOW = (255, 221, 0)  # star
BLUE = (0, 122, 204)    # arrow


def star(cx, cy, r_out, r_in, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        ang = rot + i * math.pi / n
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def heart(cx, cy, s):
    """Parametric heart, scaled to ~s mm tall, returned as a polygon."""
    pts = []
    for t in range(0, 360, 4):
        a = math.radians(t)
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((cx + x * s / 32, cy - y * s / 32))
    return pts


def arrow(cx, cy, L, w):
    """Upward block arrow centred at (cx,cy), height L, shaft width w."""
    head = L * 0.45
    hw = w * 2.0
    return [
        (cx, cy - L / 2),                 # tip
        (cx + hw, cy - L / 2 + head),
        (cx + w, cy - L / 2 + head),
        (cx + w, cy + L / 2),
        (cx - w, cy + L / 2),
        (cx - w, cy - L / 2 + head),
        (cx - hw, cy - L / 2 + head),
    ]


# heart (left), star (centre), arrow (right) — each ~50 mm tall, bold solids
dr.polygon(heart(30 * PXMM, 35 * PXMM, 46 * PXMM), fill=RED)
dr.polygon(star(75 * PXMM, 35 * PXMM, 26 * PXMM, 11 * PXMM), fill=YELLOW)
dr.polygon(arrow(120 * PXMM, 35 * PXMM, 50 * PXMM, 7 * PXMM), fill=BLUE)

img.save("simple-shapes/assets/shapes_test.png")
print(f"wrote simple-shapes/assets/shapes_test.png  {W}x{H}px  ({W_MM}x{H_MM}mm)")
