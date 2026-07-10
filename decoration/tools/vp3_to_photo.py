#!/usr/bin/env python3
"""Render a VP3 reference into a clean, COLOUR-ACCURATE flat raster that looks like
a sticker / vector "photo" of the design — each colour block is drawn solid in its
own thread RGB on a white ground. Used to calibrate the simple-shapes recipe: turn a
ground-truth multi-colour shape design into a photo, run it back through the
photo->VP3 pipeline, and compare the output against the ground truth.

Unlike the Arabic monochrome renderer this is per-colour-block so multi-colour shape
sets (4-colour stars, a 4-ring frame) survive the round trip. Travel jumps
(segments > 12.7 mm) are dropped so connector lines don't draw."""
import sys
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFilter

UNIT_MM = 0.1
PXMM = 8           # px per mm
STROKE_PX = 7      # line width -> fills the satin/fill column solid (shapes are bold)
MARGIN_MM = 12


def blocks_by_color(stitches, threads):
    """Yield (rgb, [stitch,...]) per colour block, split on COLOR_CHANGE."""
    out = []
    cur = []
    ti = 0
    for s in stitches:
        cmd = s[2] & 0xFF
        if cmd in (pe.COLOR_CHANGE & 0xFF, pe.COLOR_BREAK & 0xFF):
            if cur:
                out.append((ti, cur)); cur = []
            ti += 1
            continue
        cur.append(s)
    if cur:
        out.append((ti, cur))
    rgbs = []
    for idx, blk in out:
        t = threads[min(idx, len(threads) - 1)]
        rgbs.append(((t.get_red(), t.get_green(), t.get_blue()), blk))
    return rgbs


def main(vp3, out_png):
    pat = pe.read(vp3)
    st = pat.stitches
    xs = [s[0] for s in st]; ys = [s[1] for s in st]
    minx, miny = min(xs), min(ys)
    w_mm = (max(xs) - minx) * UNIT_MM; h_mm = (max(ys) - miny) * UNIT_MM
    W = int((w_mm + 2 * MARGIN_MM) * PXMM); H = int((h_mm + 2 * MARGIN_MM) * PXMM)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(img)

    def xf(x, y):
        return (MARGIN_MM * PXMM + (x - minx) * UNIT_MM * PXMM,
                MARGIN_MM * PXMM + (y - miny) * UNIT_MM * PXMM)

    for rgb, blk in blocks_by_color(st, pat.threadlist):
        prev = None; prevxy = None
        for s in blk:
            cmd = s[2] & 0xFF
            pt = xf(s[0], s[1])
            if cmd in (pe.TRIM & 0xFF, pe.END & 0xFF):
                prev = None; continue
            if prev is not None:
                dx = (s[0] - prevxy[0]) * UNIT_MM; dy = (s[1] - prevxy[1]) * UNIT_MM
                if (dx * dx + dy * dy) ** 0.5 <= 12.7:   # real stitch, not a travel
                    dr.line([prev, pt], fill=rgb, width=STROKE_PX)
            prev = pt; prevxy = (s[0], s[1])

    # morphological close so each shape reads as a solid blob (no satin gaps)
    img = img.filter(ImageFilter.MinFilter(3))   # grow dark/coloured
    img = img.filter(ImageFilter.MaxFilter(3))    # shrink back
    img.save(out_png)
    print(f"{vp3} -> {out_png}   {W}x{H}px  ({w_mm:.0f}x{h_mm:.0f}mm @ {PXMM}px/mm)  "
          f"colors={len(pat.threadlist)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
