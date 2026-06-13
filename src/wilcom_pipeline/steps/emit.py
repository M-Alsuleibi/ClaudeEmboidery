"""Step 6 - Emit the three artifacts.

  NAME_pro.vp3            -> the AHK script's only input (internal intermediate).
                            Must carry the matched thread RGBs.
  NAME_pro_preview.png    -> Phase A self-verify gate + human visual check.
  NAME_pro_threadlist.txt -> thread assignment in ES + machine operator sheet
                            (threads, catalog #s, sew order).

Consumes ctx.stitch_pattern + ctx.thread_map; writes the files at the
config.*_path locations. VP3 is written with pyembroidery.
"""

from __future__ import annotations

from ..config import PipelineContext


def run(ctx: PipelineContext) -> None:
    raise NotImplementedError(
        "emit: write VP3 (with thread RGBs) via pyembroidery, render preview PNG, "
        "write threadlist TXT in sew order, to config.vp3_path/preview_path/threadlist_path."
    )
