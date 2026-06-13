"""Step 7 - Self-verify (the gate).

Render the preview and check it before anything goes to Phase B:
  - diff vs. source: no region eaten by the background drop
  - stitch count vs. stitched area within norms
  - trim / jump / color-change counts vs. professional norms for this size

Only a pass proceeds to Phase B. A fail should re-run Phase A with adjusted
flags (caller's responsibility for now). Writes ctx.verification = {
    "passed": bool, "checks": [...], "metrics": {...} }.
"""

from __future__ import annotations

from ..config import PipelineContext


def run(ctx: PipelineContext) -> None:
    raise NotImplementedError(
        "verify: diff preview vs. source for dropped regions, sanity-check stitch "
        "count + trim/jump/color-change counts; set ctx.verification['passed']."
    )
