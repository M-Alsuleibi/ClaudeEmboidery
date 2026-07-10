#!/usr/bin/env python3
"""Measure an output VP3 against the SOURCE photo it was traced from (no ground-truth
VP3 needed). Both are reduced to a non-white ink mask, fit to a common canvas by
bounding box, and compared: IoU + how much of the source ink the stitches cover.
Writes a RED=source / BLUE=output / PURPLE=match overlay. This is the
'compare near-final work to the original photo, measure drift, iterate' gate."""
import sys
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFilter

UNIT_MM = 0.1
PXMM = 4
STROKE_PX = 3


def photo_mask(path, canvas):
    im = Image.open(path).convert("RGB")
    a = np.array(im)
    ink = ~((a[:, :, 0] > 235) & (a[:, :, 1] > 235) & (a[:, :, 2] > 235))
    ys, xs = np.where(ink)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    crop = Image.fromarray((ink[y0:y1 + 1, x0:x1 + 1] * 255).astype("uint8"))
    return fit(crop, canvas)


def vp3_mask(path, canvas):
    pat = pe.read(path)
    st = pat.stitches
    xs = [s[0] for s in st]; ys = [s[1] for s in st]
    minx, miny = min(xs), min(ys)
    w_mm = (max(xs) - minx) * UNIT_MM; h_mm = (max(ys) - miny) * UNIT_MM
    W = int(w_mm * PXMM) + 8; H = int(h_mm * PXMM) + 8
    img = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(img)
    prev = None; pxy = None
    for s in st:
        cmd = s[2] & 0xFF
        pt = (4 + (s[0] - minx) * UNIT_MM * PXMM, 4 + (s[1] - miny) * UNIT_MM * PXMM)
        if cmd in (pe.TRIM & 0xFF, pe.COLOR_CHANGE & 0xFF, pe.END & 0xFF):
            prev = None; continue
        if prev is not None:
            d = (((s[0] - pxy[0]) * UNIT_MM) ** 2 + ((s[1] - pxy[1]) * UNIT_MM) ** 2) ** .5
            if d <= 12.7:
                dr.line([prev, pt], fill=255, width=STROKE_PX)
        prev = pt; pxy = (s[0], s[1])
    img = img.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    return fit(img, canvas)


def fit(mask, canvas):
    W, H = canvas
    bbox = mask.getbbox()
    mask = mask.crop(bbox)
    mw, mh = mask.size
    s = min((W - 16) / mw, (H - 16) / mh)
    mask = mask.resize((max(1, int(mw * s)), max(1, int(mh * s))))
    out = Image.new("L", (W, H), 0)
    out.paste(mask, ((W - mask.size[0]) // 2, (H - mask.size[1]) // 2))
    return out


def main(photo, vp3, out):
    canvas = (700, 700)
    P = np.array(photo_mask(photo, canvas)) > 128
    V = np.array(vp3_mask(vp3, canvas)) > 128
    inter = (P & V).sum(); union = (P | V).sum()
    iou = inter / union if union else 0
    cov = inter / P.sum() if P.sum() else 0
    over = Image.merge("RGB", [Image.fromarray((P * 255).astype("uint8")),
                               Image.new("L", canvas, 0),
                               Image.fromarray((V * 255).astype("uint8"))])
    over.save(out)
    print(f"SOURCE {photo}")
    print(f"OUTPUT {vp3}")
    print(f"  IoU={iou*100:.1f}%   source-covered={cov*100:.1f}%")
    print(f"  overlay -> {out}  (RED=source BLUE=output PURPLE=match)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
