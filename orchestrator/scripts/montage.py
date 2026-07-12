#!/usr/bin/env python3
"""Colour-accurate thumbnail montage of decoration VP3s — render each colour block
in its thread colour so we can see what the decoration actually depicts."""
import sys, os, math
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFont

UNIT_MM = 0.1

def render_one(path, cell_px=320, pad=8):
    pat = pe.read(path)
    st = pat.stitches
    threads = pat.threadlist
    xs=[s[0] for s in st]; ys=[s[1] for s in st]
    minx,miny=min(xs),min(ys); maxx,maxy=max(xs),max(ys)
    w=(maxx-minx)*UNIT_MM; h=(maxy-miny)*UNIT_MM
    scale=(cell_px-2*pad)/max(w,h,1)
    W=int(w*scale)+2*pad; H=int(h*scale)+2*pad
    img=Image.new("RGB",(max(W,1),max(H,1)),"white")
    dr=ImageDraw.Draw(img)
    def xf(x,y): return (pad+(x-minx)*UNIT_MM*scale, pad+(y-miny)*UNIT_MM*scale)
    ci=0
    col=threads[0] if threads else None
    def rgb(t): return (t.get_red(),t.get_green(),t.get_blue()) if t else (0,0,0)
    cur=rgb(col)
    prev=None
    for s in st:
        cmd=s[2]&0xFF
        if cmd in (pe.COLOR_CHANGE&0xFF, pe.COLOR_BREAK&0xFF):
            ci+=1; cur=rgb(threads[ci]) if ci<len(threads) else cur; prev=None; continue
        if cmd in (pe.TRIM&0xFF, pe.END&0xFF):
            prev=None; continue
        pt=xf(s[0],s[1])
        if prev is not None:
            dr.line([prev,pt],fill=cur,width=1)
        prev=pt
    return img, w, h

def main():
    outpath=sys.argv[1]
    files=sys.argv[2:]
    cell=320; cols=4
    rows=math.ceil(len(files)/cols)
    label_h=26
    sheet=Image.new("RGB",(cols*cell, rows*(cell+label_h)),"white")
    dr=ImageDraw.Draw(sheet)
    try: font=ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf",12)
    except: font=ImageFont.load_default()
    for i,f in enumerate(files):
        try: thumb,w,h=render_one(f,cell)
        except Exception as e:
            print(f"ERR {f}: {e}"); continue
        r,c=divmod(i,cols)
        x0=c*cell; y0=r*(cell+label_h)
        ox=x0+(cell-thumb.width)//2; oy=y0+label_h+(cell-thumb.height)//2
        sheet.paste(thumb,(ox,oy))
        name=os.path.basename(f)[:38]
        dr.text((x0+3,y0+4),f"{name}\n{w:.0f}x{h:.0f}mm",fill="black",font=font)
        dr.rectangle([x0,y0,x0+cell-1,y0+cell+label_h-1],outline=(200,200,200))
    sheet.save(outpath)
    print("wrote",outpath, sheet.size)

main()
