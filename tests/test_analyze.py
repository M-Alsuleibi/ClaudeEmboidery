"""Tests for step 1 (analyze) against synthetic images with known properties."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from wilcom_pipeline.config import PipelineConfig, PipelineContext
from wilcom_pipeline.steps import analyze


def _ctx(tmp_path, arr, *, width_mm=100.0, height_mm=None, name="t") -> PipelineContext:
    path = tmp_path / f"{name}.png"
    Image.fromarray(arr.astype(np.uint8)).save(path)
    cfg = PipelineConfig(
        input_path=path,
        output_dir=tmp_path / "out",
        name=name,
        target_width_mm=width_mm,
        target_height_mm=height_mm,
    )
    return PipelineContext(config=cfg)


def _solid(h, w, rgb, alpha=None):
    arr = np.zeros((h, w, 3 if alpha is None else 4), np.uint8)
    arr[..., :3] = rgb
    if alpha is not None:
        arr[..., 3] = alpha
    return arr


def test_logo_white_bg_red_shape(tmp_path):
    arr = _solid(200, 200, (255, 255, 255))
    arr[35:165, 35:165] = (200, 30, 30)  # big centred red square
    ctx = _ctx(tmp_path, arr)
    analyze.run(ctx)
    a = ctx.analysis

    assert a["background"]["method"] == "border-dominant"
    assert a["background"]["is_separable"] is True
    assert max(a["background"]["color"]) > 240  # bg ~ white
    # a dominant element colour close to the red we drew
    reds = [c for c in a["colors"] if c["rgb"][0] > 150 and c["rgb"][1] < 90]
    assert reds, a["colors"]
    assert a["kind"] == "logo/graphic"
    assert a["source"]["has_alpha"] is False


def test_photo_like_noise_is_not_separable_and_classified_photo(tmp_path):
    rng = np.random.default_rng(0)
    arr = rng.integers(0, 256, size=(200, 200, 3))
    ctx = _ctx(tmp_path, arr)
    analyze.run(ctx)
    a = ctx.analysis
    assert a["kind"] == "photo"
    assert a["background"]["is_separable"] is False
    assert any("not cleanly separable" in w for w in a["warnings"])


def test_dark_on_dark_flagged(tmp_path):
    arr = _solid(200, 200, (12, 12, 12))         # near-black bg
    arr[60:140, 60:140] = (45, 45, 45)           # dark-grey shape
    ctx = _ctx(tmp_path, arr)
    analyze.run(ctx)
    a = ctx.analysis
    assert a["contrast"]["low_contrast_with_bg"], a["contrast"]
    assert any("dark-on-dark" in w for w in a["warnings"])


def test_alpha_background_detected(tmp_path):
    arr = _solid(200, 200, (200, 30, 30), alpha=0)   # fully transparent
    arr[50:150, 50:150, 3] = 255                     # opaque red square
    ctx = _ctx(tmp_path, arr)
    analyze.run(ctx)
    a = ctx.analysis
    assert a["source"]["has_alpha"] is True
    assert a["background"]["method"] == "alpha"
    assert a["background"]["color"] is None
    assert a["background"]["is_separable"] is True


def test_mm_resolution_from_width(tmp_path):
    arr = _solid(100, 200, (255, 255, 255))  # 200 wide x 100 tall, aspect 2.0
    arr[30:70, 80:120] = (10, 10, 10)
    ctx = _ctx(tmp_path, arr, width_mm=100.0)
    analyze.run(ctx)
    mm = ctx.analysis["size_mm"]
    assert mm["width_mm"] == pytest.approx(100.0)
    assert mm["height_mm"] == pytest.approx(50.0)


def test_smallest_feature_in_mm_present_for_separable(tmp_path):
    arr = _solid(200, 200, (255, 255, 255))
    arr[:, 98:102] = (10, 10, 10)  # a thin 4px vertical line
    ctx = _ctx(tmp_path, arr, width_mm=200.0)  # 1 mm/px
    analyze.run(ctx)
    a = ctx.analysis
    assert a["smallest_feature_mm"] is not None
    # thin line ~4px at 1mm/px -> a few mm; definitely flagged below satin min if small
    assert a["smallest_feature_px"] is not None
