#!/usr/bin/env python3
"""Render a VP3 reference into a clean SOLID black-on-white raster that looks like
a photo/scan of the calligraphy (satin columns become solid strokes), so we can
feed it through the photo->VP3 pipeline and calibrate against the ground truth.
Travel jumps (segments > 12.7mm) are dropped so connector lines don't draw."""
import sys
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFilter

UNIT_MM = 0.1
PXMM = 8           # px per mm
STROKE_PX = 4      # line width -> fills the satin column solid
MARGIN_MM = 12

def main(vp3, out_png):
    pat = pe.read(vp3)
    st = pat.stitches
    xs = [s[0] for s in st]; ys = [s[1] for s in st]
    minx, miny = min(xs), min(ys)
    w_mm = (max(xs)-minx)*UNIT_MM; h_mm = (max(ys)-miny)*UNIT_MM
    W = int((w_mm+2*MARGIN_MM)*PXMM); H = int((h_mm+2*MARGIN_MM)*PXMM)
    img = Image.new("L", (W, H), 255)
    dr = ImageDraw.Draw(img)
    def xf(x,y):
        return (MARGIN_MM*PXMM + (x-minx)*UNIT_MM*PXMM,
                MARGIN_MM*PXMM + (y-miny)*UNIT_MM*PXMM)
    prev = None
    for s in st:
        cmd = s[2] & 0xFF
        pt = xf(s[0], s[1])
        if cmd in (pe.TRIM & 0xFF, pe.COLOR_CHANGE & 0xFF, pe.END & 0xFF):
            prev = None
            continue
        if prev is not None:
            dx = (s[0]-prevxy[0])*UNIT_MM; dy=(s[1]-prevxy[1])*UNIT_MM
            if (dx*dx+dy*dy) ** 0.5 <= 12.7:  # real stitch, not a travel jump
                dr.line([prev, pt], fill=0, width=STROKE_PX)
        prev = pt; prevxy = (s[0], s[1])
    # close tiny gaps so each stroke is a solid blob
    img = img.filter(ImageFilter.MinFilter(3))   # dilate black
    img = img.filter(ImageFilter.MaxFilter(3))    # erode back (morphological close)
    # CRISP: hard threshold to pure black/white (no anti-alias halo -> no phantom cone)
    img = img.point(lambda v: 0 if v < 128 else 255, mode="L")
    img.convert("RGB").save(out_png)
    print(f"{vp3} -> {out_png}   {W}x{H}px  ({w_mm:.0f}x{h_mm:.0f}mm @ {PXMM}px/mm)")

main(sys.argv[1], sys.argv[2])
