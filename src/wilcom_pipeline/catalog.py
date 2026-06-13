"""Thread catalogs: parse Ink-Stitch .gpl palettes and match colours to cones.

Ink-Stitch ships authoritative manufacturer palettes as GIMP palette (.gpl)
files. Each colour line is:

    R G B <whitespace> <colour name, may contain spaces> <catalog code>

e.g. ``183 195 197    Celestial Blue   1610``. Matching is done in CIELAB
(see color.py) — nearest-in-RGB picks the wrong cone surprisingly often.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from .color import delta_e, srgb_to_lab

# data/threads lives at the repo root, two levels above this package dir.
_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "threads"

_HEADER_PREFIXES = ("GIMP Palette", "Name:", "Columns:")
_CHART_DISPLAY = {
    "madeira-polyneon": "Madeira Polyneon",
    "isacord": "Isacord Polyester",
}


@dataclass(frozen=True)
class ThreadColor:
    code: str
    name: str
    rgb: tuple[int, int, int]


@dataclass(eq=False)
class ThreadCatalog:
    key: str
    display: str
    colors: list[ThreadColor]
    labs: np.ndarray  # (N, 3), parallel to .colors

    def nearest(self, rgb) -> tuple[ThreadColor, float]:
        """Closest cone to an RGB colour, with its CIE76 ΔE."""
        lab = srgb_to_lab(np.asarray(rgb, dtype=float))
        d = delta_e(self.labs, lab)
        i = int(np.argmin(d))
        return self.colors[i], float(d[i])


def parse_gpl(path: Path) -> list[ThreadColor]:
    colors: list[ThreadColor] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(_HEADER_PREFIXES):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            continue  # not a colour row
        rest = parts[3:]
        # The catalog code is the trailing token; the name is everything between.
        if len(rest) >= 2:
            code, name = rest[-1], " ".join(rest[:-1])
        else:
            code, name = rest[0], ""
        colors.append(ThreadColor(code=code, name=name, rgb=(r, g, b)))
    return colors


def catalog_path(chart_key: str) -> Path:
    return _DATA_DIR / f"{chart_key}.gpl"


@lru_cache(maxsize=None)
def load_catalog(chart_key: str) -> ThreadCatalog:
    path = catalog_path(chart_key)
    if not path.is_file():
        raise FileNotFoundError(
            f"Thread catalog not found: {path}\n"
            "Expected an Ink-Stitch .gpl palette (see data/threads/README.md)."
        )
    colors = parse_gpl(path)
    if not colors:
        raise ValueError(f"No colours parsed from {path}")
    labs = srgb_to_lab(np.array([c.rgb for c in colors], dtype=float))
    return ThreadCatalog(
        key=chart_key,
        display=_CHART_DISPLAY.get(chart_key, chart_key),
        colors=colors,
        labs=labs,
    )
