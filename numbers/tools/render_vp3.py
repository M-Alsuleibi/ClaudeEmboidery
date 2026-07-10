#!/usr/bin/env python3
"""Render each Arabic VP3 to a PNG (stitch lines) + segment by TRIM into pieces,
measuring each piece's geometry (satin vs run, width, span)."""
import sys, math, os
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw

UNIT_MM = 0.1
SCALE = 4  # px per mm for render

def pieces_by_trim(stitches):
    """Split stitch list into runs separated by TRIM/COLOR_CHANGE."""
    pieces = []
    cur = []
    for s in stitches:
        cmd = s[2] & 0xFF
        if cmd in (pe.TRIM & 0xFF, pe.COLOR_CHANGE & 0xFF, pe.COLOR_BREAK & 0xFF, pe.END & 0xFF):
            if len(cur) > 1:
                pieces.append(cur)
            cur = []
            continue
        cur.append((s[0], s[1]))
    if len(cur) > 1:
        pieces.append(cur)
    return pieces

def piece_geom(pts):
    p = np.array(pts, float)
    d = np.diff(p, axis=0)
    seglen = np.hypot(d[:,0], d[:,1]) * UNIT_MM
    a = np.arctan2(d[:,1], d[:,0])
    da = (np.diff(a) + np.pi) % (2*np.pi) - np.pi
    turn = np.abs(np.degrees(da))
    rev = np.mean(turn > 120)*100 if len(turn) else 0
    bbox = (p[:,0].max()-p[:,0].min())*UNIT_MM, (p[:,1].max()-p[:,1].min())*UNIT_MM
    span = math.hypot(*bbox)
    valid = seglen[seglen>0.05]
    return dict(n=len(p), rev=rev, span=span,
                med=float(np.median(valid)) if len(valid) else 0,
                bbox=bbox)

def render(path, out_png):
    pat = pe.read(path)
    st = pat.stitches
    xs = [s[0] for s in st]; ys = [s[1] for s in st]
    minx, miny = min(xs), min(ys)
    w_mm = (max(xs)-minx)*UNIT_MM; h_mm = (max(ys)-miny)*UNIT_MM
    W = int(w_mm*SCALE)+20; H = int(h_mm*SCALE)+20
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)
    def xf(x,y):
        return (10 + (x-minx)*UNIT_MM*SCALE, 10 + (y-miny)*UNIT_MM*SCALE)
    pieces = pieces_by_trim(st)
    for blk in pieces:
        prev = None
        for (x,y) in blk:
            pt = xf(x,y)
            if prev is not None:
                dr.line([prev, pt], fill=(0,0,0), width=1)
            prev = pt
    img.save(out_png)
    # geometry summary of pieces
    geoms = [piece_geom(b) for b in pieces if len(b)>2]
    spans = sorted([g['span'] for g in geoms])
    revs = [g['rev'] for g in geoms]
    big = [g for g in geoms if g['span']>15]
    small = [g for g in geoms if g['span']<=15]
    print(f"\n{path}  ->  {out_png}")
    print(f"  size {w_mm:.1f}x{h_mm:.1f}mm  pieces(by trim)={len(pieces)}")
    print(f"  piece spans mm: min={spans[0]:.1f} med={spans[len(spans)//2]:.1f} max={spans[-1]:.1f}")
    print(f"  big pieces (span>15mm, main strokes/decor): {len(big)}  "
          f"avg rev={np.mean([g['rev'] for g in big]):.0f}%  avg satinW(med seg)={np.mean([g['med'] for g in big]):.2f}mm")
    print(f"  small pieces (span<=15mm, dots/diacritics): {len(small)}  "
          f"avg rev={np.mean([g['rev'] for g in small]) if small else 0:.0f}%")

os.makedirs(sys.argv[1], exist_ok=True)
for p in sys.argv[2:]:
    name = os.path.splitext(os.path.basename(p))[0]
    render(p, os.path.join(sys.argv[1], name+".png"))
