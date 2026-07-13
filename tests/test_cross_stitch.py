"""Tests for the counted cross-stitch primitive (steps/crossstitch.py + its config wiring).

Pure geometry + pyembroidery — no Ink-Stitch binary needed (that's the point of the
primitive: it builds the VP3 directly). Covers cell assignment, the per-cell X structure,
break-apart trims / colour changes, the no-stray-origin invariant, and the config flags.
"""

from __future__ import annotations

import types
from pathlib import Path

import numpy as np
import pyembroidery as pe
from PIL import Image

from wilcom_pipeline.config import PipelineConfig
from wilcom_pipeline.steps.crossstitch import (
    _cell_colours,
    build_cross_stitch_pattern,
)

_STITCH = pe.STITCH & 0xFF
_TRIM = pe.TRIM & 0xFF
_CC = pe.COLOR_CHANGE & 0xFF
_END = pe.END & 0xFF


def _ctx(arr: np.ndarray, palette, width_mm: float):
    """A minimal step-5 context: palette-quantised RGBA image + palette + thread_map."""
    return types.SimpleNamespace(
        preprocessed_image=Image.fromarray(arr, "RGBA"),
        palette=palette,
        thread_map=[{"thread_rgb": tuple(rgb)} for rgb in palette],
        analysis={"size_mm": {"width_mm": width_mm, "height_mm": width_mm * arr.shape[0] / arr.shape[1]}},
    )


def _block(h=40, w=40, boxes=()):
    arr = np.zeros((h, w, 4), np.uint8)
    for (y0, y1, x0, x1, rgb) in boxes:
        arr[y0:y1, x0:x1, :3] = rgb
        arr[y0:y1, x0:x1, 3] = 255
    return arr


def _cmd_counts(pat):
    out = {}
    for s in pat.stitches:
        out[s[2] & 0xFF] = out.get(s[2] & 0xFF, 0) + 1
    return out


# --------------------------------------------------------------------------- #
# cell assignment
# --------------------------------------------------------------------------- #
def test_cell_colours_majority_and_background():
    # 20x20 green block on a 40x40 transparent canvas, 4px cells -> a 10x10 grid.
    arr = _block(40, 40, [(10, 30, 10, 30, (0, 153, 0))])
    img = np.asarray(Image.fromarray(arr, "RGBA"))
    cc = _cell_colours(img, [(0, 153, 0)], ph=4, n_rows=10, n_cols=10)
    assert cc.shape == (10, 10)
    # interior cells (fully inside the block) are colour 0; the far corners are background.
    assert cc[3, 3] == 0 and cc[5, 5] == 0
    assert cc[0, 0] == -1 and cc[9, 9] == -1
    # only the block region is set; count of ink cells is modest (4x4 fully-covered core)
    assert (cc == 0).sum() >= 4


# --------------------------------------------------------------------------- #
# pattern structure
# --------------------------------------------------------------------------- #
def test_single_colour_x_structure():
    arr = _block(40, 40, [(10, 30, 10, 30, (0, 153, 0))])
    ctx = _ctx(arr, [(0, 153, 0)], width_mm=20.0)  # 0.5 mm/px, pitch 2 mm -> 4 px cells
    pat, n_cells, n_col = build_cross_stitch_pattern(ctx, 2.0)
    assert n_cells > 0 and n_col == 1
    counts = _cmd_counts(pat)
    # exactly 4 penetrations per cell (the X), one END, at least one TRIM (>=1 cluster).
    assert counts[_STITCH] == 4 * n_cells
    assert counts.get(_END, 0) == 1
    assert counts.get(_TRIM, 0) >= 1
    # thread colour = the cone RGB so step-6 can name it by RGB match
    t = pat.threadlist[0]
    assert (t.get_red(), t.get_green(), t.get_blue()) == (0, 153, 0)


def test_no_stray_origin_point():
    # A regression guard: appending stitches directly (not via add_stitch_absolute) left
    # trim()/end() at (0,0), which polluted the bounding box. There must be no (0,0) command.
    arr = _block(40, 40, [(10, 30, 10, 30, (0, 153, 0))])
    ctx = _ctx(arr, [(0, 153, 0)], width_mm=20.0)
    pat, _, _ = build_cross_stitch_pattern(ctx, 2.0)
    assert not any(s[0] == 0 and s[1] == 0 for s in pat.stitches)


