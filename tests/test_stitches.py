"""Tests for step 5 (stitches): Ink-Stitch headless digitizing.

Skipped when the Ink-Stitch binary isn't vendored, so the suite stays portable.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from wilcom_pipeline.config import PipelineConfig, PipelineContext
from wilcom_pipeline.steps import analyze, preprocess, thread_match, trace, stitches

pytestmark = pytest.mark.skipif(
    not stitches.binary_available(), reason="Ink-Stitch binary not vendored"
)


def _run_to_trace(tmp_path, arr, *, width_mm=60.0, num_colors=8) -> PipelineContext:
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
    analyze.run(ctx)
    preprocess.run(ctx)
    thread_match.run(ctx)
    trace.run(ctx)
    return ctx


def _two_colour_logo():
    arr = np.full((160, 160, 3), 255, np.uint8)
    arr[30:130, 30:80] = (20, 40, 130)    # navy block
    arr[30:130, 85:130] = (210, 40, 40)   # red block
    return arr


def test_stitches_produced_and_loaded(tmp_path):
    ctx = _run_to_trace(tmp_path, _two_colour_logo())
    stitches.run(ctx)
    assert ctx.stitch_pattern is not None
    assert len(ctx.stitch_pattern.stitches) > 100        # real coverage
    assert len(ctx.stitch_pattern.threadlist) == len(ctx.palette) == 2


def test_thread_colours_carried_into_pattern(tmp_path):
    ctx = _run_to_trace(tmp_path, _two_colour_logo())
    stitches.run(ctx)
    pattern_rgbs = {
        (t.get_red(), t.get_green(), t.get_blue()) for t in ctx.stitch_pattern.threadlist
    }
    thread_rgbs = {m["thread_rgb"] for m in ctx.thread_map}
    assert pattern_rgbs == thread_rgbs                   # VP3 carries matched cones


def test_stitched_extent_is_sane(tmp_path):
    # navy+red span 30..130 px of a 160px image at 60mm wide -> ~37.5mm content
    ctx = _run_to_trace(tmp_path, _two_colour_logo(), width_mm=60.0)
    stitches.run(ctx)
    xs = [s[0] for s in ctx.stitch_pattern.stitches]
    width_mm = (max(xs) - min(xs)) / 10
    assert 25 < width_mm < 55


def test_thin_curved_stroke_becomes_satin(tmp_path):
    # A thin, curved (multi-point centerline) stroke is "linework" -> satin.
    arr = np.full((140, 380, 3), 255, np.uint8)
    xs = np.arange(380)
    ys = (70 + 36 * np.sin(xs / 34.0)).astype(int)
    for x in xs:
        arr[ys[x] - 2 : ys[x] + 3, x] = (20, 30, 90)  # ~5px-tall wavy band
    ctx = _run_to_trace(tmp_path, arr, width_mm=130.0, num_colors=4)
    stitches.run(ctx)

    # the stitch-ready SVG should contain at least one satin column
    ready = (tmp_path / "out" / "t_inkstitch.svg").read_text()
    assert "satin_column" in ready
    assert ctx.stitch_pattern is not None and len(ctx.stitch_pattern.stitches) > 100


def test_requires_svg_path(tmp_path):
    path = tmp_path / "in.png"
    Image.fromarray(_two_colour_logo()).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t", target_width_mm=60.0
    )
    ctx = PipelineContext(config=cfg)
    with pytest.raises(RuntimeError, match="svg_path"):
        stitches.run(ctx)
