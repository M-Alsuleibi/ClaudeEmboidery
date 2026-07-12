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

# Fabric -> automatic pull-compensation per side (mm). From the Wilcom Reference Manual
# guideline table (p429; see wilcom-manual-rules.md): firmer / low-stretch fabrics need
# less overstitch, stretchy / pile fabrics need more. `--fabric` sets the pull-comp
# default; an explicit `--pull-comp-mm` still overrides it.
FABRIC_PULL_COMP = {
    "cotton": 0.20, "drill": 0.20, "denim": 0.20,    # firm / low stretch  (manual: 0.20)
    "silk": 0.30,                                     # medium
    "t-shirt": 0.35, "jersey": 0.35, "knit": 0.35,   # stretchy            (manual: 0.35)
    "fleece": 0.40, "jumper": 0.40, "terry": 0.40,   # very stretchy / pile (manual: 0.40)
}
SUPPORTED_FABRICS = tuple(FABRIC_PULL_COMP)
_DEFAULT_PULL_COMP_MM = 0.20  # historical default when neither --fabric nor --pull-comp-mm is given

# Per-category default thread-colour count, used when --colors is omitted. Derived from the
# ground-truth fingerprint medians (data/category_profiles.json) reinforced by the manual's
# photo colour bands (grayscale 5-6, simple 7-10, complex 14-16; p1091). Real production is
# far more sparing with thread than the old flat default of 8 — arabic / decoration /
# simple-shapes are typically MONOCHROME. anime has no ground truth, so it takes the manual's
# mid photo band. A colourful design in a monochrome-median category should pass an explicit
# --colors (the "--colors 1 washout" trap cuts both ways). Explicit --colors always wins.
CATEGORY_COLORS = {
    "letters": 2, "arabic": 1, "3D": 8, "anime": 8,
    "simple-shapes": 1, "decoration": 1, "numbers": 4,
}
# NB anime = 8 (was 12) and anime is now satin-dominant, from the first real anime ground-truth
# pair (pink-goku: 7 colours, 82.9% satin). See svg-and-geometry-approach/FINDINGS.md. n=1 —
# firm up with more anime pairs.
_DEFAULT_NUM_COLORS = 8  # when neither --colors nor --category is given


