"""Step 1 - Analyze (the "Step 0" of the goal doc).

Read the image and *derive* settings instead of guessing:
  - what it is (photo vs graphic/logo vs line-art/text)  [heuristic]
  - background color + whether it's cleanly separable
  - each distinct element and its dominant color
  - dark-on-dark risks (low-contrast element/bg and element/element pairs)
  - smallest feature size (drives minimum-stitch decisions later)

Because the target physical size is already known (config), this also resolves
the full width x height in mm and reports the smallest feature *in mm* — which is
exactly what step 5 needs to honour minimum stitch sizes.

Writes its findings to `ctx.analysis`.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage
from sklearn.cluster import MiniBatchKMeans

from ..config import PipelineContext
from ..imaging import BG_COLOR_TOL, load_rgb_alpha

# --- tunables (documented so they're easy to calibrate against references) ---
_ANALYSIS_MAX_DIM = 400        # downsample longest side to this for stats (speed)
_BG_BORDER_FRAC = 0.45         # border must be >=45% one color to call bg separable
_MAX_CLUSTERS_PROBE = 12       # upper bound on element colours we look for
_MIN_CLUSTER_COVERAGE = 0.02   # clusters below this fraction of fg are noise
_LOW_CONTRAST_RATIO = 2.0      # WCAG contrast ratio below this = merge/vanish risk
_FLAT_GRAD_THRESH = 10.0       # per-channel gradient below this = "flat" pixel
_PHOTO_FLAT_FRAC = 0.45        # below this flat fraction we call it a photo
_MIN_SATIN_MM = 1.2            # features thinner than this risk being below satin min


def run(ctx: PipelineContext) -> None:
    img = Image.open(ctx.config.input_path)
    img.load()
    full_w, full_h = img.size

    rgb_full, alpha_full = load_rgb_alpha(img)
    rgb, alpha = _downsample(rgb_full, alpha_full, _ANALYSIS_MAX_DIM)
    sh, sw = rgb.shape[:2]

    background, fg_mask = _detect_background(rgb, alpha)
    fg_coverage = float(fg_mask.mean())

    colors = _cluster_colors(rgb, fg_mask)
    flat_frac = _flat_fraction(rgb)
    smallest_px_small = _smallest_feature_px(fg_mask) if background["is_separable"] else None

    # px scale between the downsampled stats and the real image
    scale = full_w / sw
    smallest_feature_px = (smallest_px_small * scale) if smallest_px_small else None

    mm = _resolve_mm(ctx, full_w, full_h)
    smallest_feature_mm = (
        smallest_feature_px * mm["mm_per_px"] if smallest_feature_px else None
    )

    contrast = _contrast_risks(background, colors)
    kind = _classify_kind(colors, flat_frac, fg_coverage, smallest_feature_mm)

    warnings: list[str] = []
    if not background["is_separable"]:
        warnings.append(
            "Background is not cleanly separable; the drop step may eat real regions."
        )
    if smallest_feature_mm is not None and smallest_feature_mm < _MIN_SATIN_MM:
        warnings.append(
            f"Smallest feature ~{smallest_feature_mm:.2f} mm is below the ~{_MIN_SATIN_MM} mm "
            "satin minimum; enlarge the design or use run/triple-run for those strokes."
        )
    if contrast["low_contrast_with_bg"]:
        warnings.append(
            f"{len(contrast['low_contrast_with_bg'])} element colour(s) low-contrast vs "
            "background (dark-on-dark / light-on-light risk)."
        )

    ctx.analysis = {
        "source": {
            "size_px": (full_w, full_h),
            "aspect_ratio": round(full_w / full_h, 4),
            "mode": img.mode,
            "has_alpha": alpha_full is not None,
        },
        "size_mm": mm,
        "kind": kind,
        "background": background,
        "foreground_coverage": round(fg_coverage, 4),
        "colors": colors,
        "num_colors_suggested": max(2, len(colors)),
        "flat_fraction": round(flat_frac, 4),
        "smallest_feature_px": round(smallest_feature_px, 2) if smallest_feature_px else None,
        "smallest_feature_mm": round(smallest_feature_mm, 3) if smallest_feature_mm else None,
        "contrast": contrast,
        "warnings": warnings,
    }
    _print_summary(ctx.analysis)


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
    rgb_s = np.asarray(Image.fromarray(rgb).resize((new_w, new_h), Image.BILINEAR))
    alpha_s = (
        np.asarray(Image.fromarray(alpha).resize((new_w, new_h), Image.BILINEAR))
        if alpha is not None
        else None
    )
    return rgb_s, alpha_s


def _detect_background(
    rgb: np.ndarray, alpha: np.ndarray | None
) -> tuple[dict, np.ndarray]:
    """Find the background and a foreground mask (True = element pixel)."""
    h, w = rgb.shape[:2]

    # 1) Transparency wins if present and meaningful.
    if alpha is not None:
        transparent = alpha < 128
        cov = float(transparent.mean())
        if cov > 0.02:
            return (
                {"method": "alpha", "color": None, "coverage": round(cov, 4), "is_separable": True},
                ~transparent,
            )

    # 2) Dominant border colour.
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).reshape(-1, 3)
    quant = (border // 8 * 8).astype(np.int32)
    keys, counts = np.unique(quant, axis=0, return_counts=True)
    top = keys[counts.argmax()]
    border_frac = counts.max() / len(border)

    dist = np.linalg.norm(rgb.reshape(-1, 3).astype(np.float32) - top, axis=1)
    bg_pixels = dist < BG_COLOR_TOL
    cov = float(bg_pixels.mean())
    fg_mask = (~bg_pixels).reshape(h, w)
    separable = bool(border_frac >= _BG_BORDER_FRAC)

    # exact bg colour = mean of the matched border-ish pixels (nicer than quantised key)
    bg_color = tuple(int(c) for c in rgb.reshape(-1, 3)[bg_pixels].mean(axis=0)) if bg_pixels.any() else tuple(int(c) for c in top)

    return (
        {
            "method": "border-dominant",
            "color": bg_color,
            "coverage": round(cov, 4),
            "border_fraction": round(float(border_frac), 4),
            "is_separable": separable,
        },
        fg_mask,
    )


def _cluster_colors(rgb: np.ndarray, fg_mask: np.ndarray) -> list[dict]:
    """Dominant element colours (excluding background), sorted by coverage."""
    pixels = rgb[fg_mask].astype(np.float32)
    if len(pixels) < 16:
        return []
    distinct = len(np.unique((pixels // 8).astype(np.int32), axis=0))
    k = int(min(_MAX_CLUSTERS_PROBE, distinct, len(pixels)))
    if k < 1:
        return []

    km = MiniBatchKMeans(n_clusters=k, random_state=0, n_init=3, batch_size=2048)
    labels = km.fit_predict(pixels)
    counts = np.bincount(labels, minlength=k)
    total = counts.sum()

    out = []
    for i in np.argsort(counts)[::-1]:
        cov = counts[i] / total
        if cov < _MIN_CLUSTER_COVERAGE:
            continue
        out.append(
            {"rgb": tuple(int(c) for c in km.cluster_centers_[i]), "coverage": round(float(cov), 4)}
        )
    return out


def _flat_fraction(rgb: np.ndarray) -> float:
    """Fraction of pixels sitting in a locally flat region (graphic vs photo cue)."""
    f = rgb.astype(np.float32)
    gy = np.abs(np.diff(f, axis=0)).max(axis=2)
    gx = np.abs(np.diff(f, axis=1)).max(axis=2)
    grad = np.zeros(rgb.shape[:2], dtype=np.float32)
    grad[:-1] = np.maximum(grad[:-1], gy)
    grad[:, :-1] = np.maximum(grad[:, :-1], gx)
    return float((grad < _FLAT_GRAD_THRESH).mean())


def _smallest_feature_px(fg_mask: np.ndarray) -> float | None:
    """Estimate the thinnest stroke width via the distance transform's medial ridge."""
    if not fg_mask.any():
        return None
    dist = ndimage.distance_transform_edt(fg_mask)
    if dist.max() <= 0:
        return None
    ridge = (dist >= ndimage.maximum_filter(dist, size=3)) & (dist > 0)
    ridge_vals = dist[ridge]
    if ridge_vals.size == 0:
        return None
    # width ~= 2 * half-width; use a low percentile for the *smallest* feature
    return float(2.0 * np.percentile(ridge_vals, 5))


