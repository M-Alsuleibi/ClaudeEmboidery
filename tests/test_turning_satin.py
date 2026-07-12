"""Tests for contour-following "turning satin" (stitches._turning_satin_lines).

Pure geometry — no Ink-Stitch binary needed. A broad satin-lean region is covered by
onion-peel rings whose rails follow the region boundary (iso-contours of the distance
field), so irregular/blobby shapes keep clean edges instead of the straight parallel
strips' stepped ones.
"""

from __future__ import annotations

import numpy as np
from lxml import etree
from scipy import ndimage

from wilcom_pipeline.steps import stitches
from wilcom_pipeline.steps.stitches import (
    _iso_contours,
    _min_dist_to_segments,
    _path_segments,
    _rdp,
    _turning_satin_lines,
)

_SVG = "http://www.w3.org/2000/svg"


def _path(d: str):
    e = etree.Element(f"{{{_SVG}}}path")
    e.set("d", d)
    return e


def _rect(w, h):
    return _path(f"M 0,0 {w},0 {w},{h} 0,{h} 0,0")


def _lshape(a=40, t=14):
    # an L: outer corner shapes where straight strips step badly
    return _path(f"M 0,0 {a},0 {a},{t} {t},{t} {t},{a} 0,{a} 0,0")


def _boundary_dist(poly_el, pts):
    A, B = _path_segments(poly_el.get("d"))
    return _min_dist_to_segments(np.asarray(pts, float), A, B)


# --------------------------------------------------------------------------- #
# marching squares
# --------------------------------------------------------------------------- #
def test_iso_contours_of_a_disk_are_one_circle():
    mask = np.zeros((61, 61), bool)
    yy, xx = np.mgrid[0:61, 0:61]
    mask[(xx - 30) ** 2 + (yy - 30) ** 2 <= 25**2] = True
    D = ndimage.distance_transform_edt(mask)
    rings = _iso_contours(D, 10.0)          # 10px inside a 25px disk -> circle r~15
    assert len(rings) == 1
    ring = rings[0]
    assert np.allclose(ring[0], ring[-1])   # closed loop
    r = np.hypot(ring[:, 0] - 30, ring[:, 1] - 30)
    assert abs(r.mean() - 15.0) < 1.5
    assert r.std() < 1.0                    # actually round, not stepped


def test_iso_contours_empty_when_level_above_field():
    D = np.zeros((10, 10))
    assert _iso_contours(D, 1.0) == []


def test_rdp_drops_collinear_keeps_corners():
    line = np.array([[0, 0], [1, 0], [2, 0], [3, 0], [3, 1], [3, 2]], float)
    out = _rdp(line, 0.1)
    assert [tuple(p) for p in out] == [(0, 0), (3, 0), (3, 2)]


# --------------------------------------------------------------------------- #
# turning satin rings
# --------------------------------------------------------------------------- #
def test_broad_rect_peels_into_nested_rings():
    # ring mode (spiral=False): the raw onion-peel geometry the spiral is built from
    lines = _turning_satin_lines(_rect(40, 20), mm_per_uu=1.0, strip_mm=3.0, spiral=False)
    assert len(lines) >= 2                  # 10mm half-depth / 3mm strips -> >= 2 rings
    for pts in lines:
        assert pts.shape[1] == 2 and len(pts) >= 4
    # outermost ring follows the boundary at half a step, everywhere (clean edge)
    d0 = _boundary_dist(_rect(40, 20), lines[0])
    assert d0.max() < 3.0                   # never further than one strip
    assert d0.min() > 0.2                   # and never ON the boundary (it's a centerline)


