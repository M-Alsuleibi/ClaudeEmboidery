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
    # A category whose fill-verdict objects are a rounding error (< 5% of verdicts) is
    # SATIN-ONLY production (arb trio: 1,523 satin / 27 fill votes, the 27 being
    # classifier residue on 46k all-satin stitches) — its "narrowest fills" are noise
    # and must not midpoint the crossover down. Use where wide satin actually ends.
    satin_only = (len(satin_w) + len(fill_w)) > 0 and (
        len(fill_w) / (len(satin_w) + len(fill_w)) < 0.05)
    if satin_only or fill_lo is None:
        crossover = satin_hi
    elif satin_hi is not None:
        crossover = round((satin_hi + fill_lo) / 2, 3)
    else:
        crossover = None

    return {
        "n_pairs": len(measure_dicts),
        "n_objects": n_objects,
        "satin_only": satin_only,
        "satin_w_mm": {"p10": _pct(satin_w, 10), "med": _pct(satin_w, 50),
                       "p90": satin_hi, "n": len(satin_w)},
        "crossover_mm": crossover,
        "fill_density_st_mm2": _pct(fill_density, 50),
        "row_spacing_mm": _pct(row_spacing, 50),
        "outline_to_fill": round(n_outline / max(n_fill, 1), 3),
    }


import re as _re


def _mm(v) -> float | None:
    """Parse an authored value like '0.65 mm', '6.20', 45 -> float, else None."""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = _re.match(r"\s*(-?\d+(?:\.\d+)?)", v)
        return float(m.group(1)) if m else None
    return None


def _norm(k: str) -> str:
    return k.lower().strip().rstrip(":")


def aggregate_props(props_dicts: list[dict]) -> dict | None:
    """Roll the AUTHORED Object Properties (transcribed from Wilcom screenshots —
    the trio's third element, `<design>_props.json`) into an `authored` block.
    These are the digitizer's chosen SETTINGS, not stitch-inferred estimates, so
    where both exist the authored value is the truer prior. Parsed tolerantly:
    screenshot entries are keyed by their active tab; enabled/disabled checkbox
    states are respected (a greyed default is never counted as a value)."""
    fill_spacing: list[float] = []
    fill_length: list[float] = []
    pull_comp_on: list[float] = []
    pc_states: list[bool] = []
    underlay_states: list[bool] = []
    trim_off_states: list[bool] = []
    n_objects = 0
    for pj in props_dicts:
        n_objects += len(pj.get("objects", []))
        for s in pj.get("screenshots", []):
            tab = _norm(str(s.get("active_tab", "")))
            settings = s.get("settings") or {}
            flat = {}

            def _walk(d, path=""):
                if isinstance(d, dict):
                    for k, v in d.items():
                        _walk(v, path + "/" + _norm(str(k)))
                else:
                    flat[path] = d

            _walk(settings)
            if tab == "fills":
                for p, v in flat.items():
                    if "underlay" in p:
                        continue
                    if p.endswith("/spacing") and (x := _mm(v)) is not None:
                        fill_spacing.append(x)
                    if p.endswith("/length") and "min" not in p and (x := _mm(v)) is not None:
                        fill_length.append(x)
            elif tab == "pull comp":
                enabled = None
                value = None
                for p, v in flat.items():
                    if "pull compensation" in p:
                        if p.endswith("/enabled") or p.endswith("/selected"):
                            enabled = bool(v)
                        elif (x := _mm(v)) is not None:
                            value = x
                if enabled is not None:
                    pc_states.append(enabled)
                    if enabled and value is not None:
                        pull_comp_on.append(value)
            elif tab == "underlay":
                for p, v in flat.items():
                    if "first underlay" in p and (p.endswith("/enabled") or p.endswith("/selected")):
                        underlay_states.append(bool(v))
            elif tab == "connectors":
                for p, v in flat.items():
                    if "trim after" in p and p.endswith("/radio_selection"):
                        trim_off_states.append(_norm(str(v)) == "off")
    if not (fill_spacing or fill_length or pc_states or underlay_states
            or trim_off_states):
        return None
    out: dict = {"n_designs": len(props_dicts), "n_objects": n_objects}
    if fill_spacing:
        out["fill_spacing_mm"] = {"med": _pct(fill_spacing, 50), "n": len(fill_spacing)}
    if fill_length:
        out["fill_length_mm"] = {"med": _pct(fill_length, 50), "n": len(fill_length)}
    if pc_states:
        out["pull_comp_disabled_frac"] = round(
            1.0 - sum(pc_states) / len(pc_states), 3)
    if pull_comp_on:
        out["pull_comp_mm"] = {"med": _pct(pull_comp_on, 50), "n": len(pull_comp_on)}
    if underlay_states:
        out["underlay_disabled_frac"] = round(
            1.0 - sum(underlay_states) / len(underlay_states), 3)
    if trim_off_states:
        out["trim_after_off_frac"] = round(
            sum(trim_off_states) / len(trim_off_states), 3)
    return out


def build() -> dict:
    priors: dict = {}
    for cat in CATEGORIES:
        mds, pds = [], []
        for path in sorted(glob.glob(str(REPO / cat / "pairs" / "*" / "*_measures.json"))):
            try:
                mds.append(json.loads(Path(path).read_text()))
            except Exception:
                print(f"! skipping unreadable {path}")
        for path in sorted(glob.glob(str(REPO / cat / "pairs" / "*" / "*_props.json"))):
            try:
                pds.append(json.loads(Path(path).read_text()))
            except Exception:
                print(f"! skipping unreadable {path}")
        rec = aggregate_measures(mds) if mds else None
        if rec:
            authored = aggregate_props(pds) if pds else None
            if authored:
                rec["authored"] = authored
                # authored vs inferred disagreement: the same physical quantity read
                # two ways — a big gap calibrates how much to trust inference on
                # screenshot-less pairs
                a_sp = (authored.get("fill_spacing_mm") or {}).get("med")
                m_sp = rec.get("row_spacing_mm")
                if a_sp and m_sp and abs(a_sp - m_sp) / max(a_sp, m_sp) > 0.25:
                    print(f"~ {cat}: authored fill spacing {a_sp}mm vs stitch-inferred "
                          f"row spacing {m_sp}mm (Δ{abs(a_sp - m_sp) / max(a_sp, m_sp):.0%})"
                          f" — trust the authored value; inference includes underlay/"
                          f"travel rows")
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
