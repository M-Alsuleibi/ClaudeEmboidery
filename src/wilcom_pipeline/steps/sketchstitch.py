"""Sketch-stitch primitive (step 5) — fur/feather animal sketch embroidery.

The animals category is NOT run/satin/tatami: production sews these designs as
**sketch stitch** — layered run strokes that follow the fur/feather direction, with
the fabric deliberately showing through (all 1,647 registered ground-truth objects
across the 10 animal pairs are outline-family; zero area fills). No fill algorithm
reproduces that hand-drawn look, so this module is a distinct stitch generator
selected by `--sketch-stitch` (AUTO for a SKETCH_STITCH_CATEGORIES category).

How it draws (calibrated against `animals/pairs/*/_measures.json`):

- A **fur-direction field** is measured from the ORIGINAL artwork (not the flat
  quantized image): the structure tensor of the source luminance, smoothed at ~2 mm,
  gives the local stroke flow the artist drew; where the art is flat (no texture),
  a region falls back to its own principal axis.
- Each colour region is scribbled in ~9 mm **orientation cells**: stroke lines along
  the cell's local fur angle, spaced by the pair prior (~0.95 mm), stitch pitch
  ~2.3 mm (the measured median segment), with endpoint/pitch jitter so strokes read
  hand-drawn rather than machine-ruled.
- Each stroke is sewn **forward - back - forward with a small lateral offset**, the
  way a pen sketches fur: that triple pass layers the thread (density lands in the
  measured 2.3-3.2 st/mm² band), and the sharp 180° turns at the stroke ends give
  the high-reversal character the ground-truth fingerprint reads as "satin" — a
  plain serpentine scanline turns 90° at row ends and reads as a fill (measured:
  satin_frac 4 vs the truth's 92-100).
- A **thin stroke needs no special case**: its rows collapse onto its own axis, so
  linework degenerates to a centerline run naturally. The keyline-detail layer
  (`KEYLINE_DETAIL_RGB`, split by preprocess, sewn last) is emitted as **bean**
  (same triple pass, zero lateral offset) for the drawn-outline weight.

Built **directly with pyembroidery** (like crossstitch.py): exact penetrations are
known, so there is nothing to trace and no Ink-Stitch binary is needed. Cones are
named downstream in step 6 from thread_map. Coordinates are Y-down, matching the
image and pyembroidery's convention. Colour order = palette (coverage) order — the
big base washes sew first, small accents later — with the keyline layer pinned last,
matching the measured production order (base wash -> fur layers -> black sketch ->
highlights).
"""

from __future__ import annotations

import numpy as np
import pyembroidery as pe
from PIL import Image
from scipy import ndimage

from ..config import KEYLINE_DETAIL_RGB, PipelineContext
from ..imaging import load_rgb_alpha

_UNITS_PER_MM = 10.0     # pyembroidery / VP3 unit = 0.1 mm
_STITCH_LEN_MM = 1.7     # calibrated on the fox: puts the fingerprint's satin_w in the
                         # measured band [1.26-1.67] (the pairs' 2.3 block median includes
                         # travel; their satin-block segments run shorter)
_SPACING_FACTOR = 0.75   # rows denser than the per-object prior: production layers the
                         # same cone across repeated stops, which the prior's single-object
                         # row spacing doesn't capture (calibrated into the density band)
_FLICK_MM = 4.2          # a long row is sewn as chained fur FLICKS of this length: short
                         # doubled-back pen strokes put a reversal every couple of stitches,
                         # the closely-spaced-reversal signature the ground truth carries
                         # (fingerprint's split-satin rule) — one long doubled row reads as
                         # a fill instead (measured satin_frac 0.8 vs the truth's 92-100)
_CELL_MM = 9.0           # orientation-cell size: fur flow is piecewise-straight at ~1 cm
_TENSOR_SIGMA_MM = 2.0   # structure-tensor smoothing: the scale fur strokes live at
_MIN_ROW_MM = 1.2        # a scribble row shorter than this is dropped (unsewable stub)
_HOP_MM = 3.0            # rows further apart than this get a trim, not a walked stitch
_JITTER_MM = 0.35        # endpoint jitter: hand-drawn, not machine-ruled
_COHERENCE_MIN = 0.06    # below this the art is flat here -> component-axis fallback
_STROKE_OFFSET_MM = 0.3  # lateral offset of the back/return passes (pen-stroke spread)
_MIN_DETAIL_MM = 0.5     # keyline pieces are short; keep them down to this length
_MIN_COMP_PX = 6         # ignore sub-speck components


