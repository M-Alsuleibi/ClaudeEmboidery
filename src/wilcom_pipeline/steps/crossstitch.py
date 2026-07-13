"""Cross-stitch primitive (step 5) — counted tatreez cross-stitch.

The tatreez category (Palestinian/Levantine *fellahi* tatreez) is NOT run/satin/tatami:
it is **counted cross-stitch** — a fixed square grid where each covered cell is an X of
two diagonal stitches. No amount of fill/satin reproduces that counted-thread look, so
this module is a distinct stitch generator selected by `--cross-stitch` (AUTO for a
`CROSS_STITCH_CATEGORIES` category).

It builds the VP3 **directly with pyembroidery** rather than going through Ink-Stitch:
the exact needle penetrations are known, so there is nothing to trace; and Ink-Stitch's
`manual_stitch` (the only way to emit exact nodes through it) *hangs* the router on a
dense qabbeh (measured: a 6-node manual path never returned in 280 s). Building the
stitches here is exact, fast, and needs no Ink-Stitch binary. Thread cones are still
named downstream in step 6 (`_stamp_thread_metadata` matches each block's RGB to the
thread_map), so this stays consistent with every other category's VP3.

Pipeline fit: consumes `ctx.preprocessed_image` (step 2 palette-quantised RGBA) +
`ctx.palette` + `ctx.thread_map`; produces `ctx.stitch_pattern`. Sew order = palette
order; each colour's disjoint cell clusters are separated by a TRIM (a Wilcom
Break-Apart boundary), colours by a COLOR_CHANGE. Coordinates follow pyembroidery's
Y-down convention (design top == min Y), so the preview/verify render upright with no
flip — exactly like an Ink-Stitch-read pattern.
"""

from __future__ import annotations

import numpy as np
import pyembroidery as pe
from scipy import ndimage

from ..config import PipelineContext

_UNITS_PER_MM = 10.0  # pyembroidery / VP3 unit = 0.1 mm
_MIN_CELL_PX = 2      # a grid cell must be at least this many pixels to carry an X


def _cell_colours(img: np.ndarray, palette, ph: int, n_rows: int, n_cols: int) -> np.ndarray:
    """(n_rows, n_cols) int grid: each cell's majority palette index, or -1 for a
    background-dominated cell. Vectorised block-mode over the palette-quantised image."""
    H, W = img.shape[:2]
    opaque = img[..., 3] > 128
    pidx = np.full((H, W), -1, np.int16)
    for k, rgb in enumerate(palette):
        m = (opaque & (img[..., 0] == rgb[0]) & (img[..., 1] == rgb[1])
             & (img[..., 2] == rgb[2]))
        pidx[m] = k

    blk = pidx[: n_rows * ph, : n_cols * ph].reshape(n_rows, ph, n_cols, ph)
    K = len(palette)
    counts = np.empty((K, n_rows, n_cols), np.int32)
    for k in range(K):
        counts[k] = (blk == k).sum(axis=(1, 3))
    bg = (blk == -1).sum(axis=(1, 3))
    best = counts.argmax(axis=0)
    colour_total = counts.sum(axis=0)
    return np.where(colour_total > bg, best, -1)  # ink outvotes background => keep the cell


def _order_cells(cells: np.ndarray) -> list[tuple[int, int, bool]]:
    """Serpentine (boustrophedon) order of a component's cells: row by row, alternating
    L->R / R->L so consecutive cells abut (short connectors, no stray travel). Returns
    (row, col, left_to_right) so each X is traversed in the sweep direction."""
    by_row: dict[int, list[int]] = {}
    for r, c in cells:
        by_row.setdefault(int(r), []).append(int(c))
    out: list[tuple[int, int, bool]] = []
    for i, r in enumerate(sorted(by_row)):
        l2r = (i % 2 == 0)
        out += [(r, c, l2r) for c in sorted(by_row[r], reverse=not l2r)]
    return out


