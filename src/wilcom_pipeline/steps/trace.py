"""Step 4 - Vector trace.

Raster -> SVG via VTracer. Then:
  - recolor traced shapes to the matched thread RGBs (ctx.thread_map)
  - one layer/group per color (so stitch generation can treat each as an object)
  - set the physical size in mm from config.target_width_mm / target_height_mm
    (the unset dimension is derived from the source aspect ratio)

Writes ctx.svg_path (the layered, mm-sized SVG).
"""

from __future__ import annotations

from ..config import PipelineContext


def run(ctx: PipelineContext) -> None:
    raise NotImplementedError(
        "trace: VTracer raster->SVG, recolor groups to thread RGBs, one group per "
        "color, scale to target mm; write SVG and set ctx.svg_path."
    )
