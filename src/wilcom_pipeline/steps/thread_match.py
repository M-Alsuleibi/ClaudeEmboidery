"""Step 3 - Thread-match.

Snap each palette color to a real catalog thread (Madeira Polyneon / Isacord)
so the colors are loadable cones and the preview, worksheet, and design all
agree. Catalogs live in data/threads/*.csv.

Match in a perceptual space (e.g. CIELAB dE) rather than raw RGB distance.

Writes ctx.thread_map: one record per palette color, e.g.
    {"rgb": (12,34,56), "catalog": "Madeira Polyneon",
     "code": "1801", "name": "Black", "thread_rgb": (10,10,10), "de": 2.3}
"""

from __future__ import annotations

from ..config import PipelineContext


def run(ctx: PipelineContext) -> None:
    raise NotImplementedError(
        "thread-match: load the chosen catalog, match each ctx.palette color by "
        "CIELAB distance to the nearest cone; set ctx.thread_map."
    )
