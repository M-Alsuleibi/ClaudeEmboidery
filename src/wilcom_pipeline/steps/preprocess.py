"""Step 2 - Preprocess.

Consumes ctx.analysis (step 1) and produces a clean, posterised RGBA image plus
the colour palette that the trace + stitch steps build on:

  - reuse analyze's palette and reduce it to config.num_colors by merging the
    *closest* colours in CIELAB (so distinct accents survive while redundant
    shades of one region collapse — area-weighted dropping would lose accents)
  - drop the background to alpha using the mask analyze described (only when the
    background was judged separable; otherwise keep everything and just posterise)
  - snap every foreground pixel to its nearest palette colour in Lab

Writes ctx.preprocessed_image (RGBA, hard-edged) and ctx.palette (RGB tuples,
ordered by realised coverage).

NOTE: annotation-line removal is listed in the goal doc but deferred — it needs
a detection strategy (leader lines / dimension text) and is a no-op here. The
other four jobs (quantise, drop bg, preserve accents, snap) are implemented.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

from ..color import srgb_to_lab
from ..config import PipelineContext
from ..imaging import BG_DELTA_E, background_like, foreground_mask, load_rgb_alpha

# Cap working resolution. Embroidery doesn't need photo-grade detail: at an 80 mm
# design 1200 px is ~15 px/mm, well past machine resolution (~0.1 mm).
_WORK_MAX_DIM = 1200

# Foreground components smaller than this (real-world area) are background noise,
# not stitchable features — drop them after the background is removed.
_MIN_FEATURE_MM2 = 0.5

# Majority-filter neighbourhood (mm) used to collapse dithered specks into solid
# blocks. Bigger = fewer/larger blocks (simpler for the machine), coarser detail.
_CONSOLIDATE_MM = 1.2

# Black-ink snap (snap_black). A pixel is "black ink" (outline/keyline/pupil) when it
# is both very dark (brightest channel below _BLACK_MAX) and near-neutral (chroma below
# _BLACK_CHROMA) — a dark *coloured* element (navy 0,0,89: hi=89; dark teal) fails the
# brightness test and is preserved. Snap only kicks in when at least _BLACK_MIN_FRAC of
# the foreground is such ink, so it's a no-op on art with no black.
_BLACK_MAX = 70
_BLACK_CHROMA = 40
_BLACK_MIN_FRAC = 0.002


def run(ctx: PipelineContext) -> None:
    cfg = ctx.config
    analysis = ctx.analysis
    if not analysis:
        raise RuntimeError("preprocess requires ctx.analysis; run analyze first.")

    img = Image.open(cfg.input_path)
    img.load()
    rgb, alpha = load_rgb_alpha(img)
    rgb, alpha = _downsample(rgb, alpha, _WORK_MAX_DIM)

    bg = analysis["background"]
    if bg.get("is_separable"):
        mask = foreground_mask(rgb, alpha, bg)
        # Drop foreground specks smaller than a stitchable feature: background
        # texture/noise leaves isolated dots that aren't border-connected and
        # would otherwise become hundreds of junk stitches.
        mm_per_px = analysis["size_mm"]["width_mm"] / rgb.shape[1]
        min_px = max(4, round(_MIN_FEATURE_MM2 / (mm_per_px**2)))
        mask = _despeckle(mask, min_px)
        # Open letter counters: foreground_mask keeps only the *border-connected*
        # background, so a page-coloured region enclosed by ink (the hole in e/B/g,
        # the open loop of a script descender) survives as foreground and gets
        # filled solid. For letterforms those counters must read through.
        if cfg.should_open_counters and bg.get("color") is not None:
            mask = _open_counters(mask, rgb, bg["color"])
    else:
        # No clean background to remove — keep every pixel, just posterise.
        mask = np.ones(rgb.shape[:2], dtype=bool)

    n_colors = cfg.resolved_num_colors
    palette = _reduce_palette(analysis["colors"], n_colors)
    if not palette:
        raise RuntimeError("preprocess: analyze found no element colours to quantise.")

    # Reserve one palette slot for pure black when the art has a real black-ink
    # population (outline/keyline/pupils). Rebuild the chromatic palette with one
    # fewer colour and dedicate the freed slot to (0,0,0), then force those pixels
    # onto it below — so a thin anti-aliased outline stays crisp black instead of
    # averaging into a dark brown, without touching the muted colours.
    black_mask = None
    if cfg.snap_black and n_colors >= 2:
        bm = _black_ink_mask(rgb, mask)
        if int(bm.sum()) >= _BLACK_MIN_FRAC * max(1, int(mask.sum())):
            palette = _reduce_palette(analysis["colors"], n_colors - 1)
            if (0, 0, 0) not in palette:
                palette.append((0, 0, 0))
            black_mask = bm

    mm_per_px = analysis["size_mm"]["width_mm"] / rgb.shape[1]
    idx_map = _assign_indices(rgb, mask, palette)
    if black_mask is not None:
        idx_map[black_mask] = palette.index((0, 0, 0))
    if cfg.purify:
        # Refine each representative to the MEDIAN of its assigned source pixels (one
        # Lloyd update) before purifying. _reduce_palette merges by area-weighted
        # average, which drags a colour toward its neighbours: here the teal absorbed
        # gray anti-aliased / satin-sheen edge pixels and drifted light (126,169,169)
        # vs the true ~(90,157,162). The cluster median is the truer brand colour —
        # robust to those edge outliers. Then _purify_ink still snaps the bright
        # primaries to pure (Black/Yellow) while keeping the muted teal verbatim
        # (see letters knowledge §8a). Decoupled from satin dissection via --purify-colors.
        palette = _refine_palette(rgb, idx_map, palette)
        palette = [_purify_ink(c) for c in palette]
    # Consolidate dithered specks into fewer, larger continuous blocks (each
    # block becomes one stitched object downstream — fewer machine trims).
    k = round(_CONSOLIDATE_MM / mm_per_px)
    k = max(3, k + 1 - (k % 2))  # nearest odd >= 3
    idx_map = _consolidate(idx_map, len(palette), k)
    out, counts = _render(idx_map, palette)

    order = [i for i in np.argsort(counts)[::-1] if counts[i] > 0]
    ctx.palette = [palette[i] for i in order]
    ctx.preprocessed_image = Image.fromarray(out, "RGBA")

    dropped = 1.0 - float((idx_map >= 0).mean())
    print(
        f"      quantised to {len(ctx.palette)} colour(s); "
        f"background dropped {dropped * 100:.1f}% of pixels; "
        f"work size {out.shape[1]}x{out.shape[0]}px"
    )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _downsample(
    rgb: np.ndarray, alpha: np.ndarray | None, max_dim: int
) -> tuple[np.ndarray, np.ndarray | None]:
    h, w = rgb.shape[:2]
    if max(h, w) <= max_dim:
        return rgb, alpha
    new_w = max(1, round(w * max_dim / max(h, w)))
    new_h = max(1, round(h * max_dim / max(h, w)))
    rgb_s = np.asarray(Image.fromarray(rgb).resize((new_w, new_h), Image.LANCZOS))
    alpha_s = (
        np.asarray(Image.fromarray(alpha).resize((new_w, new_h), Image.LANCZOS))
        if alpha is not None
        else None
    )
    return rgb_s, alpha_s


def _black_ink_mask(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Foreground pixels that are near-black *and* near-neutral — outline/keyline
    ink (and eye pupils). A dark coloured element (navy, dark teal) has a brighter
    peak channel and is excluded, so only true black ink is snapped."""
    px = rgb.astype(np.int16)
    hi = px.max(axis=2)
    lo = px.min(axis=2)
    return mask & (hi < _BLACK_MAX) & ((hi - lo) < _BLACK_CHROMA)


