#!/usr/bin/env python3
"""Compare two VP3 (or a VP3 vs a source raster) as filled ink masks, normalised
to the same physical scale and aligned by bounding box. Reports IoU / coverage
drift and writes an overlay PNG: reference=RED, candidate=BLUE, overlap=PURPLE.
This is the 'compare near-final work to the original, measure drift' step."""
import sys
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFilter, ImageChops

UNIT_MM = 0.1
PXMM = 4
STROKE_PX = 3

def vp3_mask(path, target_wh_mm=None, canvas=None):
    pat = pe.read(path)
    st = pat.stitches
    xs=[s[0] for s in st]; ys=[s[1] for s in st]
    minx,miny=min(xs),min(ys)
    w_mm=(max(xs)-minx)*UNIT_MM; h_mm=(max(ys)-miny)*UNIT_MM
    if canvas is None:
        W=int(w_mm*PXMM)+20; H=int(h_mm*PXMM)+20
    else:
        W,H=canvas
    img=Image.new("L",(W,H),0); dr=ImageDraw.Draw(img)
    # fit design into canvas preserving aspect, centered
    sx=(W-20)/ (w_mm) ; sy=(H-20)/(h_mm); s=min(sx,sy)
    offx=(W-w_mm*s)/2; offy=(H-h_mm*s)/2
    def xf(x,y): return (offx+(x-minx)*UNIT_MM*s, offy+(y-miny)*UNIT_MM*s)
    prev=None;pxy=None
    for stp in st:
        cmd=stp[2]&0xFF; pt=xf(stp[0],stp[1])
        if cmd in (pe.TRIM&0xFF,pe.COLOR_CHANGE&0xFF,pe.END&0xFF):
            prev=None;continue
        if prev is not None:
            d=(((stp[0]-pxy[0])*UNIT_MM)**2+((stp[1]-pxy[1])*UNIT_MM)**2)**.5
            if d<=12.7: dr.line([prev,pt],fill=255,width=STROKE_PX)
        prev=pt;pxy=(stp[0],stp[1])
    img=img.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    return img,(w_mm,h_mm)

def main(ref, cand, out):
    rimg,rwh=vp3_mask(ref)
    cimg,cwh=vp3_mask(cand, canvas=rimg.size)
    R=np.array(rimg)>128; C=np.array(cimg)>128
    inter=(R&C).sum(); union=(R|C).sum()
    iou=inter/union if union else 0
    cov_ref = inter/R.sum() if R.sum() else 0   # how much of ref is covered
    cov_cand= inter/C.sum() if C.sum() else 0   # how much of cand lands on ref
    over=Image.merge("RGB",[Image.fromarray((R*255).astype('uint8')),
                            Image.new("L",rimg.size,0),
                            Image.fromarray((C*255).astype('uint8'))])
    over.save(out)
    print(f"REF  {ref}  {rwh[0]:.0f}x{rwh[1]:.0f}mm")
    print(f"CAND {cand}  {cwh[0]:.0f}x{cwh[1]:.0f}mm")
    print(f"  IoU={iou*100:.1f}%   ref-covered={cov_ref*100:.1f}%   cand-on-ref={cov_cand*100:.1f}%")
    print(f"  overlay -> {out}  (RED=ref BLUE=cand PURPLE=match)")

main(sys.argv[1], sys.argv[2], sys.argv[3])
