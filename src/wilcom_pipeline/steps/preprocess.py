"""Step 2 - Preprocess.

Using ctx.analysis:
  - quantize the image down to config.num_colors thread colors
  - drop the background cleanly (transparent), without eating real regions
  - recolor accents that must survive quantization
  - remove annotation lines / artifacts

Writes ctx.preprocessed_image (RGBA) and ctx.palette (the kept RGB colors).
"""

from __future__ import annotations

from ..config import PipelineContext


def run(ctx: PipelineContext) -> None:
    raise NotImplementedError(
        "preprocess: quantize to config.num_colors, drop background to alpha, "
        "preserve accents, strip annotations; set ctx.preprocessed_image + ctx.palette."
    )
