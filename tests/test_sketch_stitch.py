"""Tests for the sketch-stitch primitive (steps/sketchstitch.py + its config wiring).

Pure geometry + pyembroidery — no Ink-Stitch binary needed (the point of the
primitive). Covers stroke generation, fur-direction following, the bean keyline
layer sewing last, break-apart trims, the no-stray-origin invariant, and config.
"""

from __future__ import annotations

import types
from pathlib import Path

import numpy as np
import pyembroidery as pe
from PIL import Image

from wilcom_pipeline.config import KEYLINE_DETAIL_RGB, PipelineConfig
from wilcom_pipeline.steps.sketchstitch import build_sketch_pattern

_STITCH = pe.STITCH & 0xFF
_TRIM = pe.TRIM & 0xFF
_CC = pe.COLOR_CHANGE & 0xFF
_END = pe.END & 0xFF


def _ctx(tmp_path, arr: np.ndarray, palette, width_mm: float, source: np.ndarray | None = None):
    """Minimal step-5 context. `source` is the ORIGINAL artwork the direction field is
    measured from (defaults to the flat quantized image itself)."""
    src = source if source is not None else arr[..., :3]
    src_path = tmp_path / "src.png"
    Image.fromarray(src.astype(np.uint8)).save(src_path)
    return types.SimpleNamespace(
        preprocessed_image=Image.fromarray(arr, "RGBA"),
        palette=palette,
        thread_map=[{"thread_rgb": tuple(rgb)} for rgb in palette],
        analysis={"size_mm": {"width_mm": width_mm,
                              "height_mm": width_mm * arr.shape[0] / arr.shape[1]}},
        config=types.SimpleNamespace(input_path=src_path),
    )


def _block(h=80, w=80, boxes=()):
    arr = np.zeros((h, w, 4), np.uint8)
    for (y0, y1, x0, x1, rgb) in boxes:
        arr[y0:y1, x0:x1, :3] = rgb
        arr[y0:y1, x0:x1, 3] = 255
    return arr


def _cmds(pat):
    out = {}
    for s in pat.stitches:
        out[s[2] & 0xFF] = out.get(s[2] & 0xFF, 0) + 1
    return out


def test_basic_structure_and_thread(tmp_path):
    arr = _block(80, 80, [(10, 70, 10, 70, (180, 120, 60))])
    ctx = _ctx(tmp_path, arr, [(180, 120, 60)], width_mm=40.0)
    pat, n_strokes, n_col = build_sketch_pattern(ctx, 1.0)
    assert n_strokes > 10 and n_col == 1
    counts = _cmds(pat)
    assert counts[_STITCH] > 50
    assert counts.get(_END, 0) == 1
    assert counts.get(_TRIM, 0) >= 1
    t = pat.threadlist[0]
    assert (t.get_red(), t.get_green(), t.get_blue()) == (180, 120, 60)
    # regression guard: trims/end must inherit the needle position, never (0,0)
    assert not any(s[0] == 0 and s[1] == 0 for s in pat.stitches)


def test_strokes_follow_source_texture_direction(tmp_path):
    # Source art has strong HORIZONTAL stripes (fur drawn left-right); the quantized
    # region is one flat block. Generated strokes must run predominantly horizontal.
    src = np.full((80, 80, 3), 255, np.uint8)
    src[::4] = (40, 20, 10)                       # horizontal texture lines
    arr = _block(80, 80, [(10, 70, 10, 70, (180, 120, 60))])
    ctx = _ctx(tmp_path, arr, [(180, 120, 60)], width_mm=40.0, source=src)
    pat, _, _ = build_sketch_pattern(ctx, 1.0)
    pts = np.array([(s[0], s[1]) for s in pat.stitches if s[2] & 0xFF == _STITCH], float)
    d = np.diff(pts, axis=0)
    keep = np.hypot(d[:, 0], d[:, 1]) > 1        # ignore zero-hops
    ang = np.abs(np.degrees(np.arctan2(d[keep, 1], d[keep, 0])))
    horiz = np.mean((ang < 30) | (ang > 150))
    assert horiz > 0.6, f"only {horiz:.0%} of segments follow the fur direction"