def _cell_points(r: int, c: int, l2r: bool, ph: int, upp: float) -> list[tuple[int, int]]:
    """The four penetrations of one cell's X. Both diagonals are drawn ('/' = BL->TR,
    '\\' = TL->BR) with a short edge connector between; the sharp reversals at each corner
    give the high-reversal 'satin-like' stitch character that reads as counted cross-stitch
    (a smooth diagonal run instead would read as a fill — measured satin_frac 100->7). The
    exit corner is the next cell's entry, so abutting cells need no travel."""
    x0, x1 = c * ph, (c + 1) * ph
    y0, y1 = r * ph, (r + 1) * ph
    TL = (round(x0 * upp), round(y0 * upp))
    TR = (round(x1 * upp), round(y0 * upp))
    BL = (round(x0 * upp), round(y1 * upp))
    BR = (round(x1 * upp), round(y1 * upp))
    return [BL, TR, TL, BR] if l2r else [BR, TL, TR, BL]


def build_cross_stitch_pattern(
    ctx: PipelineContext, pitch_mm: float
) -> tuple["pe.EmbPattern", int, int]:
    """Generate a counted cross-stitch VP3 pattern. Returns (pattern, n_cells, n_colours)."""
    img = np.asarray(ctx.preprocessed_image)
    if img.ndim != 3 or img.shape[2] < 4:
        raise ValueError("cross-stitch needs an RGBA preprocessed image")
    H, W = img.shape[:2]
    palette = [tuple(int(c) for c in rgb) for rgb in ctx.palette]
    thread_rgb = [tuple(int(c) for c in m["thread_rgb"]) for m in (ctx.thread_map or [])]
    if len(thread_rgb) < len(palette):  # fall back to the ink colour if a cone is missing
        thread_rgb += palette[len(thread_rgb):]

    mm_per_px = ctx.analysis["size_mm"]["width_mm"] / W
    ph = int(round(pitch_mm / mm_per_px))
    if ph < _MIN_CELL_PX:
        ph = _MIN_CELL_PX
    upp = mm_per_px * _UNITS_PER_MM  # pyembroidery (0.1 mm) units per pixel
    n_rows, n_cols = H // ph, W // ph
    if n_rows == 0 or n_cols == 0:
        raise ValueError("cross-stitch grid pitch larger than the design")

    cell_colour = _cell_colours(img, palette, ph, n_rows, n_cols)
    structure = ndimage.generate_binary_structure(2, 2)  # 8-connectivity

    pat = pe.EmbPattern()
    n_cells = 0
    first_block = True
    for k in range(len(palette)):
        grid = cell_colour == k
        if not grid.any():
            continue
        thread = pe.EmbThread()
        thread.set_color(*thread_rgb[k])
        pat.add_thread(thread)
        if not first_block:
            pat.color_change()
        first_block = False

        labeled, n_comp = ndimage.label(grid, structure=structure)
        for cid in range(1, n_comp + 1):
            cells = np.argwhere(labeled == cid)
            prev = None
            for r, c, l2r in _order_cells(cells):
                # A serpentine row can have GAPS (cells of this colour's connected lattice
                # separated by other colours). Bridging them with a stitch draws a long
                # horizontal travel across the design; instead lift the needle (trim) so each
                # contiguous run is its own piece. Adjacent = Chebyshev distance 1.
                if prev is not None and (abs(r - prev[0]) > 1 or abs(c - prev[1]) > 1):
                    pat.trim()
                for x, y in _cell_points(r, c, l2r, ph, upp):
                    # add_stitch_absolute (not stitches.append) so pyembroidery tracks the
                    # needle position — else trim()/color_change()/end() land at (0,0).
                    pat.add_stitch_absolute(pe.STITCH, x, y)
                prev = (r, c)
            pat.trim()  # each cell cluster is its own Break-Apart piece
            n_cells += len(cells)
    pat.end()
    return pat, n_cells, len(pat.threadlist)
