"""Smoke tests for the scaffold: config validation + pipeline wiring.

These don't test digitizing quality (steps aren't implemented yet) — they test
that the skeleton holds together and fails in the expected, graceful ways.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wilcom_pipeline import pipeline
from wilcom_pipeline.cli import build_parser
from wilcom_pipeline.config import PipelineConfig


def _config(tmp_path: Path, **overrides) -> PipelineConfig:
    kwargs = dict(
        input_path=tmp_path / "in.png",
        output_dir=tmp_path / "out",
        name="test",
        target_width_mm=80.0,
    )
    kwargs.update(overrides)
    return PipelineConfig(**kwargs)


def test_requires_a_target_size(tmp_path):
    with pytest.raises(ValueError, match="target size"):
        _config(tmp_path, target_width_mm=None)


def test_rejects_both_dimensions(tmp_path):
    with pytest.raises(ValueError, match="only one"):
        _config(tmp_path, target_width_mm=80.0, target_height_mm=50.0)


def test_rejects_unknown_thread_chart(tmp_path):
    with pytest.raises(ValueError, match="thread chart"):
        _config(tmp_path, thread_chart="nope")


def test_artifact_paths_follow_convention(tmp_path):
    cfg = _config(tmp_path, name="logo")
    assert cfg.vp3_path.name == "logo_pro.vp3"
    assert cfg.preview_path.name == "logo_pro_preview.png"
    assert cfg.threadlist_path.name == "logo_pro_threadlist.txt"


def test_pipeline_runs_end_to_end(tmp_path, capsys):
    # All 7 steps are implemented; the run should complete and write artifacts.
    # Needs the Ink-Stitch binary (step 5).
    import numpy as np
    import pytest
    from PIL import Image

    from wilcom_pipeline.steps.stitches import binary_available

    if not binary_available():
        pytest.skip("Ink-Stitch binary not vendored")

    img = tmp_path / "in.png"
    arr = np.full((64, 64, 3), 255, np.uint8)
    arr[20:44, 20:44] = (10, 10, 10)
    Image.fromarray(arr).save(img)

    cfg = _config(tmp_path, input_path=img)
    ctx = pipeline.run(cfg)
    out = capsys.readouterr().out

    assert "NOT YET IMPLEMENTED" not in out
    assert out.rstrip().endswith("done.")
    # every stage populated its slice of the context
    assert ctx.analysis and ctx.palette and ctx.preprocessed_image is not None
    assert ctx.thread_map and ctx.svg_path and ctx.stitch_pattern is not None
    assert ctx.verification.get("passed") is True
    # the three artifacts exist
    assert cfg.vp3_path.is_file()
    assert cfg.preview_path.is_file()
    assert cfg.threadlist_path.is_file()


def test_cli_parser_requires_image_and_size():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])  # missing image + size
