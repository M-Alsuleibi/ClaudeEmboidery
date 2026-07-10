#!/usr/bin/env python3
"""Batch byte-for-byte analysis of decoration reference VP3s.
Same methodology as letters/3D/simple-shapes: parse with pyembroidery, measure
threads/palette, size, satin-vs-fill via consecutive-segment turn-angle reversals
(>120 deg = satin reversal), trims, per-block geometry, and areal density.
Emits one compact line per file + a per-block breakdown, and a machine summary."""
import sys, glob, os, json
import numpy as np
import pyembroidery as pe

UNIT_MM = 0.1

def block_geom(pts):
    pts = np.array(pts, dtype=float)
    if len(pts) < 3:
        return None
    d = np.diff(pts, axis=0)
    seglen = np.hypot(d[:,0], d[:,1]) * UNIT_MM
    a = np.arctan2(d[:,1], d[:,0])
    da = (np.diff(a) + np.pi) % (2*np.pi) - np.pi
    turn = np.abs(np.degrees(da))
    rev = float(np.mean(turn > 120) * 100.0)
    valid = seglen[seglen > 0.05]
    med = float(np.median(valid)) if len(valid) else 0.0
    return dict(n=len(pts), rev=rev, med=med,
                maxseg=float(np.max(valid)) if len(valid) else 0.0)

def analyze(path):
    pat = pe.read(path)
    threads = pat.threadlist
    st = pat.stitches
    xs = [s[0] for s in st]; ys = [s[1] for s in st]
    w = (max(xs)-min(xs))*UNIT_MM; h = (max(ys)-min(ys))*UNIT_MM
    ntrim = sum(1 for s in st if (s[2]&0xFF)==(pe.TRIM&0xFF))
    ncc = sum(1 for s in st if (s[2]&0xFF)==(pe.COLOR_CHANGE&0xFF))
    nstitch = sum(1 for s in st if (s[2]&0xFF)==(pe.STITCH&0xFF))
    # blocks split on color change / break
    blocks=[]; cur=[]
    for s in st:
        cmd = s[2]&0xFF
        if cmd in (pe.COLOR_CHANGE&0xFF, pe.COLOR_BREAK&0xFF):
            if cur: blocks.append(cur); cur=[]
            continue
        if cmd in (pe.STITCH&0xFF, pe.JUMP&0xFF):
            cur.append((s[0],s[1]))
    if cur: blocks.append(cur)
    density = nstitch/(w*h) if w*h>0 else 0
    binfo=[]
    sat=fil=mix=0
    for blk in blocks:
        g = block_geom(blk)
        if not g: continue
        kind = "SATIN" if g['rev']>35 else ("FILL" if g['rev']<15 else "mix")
        if kind=="SATIN": sat+=1
        elif kind=="FILL": fil+=1
        else: mix+=1
        binfo.append((kind,g['rev'],g['med'],g['n']))
    thr=[]
    for t in threads:
        thr.append(dict(rgb=(t.get_red(),t.get_green(),t.get_blue()),
                        cat=t.catalog_number, desc=t.description, brand=t.brand))
    return dict(path=os.path.basename(path), w=w, h=h, st=len(st), nstitch=nstitch,
                trims=ntrim, cc=ncc, ncol=len(threads), threads=thr,
                density=density, blocks=binfo, sat=sat, fil=fil, mix=mix)

def main():
    files = sys.argv[1:]
    results=[]
    for f in sorted(files):
        try:
            r=analyze(f); results.append(r)
        except Exception as e:
            print(f"ERR {f}: {e}"); continue
    # compact table
    print(f"{'file':42s} {'WxH mm':>13s} {'st':>6s} {'trim':>5s} {'col':>3s} {'S/F/m':>7s} {'dens':>5s}")
    for r in results:
        print(f"{r['path'][:42]:42s} {r['w']:6.1f}x{r['h']:6.1f} {r['st']:6d} "
              f"{r['trims']:5d} {r['ncol']:3d} {r['sat']:2d}/{r['fil']:2d}/{r['mix']:2d} {r['density']:5.2f}")
    # dump json for downstream
    with open(os.path.join(os.path.dirname(__file__),'..','output','_analysis.json'),'w') as fp:
        json.dump(results, fp, indent=1)
    # detail per file
    for r in results:
        print(f"\n### {r['path']}  {r['w']:.1f}x{r['h']:.1f}mm  st={r['st']} trims={r['trims']} cols={r['ncol']} dens={r['density']:.2f}")
        for t in r['threads']:
            print(f"   rgb{t['rgb']} cat='{t['cat']}' desc='{t['desc']}' brand='{t['brand']}'")
        srev=[b[1] for b in r['blocks']]
        smed=[b[2] for b in r['blocks']]
        if srev:
            print(f"   blocks={len(r['blocks'])} S/F/mix={r['sat']}/{r['fil']}/{r['mix']} "
                  f"rev[min/med/max]={min(srev):.0f}/{np.median(srev):.0f}/{max(srev):.0f}% "
                  f"medW[min/med/max]={min(smed):.2f}/{np.median(smed):.2f}/{max(smed):.2f}mm")

if __name__=='__main__':
    main()
