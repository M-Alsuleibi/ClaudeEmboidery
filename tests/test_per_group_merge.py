"""Pure-logic tests for the per-colour-group digitize fallback (step 5).

Ink-Stitch's VP3 export centres each output on its own stitch bbox, so the per-group
minis carry a shared "frame anchor" (two manual stitches just outside opposite canvas
corners) that pins every group to one coordinate frame; the anchor block is stripped
from each pattern after read-back. These tests cover the anchor/strip/merge geometry
without needing the Ink-Stitch binary (see test_stitches.py for the end-to-end
alignment test against a real whole-design pass).
"""

from __future__ import annotations

import pyembroidery as pe
from lxml import etree

from wilcom_pipeline.steps import stitches
from wilcom_pipeline.steps.stitches import (
    _add_frame_anchor,
    _anchor_corners,
    _concat_same_colour,
    _merge_patterns,
    _pick_anchor_colour,
    _split_fills_satins,
    _strip_anchor_block,
    _write_fill_variant,
)

_SVG_NS = "http://www.w3.org/2000/svg"
_INK_NS = "http://inkstitch.org/namespace"


def _pattern(threads, stitches_):
    pat = pe.EmbPattern()
    for rgb in threads:
        pat.add_thread({"rgb": rgb})
    pat.stitches = [list(s) for s in stitches_]
    return pat


def _svg_root(body: str, viewbox: str = "0 0 1200 800", width: str = "150mm") -> etree._Element:
    return etree.fromstring(
        f'<svg xmlns="{_SVG_NS}" xmlns:inkstitch="{_INK_NS}" '
        f'width="{width}" height="100mm" viewBox="{viewbox}">{body}</svg>'.encode()
    )


# --------------------------------------------------------------------------- #
# anchor placement
# --------------------------------------------------------------------------- #
def test_anchor_corners_sit_outside_viewbox_by_margin():
    root = _svg_root("", viewbox="0 0 1200 800", width="150mm")
    (x0, y0), (x1, y1) = _anchor_corners(root)
    # 150mm / 1200uu = 0.125 mm/uu -> 5mm margin = 40uu
    assert (x0, y0) == (-40.0, -40.0)
    assert (x1, y1) == (1240.0, 840.0)


def test_add_frame_anchor_is_first_and_manual_stitch():
    root = _svg_root('<g id="color0_x"><path id="c0_0" d="M 10,10 H 20" fill="#112233"/></g>')
    _add_frame_anchor(root)
    first = root[0]
    assert first.get("id") == "frame_anchor"
    paths = first.findall(f"{{{_SVG_NS}}}path")
    assert len(paths) == 2
    for p in paths:
        assert p.get(f"{{{_INK_NS}}}stroke_method") == "manual_stitch"
    # both anchor nodes must be strictly outside the canvas on their side
    d0, d1 = paths[0].get("d"), paths[1].get("d")
    assert d0.startswith("M -40.000,-40.000")
    assert d1.startswith("M 1240.000,840.000")


def test_pick_anchor_colour_avoids_design_colours():
    used = stitches._ANCHOR_COLOURS[0]
    root = _svg_root(f'<g><path d="M 0,0 H 1" fill="{used}"/></g>')
    assert _pick_anchor_colour(root) == stitches._ANCHOR_COLOURS[1]


# --------------------------------------------------------------------------- #
# anchor strip
# --------------------------------------------------------------------------- #
def test_strip_anchor_block_removes_first_block_and_thread():
    pat = _pattern(
        [0x010101, 0x112233],
        [
            [-500, -500, pe.STITCH], [-490, -490, pe.STITCH],   # anchor block
            [0, 0, pe.COLOR_CHANGE],
            [10, 10, pe.STITCH], [20, 20, pe.STITCH],           # real group
            [20, 20, pe.END],
        ],
    )
    out = _strip_anchor_block(pat)
    assert [t.color & 0xFFFFFF for t in out.threadlist] == [0x112233]
    cmds = [(s[0], s[1], s[2] & 0xFF) for s in out.stitches]
    assert cmds == [(10, 10, pe.STITCH & 0xFF), (20, 20, pe.STITCH & 0xFF),
                    (20, 20, pe.END & 0xFF)]


def test_strip_anchor_block_none_when_only_anchor():
    # no colour change at all -> the group produced nothing but the anchor
    pat = _pattern([0x010101], [[0, 0, pe.STITCH], [1, 1, pe.STITCH], [1, 1, pe.END]])
    assert _strip_anchor_block(pat) is None
    # colour change present but no real stitches after it
    pat = _pattern([0x010101, 0x112233],
                   [[0, 0, pe.STITCH], [0, 0, pe.COLOR_CHANGE], [0, 0, pe.END]])
    assert _strip_anchor_block(pat) is None


