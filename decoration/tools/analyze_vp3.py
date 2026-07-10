#!/usr/bin/env python3
"""Byte-for-byte analysis of the Arabic reference VP3 files.
Mirrors the methodology used for letters/3D: parse with pyembroidery, measure
threads, bounds, per-colour-block stitch geometry, and classify satin vs fill
via consecutive-segment turn-angle reversals (>120 deg = satin reversal)."""
import sys, math
import numpy as np
import pyembroidery as pe

UNIT_MM = 0.1  # 1 stitch unit = 0.1 mm

def seg_angles(pts):
    d = np.diff(pts, axis=0)
    return d

def analyze_block(stitches):
    """stitches: list of (x,y) in 0.1mm units for one colour block (stitch points)."""
    pts = np.array(stitches, dtype=float)
    if len(pts) < 3:
        return None
    d = np.diff(pts, axis=0)
    seglen = np.hypot(d[:,0], d[:,1]) * UNIT_MM  # mm
    # turn angle between consecutive segments
    a = np.arctan2(d[:,1], d[:,0])
    da = np.diff(a)
    da = (da + np.pi) % (2*np.pi) - np.pi
    turn = np.abs(np.degrees(da))
    reversals = np.mean(turn > 120) * 100.0  # percent of vertices that reverse
    # satin width estimate = median cross-segment length (the short hops across a column)
    # Use median of the shorter segments (column crossings)
    valid = seglen[seglen > 0.05]
    med_seg = np.median(valid) if len(valid) else 0.0
    return dict(
        n=len(pts),
        reversals=reversals,
        med_seg_mm=med_seg,
        mean_seg_mm=float(np.mean(valid)) if len(valid) else 0.0,
        max_seg_mm=float(np.max(valid)) if len(valid) else 0.0,
    )

def dominant_angles(stitches, topk=4):
    pts = np.array(stitches, dtype=float)
    if len(pts) < 3:
        return []
    d = np.diff(pts, axis=0)
    seglen = np.hypot(d[:,0], d[:,1])
    # weight by length, fold to 0-180
    ang = (np.degrees(np.arctan2(d[:,1], d[:,0])) % 180)
    hist = np.zeros(180)
    for a, w in zip(ang, seglen):
        hist[int(a) % 180] += w
    # smooth
    k = np.ones(7)/7
    hs = np.convolve(np.concatenate([hist[-7:],hist,hist[:7]]), k, 'same')[7:-7]
    peaks = []
    for i in range(180):
        if hs[i] >= hs[(i-1)%180] and hs[i] >= hs[(i+1)%180] and hs[i] > 0:
            peaks.append((hs[i], i))
    peaks.sort(reverse=True)
    return [p[1] for p in peaks[:topk]]

def analyze_file(path):
    pat = pe.read(path)
    threads = pat.threadlist
    stitches = pat.stitches  # list of [x, y, cmd]
    # bounds
    xs = [s[0] for s in stitches]
    ys = [s[1] for s in stitches]
    w_mm = (max(xs)-min(xs))*UNIT_MM
    h_mm = (max(ys)-min(ys))*UNIT_MM
    # command histogram
    cmds = {}
    for s in stitches:
        c = s[2]
        cmds[c] = cmds.get(c,0)+1
    # split into colour blocks by COLOR_CHANGE / by thread
    blocks = []
    cur = []
    for s in stitches:
        c = s[2]
        cmd = c & 0xFF
        if cmd in (pe.COLOR_CHANGE & 0xFF, pe.COLOR_BREAK & 0xFF):
            if cur:
                blocks.append(cur); cur=[]
            continue
        if cmd in (pe.STITCH & 0xFF, pe.JUMP & 0xFF):
            cur.append((s[0], s[1]))
        elif cmd in (pe.TRIM & 0xFF,):
            pass  # keep within block but break continuity; ignore for now
    if cur:
        blocks.append(cur)

    print(f"\n{'='*70}\n{path}")
    print(f"  size: {w_mm:.1f} x {h_mm:.1f} mm   stitches: {len(stitches)}")
    # count trims
    ntrim = sum(1 for s in stitches if (s[2]&0xFF)==(pe.TRIM&0xFF))
    njump = sum(1 for s in stitches if (s[2]&0xFF)==(pe.JUMP&0xFF))
    ncc   = sum(1 for s in stitches if (s[2]&0xFF)==(pe.COLOR_CHANGE&0xFF))
    nstitch = sum(1 for s in stitches if (s[2]&0xFF)==(pe.STITCH&0xFF))
    print(f"  trims: {ntrim}  jumps: {njump}  color_changes: {ncc}  pure_stitch: {nstitch}")
    print(f"  threads ({len(threads)}):")
    for t in threads:
        rgb = (t.get_red(), t.get_green(), t.get_blue())
        print(f"    rgb{rgb}  catalog='{t.catalog_number}' desc='{t.description}' brand='{t.brand}' chart='{getattr(t,'chart','')}'")
    print(f"  colour blocks (by color_change): {len(blocks)}")
    for i, blk in enumerate(blocks):
        info = analyze_block(blk)
        if info is None:
            print(f"    block {i}: (too short, {len(blk)} pts)")
            continue
        angs = dominant_angles(blk)
        kind = "SATIN" if info['reversals'] > 35 else ("FILL" if info['reversals'] < 15 else "mixed")
        # density approx
        print(f"    block {i}: {kind:5s}  pts={info['n']:5d}  rev={info['reversals']:5.1f}%  "
              f"medSeg={info['med_seg_mm']:.2f}mm maxSeg={info['max_seg_mm']:.1f}mm  angles={angs}")

for p in sys.argv[1:]:
    analyze_file(p)
