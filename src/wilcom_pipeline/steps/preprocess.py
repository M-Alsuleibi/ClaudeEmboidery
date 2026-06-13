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
from ..imaging import foreground_mask, load_rgb_alpha

# Cap working resolution. Embroidery doesn't need photo-grade detail: at an 80 mm
# design 1200 px is ~15 px/mm, well past machine resolution (~0.1 mm).
_WORK_MAX_DIM = 1200

# Foreground components smaller than this (real-world area) are background noise,
# not stitchable features — drop them after the background is removed.
_MIN_FEATURE_MM2 = 0.5


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
    else:
        # No clean background to remove — keep every pixel, just posterise.
        mask = np.ones(rgb.shape[:2], dtype=bool)

    palette = _reduce_palette(analysis["colors"], cfg.num_colors)
    if not palette:
        raise RuntimeError("preprocess: analyze found no element colours to quantise.")

    out, counts = _quantize(rgb, mask, palette)

    order = [i for i in np.argsort(counts)[::-1] if counts[i] > 0]
    ctx.palette = [palette[i] for i in order]
    ctx.preprocessed_image = Image.fromarray(out, "RGBA")

    dropped = 1.0 - float(mask.mean())
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


def _quantize(
    rgb: np.ndarray, mask: np.ndarray, palette: list[tuple[int, int, int]]
) -> tuple[np.ndarray, np.ndarray]:
    """Snap each foreground pixel to the nearest palette colour (in Lab).

    Returns (HxWx4 RGBA, per-palette pixel counts). Background -> (0,0,0,0).
    """
    h, w = rgb.shape[:2]
    out = np.zeros((h, w, 4), dtype=np.uint8)
    fg = rgb[mask].astype(np.float32)
    if len(fg) == 0:
        return out, np.zeros(len(palette), dtype=int)

    labs_px = srgb_to_lab(fg)
    labs_pal = srgb_to_lab(np.array(palette, dtype=float))

    # Nearest centroid via k passes (k is small) — keeps memory at O(N), not O(N*k).
    best_idx = np.zeros(len(labs_px), dtype=int)
    best_d = np.full(len(labs_px), np.inf)
    for ki in range(len(labs_pal)):
        dk = np.linalg.norm(labs_px - labs_pal[ki], axis=1)
        closer = dk < best_d
        best_d[closer] = dk[closer]
        best_idx[closer] = ki

    pal_arr = np.array(palette, dtype=np.uint8)
    out[mask, :3] = pal_arr[best_idx]
    out[mask, 3] = 255
    counts = np.bincount(best_idx, minlength=len(palette))
    return out, counts
