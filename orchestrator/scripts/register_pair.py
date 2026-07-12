#!/usr/bin/env python3
"""SVG<->VP3 REGISTRATION for a (CorelDRAW-SVG, production-VP3) pair — per-object labels.

extract_pair.py reads the pair's *structure* (families, colours, order) but the SVG's own
coordinates don't map to mm (off-page/clipping paths skew the bbox; naive aspect mismatches
the VP3). This script recovers the missing scale-DEPENDENT truth:

  1. REGISTER: align the SVG ink to the VP3 stitch footprint with a similarity transform
     (scale + rotation + translation) fitted by trimmed ICP over nearest-stitch
     correspondences — robust to outlier paths (clipping rects, off-page junk), which are
     reported, not fitted.
  2. MEASURE each SVG object in real mm: fill objects get area + EDT stroke width; outline
     objects get their stitched column width.
  3. OVERLAY the VP3 stitches per object region: stitch count, density, effective row
     spacing (area / thread length), and a satin-vs-tatami verdict per region
     (fingerprint._block_kind on the stitch runs inside the region mask).

    python register_pair.py pink-goku.svg pink-goku.VP3
        -> <stem>_measures.json  +  <stem>_reg.png (red=SVG ink, blue=stitches, purple=match)

Feeds THIS pipeline's knowledge (width tiers, satin ceilings, density priors), not a model.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import pyembroidery as pe  # noqa: E402
from scipy import ndimage  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
from wilcom_pipeline.fingerprint import _block_kind  # noqa: E402

UNIT_MM = 0.1          # VP3 stitch units -> mm
SAMPLE_STEP_UU = 25.0  # target spacing when sampling SVG paths (CorelDRAW uu, ~0.25mm @ A4)
ICP_ITERS = 40
ICP_KEEP = 0.75        # trimmed fraction of correspondences kept each iteration
OUTLIER_MM = 2.0       # a sampled SVG point "hits" the design if a stitch is within this
OUTLIER_PATH_FRAC = 0.5  # >this fraction of misses -> the whole path is a non-stitched outlier
RASTER_MM_PX = 0.4     # per-object mask resolution
OUTLINE_HALO_MM = 1.2  # half-width when rasterising an outline object's polyline mask


# --------------------------------------------------------------------------- #
# SVG parsing (CorelDRAW export: class-styled paths, M/l/c/z data)
# --------------------------------------------------------------------------- #
_NUM = re.compile(r"-?\d*\.?\d+(?:e-?\d+)?", re.I)


def _tokenize(d: str):
    for cmd, args in re.findall(r"([MmLlHhVvCcSsQqTtZz])([^MmLlHhVvCcSsQqTtZz]*)", d):
        yield cmd, [float(v) for v in _NUM.findall(args)]


def _cubic(p0, p1, p2, p3, n=8):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def flatten_path(d: str) -> list[np.ndarray]:
    """Path data -> list of sampled subpath polylines (absolute coords)."""
    subs: list[list] = []
    cur = np.zeros(2)
    start = np.zeros(2)
    prev_ctrl = None
    pts: list = []
    for cmd, a in _tokenize(d):
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            if pts:
                subs.append(pts)
            cur = (cur + a[:2]) if rel and pts else np.asarray(a[:2])
            if rel and not pts and subs:
                cur = subs[-1][0] + np.asarray(a[:2])
            start = cur.copy()
            pts = [cur.copy()]
            for i in range(2, len(a), 2):           # extra pairs = implicit lineto
                cur = cur + a[i:i + 2] if rel else np.asarray(a[i:i + 2])
                pts.append(cur.copy())
            prev_ctrl = None
        elif c == "L":
            for i in range(0, len(a), 2):
                cur = cur + a[i:i + 2] if rel else np.asarray(a[i:i + 2])
                pts.append(cur.copy())
            prev_ctrl = None
        elif c == "H":
            for v in a:
                cur = np.array([cur[0] + v if rel else v, cur[1]])
                pts.append(cur.copy())
            prev_ctrl = None
        elif c == "V":
            for v in a:
                cur = np.array([cur[0], cur[1] + v if rel else v])
                pts.append(cur.copy())
            prev_ctrl = None
        elif c in "CS":
            step = 6 if c == "C" else 4
            for i in range(0, len(a) - step + 1, step):
                seg = np.asarray(a[i:i + step]).reshape(-1, 2)
                if rel:
                    seg = seg + cur
                if c == "C":
                    p1, p2, p3 = seg
                else:                               # smooth: reflect previous control
                    p1 = 2 * cur - prev_ctrl if prev_ctrl is not None else cur
                    p2, p3 = seg
                pts.extend(_cubic(cur, p1, p2, p3))
                prev_ctrl = p2
                cur = p3.copy()
        elif c in "QT":
            step = 4 if c == "Q" else 2
            for i in range(0, len(a) - step + 1, step):
                seg = np.asarray(a[i:i + step]).reshape(-1, 2)
                if rel:
                    seg = seg + cur
                if c == "Q":
                    q, p3 = seg
                else:
                    q = 2 * cur - prev_ctrl if prev_ctrl is not None else cur
                    p3 = seg[0]
                pts.extend(_cubic(cur, cur + 2 / 3 * (q - cur), p3 + 2 / 3 * (q - p3), p3))
                prev_ctrl = q
                cur = p3.copy()
        elif c == "Z":
            if pts:
                pts.append(start.copy())
            cur = start.copy()
            prev_ctrl = None
    if pts:
        subs.append(pts)
    out = []
    for s in subs:
        arr = np.asarray(s, float)
        if len(arr) >= 2:
            out.append(arr)
    return out


def _resample(poly: np.ndarray, step: float) -> np.ndarray:
    """Even arc-length resampling so long segments don't under-weight the ICP."""
    seg = np.diff(poly, axis=0)
    lens = np.hypot(seg[:, 0], seg[:, 1])
    total = lens.sum()
    if total < 1e-9:
        return poly[:1]
    n = max(int(total / step), 1)
    at = np.linspace(0, total, n + 1)
    cum = np.concatenate([[0], np.cumsum(lens)])
    out = np.empty((len(at), 2))
    idx = np.searchsorted(cum, at, side="right") - 1
    idx = np.clip(idx, 0, len(lens) - 1)
    f = (at - cum[idx]) / np.where(lens[idx] < 1e-9, 1, lens[idx])
    out = poly[idx] + f[:, None] * seg[idx]
    return out