# --------------------------------------------------------------------------- #
# merge / rejoin
# --------------------------------------------------------------------------- #
def test_merge_patterns_keeps_order_threads_and_colour_changes():
    a = _pattern([0x112233], [[0, 0, pe.STITCH], [10, 0, pe.STITCH], [10, 0, pe.END]])
    b = _pattern([0x445566], [[50, 50, pe.STITCH], [60, 50, pe.STITCH], [60, 50, pe.END]])
    merged = _merge_patterns([a, b])
    assert [t.color & 0xFFFFFF for t in merged.threadlist] == [0x112233, 0x445566]
    cmds = [s[2] & 0xFF for s in merged.stitches]
    assert cmds.count(pe.COLOR_CHANGE & 0xFF) == 1           # one change between groups
    assert cmds.count(pe.END & 0xFF) == 1                    # single END at the end
    assert cmds[-1] == pe.END & 0xFF
    # absolute coordinates untouched
    assert [s[:2] for s in merged.stitches if (s[2] & 0xFF) == (pe.STITCH & 0xFF)] == \
        [[0, 0], [10, 0], [50, 50], [60, 50]]


def test_concat_same_colour_joins_halves_with_trim_one_thread():
    fills = _pattern([0x112233], [[0, 0, pe.STITCH], [10, 0, pe.STITCH], [10, 0, pe.END]])
    satins = _pattern([0x112233], [[5, 5, pe.STITCH], [15, 5, pe.STITCH], [15, 5, pe.END]])
    out = _concat_same_colour(fills, satins)
    assert len(out.threadlist) == 1
    cmds = [s[2] & 0xFF for s in out.stitches]
    assert cmds.count(pe.COLOR_CHANGE & 0xFF) == 0
    assert cmds.count(pe.END & 0xFF) == 0                    # merge adds the final END later
    assert cmds.count(pe.TRIM & 0xFF) == 1                   # a trim separates the halves
    # either half may be missing
    assert _concat_same_colour(fills, None) is fills
    assert _concat_same_colour(None, satins) is satins


# --------------------------------------------------------------------------- #
# degraded-retry SVG rewrites
# --------------------------------------------------------------------------- #
def _anchored_mini(tmp_path):
    body = (
        '<g id="frame_anchor">'
        '<path id="frame_anchor_0" d="M -40,-40 L -32,-32" style="fill:none;stroke:#010101" '
        'inkstitch:stroke_method="manual_stitch"/>'
        '<path id="frame_anchor_1" d="M 1240,840 L 1232,832" style="fill:none;stroke:#010101" '
        'inkstitch:stroke_method="manual_stitch"/></g>'
        '<g id="color0_x">'
        '<path id="c0_0" d="M 10,10 H 100 V 100 H 10 Z" fill="#112233" '
        'inkstitch:row_spacing_mm="0.4" inkstitch:fill_underlay="True" '
        'inkstitch:pull_compensation_mm="0.2"/>'
        '<path id="c0_0_1" d="M 20,20 L 80,80" style="fill:none;stroke:#112233" '
        'inkstitch:satin_column="true" inkstitch:pull_compensation_mm="0.2"/></g>'
    )
    mini = tmp_path / "mini_grp0.svg"
    mini.write_bytes(etree.tostring(_svg_root(body), xml_declaration=True))
    return mini


def test_split_fills_satins_partitions_and_keeps_anchor(tmp_path):
    mini = _anchored_mini(tmp_path)
    fills_svg, satins_svg = _split_fills_satins(mini)
    assert fills_svg is not None and satins_svg is not None

    froot = etree.parse(str(fills_svg)).getroot()
    ids = [p.get("id") for p in froot.iter(f"{{{_SVG_NS}}}path")]
    assert "c0_0" in ids and "c0_0_1" not in ids
    assert "frame_anchor_0" in ids and "frame_anchor_1" in ids

    sroot = etree.parse(str(satins_svg)).getroot()
    ids = [p.get("id") for p in sroot.iter(f"{{{_SVG_NS}}}path")]
    assert "c0_0_1" in ids and "c0_0" not in ids
    assert "frame_anchor_0" in ids and "frame_anchor_1" in ids


def test_split_fills_satins_none_when_one_sided(tmp_path):
    body = (
        '<g id="color0_x"><path id="c0_0" d="M 10,10 H 100 V 100 H 10 Z" fill="#112233" '
        'inkstitch:row_spacing_mm="0.4"/></g>'
    )
    mini = tmp_path / "mini_grp1.svg"
    mini.write_bytes(etree.tostring(_svg_root(body), xml_declaration=True))
    fills_svg, satins_svg = _split_fills_satins(mini)
    assert fills_svg is not None
    assert satins_svg is None                               # nothing to split


def test_write_fill_variant_touches_only_fills(tmp_path):
    mini = _anchored_mini(tmp_path)
    dst = tmp_path / "pc0nou.svg"
    _write_fill_variant(mini, dst, pull_comp0=True, underlay_off=True)
    root = etree.parse(str(dst)).getroot()
    by_id = {p.get("id"): p for p in root.iter(f"{{{_SVG_NS}}}path")}
    assert by_id["c0_0"].get(f"{{{_INK_NS}}}fill_underlay") == "False"
    assert by_id["c0_0"].get(f"{{{_INK_NS}}}pull_compensation_mm") == "0"
    # satin column keeps its params untouched (its pull-comp is satin pull-comp)
    assert by_id["c0_0_1"].get(f"{{{_INK_NS}}}fill_underlay") is None
    assert by_id["c0_0_1"].get(f"{{{_INK_NS}}}pull_compensation_mm") == "0.2"
