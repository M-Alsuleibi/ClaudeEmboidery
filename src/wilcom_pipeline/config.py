"""Configuration and shared state passed through the pipeline.

`PipelineConfig` is the immutable run request (what the user asked for).
`PipelineContext` is the mutable bag of intermediate artifacts that each step
reads from and writes to as the run progresses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Catalogs we know how to snap colors to (step 3). Extend in data/threads/.
SUPPORTED_THREAD_CHARTS = ("madeira-polyneon", "isacord")


@dataclass(frozen=True)
class PipelineConfig:
    """One conversion request: a photo + a target size + knobs."""

    input_path: Path
    output_dir: Path
    name: str
    # Exactly one of these is set by the user; the other is derived from aspect ratio.
    target_width_mm: float | None = None
    target_height_mm: float | None = None
    num_colors: int = 8
    thread_chart: str = "madeira-polyneon"

    def __post_init__(self) -> None:
        if self.target_width_mm is None and self.target_height_mm is None:
            raise ValueError("Specify a target size: --width-mm or --height-mm.")
        if self.target_width_mm is not None and self.target_height_mm is not None:
            raise ValueError("Specify only one of --width-mm / --height-mm; the other is derived.")
        if self.thread_chart not in SUPPORTED_THREAD_CHARTS:
            raise ValueError(
                f"Unknown thread chart {self.thread_chart!r}; "
                f"supported: {', '.join(SUPPORTED_THREAD_CHARTS)}"
            )
        if self.num_colors < 1:
            raise ValueError("num_colors must be >= 1")

    # --- Conventional artifact paths (step 6 deliverables) ---
    @property
    def vp3_path(self) -> Path:
        return self.output_dir / f"{self.name}_pro.vp3"

    @property
    def preview_path(self) -> Path:
        return self.output_dir / f"{self.name}_pro_preview.png"

    @property
    def threadlist_path(self) -> Path:
        return self.output_dir / f"{self.name}_pro_threadlist.txt"


@dataclass
class PipelineContext:
    """Mutable state threaded through the steps. Each step fills in its slice."""

    config: PipelineConfig

    # Step 1 — analyze: a structured description of the image.
    analysis: dict[str, Any] = field(default_factory=dict)

    # Step 2 — preprocess: quantized RGBA image + the colors kept.
    preprocessed_image: Any | None = None       # PIL.Image
    palette: list[tuple[int, int, int]] = field(default_factory=list)

    # Step 3 — thread-match: palette color -> catalog thread record.
    thread_map: list[dict[str, Any]] = field(default_factory=list)

    # Step 4 — trace: path to the layered SVG (one group per thread color).
    svg_path: Path | None = None

    # Step 5 — stitches: in-memory stitch model (pyembroidery pattern or similar).
    stitch_pattern: Any | None = None

    # Step 7 — verify: pass/fail + metrics, gates the handoff to Phase B.
    verification: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
