#!/usr/bin/env python3
"""Build a production .vp3 for 3d-knowlege-test.png applying the 3D-embroidery
rules learned from مكعب.VP3 / البطيخ(1).VP3 + their stitch-out videos.

Rules applied (see 3d-embroidery-knowledge.md):
  * one flat tatami fill per visible FACET (not per colour)
  * 4 mm max stitch length, 0.4 mm row spacing, fill underlay, pull comp, trim
  * a DISTINCT fill angle per facet so adjacent faces read as separate planes
  * lighter shade = lit facet, darker shade = shadow facet
  * strict back-to-front document order (Ink-Stitch stitches in this order)
  * every edge traced LAST with a black bean (triple) running-stitch outline

Pipeline: author SVG -> vendored Ink-Stitch headless -> VP3 (same call the
repo's step-5 uses).
"""
from __future__ import annotations
import io, math, os, subprocess, zipfile, tempfile
from pathlib import Path
from lxml import etree
import pyembroidery as pe

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
INKSTITCH = Path(os.environ.get("INKSTITCH_BIN", REPO / "vendor/inkstitch/bin/inkstitch"))
SVG_NS = "http://www.w3.org/2000/svg"
INK = "http://inkstitch.org/namespace"
INKSCAPE = "http://www.inkscape.org/namespaces/inkscape"

MM_PER_PX = 0.20          # 1200 px image -> 240 mm design
IMG = 1200

FILL = {                  # measured from both reference files
    "fill_underlay": "True",
    "row_spacing_mm": "0.4",
    "max_stitch_length_mm": "4",
    "pull_compensation_mm": "0.2",
    "trim_after": "True",
}
RUN = {                   # black wireframe outline = bold running stitch (cube ref)
    "stroke_method": "running_stitch",
    "running_stitch_length_mm": "2.2",
    "bean_stitch_repeats": "1",     # triple pass -> bold edge
    "trim_after": "True",
}

# --------------------------------------------------------------------------- #
# geometry (image px, y-down) extracted from the test PNG
# --------------------------------------------------------------------------- #
# PYRAMID
T  = (284, 224); BL = (33, 576); BF = (127, 712); BR = (562, 718)
# CUBE
V_TL=(566,30); V_TR=(897,27); V_RT=(1068,101); V_RB=(1067,472)
V_FB=(695,473); V_LB=(562,355); V_FT=(688,86)
# CYLINDER
F_C=(720,971); CYL_A=214.0; CYL_B=174.0; CYL_ANG=69.0
B_C=(F_C[0]+291, F_C[1]-132)            # back cap centre (parallel ellipse)

def ellipse(c, A, B, ang_deg, n=72, t0=0.0, t1=2*math.pi):
    a = math.radians(ang_deg); u=(math.cos(a),math.sin(a)); v=(-math.sin(a),math.cos(a))
    pts=[]
    for i in range(n+1):
        t=t0+(t1-t0)*i/n
        ca,sa=math.cos(t)*A, math.sin(t)*B
        pts.append((c[0]+ca*u[0]+sa*v[0], c[1]+ca*u[1]+sa*v[1]))
    return pts

def convex_hull(points):
    pts=sorted(set(points))
    if len(pts)<3: return pts
    def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[]
    for p in pts:
        while len(lo)>=2 and cross(lo[-2],lo[-1],p)<=0: lo.pop()
        lo.append(p)
    up=[]
    for p in reversed(pts):
        while len(up)>=2 and cross(up[-2],up[-1],p)<=0: up.pop()
        up.append(p)
    return lo[:-1]+up[:-1]

front_ell = ellipse(F_C, CYL_A, CYL_B, CYL_ANG)
back_ell  = ellipse(B_C, CYL_A, CYL_B, CYL_ANG)
body_hull = convex_hull(front_ell + back_ell)
# back rim visible far arc (the up-right half) for the outline
back_arc  = ellipse(B_C, CYL_A, CYL_B, CYL_ANG, n=40,
                    t0=math.radians(CYL_ANG-90), t1=math.radians(CYL_ANG+90))

# --------------------------------------------------------------------------- #
# facets: (id, [verts], fill hex, angle, thread label)  -- back-to-front order
# --------------------------------------------------------------------------- #
FILLS = [
    # PYRAMID (two visible faces; left in shadow, right lit)
    ("pyr_left",  [T,BL,BF],            "#6d9432", 70,  "Pyramid Shadow Green"),
    ("pyr_right", [T,BF,BR],            "#81ba27", 115, "Pyramid Light Green"),
    # CUBE (left dark, right mid, top light) -- distinct angle per face
    ("cube_left", [V_TL,V_FT,V_FB,V_LB],"#cd141d", 72,  "Cube Shadow Red"),
    ("cube_right",[V_FT,V_RT,V_RB,V_FB],"#e32328", 112, "Cube Front Red"),
    ("cube_top",  [V_TL,V_TR,V_RT,V_FT],"#e9544a", 18,  "Cube Top Red"),
    # CYLINDER (body behind, then near cap on top)
    ("cyl_body",  body_hull,            "#40aad4", 65,  "Cylinder Body Blue"),
    ("cyl_cap",   front_ell,            "#60c4e6", 158, "Cylinder Cap Blue"),
]
# OUTLINES (black, stitched last)
OUTLINES = [
    ("o_pyr",   [T,BL,BF,BR], True,  [(T,BF)]),            # silhouette + ridge
    ("o_cube",  [V_TL,V_TR,V_RT,V_RB,V_FB,V_LB], True,
                [(V_FT,V_TL),(V_FT,V_RT),(V_FT,V_FB)]),    # hexagon + 3 inner
    ("o_cyl_body", body_hull, True, []),
    ("o_cyl_cap",  front_ell, True, []),
    ("o_cyl_back", back_arc,  False, []),
]

