"""Tests for SLD stroke recovery (--sld-strokes): the sldvec bridge parsing/sampling
(pure geometry, no tool needed) and the region hook's px->root mapping. The end-to-end
recover_strokes test skips automatically when the vendored tool is absent, like the
Ink-Stitch-gated stitch tests.
"""

from __future__ import annotations

import numpy as np
import pytest
from lxml import etree

from wilcom_pipeline import sldvec
from wilcom_pipeline.steps import stitches

_SVG = "http://www.w3.org/2000/svg"


# --------------------------------------------------------------------------- #
# parse_svg_strokes (pure)
# --------------------------------------------------------------------------- #
def _svg(paths: list[str]) -> str:
    body = "".join(f'<path d="{d}" stroke="black" fill="none" />' for d in paths)
    return f'<svg xmlns="{_SVG}" width="100" height="100">{body}</svg>'


def test_parse_single_cubic_endpoints():
    strokes = sldvec.parse_svg_strokes(_svg(["M 0 0 C 10,0 20,0 30,0"]))
    assert len(strokes) == 1
    s = strokes[0]
    np.testing.assert_allclose(s[0], [0, 0], atol=1e-9)
    np.testing.assert_allclose(s[-1], [30, 0], atol=1e-9)
    # straight degenerate cubic: every sample on the x-axis, x monotonic
    assert np.all(np.abs(s[:, 1]) < 1e-9)
    assert np.all(np.diff(s[:, 0]) > 0)


def test_parse_multi_segment_spline_is_continuous():
    d = "M 0 0 C 5,10 10,10 15,0 C 20,-10 25,-10 30,0"
    (s,) = sldvec.parse_svg_strokes(_svg([d]))
    # curve passes through the segment joint (15, 0)
    joint = np.min(np.hypot(s[:, 0] - 15, s[:, 1]))
    assert joint < 0.5
    # sampling step honoured: no consecutive gap much larger than requested
    gaps = np.hypot(*np.diff(s, axis=0).T)
    assert gaps.max() < 3 * sldvec._SAMPLE_STEP_PX


def test_parse_skips_degenerate_paths():
    svg = _svg([
        "M 1 2 C nan nan nan nan 1 2",     # non-finite -> skipped
        "M 0 0 C 10,0 20,0 30,0",          # good
        "M 5 5",                            # too few numbers -> skipped
    ])
    strokes = sldvec.parse_svg_strokes(svg)
    assert len(strokes) == 1
    np.testing.assert_allclose(strokes[0][-1], [30, 0], atol=1e-9)


def test_parse_drops_zero_length_repeats():
    # closed path ending where it starts, then Z: consecutive duplicates removed
    (s,) = sldvec.parse_svg_strokes(_svg(["M 0 0 C 0,10 10,10 10,0 C 10,-10 0,-10 0,0 Z"]))
    gaps = np.hypot(*np.diff(s, axis=0).T)
    assert gaps.min() > 1e-9


# --------------------------------------------------------------------------- #
# _sld_region_strokes mapping + gates (tool mocked out)
# --------------------------------------------------------------------------- #
def _rect_path(w_uu: float, h_uu: float):
    e = etree.Element(f"{{{_SVG}}}path")
    e.set("d", f"M 0,0 {w_uu},0 {w_uu},{h_uu} 0,{h_uu} 0,0")
    return e


def test_region_strokes_maps_px_to_root_frame(monkeypatch):
    # 30x6 uu rect at 1 mm/uu -> raster res 0.3 uu/px, origin (-0.6,-0.6) after pad.
    poly = _rect_path(30, 6)
    fake_px = [np.array([[2.0, 10.0], [50.0, 10.0]])]
    monkeypatch.setattr(sldvec, "recover_strokes", lambda mask: fake_px)
    out = stitches._sld_region_strokes(poly, mm_per_uu=1.0)
    assert len(out) == 1
    mask, origin, res = stitches._region_raster(poly, 1.0, evenodd=True, res_mm=0.15)
    np.testing.assert_allclose(out[0][0], origin + fake_px[0][0] * res)
    np.testing.assert_allclose(out[0][-1], origin + fake_px[0][-1] * res)


def test_region_strokes_skips_tiny_regions(monkeypatch):
    called = []
    monkeypatch.setattr(sldvec, "recover_strokes",
                        lambda mask: called.append(1) or [])
    poly = _rect_path(3, 3)   # 9 mm^2 < the 20 mm^2 gate
    assert stitches._sld_region_strokes(poly, mm_per_uu=1.0) == []
    assert not called


def test_region_strokes_drops_sub_mm_ticks(monkeypatch):
    poly = _rect_path(30, 6)
    monkeypatch.setattr(sldvec, "recover_strokes",
                        lambda mask: [np.array([[10.0, 10.0], [10.5, 10.0]])])
    assert stitches._sld_region_strokes(poly, mm_per_uu=1.0) == []


def test_recover_strokes_empty_when_unavailable(monkeypatch):
    monkeypatch.setattr(sldvec, "available", lambda: False)
    assert sldvec.recover_strokes(np.ones((50, 50), bool)) == []


# --------------------------------------------------------------------------- #
# end-to-end against the vendored tool (skips when absent)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not sldvec.available(), reason="SLD-Vectorization not vendored")
def test_recover_strokes_on_a_bar():
    # a thin horizontal bar: one stroke, spanning ~the full width
    mask = np.zeros((60, 200), bool)
    mask[27:33, 10:190] = True
    strokes = sldvec.recover_strokes(mask, timeout_s=120)
    assert strokes, "tool returned no strokes for a plain bar"
    longest = max(strokes, key=lambda s: np.hypot(*np.diff(s, axis=0).T).sum())
    span = np.ptp(longest[:, 0])
    assert span > 120                      # covers most of the bar
    assert np.all(np.abs(longest[:, 1] - 30) < 8)   # stays on the centerline