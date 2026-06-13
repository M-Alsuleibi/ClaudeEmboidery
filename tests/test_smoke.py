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


def test_pipeline_stops_gracefully_at_first_unimplemented_step(tmp_path, capsys):
    # Every step is a stub today; the run should stop at step 1 (analyze)
    # without raising, and create the output dir along the way.
    ctx = pipeline.run(_config(tmp_path))
    assert (tmp_path / "out").is_dir()
    assert "NOT YET IMPLEMENTED" in capsys.readouterr().out
    assert ctx.analysis == {}  # nothing populated yet


def test_cli_parser_requires_image_and_size():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])  # missing image + size