def d_poly(pts, close=True):
    s="M "+" L ".join(f"{x:.2f},{y:.2f}" for x,y in pts)
    return s+(" Z" if close else "")

def build_svg(dst: Path):
    nsmap={None:SVG_NS,"inkstitch":INK,"inkscape":INKSCAPE}
    svg=etree.Element(f"{{{SVG_NS}}}svg", nsmap=nsmap)
    svg.set("version","1.1")
    svg.set("width", f"{IMG*MM_PER_PX:.3f}mm")
    svg.set("height",f"{IMG*MM_PER_PX:.3f}mm")
    svg.set("viewBox",f"0 0 {IMG} {IMG}")
    for fid,pts,hexc,ang,label in FILLS:
        g=etree.SubElement(svg,f"{{{SVG_NS}}}g"); g.set("id",f"f_{fid}")
        g.set(f"{{{INKSCAPE}}}label",label)
        p=etree.SubElement(g,f"{{{SVG_NS}}}path"); p.set("id",fid)
        p.set("d",d_poly(pts)); p.set("style",f"fill:{hexc};stroke:none")
        p.set(f"{{{INK}}}angle",str(ang))
        for k,v in FILL.items(): p.set(f"{{{INK}}}{k}",v)
    for oid,pts,close,extra in OUTLINES:
        g=etree.SubElement(svg,f"{{{SVG_NS}}}g"); g.set("id",f"o_{oid}")
        g.set(f"{{{INKSCAPE}}}label","Black Outline")
        p=etree.SubElement(g,f"{{{SVG_NS}}}path"); p.set("id",oid)
        p.set("d",d_poly(pts,close)); p.set("style","fill:none;stroke:#000000;stroke-width:2")
        for k,v in RUN.items(): p.set(f"{{{INK}}}{k}",v)
        for j,(a,b) in enumerate(extra):
            p2=etree.SubElement(g,f"{{{SVG_NS}}}path"); p2.set("id",f"{oid}_e{j}")
            p2.set("d",d_poly([a,b],False)); p2.set("style","fill:none;stroke:#000000;stroke-width:2")
            for k,v in RUN.items(): p2.set(f"{{{INK}}}{k}",v)
    etree.ElementTree(svg).write(str(dst),pretty_print=True,xml_declaration=True,encoding="UTF-8")

def run_inkstitch(svg: Path) -> pe.EmbPattern:
    proc=subprocess.run([str(INKSTITCH),"--extension=zip","--format-vp3=True",str(svg)],
                        capture_output=True,timeout=300)
    if proc.returncode!=0:
        raise RuntimeError(f"Ink-Stitch exit {proc.returncode}: {proc.stderr.decode('utf-8','replace')[:1500]}")
    zf=zipfile.ZipFile(io.BytesIO(proc.stdout))
    name=[n for n in zf.namelist() if n.lower().endswith(".vp3")][0]
    with tempfile.NamedTemporaryFile(suffix=".vp3",delete=False) as t:
        t.write(zf.read(name)); tp=t.name
    try: return pe.read(tp)
    finally: os.unlink(tp)

if __name__=="__main__":
    svg=HERE/"3d-test.svg"; build_svg(svg)
    print("wrote",svg)
    pat=run_inkstitch(svg)
    out=HERE/"3d-knowlege-test.vp3"; pe.write_vp3(pat,str(out))
    from collections import Counter
    cmd=Counter(c&0xFF for _,_,c in pat.stitches)
    xs=[s[0] for s in pat.stitches]; ys=[s[1] for s in pat.stitches]
    print(f"VP3 -> {out}")
    print(f"  stitches={cmd.get(pe.STITCH&0xFF,0)} colors={len(pat.threadlist)} "
          f"trims={cmd.get(pe.TRIM&0xFF,0)} jumps={cmd.get(pe.JUMP&0xFF,0)}")
    print(f"  size={ (max(xs)-min(xs))/10:.1f} x {(max(ys)-min(ys))/10:.1f} mm")
    for i,t in enumerate(pat.threadlist):
        print(f"  [{i}] #{t.get_red():02x}{t.get_green():02x}{t.get_blue():02x} {t.description!r}")