def parse_svg(svg_path: Path) -> list[dict]:
    """All class-styled paths, in document (sew) order, with family/colour/sampled points."""
    svg = svg_path.read_text()
    style: dict[str, dict] = {}
    for name, body in re.findall(r"\.(\w+)\s*\{([^}]*)\}", svg):
        d = style.setdefault(name, {})
        if m := re.search(r"fill:\s*([^;}\s]+)", body):
            d["fill"] = None if m.group(1) == "none" else m.group(1)
        if m := re.search(r"stroke:\s*([^;}\s]+)", body):
            d["stroke"] = m.group(1)
        if m := re.search(r"stroke-width:\s*([\d.]+)", body):
            d["stroke_width"] = float(m.group(1))

    def hx(c):
        if c is None:
            return None
        return "#000000" if c == "black" else c.upper()

    objs = []
    for i, (cls, d) in enumerate(re.findall(r'<path\s+class="([^"]*)"\s+d="([^"]*)"', svg)):
        toks = cls.split()
        subs = flatten_path(d)
        if not subs:
            continue
        if toks[0] != "fil0":
            fam, colour = "fill", hx(style.get(toks[0], {}).get("fill"))
        else:
            strk = next((t for t in toks if t.startswith("str")), None)
            fam, colour = "outline", hx(style.get(strk, {}).get("stroke") if strk else None)
        objs.append({"i": i, "family": fam, "colour": colour, "class": cls, "subs": subs})
    return objs


