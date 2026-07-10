"""Generate the final-deliverable source art: a clean kawaii fox (kitsune) mascot.

Anchored to the "Aprendiendo Wilcom" playlist's animal/character practice, but
drawn ORIGINAL and flat so the Phase-A pipeline can digitise it *near-perfectly*
(a detailed frame-crop only simplifies — proven by the Rei experiment). Design
choices follow anime/best-practices.md:

  - flat, separable colours on transparency      -> clean mask + clean trace
  - few continuous regions                       -> few machine trims
  - bold dark outline >= ~2 mm                    -> real satin columns (Column A/B)
  - big orange/white areas                        -> tatami fills, foreground-last
  - every linework stroke kept >= ~1.6 mm         -> survives the 1.2 mm min width

Run:  python anime/assets/make_kitsune.py   # -> anime/assets/kitsune.png
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

ORANGE = (230, 138, 60, 255)    # head + ears        -> tatami fill
CREAM = (247, 241, 227, 255)    # muzzle + ear inner -> tatami fill
DARK = (42, 42, 48, 255)        # outline/eyes/nose  -> satin columns / fills
PINK = (232, 154, 168, 255)     # cheeks             -> small fill
CLEAR = (0, 0, 0, 0)

SS = 4
W, H = 900, 950


def _mirror(pts, cx):
    return pts + [(2 * cx - x, y) for x, y in reversed(pts)]


def draw(scale: int):
    img = Image.new("RGBA", (W * scale, H * scale), CLEAR)
    d = ImageDraw.Draw(img)
    cx = 450

    def S(seq):
        return [(int(x * scale), int(y * scale)) for x, y in seq]

    def line(p0, p1, w, fill=DARK):
        d.line(S([p0, p1]), fill=fill, width=int(w * scale), joint="curve")

    def poly_outline(pts, w):
        d.line(S(pts + [pts[0]]), fill=DARK, width=int(w * scale), joint="curve")

    # --- head (right half, top -> chin), mirrored ---------------------------
    head_r = [
        (450, 250), (560, 262), (650, 300), (701, 380), (710, 470),
        (680, 560), (618, 652), (528, 732), (450, 764),
    ]
    head = _mirror(head_r, cx)

    # --- ears (outer orange + inner cream) ---------------------------------
    l_ear = [(250, 305), (212, 96), (380, 300)]
    r_ear = [(650, 305), (688, 96), (520, 300)]
    l_ear_in = [(285, 285), (243, 150), (360, 285)]
    r_ear_in = [(615, 285), (657, 150), (540, 285)]

    # fills (orange body first, outlines added on top later)
    d.polygon(S(l_ear), fill=ORANGE)
    d.polygon(S(r_ear), fill=ORANGE)
    d.polygon(S(head), fill=ORANGE)
    d.polygon(S(l_ear_in), fill=CREAM)
    d.polygon(S(r_ear_in), fill=CREAM)

    # --- muzzle (cream), lower face down to the chin ------------------------
    muzzle_r = [
        (450, 452), (520, 470), (556, 545), (540, 632), (498, 706), (450, 748),
    ]
    muzzle = _mirror(muzzle_r, cx)
    d.polygon(S(muzzle), fill=CREAM)

    # --- cheeks (pink), on the orange beside the muzzle ---------------------
    for exx in (300, 600):
        d.ellipse(S([(exx - 44, 556), (exx + 44, 612)]), fill=PINK)

    # --- eyes: dark almond + cream catch-light ------------------------------
    for exx in (356, 544):
        d.ellipse(S([(exx - 46, 392), (exx + 46, 470)]), fill=DARK)
        d.ellipse(S([(exx + 6, 408), (exx + 30, 432)]), fill=CREAM)

    # --- nose (dark, rounded triangle at top of muzzle) ---------------------
    d.polygon(S([(450, 560), (492, 520), (408, 520)]), fill=DARK)
    # --- mouth (two soft strokes under the nose) ----------------------------
    line((450, 560), (450, 600), 11)
    line((450, 600), (404, 628), 11)
    line((450, 600), (496, 628), 11)

    # --- outlines last (the satin-column lesson): ~2.0-2.6 mm ---------------
    poly_outline(head, 26)
    poly_outline(l_ear, 22)
    poly_outline(r_ear, 22)
    poly_outline(l_ear_in, 14)
    poly_outline(r_ear_in, 14)
    poly_outline(muzzle, 18)
    return img


def main():
    big = draw(SS)
    out = big.resize((W, H), Image.LANCZOS)
    dst = Path(__file__).resolve().parent / "kitsune.png"
    out.save(dst)
    print(f"wrote {dst} ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    main()
