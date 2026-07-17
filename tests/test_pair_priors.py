"""Tests for pair-derived priors: aggregation (build_pair_priors), the consumer
(wilcom_pipeline.priors), and the step-5 ceiling substitution.

Pure JSON/numpy — no binary needed. Priors TUNE step 5's numbers (satin ceiling,
vwidth clamps, border width) from the pairs' per-object labels; a category without
pairs falls back to the hand-calibrated constants byte-identically, and a corrupt
priors file means "no priors", never a crash.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from wilcom_pipeline import priors
from wilcom_pipeline.steps.stitches import (
    _LETTERING_SATIN_MAX_WIDTH_MM,
    _SATIN_DOMINANT_CEILING_MM,
    _SATIN_MAX_WIDTH_MM,
    _outline_border_w_mm,
    _satin_ceiling,
)

_REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_pair_priors", _REPO / "orchestrator" / "scripts" / "build_pair_priors.py")
bpp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bpp)


def _measures(objects):
    return {"design": "t", "objects": objects}


def _obj(family="fill", kind=None, w=None, outlier=False, **kw):
    o = {"i": 0, "family": family, "outlier": outlier}
    if kind:
        o["stitch_kind"] = kind
    if w is not None:
        o["width_mm"] = w
    o.update(kw)
    return o


# --------------------------------------------------------------------------- #
# aggregation
# --------------------------------------------------------------------------- #
def test_aggregation_bands_and_crossover():
    md = _measures(
        [_obj(kind="satin", w=w) for w in (1.0, 2.0, 2.0, 3.0, 4.0)]
        + [_obj(kind="fill", w=w, density_st_mm2=2.0, row_spacing_mm=0.5)
           for w in (3.0, 5.0, 8.0)]
        + [_obj(family="outline", kind="satin", satin_w_mm=2.5)] * 4
    )
    rec = bpp.aggregate_measures([md])
    assert rec["n_pairs"] == 1
    assert rec["n_objects"] == 12
    sw = rec["satin_w_mm"]
    assert sw["n"] == 9                      # 5 widths + 4 satin_w_mm fallbacks
    assert sw["p10"] < sw["med"] < sw["p90"]
    # crossover = midpoint(satin p90, fill p10)
    assert abs(rec["crossover_mm"] - (sw["p90"] + 3.2) / 2) < 0.15
    assert rec["fill_density_st_mm2"] == 2.0
    assert rec["row_spacing_mm"] == 0.5
    assert rec["outline_to_fill"] == round(4 / 8, 3)


def test_aggregation_skips_outliers_and_satin_only_crossover():
    md = _measures(
        [_obj(kind="satin", w=2.0), _obj(kind="satin", w=3.0),
         _obj(kind="satin", w=99.0, outlier=True)]     # flagged path never counted
    )
    rec = bpp.aggregate_measures([md])
    assert rec["n_objects"] == 2
    assert rec["satin_w_mm"]["p90"] < 4.0
    # no fill-verdict widths -> crossover falls back to the satin p90
    assert rec["crossover_mm"] == rec["satin_w_mm"]["p90"]


def test_aggregation_empty_is_none():
    assert bpp.aggregate_measures([_measures([])]) is None


# --------------------------------------------------------------------------- #
# consumer + trust gate + corrupt-file fallback
# --------------------------------------------------------------------------- #
def _write_priors(tmp_path, monkeypatch, payload):
    f = tmp_path / "pair_priors.json"
    f.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    monkeypatch.setattr(priors, "PRIORS_PATH", f)
    return f


def test_consumer_reads_and_clamps(tmp_path, monkeypatch):
    _write_priors(tmp_path, monkeypatch, {
        "anime": {"n_pairs": 2, "crossover_mm": 2.2,
                  "satin_w_mm": {"p10": 1.1, "med": 2.2, "p90": 4.0}},
        "letters": {"n_pairs": 1, "crossover_mm": 12.0,
                    "satin_w_mm": {"p10": 2.0, "med": 2.4, "p90": 3.0}},
    })
    assert priors.satin_ceiling_mm("anime") == (3.0, 2)      # clamped UP to 3
    assert priors.satin_ceiling_mm("letters") == (9.0, 1)    # clamped DOWN to 9
    assert priors.satin_width_band_mm("anime") == (1.1, 4.0)
    assert priors.border_width_mm("anime") == 2.2
    assert priors.satin_ceiling_mm("arabic") is None         # no record
    assert priors.satin_ceiling_mm(None) is None


def test_trust_gate_n_pairs_zero(tmp_path, monkeypatch):
    _write_priors(tmp_path, monkeypatch, {
        "anime": {"n_pairs": 0, "crossover_mm": 2.0,
                  "satin_w_mm": {"p10": 1, "med": 2, "p90": 3}}})
    assert priors.category_prior("anime") is None
    assert priors.satin_ceiling_mm("anime") is None


@pytest.mark.parametrize("payload", ["{corrupt", "[]", ""])
def test_corrupt_or_wrong_shape_priors_fall_back(tmp_path, monkeypatch, payload):
    _write_priors(tmp_path, monkeypatch, payload)
    assert priors.load_priors() == {}
    assert priors.satin_ceiling_mm("anime") is None


def test_missing_file_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(priors, "PRIORS_PATH", tmp_path / "nope.json")
    assert priors.load_priors() == {}


# --------------------------------------------------------------------------- #
# step-5 ceiling substitution
# --------------------------------------------------------------------------- #
def test_ceiling_uses_prior_and_regimes_win(tmp_path, monkeypatch):
    _write_priors(tmp_path, monkeypatch, {
        "anime": {"n_pairs": 1, "crossover_mm": 4.5,
                  "satin_w_mm": {"p10": 1.0, "med": 2.2, "p90": 4.0}}})
    # prior replaces the satin-dominant default...
    assert _satin_ceiling(False, False, True, "anime") == 4.5
    # ...but explicit user regimes always win
    assert _satin_ceiling(True, False, True, "anime") == _LETTERING_SATIN_MAX_WIDTH_MM
    assert _satin_ceiling(False, True, True, "anime") == _LETTERING_SATIN_MAX_WIDTH_MM
    # no-pair categories keep the constants (byte-identical path)
    assert _satin_ceiling(False, False, True, "letters") == _SATIN_DOMINANT_CEILING_MM
    assert _satin_ceiling(False, False, False, None) == _SATIN_MAX_WIDTH_MM


def test_border_width_prefers_prior(tmp_path, monkeypatch):
    _write_priors(tmp_path, monkeypatch, {
        "anime": {"n_pairs": 1, "crossover_mm": 3.0,
                  "satin_w_mm": {"p10": 1.0, "med": 2.7, "p90": 4.0}}})
    assert _outline_border_w_mm("anime") == 2.7             # prior med, inside clamp
    w = _outline_border_w_mm("letters")                     # no pairs -> profile med
    assert 1.5 <= w <= 3.0


# --------------------------------------------------------------------------- #
# the satin-only law (the arb trio): flag, authored spacing, ceiling precedence
# --------------------------------------------------------------------------- #
def _satin_only_record(**authored):
    rec = {"n_pairs": 8, "satin_only": True, "crossover_mm": 3.5,
           "satin_w_mm": {"p10": 0.8, "med": 1.75, "p90": 3.5},
           "authored": {"fill_length_mm": {"med": 7.0, "n": 15}}}
    rec["authored"].update(authored)
    return rec


def test_satin_only_flag_and_authored_spacing(tmp_path, monkeypatch):
    _write_priors(tmp_path, monkeypatch, {
        "arabic": _satin_only_record(
            satin_spacing_mm={"med": 0.42, "n": 10},
            satin_auto_spacing_mm={"med": 0.24, "n": 2}),
        "anime": {"n_pairs": 1, "crossover_mm": 2.4,
                  "satin_w_mm": {"p10": 1.0, "med": 1.5, "p90": 2.4}},
    })
    assert priors.satin_only("arabic") is True
    assert priors.satin_only("anime") is False       # record without the flag
    assert priors.satin_only("letters") is False     # no record at all
    # the auto-spacing displayed value (what production actually sews) outranks
    # the manual-spacing median; a category without authored spacing gets None
    assert priors.authored_satin_spacing_mm("arabic") == 0.24
    assert priors.authored_satin_spacing_mm("anime") is None


def test_satin_only_ceiling_is_auto_split_and_outranks_regimes(tmp_path, monkeypatch):
    _write_priors(tmp_path, monkeypatch, {"arabic": _satin_only_record()})
    # ceiling = the authored Auto-Split length (7.0) whatever the regime flags say:
    # the trio's authored settings define correct, not the 9mm lean/lettering blanket
    assert _satin_ceiling(False, False, True, "arabic") == 7.0
    assert _satin_ceiling(False, True, True, "arabic") == 7.0
    assert _satin_ceiling(True, False, True, "arabic") == 7.0


def test_aggregation_splits_satin_spacing_by_auto_state():
    props = {
        "screenshots": [
            # arb-style: Satin type, auto spacing ON, spacing greyed (auto owns it)
            {"active_tab": "Fills",
             "settings": {"Dropdown": "Satin",
                          "Stitch values": {"Spacing": "0.24 mm (greyed)"},
                          "Auto spacing": {"enabled": True,
                                           "displayed_value": {"Adjust": "90 %"}}}},
            # 7-style: everything greyed under displayed_value, auto CHECKED
            {"active_tab": "Fills",
             "settings": {"Dropdown": {"enabled": False, "displayed_value": "Satin"},
                          "Stitch values": {"Spacing": {"enabled": False,
                                                        "displayed_value": "0.24 mm"}},
                          "Auto spacing": {"enabled": False, "checked": True}}},
            # manual satin spacing
            {"active_tab": "Fills",
             "settings": {"Type": "Satin",
                          "Stitch values": {"Spacing": "0.40 mm"},
                          "Auto spacing": {"enabled": False}}},
            # tatami screenshot: its spacing must NOT land in either satin bucket
            {"active_tab": "Fills",
             "settings": {"Fill type": "Tatami",
                          "Stitch values": {"Spacing": "0.65 mm",
                                            "Length": "6.20 mm"}}},
        ],
    }
    out = bpp.aggregate_props([props])
    assert out["satin_auto_spacing_mm"] == {"med": 0.24, "n": 2}
    assert out["satin_spacing_mm"] == {"med": 0.4, "n": 1}
    assert out["fill_spacing_mm"]["n"] == 4          # informational: every spacing