def _flow_field(ctx: PipelineContext, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """(theta, coherence) per work pixel: local fur-stroke direction from the source
    art's structure tensor. theta is the FLOW (along-stroke) angle in radians."""
    h, w = shape
    img = Image.open(ctx.config.input_path)
    img.load()
    rgb, _ = load_rgb_alpha(img)
    g = np.asarray(
        Image.fromarray(rgb).convert("L").resize((w, h), Image.LANCZOS), np.float32
    )
    gx = ndimage.sobel(g, axis=1)
    gy = ndimage.sobel(g, axis=0)
    mm_per_px = ctx.analysis["size_mm"]["width_mm"] / w
    sigma = max(1.0, _TENSOR_SIGMA_MM / mm_per_px)
    jxx = ndimage.gaussian_filter(gx * gx, sigma)
    jxy = ndimage.gaussian_filter(gx * gy, sigma)
    jyy = ndimage.gaussian_filter(gy * gy, sigma)
    # dominant GRADIENT orientation (mod pi); the stroke flows perpendicular to it
    phi = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    theta = phi + np.pi / 2.0
    coherence = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy * jxy) / (jxx + jyy + 1e-6)
    return theta.astype(np.float32), coherence.astype(np.float32)


def _component_axis(ys: np.ndarray, xs: np.ndarray) -> float:
    """Principal-axis angle of a pixel set (fallback flow where the art is flat)."""
    x = xs - xs.mean()
    y = ys - ys.mean()
    cxx, cyy, cxy = float((x * x).mean()), float((y * y).mean()), float((x * y).mean())
    return 0.5 * float(np.arctan2(2.0 * cxy, cxx - cyy))


def _cell_angle(theta: np.ndarray, coh: np.ndarray, ys: np.ndarray, xs: np.ndarray,
                fallback: float) -> float:
    """Coherence-weighted circular mean (period pi) of the flow over one cell's pixels."""
    t = theta[ys, xs]
    w = coh[ys, xs]
    s = float((w * np.sin(2.0 * t)).sum())
    c = float((w * np.cos(2.0 * t)).sum())
    if np.hypot(s, c) < _COHERENCE_MIN * max(1, len(ys)):
        return fallback
    return 0.5 * float(np.arctan2(s, c))


def _scribble_rows(ys: np.ndarray, xs: np.ndarray, angle: float, spacing_px: float,
                   min_row_px: float, rng: np.random.Generator) -> list[np.ndarray]:
    """Serpentine scribble rows for one cell's pixel set: bin the pixels into rows
    perpendicular to `angle`, split each row at mask gaps, emit each run as a 2-point
    segment (endpoints jittered) in image coordinates. Alternating direction happens
    at emission time (caller reverses odd rows)."""
    ca, sa = np.cos(angle), np.sin(angle)
    u = xs * ca + ys * sa          # along the stroke
    v = -xs * sa + ys * ca         # across the strokes
    rows: list[np.ndarray] = []
    rv = np.round(v / spacing_px).astype(np.int32)
    order = np.lexsort((u, rv))
    u_s, v_s, rv_s = u[order], v[order], rv[order]
    gap_px = max(2.5, spacing_px)
    start = 0
    for i in range(1, len(u_s) + 1):
        boundary = (i == len(u_s)) or (rv_s[i] != rv_s[start]) or (u_s[i] - u_s[i - 1] > gap_px)
        if not boundary:
            continue
        u0, u1 = u_s[start], u_s[i - 1]
        if u1 - u0 >= min_row_px:
            vc = float(v_s[start:i].mean())
            j0, j1 = rng.uniform(-1, 1, 2)
            rows.append(np.array([[u0 + j0, vc], [u1 + j1, vc]], np.float64))
        start = i
    # back to image coords
    out = []
    for r in rows:
        x = r[:, 0] * ca - r[:, 1] * sa
        y = r[:, 0] * sa + r[:, 1] * ca
        out.append(np.stack([x, y], axis=1))
    return out


