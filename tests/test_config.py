"""Tests for PipelineConfig resolvers: the manual-derived calibration defaults
(--fabric pull-compensation, per-category colour priors). See wilcom-manual-rules.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wilcom_pipeline.config import PipelineConfig


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(
        input_path=Path("x.png"), output_dir=Path("out"), name="t",
        target_width_mm=50.0, **kw,
    )


# --- colour count -----------------------------------------------------------
def test_num_colors_defaults_to_eight_without_category():
    assert _cfg().resolved_num_colors == 8


def test_num_colors_from_category_prior():
    assert _cfg(category="decoration").resolved_num_colors == 1
    assert _cfg(category="numbers").resolved_num_colors == 4
    assert _cfg(category="3D").resolved_num_colors == 8


def test_explicit_colors_overrides_category_prior():
    assert _cfg(category="decoration", num_colors=6).resolved_num_colors == 6


# --- pull compensation ------------------------------------------------------
def test_pull_comp_defaults_without_fabric():
    assert _cfg().resolved_pull_comp_mm == pytest.approx(0.2)


def test_pull_comp_from_fabric():
    assert _cfg(fabric="cotton").resolved_pull_comp_mm == pytest.approx(0.20)
    assert _cfg(fabric="t-shirt").resolved_pull_comp_mm == pytest.approx(0.35)
    assert _cfg(fabric="fleece").resolved_pull_comp_mm == pytest.approx(0.40)


def test_explicit_pull_comp_overrides_fabric():
    assert _cfg(fabric="fleece", pull_compensation_mm=0.05).resolved_pull_comp_mm == pytest.approx(0.05)


# --- validation -------------------------------------------------------------
def test_unknown_fabric_rejected():
    with pytest.raises(ValueError, match="Unknown fabric"):
        _cfg(fabric="velvet")


def test_zero_colors_rejected():
    with pytest.raises(ValueError, match="num_colors"):
        _cfg(num_colors=0)
