#!/usr/bin/env python3
"""Author a clean synthetic *decoration* test motif: a radial rosette / mandala —
the most iconic decoration archetype (radial symmetry, thin ornamental linework that
routes wholesale to satin, like the 5x5/7x7/4x4 reference mandalas). Drawn as crisp
thin strokes on white so the width classifier satins it; single accent colour."""
import math
from PIL import Image, ImageDraw

S = 1500                      # canvas px (square)
C = S / 2
INK = (8, 84, 54)            # deep tonal green — typical tone-on-tone decoration colour
STROKE = 22                  # px (~1.9 mm at 130 mm / 1500 px = 11.5 px/mm) — bold enough
                             # to survive quantization (thin strokes wash pale on white)

base = Image.new("RGB", (S, S), "white")

def petal_layer(base_r, length, width, sw, fill=None):
    """A vertical pointed-leaf petal on its own S x S RGBA layer, pointing UP, with its
    base at radius `base_r` above centre and tip a further `length` out — so a gap of
    `base_r` is left open at the middle (no solid overlapping hub). Rotation is about the
    canvas centre, turning it into one ray of an open radial motif."""
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx = C
    base_y = C - base_r
    tip_y = base_y - length
    pts_r, pts_l = [], []
    N = 40
    for i in range(N + 1):
        t = i / N
        y = base_y + (tip_y - base_y) * t
        x = (width / 2) * math.sin(math.pi * t)   # lens: 0 at both ends, max mid
        pts_r.append((cx + x, y))
        pts_l.append((cx - x, y))
    d.polygon(pts_r + pts_l[::-1], outline=INK, width=sw, fill=fill)
    d.line([(cx, base_y - length * 0.08), (cx, tip_y + length * 0.12)],
           fill=INK, width=max(2, sw - 10))       # centre vein
    return lay

def stamp_radial(n, half_step=False, **kw):
    for k in range(n):
        lay = petal_layer(**kw)
        ang = -(k + (0.5 if half_step else 0.0)) * 360.0 / n
        rot = lay.rotate(ang, center=(C, C), resample=Image.BICUBIC)
        base.paste(rot, (0, 0), rot)

# Petals are drawn SOLID (fill=INK), not as hollow outlines. A hollow leaf traps its
# interior white as an enclosed counter; with --colors 1 the quantiser then averages
# ink+trapped-white into a pale grey (washout) and the colour cannot be recovered by any
# flag (the k=1 centroid is computed pre-counter-drop). Solid leaves keep the kept
# foreground all-ink, so the single colour quantises true — and the raster tracer renders
# decoration ornament as clean FILLS regardless (the honest boundary, §7). (§5 lesson.)
# --- outer ring of 12 long slender leaves (open: base sits out at r=235) -----
stamp_radial(12, base_r=235, length=345, width=120, sw=STROKE, fill=INK)
# --- middle ring of 12 shorter leaves, offset half a step -------------------
stamp_radial(12, half_step=True, base_r=150, length=130, width=95, sw=STROKE, fill=INK)

dr = ImageDraw.Draw(base)
def ring(r, sw):
    dr.ellipse([C - r, C - r, C + r, C + r], outline=INK, width=sw)
def dot_ring(r, n, rad):
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = C + r * math.cos(a), C + r * math.sin(a)
        dr.ellipse([x - rad, y - rad, x + rad, y + rad], fill=INK)

# Radiating mandala — NO fully-enclosing outer ring: an outer ring would trap the white
# petal-gaps as enclosed "counters", and with --colors 1 the quantiser then averages
# ink+trapped-white into a pale grey (washout). Leaving the gaps open to the border lets
# the background drop them, so the single ink quantises true. (Decoration lesson §5.)
dot_ring(625, 28, 11)        # outer bead ring (disjoint dots -> many trims, expected)
# central flower (small solid rosette, isolated in the open middle)
dot_ring(95, 8, 22)
dr.ellipse([C - 46, C - 46, C + 46, C + 46], fill=INK)

# Emit a crisp 2-colour image AT THE PIPELINE'S WORK RESOLUTION (1200 px). Two halo
# sources wash thin ink pale (knowledge §5): bicubic rotation, and the pipeline's own
# downscale to 1200 px. We kill both — threshold every non-near-white pixel to pure INK
# (removes rotation haloes), then resize to 1200 px with NEAREST (no new halo) so the
# pipeline never has to downscale. Result: the single ink quantises to its true colour.
import numpy as np
a = np.asarray(base).astype(np.int16)
ink_mask = a.sum(axis=2) < (250 * 3 - 30)        # anything darker than ~near-white
out = np.full_like(a, 255)
out[ink_mask] = INK
img = Image.fromarray(out.astype(np.uint8)).resize((1200, 1200), Image.NEAREST)
img.save("decoration/assets/decoration_test.png")
print("wrote decoration/assets/decoration_test.png", img.size,
      "ink px frac %.3f" % (ink_mask.mean()))
