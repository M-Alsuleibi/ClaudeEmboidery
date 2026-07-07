"""Step 3 - Thread-match.

Snap each palette colour (step 2) to a real catalog cone (Madeira Polyneon /
Isacord) in CIELAB, so the preview, worksheet, and design all agree and the
operator loads cones that exist. Catalogs come from Ink-Stitch .gpl palettes
(see catalog.py).

Writes ctx.thread_map: one record per palette colour, aligned with ctx.palette:
    {"rgb": (12,34,56), "catalog": "Madeira Polyneon",
     "code": "1801", "name": "Black", "thread_rgb": (10,10,10), "de": 2.3}

Region merging when two colours hit the same cone is left to step 5 (routing /
minimal colour changes); here we just assign and flag the collision.
"""

from __future__ import annotations

from ..catalog import load_catalog
from ..config import PipelineContext

_GOOD_DE = 5.0   # <= this: a faithful match
_POOR_DE = 12.0  # > this: the cone is visibly off; worth flagging


def run(ctx: PipelineContext) -> None:
    if not ctx.palette:
        raise RuntimeError("thread-match requires ctx.palette; run preprocess first.")

    cat = load_catalog(ctx.config.thread_chart)
    thread_map: list[dict] = []
    for rgb in ctx.palette:
        thread, de = cat.nearest(rgb)
        # In lettering mode the inks are already purified to the intended colour
        # (pure black/red, like the 10000.VP3 ground truth, which stored pure RGB
        # *and* a cone code). So render/store the pure ink and keep the nearest
        # cone only as the operator's reference (code/name). Otherwise the design
        # would render the off cone (e.g. pure red -> a pinkish "Fluo" cone).
        thread_rgb = tuple(int(c) for c in rgb) if ctx.config.purify else thread.rgb
        thread_map.append(
            {
                "rgb": tuple(int(c) for c in rgb),
                "catalog": cat.display,
                "code": thread.code,
                "name": thread.name,
                "thread_rgb": thread_rgb,
                "de": round(de, 2),
            }
        )
    ctx.thread_map = thread_map

    print(f"      matched {len(thread_map)} colour(s) to {cat.display} ({len(cat.colors)} cones):")
    for m in thread_map:
        flag = "" if m["de"] <= _GOOD_DE else ("  ~off" if m["de"] <= _POOR_DE else "  !! poor")
        print(f"        {m['rgb']} -> {m['code']} {m['name']} (dE {m['de']}){flag}")

    poor = [m for m in thread_map if m["de"] > _POOR_DE]
    if poor:
        print(f"      ! {len(poor)} colour(s) matched poorly (dE>{_POOR_DE:g}); "
              "no closer cone in this chart.")
    codes = [m["code"] for m in thread_map]
    dups = sorted({c for c in codes if codes.count(c) > 1})
    if dups:
        print(f"      note: cone(s) {dups} shared by multiple regions — merge in step 5.")
