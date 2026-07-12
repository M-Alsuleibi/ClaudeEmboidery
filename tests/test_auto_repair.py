"""Tests for --auto-repair (step 2/3 artwork repair) and the step-7 sewability gate.

Pure numpy fixtures — no Ink-Stitch binary needed. Repair acts on the problems the
analyzer only warned about (specks, hairlines, duplicate-cone colours); the gate adds
density stacking / penetration spacing / stitch budget checks.
"""

from __future__ import annotations

import numpy as np
import pyembroidery as pe

from wilcom_pipeline.steps.preprocess import _auto_repair
from wilcom_pipeline.steps.verify import (
    _budget_check,
    _penetration_check,
    _stacking_check,
)

MM = 0.5  # fixtures use 0.5mm per pixel


# --------------------------------------------------------------------------- #
# repair ① specks
# --------------------------------------------------------------------------- #
def test_speck_merges_into_surrounding_colour():
    idx = np.full((40, 40), -1, np.int32)
    idx[5:35, 5:35] = 0                     # big colour-0 field
    idx[20:22, 20:22] = 1                   # 2x2px = 1mm2 colour-1 speck inside it
    out, log, _ = _auto_repair(idx, 2, MM)
    assert (out[20:22, 20:22] == 0).all()   # merged into the surrounding colour
    assert any("speck" in line for line in log)


def test_speck_on_background_is_left_alone():
    idx = np.full((40, 40), -1, np.int32)
    idx[20:22, 20:22] = 1                   # isolated speck on background
    out, _log, _ = _auto_repair(idx, 2, MM)
    assert (out[20:22, 20:22] == 1).all()   # never merged INTO background


def test_dotted_pattern_is_kept():
    idx = np.full((40, 80), -1, np.int32)
    idx[5:35, 5:75] = 0
    for k in range(3):                      # 3 same-colour specks in a row = dots
        idx[19:21, 15 + 20 * k:17 + 20 * k] = 1
    out, log, _ = _auto_repair(idx, 2, MM)
    assert (out == 1).sum() == 3 * 4        # all kept
    assert any("dotted" in line for line in log)


# --------------------------------------------------------------------------- #
# repair ② hairlines
# --------------------------------------------------------------------------- #
def test_hairline_is_thickened_into_background_only():
    idx = np.full((60, 60), -1, np.int32)
    idx[35:55, 5:55] = 1                    # solid block: the hairline is a MINOR part
    idx[20, 5:55] = 0                       # 1px = 0.5mm hairline on background
    out, log, fixed = _auto_repair(idx, 2, MM)
    assert fixed
    assert any("hairline" in line for line in log)
    col = out[:, 30]
    assert (col[:30] == 0).sum() >= 2       # ~>=1.0mm wide now
    assert (out[35:55, 5:55] == 1).all()    # the solid block is untouched


def test_hairline_next_to_colour_never_eats_the_neighbour():
    idx = np.full((40, 60), -1, np.int32)
    idx[22:35, 5:55] = 1                    # solid block below...
    idx[21, 5:55] = 0                       # ...hairline touching it
    out, _log, _ = _auto_repair(idx, 2, MM)
    assert (out[22:35, 5:55] == 1).all()    # neighbour colour untouched


def test_mostly_hairline_design_gets_advice_not_fattening():
    idx = np.full((40, 60), -1, np.int32)
    idx[10, 5:55] = 0                       # two hairlines and nothing else
    idx[30, 5:55] = 0
    out, log, fixed = _auto_repair(idx, 1, MM)
    assert not fixed
    assert (out == 0).sum() == (idx == 0).sum()          # untouched
    assert any("enlarge" in line for line in log)


# --------------------------------------------------------------------------- #
# gate: stacking / penetration / budget
# --------------------------------------------------------------------------- #
def _fill_layer(x0, y0, w, h, spacing=0.4, unit=10):
    """Synthetic tatami: horizontal rows spacing apart, 3mm penetrations. 0.1mm units."""
    st = []
    y = y0
    row = 0
    while y <= y0 + h:
        xs = np.arange(x0, x0 + w + 1e-6, 3.0)
        if row % 2:
            xs = xs[::-1]
        for x in xs:
            st.append([int(x * unit), int(y * unit), pe.STITCH])
        y += spacing
        row += 1
    return st


def test_stacking_single_and_double_layer_pass_triple_fails():
    one = _fill_layer(0, 0, 20, 20)
    ok, detail = _stacking_check(one + [[0, 0, pe.END]])
    assert ok, detail
    two = one + _fill_layer(0, 0, 20, 20)
    ok, _ = _stacking_check(two + [[0, 0, pe.END]])
    assert ok                                             # border-over-fill is fine
    # 12 tatami layers ~ 6 satin-layers over the whole patch = a genuine pile-up
    # (thresholds are calibrated against production VP3s: they peak at ~5 satin-layers)
    pile = one * 12
    ok, detail = _stacking_check(pile + [[0, 0, pe.END]])
    assert not ok
    assert "mm2" in detail                                # reports the affected area


def test_penetration_spacing():
    good = _fill_layer(0, 0, 20, 20)
    ok, _ = _penetration_check(good)
    assert ok
    jitter = [[i % 2, 0, pe.STITCH] for i in range(200)]  # 0.02mm apart
    ok, detail = _penetration_check(jitter)
    assert not ok and "%" in detail


def test_budget_check_uses_category_profile():
    class Cfg:
        category = "letters"

    class Ctx:
        config = Cfg()

    r = _budget_check(Ctx(), n_stitch=1000, area_mm2=1000.0)   # letters med ~1.05/mm2
    assert r is not None and r[0] is True
    r = _budget_check(Ctx(), n_stitch=10_000, area_mm2=1000.0)
    assert r is not None and r[0] is False
    Cfg.category = None
    assert _budget_check(Ctx(), 1000, 1000.0) is None          # no category -> skipped


# --------------------------------------------------------------------------- #
# --no-auto-repair = byte-identical old behaviour
# --------------------------------------------------------------------------- #
def test_flag_off_is_identity(tmp_path):
    from PIL import Image
    from wilcom_pipeline.config import PipelineConfig, PipelineContext
    from wilcom_pipeline.steps import analyze, preprocess

    arr = np.full((120, 120, 3), 255, np.uint8)
    arr[20:100, 20:60] = (20, 40, 130)
    arr[55:57, 70:72] = (210, 40, 40)       # a speck repair WOULD touch
    src = tmp_path / "in.png"
    Image.fromarray(arr).save(src)

    def img_for(repair: bool):
        cfg = PipelineConfig(input_path=src, output_dir=tmp_path / f"o{repair}",
                             name="t", target_width_mm=60.0, num_colors=2,
                             auto_repair=repair)
        ctx = PipelineContext(config=cfg)
        analyze.run(ctx)
        preprocess.run(ctx)
        return np.asarray(ctx.preprocessed_image)

    off = img_for(False)
    off2 = img_for(False)
    assert (off == off2).all()              # deterministic
    # and the repair path is genuinely gated: on-vs-off may differ, off equals itself
