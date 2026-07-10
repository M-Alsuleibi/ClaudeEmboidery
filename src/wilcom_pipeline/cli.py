"""Command-line entrypoint.

    wilcom-pipeline photo.png --width-mm 80
    python -m wilcom_pipeline photo.png --height-mm 50 --colors 6 --thread-chart isacord
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import (
    SUPPORTED_CATEGORIES,
    SUPPORTED_FABRICS,
    SUPPORTED_FILL_METHODS,
    SUPPORTED_THREAD_CHARTS,
    PipelineConfig,
)
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

    p.add_argument("--colors", type=int, default=None,
                   help="Number of thread colors to quantize to. Default: the --category "
                        "prior (arabic/decoration/simple-shapes 1, letters 2, numbers 4, "
                        "3D 8, anime 8) when a category is given, else 8. Pass an explicit "
                        "value for a colourful design in a monochrome-median category.")
    p.add_argument("--thread-chart", choices=SUPPORTED_THREAD_CHARTS,
                   default="madeira-polyneon",
                   help="Catalog to snap colors to (default: madeira-polyneon).")
    p.add_argument("--fill-method", choices=SUPPORTED_FILL_METHODS, default="auto_fill",
                   help="Ink-Stitch fill for solid regions. 'auto_fill' (default) routes "
                        "one continuous path — best for compact shapes but its travel "
                        "routing can be pathologically slow / time out on long thin "
                        "sprawling regions; 'contour_fill' follows the shape contour "
                        "(fast, natural for calligraphy); 'meander_fill' stipples.")
    p.add_argument("--category", choices=SUPPORTED_CATEGORIES, default=None,
                   help="Production category of the design (letters/arabic/3D/anime/"
                        "simple-shapes/decoration/numbers). Step 7 scores the run against that "
                        "category's ground-truth fingerprint and flags drift (satin%%, colours, "
                        "density). Optional — omit and verify infers the nearest category. "
                        "Never fails the gate; it's production-style guidance.")
    p.add_argument("--output-dir", type=Path, default=Path("output"),
                   help="Where to write the artifacts (default: ./output).")
    p.add_argument("--name", default=None,
                   help="Design name / output stem (default: input filename stem).")
    p.add_argument("--lettering", action="store_true",
                   help="Block/typeset lettering mode: satin the letter strokes "
                        "(dissect each glyph into stroke-columns), raise the satin "
                        "width ceiling, and snap inks to pure colour. Use for block "
                        "capitals / typeset words, not cursive calligraphy.")
    p.add_argument("--purify-colors", action="store_true",
                   help="Snap near-pure primaries to pure and keep custom/muted brand "
                        "colours verbatim, WITHOUT satin-dissecting glyphs. Use for "
                        "mixed designs (display caps + cursive script) that --lettering "
                        "would shatter, to still get faithful colours. Implied by --lettering.")
    p.add_argument("--open-counters", action=argparse.BooleanOptionalAction, default=None,
                   help="Drop page-coloured regions ENCLOSED by ink (the hole in e/B/g, "
                        "the open loop of a script descender) to background so they read "
                        "through instead of filling solid. Default: auto (on for letter "
                        "modes). Use --no-open-counters to keep enclosed same-as-page "
                        "regions as a stitched fill (e.g. a white shape inside a logo).")
    p.add_argument("--fabric", choices=SUPPORTED_FABRICS, default=None,
                   help="Target fabric — sets the default pull-compensation from the Wilcom "
                        "manual's table (cotton/denim/drill 0.20, silk 0.30, t-shirt/knit/"
                        "jersey 0.35, fleece/jumper/terry 0.40 mm). A no-op if --pull-comp-mm "
                        "is given. Omit for the 0.2 mm default.")
    p.add_argument("--pull-comp-mm", type=float, default=None,
                   help="Pull-compensation per side (mm) added to fills/satins. Overrides "
                        "--fabric. Default (no --fabric): 0.2. Lower it (e.g. 0.05) so FINE "
                        "decoration — thin tashkeel on Arabic calligraphy — reads as crisp as "
                        "the source art instead of fattened.")
    p.add_argument("--fill-underlay", action=argparse.BooleanOptionalAction, default=True,
                   help="Lay a fill underlay under solid regions (default: on). "
                        "Use --no-fill-underlay to drop the extra widening pass when "
                        "matching thin decoration to the original.")
    p.add_argument("--satin-underlay", action=argparse.BooleanOptionalAction, default=True,
                   help="Lay a center-walk + contour underlay under satin columns so "
                        "their edges don't tunnel/pucker (default: on — 'always underlay "
                        "your satins'). Use --no-satin-underlay to compare or keep a very "
                        "fine column light.")
    p.add_argument("--thin-line-run", action=argparse.BooleanOptionalAction, default=True,
                   help="Route linework colours thinner than the min satin width (~1.6 mm) "
                        "to a running/bean (triple) stitch along their centerline instead "
                        "of fattening them into a narrow satin (default: on — the 'line < "
                        "1.6 mm -> run/triple-run' rule; e.g. a logo's black keyline). Use "
                        "--no-thin-line-run to force narrow satins. Ignored under --lettering.")
    p.add_argument("--branch-satin", action=argparse.BooleanOptionalAction, default=False,
                   help="Dissect a BRANCHY stroke region in the satin width band into one "
                        "satin column per branch (like --lettering does for glyph strokes), "
                        "instead of keeping it a single tatami fill. For organic strokes that "
                        "fork — a calligraphic letter, an ornament limb. Off by default: it "
                        "restructures the sew path and can leave small gaps at junctions. "
                        "Guarded to fire only on a few long branches that form most of the "
                        "shape (a dense mesh stays a fill); no-op under --lettering.")
    p.add_argument("--satin-lean", action=argparse.BooleanOptionalAction, default=False,
                   help="For a satin-dominant category (--category arabic/decoration/letters/…), "
                        "lean the tiering to satin: raise the ceiling + dissect branchy strokes "
                        "so bold strokes become satin columns instead of tatami, matching the "
                        "ground truth's ~100%% satin. OFF by default — the pipeline's fixed-width "
                        "satins UNDER-COVER a bold/modulated stroke (Arabic: coverage 99.9%%->81.6%%). "
                        "Use only when the satin *look* matters more than pixel coverage; no-op "
                        "unless the category is satin-dominant.")
    p.add_argument("--snap-black", action=argparse.BooleanOptionalAction, default=True,
                   help="Dedicate one thread to pure black and route the near-black, "
                        "near-neutral pixels (a logo's outline/keyline, eye pupils) to it "
                        "(default: on). Keeps a thin black outline crisp instead of letting "
                        "quantisation average it into a dark brown, WITHOUT the neon "
                        "over-saturation --purify-colors causes on muted colours. A no-op "
                        "when the art has no real black. Use --no-snap-black to disable.")
    p.add_argument("--auto-route", action=argparse.BooleanOptionalAction, default=False,
                   help="Run Ink-Stitch auto_satin / auto_run per colour to thread each "
                        "colour's satin columns / running stitches into one connected, "
                        "optimally-ordered path (underpathing instead of trims, chosen "
                        "entry/exit). Cuts travel + trims on satin-/run-heavy designs "
                        "(lettering, outlines). Off by default (restructures the sew path; "
                        "can add travel on scattered pieces like Arabic dots).")
    p.add_argument("--realistic-preview", action=argparse.BooleanOptionalAction, default=True,
                   help="Render the preview with Ink-Stitch's realistic thread renderer "
                        "(honest stroke widths + thread look) instead of the fast polyline "
                        "draw (default: on). Costs an extra stitch-plan pass; falls back to "
                        "the polyline preview on error. Use --no-realistic-preview for speed.")
    p.add_argument("--gradient", action=argparse.BooleanOptionalAction, default=False,
                   help="De-posterize smooth shading: merge adjacent palette colours that "
                        "are the same hue but different lightness (e.g. a shell's light/dark "
                        "orange) into one region stitched as a smooth density-modulated "
                        "gradient (Ink-Stitch gradient_blocks), instead of hard flat bands. "
                        "Off by default (experimental; the merge heuristic can misfire).")
    p.add_argument("--spine-fill", action=argparse.BooleanOptionalAction, default=False,
                   help="Spine-guided fill (experimental): for a region kept as a FILL "
                        "(branchy stroke / broad blob), reuse its longest extracted "
                        "centerline as an Ink-Stitch guided_fill guide so the fill rows "
                        "follow the shape's medial axis instead of a fixed angle (the "
                        "PEmbroider hatchSpine idea). Directional/visual only — it does NOT "
                        "raise the fingerprint's satin%% (only real satin does; see "
                        "--satin-lean). Off by default.")
    p.add_argument("--vwidth-satin", action=argparse.BooleanOptionalAction, default=False,
                   help="Variable-width satin (experimental): build each satin column directly "
                        "from its centerline, offsetting the rails by the LOCAL half-width "
                        "(centerline-to-boundary distance, the medial-axis idea) instead of one "
                        "average width via stroke_to_satin. Fixes --satin-lean's under-coverage "
                        "on bold/modulated strokes. Falls back to fixed-width per column on "
                        "geometry failure. Off by default.")
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
            fill_method=args.fill_method,
            lettering=args.lettering,
            purify_colors=args.purify_colors,
            open_counters=args.open_counters,
            pull_compensation_mm=args.pull_comp_mm,
            fabric=args.fabric,
            fill_underlay=args.fill_underlay,
            satin_underlay=args.satin_underlay,
            thin_line_run=args.thin_line_run,
            branch_satin=args.branch_satin,
            snap_black=args.snap_black,
            auto_route=args.auto_route,
            realistic_preview=args.realistic_preview,
            gradient=args.gradient,
            category=args.category,
            satin_lean=args.satin_lean,
            spine_fill=args.spine_fill,
            vwidth_satin=args.vwidth_satin,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    pipeline.run(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