def _despeckle(mask: np.ndarray, min_px: int) -> np.ndarray:
    """Remove connected foreground components smaller than min_px pixels."""
    if min_px <= 1:
        return mask
    labels, n = ndimage.label(mask)
    if n == 0:
        return mask
    counts = np.bincount(labels.ravel())
    counts[0] = 0  # the background label
    return (counts >= min_px)[labels]


def _refine_palette(
    rgb: np.ndarray, idx_map: np.ndarray, palette: list[tuple[int, int, int]]
) -> list[tuple[int, int, int]]:
    """Move each palette colour to the median RGB of the pixels assigned to it.

    A single Lloyd (k-means) centroid update, using the median (not mean) so the
    representative isn't dragged by anti-aliased / sheen edge pixels straddling two
    inks. Empty clusters keep their prior colour.
    """
    out = list(palette)
    for i in range(len(palette)):
        px = rgb[idx_map == i]
        if len(px):
            out[i] = tuple(int(v) for v in np.median(px, axis=0))
    return out


def _open_counters(
    mask: np.ndarray, rgb: np.ndarray, bg_color, tol: float = BG_DELTA_E
) -> np.ndarray:
    """Reclassify enclosed page-coloured pixels (letter counters) as background.

    `foreground_mask` only drops *border-connected* background, on purpose (so an
    interior region that merely shares the background colour isn't eaten). For
    lettering that guard is wrong: the white inside a loop is the page showing
    through a counter, and must read open. Any foreground pixel within `tol` ΔE of
    the page colour is therefore the page, not ink — drop it. Ink (black/teal/
    yellow strokes) is far from the page colour, so strokes are untouched; the
    anti-aliased rim between stroke and counter is mid-tone (not page-like) and
    stays ink, giving a clean open hole. VTracer then emits a compound path with
    the hole, and Ink-Stitch's fill respects it.
    """
    return mask & ~background_like(rgb, bg_color, tol)