def test_keyline_detail_sews_last_as_bean(tmp_path):
    # base block + a thin KEYLINE_DETAIL_RGB stroke: the detail layer must be the LAST
    # colour block and sewn bean (tripled segments => repeated penetrations).
    arr = _block(80, 120, [(10, 70, 10, 70, (180, 120, 60))])
    arr[40:42, 75:115, :3] = KEYLINE_DETAIL_RGB
    arr[40:42, 75:115, 3] = 255
    palette = [KEYLINE_DETAIL_RGB, (180, 120, 60)]   # detail FIRST in palette on purpose
    ctx = _ctx(tmp_path, arr, palette, width_mm=60.0)
    ctx.thread_map = [{"thread_rgb": (0, 0, 0)}, {"thread_rgb": (180, 120, 60)}]
    pat, _, n_col = build_sketch_pattern(ctx, 1.0)
    assert n_col == 2
    last = pat.threadlist[-1]
    assert (last.get_red(), last.get_green(), last.get_blue()) == (0, 0, 0)
    assert _cmds(pat).get(_CC, 0) == 1
    # bean: the detail block revisits penetrations (forward-back-forward)
    blocks, cur = [[]], []
    for s in pat.stitches:
        if s[2] & 0xFF == _CC:
            blocks.append([])
        elif s[2] & 0xFF == _STITCH:
            blocks[-1].append((s[0], s[1]))
    detail = blocks[-1]
    # bean re-enters the same penetrations (forward-back-forward on one line), so a
    # large share of the block's points are duplicates
    dup = len(detail) - len(set(detail))
    assert dup >= len(detail) // 3, "detail layer is not bean-stitched"


def test_airy_coverage_density(tmp_path):
    # The sketch look leaves fabric visible: stitches per covered mm^2 stays in a
    # sane sketch band (well below solid tatami's needlework, well above nothing).
    arr = _block(80, 80, [(10, 70, 10, 70, (180, 120, 60))])
    ctx = _ctx(tmp_path, arr, [(180, 120, 60)], width_mm=40.0)
    pat, _, _ = build_sketch_pattern(ctx, 1.0)
    n = _cmds(pat)[_STITCH]
    area_mm2 = (60 * 0.5) * (60 * 0.5)   # block is 60x60 px at 0.5 mm/px
    assert 0.3 < n / area_mm2 < 6.0


def test_disjoint_components_get_trims(tmp_path):
    arr = _block(80, 120, [(10, 70, 5, 45, (180, 120, 60)),
                           (10, 70, 70, 110, (180, 120, 60))])
    ctx = _ctx(tmp_path, arr, [(180, 120, 60)], width_mm=60.0)
    pat, _, _ = build_sketch_pattern(ctx, 1.0)
    assert _cmds(pat).get(_TRIM, 0) >= 2


# --------------------------------------------------------------------------- #
# config wiring
# --------------------------------------------------------------------------- #
def _cfg(**kw) -> PipelineConfig:
    base = dict(input_path=Path("x.png"), output_dir=Path("out"), name="x",
                target_width_mm=100.0)
    base.update(kw)
    return PipelineConfig(**base)


def test_sketch_auto_for_animals():
    assert _cfg(category="animals").resolved_sketch_stitch is True
    assert _cfg(category="anime").resolved_sketch_stitch is False
    assert _cfg().resolved_sketch_stitch is False


def test_sketch_flag_overrides_category():
    assert _cfg(category="animals", sketch_stitch=False).resolved_sketch_stitch is False
    assert _cfg(category="anime", sketch_stitch=True).resolved_sketch_stitch is True


def test_sketch_spacing_resolution():
    from wilcom_pipeline import priors
    assert _cfg(sketch_row_spacing_mm=0.5).resolved_sketch_row_spacing_mm == 0.5
    s = _cfg(category="animals").resolved_sketch_row_spacing_mm
    assert s == priors.sketch_row_spacing_mm("animals")
    assert 0.2 < s < 3.0
    assert _cfg(category="anime").resolved_sketch_row_spacing_mm > 0


def test_sketch_spacing_validation():
    import pytest
    with pytest.raises(ValueError):
        _cfg(sketch_row_spacing_mm=0.05)
    with pytest.raises(ValueError):
        _cfg(sketch_row_spacing_mm=9.0)
