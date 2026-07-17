"""Tests for step 5 (stitches): Ink-Stitch headless digitizing.

Skipped when the Ink-Stitch binary isn't vendored, so the suite stays portable.
"""

from __future__ import annotations

import numpy as np
import pyembroidery as pe
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


def test_curved_stroke_in_satin_band_becomes_underlaid_satin(tmp_path):
    # A curved (multi-point centerline) stroke whose width lands in the satin
    # band (>= ~1.6 mm) is "linework" -> a satin column, laid over the default
    # center-walk + contour underlay (satin_underlay on by default).
    arr = np.full((140, 380, 3), 255, np.uint8)
    xs = np.arange(380)
    ys = (70 + 36 * np.sin(xs / 34.0)).astype(int)
    for x in xs:
        arr[ys[x] - 3 : ys[x] + 4, x] = (20, 30, 90)  # ~7px-tall wavy band -> ~2 mm
    ctx = _run_to_trace(tmp_path, arr, width_mm=130.0, num_colors=4)
    stitches.run(ctx)

    # the stitch-ready SVG should contain at least one *underlaid* satin column
    ready = (tmp_path / "out" / "t_working.svg").read_text()
    assert "satin_column" in ready
    assert "center_walk_underlay" in ready and "contour_underlay" in ready
    assert ctx.stitch_pattern is not None and len(ctx.stitch_pattern.stitches) > 100


def test_hairline_stroke_becomes_running_stitch(tmp_path):
    # A stroke thinner than the min satin width (~1.6 mm) is too thin to satin
    # without fattening -> a running/bean (triple) stitch along its centerline
    # (thin_line_run on by default; the playbook's "line < 1.6 mm -> run").
    arr = np.full((140, 380, 3), 255, np.uint8)
    xs = np.arange(380)
    ys = (70 + 36 * np.sin(xs / 34.0)).astype(int)
    for x in xs:
        arr[ys[x] - 2 : ys[x] + 3, x] = (20, 30, 90)  # ~5px-tall wavy band -> ~1.5 mm
    ctx = _run_to_trace(tmp_path, arr, width_mm=130.0, num_colors=4)
    stitches.run(ctx)

    ready = (tmp_path / "out" / "t_working.svg").read_text()
    assert 'stroke_method="running_stitch"' in ready
    assert 'bean_stitch_repeats' in ready          # triple/bean pass -> solid line
    # Variable run length: nominal = straight-run max, tolerance auto-shortens on curves.
    assert 'running_stitch_length_mm="4"' in ready
    assert 'running_stitch_tolerance_mm="0.2"' in ready
    assert "satin_column" not in ready             # not fattened into a satin
    assert ctx.stitch_pattern is not None and len(ctx.stitch_pattern.stitches) > 100


def test_thin_line_run_can_be_disabled(tmp_path):
    # --no-thin-line-run forces the same hairline back into a (clamped) satin,
    # the pre-② behaviour (bold-outline designs want this).
    arr = np.full((140, 380, 3), 255, np.uint8)
    xs = np.arange(380)
    ys = (70 + 36 * np.sin(xs / 34.0)).astype(int)
    for x in xs:
        arr[ys[x] - 2 : ys[x] + 3, x] = (20, 30, 90)
    path = tmp_path / "in.png"
    Image.fromarray(arr.astype(np.uint8)).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t",
        target_width_mm=130.0, num_colors=4, thin_line_run=False,
    )
    ctx = PipelineContext(config=cfg)
    for step in (analyze, preprocess, thread_match, trace, stitches):
        step.run(ctx)

    ready = (tmp_path / "out" / "t_working.svg").read_text()
    assert "satin_column" in ready
    assert 'stroke_method="running_stitch"' not in ready


def test_run_demotion_guard_keeps_large_meshy_region_as_fill():
    # The missing-middle-arc incident (arb trio, 2026-07-17): a 1,090mm2 connected
    # calligraphy band whose thin connectors dragged its area-weighted width to
    # "1.36mm" was demoted to 6 bean runs (long_frac 0.16 — spurs dominate), dropping
    # its fill: ~15% coverage sewed, verify stayed green. The guard: a sub-1.6mm
    # region may only demote to runs when it is small OR its long centerlines carry
    # the skeleton. Pure-unit test of the decision (no Ink-Stitch binary needed).
    from lxml import etree
    from wilcom_pipeline.steps.stitches import _SVG_NS, _run_demotion_ok

    def _line(length_uu):
        return etree.fromstring(
            f'<path xmlns="{_SVG_NS}" d="M0,0 L{length_uu:.1f},0"/>')

    # the arb middle arc, to scale: 6 longs carrying ~16% of an 800mm skeleton
    longs = [_line(85) for _ in range(6)]
    spurs = [_line(3.4) for _ in range(198)]
    assert not _run_demotion_ok(1.36, 1090.0, longs, longs + spurs)

    # a genuine long hairline keyline (one centerline = the whole skeleton) still runs,
    # even though its area exceeds the cap (140mm x 1.5mm = 210mm2)
    hair = [_line(560)]
    assert _run_demotion_ok(1.5, 210.0, hair, hair)

    # a small diacritic/dot stays a run regardless of its (noisy) long fraction
    dot_longs = [_line(12)]
    dot_lines = dot_longs + [_line(20), _line(15)]
    assert _run_demotion_ok(1.0, 8.0, dot_longs, dot_lines)

    # at-or-above the satin threshold the run tier never applies
    assert not _run_demotion_ok(1.7, 8.0, dot_longs, dot_lines)