def test_rings_follow_a_non_convex_contour():
    # the L-shape's inner corner: straight strips step across it; turning satin must
    # stay inside the region and keep hugging the boundary around the notch
    poly = _lshape()
    lines = _turning_satin_lines(poly, mm_per_uu=1.0, strip_mm=3.0)
    outer = lines[0]
    d = _boundary_dist(poly, outer)
    assert d.min() < 3.0                    # follows the contour into/around the notch
    # every point stays strictly inside the L (never crosses the notch)
    for pts in lines:
        for x, y in pts[:: max(1, len(pts) // 50)]:
            inside_arm_h = (0 <= x <= 40) and (0 <= y <= 14)
            inside_arm_v = (0 <= x <= 14) and (0 <= y <= 40)
            assert inside_arm_h or inside_arm_v


# --------------------------------------------------------------------------- #
# spiral chaining (one continuous column instead of one per ring)
# --------------------------------------------------------------------------- #
def _no_proper_self_intersection(pts):
    """Brute-force check that no two non-adjacent segments of the polyline cross."""
    from wilcom_pipeline.steps.stitches import _segments_cross
    n = len(pts) - 1
    for i in range(n):
        # skip the 2 neighbouring segments on each side (shared endpoints)
        A = np.array([pts[j] for j in range(n) if abs(j - i) > 1])
        B = np.array([pts[j + 1] for j in range(n) if abs(j - i) > 1])
        if len(A) and _segments_cross(pts[i], pts[i + 1], A, B):
            return False
    return True


def test_rect_spirals_into_one_polyline():
    # spiral=True: valid geometry, kept for reference — NOT sewable as one column
    # (Ink-Stitch rail pairing degenerates when touching turns graze; see
    # _stagger_ring_seams). Emission uses staggered rings instead.
    rings = _turning_satin_lines(_rect(40, 20), mm_per_uu=1.0, strip_mm=3.0, spiral=False)
    spiral = _turning_satin_lines(_rect(40, 20), mm_per_uu=1.0, strip_mm=3.0, spiral=True)
    assert len(spiral) == 1                  # all rings chained into one column
    pts = spiral[0]

    def arclen(p):
        seg = np.diff(p, axis=0)
        return float(np.hypot(seg[:, 0], seg[:, 1]).sum())

    # nothing was lost: the spiral is nearly as long as all rings together (the rings
    # carry a seam-overshoot lap the spiral doesn't, hence the slack)
    assert arclen(pts) > 0.75 * sum(arclen(r) for r in rings)
    assert _no_proper_self_intersection(pts)


def test_spiral_monotonically_deepens():
    # sample the distance-to-boundary along the spiral: the per-ring average depth
    # must increase ring by ring (outermost first, inward last)
    poly = _rect(40, 20)
    spiral = _turning_satin_lines(poly, mm_per_uu=1.0, strip_mm=3.0, spiral=True)[0]
    d = _boundary_dist(poly, spiral)
    third = len(d) // 3
    assert d[:third].mean() < d[-third:].mean()      # start shallow, end deep


def test_wavy_blob_spiral_no_self_intersection():
    # the acceptance fixture shape (wavy disc) — the spiral must chain cleanly
    import numpy as _np
    ang = _np.linspace(0, 2 * _np.pi, 73)[:-1]
    rad = 22 + 2.2 * _np.sin(3 * ang) + 1.0 * _np.cos(5 * ang)
    pts = _np.stack([25 + rad * _np.cos(ang), 25 + rad * _np.sin(ang)], axis=1)
    d = "M " + " ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + f" {pts[0][0]:.2f},{pts[0][1]:.2f}"
    poly = _path(d)
    spiral = _turning_satin_lines(poly, mm_per_uu=1.0, strip_mm=3.0, spiral=True)
    assert len(spiral) == 1
    assert _no_proper_self_intersection(spiral[0])


def test_spiral_seam_sits_on_a_straight_stretch():
    from wilcom_pipeline.steps.stitches import _straightest_vertex
    # a rounded shape with one long flat edge: the seam vertex starts the longest edge
    pts = np.array([[0, 0], [40, 0], [42, 5], [40, 10], [20, 12], [0, 10]], float)
    assert _straightest_vertex(pts) == 0     # the 40-long bottom edge


def test_thin_region_yields_no_rings():
    # thinner than half a strip everywhere -> nothing to peel (caller falls back)
    assert _turning_satin_lines(_rect(40, 2), mm_per_uu=1.0, strip_mm=3.0) == []


def test_tiny_region_yields_no_rings():
    assert _turning_satin_lines(_rect(1, 1), mm_per_uu=1.0, strip_mm=3.0) == []


def test_straight_strips_still_available_as_fallback():
    lines = stitches._satin_strip_lines(_rect(40, 20), mm_per_uu=1.0, strip_mm=3.0)
    assert len(lines) >= 4
    (p0, p1) = lines[0]
    assert len(p0) == 2 and len(p1) == 2


# --------------------------------------------------------------------------- #
# branch-junction mitres (--branch-satin): columns overlap where they meet
# --------------------------------------------------------------------------- #
def _centerline(d):
    e = etree.Element(f"{{{_SVG}}}path")
    e.set("d", d)
    e.set("style", "fill:none;stroke:#000")
    return e


def _mitre_fixture(n_branches, poly_w=40.0):
    # n branches meeting at (20,20) inside a 40x40 region
    from wilcom_pipeline.steps.stitches import _mitre_branch_junctions
    import numpy as _np
    lines = []
    for k in range(n_branches):
        a = 2 * _np.pi * k / n_branches
        x, y = 20 + 15 * _np.cos(a), 20 + 15 * _np.sin(a)
        lines.append(_centerline(f"M {x:.2f},{y:.2f} 20,20"))   # ends AT the junction
    poly = _path(f"M 0,0 {poly_w},0 {poly_w},{poly_w} 0,{poly_w} 0,0")
    n = _mitre_branch_junctions(lines, poly, mm_per_uu=1.0)
    return lines, n


def _last_pt(el):
    import re as _re
    x, y = _re.findall(r"(-?\d+\.?\d*),(-?\d+\.?\d*)", el.get("d"))[-1]
    return float(x), float(y)


def test_mitre_extends_each_branch_past_the_junction():
    lines, n = _mitre_fixture(3)
    assert n == 3                                    # every end extended once
    for el in lines:
        x, y = _last_pt(el)
        d = np.hypot(x - 20, y - 20)
        # extension = local half-width clamped to <= 2mm; junction is 20 from the
        # boundary of the 40x40 rect, so the clamp must have engaged at 2.0
        assert 1.9 < d < 2.1
        # and it extends PAST the junction along the branch direction (outward)
        assert d > 0


def test_mitre_extension_is_clamped_low_too():
    # region only 2mm wide around the junction -> half-width ~1 -> clamped to >= 0.5
    from wilcom_pipeline.steps.stitches import _mitre_branch_junctions
    lines = [_centerline("M 5,1 20,1"), _centerline("M 35,1 20,1")]
    poly = _path("M 0,0 40,0 40,2 0,2 0,0")
    n = _mitre_branch_junctions(lines, poly, mm_per_uu=1.0)
    assert n == 2
    for el in lines:
        x, y = _last_pt(el)
        assert 0.4 <= np.hypot(x - 20, y - 1) <= 1.1     # ~local half-width (1), >= min


def test_mitre_skips_dense_hubs():
    lines, n = _mitre_fixture(5)                     # 5 ends in one cluster > max 4
    assert n == 0
    for el in lines:
        assert _last_pt(el) == (20.0, 20.0)          # untouched


def test_mitre_ignores_far_apart_ends():
    from wilcom_pipeline.steps.stitches import _mitre_branch_junctions
    lines = [_centerline("M 0,0 10,0"), _centerline("M 30,0 40,0")]  # no shared junction
    poly = _path("M 0,-5 40,-5 40,5 0,5 0,-5")
    assert _mitre_branch_junctions(lines, poly, mm_per_uu=1.0) == 0


def test_default_rings_have_staggered_seams():
    # emission default: separate rings whose seams DRIFT ~1.5 steps ring to ring —
    # close enough for the travel planner to chain them, never radially aligned
    rings = _turning_satin_lines(_rect(40, 20), mm_per_uu=1.0, strip_mm=3.0)
    assert len(rings) >= 2
    for a, b in zip(rings, rings[1:]):
        d = np.hypot(*(b[0] - a[0]))
        assert 1.0 < d <= 12.0        # staggered (not aligned) but within travel budget