def test_multi_colour_order_and_breaks():
    # two separated blocks -> two colours, a colour change between, a trim per cluster.
    arr = _block(40, 60, [(10, 30, 10, 30, (0, 153, 0)),
                          (10, 30, 40, 55, (255, 0, 0))])
    ctx = _ctx(arr, [(0, 153, 0), (255, 0, 0)], width_mm=30.0)
    pat, n_cells, n_col = build_cross_stitch_pattern(ctx, 2.0)
    assert n_col == 2
    assert [(t.get_red(), t.get_green(), t.get_blue()) for t in pat.threadlist] == \
           [(0, 153, 0), (255, 0, 0)]
    counts = _cmd_counts(pat)
    assert counts.get(_CC, 0) == 1  # exactly one change between the two colours
    # the colour change is NOT at the origin (it inherits the last real stitch position)
    cc_pts = [(s[0], s[1]) for s in pat.stitches if s[2] & 0xFF == _CC]
    assert cc_pts and cc_pts[0] != (0, 0)


def test_disjoint_clusters_get_separate_trims():
    # one colour, two separated blocks -> two connected components -> two trims.
    arr = _block(40, 70, [(10, 30, 5, 22, (0, 153, 0)),
                          (10, 30, 48, 65, (0, 153, 0))])
    ctx = _ctx(arr, [(0, 153, 0)], width_mm=35.0)
    pat, _, _ = build_cross_stitch_pattern(ctx, 2.0)
    assert _cmd_counts(pat).get(_TRIM, 0) == 2


def test_high_reversal_character():
    # The per-cell X must read as high-reversal (satin-like counted cross-stitch), NOT a
    # smooth run — that is what matches the tatreez ground-truth fingerprint (satin_frac~100).
    arr = _block(60, 60, [(6, 54, 6, 54, (0, 153, 0))])
    ctx = _ctx(arr, [(0, 153, 0)], width_mm=30.0)
    pat, _, _ = build_cross_stitch_pattern(ctx, 2.0)
    pts = np.array([(s[0], s[1]) for s in pat.stitches if s[2] & 0xFF == _STITCH], float)
    d = np.diff(pts, axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    turn = np.abs((np.diff(ang) + np.pi) % (2 * np.pi) - np.pi)
    reversal_frac = np.mean(np.degrees(turn) > 120)
    assert reversal_frac > 0.4  # production tatreez measures ~0.8


# --------------------------------------------------------------------------- #
# config wiring
# --------------------------------------------------------------------------- #
def _cfg(**kw) -> PipelineConfig:
    base = dict(input_path=Path("x.png"), output_dir=Path("out"), name="x", target_width_mm=100.0)
    base.update(kw)
    return PipelineConfig(**base)


def test_cross_stitch_auto_for_tatreez():
    assert _cfg(category="tatreez").resolved_cross_stitch is True
    assert _cfg(category="arabic").resolved_cross_stitch is False
    assert _cfg().resolved_cross_stitch is False


def test_cross_stitch_flag_overrides_category():
    assert _cfg(category="tatreez", cross_stitch=False).resolved_cross_stitch is False
    assert _cfg(category="arabic", cross_stitch=True).resolved_cross_stitch is True


def test_cross_stitch_pitch_resolution():
    from wilcom_pipeline import priors
    # explicit override wins
    assert _cfg(cross_stitch_pitch_mm=1.5).resolved_cross_stitch_pitch_mm == 1.5
    # tatreez has ingested pairs -> the prior (its measured satin-width median) drives it.
    # Assert the LOGIC (prior value flows through), not a fixed number that shifts as pairs
    # are added — just sanity-bound it to a plausible cross-stitch pitch.
    p = _cfg(category="tatreez").resolved_cross_stitch_pitch_mm
    assert p == priors.cross_stitch_pitch_mm("tatreez")
    assert 0.5 < p < 5.0
    # a category with no cross-stitch prior falls back to the positive default
    assert _cfg(category="anime").resolved_cross_stitch_pitch_mm > 0


def test_cross_stitch_pitch_validation():
    import pytest
    with pytest.raises(ValueError):
        _cfg(cross_stitch_pitch_mm=0.1)
    with pytest.raises(ValueError):
        _cfg(cross_stitch_pitch_mm=20.0)
