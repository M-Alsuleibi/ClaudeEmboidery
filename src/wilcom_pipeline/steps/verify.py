"""Step 7 - Self-verify (the gate).

Sanity-check the result before it goes to Phase B (Wilcom). Records
ctx.verification = {"passed": bool, "checks": [...], "metrics": {...}}.

Checks (v1, thresholds documented for calibration against the reference set):
  - nonzero stitches
  - every colour actually sewed (a zero-stitch block = a region eaten by the
    background drop, or a fill that failed) -> hard fail
  - colour changes == colours - 1                                 -> hard fail
  - fill density within a plausible band                          -> warn
  - not over-fragmented (trims+jumps per stitch)                  -> warn
Plus carry-forward of analyze's quality flags (smallest feature, contrast).

A "fail" should trigger a Phase A re-run with adjusted flags — that's the
caller's job; this step only judges and reports.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pyembroidery as pe

from .. import fingerprint
from ..config import PipelineContext

_STITCH = pe.STITCH & 0xFF
_JUMP = pe.JUMP & 0xFF
_TRIM = pe.TRIM & 0xFF
_COLOR_CHANGE = pe.COLOR_CHANGE & 0xFF

_MIN_DENSITY = 0.3    # stitches/mm^2 below this: suspiciously sparse / missing fill
_MAX_DENSITY = 15.0   # above this: over-dense
_MAX_FRAG = 0.05      # (trims+jumps)/stitches above this: over-fragmented

# Sewability checks (needed now that borders/underlap deliberately OVERLAP objects —
# global density can look fine while one spot stacks many layers of thread).
# CALIBRATED against the production ground truth (pink-goku/letters/decoration/arabic
# VP3s): production peaks at <=5.2 SATIN-layers with <=0.8mm2 above 5 layers, while
# genuine pile-ups (our scrap+satin+border stacks) run 7-15 layers over 20-230mm2.
_STACK_RES_MM = 0.5       # raster cell size for the local thread-length map
_STACK_LAYER_MM = 5.0     # thread one SATIN layer deposits per mm^2 (0.4mm zigzag pitch)
_STACK_MAX_LAYERS = 5.0   # beyond ~5 satin-layers = a real pile-up...
_STACK_MAX_MM2 = 10.0     # ...warn when it covers more than this much area
_PENETRATION_MM = 0.3     # consecutive penetrations closer than this risk cutting the fabric
_PENETRATION_MAX_FRAC = 0.05
_BUDGET_FACTOR = 1.8      # actual stitches beyond this x the category expectation = bloat


def run(ctx: PipelineContext) -> None:
    if ctx.stitch_pattern is None:
        raise RuntimeError("verify requires ctx.stitch_pattern; run stitches first.")
    pattern = ctx.stitch_pattern

    blocks = _stitches_per_colour_block(pattern.stitches)
    cmds = Counter(c & 0xFF for _, _, c in pattern.stitches)
    n_stitch = cmds.get(_STITCH, 0)
    n_color = len(pattern.threadlist)
    n_changes = cmds.get(_COLOR_CHANGE, 0)

    xs = [s[0] for s in pattern.stitches]
    ys = [s[1] for s in pattern.stitches]
    w_mm = (max(xs) - min(xs)) / 10 if xs else 0.0
    h_mm = (max(ys) - min(ys)) / 10 if ys else 0.0
    area = max(w_mm * h_mm, 1e-6)
    density = n_stitch / area
    frag = (cmds.get(_TRIM, 0) + cmds.get(_JUMP, 0)) / max(n_stitch, 1)

    checks: list[dict] = []

    checks.append(_chk("nonzero_stitches", n_stitch > 0, "error",
                       f"{n_stitch} stitches"))
    empty = [i + 1 for i, c in enumerate(blocks) if c == 0]
    checks.append(_chk("all_colours_sewed", not empty and len(blocks) == n_color, "error",
                       "every colour has stitches" if not empty
                       else f"colour block(s) {empty} have no stitches"))
    checks.append(_chk("colour_changes_consistent", n_changes == max(n_color - 1, 0), "error",
                       f"{n_changes} change(s) for {n_color} colour(s)"))
    checks.append(_chk("density_in_band", _MIN_DENSITY <= density <= _MAX_DENSITY, "warn",
                       f"{density:.2f} stitches/mm^2 (band {_MIN_DENSITY}-{_MAX_DENSITY})"))
    checks.append(_chk("not_fragmented", frag <= _MAX_FRAG, "warn",
                       f"{frag*100:.2f}% trims+jumps per stitch (max {_MAX_FRAG*100:.0f}%)"))

    # Sewability: local density STACKING (overlapping objects piling >3 layers in one
    # spot), needle-cut risk (consecutive penetrations too close), and a stitch budget
    # against the category's ground-truth density. All warn-level.
    stack_ok, stack_detail = _stacking_check(pattern.stitches)
    checks.append(_chk("density_stacking", stack_ok, "warn", stack_detail))
    pen_ok, pen_detail = _penetration_check(pattern.stitches)
    checks.append(_chk("penetration_spacing", pen_ok, "warn", pen_detail))
    budget = _budget_check(ctx, n_stitch, area)
    if budget is not None:
        checks.append(_chk("stitch_budget", budget[0], "warn", budget[1]))

    # Production-fit: score the run against the ground-truth fingerprint for its category
    # (data/category_profiles.json). A `warn` (never fails the gate) — production-style
    # guidance, e.g. "the truth for arabic is 100% satin but this is 0%; density too sparse".
    fit = _production_fit(ctx, pattern)
    if fit is not None:
        checks.append(_chk("production_fit", fit["passed"], "warn", fit["detail"]))

    # Carry forward analyze's quality flags as informational notes.
    notes = list(ctx.analysis.get("warnings", []))

    passed = all(c["passed"] for c in checks if c["severity"] == "error")
    ctx.verification = {
        "passed": passed,
        "checks": checks,
        "notes": notes,
        "production_fit": fit,
        "metrics": {
            "stitches": n_stitch,
            "colours": n_color,
            "trims": cmds.get(_TRIM, 0),
            "jumps": cmds.get(_JUMP, 0),
            "extent_mm": (round(w_mm, 1), round(h_mm, 1)),
            "density_per_mm2": round(density, 2),
            "fragmentation": round(frag, 4),
        },
    }
    _print_report(ctx.verification)


# --------------------------------------------------------------------------- #
# sewability checks
# --------------------------------------------------------------------------- #
def _stacking_check(stitches) -> tuple[bool, str]:
    """Local thread-length map: rasterize the stitch segments at _STACK_RES_MM and flag
    cells holding more than _STACK_MAX_LAYERS satin-layers of thread. A border over a
    fill is deliberate production layering (measures ~1-3); a many-layer pile-up cuts
    fabric and breaks needles. Reports the worst spot + affected area."""
    pts = np.asarray([(x / 10.0, y / 10.0) for x, y, c in stitches
                      if (c & 0xFF) == _STITCH])
    if len(pts) < 2:
        return True, "no stitches to map"
    x0, y0 = pts.min(0)
    res = _STACK_RES_MM
    W = int((pts[:, 0].max() - x0) / res) + 2
    H = int((pts[:, 1].max() - y0) / res) + 2
    if W * H > 4_000_000:
        return True, "design too large to map (skipped)"
    length = np.zeros((H, W))
    # deposit each segment's length into the cells it crosses (~4 samples per cell)
    seg_a, seg_b = pts[:-1], pts[1:]
    seg_len = np.hypot(*(seg_b - seg_a).T)
    step = res / 4.0
    for a, b, L in zip(seg_a, seg_b, seg_len):
        if L <= 0 or L > 12.0:      # jump-like gap between pieces, not thread on top
            continue
        n = max(int(L / step), 1)
        ts = (np.arange(n) + 0.5) / n
        sx = ((a[0] + ts * (b[0] - a[0]) - x0) / res).astype(int)
        sy = ((a[1] + ts * (b[1] - a[1]) - y0) / res).astype(int)
        np.add.at(length, (sy, sx), L / n)
    # De-alias: a 0.4mm-row layer lands 1 or 2 rows per 0.5mm cell (up to ~2.2x the
    # norm in single cells) — average over a ~1.5mm neighbourhood before thresholding
    # so the check measures real layering, not raster phase.
    from scipy import ndimage
    length = ndimage.uniform_filter(length, size=3)
    layer_per_cell = _STACK_LAYER_MM * res * res     # one layer's thread per cell
    hot = length > _STACK_MAX_LAYERS * layer_per_cell
    hot_mm2 = float(hot.sum()) * res * res
    worst = float(length.max()) / layer_per_cell
    if hot_mm2 <= _STACK_MAX_MM2:
        return True, (f"worst spot {worst:.1f} satin-layers; "
                      f"{hot_mm2:.1f}mm2 above {_STACK_MAX_LAYERS:g} layers "
                      f"(max {_STACK_MAX_MM2:g}mm2)")
    wy, wx = np.unravel_index(int(length.argmax()), length.shape)
    return False, (f"{hot_mm2:.1f}mm2 stacked above {_STACK_MAX_LAYERS:g} satin-layers "
                   f"(max {_STACK_MAX_MM2:g}mm2); worst {worst:.1f} layers at "
                   f"({x0 + wx * res:.0f},{y0 + wy * res:.0f})mm")


def _penetration_check(stitches) -> tuple[bool, str]:
    """Fraction of consecutive penetrations closer than _PENETRATION_MM — repeated
    near-identical needle drops perforate the fabric."""
    pts = np.asarray([(x / 10.0, y / 10.0) for x, y, c in stitches
                      if (c & 0xFF) == _STITCH])
    if len(pts) < 2:
        return True, "no stitches"
    d = np.hypot(*np.diff(pts, axis=0).T)
    frac = float((d < _PENETRATION_MM).mean())
    ok = frac <= _PENETRATION_MAX_FRAC
    return ok, (f"{frac * 100:.1f}% of penetrations closer than {_PENETRATION_MM}mm "
                f"(max {_PENETRATION_MAX_FRAC * 100:.0f}%)")


def _budget_check(ctx: PipelineContext, n_stitch: int, area_mm2: float):
    """Stitch budget: the ceiling is the densest the category's REFERENCE files ever
    sew (observed density hi + 10%) — a rebuild of the densest reference must never
    warn (the arb trio sews 0.67 st/mm2 while the arabic median is 0.42; median x1.8
    flagged stitch counts the trio itself declares correct). Profiles without the
    observed range fall back to median x _BUDGET_FACTOR. The tighter per-run signal
    stays the production_fit density band. None when no category/profile."""
    cat = ctx.config.category
    prof = fingerprint.load_profiles().get(cat or "", {})
    band = (prof.get("density") or {}) if prof.get("n_files") else {}
    hi, med = band.get("hi"), band.get("med")
    if hi:
        limit = float(hi) * 1.1 * area_mm2
        detail = (f"{n_stitch} stitches vs <= {limit:.0f} for {cat} "
                  f"(densest reference {float(hi):g} st/mm2 + 10%)")
    elif med:
        limit = _BUDGET_FACTOR * float(med) * area_mm2
        detail = (f"{n_stitch} stitches vs ~{float(med) * area_mm2:.0f} expected for "
                  f"{cat} (warn beyond {_BUDGET_FACTOR:g}x)")
    else:
        return None
    return n_stitch <= limit, detail


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _chk(name: str, passed: bool, severity: str, detail: str) -> dict:
    return {"name": name, "passed": bool(passed), "severity": severity, "detail": detail}


def _production_fit(ctx: PipelineContext, pattern) -> dict | None:
    """Score this run against the ground-truth fingerprint for its category. Returns
    {passed, category, declared, drift, detail} or None if no profiles are available.
    The category is `ctx.config.category` if declared, else the nearest by feature match."""
    profiles = fingerprint.load_profiles()
    if not profiles:
        return None
    feat = fingerprint.features_from_pattern(pattern.stitches, pattern.threadlist)
    declared = ctx.config.category
    cat = declared or fingerprint.nearest_category(feat, profiles)
    prof = profiles.get(cat) if cat else None
    if not prof or not prof.get("n_files"):
        return None
    drift = fingerprint.drift_check(feat, prof)
    src = "declared" if declared else "nearest"
    parts = [f"{d['feature']}={d['value']:g} [{d['lo']:g}-{d['hi']:g}] "
             f"{'ok' if d['ok'] else 'DRIFT'}" for d in drift]
    detail = f"vs {cat} ({src}, n={prof['n_files']}): " + "; ".join(parts)
    return {
        "passed": all(d["ok"] for d in drift),
        "category": cat, "declared": bool(declared), "drift": drift, "detail": detail,
    }


def _stitches_per_colour_block(stitches) -> list[int]:
    """STITCH counts split at each COLOR_CHANGE (one entry per colour block)."""
    blocks: list[int] = []
    count = 0
    for _, _, cmd in stitches:
        c = cmd & 0xFF
        if c == _STITCH:
            count += 1
        elif c == _COLOR_CHANGE:
            blocks.append(count)
            count = 0
    blocks.append(count)
    return blocks


def _print_report(v: dict) -> None:
    verdict = "PASS" if v["passed"] else "FAIL"
    print(f"      gate: {verdict}")
    for c in v["checks"]:
        mark = "ok " if c["passed"] else ("!! " if c["severity"] == "error" else "~  ")
        print(f"        [{mark}] {c['name']}: {c['detail']}")
    for n in v["notes"]:
        print(f"        (note) {n}")
