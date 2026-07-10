"""Generate the source logo digitised in the tutorial: Studio Ghibli's Totoro.

The Oct #3 Wilcom class ("REPASO COLUMNA A-B / REALIZAR PUNTAS / DISEÑO EMB.")
traces Totoro silhouettes (tab: "PRACTICA GHIBLI PEDRO") as its practice design.
This script redraws a clean, embroidery-friendly Totoro so the Phase A pipeline
has a crisp, flat-colour source to digitise — the same character the video uses.

Why these choices map to the lesson:
  - Flat, separable colours on a transparent background  -> clean foreground mask
    + clean VTracer paths (no photographic dither to fight).
  - Few colours, each a continuous region                -> few machine trims.
  - A thin dark outline + whiskers (small median width)   -> the pipeline turns
    these into *satin columns* == the video's Column A / Column B linework.
  - Big gray body + cream belly (large median width)      -> tatami fills.

Run:  python anime/assets/make_totoro.py            # -> anime/assets/totoro.png
Supersampled 4x then box-downsampled for smooth, near-flat edges.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# --- palette (4 production colours) ----------------------------------------- #
GRAY = (138, 141, 146, 255)    # body + ears        -> tatami fill
CREAM = (236, 232, 219, 255)   # belly              -> tatami fill
DARK = (43, 47, 53, 255)       # outline/markings   -> satin columns (Column A/B)
WHITE = (251, 251, 251, 255)   # eye whites         -> small fill
CLEAR = (0, 0, 0, 0)

SS = 4                          # supersample factor
W, H = 900, 1000               # final px (design canvas, transparent bg)


def _mirror(pts_right_half, cx):
    """Build a closed symmetric polygon from the right-half outline (top->bottom)."""
    left = [(2 * cx - x, y) for x, y in reversed(pts_right_half)]
    return pts_right_half + left


def draw(scale: int):
    w, h = W * scale, H * scale
    img = Image.new("RGBA", (w, h), CLEAR)
    d = ImageDraw.Draw(img)
    cx = (W // 2) * scale

    def S(seq):
        return [(int(x * scale), int(y * scale)) for x, y in seq]

    def line(p0, p1, width_px, fill=DARK):
        d.line(S([p0, p1]), fill=fill, width=int(width_px * scale), joint="curve")

    # --- body silhouette (right half, top -> bottom), mirrored --------------- #
    body_r = [
        (450, 150), (520, 158), (590, 192), (642, 250), (676, 330),
        (696, 430), (700, 540), (690, 650), (660, 752), (606, 838),
        (530, 894), (450, 910),
    ]
    body = _mirror(body_r, 450)

    # --- ears (pointed), drawn as part of the gray body --------------------- #
    left_ear = [(372, 196), (336, 60), (430, 168)]
    right_ear = [(528, 168), (564, 60), (468, 196)]

    # gray body fill (outline added on top later so edges read crisp)
    d.polygon(S(body), fill=GRAY)
    d.polygon(S(left_ear), fill=GRAY)
    d.polygon(S(right_ear), fill=GRAY)

    # --- belly (cream), a rounded shield on the lower front ----------------- #
    belly_r = [
        (450, 360), (516, 372), (566, 430), (588, 520), (586, 626),
        (560, 730), (510, 806), (450, 840),
    ]
    belly = _mirror(belly_r, 450)
    d.polygon(S(belly), fill=CREAM)

    # --- chevron markings on the belly (3 rows of bold V's) ----------------- #
    # >= 1.6 mm wide so they survive the 1.2 mm consolidation and satin cleanly.
    chev_w = 18
    for (cyr, half, drop) in [(440, 92, 44), (528, 100, 50), (616, 92, 46)]:
        for s in (-1, 1):
            line((450, cyr + drop), (450 + s * half, cyr - 8), chev_w)

    # --- eyes: white disc + dark pupil, two close-set near top of head ------ #
    # Large enough (white ring ~28 px) to survive consolidation -> stays 4 colours.
    for ex in (398, 502):
        d.ellipse(S([(ex - 52, 224), (ex + 52, 328)]), fill=WHITE, outline=DARK,
                  width=int(9 * scale))
        d.ellipse(S([(ex - 24, 252), (ex + 24, 300)]), fill=DARK)

    # --- nose (dark diamond) between/under the eyes ------------------------- #
    d.polygon(S([(450, 300), (482, 330), (450, 366), (418, 330)]), fill=DARK)

    # --- whiskers (3 each side, ~1.6 mm -> satin/running linework) ----------- #
    for s in (-1, 1):
        base_x = 450 + s * 52
        for (y0, y1, dx) in [(300, 282, 150), (322, 322, 164), (344, 360, 150)]:
            line((base_x, y0), (base_x + s * dx, y1), 16)

    # --- outline last (sits on top): the Column A/B satin lesson ------------ #
    # ~2.0-2.4 mm dark borders -> clean satin columns, the heart of the video.
    d.line(S(body + [body[0]]), fill=DARK, width=int(24 * scale), joint="curve")
    d.line(S(left_ear + [left_ear[0]]), fill=DARK, width=int(20 * scale), joint="curve")
    d.line(S(right_ear + [right_ear[0]]), fill=DARK, width=int(20 * scale), joint="curve")
    d.line(S(belly + [belly[0]]), fill=DARK, width=int(20 * scale), joint="curve")
    return img


def main():
    big = draw(SS)
    out = big.resize((W, H), Image.LANCZOS)
    dst = Path(__file__).resolve().parent / "totoro.png"
    out.save(dst)
    print(f"wrote {dst} ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    main()
