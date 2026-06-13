"""Tests for step 4 (trace): layered, mm-sized, thread-recoloured SVG."""

from __future__ import annotations

import numpy as np
import pytest
from lxml import etree
from PIL import Image

from wilcom_pipeline.config import PipelineConfig, PipelineContext
from wilcom_pipeline.steps import analyze, preprocess, thread_match, trace

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"


def _run_to_trace(tmp_path, arr, *, width_mm=80.0, num_colors=8) -> PipelineContext:
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


def _logo(colors):
    """White canvas with vertical colour bands (each a distinct element colour)."""
    arr = np.full((200, 200, 3), 255, np.uint8)
    band = 160 // len(colors)
    for i, c in enumerate(colors):
        x0 = 20 + i * band
        arr[30:170, x0 : x0 + band] = c
    return arr


def test_trace_writes_svg_and_sets_path(tmp_path):
    ctx = _run_to_trace(tmp_path, _logo([(20, 40, 130), (210, 40, 40)]))
    assert ctx.svg_path is not None and ctx.svg_path.is_file()


def test_svg_has_mm_size_and_viewbox(tmp_path):
    ctx = _run_to_trace(tmp_path, _logo([(20, 40, 130)]), width_mm=80.0)
    root = etree.parse(str(ctx.svg_path)).getroot()
    assert root.get("width").endswith("mm")
    assert root.get("height").endswith("mm")
    assert float(root.get("width")[:-2]) == pytest.approx(80.0)
    vb = root.get("viewBox").split()
    assert len(vb) == 4 and vb[0] == "0"


def test_one_group_per_colour_with_label_and_thread_fill(tmp_path):
    ctx = _run_to_trace(tmp_path, _logo([(20, 40, 130), (210, 40, 40)]))
    root = etree.parse(str(ctx.svg_path)).getroot()
    gs = root.findall(f"{{{SVG_NS}}}g")
    assert len(gs) == len(ctx.palette) == 2

    thread_hexes = {
        "#{:02X}{:02X}{:02X}".format(*m["thread_rgb"]) for m in ctx.thread_map
    }
    for g in gs:
        assert g.get(f"{{{INK_NS}}}label")          # inkscape:label present
        paths = g.findall(f"{{{SVG_NS}}}path")
        assert paths
        fills = {p.get("fill") for p in paths}
        assert len(fills) == 1                       # uniform fill per group
        assert fills.pop() in thread_hexes           # recoloured to a thread cone


def test_sew_order_enclosed_colour_sews_last():
    # red square containing a blue square; green square off on its own.
    arr = np.zeros((120, 200, 4), np.uint8)
    arr[20:100, 10:90] = (200, 30, 30, 255)    # red (idx 0)
    arr[45:75, 35:65] = (20, 40, 160, 255)     # blue inside red (idx 1)
    arr[40:80, 140:180] = (30, 150, 40, 255)   # green, separate (idx 2)
    img = Image.fromarray(arr, "RGBA")
    palette = [(200, 30, 30), (20, 40, 160), (30, 150, 40)]

    order = trace._sew_order(img, palette)
    assert order[-1] == 1                       # enclosed blue sews last
    assert order.index(0) < order.index(1)      # its encloser (red) sews first


def test_requires_thread_map(tmp_path):
    # Run only up to preprocess, then trace must refuse.
    path = tmp_path / "in.png"
    Image.fromarray(_logo([(20, 40, 130)])).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t", target_width_mm=80.0
    )
    ctx = PipelineContext(config=cfg)
    analyze.run(ctx)
    preprocess.run(ctx)
    with pytest.raises(RuntimeError, match="thread_map"):
        trace.run(ctx)
