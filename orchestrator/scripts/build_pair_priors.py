#!/usr/bin/env python3
"""Aggregate the per-object pair labels into per-category digitizing PRIORS.

The (SVG, VP3) pairs yield object-level ground truth (`<cat>/pairs/<design>/
<design>_measures.json`: per-object mm width, density, row spacing, satin-vs-tatami
verdict). This script rolls ALL of a category's pairs up into `data/pair_priors.json`,
which step 5 reads to TUNE its numbers (satin ceiling, vwidth clamps, border width) —
so every new pair the user drops automatically moves the digitizing decisions, with no
code change. Structure decisions (large regions = tatami, etc.) are never affected.

    .venv/bin/python orchestrator/scripts/build_pair_priors.py   # rebuild + print

Per category:
  satin_w_mm       p10/med/p90 of satin-verdict object widths (fills measured by EDT;
                   the band real production satin lives in)
  crossover_mm     the measured satin/fill width boundary: midpoint between the widest
                   satin-verdict widths (p90) and the narrowest fill-verdict widths
                   (p10). When they overlap (they usually do), the midpoint of the two
                   estimates; satin-only categories fall back to satin p90.
  fill_density / row_spacing_mm   medians over fill-verdict objects
  outline_to_fill  outline-family : fill-family object count ratio (borders-per-fill)
  n_pairs / n_objects             trust gates (n_pairs >= 1 activates the prior)

Run automatically by ingest_pairs.py after each ingest. Idempotent."""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from wilcom_pipeline.fingerprint import CATEGORIES  # noqa: E402
from wilcom_pipeline.priors import PRIORS_PATH  # noqa: E402


def _pct(vals: list[float], q: float) -> float | None:
    return round(float(np.percentile(np.asarray(vals, float), q)), 3) if vals else None


def aggregate_measures(measure_dicts: list[dict]) -> dict | None:
    """Roll a category's _measures.json dicts into one prior record. None if empty."""
    satin_w: list[float] = []      # widths of satin-verdict objects
    fill_w: list[float] = []       # widths of fill-verdict objects
    fill_density: list[float] = []
    row_spacing: list[float] = []
    n_outline = n_fill = 0
    n_objects = 0
    for md in measure_dicts:
        for o in md.get("objects", []):
            if o.get("outlier"):
                continue
            n_objects += 1
            if o["family"] == "outline":
                n_outline += 1
            else:
                n_fill += 1
            kind = o.get("stitch_kind")
            w = o.get("width_mm")
            if kind == "satin":
                if w is not None:
                    satin_w.append(float(w))
                elif o.get("satin_w_mm") is not None:
                    satin_w.append(float(o["satin_w_mm"]))
            elif kind == "fill" and w is not None:
                fill_w.append(float(w))
            if kind == "fill":
                if o.get("density_st_mm2") is not None:
                    fill_density.append(float(o["density_st_mm2"]))
                if o.get("row_spacing_mm") is not None:
                    row_spacing.append(float(o["row_spacing_mm"]))
    if not n_objects:
        return None

    # The measured satin/fill width boundary. Production bands overlap, so take the
    # midpoint of "where wide satin ends" (p90) and "where narrow fills begin" (p10);
    # a category with no fill-verdict widths uses the satin p90 alone.
    satin_hi = _pct(satin_w, 90)
    fill_lo = _pct(fill_w, 10)
    if satin_hi is not None and fill_lo is not None:
        crossover = round((satin_hi + fill_lo) / 2, 3)
    else:
        crossover = satin_hi if satin_hi is not None else None

    return {
        "n_pairs": len(measure_dicts),
        "n_objects": n_objects,
        "satin_w_mm": {"p10": _pct(satin_w, 10), "med": _pct(satin_w, 50),
                       "p90": satin_hi, "n": len(satin_w)},
        "crossover_mm": crossover,
        "fill_density_st_mm2": _pct(fill_density, 50),
        "row_spacing_mm": _pct(row_spacing, 50),
        "outline_to_fill": round(n_outline / max(n_fill, 1), 3),
    }


def build() -> dict:
    priors: dict = {}
    for cat in CATEGORIES:
        mds = []
        for path in sorted(glob.glob(str(REPO / cat / "pairs" / "*" / "*_measures.json"))):
            try:
                mds.append(json.loads(Path(path).read_text()))
            except Exception:
                print(f"! skipping unreadable {path}")
        rec = aggregate_measures(mds) if mds else None
        if rec:
            priors[cat] = rec
    return priors


def main() -> int:
    priors = build()
    PRIORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRIORS_PATH.write_text(json.dumps(priors, indent=1))
    print(f"wrote {PRIORS_PATH.relative_to(REPO)}\n")
    print(f"{'category':<14} pairs objs  satinW(p10/med/p90)  crossover  o:f")
    for cat, p in priors.items():
        sw = p["satin_w_mm"]
        print(f"{cat:<14} {p['n_pairs']:>5} {p['n_objects']:>4}  "
              f"{sw['p10']}/{sw['med']}/{sw['p90']:<12} {str(p['crossover_mm']):>7}  "
              f"{p['outline_to_fill']}")
    if not priors:
        print("(no pairs found — priors file is empty; step 5 uses its constants)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