def test_requires_svg_path(tmp_path):
    path = tmp_path / "in.png"
    Image.fromarray(_two_colour_logo()).save(path)
    cfg = PipelineConfig(
        input_path=path, output_dir=tmp_path / "out", name="t", target_width_mm=60.0
    )
    ctx = PipelineContext(config=cfg)
    with pytest.raises(RuntimeError, match="svg_path"):
        stitches.run(ctx)


def _block_bboxes_mm(pattern):
    """Per-colour-block stitch bbox in mm (split on COLOR_CHANGE)."""
    blocks, cur = [], []
    for x, y, c in pattern.stitches:
        cmd = c & 0xFF
        if cmd == (pe.COLOR_CHANGE & 0xFF):
            blocks.append(cur)
            cur = []
        elif cmd == (pe.STITCH & 0xFF):
            cur.append((x, y))
    if cur:
        blocks.append(cur)
    out = []
    for b in blocks:
        xs = [x for x, _ in b]
        ys = [y for _, y in b]
        out.append((min(xs) / 10, min(ys) / 10, max(xs) / 10, max(ys) / 10))
    return out


def test_per_group_digitize_is_coordinate_faithful(tmp_path):
    # Ink-Stitch's VP3 export centres each mini on its OWN stitch bbox, so without the
    # frame anchor the merged groups shift relative to each other. Digitize the same
    # ready SVG whole and per-group: every colour block must land in the same place
    # relative to the design (frames may differ by a global constant only).
    ctx = _run_to_trace(tmp_path, _two_colour_logo())
    stitches.run(ctx)                       # fast path: single whole-design pass
    assert ctx.per_group_svgs is None       # non-hanging design never goes per-group
    whole = ctx.stitch_pattern

    binary = stitches._locate_binary()
    merged, group_svgs = stitches._digitize_per_group(binary, ctx.stitch_svg_path)
    assert len(group_svgs) == 2             # both groups digitized as-is, files kept
    assert all(p.exists() for p in group_svgs)

    wb = _block_bboxes_mm(whole)
    mb = _block_bboxes_mm(merged)
    assert len(wb) == len(mb) == 2
    # anchor thread stripped: only the real cones, in sew order, same as the whole pass
    assert [t.color for t in merged.threadlist] == [t.color for t in whole.threadlist]

    def centre(bb):
        return ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)

    # relative offset between the two colour blocks must match the whole pass sub-mm
    dwx = centre(wb[1])[0] - centre(wb[0])[0]
    dwy = centre(wb[1])[1] - centre(wb[0])[1]
    dmx = centre(mb[1])[0] - centre(mb[0])[0]
    dmy = centre(mb[1])[1] - centre(mb[0])[1]
    assert abs(dwx - dmx) < 1.0 and abs(dwy - dmy) < 1.0
    # and each block keeps its size (nothing rescaled/reframed)
    for w, m in zip(wb, mb):
        assert abs((w[2] - w[0]) - (m[2] - m[0])) < 1.0
        assert abs((w[3] - w[1]) - (m[3] - m[1])) < 1.0


def test_outline_objects_layer_borders_over_fills(tmp_path):
    # --outline-objects: each substantial fill gains a closed satin border sewn right
    # after it (same colour group) — the production "outline family". Off by default
    # for an uncategorised design (AUTO = satin-dominant categories only).
    import dataclasses
    ctx = _run_to_trace(tmp_path, _two_colour_logo())
    ctx.config = dataclasses.replace(ctx.config, outline_objects=True)
    stitches.run(ctx)
    # NOTE stroke_to_satin renames the border ids, so assert STRUCTURE: in every colour
    # group the fill is followed by a satin column in the SAME colour (the border).
    from lxml import etree as _et
    root = _et.parse(str(tmp_path / "out" / "t_working.svg")).getroot()
    svg = "http://www.w3.org/2000/svg"
    ink = "http://inkstitch.org/namespace"
    n_groups_with_border = 0
    for g in root.iter(f"{{{svg}}}g"):
        paths = list(g.iter(f"{{{svg}}}path"))
        fills = [p for p in paths if p.get("fill") and p.get("fill") != "none"]
        satins = [p for p in paths if p.get(f"{{{ink}}}satin_column")]
        if not (fills and satins):
            continue
        n_groups_with_border += 1
        assert paths.index(satins[0]) > paths.index(fills[0])   # border sews AFTER its fill
        assert fills[0].get("fill").lower() in (satins[0].get("style") or "").lower()
        assert satins[0].get(f"{{{ink}}}trim_after") == "True"  # standard satin params on
        assert satins[0].get(f"{{{ink}}}center_walk_underlay") == "True"
    assert n_groups_with_border == 2                     # both colour groups got borders


def test_outline_objects_default_off_without_category(tmp_path):
    ctx = _run_to_trace(tmp_path, _two_colour_logo())
    stitches.run(ctx)                                    # outline_objects=None, no category
    ready = (tmp_path / "out" / "t_working.svg").read_text()
    assert "border" not in ready
