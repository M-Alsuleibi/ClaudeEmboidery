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


# A border-touching component with no corner is kept as background only if the
# border accounts for at least this share of its own perimeter (edge slivers /
# antialiasing strips qualify; a subject region merely cut off by the frame,
# like a white shirt running out the bottom of a portrait, does not).
BORDER_CONTACT_FRAC = 0.25


def border_connected_background(
    rgb: np.ndarray, bg_color, tol: float = BG_DELTA_E
) -> np.ndarray:
    """Background-like pixels in a region that touches the image border.

    The page background wraps around the subject, so it holds at least one image
    corner. A background-like region that touches the border but holds no corner
    is usually part of a subject the frame cuts off (a garment exiting the bottom
    edge) — that must stay foreground, not be flooded away. Corner-less border
    components are therefore kept as background only when the border makes up a
    large fraction of their perimeter. If *no* component holds a corner (subject
    art covering all four corners), fall back to plain border connectivity.
    """
    like = background_like(rgb, bg_color, tol)
    labels, n = ndimage.label(like)
    if n == 0:
        return np.zeros(rgb.shape[:2], dtype=bool)
    edge = np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    border_labels = np.unique(edge)
    border_labels = border_labels[border_labels != 0]
    if border_labels.size == 0:
        return np.zeros(rgb.shape[:2], dtype=bool)
    corner_labels = {labels[0, 0], labels[0, -1], labels[-1, 0], labels[-1, -1]} - {0}
    if corner_labels:
        keep = []
        for lb in border_labels:
            if lb in corner_labels:
                keep.append(lb)
                continue
            comp = labels == lb
            contact = int(
                comp[0, :].sum() + comp[-1, :].sum() + comp[:, 0].sum() + comp[:, -1].sum()
            )
            perimeter = int((comp & ~ndimage.binary_erosion(comp)).sum())
            if perimeter == 0 or contact >= BORDER_CONTACT_FRAC * perimeter:
                keep.append(lb)
        border_labels = np.asarray(keep)
    return np.isin(labels, border_labels)


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