def _split_flicks(row: np.ndarray, flick_px: float,
                  rng: np.random.Generator) -> list[np.ndarray]:
    """Split one long row line into chained fur flicks of ~flick_px (±20% jitter).
    Consecutive flicks share their junction point, so the chain sews continuously."""
    p0, p1 = row[0], row[-1]
    length = float(np.hypot(*(p1 - p0)))
    n = max(1, int(round(length / flick_px)))
    if n == 1:
        return [row]
    cuts = np.linspace(0.0, 1.0, n + 1)
    cuts[1:-1] += rng.uniform(-0.2, 0.2, n - 1) / n
    pts = p0[None, :] + cuts[:, None] * (p1 - p0)[None, :]
    return [np.stack([pts[i], pts[i + 1]]) for i in range(n)]


def _line_points(p0, p1, pitch_px: float, rng: np.random.Generator) -> list[tuple[float, float]]:
    """Run penetrations from p0 to p1 at ~pitch with 10% along-line jitter."""
    (x0, y0), (x1, y1) = p0, p1
    length = float(np.hypot(x1 - x0, y1 - y0))
    steps = max(1, int(round(length / pitch_px)))
    xs = np.linspace(x0, x1, steps + 1)
    ys = np.linspace(y0, y1, steps + 1)
    if steps > 1 and length > 0:
        jit = rng.uniform(-0.1, 0.1, steps - 1) * pitch_px
        xs[1:-1] += jit * (x1 - x0) / length
        ys[1:-1] += jit * (y1 - y0) / length
    return list(zip(xs, ys))


def _emit_sketch_stroke(pat: "pe.EmbPattern", pts: np.ndarray, upp: float,
                        pitch_px: float, offset_px: float,
                        rng: np.random.Generator, bean: bool) -> int:
    """Sew one stroke the way a pen sketches fur: forward, back, forward again, the
    return passes laterally offset by ~offset_px (zero for the bean keyline, which
    doubles back exactly on itself). The sharp 180° turns at the stroke ends are the
    high-reversal signature the ground truth carries; the triple pass is the layered
    thread that puts density in the measured band."""
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    length = float(np.hypot(x1 - x0, y1 - y0))
    if length <= 0:
        return 0
    if bean:
        # true bean: the return passes re-enter the SAME penetrations, reinforcing
        # the drawn line the way production sews black sketch outlines
        fwd = _line_points((x0, y0), (x1, y1), pitch_px, rng)
        seq = fwd + fwd[-2::-1] + fwd[1:]
    else:
        # each pass PIVOTS at the shared endpoint and fans out at its far end: the
        # needle turns ~175° in place, which is the reversal the fingerprint (and the
        # fabric) sees. Starting the return pass at a laterally-offset point instead
        # splits the turn into two ~90° jogs and the whole block reads as a fill
        # (measured: rev 3% vs the intended ~35%).
        nx, ny = -(y1 - y0) / length, (x1 - x0) / length   # unit normal
        d1 = offset_px * rng.uniform(0.6, 1.4)
        d2 = -offset_px * rng.uniform(0.6, 1.4)
        seq = (_line_points((x0, y0), (x1, y1), pitch_px, rng)
               + _line_points((x1, y1), (x0 + nx * d1, y0 + ny * d1), pitch_px, rng)[1:]
               + _line_points((x0 + nx * d1, y0 + ny * d1), (x1 + nx * d2, y1 + ny * d2),
                              pitch_px, rng)[1:])
    for x, y in seq:
        pat.add_stitch_absolute(pe.STITCH, round(x * upp), round(y * upp))
    return len(seq)


