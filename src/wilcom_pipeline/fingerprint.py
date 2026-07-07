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

Auto-Split caveat (Reference Manual p1197, see wilcom-manual-rules.md): a WIDE satin column
whose long rail-to-rail stitch is broken into co-linear sub-stitches ("Auto Split") has its
per-vertex reversal fraction DILUTED below 35%, so the rule above miscounts it as tatami --
Wilcom's own machine-file reader hits the same trap unless "recognize auto splits" is on. We
recover it geometrically in `_is_split_satin`: a narrow oscillating ribbon (many reversals,
each a short rail-to-rail crossing <= the ~7mm satin ceiling) is satin regardless of splits.
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


_REV_TURN_DEG = 120.0       # a vertex "reverses" when the path turns more than this
_SATIN_REV_PCT = 35.0       # >this reversal fraction => satin outright (unsplit column)
_FILL_REV_PCT = 15.0        # <this => fill; between the two => mixed
_SPLIT_MIN_REV = 6          # a real (split) satin column oscillates at least this many times
_SPLIT_CROSS_MAX_MM = 8.0   # rail-to-rail crossing <= ~7mm satin ceiling (+margin) => narrow ribbon


def _is_split_satin(seg: np.ndarray, is_rev: np.ndarray) -> bool:
    """True when a block is an Auto-Split satin column that the reversal-fraction rule would
    otherwise miscount as tatami (Reference Manual p1197). Split-invariant: the co-linear
    split points are NOT reversals, so the reversals still mark the two rails. A satin column
    then shows many reversals whose along-path spacing (rail-to-rail crossing distance) is
    small and bounded by the satin ceiling; a genuine tatami fill has reversals a full row
    apart, so its crossing distance is large."""
    rev_vertices = np.nonzero(is_rev)[0] + 1              # vertex indices carrying a reversal
    if rev_vertices.size < _SPLIT_MIN_REV:
        return False
    pos = np.concatenate(([0.0], np.cumsum(seg)))         # path length (mm) at each vertex
    cross = np.diff(pos[rev_vertices])                    # rail-to-rail crossing distances
    cross = cross[cross > 0.05]
    if cross.size < _SPLIT_MIN_REV - 1:
        return False
    return float(np.median(cross)) <= _SPLIT_CROSS_MAX_MM


def _block_kind(pts: list[tuple[float, float]]):
    """(kind, median_segment_mm, n_points) for one colour block, or None if too short.
    kind: 'satin' (>35% vertices reverse, OR an Auto-Split narrow ribbon), 'fill' (<15%),
    else 'mixed'."""
    p = np.asarray(pts, float)
    if len(p) < 3:
        return None
    d = np.diff(p, axis=0)
    seg = np.hypot(d[:, 0], d[:, 1]) * _UNIT_MM
    a = np.arctan2(d[:, 1], d[:, 0])
    da = (np.diff(a) + np.pi) % (2 * np.pi) - np.pi
    is_rev = np.abs(np.degrees(da)) > _REV_TURN_DEG
    rev = float(np.mean(is_rev) * 100)
    valid = seg[seg > 0.05]
    med = float(np.median(valid)) if valid.size else 0.0
    if rev > _SATIN_REV_PCT or _is_split_satin(seg, is_rev):
        kind = "satin"
    elif rev < _FILL_REV_PCT:
        kind = "fill"
    else:
        kind = "mixed"
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


_SATIN_DOMINANT_MIN = 60.0  # median satin% above which a category's truth is "satin-dominant"


def category_satin_dominant(category: str | None) -> bool:
    """True when the ground-truth fingerprint for this category is satin-dominant (median
    satin% >= _SATIN_DOMINANT_MIN) — letters/arabic/simple-shapes/decoration/numbers are,
    3D is not, anime has no data. Step 5 uses this to lean the tiering toward satin so the
    output moves toward the truth's ~100% satin instead of defaulting to tatami fills."""
    if not category:
        return False
    prof = load_profiles().get(category) or {}
    band = prof.get("satin_frac")
    return bool(band and band.get("med", 0) >= _SATIN_DOMINANT_MIN)


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
