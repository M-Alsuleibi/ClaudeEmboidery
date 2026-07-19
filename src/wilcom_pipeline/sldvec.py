"""SLD-Vectorization bridge (--sld-strokes).

Recovers ORDERED PEN STROKES (centerline polylines with the traversal order a
calligrapher would draw, intersections resolved by the paper's CNN) from a raster
region mask, via the vendored SLD-Vectorization tool (Magne & Sorkine-Hornung,
"Single-Line Drawing Vectorization", CGF 44(7) / Pacific Graphics 2025).

The tool is a separate patched checkout + venv under vendor/sld-vectorization/
(override with $SLDVEC_BIN) — see docs/research/sld-vectorization-eval.md for the
required patches (fat-stroke merge guard, CPU torch, NaN export guard) and the
measured arb results (allah glyph: 5 calligraphically-correct strokes; red arcs:
406 strokes, 83% skeleton coverage). Like Ink-Stitch, it is NOT a pip dependency:
everything here degrades to [] / False when the tool is absent, and the caller
falls back to the skeleton branch-chaining path.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_BIN = _REPO_ROOT / "vendor" / "sld-vectorization" / "venv" / "bin" / "SLDvec"

_FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_PATH_D_RE = re.compile(r'<path[^>]*\bd="([^"]+)"')

# SLD internally rescales its input to max 1000 px; feed it close to that so thin
# diacritic strokes keep a few pixels of body. (The region raster is ~0.3 mm/px.)
_TARGET_PX = 900
_SAMPLE_STEP_PX = 2.0       # polyline sampling step along each recovered Bezier, in
                            # SLD-input px (~0.6 mm at the raster's native scale)
_DEFAULT_TIMEOUT_S = 300


def binary() -> Path:
    env = os.environ.get("SLDVEC_BIN")
    return Path(env) if env else _DEFAULT_BIN


def available() -> bool:
    return binary().is_file() and os.access(binary(), os.X_OK)


def _cubic_points(p0, c1, c2, p3, step_px: float) -> np.ndarray:
    """Sample one cubic Bezier segment at ~step_px spacing (control-polygon length
    as the arc-length proxy). Includes both endpoints."""
    ctrl = np.asarray([p0, c1, c2, p3], float)
    approx_len = float(np.hypot(*np.diff(ctrl, axis=0).T).sum())
    n = max(2, int(np.ceil(approx_len / max(step_px, 1e-6))) + 1)
    t = np.linspace(0.0, 1.0, n)[:, None]
    m = 1.0 - t
    return (m**3 * ctrl[0] + 3 * m**2 * t * ctrl[1]
            + 3 * m * t**2 * ctrl[2] + t**3 * ctrl[3])


def parse_svg_strokes(svg_text: str, step_px: float = _SAMPLE_STEP_PX) -> list[np.ndarray]:
    """Parse SLD's output SVG (one path per recovered stroke, 'M x y' + repeated
    'C c1 c2 p' cubics) into sampled (N,2) polylines in image-pixel coordinates.
    Degenerate paths (too few numbers, non-finite) are skipped."""
    strokes: list[np.ndarray] = []
    for d in _PATH_D_RE.findall(svg_text):
        nums = [float(v) for v in _FLOAT_RE.findall(d)]
        if len(nums) < 8 or (len(nums) - 2) % 6:
            continue
        vals = np.asarray(nums, float)
        if not np.isfinite(vals).all():
            continue
        pts = [vals[0:2]]
        prev = vals[0:2]
        for k in range(2, len(vals), 6):
            c1, c2, p3 = vals[k:k + 2], vals[k + 2:k + 4], vals[k + 4:k + 6]
            seg = _cubic_points(prev, c1, c2, p3, step_px)
            pts.append(seg[1:])
            prev = p3
        arr = np.vstack(pts)
        keep = np.ones(len(arr), bool)
        keep[1:] = np.hypot(*np.diff(arr, axis=0).T) > 1e-9
        arr = arr[keep]
        if len(arr) >= 2:
            strokes.append(arr)
    return strokes


def recover_strokes(mask: np.ndarray, timeout_s: int = _DEFAULT_TIMEOUT_S) -> list[np.ndarray]:
    """Run SLD-Vectorization on a bool ink mask. Returns each recovered stroke as an
    (N,2) float array in MASK-PIXEL coordinates (x=col, y=row), in the tool's drawing
    order. [] when the tool is unavailable, times out, fails, or finds nothing —
    callers treat [] as "fall back to the skeleton path"."""
    if not available() or mask is None or not mask.any():
        return []
    from PIL import Image

    h, w = mask.shape
    scale = min(4.0, max(1.0, _TARGET_PX / max(h, w)))
    img = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8))
    if scale > 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    with tempfile.TemporaryDirectory(prefix="sldvec_") as td:
        png = Path(td) / "region.png"
        out = Path(td) / "region_sld.svg"
        img.save(png)
        try:
            subprocess.run(
                [str(binary()), "run", str(png), "--output-path", str(out),
                 "--multiple-lines"],
                capture_output=True, timeout=timeout_s, check=True)
            svg_text = out.read_text(encoding="utf-8")
        except (subprocess.SubprocessError, OSError, UnicodeDecodeError):
            return []
        strokes = parse_svg_strokes(svg_text)

    return [s / scale for s in strokes]