# --------------------------------------------------------------------------- #
# registration (trimmed-ICP similarity)
# --------------------------------------------------------------------------- #
def _umeyama(src: np.ndarray, dst: np.ndarray):
    """Closed-form 2D similarity (scale s, rotation R, translation t): dst ~ s*R@src + t."""
    ms, md = src.mean(0), dst.mean(0)
    S, D = src - ms, dst - md
    C = D.T @ S / len(src)
    U, sig, Vt = np.linalg.svd(C)
    d = np.sign(np.linalg.det(U) * np.linalg.det(Vt))
    R = U @ np.diag([1.0, d]) @ Vt
    var = (S ** 2).sum() / len(src)
    s = (sig * np.array([1.0, d])).sum() / max(var, 1e-12)
    t = md - s * (R @ ms)
    return s, R, t


def register(svg_pts: np.ndarray, vp3_pts: np.ndarray):
    """Robust similarity aligning SVG samples to the stitch cloud. Init from medians + MAD
    (outlier paths can't skew those the way a bbox is skewed), then trimmed ICP."""
    med_s, med_v = np.median(svg_pts, 0), np.median(vp3_pts, 0)
    mad_s = np.median(np.abs(svg_pts - med_s), 0)
    mad_v = np.median(np.abs(vp3_pts - med_v), 0)
    s = float(np.mean(mad_v / np.where(mad_s < 1e-9, 1, mad_s)))
    R = np.eye(2)
    t = med_v - s * med_s

    tree = cKDTree(vp3_pts)
    n_keep = max(int(len(svg_pts) * ICP_KEEP), 10)
    for _ in range(ICP_ITERS):
        cur = svg_pts @ (s * R).T + t
        dist, near = tree.query(cur, k=1)
        keep = np.argsort(dist)[:n_keep]
        s2, R2, t2 = _umeyama(svg_pts[keep], vp3_pts[near[keep]])
        if abs(s2 - s) < 1e-5 * s and np.allclose(t2, t, atol=1e-3):
            s, R, t = s2, R2, t2
            break
        s, R, t = s2, R2, t2
    cur = svg_pts @ (s * R).T + t
    dist, _ = tree.query(cur, k=1)
    rms = float(np.sqrt((np.sort(dist)[:n_keep] ** 2).mean()))
    return s, R, t, rms, dist


def apply_T(pts: np.ndarray, s: float, R: np.ndarray, t: np.ndarray) -> np.ndarray:
    return pts @ (s * R).T + t


