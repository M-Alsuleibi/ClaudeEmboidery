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


def test_working_resolution_is_capped(tmp_path):
    arr = _solid(2000, 2000, (255, 255, 255))
    arr[400:1600, 400:1600] = (30, 120, 60)
    ctx = _run(tmp_path, arr)
    w, h = ctx.preprocessed_image.size
    assert max(w, h) <= preprocess._WORK_MAX_DIM
