"""The Phase A orchestrator: runs steps 1-7 in order against a shared context.

Steps are intentionally small and ordered. Each is a callable `run(ctx)` that
mutates the context in place. Unimplemented steps raise `NotImplementedError`;
the orchestrator stops cleanly at the first one and reports how far it got, so
the skeleton is runnable from day one and the build order is obvious.
"""

from __future__ import annotations

from collections.abc import Callable

from .config import PipelineConfig, PipelineContext
from .steps import (
    analyze,
    preprocess,
    thread_match,
    trace,
    stitches,
    emit,
    verify,
)

Step = Callable[[PipelineContext], None]

# (number, human label, callable) — the canonical Phase A sequence.
STEPS: list[tuple[int, str, Step]] = [
    (1, "analyze", analyze.run),
    (2, "preprocess", preprocess.run),
    (3, "thread-match", thread_match.run),
    (4, "trace", trace.run),
    (5, "stitches", stitches.run),
    (6, "emit", emit.run),
    (7, "verify", verify.run),
]


def run(config: PipelineConfig) -> PipelineContext:
    """Execute the pipeline. Returns the context (partial if a step is a stub)."""
    ctx = PipelineContext(config=config)
    print(f"[wilcom-pipeline] {config.input_path.name} -> {config.output_dir}")
    for number, label, step in STEPS:
        print(f"  [{number}/{len(STEPS)}] {label} ...", flush=True)
        try:
            step(ctx)
        except NotImplementedError as exc:
            print(f"  [{number}/{len(STEPS)}] {label}: NOT YET IMPLEMENTED — {exc}")
            print(f"[wilcom-pipeline] stopped at step {number} ({label}).")
            return ctx
    print("[wilcom-pipeline] done.")
    return ctx
