"""Command-line entrypoint.

    wilcom-pipeline photo.png --width-mm 80
    python -m wilcom_pipeline photo.png --height-mm 50 --colors 6 --thread-chart isacord
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import SUPPORTED_THREAD_CHARTS, PipelineConfig
from . import pipeline


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wilcom-pipeline",
        description="Phase A: photo -> VP3 + worksheet + preview for Wilcom EmbroideryStudio.",
    )
    p.add_argument("image", type=Path, help="Input photo/logo (PNG/JPG).")

    size = p.add_mutually_exclusive_group(required=True)
    size.add_argument("--width-mm", type=float, help="Target physical width in mm.")
    size.add_argument("--height-mm", type=float, help="Target physical height in mm.")

    p.add_argument("--colors", type=int, default=8,
                   help="Number of thread colors to quantize to (default: 8).")
    p.add_argument("--thread-chart", choices=SUPPORTED_THREAD_CHARTS,
                   default="madeira-polyneon",
                   help="Catalog to snap colors to (default: madeira-polyneon).")
    p.add_argument("--output-dir", type=Path, default=Path("output"),
                   help="Where to write the artifacts (default: ./output).")
    p.add_argument("--name", default=None,
                   help="Design name / output stem (default: input filename stem).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.image.is_file():
        print(f"error: input image not found: {args.image}", file=sys.stderr)
        return 2

    try:
        config = PipelineConfig(
            input_path=args.image,
            output_dir=args.output_dir,
            name=args.name or args.image.stem,
            target_width_mm=args.width_mm,
            target_height_mm=args.height_mm,
            num_colors=args.colors,
            thread_chart=args.thread_chart,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    pipeline.run(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