def _resolve_mm(ctx: PipelineContext, full_w: int, full_h: int) -> dict:
    cfg = ctx.config
    if cfg.target_width_mm is not None:
        mm_per_px = cfg.target_width_mm / full_w
    else:
        mm_per_px = cfg.target_height_mm / full_h
    return {
        "width_mm": round(full_w * mm_per_px, 2),
        "height_mm": round(full_h * mm_per_px, 2),
        "mm_per_px": mm_per_px,
    }


def _rel_luminance(rgb) -> np.ndarray | float:
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722


def _contrast_ratio(l1: float, l2: float) -> float:
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _contrast_risks(background: dict, colors: list[dict]) -> dict:
    low_bg: list[dict] = []
    if background.get("color") is not None:
        bg_l = float(_rel_luminance(background["color"]))
        for c in colors:
            ratio = _contrast_ratio(bg_l, float(_rel_luminance(c["rgb"])))
            if ratio < _LOW_CONTRAST_RATIO:
                low_bg.append({"rgb": c["rgb"], "contrast_ratio": round(ratio, 2)})

    low_pairs: list[dict] = []
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            ratio = _contrast_ratio(
                float(_rel_luminance(colors[i]["rgb"])),
                float(_rel_luminance(colors[j]["rgb"])),
            )
            if ratio < _LOW_CONTRAST_RATIO:
                low_pairs.append(
                    {"a": colors[i]["rgb"], "b": colors[j]["rgb"], "contrast_ratio": round(ratio, 2)}
                )
    return {"low_contrast_with_bg": low_bg, "low_contrast_pairs": low_pairs}


def _classify_kind(
    colors: list[dict], flat_frac: float, fg_coverage: float, smallest_mm: float | None
) -> str:
    """Heuristic, best-effort label — informs defaults, not a hard decision."""
    if flat_frac < _PHOTO_FLAT_FRAC:
        return "photo"
    if fg_coverage < 0.18 and smallest_mm is not None and smallest_mm < 2.5:
        return "line-art/text"
    return "logo/graphic"


def _print_summary(a: dict) -> None:
    bg = a["background"]
    bg_desc = bg["method"] + ("" if bg["is_separable"] else " (NOT separable)")
    print(
        f"      kind={a['kind']}  colors={len(a['colors'])} (suggest {a['num_colors_suggested']})  "
        f"size={a['size_mm']['width_mm']}x{a['size_mm']['height_mm']}mm  bg={bg_desc}"
    )
    if a["smallest_feature_mm"] is not None:
        print(f"      smallest feature ~{a['smallest_feature_mm']} mm")
    for w in a["warnings"]:
        print(f"      ! {w}")