def _purify_ink(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Snap a lettering ink to its 'intended' pure colour — but only when it is
    *already* a near-pure primary/secondary, never boosting a muted brand colour.

    Grounded in the ground-truth lettering files: 10000/11000/12000.VP3 snap their
    primaries to pure (Black (0,0,0), Red (255,0,0), Yellow (255,255,0)) yet keep a
    custom mid-tone (12000's teal (42,133,143)) *verbatim*. The signature of a pure
    primary/secondary is one-or-two channels maxed and the rest near zero
    (max≈255, min≈0); a render only adds sheen/wash to that, so we clean it back to
    full chroma. A muted/custom colour (teal, olive, navy) has a mid-range max and
    must be preserved — pushing it to S=V=1 turned teal into neon cyan (a drift).

    So: low-chroma -> black/white; near-pure chromatic -> full chroma at same hue;
    everything else -> unchanged.
    """
    import colorsys

    r, g, b = (int(c) for c in rgb)
    hi, lo = max(r, g, b), min(r, g, b)
    chroma = hi - lo
    if chroma < 40:  # neutral: black/gray/white
        return (0, 0, 0) if hi < 160 else (255, 255, 255)
    # Snap to pure only when the ink is BRIGHT *and* saturated — i.e. a primary/
    # secondary the render/JPEG merely washed out (yellow 218,219,78 -> 255,255,0,
    # washed red 226,46,45 -> 255,0,0). A genuinely muted/custom mid-tone has a
    # lower peak channel (teal 42,133,143, navy 0,0,89) and is kept verbatim, so it
    # never blows up to a neon. Brightness (hi>=200) separates "light near-primary"
    # from "dark custom colour"; the chroma ratio rejects bright pastels.
    if hi >= 200 and chroma >= 0.45 * hi:
        h, _s, _v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        pr, pg, pb = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        return (round(pr * 255), round(pg * 255), round(pb * 255))
    return (r, g, b)  # muted/custom brand colour — keep exactly (e.g. teal, navy)


def _reduce_palette(colors: list[dict], num_colors: int) -> list[tuple[int, int, int]]:
    """Merge analyze's palette down to num_colors by closest pair in Lab.

    Returns at most num_colors RGB tuples (fewer if analyze found fewer — we
    don't invent colours that aren't in the image).
    """
    pal = [
        {"rgb": tuple(int(x) for x in c["rgb"]), "coverage": float(c["coverage"])}
        for c in colors
    ]
    while len(pal) > num_colors:
        labs = srgb_to_lab(np.array([p["rgb"] for p in pal], dtype=float))
        best: tuple[float, int, int] | None = None
        for i in range(len(pal)):
            for j in range(i + 1, len(pal)):
                d = float(np.linalg.norm(labs[i] - labs[j]))
                if best is None or d < best[0]:
                    best = (d, i, j)
        assert best is not None
        _, i, j = best
        wi, wj = pal[i]["coverage"], pal[j]["coverage"]
        w = (wi + wj) or 1.0
        merged = tuple(
            int(round((pal[i]["rgb"][k] * wi + pal[j]["rgb"][k] * wj) / w)) for k in range(3)
        )
        pal[i] = {"rgb": merged, "coverage": wi + wj}
        del pal[j]
    return [p["rgb"] for p in pal]


def _assign_indices(
    rgb: np.ndarray, mask: np.ndarray, palette: list[tuple[int, int, int]]
) -> np.ndarray:
    """Map each foreground pixel to its nearest palette colour (in Lab).

    Returns an HxW int map: palette index, or -1 for background.
    """
    h, w = rgb.shape[:2]
    idx_map = np.full((h, w), -1, dtype=np.int32)
    fg = rgb[mask].astype(np.float32)
    if len(fg) == 0:
        return idx_map

    labs_px = srgb_to_lab(fg)
    labs_pal = srgb_to_lab(np.array(palette, dtype=float))
    best_idx = np.zeros(len(labs_px), dtype=np.int32)
    best_d = np.full(len(labs_px), np.inf)
    for ki in range(len(labs_pal)):
        dk = np.linalg.norm(labs_px - labs_pal[ki], axis=1)
        closer = dk < best_d
        best_d[closer] = dk[closer]
        best_idx[closer] = ki

    idx_map[mask] = best_idx
    return idx_map


def _consolidate(idx_map: np.ndarray, n_colors: int, k: int) -> np.ndarray:
    """Collapse dithered specks into solid blocks with a majority (mode) filter.

    A shaded photo posterises into many tiny same-colour specks; left alone each
    becomes its own stitched object (lots of machine trims/travel). Reassigning
    each foreground pixel to the colour that dominates its k-px neighbourhood
    merges the dither into a few larger continuous blocks. Foreground stays
    foreground (so the background drop is preserved), and a thin stroke sitting
    on the (transparent) background is safe — only its own colour gets votes
    there — so clean linework like calligraphy is not eroded.
    """
    if k < 3:
        return idx_map
    fg = idx_map >= 0
    if not fg.any():
        return idx_map
    votes = np.stack(
        [ndimage.uniform_filter((idx_map == c).astype(np.float32), size=k)
         for c in range(n_colors)]
    )
    new = votes.argmax(axis=0).astype(np.int32)
    new[~fg] = -1
    return new


def _render(idx_map: np.ndarray, palette: list[tuple[int, int, int]]) -> tuple[np.ndarray, np.ndarray]:
    """Build the RGBA image + per-palette pixel counts from an index map."""
    h, w = idx_map.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    fg = idx_map >= 0
    if fg.any():
        pal = np.array(palette, dtype=np.uint8)
        out[fg, :3] = pal[idx_map[fg]]
        out[fg, 3] = 255
        counts = np.bincount(idx_map[fg], minlength=len(palette))
    else:
        counts = np.zeros(len(palette), dtype=int)
    return out, counts
