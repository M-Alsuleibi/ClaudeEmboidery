"""Image I/O + background-mask helpers shared by analyze and preprocess.

Keeping these in one place means analyze and preprocess agree on what counts
as "background" — analyze decides the *descriptor* (method + colour), and any
step can rebuild a foreground mask from that descriptor at any resolution.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

# L2 RGB distance treated as "the same colour" as a flat background.
BG_COLOR_TOL = 28.0


def load_rgb_alpha(img: Image.Image) -> tuple[np.ndarray, np.ndarray | None]:
    """Return (HxWx3 uint8 RGB, HxW uint8 alpha or None)."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = np.asarray(img.convert("RGBA"))
        return np.ascontiguousarray(rgba[..., :3]), np.ascontiguousarray(rgba[..., 3])
    return np.asarray(img.convert("RGB")), None


def foreground_mask(
    rgb: np.ndarray, alpha: np.ndarray | None, background: dict
) -> np.ndarray:
    """Rebuild a foreground mask (True = element) from a background descriptor.

    Works at any resolution, so a step can downsample first and still mask
    consistently with how analyze described the background.
    """
    if background.get("method") == "alpha":
        if alpha is None:
            return np.ones(rgb.shape[:2], dtype=bool)
        return alpha >= 128
    color = background.get("color")
    if color is None:
        return np.ones(rgb.shape[:2], dtype=bool)
    dist = np.linalg.norm(rgb.astype(np.float32) - np.asarray(color, np.float32), axis=-1)
    return dist >= BG_COLOR_TOL
