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

# Production categories (the router's classes). Used by step 7's fingerprint drift check
# to compare a run against the ground-truth profile for its category (data/category_profiles.json).
SUPPORTED_CATEGORIES = (
    "letters", "arabic", "3D", "anime", "simple-shapes", "decoration", "numbers",
)

# Ink-Stitch fill methods for solid regions (step 5). `auto_fill` routes one
# continuous path (best for compact shapes, but its travel routing is O(complex)
# and can time out on long thin sprawling regions like calligraphy). `contour_fill`
# follows the shape contour inward — fast and natural for calligraphic strokes.
SUPPORTED_FILL_METHODS = (
    "auto_fill", "contour_fill", "meander_fill", "guided_fill", "circular_fill",
)


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
    # Ink-Stitch fill method for solid fill regions (step 5). Default `auto_fill`;
    # use `contour_fill` for calligraphy / long thin shapes where auto_fill's travel
    # routing is pathologically slow (it timed out at 900s on the hamdollelah piece).
    fill_method: str = "auto_fill"
    # Lettering mode: for block / typeset glyphs (not cursive calligraphy). Routes
    # letter strokes to satin columns (dissecting each glyph into its stroke-columns
    # rather than filling it), raises the satin-width ceiling, and snaps inks to
    # pure colour. Learned from the 10000.VP3 ground-truth (see letters knowledge §8a).
    lettering: bool = False
    # Purify colours only (no satin dissection): snap near-pure primaries to pure and
    # keep custom/muted brand colours verbatim (the 12000.VP3 rule — pure Yellow/Black,
    # custom teal kept). Decoupled from `lettering` so a *mixed* design (display caps +
    # cursive script, which dissection would shatter) can still get faithful colours on
    # the safe default fill/satin classification. Implied by `lettering`.
    purify_colors: bool = False
    # Open letter counters: drop page-coloured regions *enclosed* by ink (the hole in
    # e/B/g, the open loop of a script descender) to background so they read through,
    # instead of filling them solid. None = auto (on for letter modes — letterforms
    # always have open counters); True/False forces it. See preprocess._open_counters.
    open_counters: bool | None = None
    # Stitch-side thickening knobs (step 5). Every fill/satin is widened by a fixed
    # pull-compensation (fabric-pull comp) and, for fills, an underlay pass — together
    # ~0.2-0.4 mm per side. That fixed band over-fattens FINE decoration (thin tashkeel
    # on Arabic calligraphy), making them read heavier than the source art. Lower the
    # pull-comp and/or drop the underlay to keep thin marks crisp. Defaults preserve
    # the production behaviour; opt in via --pull-comp-mm / --no-fill-underlay.
    pull_compensation_mm: float = 0.2
    fill_underlay: bool = True
    # Satin underlay (step 5): lay a center-walk + contour underlay under every
    # satin column so its edges don't tunnel/pucker ("always underlay your satins").
    # On by default — the production norm; drop it to compare or to keep a very fine
    # column light. Ink-Stitch sizes the underlay insets/stitch-length itself.
    satin_underlay: bool = True
    # Thin-line running stitch (step 5): a linework colour whose median stroke width
    # is below the min-satin-width (~1.6 mm) is too thin to satin without fattening,
    # so each of its centerlines is stitched as a running/bean (triple) stitch — the
    # playbook's "line < 1.6 mm -> run/triple-run" object (a logo keyline). On by
    # default; drop it to force such colours into (clamped-up) narrow satins as before.
    # Ignored under --lettering (there thin strokes are still meant to satin).
    thin_line_run: bool = True
    # Branch satin (step 5): dissect a *branchy* stroke region in the satin width band into
    # one satin column per branch — generalising lettering's glyph dissection to organic art
    # (a forked calligraphic stroke, an ornament limb). Off by default: it restructures the
    # sew path and, since only the long branches are satined, can leave small gaps at
    # junctions, so it's opt-in. Guarded so it fires only on a FEW long branches that are
    # most of the skeleton (a dense mesh like a turtle-shell band stays one fill). No-op
    # under --lettering (which already dissects). See stitches._linework_prepass.
    branch_satin: bool = False
    # Satin-lean (step 5): for a satin-dominant category (per the ground-truth fingerprint —
    # arabic/decoration/letters/…), raise the satin ceiling + force branch dissection so bold
    # strokes become satin columns instead of tatami fills, matching the truth's ~100% satin.
    # OFF by default and DELIBERATELY so: the pipeline's fixed-width satins UNDER-COVER a
    # bold/modulated stroke (measured on the Arabic run: satin% 0->100 matched the truth but
    # source-coverage fell 99.9%->81.6%). It's the trace-vs-hand-digitize boundary — a faithful
    # satin needs variable width (Phase-B craft). Opt in only when the production satin *look*
    # matters more than pixel coverage; a no-op unless the category is satin-dominant.
    satin_lean: bool = False
    # Production category (letters/arabic/3D/anime/simple-shapes/decoration/numbers) for
    # step-7's fingerprint drift check — the run is scored against that category's ground-truth
    # profile (data/category_profiles.json: satin%, colours, density, satin width). None => verify
    # infers the nearest category by feature match. Purely informational (never fails the gate).
    category: str | None = None
    # Black-ink snap (step 2): dedicate one palette slot to pure black and route the
    # near-black, near-neutral pixels (a logo's outline/keyline, eye pupils) to it.
    # Quantisation otherwise averages a thin anti-aliased black outline into a dark
    # brown and loses it; this keeps the keyline crisp WITHOUT over-saturating muted
    # colours the way --purify-colors does (which snaps every near-primary, turning a
    # muted orange neon). Gated: a no-op unless the art has a real near-black
    # population, so it's safe to leave on. On by default.
    snap_black: bool = True
    # Auto-route (step 5 post-pass): run Ink-Stitch's auto_satin / auto_run PER COLOUR
    # to thread each colour's satin columns / running stitches into one connected,
    # optimally-ordered path — underpathing between adjacent pieces instead of trimming,
    # and picking entry/exit direction. Cuts travel + trims/jumps on satin- or
    # run-heavy designs (lettering, outlines). Off by default: it restructures the sew
    # path, and on spatially-scattered pieces (Arabic dots) a single path can add
    # travel — opt in per design via --auto-route.
    auto_route: bool = False
    # Realistic preview (step 6): render the preview with Ink-Stitch's own realistic
    # thread renderer (stitch_plan_preview, realistic-vector) rasterized via cairosvg
    # (no Inkscape needed) instead of the fast polyline draw. Honest stroke widths +
    # thread look; costs an extra stitch-plan pass. Falls back to the polyline preview
    # if it errors or cairosvg is missing. On by default.
    realistic_preview: bool = True
    # Gradient shading (steps 4/5): de-posterize smooth tonal areas. Adjacent palette
    # colours that are the same hue but different lightness (e.g. a shell's light/dark
    # orange bands) are merged into one region stitched as a smooth density-modulated
    # gradient via Ink-Stitch gradient_blocks, instead of hard flat bands. Off by default
    # (experimental: the hue/lightness/adjacency heuristic can over- or under-merge).
    gradient: bool = False

    @property
    def purify(self) -> bool:
        """Whether to snap inks to their intended pure/custom colour (step 2 & 3)."""
        return self.lettering or self.purify_colors

    @property
    def should_open_counters(self) -> bool:
        """Whether to drop enclosed page-coloured counters to background (step 2)."""
        return self.purify if self.open_counters is None else self.open_counters

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
        if self.fill_method not in SUPPORTED_FILL_METHODS:
            raise ValueError(
                f"Unknown fill method {self.fill_method!r}; "
                f"supported: {', '.join(SUPPORTED_FILL_METHODS)}"
            )
        if self.num_colors < 1:
            raise ValueError("num_colors must be >= 1")
        if self.category is not None and self.category not in SUPPORTED_CATEGORIES:
            raise ValueError(
                f"Unknown category {self.category!r}; "
                f"supported: {', '.join(SUPPORTED_CATEGORIES)}"
            )

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

    # Step 5 — stitches: path to the stitch-ready SVG (inkstitch params injected).
    # Kept so step 6 can render the realistic preview from it.
    stitch_svg_path: Path | None = None

    # Step 5 — stitches: in-memory stitch model (pyembroidery pattern or similar).
    stitch_pattern: Any | None = None

    # Step 7 — verify: pass/fail + metrics, gates the handoff to Phase B.
    verification: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
