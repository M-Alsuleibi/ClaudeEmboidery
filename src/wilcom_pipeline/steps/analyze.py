"""Step 1 - Analyze (the "Step 0" of the goal doc).

Read the image and *derive* settings instead of guessing:
  - what it is (photo / logo / text / line art)
  - background color + whether it's separable
  - each distinct element and its dominant color
  - dark-on-dark risks (low-contrast adjacent regions)
  - smallest feature size (drives minimum-stitch decisions later)

Writes its findings to `ctx.analysis` for downstream steps to consume.
"""

from __future__ import annotations

from ..config import PipelineContext


def run(ctx: PipelineContext) -> None:
    raise NotImplementedError(
        "analyze: load the image, detect background, cluster element colors, "
        "flag dark-on-dark + smallest feature; populate ctx.analysis."
    )
