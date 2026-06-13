"""Image I/O + background-mask helpers shared by analyze and preprocess.

Background detection is connectivity-based: a pixel is background only if it is
both *background-like* (within a CIELAB ΔE of the border's representative colour)
AND part of a region that touches the image edge. That tolerates gentle tonal
variation in a real background (a soft cream illustration backdrop, a vignette)
while stopping at the subject's edges, and it won't eat an interior region that
merely shares the background colour but isn't connected to the border.

analyze decides the descriptor (method + representative colour + separability);
any step can rebuild the same mask from that descriptor at any resolution.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

from .color import delta_e, srgb_to_lab

# CIELAB ΔE within which a pixel counts as "the background colour".
BG_DELTA_E = 12.0


def load_rgb_alpha(img: Image.Image) -> tuple[np.ndarray, np.ndarray | None]:
    """Return (HxWx3 uint8 RGB, HxW uint8 alpha or None)."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = np.asarray(img.convert("RGBA"))
        return np.ascontiguousarray(rgba[..., :3]), np.ascontiguousarray(rgba[..., 3])
    return np.asarray(img.convert("RGB")), None


def background_like(rgb: np.ndarray, bg_color, tol: float = BG_DELTA_E) -> np.ndarray:
    """Boolean mask of pixels within `tol` ΔE of `bg_color` (any (...,3) shape)."""
    lab = srgb_to_lab(np.asarray(rgb, dtype=np.float64))
    bg_lab = srgb_to_lab(np.asarray(bg_color, dtype=np.float64))
    return delta_e(lab, bg_lab) < tol


def border_connected_background(
    rgb: np.ndarray, bg_color, tol: float = BG_DELTA_E
) -> np.ndarray:
    """Background-like pixels in a region that touches the image border."""
    like = background_like(rgb, bg_color, tol)
    labels, n = ndimage.label(like)
    if n == 0:
        return np.zeros(rgb.shape[:2], dtype=bool)
    edge = np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    keep = np.unique(edge)
    keep = keep[keep != 0]
    if keep.size == 0:
        return np.zeros(rgb.shape[:2], dtype=bool)
    return np.isin(labels, keep)


def foreground_mask(
    rgb: np.ndarray, alpha: np.ndarray | None, background: dict
) -> np.ndarray:
    """Rebuild a foreground mask (True = element) from a background descriptor."""
    if background.get("method") == "alpha":
        if alpha is None:
            return np.ones(rgb.shape[:2], dtype=bool)
        return alpha >= 128
    color = background.get("color")
    if color is None:
        return np.ones(rgb.shape[:2], dtype=bool)
    return ~border_connected_background(rgb, color)
