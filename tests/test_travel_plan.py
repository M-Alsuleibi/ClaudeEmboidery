"""Tests for travel planning (stitches._plan_travel helpers).

Production sews near-continuously (pink-goku: 0 trims); the planner chains each colour's
pieces, steers fill entry/exit via Ink-Stitch's starting_point/ending_point object
commands (probed: they snap to the target's nearest boundary point), and drops trim_after
ONLY where the straight travel is short and covered by later-sewn stitching or the
colour's own regions — the cover law. Pure geometry; no binary needed.
"""

from __future__ import annotations

import numpy as np
from lxml import etree

from wilcom_pipeline.steps.stitches import (
    _TRAVEL_COVER_MIN,
    _chain_units,
    _closest_pair,
    _group_pieces,
    _load_command_symbols,
    _piece_endpoints,
    _segment_covered,
)

_SVG = "http://www.w3.org/2000/svg"
_INK = "http://inkstitch.org/namespace"


def _group(paths_xml: str):
    return etree.fromstring(
        f'<g xmlns="{_SVG}" xmlns:inkstitch="{_INK}" id="color0_x">{paths_xml}</g>'
    )


def _rect_xml(pid, x, y, w=10, h=10, extra=""):
    return (f'<path id="{pid}" d="M {x},{y} {x + w},{y} {x + w},{y + h} {x},{y + h} '
            f'{x},{y}" fill="#112233" inkstitch:row_spacing_mm="0.4" '
            f'inkstitch:trim_after="True" {extra}/>')


# --------------------------------------------------------------------------- #
# chaining
# --------------------------------------------------------------------------- #
def test_chain_orders_nearest_neighbour():
    # doc order A(0), C(far), B(near A): the chain must visit A -> B -> C
    g = _group(_rect_xml("A", 0, 0) + _rect_xml("C", 100, 0) + _rect_xml("B", 20, 0))
    pieces = _chain_units(_group_pieces(g))
    assert [p["el"].get("id") for p in pieces] == ["A", "B", "C"]


def test_chain_keeps_border_bonded_to_its_fill():
    # B's border must ride with B even when the chain reorders around it
    g = _group(
        _rect_xml("A", 0, 0)
        + _rect_xml("C", 100, 0)
        + _rect_xml("B", 20, 0)
        + '<path id="Bb" d="M 21,1 29,1 29,9 21,9 21,1" '
          'style="fill:none;stroke:#112233" inkstitch:satin_column="true" '
          'inkstitch:trim_after="True" data-wilcom-border="1"/>'
    )
    pieces = _chain_units(_group_pieces(g))
    order = [p["el"].get("id") for p in pieces]
    # bonding: the border is in the same unit as the path preceding it in doc order
    assert order.index("Bb") == order.index("B") + 1


def test_closest_pair_is_symmetric_minimum():
    P = np.array([[0.0, 0.0], [10.0, 0.0]])
    Q = np.array([[13.0, 4.0], [50.0, 50.0]])
    p, q, d = _closest_pair(P, Q)
    assert tuple(p) == (10.0, 0.0) and tuple(q) == (13.0, 4.0)
    assert abs(d - 5.0) < 1e-9


# --------------------------------------------------------------------------- #
# entry/exit endpoints
# --------------------------------------------------------------------------- #
def test_fill_endpoints_steer_toward_neighbours():
    g = _group(_rect_xml("A", 0, 0) + _rect_xml("B", 20, 0))
    pieces = _group_pieces(g)
    prev_exit = np.array([-5.0, 5.0])                    # something to A's left
    entry, exit_ = _piece_endpoints(pieces[0], prev_exit, pieces[1]["pts"])
    assert entry[0] == 0.0                               # entry on A's left side
    assert exit_[0] == 10.0                              # exit on A's right side (toward B)


def test_run_endpoints_are_path_ends():
    g = _group('<path id="r" d="M 0,0 5,5 9,0" style="fill:none;stroke:#112233" '
               'inkstitch:stroke_method="running_stitch" inkstitch:trim_after="True"/>')
    pieces = _group_pieces(g)
    entry, exit_ = _piece_endpoints(pieces[0], None, None)
    assert tuple(entry) == (0.0, 0.0) and tuple(exit_) == (9.0, 0.0)


def test_border_ring_exits_at_its_seam():
    g = _group('<path id="b" d="M 1,1 9,1 9,9 1,9 1,1" style="fill:none;stroke:#112233" '
               'inkstitch:satin_column="true" data-wilcom-border="1"/>')
    pieces = _group_pieces(g)
    entry, exit_ = _piece_endpoints(pieces[0], None, None)
    assert tuple(entry) == (1.0, 1.0) and tuple(exit_) == (1.0, 1.0)   # closed ring seam


# --------------------------------------------------------------------------- #
# the cover law
# --------------------------------------------------------------------------- #
def test_segment_covered_fraction():
    cover = np.zeros((20, 40), bool)
    cover[:, :20] = True                                 # left half covered
    origin = np.array([0.0, 0.0])
    frac = _segment_covered(np.array([0.0, 10.0]), np.array([39.0, 10.0]),
                            cover, origin, 1.0)
    assert 0.45 < frac < 0.60                            # ~half the segment covered
    assert _segment_covered(np.array([0.0, 10.0]), np.array([19.0, 10.0]),
                            cover, origin, 1.0) == 1.0
    assert _segment_covered(np.array([21.0, 10.0]), np.array([39.0, 10.0]),
                            cover, origin, 1.0) == 0.0
    assert _TRAVEL_COVER_MIN > 0.5                       # half-covered must NOT pass


def test_command_symbols_load_from_vendor_bundle():
    syms = _load_command_symbols()
    if syms is None:                                     # vendor bundle absent -> planner off
        return
    assert set(syms) == {"inkstitch_starting_point", "inkstitch_ending_point"}
