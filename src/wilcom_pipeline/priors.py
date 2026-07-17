"""Pair-derived digitizing priors (data/pair_priors.json).

The production (SVG, VP3) pairs yield per-object labels; `orchestrator/scripts/
build_pair_priors.py` aggregates them per category, and step 5 reads them here to TUNE
its numbers — the measured satin/fill width crossover replaces the hand-chosen satin
ceiling, the satin width band drives the vwidth clamps, and the outline-object width
median sets the border width. A category with no pairs (n_pairs == 0 / no record) falls
back to the hand-calibrated constants, byte-identically. Priors only ever tune NUMBERS;
the structure rules (large regions = tatami, contour only as last resort, ...) stand.

Best-effort by design: a missing/corrupt priors file simply means "no priors".
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
PRIORS_PATH = _REPO_ROOT / "data" / "pair_priors.json"

# The ceiling substitution stays inside the regime the pipeline was validated for:
# 3mm (the conservative default) .. 9mm (the lettering/satin-lean maximum).
CEILING_MIN_MM = 3.0
CEILING_MAX_MM = 9.0


def load_priors() -> dict:
    """The whole priors file ({} when absent/corrupt — constants then apply)."""
    try:
        data = json.loads(PRIORS_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def category_prior(category: str | None) -> dict | None:
    """The prior record for a category, or None when there are no trusted pairs."""
    if not category:
        return None
    rec = load_priors().get(category)
    if not isinstance(rec, dict) or not rec.get("n_pairs"):
        return None
    return rec


def satin_ceiling_mm(category: str | None) -> tuple[float, int] | None:
    """(measured satin/fill crossover clamped to 3-9mm, n_pairs) or None.
    This is the pair-calibrated replacement for the hand-chosen satin ceiling.

    A SATIN-ONLY category (production digitizes zero fills — arabic per the arb trio)
    keeps satin however wide the stroke runs and Auto-Splits the long stitches, so its
    ceiling is the digitizer's own Auto-Split length (authored on the Fills tab,
    captured as `authored.fill_length_mm`; 7.00 mm on every transcribed design) rather
    than a width percentile, which under-sees the few wide columns."""
    rec = category_prior(category)
    if not rec or rec.get("crossover_mm") is None:
        return None
    c = float(rec["crossover_mm"])
    if rec.get("satin_only"):
        split = ((rec.get("authored") or {}).get("fill_length_mm") or {}).get("med")
        if split:
            c = max(c, float(split))
    return min(max(c, CEILING_MIN_MM), CEILING_MAX_MM), int(rec["n_pairs"])


def satin_width_band_mm(category: str | None) -> tuple[float, float] | None:
    """(p10, p90) of the category's measured satin widths — the vwidth clamp band."""
    rec = category_prior(category)
    band = (rec or {}).get("satin_w_mm") or {}
    lo, hi = band.get("p10"), band.get("p90")
    if lo is None or hi is None or not (0 < float(lo) <= float(hi)):
        return None
    return float(lo), float(hi)


def border_width_mm(category: str | None) -> float | None:
    """The measured satin width median — what production sews its outline objects at."""
    rec = category_prior(category)
    med = ((rec or {}).get("satin_w_mm") or {}).get("med")
    return float(med) if med else None


def trim_after_off(category: str | None) -> bool:
    """True when the category's AUTHORED connector settings say "Trim after: Off" —
    production sews the whole colour continuously on untrimmed jump/run connectors
    (the arb trio: 1,618 objects, 46k stitches, 2 trims). Step 5's travel planner then
    drops trims by travel length alone, without requiring the travel to be covered."""
    rec = category_prior(category)
    frac = ((rec or {}).get("authored") or {}).get("trim_after_off_frac")
    return frac is not None and float(frac) >= 0.5


def cross_stitch_pitch_mm(category: str | None) -> float | None:
    """The measured cross-stitch cell pitch for a counted-cross-stitch category
    (tatreez): the register pass measures each little cross arm as a "satin" width, so
    the satin-width median IS the grid pitch (tatreez ≈ 2.1 mm). None with no pairs."""
    return border_width_mm(category)


def sketch_row_spacing_mm(category: str | None) -> float | None:
    """The measured scribble row spacing for a sketch-stitch category (animals): the
    register pass measures the spacing between a scribble object's parallel strokes as
    its row_spacing (animals ≈ 0.98 mm). None with no pairs."""
    rec = category_prior(category)
    v = (rec or {}).get("row_spacing_mm")
    return float(v) if v else None