@dataclass(frozen=True)
class PipelineConfig:
    """One conversion request: a photo + a target size + knobs."""

    input_path: Path
    output_dir: Path
    name: str
    # Exactly one of these is set by the user; the other is derived from aspect ratio.
    target_width_mm: float | None = None
    target_height_mm: float | None = None
    # Thread-colour count. None => resolve from the category prior (CATEGORY_COLORS) if a
    # category is given, else the flat default 8. See `resolved_num_colors`.
    num_colors: int | None = None
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
    # pull-comp and/or drop the underlay to keep thin marks crisp. `None` => resolve from
    # `fabric` (FABRIC_PULL_COMP) if set, else the 0.2 mm default. See `resolved_pull_comp_mm`.
    pull_compensation_mm: float | None = None
    fill_underlay: bool = True
    # Target fabric (--fabric): sets the default pull-compensation from the manual's fabric
    # table (FABRIC_PULL_COMP: cotton/denim 0.20, silk 0.30, tee/knit 0.35, fleece/terry 0.40).
    # A no-op if --pull-comp-mm is given explicitly. None => use the 0.2 mm default.
    fabric: str | None = None
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
    # Now IMPLIES variable-width satin (see vwidth_satin): the old blocker was that FIXED-width
    # satins under-cover a modulated stroke, but building the rails at the local half-width fixes
    # it. Measured on the Ramadan calligraphy: satin_frac 0->100 (matches truth) AND coverage
    # 97.9%->99.3%, shape-IoU 67%->81%, over-ink 1.43x->1.22x — better than the fill it replaces.
    # Still opt-in + a no-op unless the category is satin-dominant (it restructures the sew path).
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
    # Spine-guided fill (step 5, experimental): a region that lands in a FILL tier (branchy
    # stroke in the satin band, or a broad blob) is normally stitched as a flat angle-fixed
    # tatami and its extracted centerlines are discarded. With --spine-fill, keep the region's
    # longest centerline as an Ink-Stitch guided_fill GUIDE so the fill rows follow the shape's
    # medial axis instead of a single fixed angle (the PEmbroider hatchSpine idea, reusing the
    # centerlines the tier already computes). This is a DIRECTIONAL / visual improvement only:
    # a guided fill is still low-reversal rows, so it does NOT raise the fingerprint's satin%
    # (only real satin columns do — see --satin-lean / --branch-satin). Off by default.
    spine_fill: bool = False
    # Underlap (step 4): production objects OVERLAP — an earlier-sewn fill extends UNDER its
    # later-sewn neighbour by this many mm so fabric pull can't open a white gap at the seam
    # (measured on abutting rects: 7.7 uncovered px per mm of seam in the ±0.4 mm band without
    # it). Distinct from pull-comp: pull-comp widens STITCHES uniformly at digitize time;
    # underlap moves the traced GEOMETRY, only along seams, only into later-sewn colours
    # (background and dropped counter holes are never claimed). 0 disables (exact old trace).
    underlap_mm: float = 0.5
    # Auto-repair (steps 2/3): act on the artwork problems the analyzer only WARNED about,
    # the way a production digitizer edits the art before digitizing: ① sub-sewable specks
    # (< ~1.5 mm²) merge into their surrounding colour (never into background; dotted
    # patterns — >=3 same-colour specks — are kept); ② isolated hairlines thinner than the
    # 0.8 mm run minimum are thickened to ~1 mm (into background only; a >30 % hairline
    # design gets the "enlarge" advice instead — don't fatten calligraphy wholesale);
    # ③ palette colours within ΔE<5 that matched the SAME thread cone merge before tracing.
    # Every action is logged as "auto-repaired: ...". --no-auto-repair = old behaviour.
    auto_repair: bool = True
    # Travel planning (step 5 post-pass): production sews near-continuously (pink-goku:
    # 0 trims; we used to trim after every region). Chains each colour's pieces nearest-
    # neighbour, pins fill entries/exits to the junction points (Ink-Stitch's
    # starting_point/ending_point object commands — probed: they snap to the target's
    # nearest boundary point), and drops trim_after ONLY where the straight travel is
    # <= ~12mm AND >=90% covered by later-sewn stitching or the colour's own regions —
    # never where the thread would show. On by default; --no-travel-plan restores
    # trim-after-every-region.
    travel_plan: bool = True
    # Outline objects (step 5 post-pass): production designs are LAYERED — the pink-goku
    # ground-truth pair decomposes into 118 fill + 217 OUTLINE objects (satin borders/detail
    # sewn ON TOP of the fills), which is where most of its 82.9% satin comes from. This pass
    # adds a closed satin border riding each substantial fill region's boundary (outer edge
    # kissing the boundary, inner half overlapping the fill — deliberate, like production).
    # Tri-state: None = AUTO (on for a satin-dominant category per the ground-truth
    # fingerprint, off otherwise); True/False force it. Resolved in stitches (needs the
    # fingerprint's satin-dominance, which config can't import).
    outline_objects: bool | None = None
    # Variable-width satin (step 5): build each satin column DIRECTLY from its centerline + region
    # boundary, offsetting the two rails by the LOCAL half-width (distance from the centerline to
    # the boundary — the medial-axis / hatchSpineVF idea) instead of a single average width fed
    # through stroke_to_satin. Fixes --satin-lean's under-coverage on bold/modulated strokes (its
    # fixed-width satins can't fill a thick belly + thin ends). Measured win on the Ramadan
    # calligraphy vs fixed-width: coverage 97.9->99.3%, shape-IoU 67->81%, over-ink 1.43x->1.22x,
    # and it reads satin_frac=100 like the ground truth. Falls back to fixed-width per column on
    # any geometry failure. Off by default on its own, but IMPLIED by --satin-lean.
    vwidth_satin: bool = False

    @property
    def resolved_num_colors(self) -> int:
        """The colour count actually used (step 2): explicit --colors wins, else the
        category prior (CATEGORY_COLORS), else the flat default 8."""
        if self.num_colors is not None:
            return self.num_colors
        if self.category is not None:
            return CATEGORY_COLORS.get(self.category, _DEFAULT_NUM_COLORS)
        return _DEFAULT_NUM_COLORS

    @property
    def resolved_pull_comp_mm(self) -> float:
        """The pull-compensation actually used (step 5): explicit --pull-comp-mm wins, else
        the fabric's value (FABRIC_PULL_COMP), else the 0.2 mm default."""
        if self.pull_compensation_mm is not None:
            return self.pull_compensation_mm
        if self.fabric is not None:
            return FABRIC_PULL_COMP.get(self.fabric, _DEFAULT_PULL_COMP_MM)
        return _DEFAULT_PULL_COMP_MM

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
        if self.num_colors is not None and self.num_colors < 1:
            raise ValueError("num_colors must be >= 1")
        if self.category is not None and self.category not in SUPPORTED_CATEGORIES:
            raise ValueError(
                f"Unknown category {self.category!r}; "
                f"supported: {', '.join(SUPPORTED_CATEGORIES)}"
            )
        if self.fabric is not None and self.fabric not in FABRIC_PULL_COMP:
            raise ValueError(
                f"Unknown fabric {self.fabric!r}; "
                f"supported: {', '.join(SUPPORTED_FABRICS)}"
            )
        if not (0.0 <= self.underlap_mm <= 2.0):
            raise ValueError("underlap_mm must be between 0 (off) and 2.0")

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

    @property
    def working_svg_path(self) -> Path:
        """The stitch-ready SVG (step 5): every path carries its inkstitch:* object type +
        params — the editable, object-level design, before it's flattened to the VP3. Kept as
        a deliverable (the VP3 discards the object structure)."""
        return self.output_dir / f"{self.name}_working.svg"


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

    # Step 5 — stitches: set only when the whole-design digitize hung and the per-colour-
    # group fallback ran — the working per-group SVGs in sew order (1-2 files per group).
    # Step 6 composites the realistic preview from these instead of re-hitting the hang.
    per_group_svgs: list[Path] | None = None

    # Step 7 — verify: pass/fail + metrics, gates the handoff to Phase B.
    verification: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
