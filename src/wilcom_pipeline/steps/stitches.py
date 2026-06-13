"""Step 5 - Generate stitches (quality + machine-optimization baked in).

Best practice:
  - right stitch type per region: satin for columns/text, tatami/fill for areas,
    run/triple-run for fine lines
  - appropriate underlay; density ~4-5 lines/mm (~0.4 mm)
  - pull compensation on columns/fills
  - sequence by stacking depth (foreground last); tie-ins / tie-offs
  - respect minimum sizes; preserve fine detail
  - Arabic text/calligraphy: connected-script pathing, dot/diacritic handling,
    minimum legible sizes

Machine-optimized:
  - 2-opt travel routing; short hops sewn through, long hops trimmed
    (each trim doubles as a Break-Apart boundary in Wilcom)
  - minimal color changes (merge regions mapping to the same cone)
  - sane total stitch count

Consumes ctx.svg_path (+ ctx.thread_map); writes ctx.stitch_pattern.
This is where Ink/Stitch (or an equivalent digitizer) plugs in.
"""

from __future__ import annotations

from ..config import PipelineContext


def run(ctx: PipelineContext) -> None:
    raise NotImplementedError(
        "stitches: digitize the layered SVG into stitches (satin/fill/run per region, "
        "underlay, density, pull comp, sequencing, routing/trims); set ctx.stitch_pattern."
    )
