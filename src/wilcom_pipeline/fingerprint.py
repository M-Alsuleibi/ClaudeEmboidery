"""Per-category statistical fingerprints of the ground-truth production VP3s.

One feature vector per design (extracted identically from a ground-truth file offline or
from the pipeline's own `ctx.stitch_pattern` at verify time), aggregated per category into
`data/category_profiles.json`. Step 7 scores each run against its category's fingerprint and
warns when it drifts outside the truth's p25–p75 band — turning the hand-tuned gate into a
data-derived "does this look like real production for its category?" check.

Not machine learning in the deep sense: with ~83 unpaired ground-truth files (some categories
<= 4), we fit distributions, not weights. A block is SATIN if >35% of its vertices reverse
(turn >120 deg), FILL if <15%, else mixed (matches analyze_vp3.py); density = n_stitch / bbox
area (matches verify.py). See memory: wilcom-stitch-type-taxonomy, per-region-tiering.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyembroidery as pe

from .config import SUPPORTED_CATEGORIES as CATEGORIES

_UNIT_MM = 0.1  # one stitch unit = 0.1 mm
_REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_PATH = _REPO_ROOT / "data" / "category_profiles.json"

# Numeric features aggregated per category. Ordered; the drift check reports on a subset.
FEATURES = (
    "longest_mm", "aspect", "n_stitch", "n_colors", "n_blocks", "density",
    "satin_frac", "fill_frac", "mixed_frac", "satin_w_mm", "fill_seg_mm",
    "stitch_len_mm", "trim_rate", "frag",
)
# The features whose drift is worth surfacing on every run (the production-style signals).
_DRIFT_KEYS = ("satin_frac", "fill_frac", "n_colors", "density", "satin_w_mm")

_STITCH = pe.STITCH & 0xFF
_JUMP = pe.JUMP & 0xFF
_TRIM = pe.TRIM & 0xFF
_CC = pe.COLOR_CHANGE & 0xFF
_CB = pe.COLOR_BREAK & 0xFF


def _block_kind(pts: list[tuple[float, float]]):
    """(kind, median_segment_mm, n_points) for one colour block, or None if too short.
    kind: 'satin' (>35% vertices reverse), 'fill' (<15%), else 'mixed'."""
    p = np.asarray(pts, float)
    if len(p) < 3:
        return None
    d = np.diff(p, axis=0)
    seg = np.hypot(d[:, 0], d[:, 1]) * _UNIT_MM
    a = np.arctan2(d[:, 1], d[:, 0])
    da = (np.diff(a) + np.pi) % (2 * np.pi) - np.pi
    rev = float(np.mean(np.abs(np.degrees(da)) > 120) * 100)
    valid = seg[seg > 0.05]
    med = float(np.median(valid)) if valid.size else 0.0
    kind = "satin" if rev > 35 else ("fill" if rev < 15 else "mixed")
    return kind, med, len(p)


def features_from_pattern(stitches, threadlist) -> dict:
    """Extract the feature vector from a pyembroidery pattern's stitches + threadlist.
    Used both offline (ground-truth files) and at verify time (ctx.stitch_pattern)."""
    xs = [s[0] for s in stitches]
    ys = [s[1] for s in stitches]
    w = (max(xs) - min(xs)) * _UNIT_MM if xs else 0.0
    h = (max(ys) - min(ys)) * _UNIT_MM if ys else 0.0
    n_stitch = sum(1 for s in stitches if (s[2] & 0xFF) == _STITCH)
    n_trim = sum(1 for s in stitches if (s[2] & 0xFF) == _TRIM)
    n_jump = sum(1 for s in stitches if (s[2] & 0xFF) == _JUMP)

    blocks: list[list] = []
    cur: list = []
    for s in stitches:
        cmd = s[2] & 0xFF
        if cmd in (_CC, _CB):
            if cur:
                blocks.append(cur)
                cur = []
        elif cmd in (_STITCH, _JUMP):
            cur.append((s[0], s[1]))
    if cur:
        blocks.append(cur)

    satin_n = fill_n = mixed_n = 0
    satin_w: list[float] = []
    fill_seg: list[float] = []
    all_seg: list[float] = []
    for b in blocks:
        r = _block_kind(b)
        if not r:
            continue
        kind, med, n = r
        all_seg.append(med)
        if kind == "satin":
            satin_n += n
            satin_w.append(med)
        elif kind == "fill":
            fill_n += n
            fill_seg.append(med)
        else:
            mixed_n += n
    tot = max(satin_n + fill_n + mixed_n, 1)
    n_col = len(threadlist)
    area = max(w * h, 1e-6)
    return {
        "longest_mm": max(w, h),
        "aspect": max(w, h) / max(min(w, h), 1e-6),
        "n_stitch": n_stitch,
        "n_colors": n_col,
        "n_blocks": len(blocks),
        "density": n_stitch / area,
        "satin_frac": 100 * satin_n / tot,
        "fill_frac": 100 * fill_n / tot,
        "mixed_frac": 100 * mixed_n / tot,
        "satin_w_mm": float(np.median(satin_w)) if satin_w else None,
        "fill_seg_mm": float(np.median(fill_seg)) if fill_seg else None,
        "stitch_len_mm": float(np.median(all_seg)) if all_seg else None,
        "trim_rate": n_trim / max(n_stitch, 1),
        "frag": (n_trim + n_jump) / max(n_stitch, 1),
    }


def aggregate(rows: list[dict]) -> dict:
    """Aggregate per-file feature dicts into a category profile (median + p25/p75 per feature)."""
    prof: dict = {"n_files": len(rows)}
    for k in FEATURES:
        vals = [r[k] for r in rows if r.get(k) is not None]
        if not vals:
            prof[k] = None
            continue
        v = np.asarray(vals, float)
        prof[k] = {
            "med": round(float(np.median(v)), 3),
            "p25": round(float(np.percentile(v, 25)), 3),
            "p75": round(float(np.percentile(v, 75)), 3),
            "n": len(vals),
        }
    return prof


def load_profiles() -> dict:
    """Load the committed per-category profiles, or {} if absent."""
    try:
        return json.loads(PROFILES_PATH.read_text())
    except Exception:
        return {}


def _feat_vec(feat: dict, profiles: dict) -> np.ndarray | None:
    """Normalised feature vector for nearest-category matching (uses features every
    profile has: geometry + object mix, scaled by each feature's cross-category spread)."""
    keys = ("satin_frac", "fill_frac", "n_colors", "density", "longest_mm", "stitch_len_mm")
    ref = [p for p in profiles.values() if p.get("n_files")]
    if not ref:
        return None
    out = []
    for k in keys:
        meds = [p[k]["med"] for p in ref if p.get(k)]
        if not meds or feat.get(k) is None:
            out.append(0.0)
            continue
        spread = (max(meds) - min(meds)) or 1.0
        out.append(feat[k] / spread)
    return np.asarray(out, float)


def nearest_category(feat: dict, profiles: dict) -> str | None:
    """The category whose median fingerprint is closest to this design (fallback when the
    caller didn't declare a category). Excludes categories with no ground-truth files."""
    fv = _feat_vec(feat, profiles)
    if fv is None:
        return None
    best, bestd = None, float("inf")
    for cat, p in profiles.items():
        if not p.get("n_files"):
            continue
        pv = _feat_vec({k: (p[k]["med"] if p.get(k) else None) for k in FEATURES}, profiles)
        if pv is None:
            continue
        d = float(np.linalg.norm(fv - pv))
        if d < bestd:
            best, bestd = cat, d
    return best


def drift_check(feat: dict, profile: dict) -> list[dict]:
    """Compare a design's features to a category profile's p25–p75 bands. Returns a list of
    {feature, value, lo, hi, ok} for the production-style signals — `ok=False` means drift."""
    out = []
    for k in _DRIFT_KEYS:
        band = profile.get(k)
        val = feat.get(k)
        if not band or val is None:
            continue
        lo, hi = band["p25"], band["p75"]
        out.append({"feature": k, "value": round(float(val), 2),
                    "lo": lo, "hi": hi, "ok": lo <= val <= hi})
    return out
