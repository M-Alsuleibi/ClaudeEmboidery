"""Tests for step 7 (verify): the quality gate.

Most cases use lightweight synthetic patterns (verify only needs .stitches and
len(.threadlist)), so they run without the Ink-Stitch binary. One integration
case exercises the real chain and skips without it.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pyembroidery as pe
import pytest
from PIL import Image

from wilcom_pipeline.config import PipelineConfig, PipelineContext
from wilcom_pipeline.steps import analyze, preprocess, thread_match, trace, stitches, verify

S, CC, E = pe.STITCH, pe.COLOR_CHANGE, pe.END


def _ctx(tmp_path, stitch_list, n_threads, analysis=None):
    cfg = PipelineConfig(
        input_path=tmp_path / "x.png", output_dir=tmp_path / "out",
        name="t", target_width_mm=50.0,
    )
    ctx = PipelineContext(config=cfg)
    ctx.analysis = analysis or {}
    ctx.stitch_pattern = SimpleNamespace(
        stitches=stitch_list, threadlist=[object()] * n_threads
    )
    return ctx


def _check(ctx, name):
    return next(c for c in ctx.verification["checks"] if c["name"] == name)


def test_clean_pattern_passes_gate(tmp_path):
    st = [
        (0, 0, S), (100, 0, S), (100, 100, S), (0, 100, S), (0, 0, S),
        (0, 0, CC),
        (200, 0, S), (300, 0, S), (300, 100, S), (200, 100, S),
        (0, 0, E),
    ]
    ctx = _ctx(tmp_path, st, n_threads=2)
    verify.run(ctx)
    assert ctx.verification["passed"] is True
    assert all(c["passed"] for c in ctx.verification["checks"] if c["severity"] == "error")


def test_empty_colour_block_fails_gate(tmp_path):
    # second colour block has zero stitches -> a region was eaten
    st = [(0, 0, S), (100, 0, S), (0, 0, CC), (0, 0, E)]
    ctx = _ctx(tmp_path, st, n_threads=2)
    verify.run(ctx)
    assert ctx.verification["passed"] is False
    assert _check(ctx, "all_colours_sewed")["passed"] is False


def test_colour_change_mismatch_fails_gate(tmp_path):
    # 2 threads but no colour change between them
    st = [(0, 0, S), (100, 0, S), (100, 100, S), (0, 0, E)]
    ctx = _ctx(tmp_path, st, n_threads=2)
    verify.run(ctx)
    assert ctx.verification["passed"] is False
    assert _check(ctx, "colour_changes_consistent")["passed"] is False


def test_metrics_and_notes_present(tmp_path):
    st = [(0, 0, S), (100, 0, S), (100, 100, S), (0, 0, E)]
    ctx = _ctx(tmp_path, st, n_threads=1, analysis={"warnings": ["a note"]})
    verify.run(ctx)
    m = ctx.verification["metrics"]
    assert set(m) >= {"stitches", "colours", "trims", "jumps", "extent_mm", "density_per_mm2"}
    assert ctx.verification["notes"] == ["a note"]


def test_requires_stitch_pattern(tmp_path):
    cfg = PipelineConfig(
        input_path=tmp_path / "x.png", output_dir=tmp_path / "out",
        name="t", target_width_mm=50.0,
    )
    ctx = PipelineContext(config=cfg)
    with pytest.raises(RuntimeError, match="stitch_pattern"):
        verify.run(ctx)


def test_budget_ceiling_is_the_densest_reference():
    """The stitch budget must never warn on a stitch count the category's own
    reference files reach: the ceiling is the observed density hi + 10% (the arb
    trio sews 0.67 st/mm2 vs the arabic median 0.42 — median x1.8 flagged counts
    inside the trio's correct band), while genuinely bloated counts still warn."""
    from types import SimpleNamespace
    from wilcom_pipeline.steps.verify import _budget_check
    from wilcom_pipeline import fingerprint

    prof = fingerprint.load_profiles().get("arabic", {})
    band = prof.get("density") or {}
    if not (prof.get("n_files") and band.get("hi")):
        pytest.skip("no arabic profile with observed range")
    hi = float(band["hi"])
    ctx = SimpleNamespace(config=SimpleNamespace(category="arabic"))
    area = 60000.0
    ok, _ = _budget_check(ctx, int(hi * area), area)          # the densest reference
    assert ok is True
    ok, _ = _budget_check(ctx, int(hi * 1.3 * area), area)    # 30% denser = bloat
    assert ok is False


@pytest.mark.skipif(not stitches.binary_available(), reason="Ink-Stitch binary not vendored")
def test_real_logo_passes_gate(tmp_path):
    arr = np.full((160, 160, 3), 255, np.uint8)
    arr[30:130, 30:80] = (20, 40, 130)
    arr[30:130, 85:130] = (210, 40, 40)
    path = tmp_path / "in.png"
    Image.fromarray(arr).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t", target_width_mm=60.0
    )
    ctx = PipelineContext(config=cfg)
    for step in (analyze, preprocess, thread_match, trace, stitches, verify):
        step.run(ctx)
    assert ctx.verification["passed"] is True
