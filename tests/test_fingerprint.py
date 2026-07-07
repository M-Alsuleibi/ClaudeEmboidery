"""Tests for the stitch-type classifier in fingerprint._block_kind.

Focus: the Auto-Split satin recovery (Reference Manual p1197 / wilcom-manual-rules.md).
A wide satin column whose rail-to-rail stitch is split into co-linear sub-stitches must
still classify as 'satin' even though its per-vertex reversal fraction drops below 35%;
a genuine wide tatami fill (long rows) must stay 'fill'. Pure geometry, no Ink-Stitch.
"""

from __future__ import annotations

from wilcom_pipeline.fingerprint import _block_kind

_UNIT = 10.0  # stitch units per mm (1 unit = 0.1 mm), so mm -> units for building points


def _slanted_rows(span_mm, height_mm, steps, spacing_mm=0.4):
    """Back-and-forth rows across `span_mm`, each row slightly slanted so consecutive rows
    are anti-parallel (a >120 deg reversal at each row end). `steps` co-linear points per
    row -> steps=1 is a single crossing (unsplit satin), steps>1 splits it (Auto Split for
    satin; multi-stitch rows for tatami). The row's along-span length is the rail-to-rail
    crossing distance the classifier keys on."""
    pts, y, left = [], 0.0, True
    pts.append((0.0, 0.0))
    while y < height_mm:
        x0 = 0.0 if left else span_mm
        x1 = span_mm if left else 0.0
        for k in range(1, steps + 1):
            t = k / steps
            pts.append(((x0 + (x1 - x0) * t) * _UNIT, (y + spacing_mm * t) * _UNIT))
        y += spacing_mm
        left = not left
    return pts


def _satin_column(width_mm, length_mm, splits=0):
    """Narrow satin ribbon: crossings of `width_mm`, `splits` co-linear split points each."""
    return _slanted_rows(width_mm, length_mm, steps=splits + 1)


def _tatami_fill(width_mm, height_mm, stitch_mm=3.0):
    """Wide tatami: rows spanning `width_mm` built from ~stitch_mm run stitches."""
    return _slanted_rows(width_mm, height_mm, steps=max(round(width_mm / stitch_mm), 1))


def test_unsplit_narrow_satin_is_satin():
    kind, _, _ = _block_kind(_satin_column(2.5, 30.0, splits=0))
    assert kind == "satin"


def test_autosplit_wide_satin_recovered_as_satin():
    # 6 mm column split into 3 co-linear pieces per crossing: reversal fraction ~1/4,
    # which the old >35% rule would have called fill/mixed.
    kind, _, _ = _block_kind(_satin_column(6.0, 40.0, splits=2))
    assert kind == "satin"


def test_wide_tatami_stays_fill():
    # 40 mm-wide region, 3 mm rows: reversals a full row apart -> not a narrow ribbon.
    kind, _, _ = _block_kind(_tatami_fill(40.0, 30.0))
    assert kind == "fill"
