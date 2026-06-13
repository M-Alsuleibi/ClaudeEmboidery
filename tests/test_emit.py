"""Tests for step 6 (emit): VP3 + preview + threadlist artifacts.

The end-to-end paths need the Ink-Stitch binary (the pattern comes from step 5)
and skip without it. The prerequisite-guard test always runs.
"""

from __future__ import annotations

import numpy as np
import pyembroidery as pe
import pytest
from PIL import Image

from wilcom_pipeline.config import PipelineConfig, PipelineContext
from wilcom_pipeline.steps import analyze, preprocess, thread_match, trace, stitches, emit

_needs_binary = pytest.mark.skipif(
    not stitches.binary_available(), reason="Ink-Stitch binary not vendored"
)


def _run_to_emit(tmp_path, arr, *, width_mm=60.0, num_colors=8):
    path = tmp_path / "in.png"
    Image.fromarray(arr.astype(np.uint8)).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t",
        target_width_mm=width_mm, num_colors=num_colors,
    )
    ctx = PipelineContext(config=cfg)
    for step in (analyze, preprocess, thread_match, trace, stitches, emit):
        step.run(ctx)
    return ctx, cfg


def _two_colour_logo():
    arr = np.full((160, 160, 3), 255, np.uint8)
    arr[30:130, 30:80] = (20, 40, 130)
    arr[30:130, 85:130] = (210, 40, 40)
    return arr


@_needs_binary
def test_all_three_artifacts_written(tmp_path):
    _, cfg = _run_to_emit(tmp_path, _two_colour_logo())
    assert cfg.vp3_path.is_file()
    assert cfg.preview_path.is_file()
    assert cfg.threadlist_path.is_file()


@_needs_binary
def test_vp3_reads_back_with_threads(tmp_path):
    ctx, cfg = _run_to_emit(tmp_path, _two_colour_logo())
    p = pe.read(str(cfg.vp3_path))
    assert len(p.stitches) > 100
    assert len(p.threadlist) == len(ctx.palette) == 2


@_needs_binary
def test_threadlist_has_sew_order_and_codes(tmp_path):
    ctx, cfg = _run_to_emit(tmp_path, _two_colour_logo())
    text = cfg.threadlist_path.read_text()
    assert "sew order" in text
    assert "total stitches" in text
    for m in ctx.thread_map:
        assert m["code"] in text


@_needs_binary
def test_preview_is_a_valid_image(tmp_path):
    _, cfg = _run_to_emit(tmp_path, _two_colour_logo())
    with Image.open(cfg.preview_path) as im:
        assert im.mode == "RGB"
        assert max(im.size) <= emit._PREVIEW_MAX_PX + 2 * emit._MARGIN_PX


def test_requires_stitch_pattern(tmp_path):
    path = tmp_path / "in.png"
    Image.fromarray(_two_colour_logo()).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t", target_width_mm=60.0
    )
    ctx = PipelineContext(config=cfg)
    with pytest.raises(RuntimeError, match="stitch_pattern"):
        emit.run(ctx)
