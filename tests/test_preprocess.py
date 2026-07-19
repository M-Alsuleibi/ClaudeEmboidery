"""Tests for step 2 (preprocess): background drop + palette reduction + snap."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from wilcom_pipeline.config import PipelineConfig, PipelineContext
from wilcom_pipeline.steps import analyze, preprocess


def _run(tmp_path, arr, *, num_colors=8, width_mm=100.0) -> PipelineContext:
    path = tmp_path / "in.png"
    Image.fromarray(arr.astype(np.uint8)).save(path)
    cfg = PipelineConfig(
        input_path=path,
        output_dir=tmp_path / "out",
        name="t",
        target_width_mm=width_mm,
        num_colors=num_colors,
    )
    ctx = PipelineContext(config=cfg)
    analyze.run(ctx)       # preprocess depends on analyze's output
    preprocess.run(ctx)
    return ctx


def _solid(h, w, rgb, alpha=None):
    arr = np.zeros((h, w, 3 if alpha is None else 4), np.uint8)
    arr[..., :3] = rgb
    if alpha is not None:
        arr[..., 3] = alpha
    return arr


def test_background_dropped_to_alpha(tmp_path):
    arr = _solid(200, 200, (255, 255, 255))
    arr[60:140, 60:140] = (200, 30, 30)  # red square on white
    ctx = _run(tmp_path, arr)

    img = ctx.preprocessed_image
    assert img.mode == "RGBA"
    a = np.asarray(img)
    assert a[0, 0, 3] == 0           # corner = background = transparent
    ch, cw = a.shape[0] // 2, a.shape[1] // 2
    assert a[ch, cw, 3] == 255       # centre = element = opaque
    assert a[ch, cw, 0] > 150 and a[ch, cw, 1] < 90  # ~red
    assert len(ctx.palette) == 1     # only one element colour


def test_color_budget_merges_closest(tmp_path):
    arr = _solid(220, 220, (255, 255, 255))
    arr[20:200, 20:80] = (20, 40, 130)    # navy (far from the others)
    arr[20:200, 90:140] = (210, 40, 40)   # red  -- close-ish to gold
    arr[20:200, 150:200] = (225, 170, 40)  # gold
    ctx = _run(tmp_path, arr, num_colors=2)
    assert len(ctx.palette) == 2
    # navy must survive (it's the lone distinct colour); a blue-dominant entry stays
    assert any(b > r for (r, g, b) in ctx.palette)


def test_alpha_input_preserves_transparency(tmp_path):
    arr = _solid(200, 200, (200, 30, 30), alpha=0)
    arr[50:150, 50:150, 3] = 255   # opaque red square, rest transparent
    ctx = _run(tmp_path, arr)
    a = np.asarray(ctx.preprocessed_image)
    assert a[0, 0, 3] == 0
    assert a[100, 100, 3] == 255


def test_palette_ordered_by_coverage(tmp_path):
    arr = _solid(200, 200, (255, 255, 255))
    arr[10:190, 10:170] = (20, 40, 130)    # big navy region
    arr[10:40, 170:190] = (225, 170, 40)   # tiny gold corner
    ctx = _run(tmp_path, arr, num_colors=4)
    r, g, b = ctx.palette[0]
    assert b > r and b > g          # most-covered colour is the navy


def test_requires_analysis_first(tmp_path):
    path = tmp_path / "in.png"
    Image.fromarray(_solid(32, 32, (255, 255, 255))).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t", target_width_mm=50.0
    )
    ctx = PipelineContext(config=cfg)
    with pytest.raises(RuntimeError, match="analyze"):
        preprocess.run(ctx)


def test_consolidate_merges_dither():
    # a block of colour 0 sprinkled with colour-1 specks (like posterised shading)
    from scipy import ndimage

    rng = np.random.default_rng(0)
    idx = np.zeros((40, 40), np.int32)
    idx[rng.random((40, 40)) < 0.25] = 1

    _, b0 = ndimage.label(idx == 0)
    _, b1 = ndimage.label(idx == 1)
    out = preprocess._consolidate(idx.copy(), 2, k=5)
    _, a0 = ndimage.label(out == 0)
    _, a1 = ndimage.label(out == 1)

    assert (a0 + a1) < (b0 + b1)                  # far fewer components
    assert (out == 1).sum() < (idx == 1).sum()    # minority specks absorbed


def test_consolidate_keeps_background_dropped():
    # foreground (>=0) stays foreground; background (-1) stays background
    idx = np.full((20, 20), -1, np.int32)
    idx[5:15, 5:15] = 0
    out = preprocess._consolidate(idx.copy(), 1, k=5)
    assert (out == -1).sum() == (idx == -1).sum()


def test_interior_black_linework_survives_consolidate(tmp_path):
    # A thin black line INSIDE a flat colour region (a mouth on a face) is thinner
    # than the consolidation kernel and would lose every neighbourhood vote; the
    # snapped black-ink mask must be re-imposed so facial linework isn't erased.
    arr = _solid(400, 800, (255, 255, 255))
    arr[40:360, 40:760] = (247, 210, 185)      # skin block
    arr[200, 250:550] = (0, 0, 0)              # 1px black line inside it (mouth)
    arr[40:360, 40:80] = (0, 0, 0)             # a black bar so ink fraction > _BLACK_MIN_FRAC
    # 800px input stays unscaled; k=3 mode filter erases a 1px interior line (3/9 votes)
    ctx = _run(tmp_path, arr, num_colors=3, width_mm=300.0)
    a = np.asarray(ctx.preprocessed_image)
    line = a[200, 300]
    # survives as black ink — on the keyline-detail layer (thin stroke => sews last)
    from wilcom_pipeline.config import KEYLINE_DETAIL_RGB

    assert tuple(line[:3]) in ((0, 0, 0), KEYLINE_DETAIL_RGB) and line[3] == 255
    assert KEYLINE_DETAIL_RGB in ctx.palette


def test_working_resolution_is_capped(tmp_path):
    arr = _solid(2000, 2000, (255, 255, 255))
    arr[400:1600, 400:1600] = (30, 120, 60)
    ctx = _run(tmp_path, arr)
    w, h = ctx.preprocessed_image.size
    assert max(w, h) <= preprocess._WORK_MAX_DIM


# --------------------------------------------------------------------------- #
# work-size by physical resolution (_work_max_dim) + median palette refine
# --------------------------------------------------------------------------- #
def _cfg(tmp_path, **kw):
    return PipelineConfig(input_path=tmp_path / "x.png", output_dir=tmp_path,
                          name="t", target_width_mm=kw.pop("width", 100.0), **kw)


def test_work_dim_flat_by_default(tmp_path):
    cfg = _cfg(tmp_path)
    a = {"size_mm": {"width_mm": 280.0, "height_mm": 230.0}}
    assert preprocess._work_max_dim(cfg, a) == preprocess._WORK_MAX_DIM


def test_work_dim_forced_by_knob_and_clamped(tmp_path):
    a = {"size_mm": {"width_mm": 280.0, "height_mm": 230.0}}
    cfg = _cfg(tmp_path, work_res_mm=0.15)
    assert preprocess._work_max_dim(cfg, a) == round(280 / 0.15)
    # small design clamps UP to the historical cap (no behaviour change)
    a_small = {"size_mm": {"width_mm": 90.0, "height_mm": 70.0}}
    assert preprocess._work_max_dim(cfg, a_small) == preprocess._WORK_MAX_DIM
    # garment-scale clamps DOWN to the memory cap
    a_huge = {"size_mm": {"width_mm": 1100.0, "height_mm": 1000.0}}
    assert preprocess._work_max_dim(cfg, a_huge) == preprocess._WORK_MAX_DIM_CAP


def test_work_dim_auto_for_satin_only(tmp_path, monkeypatch):
    monkeypatch.setattr(preprocess.priors, "satin_only", lambda c: c == "arabic")
    a = {"size_mm": {"width_mm": 280.0, "height_mm": 230.0}}
    assert (preprocess._work_max_dim(_cfg(tmp_path, category="arabic"), a)
            == round(280 / preprocess._WORK_RES_SATIN_ONLY_MM))
    assert preprocess._work_max_dim(_cfg(tmp_path, category="anime"), a) \
        == preprocess._WORK_MAX_DIM


def test_median_refine_corrects_aa_drift(tmp_path):
    # a red block whose 2px border is salmon (anti-aliasing toward white): the
    # refined palette entry must sit at the CORE red, not the mean-dragged salmon
    arr = np.full((120, 120, 3), 255, np.uint8)
    arr[20:100, 20:100] = (255, 120, 120)      # AA rim
    arr[24:96, 24:96] = (237, 28, 36)          # core red
    ctx = _run(tmp_path, arr, num_colors=1)
    red = min(ctx.palette, key=lambda c: abs(c[0] - 237) + abs(c[1] - 28))
    assert abs(red[0] - 237) <= 10 and abs(red[1] - 28) <= 25 and abs(red[2] - 36) <= 25, \
        f"palette stayed AA-drifted: {ctx.palette}"
