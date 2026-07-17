"""Tests for variable-width satin construction + underlay-by-width (stitches._build_vwidth_satin).

Pure geometry — no Ink-Stitch binary needed. Verifies the manual's underlay-by-width rule
(wilcom-manual-rules.md §3): a WIDE satin column (>~3 mm) gets a zigzag underlay; a narrow one
does not (it relies on the center-walk / Center Run).
"""

from __future__ import annotations

from lxml import etree

from wilcom_pipeline.steps import stitches

_SVG = "http://www.w3.org/2000/svg"
_INK = "http://inkstitch.org/namespace"


def _path(d: str):
    e = etree.Element(f"{{{_SVG}}}path")
    e.set("d", d)
    return e


def _straight_center(length=40, step=5, y=10):
    return "M " + " ".join(f"{x},{y}" for x in range(0, length + step, step))


def _rect_boundary(halfw, length=40, y=10):
    # closed rectangle +/- halfw around the centerline y
    lo, hi = y - halfw, y + halfw
    return f"M 0,{lo} {length},{lo} {length},{hi} 0,{hi} 0,{lo}"


def _build(center_d, boundary_d, mm_per_uu=1.0, satin_max_mm=7.0):
    c = _path(center_d)
    ok = stitches._build_vwidth_satin(c, _path(boundary_d), "#000000", mm_per_uu, satin_max_mm)
    return c, ok


def test_builds_a_satin_column():
    c, ok = _build(_straight_center(), _rect_boundary(1.5))
    assert ok is True
    assert c.get(f"{{{_INK}}}satin_column") == "true"
    assert c.get("transform") is None            # rails baked into the root frame
    assert c.get("d").count("M") >= 3            # 2 rails + >=1 rung


def test_wide_column_gets_zigzag_underlay():
    # full width ~5 mm (> 3 mm fixed band) -> zigzag underlay
    c, ok = _build(_straight_center(), _rect_boundary(2.5))
    assert ok and c.get(f"{{{_INK}}}zigzag_underlay") == "true"


def test_narrow_column_has_no_zigzag_underlay():
    # full width ~2 mm (< 3 mm) -> rely on center-walk, no zigzag
    c, ok = _build(_straight_center(), _rect_boundary(1.0))
    assert ok and c.get(f"{{{_INK}}}zigzag_underlay") is None


def test_degenerate_geometry_returns_false():
    c, ok = _build("M 0,0 1,0", _rect_boundary(2.0))  # too few centerline points
    assert ok is False


# --- broad-region satin strip tiling (stitches._satin_strip_lines) ---
def _rect(w, h):
    return _path(f"M 0,0 {w},0 {w},{h} 0,{h} 0,0")


def test_broad_region_tiles_into_satin_strips():
    # a 40x20 mm region banded every 3 mm -> several straight satin-column centerlines
    lines = stitches._satin_strip_lines(_rect(40, 20), mm_per_uu=1.0, strip_mm=3.0)
    assert len(lines) >= 4
    (p0, p1) = lines[0]
    assert len(p0) == 2 and len(p1) == 2          # each strip is a 2-point centerline


def test_tiny_region_yields_no_strips():
    assert stitches._satin_strip_lines(_rect(1, 1), mm_per_uu=1.0, strip_mm=3.0) == []


# --- hairpin splitting (stitches._split_centerline_at_hairpins) ---
def _in_group(d: str):
    g = etree.Element(f"{{{_SVG}}}g")
    p = etree.SubElement(g, f"{{{_SVG}}}path")
    p.set("d", d)
    p.set("id", "cl")
    return p


def test_hairpin_centerline_splits_into_pieces():
    # a 20mm out-and-back U (1mm apart): the 180deg turn at x=20 must cut the
    # centerline in two, or the offset rails fold and the column fans
    fwd = " ".join(f"{x},0" for x in range(0, 21))
    back = " ".join(f"{x},1" for x in range(20, -1, -1))
    p = _in_group("M " + fwd + " " + back)
    pieces = stitches._split_centerline_at_hairpins(p, mm_per_uu=1.0)
    assert len(pieces) == 2
    assert pieces[0] is p and pieces[1].get("id") == "cl_hp1"
    assert pieces[1].getparent() is p.getparent()


def test_straight_centerline_stays_whole():
    p = _in_group(_straight_center())
    assert stitches._split_centerline_at_hairpins(p, mm_per_uu=1.0) == [p]


def test_gentle_curve_stays_whole():
    # a quarter circle r=20mm turns 90deg total but never sharply per chord
    import numpy as np
    ts = np.linspace(0, np.pi / 2, 60)
    d = "M " + " ".join(f"{20*np.cos(t):.2f},{20*np.sin(t):.2f}" for t in ts)
    p = _in_group(d)
    assert stitches._split_centerline_at_hairpins(p, mm_per_uu=1.0) == [p]
