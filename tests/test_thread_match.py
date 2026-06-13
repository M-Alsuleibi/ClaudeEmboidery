"""Tests for step 3 (thread-match) and the .gpl catalog parser."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from wilcom_pipeline import catalog
from wilcom_pipeline.config import PipelineConfig, PipelineContext
from wilcom_pipeline.steps import analyze, preprocess, thread_match


# --- catalog parsing -------------------------------------------------------- #
def test_parse_gpl_handles_names_with_spaces(tmp_path):
    gpl = tmp_path / "mini.gpl"
    gpl.write_text(
        "GIMP Palette\n"
        "Name: Ink/Stitch: Test\n"
        "Columns: 4\n"
        "# RGB Value   Color Name Number\n"
        "183 195 197   Celestial Blue   1610\n"
        "0 0 0\tBlack\t1801\n"
        "255 255 255   White 1800\n"
    )
    colors = catalog.parse_gpl(gpl)
    assert len(colors) == 3
    assert colors[0].rgb == (183, 195, 197)
    assert colors[0].name == "Celestial Blue"
    assert colors[0].code == "1610"
    assert colors[1].name == "Black" and colors[1].code == "1801"


def test_real_catalogs_load():
    for key, minimum in (("madeira-polyneon", 100), ("isacord", 100)):
        cat = catalog.load_catalog(key)
        assert len(cat.colors) > minimum
        assert cat.labs.shape == (len(cat.colors), 3)


def test_nearest_finds_exact_catalog_color():
    cat = catalog.load_catalog("madeira-polyneon")
    target = cat.colors[10]
    found, de = cat.nearest(target.rgb)
    assert found.code == target.code
    assert de < 1e-6


def test_nearest_black_and_white_are_sane():
    cat = catalog.load_catalog("isacord")
    black, de_k = cat.nearest((0, 0, 0))
    white, de_w = cat.nearest((255, 255, 255))
    assert de_k < 25 and sum(black.rgb) < 120        # genuinely dark cone
    assert de_w < 25 and sum(white.rgb) > 680        # genuinely light cone


# --- the step --------------------------------------------------------------- #
def _ctx_through_preprocess(tmp_path, arr, *, chart="madeira-polyneon", num_colors=8):
    path = tmp_path / "in.png"
    Image.fromarray(arr.astype(np.uint8)).save(path)
    cfg = PipelineConfig(
        input_path=path,
        output_dir=tmp_path / "out",
        name="t",
        target_width_mm=100.0,
        num_colors=num_colors,
        thread_chart=chart,
    )
    ctx = PipelineContext(config=cfg)
    analyze.run(ctx)
    preprocess.run(ctx)
    return ctx


def test_thread_map_aligned_with_palette(tmp_path):
    arr = np.full((200, 200, 3), 255, np.uint8)
    arr[40:160, 40:120] = (20, 40, 130)    # navy
    arr[40:160, 130:160] = (210, 40, 40)   # red
    ctx = _ctx_through_preprocess(tmp_path, arr)
    thread_match.run(ctx)

    assert len(ctx.thread_map) == len(ctx.palette)
    for pal_rgb, m in zip(ctx.palette, ctx.thread_map):
        assert m["rgb"] == tuple(int(c) for c in pal_rgb)
        assert m["code"] and isinstance(m["thread_rgb"], tuple)
        assert m["catalog"] == "Madeira Polyneon"
        assert m["de"] >= 0


def test_chart_selection_changes_catalog(tmp_path):
    arr = np.full((120, 120, 3), 255, np.uint8)
    arr[30:90, 30:90] = (200, 30, 30)
    ctx = _ctx_through_preprocess(tmp_path, arr, chart="isacord")
    thread_match.run(ctx)
    assert all(m["catalog"] == "Isacord Polyester" for m in ctx.thread_map)


def test_requires_palette_first(tmp_path):
    path = tmp_path / "in.png"
    Image.fromarray(np.full((32, 32, 3), 255, np.uint8)).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t", target_width_mm=50.0
    )
    ctx = PipelineContext(config=cfg)
    with pytest.raises(RuntimeError, match="palette"):
        thread_match.run(ctx)