# --------------------------------------------------------------------------- #
# per-object measurement
# --------------------------------------------------------------------------- #
def _shoelace(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _object_mask(subs_mm, family, bounds, res=RASTER_MM_PX):
    """Rasterise one object into a bool mask over the design bounds (mm frame)."""
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bounds
    W = int((x1 - x0) / res) + 2
    H = int((y1 - y0) / res) + 2
    im = Image.new("L", (W, H), 0)
    dr = Image.core if False else ImageDraw.Draw(im)
    for spts in subs_mm:
        px = [((x - x0) / res, (y - y0) / res) for x, y in spts]
        if family == "fill" and len(px) >= 3:
            dr.polygon(px, fill=255)
        else:
            dr.line(px, fill=255, width=max(int(2 * OUTLINE_HALO_MM / res), 1))
    return np.asarray(im) > 128, (x0, y0, res)


def _width_from_mask(mask: np.ndarray, res: float) -> float | None:
    """2 x median ridge EDT = the region's typical stroke width (mm)."""
    if mask.sum() < 4:
        return None
    dist = ndimage.distance_transform_edt(mask)
    ridge = (dist >= ndimage.maximum_filter(dist, size=3)) & (dist > 0)
    w = dist[ridge]
    return float(2 * np.median(w) * res) if w.size else None


def _stitch_blocks(pat) -> list[tuple[int, np.ndarray]]:
    """[(thread index, (N,2) mm stitch runs pts)] — one entry per colour block."""
    blocks, cur, ti = [], [], 0
    for x, y, c in pat.stitches:
        cmd = c & 0xFF
        if cmd == (pe.COLOR_CHANGE & 0xFF):
            blocks.append((ti, np.asarray(cur) * UNIT_MM if cur else np.empty((0, 2))))
            cur, ti = [], ti + 1
        elif cmd == (pe.STITCH & 0xFF):
            cur.append((x, y))
    blocks.append((ti, np.asarray(cur) * UNIT_MM if cur else np.empty((0, 2))))
    return [(i, b) for i, b in blocks if len(b)]


def _rgb(hexs: str) -> np.ndarray:
    return np.array([int(hexs[i:i + 2], 16) for i in (1, 3, 5)], float)


def measure_objects(objs, pat, s, R, t, dist_per_pt, pt_path_idx):
    threads = [np.array([th.get_red(), th.get_green(), th.get_blue()], float)
               for th in pat.threadlist]
    blocks = _stitch_blocks(pat)
    all_st = np.concatenate([b for _, b in blocks])
    x0, y0 = all_st.min(0) - 2
    x1, y1 = all_st.max(0) + 2
    bounds = (x0, y0, x1, y1)

    # flag outlier paths (clipping/off-page): most sampled points miss the stitch cloud
    outlier = {}
    for k in set(pt_path_idx.tolist()):
        d = dist_per_pt[pt_path_idx == k]
        outlier[k] = float((d > OUTLIER_MM).mean()) > OUTLIER_PATH_FRAC

    rows = []
    for o in objs:
        subs_mm = [apply_T(sp, s, R, t) for sp in o["subs"]]
        rec = {"i": o["i"], "family": o["family"], "colour": o["colour"],
               "outlier": bool(outlier.get(o["i"], False))}
        if rec["outlier"]:
            rows.append(rec)
            continue
        mask, (mx, my, res) = _object_mask(subs_mm, o["family"], bounds)
        area_mm2 = (sum(_shoelace(sp) for sp in subs_mm if len(sp) >= 3)
                    if o["family"] == "fill" else float(mask.sum()) * res * res)
        rec["area_mm2"] = round(area_mm2, 2)
        if o["family"] == "fill":
            w = _width_from_mask(mask, res)
            if w is not None:
                rec["width_mm"] = round(w, 2)

        # stitches inside the mask, from same-colour blocks only
        want = _rgb(o["colour"]) if o["colour"] else None
        n_in, thread_len, runs = 0, 0.0, []
        for ti, bpts in blocks:
            if want is not None and threads:
                if np.linalg.norm(threads[ti % len(threads)] - want) > 90:
                    continue
            ix = ((bpts[:, 0] - mx) / res).astype(int)
            iy = ((bpts[:, 1] - my) / res).astype(int)
            ok = (ix >= 0) & (ix < mask.shape[1]) & (iy >= 0) & (iy < mask.shape[0])
            inside = np.zeros(len(bpts), bool)
            inside[ok] = mask[iy[ok], ix[ok]]
            n_in += int(inside.sum())
            ids = np.where(inside)[0]
            if ids.size < 2:
                continue
            for run in np.split(ids, np.where(np.diff(ids) > 1)[0] + 1):
                if run.size >= 8:
                    seg = np.diff(bpts[run], axis=0)
                    thread_len += float(np.hypot(seg[:, 0], seg[:, 1]).sum())
                    runs.append(bpts[run] / UNIT_MM)   # _block_kind expects 0.1mm units
        rec["n_stitches"] = n_in
        if area_mm2 > 1 and n_in:
            rec["density_st_mm2"] = round(n_in / area_mm2, 2)
            if thread_len:
                rec["row_spacing_mm"] = round(area_mm2 / thread_len, 2)
        # satin-vs-tatami verdict: majority stitch count over classified runs
        votes: dict[str, int] = {}
        widths = []
        for rpts in runs:
            kind, med, n = _block_kind([tuple(p) for p in rpts])
            votes[kind] = votes.get(kind, 0) + n
            if kind == "satin" and med:
                widths.append(med)
        if votes:
            rec["stitch_kind"] = max(votes, key=votes.get)
            rec["kind_votes"] = votes
            if widths:
                rec["satin_w_mm"] = round(float(np.median(widths)), 2)
        rows.append(rec)
    return rows, bounds


def overlay_png(objs, rows, pat, s, R, t, bounds, dst: Path):
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bounds
    res = max((x1 - x0), (y1 - y0)) / 1200
    W, H = int((x1 - x0) / res) + 4, int((y1 - y0) / res) + 4
    ink = Image.new("L", (W, H), 0)
    di = ImageDraw.Draw(ink)
    flagged = {r["i"] for r in rows if r.get("outlier")}
    for o in objs:
        if o["i"] in flagged:
            continue
        for sp in o["subs"]:
            pts = apply_T(sp, s, R, t)
            di.line([((x - x0) / res, (y - y0) / res) for x, y in pts], fill=255, width=2)
    st = Image.new("L", (W, H), 0)
    ds = ImageDraw.Draw(st)
    prev = None
    for x, y, c in pat.stitches:
        cmd = c & 0xFF
        p = ((x * UNIT_MM - x0) / res, (y * UNIT_MM - y0) / res)
        if cmd == (pe.STITCH & 0xFF):
            if prev is not None:
                ds.line([prev, p], fill=255, width=1)
            prev = p
        else:
            prev = None
    a, b = np.asarray(ink) > 0, np.asarray(st) > 0
    img = np.full((H, W, 3), 255, np.uint8)
    img[a & ~b] = (220, 40, 40)
    img[b & ~a] = (40, 60, 220)
    img[a & b] = (140, 40, 160)
    Image.fromarray(img).save(dst)


def main():
    svg_path, vp3_path = Path(sys.argv[1]), Path(sys.argv[2])
    objs = parse_svg(svg_path)
    pat = pe.read(str(vp3_path))
    vp3_pts = np.asarray([(x * UNIT_MM, y * UNIT_MM) for x, y, c in pat.stitches
                          if (c & 0xFF) == (pe.STITCH & 0xFF)])

    clouds, idx = [], []
    for o in objs:
        for sp in o["subs"]:
            r = _resample(sp, SAMPLE_STEP_UU)
            clouds.append(r)
            idx.append(np.full(len(r), o["i"]))
    svg_pts = np.concatenate(clouds)
    pt_path_idx = np.concatenate(idx)

    s, R, t, rms, dist = register(svg_pts, vp3_pts)
    rot_deg = float(np.degrees(np.arctan2(R[1, 0], R[0, 0])))
    rows, bounds = measure_objects(objs, pat, s, R, t, dist, pt_path_idx)

    n_out = sum(1 for r in rows if r.get("outlier"))
    kinds = {}
    for r in rows:
        if "stitch_kind" in r:
            kinds[r["stitch_kind"]] = kinds.get(r["stitch_kind"], 0) + 1
    print(f"=== {svg_path.stem}: SVG<->VP3 registration ===")
    print(f"  similarity: scale {s:.5f} mm/uu  rotation {rot_deg:.2f} deg  "
          f"translation ({t[0]:.1f}, {t[1]:.1f}) mm")
    print(f"  trimmed RMS residual: {rms:.2f} mm over {len(svg_pts)} samples")
    print(f"  objects: {len(rows)}  ({n_out} flagged as non-stitched outliers)")
    print(f"  stitch-kind verdicts: {kinds}")
    fills = [r for r in rows if r["family"] == "fill" and "width_mm" in r]
    if fills:
        ws = [r["width_mm"] for r in fills]
        print(f"  fill-object widths (mm): median {np.median(ws):.2f}  "
              f"p10 {np.percentile(ws, 10):.2f}  p90 {np.percentile(ws, 90):.2f}")

    out = svg_path.with_name(svg_path.stem + "_measures.json")
    out.write_text(json.dumps({
        "design": svg_path.stem,
        "transform": {"scale_mm_per_uu": s, "rotation_deg": rot_deg,
                      "translation_mm": t.tolist(), "trimmed_rms_mm": rms},
        "objects": rows,
    }, indent=1))
    png = svg_path.with_name(svg_path.stem + "_reg.png")
    overlay_png(objs, rows, pat, s, R, t, bounds, png)
    print(f"wrote {out.name} + {png.name}")


if __name__ == "__main__":
    main()