def build_sketch_pattern(
    ctx: PipelineContext, row_spacing_mm: float
) -> tuple["pe.EmbPattern", int, int]:
    """Generate the sketch-stitch pattern. Returns (pattern, n_strokes, n_colours)."""
    img = np.asarray(ctx.preprocessed_image)
    if img.ndim != 3 or img.shape[2] < 4:
        raise ValueError("sketch-stitch needs an RGBA preprocessed image")
    H, W = img.shape[:2]
    palette = [tuple(int(c) for c in rgb) for rgb in ctx.palette]
    thread_rgb = [tuple(int(c) for c in m["thread_rgb"]) for m in (ctx.thread_map or [])]
    if len(thread_rgb) < len(palette):
        thread_rgb += palette[len(thread_rgb):]

    mm_per_px = ctx.analysis["size_mm"]["width_mm"] / W
    upp = mm_per_px * _UNITS_PER_MM
    spacing_px = max(1.0, row_spacing_mm * _SPACING_FACTOR / mm_per_px)
    pitch_px = max(1.0, _STITCH_LEN_MM / mm_per_px)
    cell_px = max(4, int(round(_CELL_MM / mm_per_px)))
    min_row_px = _MIN_ROW_MM / mm_per_px
    min_detail_px = max(2.0, _MIN_DETAIL_MM / mm_per_px)
    flick_px = _FLICK_MM / mm_per_px
    offset_px = _STROKE_OFFSET_MM / mm_per_px
    hop_px = _HOP_MM / mm_per_px
    jitter_px = _JITTER_MM / mm_per_px
    rng = np.random.default_rng(0)

    theta, coh = _flow_field(ctx, (H, W))
    opaque = img[..., 3] > 128

    # sew order: palette (coverage) order, keyline-detail layer pinned last
    order = sorted(range(len(palette)),
                   key=lambda k: palette[k] == KEYLINE_DETAIL_RGB)
    structure = ndimage.generate_binary_structure(2, 2)

    pat = pe.EmbPattern()
    n_strokes = 0
    first_block = True
    for k in order:
        rgb = palette[k]
        mask = (opaque & (img[..., 0] == rgb[0]) & (img[..., 1] == rgb[1])
                & (img[..., 2] == rgb[2]))
        if not mask.any():
            continue
        bean = rgb == KEYLINE_DETAIL_RGB
        min_len = min_detail_px if bean else min_row_px

        # generate ALL of this colour's strokes first: a colour whose regions are too
        # small/thin to yield a single stroke must not claim a thread block (an empty
        # block fails step 7's all_colours_sewed check)
        pieces: list[list[np.ndarray]] = []   # one stroke list per component
        labeled, _n = ndimage.label(mask, structure=structure)
        for cid, sl in enumerate(ndimage.find_objects(labeled), start=1):
            comp = labeled[sl] == cid
            if int(comp.sum()) < _MIN_COMP_PX:
                continue
            cys, cxs = np.nonzero(comp)
            cys = cys + sl[0].start
            cxs = cxs + sl[1].start
            fallback = _component_axis(cys, cxs)
            strokes: list[np.ndarray] = []
            cell_ids = (cys // cell_px) * (W // cell_px + 2) + (cxs // cell_px)
            for cell in np.unique(cell_ids):
                m = cell_ids == cell
                ys_c, xs_c = cys[m], cxs[m]
                ang = _cell_angle(theta, coh, ys_c, xs_c, fallback)
                rows = _scribble_rows(ys_c, xs_c, ang, spacing_px, min_len, rng)
                for i, r in enumerate(rows):
                    if i % 2:
                        r = r[::-1]
                    r += rng.uniform(-jitter_px, jitter_px, r.shape)
                    strokes.extend(_split_flicks(r, flick_px, rng) if not bean else [r])
            if strokes:
                pieces.append(strokes)
        if not pieces:
            continue

        thread = pe.EmbThread()
        thread.set_color(*thread_rgb[k])
        pat.add_thread(thread)
        if not first_block:
            pat.color_change()
        first_block = False

        for strokes in pieces:
            # sew: walk to the next stroke if close, else trim (Break-Apart piece)
            prev_end = None
            for s in strokes:
                if prev_end is not None:
                    d = float(np.hypot(*(s[0] - prev_end)))
                    if d > hop_px:
                        pat.trim()
                n_strokes += 1
                _emit_sketch_stroke(pat, s, upp, pitch_px, offset_px, rng, bean)
                prev_end = s[-1]
            pat.trim()
    pat.end()
    return pat, n_strokes, len(pat.threadlist)
