"""Tests for outline objects (stitches._border_centerlines & friends).

Pure geometry — no Ink-Stitch binary needed. Production designs layer satin BORDERS on
top of fills (pink-goku: 217 outline vs 118 fill objects); the border centerline is the
EDT iso-contour at depth w/2, so the satin's outer edge kisses the region boundary and
its inner half overlaps the fill. Holes (letter counters) are bordered too.
"""

from __future__ import annotations

import numpy as np
from lxml import etree

from wilcom_pipeline.steps.stitches import (
    _BORDER_W_MAX_MM,
    _BORDER_W_MIN_MM,
    _border_centerlines,
    _fill_colour,
    _min_dist_to_segments,
    _outline_border_w_mm,
    _path_segments,
    _region_raster,
)

_SVG = "http://www.w3.org/2000/svg"


def _path(d: str, fill: str | None = "#112233"):
    e = etree.Element(f"{{{_SVG}}}path")
    e.set("d", d)
    if fill:
        e.set("fill", fill)
    return e


def _rect(w, h):
    return _path(f"M 0,0 {w},0 {w},{h} 0,{h} 0,0")


def _rect_with_hole(w=40, h=30, hx0=15, hy0=10, hw=10, hh=10):
    return _path(f"M 0,0 {w},0 {w},{h} 0,{h} 0,0 "
                 f"M {hx0},{hy0} {hx0 + hw},{hy0} {hx0 + hw},{hy0 + hh} {hx0},{hy0 + hh} "
                 f"{hx0},{hy0}")


def _ring_boundary_dist(poly_el, ring):
    A, B = _path_segments(poly_el.get("d"))
    return _min_dist_to_segments(np.asarray(ring, float), A, B)


# --------------------------------------------------------------------------- #
# evenodd raster (holes must survive for border extraction)
# --------------------------------------------------------------------------- #
def test_region_raster_evenodd_keeps_the_hole():
    poly = _rect_with_hole()
    filled, _, res = _region_raster(poly, mm_per_uu=1.0)              # default: union
    holed, _, _ = _region_raster(poly, mm_per_uu=1.0, evenodd=True)
    assert filled.sum() > holed.sum()                                 # hole removed area
    # the hole centre is inside for the union raster, outside for evenodd
    # (probe the pixel at the hole's middle)
    def at(mask, x, y):
        return mask[int(y / res) + 2, int(x / res) + 2]               # +2 = raster pad
    assert at(filled, 20, 15)
    assert not at(holed, 20, 15)


# --------------------------------------------------------------------------- #
# border centerlines
# --------------------------------------------------------------------------- #
def test_border_rides_the_boundary_at_half_width():
    poly = _rect(40, 20)
    rings = _border_centerlines(poly, mm_per_uu=1.0, w_mm=2.0)
    assert len(rings) == 1
    ring = rings[0]
    assert np.allclose(ring[0], ring[-1], atol=1e-6)                  # closed loop
    d = _ring_boundary_dist(poly, ring)
    assert abs(d.mean() - 1.0) < 0.5                                  # ~w/2 from boundary
    assert d.max() < 1.8                                              # never wanders inward


def test_hole_gets_its_own_border_ring():
    poly = _rect_with_hole()
    rings = _border_centerlines(poly, mm_per_uu=1.0, w_mm=2.0)
    assert len(rings) == 2                                            # outer + counter
    # one ring must hug the hole: its points all lie near the hole's boundary box
    hole_rings = [r for r in rings
                  if r[:, 0].min() > 10 and r[:, 0].max() < 30
                  and r[:, 1].min() > 5 and r[:, 1].max() < 25]
    assert len(hole_rings) == 1


def test_small_region_gets_no_border():
    assert _border_centerlines(_rect(5, 5), mm_per_uu=1.0, w_mm=2.0) == []   # 25 < 40mm2


def test_region_thinner_than_border_gets_no_border():
    assert _border_centerlines(_rect(50, 1.5), mm_per_uu=1.0, w_mm=2.0) == []


# --------------------------------------------------------------------------- #
# width prior + colour helper
# --------------------------------------------------------------------------- #
def test_border_width_from_category_profile_is_clamped():
    w = _outline_border_w_mm("letters")           # profile med ~2.37 -> inside the clamp
    assert _BORDER_W_MIN_MM <= w <= _BORDER_W_MAX_MM
    assert _outline_border_w_mm("no-such-category") == 2.0
    assert _outline_border_w_mm(None) == 2.0


def test_fill_colour_reads_attr_and_style():
    assert _fill_colour(_path("M 0,0 H 1", fill="#A0B0C0")) == "#A0B0C0"
    styled = _path("M 0,0 H 1", fill=None)
    styled.set("style", "fill:#010203;stroke:none")
    assert _fill_colour(styled) == "#010203"
    assert _fill_colour(_path("M 0,0 H 1", fill="none")) is None


def test_auto_gating_data_holds():
    # run() resolves outline_objects=None as "on iff the category is satin-dominant":
    # anime's ground truth (pink-goku pair) makes it satin-dominant; 3D's shaded solids
    # keep it off. Pin the data the AUTO default depends on.
    from wilcom_pipeline.fingerprint import category_satin_dominant
    assert category_satin_dominant("anime") is True
    assert category_satin_dominant("3D") is False
    assert category_satin_dominant(None) is False
