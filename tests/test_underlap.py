"""Tests for underlap (trace._underlap_masks + the seam it closes).

Production objects overlap: an earlier-sewn fill extends UNDER its later-sewn neighbour
so fabric pull can't open a white gap at the seam. The pure tests cover the mask logic
(who gains, who must never be touched); the binary-gated test measures the actual stitch
coverage in the seam band of a two-colour abutting design.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from wilcom_pipeline.steps.trace import _palette_masks, _underlap_masks

PAL = [(10, 20, 30), (200, 50, 50), (50, 200, 50)]


def _img(shape=(40, 60)):
    """Transparent RGBA canvas + painter."""
    arr = np.zeros((*shape, 4), np.uint8)

    def paint(sl, idx):
        arr[sl] = (*PAL[idx], 255)
    return arr, paint


def test_earlier_colour_gains_only_into_later_pixels():
    arr, paint = _img()
    paint(np.s_[10:30, 5:30], 0)     # left block, sewn first
    paint(np.s_[10:30, 30:55], 1)    # right block, sewn second -> shared seam at x=30
    masks = _palette_masks(Image.fromarray(arr), PAL)
    out = _underlap_masks(masks, order=[0, 1], r_px=3)

    assert set(out) == {0}                                  # only the earlier colour grew
    grown = out[0] & ~masks[0]
    assert grown.any()
    assert (grown & ~masks[1]).sum() == 0                   # ...and ONLY into colour 1
    assert grown[:, 30:34].any() and not grown[:, 35:].any()  # ~r_px past the seam
    # the later colour's mask is never touched (it isn't even in the result)
    assert 1 not in out


def test_background_and_transparent_holes_are_never_claimed():
    arr, paint = _img()
    paint(np.s_[5:35, 5:30], 0)      # ring colour...
    arr[15:25, 12:22] = 0            # ...with a transparent hole (an opened counter)
    paint(np.s_[5:35, 30:55], 1)     # later neighbour on the right
    im = Image.fromarray(arr)
    masks = _palette_masks(im, PAL)
    out = _underlap_masks(masks, order=[0, 1], r_px=3)

    assert 0 in out
    assert not out[0][15:25, 12:22].any()                   # the hole stays open
    # nothing anywhere grows into transparent pixels
    all_colour = masks[0] | masks[1] | masks[2]
    assert (out[0] & ~all_colour).sum() == 0


def test_sew_order_direction_matters():
    arr, paint = _img()
    paint(np.s_[10:30, 5:30], 0)
    paint(np.s_[10:30, 30:55], 1)
    masks = _palette_masks(Image.fromarray(arr), PAL)
    # flip the sew order: now colour 1 sews first and IT gains under colour 0
    out = _underlap_masks(masks, order=[1, 0], r_px=3)
    assert set(out) == {1}
    assert ((out[1] & ~masks[1]) & masks[0]).any()


def test_r_zero_disables():
    arr, paint = _img()
    paint(np.s_[10:30, 5:30], 0)
    paint(np.s_[10:30, 30:55], 1)
    masks = _palette_masks(Image.fromarray(arr), PAL)
    assert _underlap_masks(masks, order=[0, 1], r_px=0) == {}


def test_three_colours_chain():
    # 0 sews first, then 1, then 2: 0 may grow under both, 1 only under 2, 2 never.
    arr, paint = _img((40, 90))
    paint(np.s_[10:30, 5:30], 0)
    paint(np.s_[10:30, 30:60], 1)
    paint(np.s_[10:30, 60:85], 2)
    masks = _palette_masks(Image.fromarray(arr), PAL)
    out = _underlap_masks(masks, order=[0, 1, 2], r_px=2)
    assert set(out) == {0, 1}
    assert ((out[1] & ~masks[1]) & masks[2]).any()          # 1 grew under 2
    assert ((out[1] & ~masks[1]) & masks[0]).sum() == 0     # ...but not under earlier 0


# --------------------------------------------------------------------------- #
# end-to-end seam coverage (needs the Ink-Stitch binary)
# --------------------------------------------------------------------------- #
from wilcom_pipeline.steps import stitches as _st  # noqa: E402


@pytest.mark.skipif(not _st.binary_available(), reason="Ink-Stitch binary not vendored")
def test_underlap_closes_the_seam_and_leaves_later_colour_alone(tmp_path):
    import pyembroidery as pe
    from wilcom_pipeline.config import PipelineConfig, PipelineContext
    from wilcom_pipeline.steps import analyze, preprocess, thread_match, trace

    arr = np.full((200, 320, 3), 255, np.uint8)
    arr[40:160, 30:160] = (20, 40, 130)
    arr[40:160, 160:290] = (210, 40, 40)   # shared seam at x=160
    src = tmp_path / "in.png"
    Image.fromarray(arr).save(src)

    def run_to(step_stitches: bool, underlap: float):
        cfg = PipelineConfig(input_path=src, output_dir=tmp_path / f"o{underlap}",
                             name="s", target_width_mm=80.0, num_colors=2,
                             underlap_mm=underlap)
        ctx = PipelineContext(config=cfg)
        for step in (analyze, preprocess, thread_match, trace):
            step.run(ctx)
        if step_stitches:
            _st.run(ctx)
        return ctx

    # trace-only, underlap off vs on: the LATER colour's paths must be identical
    a = run_to(False, 0.0)
    b = run_to(False, 0.5)
    from lxml import etree
    svg = "http://www.w3.org/2000/svg"

    def group_ds(ctx):
        root = etree.parse(str(ctx.svg_path)).getroot()
        return {g.get("id"): [p.get("d") for p in g.iter(f"{{{svg}}}path")]
                for g in root.iter(f"{{{svg}}}g") if g.get("id")}

    da, db = group_ds(a), group_ds(b)
    assert da.keys() == db.keys()
    # document order = sew order; the LAST group is the later colour -> untouched
    later = list(db)[-1]
    earlier = list(db)[0]
    assert da[later] == db[later]
    assert da[earlier] != db[earlier]                       # the earlier one moved

    # Full runs, underlap off vs on. NOTE the honest seam metric: a rendered tatami fill
    # never covers 100% of any band (inherent ~25% inter-row texture), so "count white
    # pixels in the band" measures texture, not the seam. What fabric pull actually cares
    # about is (a) how far the two colour blocks' STITCHES overlap across the seam — the
    # pull margin — and (b) that no fully-void column exists at the seam.
    off = run_to(True, 0.0)
    on = run_to(True, 0.5)
    ov_off, void_off = _seam_overlap_mm(off.stitch_pattern)
    ov_on, void_on = _seam_overlap_mm(on.stitch_pattern)
    # underlap must widen the stitched overlap by roughly underlap_mm
    assert ov_on - ov_off > 0.3, (ov_off, ov_on)
    assert not void_on                                       # no void column at the seam


def _seam_overlap_mm(pattern):
    """(overlap width mm of the two colour blocks around the seam, void-column present?)"""
    import pyembroidery as pe
    from PIL import ImageDraw

    PXMM = 10
    st = pattern.stitches
    xs = [s[0] for s in st]; ys = [s[1] for s in st]
    x0, y0 = min(xs), min(ys)
    W = int((max(xs) - x0) / 10 * PXMM) + 8
    H = int((max(ys) - y0) / 10 * PXMM) + 8
    blocks, prev = [], None
    im = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(im)
    for x, y, c in st:
        cmd = c & 0xFF
        p = (4 + (x - x0) / 10 * PXMM, 4 + (y - y0) / 10 * PXMM)
        if cmd == (pe.STITCH & 0xFF):
            if prev is not None:
                dr.line([prev, p], fill=255, width=3)
            prev = p
        elif cmd == (pe.COLOR_CHANGE & 0xFF):
            blocks.append(np.asarray(im) > 0)
            im = Image.new("L", (W, H), 0)
            dr = ImageDraw.Draw(im)
            prev = None
        else:
            prev = None
    blocks.append(np.asarray(im) > 0)
    assert len(blocks) == 2
    union = blocks[0] | blocks[1]
    ys_any = np.where(union.any(axis=1))[0]
    yl, yh = ys_any[0] + PXMM, ys_any[-1] - PXMM

    def present(mask):  # x-columns where the block really stitches (not stray zigzag tips)
        return np.where(mask[yl:yh + 1].mean(axis=0) >= 0.3)[0]

    p0, p1 = present(blocks[0]), present(blocks[1])
    lo = max(p0.min(), p1.min())
    hi = min(p0.max(), p1.max())
    overlap_mm = max(0, hi - lo + 1) / PXMM
    mid = W // 2
    void = bool((union[yl:yh + 1, mid - 4:mid + 5].mean(axis=0) < 0.15).any())
    return overlap_mm, void
