"""Colour-space helpers shared across steps.

sRGB -> CIELAB (D65) plus a CIE76 ΔE. Perceptual distance matters for both
quantisation (step 2) and thread matching (step 3): nearest-in-RGB picks the
wrong cone surprisingly often, nearest-in-Lab tracks how the eye sees it.

All functions accept either a single (3,) colour or an array shaped (..., 3),
values in 0-255, and broadcast over the leading axes.
"""

from __future__ import annotations

import numpy as np

# sRGB D65 -> XYZ
_XYZ_FROM_RGB = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_WHITE_D65 = np.array([0.95047, 1.0, 1.08883])
_EPS = 216 / 24389
_KAPPA = 24389 / 27


def srgb_to_linear(rgb) -> np.ndarray:
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb_to_lab(rgb) -> np.ndarray:
    """sRGB (0-255) -> CIELAB. Output shape matches input (..., 3)."""
    lin = srgb_to_linear(rgb)
    xyz = (lin @ _XYZ_FROM_RGB.T) / _WHITE_D65
    f = np.where(xyz > _EPS, np.cbrt(xyz), (_KAPPA * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def delta_e(lab1, lab2) -> np.ndarray | float:
    """CIE76 colour difference between two Lab values / arrays."""
    return np.linalg.norm(np.asarray(lab1, float) - np.asarray(lab2, float), axis=-1)
