"""Step 5 - Generate stitches (Ink-Stitch headless).

Build a stitch-ready SVG, then invoke the vendored, self-contained Ink-Stitch
binary to digitize it and read the VP3 back into ctx.stitch_pattern.

Headless (no Inkscape GUI needed for export):
    inkstitch --extension=zip --format-vp3=True design.svg > out.zip

Stitch-type assignment (the goal doc's "right stitch type per region") — each REGION
(connected component) is tiered by its OWN stroke width at final size, so one colour can
mix a thin keyline (run), a medium stroke (satin) and a solid blob (fill). A colour first
enters the pre-pass only if its AREA-weighted width is below the ceiling (a solid fill
colour isn't skeletonised); then per block, by width (region area / centerline length):
  - "run" colours (thinner than ~1.6 mm — the min-satin-width law, §0b.2 of the
    playbook): too thin to satin without fattening, so each substantial
    centerline becomes a **running / bean (triple) stitch** (fill_to_stroke ->
    stroke_method=running_stitch). This is the playbook's "line < 1.6 mm ->
    run/triple-run" object, e.g. a logo's black keyline.
  - "satin" colours (median width up to the ceiling — calligraphy, text, thin
    columns) get their *substantial* strokes converted to real satin columns:
    fill_to_stroke (centerline) -> stroke_to_satin, laid over a **center-walk +
    contour underlay** so the column doesn't tunnel/pucker ("always underlay your
    satins"). A region's fill is kept (tatami) if it has no substantial
    centerline (blobs, tiny fragments).
  - all remaining fills get best-practice params: fill underlay, ~0.4mm density,
    pull compensation, and trim_after (so a colour's disjoint regions aren't
    joined by long travel stitches; each trim is a Wilcom Break-Apart boundary).

True variable-width satin on freeform script is the human-refinement step; here
a single approximate width per colour is used. Anything that errors in the
linework pre-pass falls back to plain fills, so the step always produces a valid
design.

Two DIFFERENT gap-fighting mechanisms exist — don't confuse them:
  - **pull compensation** (here, step 5): widens the STITCHES of every object uniformly
    at digitize time (`pull_compensation_mm`), compensating fabric pull on the object
    itself. It fattens everything, including edges facing background.
  - **underlap** (step 4, `--underlap-mm`): moves the traced GEOMETRY — an earlier-sewn
    colour's region extends 0.5 mm UNDER its later-sewn neighbour, only along shared
    seams, so pull can't open a white gap between abutting colours (the production
    object-overlap). Background and opened counters are never claimed.
"""

from __future__ import annotations

import io
import math
import os
import re
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pyembroidery as pe
from lxml import etree
from scipy import ndimage

from ..config import PipelineContext
from ..fingerprint import category_satin_dominant, load_profiles
from .. import priors

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BIN = _REPO_ROOT / "vendor" / "inkstitch" / "bin" / "inkstitch"
# A dense, many-region fill design (e.g. cursive lettering at 140 mm) can take
# several minutes in Ink-Stitch; 300 s was too tight and timed out mid-fill.
_TIMEOUT_S = 900
_SATIN_TIMEOUT_S = 600
_REALISTIC_PREVIEW_PX = 800  # long side of the realistic preview raster (matches
                             # emit._PREVIEW_MAX_PX so both preview modes are one size)

_SVG_NS = "http://www.w3.org/2000/svg"
_INKSTITCH_NS = "http://inkstitch.org/namespace"

# Best-practice fill/satin params injected before digitizing. Pull-compensation and
# the fill underlay are config-tunable (PipelineConfig.pull_compensation_mm /
# fill_underlay): the defaults (0.2 mm, underlay on) are the production norm, but fine
# decoration (thin Arabic tashkeel) reads heavier than the source unless they're lowered.
def _fill_params(pull_comp_mm: float, fill_underlay: bool) -> dict[str, str]:
    return {
        "fill_underlay": "True" if fill_underlay else "False",
        "row_spacing_mm": "0.4",
        "pull_compensation_mm": f"{pull_comp_mm:g}",
        "trim_after": "True",
    }


def _satin_params(pull_comp_mm: float, satin_underlay: bool,
                  satin_spacing_mm: float | None = None) -> dict[str, str]:
    # Satins get pull-comp + trim_after (so they aren't joined by long travels).
    # Underlay is the "always underlay your satins" rule: a center-walk run down
    # the spine + a contour run inset from each long edge stabilise the column so
    # its edges don't tunnel or pucker. Ink-Stitch's own defaults size the insets/
    # stitch-length; we just switch the two passes on. `satin_spacing_mm` is the
    # AUTHORED zigzag density from the pair-trio props (a satin-only category sews
    # at the digitizer's own spacing — arb: auto spacing 0.24mm @ 90%); None keeps
    # Ink-Stitch's default.
    params = {"pull_compensation_mm": f"{pull_comp_mm:g}", "trim_after": "True"}
    if satin_spacing_mm:
        params["zigzag_spacing_mm"] = f"{satin_spacing_mm:g}"
    if satin_underlay:
        params["center_walk_underlay"] = "True"
        params["contour_underlay"] = "True"
    return params


# Running / bean stitch for sub-satin linework (§0a: "line < ~1.6 mm ->
# run/triple-run"). A thin keyline is stitched *along* its centerline, not
# fattened into a too-narrow satin. bean_stitch_repeats=1 -> a triple (bean) pass
# so the line reads solid; a single running stitch can look sparse on a curve.
#
# Variable run length (Wilcom manual p219-220, wilcom-manual-rules.md §2): instead of one
# fixed length, set the nominal to the manual's straight-run maximum (~4.0 mm, "mimic
# hand-made embroidery") and let Ink-Stitch's tolerance -- the manual's "chord gap" -- split
# stitches shorter on tight curves so the line follows the shape closely (toward the manual's
# ~1.8 mm). Long, few penetrations on straights; tight on curves.
_RUN_STITCH_LEN_MM = 4.0
_RUN_TOLERANCE_MM = 0.2     # chord gap: max deviation from the path before a stitch is split
_RUN_BEAN_REPEATS = "1"


def _run_params() -> dict[str, str]:
    return {
        "stroke_method": "running_stitch",
        "running_stitch_length_mm": f"{_RUN_STITCH_LEN_MM:g}",
        "running_stitch_tolerance_mm": f"{_RUN_TOLERANCE_MM:g}",
        "bean_stitch_repeats": _RUN_BEAN_REPEATS,
        "trim_after": "True",
    }

# Satin classification / generation tunables.
_SATIN_MAX_WIDTH_MM = 3.0   # DEFAULT satin/fill boundary (conservative): a column up to this wide
                            # satins, wider fills. Kept low for non-satin-dominant categories (3D /
                            # anime) whose shaded solids are tatami fills — raising it over-satins
                            # them (measured: gold 2026 went 92% satin vs 3D truth ~7%).
_SATIN_DOMINANT_CEILING_MM = 7.0  # satin/fill boundary for a SATIN-DOMINANT category (arabic /
                            # letters / decoration / simple-shapes / numbers, per the ground-truth
                            # fingerprint): the Wilcom-manual ceiling — satin covers to ~7mm via
                            # variable width (see wilcom-manual-rules.md §1). Closes the satin gap
                            # by default ONLY where the truth is satin-heavy.
_SATIN_FIXED_MAX_MM = 3.0   # within the satin band, columns up to this stay FIXED-width (narrow,
                            # proven); WIDER ones (3-7mm) build VARIABLE-width — a uniform width
                            # under-covers a modulated wide stroke — and get a zigzag underlay
                            # instead of relying on the center-walk (manual underlay-by-width p412).
_RUN_MAX_REGION_AREA_MM2 = 150.0  # run-demotion guard, HALF 1: above this area a
                            # sub-1.6mm-average region is suspect. Alone it would also
                            # block a long genuine hairline (a 140mm wavy keyline is
                            # ~210mm2), so demotion is only blocked when the region is
                            # ALSO spur-dominated (long_frac < _BRANCH_COVER_MIN): a
                            # merged calligraphy band (arb middle arc: 1,090mm2 at
                            # "1.36mm" avg width, long_frac 0.16 — thin connectors
                            # dragging broad strokes under the threshold) becomes bean
                            # runs covering ~15% and its fill never sews (the
                            # missing-middle-arc incident). Such a region stays a fill
                            # (the "large regions = tatami" hard rule).
_RUN_MAX_WIDTH_MM = 1.6     # below this a linework colour is too thin to satin ->
                            # running/bean stitch (the min-satin-width law, §0b.2)
_MIN_REGION_PX = 20         # ignore speckle components when measuring a colour's width
_MIN_LINEWORK_PX = 250      # a *broad* colour is pulled into the pre-pass only if it holds
                            # a sub-ceiling region at least this big (on the ~1200px work
                            # canvas): a substantial keyline, not a quantisation scrap
_MAX_RUN_STROKES = 400      # guard: pathologically many run strokes -> plain fills
_MIN_SATIN_PTS = 15         # a centerline needs at least this many points to satin
_MAX_SPURS_FOR_SATIN = 4    # a block is a "single column" only if it yields <= this
                            # many centerlines total (1 real + a few tiny spurs);
                            # more than that = a complex shape -> keep as one fill
_MAX_SATIN_COLUMNS = 80     # guard against pathological slowness
_MAX_BRANCH_SATINS = 12     # --branch-satin: dissect a branchy stroke block into at most
                            # this many satins (more long branches => a mesh, not strokes;
                            # keep it one fill — a dense network shatters into junk pieces)
_BRANCH_COVER_MIN = 0.6     # ...and only when the long centerlines are >= this fraction of
                            # the skeleton length (else per-branch satins leave big gaps)
_SATIN_MIN_W_MM = 1.0       # clamp satin width
_SATIN_MAX_W_MM = 7.0

# Lettering mode (block/typeset glyphs): block-letter strokes are wider than
# calligraphy, and the production norm is to dissect each glyph into stroke-columns
# and satin every one (not just the single-column case). See letters knowledge §8a.
_LETTERING_SATIN_MAX_WIDTH_MM = 9.0   # treat strokes up to this wide as satin-able
_LETTERING_SATIN_MAX_W_MM = 6.0       # cap satin width near the production ~3.4 mm band
_LETTERING_MIN_SATIN_PTS = 10         # keep shorter strokes (letter arms) as satins
_LETTERING_MAX_SATIN_COLUMNS = 240    # a long word dissects into many columns


def _satin_ceiling(lettering: bool, satin_lean: bool, satin_dominant: bool,
                   category: str | None = None, log: bool = False) -> float:
    """The region-width satin/fill boundary (mm), by regime. Lettering / --satin-lean push the
    ceiling highest (dissect wide block strokes; explicit user regimes always win). Otherwise a
    category with ingested PAIRS uses its MEASURED satin/fill width crossover (pair prior,
    clamped 3-9mm — the loop the pairs exist to close); else a satin-DOMINANT category takes the
    manual's ~7mm and everything else (3D/unknown, whose shaded solids are tatami fills) keeps
    the conservative 3mm so a raised ceiling can't over-satin them. A SATIN-ONLY category's
    prior (the authored Auto-Split length — the width beyond which production splits the long
    stitches rather than switching to fill) outranks even the lettering/satin-lean blanket:
    the trio's authored settings define correct, not the regime constant."""
    pri = priors.satin_ceiling_mm(category)
    if pri is not None and priors.satin_only(category):
        ceiling, n_pairs = pri
        if log:
            print(f"      pair prior: satin ceiling {ceiling:.1f}mm, satin-only "
                  f"(n={n_pairs} pair{'s' if n_pairs != 1 else ''})", flush=True)
        return ceiling
    if lettering or satin_lean:
        return _LETTERING_SATIN_MAX_WIDTH_MM
    if pri is not None:
        ceiling, n_pairs = pri
        if log:
            print(f"      pair prior: satin ceiling {ceiling:.1f}mm "
                  f"(n={n_pairs} pair{'s' if n_pairs != 1 else ''})", flush=True)
        return ceiling
    return _SATIN_DOMINANT_CEILING_MM if satin_dominant else _SATIN_MAX_WIDTH_MM


def _candidate_binary() -> Path:
    env = os.environ.get("INKSTITCH_BIN")
    return Path(env) if env else _DEFAULT_BIN


def binary_available() -> bool:
    return _candidate_binary().is_file()


def _locate_binary() -> Path:
    cand = _candidate_binary()
    if not cand.is_file():
        raise RuntimeError(
            f"Ink-Stitch binary not found at {cand}.\n"
            "Vendor the Linux portable bundle under vendor/inkstitch/ or set "
            "INKSTITCH_BIN (see README)."
        )
    return cand


def run(ctx: PipelineContext) -> None:
    # Cross-stitch categories (tatreez tatreez): counted cross-stitch is a distinct stitch
    # primitive (a fixed grid of X motifs), not the run/satin/tatami tiers. It's built
    # directly as stitches (no Ink-Stitch) from the quantized image — no traced SVG needed
    # (step 4 skips itself for these categories: vtracer on a pixel-grid mock-up with AA
    # speckle allocates gigabytes for paths nothing would read — it OOM-killed a 400mm
    # tatreez panel at ~5GB RSS).
    if ctx.config.resolved_cross_stitch:
        _run_cross_stitch(ctx)
        return

    # Sketch-stitch categories (animals fur/feather): layered run strokes along the
    # measured fur-direction field — also built directly (no Ink-Stitch, no traced SVG).
    if ctx.config.resolved_sketch_stitch:
        _run_sketch_stitch(ctx)
        return

    if ctx.svg_path is None:
        raise RuntimeError("stitches requires ctx.svg_path; run trace first.")

    binary = _locate_binary()
    # The stitch-ready ("working") SVG: every path carries its inkstitch:* object type + params.
    # It's a kept deliverable (the object structure is lost when flattened to the VP3) and also
    # feeds step 6's realistic preview. The _A/_B fill_to_stroke/stroke_to_satin passes derive
    # their names from this stem, so they're the throwaway intermediates.
    ready_svg = ctx.config.working_svg_path
    n_satin, n_run = _build_stitch_svg(ctx, binary, ready_svg)

    # Outline objects (the production "outline family"): closed satin borders layered over
    # the substantial fills. Tri-state flag: explicit --outline-objects wins; AUTO = on for
    # a satin-dominant category (whose ground truth is outline/satin-heavy), off otherwise.
    outline_on = (ctx.config.outline_objects if ctx.config.outline_objects is not None
                  else category_satin_dominant(ctx.config.category))
    if outline_on:
        n_satin += _add_outline_objects(ctx, binary, ready_svg)

    # Travel planning: chain each colour's pieces, steer fill entries/exits (probed:
    # Ink-Stitch's starting_point/ending_point object commands snap to the target's
    # nearest boundary point), and drop trim_after where the travel is short + covered.
    if ctx.config.travel_plan:
        _plan_travel(ctx, ready_svg)

    if ctx.config.auto_route and (n_satin or n_run):
        _auto_route(ctx, binary, ready_svg)

    ctx.stitch_svg_path = ready_svg

    pattern, group_svgs = _digitize(binary, ready_svg)

    # Authored connector chains (see the block comment above _split_long_travels):
    # a trim-after-off category with an authored Jump length splits its mid-length
    # travels into <= jump_mm segments, exactly like the reference sews.
    if priors.trim_after_off(ctx.config.category):
        jump = priors.authored_jump_mm(ctx.config.category)
        if jump:
            n_split = _split_long_travels(pattern, jump)
            if n_split:
                print(f"      connectors -> {n_split} segment(s) added splitting "
                      f"travels > {_TRAVEL_SPLIT_MIN_MM:g}mm into <= {jump:g}mm "
                      f"chains (authored Connectors: Jump)", flush=True)

    ctx.stitch_pattern = pattern
    ctx.per_group_svgs = group_svgs
    _print_summary(pattern, n_satin, n_run)


# Connector encoding, measured against the reference VP3 (arb trio):
# - A STITCH->JUMP reclassification was tried and REVERTED: VP3 has no jump opcode
#   (pyembroidery drops JUMPs on write / decodes the 80-01 long-move escape back as
#   STITCH), so converting only bloated the file with writer-split chains.
# - What production ACTUALLY does (movement histogram: 812 moves @4-6mm, 338 @6-8mm,
#   only 15 >8mm in 46k stitches) is split every within-colour connector into
#   segments of at most the authored Connectors "Jump" length (7.0mm), while the few
#   big arc-to-arc repositioning moves stay single long moves (up to 275.7mm, VP3
#   80-01 escapes). Our un-split 8-13mm hops (~3k of them) were the structural drift
#   that fragmented the design on Wilcom import.
_TRAVEL_SPLIT_MIN_MM = 8.0     # moves up to ~jump+tolerance stay single (ref keeps 6-8mm)
_TRAVEL_SPLIT_MAX_MM = 20.0    # above this = repositioning; the reference drapes it single


def _split_long_travels(pattern, jump_mm: float) -> int:
    """Split mid-length STITCH travel moves (_TRAVEL_SPLIT_MIN_MM < d <=
    _TRAVEL_SPLIT_MAX_MM) into equal segments of at most `jump_mm`, in place —
    the authored connector chain production sews. Returns segments added."""
    s_cmd = pe.STITCH & 0xFF
    lo = _TRAVEL_SPLIT_MIN_MM * 10.0
    hi = _TRAVEL_SPLIT_MAX_MM * 10.0
    seg = jump_mm * 10.0
    st = pattern.stitches
    out = []
    added = 0
    prev = None
    for stitch in st:
        x, y, c = stitch[0], stitch[1], stitch[2]
        if prev is not None and (c & 0xFF) == s_cmd and (prev[2] & 0xFF) == s_cmd:
            d = ((x - prev[0]) ** 2 + (y - prev[1]) ** 2) ** 0.5
            if lo < d <= hi:
                n = int(np.ceil(d / seg))
                for k in range(1, n):
                    t = k / n
                    out.append([prev[0] + t * (x - prev[0]),
                                prev[1] + t * (y - prev[1]), pe.STITCH])
                    added += 1
        out.append(stitch)
        prev = stitch
    if added:
        st[:] = out
    return added


def _run_cross_stitch(ctx: PipelineContext) -> None:
    """Step-5 cross-stitch path: build the counted-cross-stitch pattern directly and
    set ctx.stitch_pattern. No stitch-ready SVG (step 6 uses the polyline preview, which
    is faithful for an X-grid) and no per-group SVGs."""
    from .crossstitch import build_cross_stitch_pattern

    pitch = ctx.config.resolved_cross_stitch_pitch_mm
    pattern, n_cells, n_colours = build_cross_stitch_pattern(ctx, pitch)
    ctx.stitch_pattern = pattern
    ctx.stitch_svg_path = None
    ctx.per_group_svgs = None

    cmds = Counter(c & 0xFF for _, _, c in pattern.stitches)
    n_stitch = cmds.get(pe.STITCH & 0xFF, 0)
    n_trim = cmds.get(pe.TRIM & 0xFF, 0)
    xs = [s[0] for s in pattern.stitches]
    ys = [s[1] for s in pattern.stitches]
    w = (max(xs) - min(xs)) / 10 if xs else 0
    h = (max(ys) - min(ys)) / 10 if ys else 0
    print(f"      cross-stitch -> {n_cells} X-cells, {n_stitch} stitches, {n_colours} "
          f"colour(s), {n_trim} trim(s); extent ~{w:.1f}x{h:.1f}mm @ {pitch:.2f}mm grid")


def _run_sketch_stitch(ctx: PipelineContext) -> None:
    """Step-5 sketch-stitch path: build the fur/feather scribble pattern directly and
    set ctx.stitch_pattern. No stitch-ready SVG (step 6 uses the polyline preview,
    which is faithful for run strokes) and no per-group SVGs."""
    from .sketchstitch import build_sketch_pattern

    spacing = ctx.config.resolved_sketch_row_spacing_mm
    pattern, n_strokes, n_colours = build_sketch_pattern(ctx, spacing)
    ctx.stitch_pattern = pattern
    ctx.stitch_svg_path = None
    ctx.per_group_svgs = None

    cmds = Counter(c & 0xFF for _, _, c in pattern.stitches)
    n_stitch = cmds.get(pe.STITCH & 0xFF, 0)
    n_trim = cmds.get(pe.TRIM & 0xFF, 0)
    xs = [s[0] for s in pattern.stitches]
    ys = [s[1] for s in pattern.stitches]
    w = (max(xs) - min(xs)) / 10 if xs else 0
    h = (max(ys) - min(ys)) / 10 if ys else 0
    print(f"      sketch-stitch -> {n_strokes} stroke(s), {n_stitch} stitches, "
          f"{n_colours} colour(s), {n_trim} trim(s); extent ~{w:.1f}x{h:.1f}mm "
          f"@ {spacing:.2f}mm rows")


def render_realistic_preview(ctx: PipelineContext, svg: Path, dst: Path) -> bool:
    """Render a realistic thread preview of the stitch-ready SVG.

    Ink-Stitch's `stitch_plan_preview` (render-mode realistic-vector) draws the
    stitches as shaded *vector* threads into the SVG (design layer hidden); cairosvg
    then rasterizes that to PNG — no Inkscape needed (the `png_realistic` output
    extension shells out to the `inkscape` binary, which we deliberately don't have).
    A design that went through the per-group digitize fallback would re-hit the same
    combined-routing hang here, so it is previewed per group instead: each working
    per-group SVG keeps the full document canvas, so the rasters align pixel-for-pixel
    and alpha-composite in sew order. Best-effort: returns False on any failure so
    step 6 falls back to the fast polyline preview.
    """
    try:
        binary = _locate_binary()
        import cairosvg  # optional dependency; lazy import
    except Exception:
        return False

    sz = ctx.analysis.get("size_mm", {}) if ctx.analysis else {}
    w_mm = float(sz.get("width_mm", 1) or 1)
    h_mm = float(sz.get("height_mm", 1) or 1)
    size_kw = ({"output_width": _REALISTIC_PREVIEW_PX} if w_mm >= h_mm
               else {"output_height": _REALISTIC_PREVIEW_PX})

    if ctx.per_group_svgs:
        return _realistic_preview_composite(binary, ctx.per_group_svgs, dst, size_kw)

    tmp = dst.with_name(dst.stem + "_splan.svg")
    try:
        proc = subprocess.run(
            [str(binary), "--extension=stitch_plan_preview",
             "--render-mode=realistic-vector", "--layer-visibility=hidden",
             "--move-to-side=false", "--overwrite=true", "--render-jumps=false",
             str(svg)],
            capture_output=True, timeout=_PREVIEW_TIMEOUT_S,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return False
        tmp.write_bytes(_strip_command_markers(proc.stdout))
        cairosvg.svg2png(url=str(tmp), write_to=str(dst),
                         background_color="white", **size_kw)
        return True
    except Exception:
        return False
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def _strip_command_markers(svg_bytes: bytes) -> bytes:
    """Remove entry/exit command marker groups from a stitch-plan SVG before rasterizing
    the preview (their connectors are display:none but the symbol <use>s would render as
    faint blue dashes around the design). Best-effort: returns the input on any failure."""
    try:
        root = etree.fromstring(svg_bytes)
        for g in list(root.iter(f"{{{_SVG_NS}}}g")):
            if (g.get("id") or "").startswith("command_group"):
                g.getparent().remove(g)
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8")
    except Exception:
        return svg_bytes


def _realistic_preview_composite(binary: Path, group_svgs: list[Path], dst: Path,
                                 size_kw: dict) -> bool:
    """Realistic preview for a per-group-digitized design: stitch_plan_preview each working
    per-group SVG (they completed the digitize, so they complete here too), rasterize on the
    shared canvas with a transparent background, and alpha-composite in sew order. The frame
    anchors sit outside the viewBox, so rasterization clips them away."""
    try:
        import cairosvg
        from PIL import Image
    except Exception:
        return False
    out = None
    tmp = dst.with_name(dst.stem + "_splan.svg")
    try:
        for gs in group_svgs:
            proc = subprocess.run(
                [str(binary), "--extension=stitch_plan_preview",
                 "--render-mode=realistic-vector", "--layer-visibility=hidden",
                 "--move-to-side=false", "--overwrite=true", "--render-jumps=false",
                 str(gs)],
                capture_output=True, timeout=_PREVIEW_TIMEOUT_S,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                return False
            tmp.write_bytes(_strip_command_markers(proc.stdout))
            png = cairosvg.svg2png(url=str(tmp), **size_kw)  # transparent background
            layer = Image.open(io.BytesIO(png)).convert("RGBA")
            out = layer if out is None else Image.alpha_composite(out, layer)
        if out is None:
            return False
        white = Image.new("RGBA", out.size, "white")
        Image.alpha_composite(white, out).convert("RGB").save(dst)
        return True
    except Exception:
        return False
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# stitch-ready SVG (satin pre-pass + fill params)
# --------------------------------------------------------------------------- #
def _build_stitch_svg(ctx: PipelineContext, binary: Path, dst: Path) -> tuple[int, int]:
    """Write the stitch-ready SVG; return (satin columns made, run strokes made)."""
    # Gradient pre-pass: expand any gradient compound path (fill:url) into variable-
    # density colour blocks BEFORE the linework/fill classification (they end up in
    # `gradient*` groups the linework pass ignores; params handled in _apply_fill_params).
    src_svg = ctx.svg_path
    if ctx.config.gradient:
        grad_svg = dst.with_name(dst.stem + "_grad.svg")
        try:
            if _apply_gradient_blocks(binary, ctx.svg_path, grad_svg):
                src_svg = grad_svg
        except Exception as exc:
            print(f"      gradient_blocks pass failed ({type(exc).__name__}); flat fills")

    try:
        line_idx = _linework_indices(ctx)
    except Exception:  # classification is best-effort
        line_idx = set()

    pc, ul = _resolved_pull_comp(ctx), ctx.config.fill_underlay
    su = _resolved_satin_underlay(ctx)
    sp = _authored_satin_spacing(ctx)
    if not line_idx:
        _inject_params(src_svg, dst, ctx.config.fill_method, pc, ul, su, sp)
        return 0, 0
    try:
        return _linework_prepass(ctx, binary, line_idx, dst, src_svg)
    except Exception as exc:
        print(f"      linework pre-pass failed ({type(exc).__name__}: {exc}); using fills")
        _inject_params(src_svg, dst, ctx.config.fill_method, pc, ul, su, sp)
        return 0, 0


def _apply_gradient_blocks(binary: Path, src: Path, dst: Path) -> bool:
    """Run Ink-Stitch gradient_blocks on every gradient compound path (fill:url) in the
    trace SVG, converting each to variable-density colour blocks. Chains through dst.
    Returns True if at least one gradient path was expanded (else caller keeps src)."""
    try:
        root = etree.parse(str(src)).getroot()
    except Exception:
        return False
    grad_ids = [p.get("id") for p in root.iter(f"{{{_SVG_NS}}}path")
                if "fill:url(" in (p.get("style") or "") and p.get("id")]
    if not grad_ids:
        return False
    cur, processed = src, False
    for gid in grad_ids:
        try:
            _run_extension(binary, "gradient_blocks", [gid], [], cur, dst)
            cur, processed = dst, True
        except Exception as exc:
            print(f"      gradient_blocks ({gid}) skipped: {type(exc).__name__}")
    return processed


def _region_widths(mask: np.ndarray, mm_per_px: float) -> list[tuple[int, float]]:
    """(area_px, median stroke width mm) for each substantial connected component
    of a colour mask. The EDT is taken on the whole mask at once (components are
    separated by background, so they don't interfere and boundaries stay correct),
    then ridge widths are bucketed by component label."""
    dist = ndimage.distance_transform_edt(mask)
    structure = ndimage.generate_binary_structure(2, 2)  # 8-connectivity
    lbl, n = ndimage.label(mask, structure=structure)
    if n == 0:
        return []
    areas = np.bincount(lbl.ravel(), minlength=n + 1)  # index 0 == background
    ridge = (dist >= ndimage.maximum_filter(dist, size=3)) & (dist > 0)
    rl, rd = lbl[ridge], dist[ridge]
    out: list[tuple[int, float]] = []
    for k in range(1, n + 1):
        if areas[k] < _MIN_REGION_PX:
            continue
        w = rd[rl == k]
        if w.size:
            out.append((int(areas[k]), 2 * float(np.median(w)) * mm_per_px))
    return out


def _area_weighted_width(regions: list[tuple[int, float]], pct: float) -> float:
    """Width at the given area-weighted percentile — a colour's typical INK width.
    Unlike a ridge-pixel median it is robust to a scatter of thin scraps: a thin
    line is nearly all ridge, so by ridge-pixel count a few slivers can out-vote a
    colour whose bulk is one bold band (and, perversely, flip it 'run' as the design
    is ENLARGED — measured on the turtle shell band going satin@280/360 but run@480).
    Weighting by region AREA instead asks 'what does most of the ink look like'."""
    if not regions:
        return 0.0
    ordered = sorted(regions, key=lambda t: t[1])
    target = sum(a for a, _ in ordered) * pct / 100.0
    cum = 0
    for area, w in ordered:
        cum += area
        if cum >= target:
            return w
    return ordered[-1][1]


def _linework_indices(ctx: PipelineContext) -> set[int]:
    """Colours worth running through the linework pre-pass — those that hold satin-/run-able
    linework (calligraphy, text, thin columns, outlines, keylines) rather than being pure
    solid fill. A colour qualifies if EITHER:
      - its AREA-weighted width is below the satin ceiling (a mostly-linework colour), OR
      - it is otherwise broad (a solid blob dominates) BUT still carries a *substantial*
        sub-ceiling region (>= _MIN_LINEWORK_PX) — e.g. a logo whose black is a big solid
        wordmark PLUS a thin keyline: the keyline should be split out, not buried in a fill.

    This only *gates which colours get skeletonised* (a pure solid fill shouldn't be): the
    run / satin / fill verdict is taken later PER REGION in the pre-pass from each block's
    own width, so one colour can mix a thin keyline (run), a medium stroke (satin) and a
    solid blob (fill). The colour-level statistic is area-weighted (see _area_weighted_width)
    so it isn't skewed by a scatter of thin scraps; the _MIN_LINEWORK_PX floor keeps a broad
    colour out unless its thin part is a real object rather than quantisation noise."""
    img = np.asarray(ctx.preprocessed_image)
    opaque = img[..., 3] > 128
    mm_per_px = ctx.analysis["size_mm"]["width_mm"] / img.shape[1]
    lettering = ctx.config.lettering
    # satin-lean: when the declared category's ground truth is satin-dominant (arabic,
    # decoration, letters, …), raise the ceiling so bold strokes enter the linework pass and
    # become satin columns instead of tatami — moving toward the truth's ~100% satin.
    # A SATIN-ONLY pair prior (production digitizes zero fills — the arb trio) takes this
    # path AUTOMATICALLY, no flag needed: the trio defines the category's law.
    satin_dominant = category_satin_dominant(ctx.config.category)
    satin_only = priors.satin_only(ctx.config.category)
    satin_lean = ((ctx.config.satin_lean and satin_dominant) or satin_only) and not lettering
    width_ceiling = _satin_ceiling(lettering, satin_lean, satin_dominant,
                                   ctx.config.category, log=True)

    line: set[int] = set()
    for i, rgb in enumerate(ctx.palette):
        mask = opaque & np.all(img[..., :3] == np.array(rgb, np.uint8), axis=-1)
        if mask.sum() < 20:
            continue
        if satin_only:
            # satin-only production: every colour is linework by definition (no colour may
            # stay plain fills), so all of them enter the pre-pass.
            line.add(i)
            continue
        regions = _region_widths(mask, mm_per_px)
        if not regions:
            continue
        if _area_weighted_width(regions, 50) < width_ceiling or any(
            w < width_ceiling and area >= _MIN_LINEWORK_PX for area, w in regions
        ):
            line.add(i)
    return line


def _linework_prepass(
    ctx: PipelineContext, binary: Path, line_idx: set[int],
    dst: Path, src_svg: Path | None = None,
) -> tuple[int, int]:
    pc, ul = _resolved_pull_comp(ctx), ctx.config.fill_underlay
    su = _resolved_satin_underlay(ctx)
    sp = _authored_satin_spacing(ctx)
    src_svg = src_svg or ctx.svg_path
    root = etree.parse(str(src_svg)).getroot()
    line_path_ids: list[str] = []
    for g in root.iter(f"{{{_SVG_NS}}}g"):
        m = re.match(r"color(\d+)_", g.get("id") or "")
        if m and int(m.group(1)) in line_idx:
            line_path_ids += [p.get("id") for p in g.findall(f"{{{_SVG_NS}}}path")]
    if not line_path_ids:
        _inject_params(src_svg, dst, ctx.config.fill_method, pc, ul, su, sp)
        return 0, 0

    # Pass A: fill -> centerline strokes, keeping the original fills. Both satin
    # and run colours need the centerline; we branch per colour below.
    tmp_a = dst.with_name(dst.stem + "_A.svg")
    _run_extension(binary, "fill_to_stroke", line_path_ids,
                   ["--keep_original=True", "--threshold_mm=2"], src_svg, tmp_a)

    # thread colour per palette index (satin/run must keep its colour, not black)
    thread_hex = {
        i: "#{:02X}{:02X}{:02X}".format(*m["thread_rgb"])
        for i, m in enumerate(ctx.thread_map)
    }

    tree_a = etree.parse(str(tmp_a))
    root_a = tree_a.getroot()
    mm_per_uu = _mm_per_uu(root_a)
    centerlines: dict[str, list] = {}
    originals: dict[str, object] = {}
    for p in root_a.iter(f"{{{_SVG_NS}}}path"):
        pid = p.get("id") or ""
        if _is_centerline(p) and re.match(r"c\d+_\d+_", pid):
            centerlines.setdefault(pid.rsplit("_", 1)[0], []).append(p)
        elif re.fullmatch(r"c\d+_\d+", pid):
            originals[pid] = p


    # Decide an action PER REGION (block) *before* mutating, so a satin-overflow
    # fallback can demote satins to fills while keeping the (cheap) runs. Each block's
    # own width (outline area / centerline length, in mm) picks its tier — so one
    # colour can mix a thin keyline (run), a medium stroke (satin) and a solid blob
    # (fill), instead of the whole colour sharing one verdict:
    #   - width < the min-satin width (~1.6 mm) -> running / bean stitch along each
    #     substantial centerline (the "line < 1.6 mm -> run/triple-run" object); the
    #     original fill + tiny spurs are dropped.
    #   - width in the satin band AND a single clean column (one substantial centerline)
    #     -> a real satin. A branchy block (a letter like ر, a complex band) that would
    #     shatter into many pieces stays ONE continuous fill — murder on the machine.
    #   - anything broader than the ceiling, or branchy -> keep as one continuous fill.
    #   Lettering mode (--lettering): the production norm is the opposite — a block
    # capital is *meant* to be dissected into its stroke-columns, each satined at its own
    # width (letters knowledge §8a, calibrated against the 10000.VP3 ground truth), and
    # run is disabled. So we satin EVERY substantial centerline of the block.
    lettering = ctx.config.lettering
    # satin-lean (see _linework_indices): a satin-dominant category raises the ceiling AND
    # turns on branch dissection, so a bold/branchy stroke becomes per-branch satins rather
    # than one tatami fill — pushing the output toward the ground truth's ~100% satin.
    # A SATIN-ONLY pair prior (the arb trio: production digitizes zero fills) enables the
    # path automatically and lifts the overflow demotions below — the trio defines correct.
    satin_dominant = category_satin_dominant(ctx.config.category)
    satin_only = priors.satin_only(ctx.config.category)
    satin_lean = ((ctx.config.satin_lean and satin_dominant) or satin_only) and not lettering
    # satin-only: no run demotion — production sews sub-1.6mm linework as NARROW satin
    # (the arb video's 703 Column C pieces at 0.80mm), never as bean runs.
    run_enabled = ctx.config.thin_line_run and not lettering and not satin_only
    branch_satin = (ctx.config.branch_satin or satin_lean) and not lettering
    # Spine-guided fill: a region that stays a fill keeps its longest centerline as a
    # guided_fill guide (rows follow the medial axis) instead of dropping all centerlines.
    spine_fill = ctx.config.spine_fill
    spine_cands: list[tuple[str, object, int]] = []  # (orig id, guide centerline, colour idx)

    # Strip/ring width for broad-region satin cover under satin-only: calibrated from
    # the reference VP3s' own STITCH-LENGTH median (fingerprint profile satin_w_mm —
    # a strip's throw length IS its width, so this is the quantity the reference
    # defines; arabic profile med 2.4 vs the register-pass column-width med 1.75,
    # which under-shot: strips at 1.75 measured satin_w 1.73 vs the reference band
    # floor 1.94 AND cost 66k stitches vs the 41-51k band). Register med is the
    # fallback; other categories keep the historical 3mm band. Narrower than 3mm also
    # matters structurally: a 3mm ring folds its 1.5mm inner offset on tight
    # curvature into sunburst fans.
    strip_mm = _STRIP_MM
    if satin_only:
        med = ((load_profiles().get(ctx.config.category or "", {})
                .get("satin_w_mm") or {}).get("med")
               or priors.border_width_mm(ctx.config.category))
        if med:
            strip_mm = float(np.clip(med, 1.5, _STRIP_MM))

    def _keep_as_fill(orig, lines, idx):
        # Under --satin-lean (satin-dominant category), cover a broad region with satin
        # instead of one tatami fill ("sombras con satin"), closing the fill->satin gap.
        # CONTOUR-FOLLOWING "turning satin" rings first (rails follow the region boundary,
        # so edges stay clean on irregular/blobby shapes); straight parallel strips only as
        # fallback (stepped edges); one plain fill if both are degenerate.
        if satin_lean:
            poly = originals.get(orig)
            strips = _turning_satin_lines(poly, mm_per_uu, strip_mm)
            if not strips:
                straight = _satin_strip_lines(poly, mm_per_uu, strip_mm)
                # >=2 strips = a real tiling; under satin-ONLY even a single strip is
                # accepted (it only happens on a dot-sized region, where one 3mm column
                # IS the production cover — a fill is forbidden there)
                if len(straight) >= (1 if satin_only else 2):
                    strips = [np.asarray(seg, float) for seg in straight]
            if strips:
                strip_lines.extend((pts, idx) for pts in strips)
                drop_centerlines.extend(lines)
                drop_originals.add(orig)
                return
        if spine_fill and lines:
            guide = max(lines, key=lambda c: _polyline_len_uu(c.get("d") or ""))
            spine_cands.append((orig, guide, idx))
            drop_centerlines.extend(c for c in lines if c is not guide)
        else:
            drop_centerlines.extend(lines)

    # satin-only lowers the centerline floor to the vwidth minimum: production covers
    # even short spurs with tiny columns (the arb object list starts 17/6/19-stitch
    # pieces), and a 15-pt floor would drop them to the ring fallback.
    min_pts = (_LETTERING_MIN_SATIN_PTS if lettering
               else _VWIDTH_MIN_PTS if satin_only else _MIN_SATIN_PTS)
    width_ceiling = _satin_ceiling(lettering, satin_lean, satin_dominant,
                                   ctx.config.category)
    satin_max_mm = _LETTERING_SATIN_MAX_W_MM if (lettering or satin_lean) else _SATIN_MAX_W_MM
    satin_min_mm = _SATIN_MIN_W_MM
    band = priors.satin_width_band_mm(ctx.config.category)
    if band is not None and (satin_only or not (lettering or satin_lean)):
        # vwidth clamps from the category's MEASURED satin width band (pair prior).
        # A satin-only category applies them even on its automatic lean path:
        # production's own column widths (arb p10-p90 0.8-3.5mm) beat the lean
        # blanket's 6mm cap — a merged calligraphy band swept at 6mm reads blobby
        # and stacks thread where the fat column self-overlaps on tight curves.
        satin_min_mm = max(band[0], 0.5)
        satin_max_mm = min(max(band[1], satin_min_mm + 0.5), _SATIN_MAX_W_MM)
    run_strokes: list[tuple[object, int]] = []          # (centerline, colour idx)
    satin_cands: list[tuple[object, int, float]] = []   # (centerline, colour idx, width mm)
    strip_lines: list[tuple] = []                       # broad-region satin centerlines:
                                                        # ((N,2) root-frame points, colour idx)
    drop_centerlines: list[object] = []
    drop_originals: set[str] = set()
    for orig, lines in centerlines.items():
        idx = int(re.match(r"c(\d+)_", orig).group(1))
        longs = [c for c in lines if _npts(c) >= min_pts]
        if not longs:
            _keep_as_fill(orig, lines, idx)  # no real centerline (blob/scrap) -> fill or strip-tile
            continue
        # width = region area / FULL skeleton length (all centerlines, incl. spurs);
        # dividing by only the long ones over-estimates a branchy thin region's width.
        w_mm = _block_width_mm(originals.get(orig), lines, mm_per_uu)

        if lettering:
            satin_cands += [(c, idx, w_mm) for c in longs]
            drop_centerlines += [c for c in lines if c not in longs]
            drop_originals.add(orig)
        elif run_enabled and _run_demotion_ok(
                w_mm, _region_area_mm2(originals.get(orig), mm_per_uu), longs, lines):
            run_strokes += [(c, idx) for c in longs]
            drop_centerlines += [c for c in lines if c not in longs]
            drop_originals.add(orig)
        elif 0 < w_mm < width_ceiling:
            # Satin band. A single clean column always satins. A forked/branchy STROKE
            # region — a few long centerlines that are most of the skeleton (so satining
            # them leaves few gaps) — dissects into one satin per branch when --branch-satin
            # is on (generalising lettering's glyph dissection to organic strokes: a letter
            # ر, a forked ornament limb). Otherwise it stays ONE continuous fill.
            # SATIN-ONLY (the arb trio): production dissects EVERY region into per-stroke
            # columns — 1,618 of them, throws perpendicular to each pen stroke — so ALL
            # skeleton branches become columns, uncapped and ungated. (The turning-ring
            # cover this replaced sews boundary-parallel rings: satin_frac reads 100 but
            # the stitch DIRECTION is wrong everywhere — the huge visual drift vs the
            # reference in Wilcom.)
            if satin_only:
                keep = longs
            elif len(longs) == 1 and len(lines) <= _MAX_SPURS_FOR_SATIN:
                keep = longs[:1]
            elif (branch_satin and 2 <= len(longs) <= _MAX_BRANCH_SATINS
                  and _long_frac(longs, lines) >= _BRANCH_COVER_MIN):
                keep = longs
            else:
                keep = []
            if keep:
                if len(keep) > 1:
                    # branch dissection: mitre the junctions so per-branch columns
                    # overlap instead of gapping where they meet
                    try:
                        _mitre_branch_junctions(keep, originals.get(orig), mm_per_uu)
                    except Exception:
                        pass  # geometry hiccup -> unmitred branches (the old behaviour)
                satin_cands += [(c, idx, w_mm) for c in keep]
                drop_centerlines += [c for c in lines if c not in keep]
                drop_originals.add(orig)
            else:
                _keep_as_fill(orig, lines, idx)  # not stroke-like / too meshy -> one fill
        else:
            _keep_as_fill(orig, lines, idx)  # broad -> tatami fill, or satin strips under --satin-lean

    # Satin-lean sweep: an original that yielded NO centerline at all (a round dot, a
    # letter head — fill_to_stroke culls a skeleton shorter than its threshold) never
    # enters the loop above and would silently stay a plain fill. Under satin-lean every
    # region must satin, so route those through the same broad-region strip path
    # (turning rings; the single-strip fallback covers the smallest dots).
    if satin_lean:
        for orig in list(originals):
            if orig not in centerlines and orig not in drop_originals:
                _keep_as_fill(orig, [], int(re.match(r"c(\d+)_", orig).group(1)))

    # Junction-continuity chaining (satin-only): the skeleton cuts every pen stroke
    # wherever strokes cross, so a region's branch list is stroke FRAGMENTS. Merge the
    # fragments that continue smoothly through each junction back into single
    # pen-stroke polylines — what the calligrapher drew and the digitizer traces (one
    # column sewn THROUGH the crossing, the other layered over it). Chains only ever
    # form within one region's own branches, so nothing joins across background gaps.
    if satin_only and satin_cands:
        by_orig: dict[str, list] = {}
        for entry in satin_cands:
            by_orig.setdefault(
                (entry[0].get("id") or "").rsplit("_", 1)[0], []).append(entry)
        chained: list = []
        n_before = len(satin_cands)
        for _oid, group in by_orig.items():
            if len(group) < 2:
                chained.extend(group)
                continue
            try:
                chained.extend(_chain_branches_at_junctions(group, mm_per_uu))
            except Exception:
                chained.extend(group)          # geometry hiccup -> unchained branches
        satin_cands = chained
        if len(satin_cands) < n_before:
            print(f"      junction chaining -> {n_before} branch fragment(s) into "
                  f"{len(satin_cands)} stroke(s)", flush=True)

    # Satin-overflow guard (pathological stroke_to_satin slowness): demote the
    # satin candidates back to fills but keep the runs. LIFTED for a satin-only
    # category — production digitizes however many columns the design needs (the
    # arb trio: 1,618 objects), so no count may push regions back to tatami.
    max_columns = _LETTERING_MAX_SATIN_COLUMNS if lettering else _MAX_SATIN_COLUMNS
    if len(satin_cands) > max_columns and not satin_only:
        for c, _idx, _w in satin_cands:
            drop_centerlines.append(c)
            drop_originals.discard(c.get("id").rsplit("_", 1)[0])
        satin_cands = []
    if len(run_strokes) > _MAX_RUN_STROKES and not satin_only:
        _inject_params(ctx.svg_path, dst, ctx.config.fill_method, pc, ul, su, sp)
        return 0, 0

    # Apply the decisions to the tree — each satin at its own region width.
    for c, idx in run_strokes:
        _set_run_style(c, thread_hex.get(idx, "#000000"))
    # Satin columns: with --vwidth-satin, build each one directly from its centerline + region
    # boundary (rails offset by the LOCAL half-width) so it's a satin_column already; otherwise
    # set a uniform stroke width for the stroke_to_satin pass. Per-column fallback on failure.
    # satin-lean IMPLIES vwidth: leaning a satin-dominant category to satin with FIXED-width
    # columns under-covers modulated strokes (measured: over-inks ~1.43x, IoU 67%); building the
    # rails at the local half-width instead holds coverage AND matches the shape (1.22x, IoU 81%
    # on the Ramadan calligraphy) while reading satin_frac=100 like the ground truth. So whenever
    # we lean to satin we also build it variable-width — that's the fix the lean was blocked on.
    # Any column WIDER than the fixed-width-safe band (~3mm) is built variable-width even without
    # --vwidth-satin/--satin-lean: a uniform width under-covers a wide modulated stroke, so the
    # raised ~7mm ceiling only pays off with vwidth. Narrow columns (<=3mm) stay fixed-width.
    vwidth_all = ctx.config.vwidth_satin or satin_lean
    satin_ids: list[str] = []
    n_vwidth = 0
    footprints: dict[str, list] = {}       # orig region id -> built columns' swept polys
    for c, idx, w_mm in satin_cands:
        color = thread_hex.get(idx, "#000000")
        orig_id = (c.get("id") or "").rsplit("_", 1)[0]
        if vwidth_all or w_mm > _SATIN_FIXED_MAX_MM:
            poly = originals.get(orig_id)
            if poly is not None:
                # split snaking centerlines at hairpins first (see the splitter):
                # each short piece builds its own well-behaved column, like
                # production's one-column-per-stroke dissection
                try:
                    pieces = _split_centerline_at_hairpins(c, mm_per_uu)
                except Exception:
                    pieces = [c]
                for pc_el in pieces:
                    rails: list = []
                    try:
                        if _build_vwidth_satin(pc_el, poly, color, mm_per_uu,
                                               satin_max_mm, satin_min_mm,
                                               rails_out=rails):
                            n_vwidth += 1
                            left, right = rails[0]
                            footprints.setdefault(orig_id, []).append(
                                np.vstack([left, right[::-1]]))
                            continue
                    except Exception:
                        pass  # degenerate geometry -> fixed-width fallback below
                    w_uu = float(np.clip(w_mm, satin_min_mm, satin_max_mm)) / mm_per_uu
                    _set_stroke_style(pc_el, w_uu, color)
                    satin_ids.append(pc_el.get("id"))
                    try:
                        pts = _xf(np.asarray(
                            [(float(x), float(y)) for x, y in
                             _COORD_RE.findall(pc_el.get("d") or "")], float),
                            _ctm(pc_el))
                        footprints.setdefault(orig_id, []).append(
                            _stroke_footprint(pts, w_uu / 2))
                    except Exception:
                        pass
                continue
        w_uu = float(np.clip(w_mm, satin_min_mm, satin_max_mm)) / mm_per_uu
        _set_stroke_style(c, w_uu, color)
        satin_ids.append(c.get("id"))

    # SATIN-ONLY residual cover: per-branch columns don't TILE a region (junction
    # lobes and wide spots between branches stay bare — measured 62% source-ink
    # coverage vs 91%); production's per-stroke dissection covers everything. Tile
    # what the built columns didn't sweep with ring/strip patch columns.
    if satin_only and footprints:
        n_patch = 0
        for orig_id, fps in footprints.items():
            poly = originals.get(orig_id)
            if poly is None:
                continue
            try:
                lines = _residual_cover_lines(poly, fps, mm_per_uu, strip_mm)
            except Exception:
                lines = []
            if lines:
                p_idx = int(re.match(r"c(\d+)_", orig_id).group(1))
                strip_lines.extend((pts, p_idx) for pts in lines)
                n_patch += len(lines)
        if n_patch:
            print(f"      satin-only residual cover -> {n_patch} patch column(s)",
                  flush=True)
    # Broad-region satin centerlines (turning rings or straight strips) -> fixed-width
    # satin columns (root frame, no transform).
    # Every strip centerline (staggered turning ring or straight strip) goes through
    # stroke_to_satin PER RING — per-ring columns keep Ink-Stitch's rail pairing local
    # and close ring seams cleanly. (Two single-column alternatives were DISPROVEN by
    # measurement: one spiral column skews the fraction-based rail pairing into
    # multi-turn throws — median stitch 13.7mm vs the 3.3mm width — and a direct
    # rails+rungs build leaves pinholes where tight inner curvature folds the inner
    # rail between 4mm rungs.)
    strip_w_uu = strip_mm / mm_per_uu
    n_strip_el = 0
    for pts, idx in strip_lines:
        # Split each strip/ring arc at hairpins BEFORE stroke_to_satin: on a folded
        # arc its rail-split heuristic pairs a tiny rail with the whole outline and
        # the column sews a sunburst fan across the shape (measured: single-subpath
        # satin columns spanning ~20mm at the arb stacking hotspots).
        arr = np.asarray(pts, float)
        pieces = _hairpin_bounds(arr, mm_per_uu)
        # A CLOSED ring that survived whole still fans: the two offset rails of a
        # closed loop have no free ends, so Ink-Stitch's fractional pairing skews on
        # tight curvature (the residual arb sunbursts). Cut it into two open
        # half-arcs — open columns pair rails end-to-end cleanly. Closedness is
        # detected by NET TURNING (~360deg for a loop): an endpoint-distance test
        # misses rings because _ring_polyline overshoots the seam by ~one strip.
        if len(pieces) == 1 and len(arr) >= 6 and abs(_net_turning_deg(arr)) > 300.0:
            mid = len(arr) // 2
            pieces = [(0, mid), (mid, len(arr) - 1)]
        for a, b in pieces:
            if b - a < 1:
                continue
            el = etree.SubElement(root_a, f"{{{_SVG_NS}}}path")
            el.set("id", f"strip{n_strip_el}")
            el.set("d", "M " + " ".join(f"{x:.3f},{y:.3f}" for x, y in arr[a:b + 1]))
            _set_stroke_style(el, strip_w_uu, thread_hex.get(idx, "#000000"))
            satin_ids.append(f"strip{n_strip_el}")
            n_strip_el += 1
    for c in drop_centerlines:
        if c.getparent() is not None:
            c.getparent().remove(c)
    for orig in drop_originals:
        if orig in originals and originals[orig].getparent() is not None:
            originals[orig].getparent().remove(originals[orig])

    # Spine-guided fills: wire each kept-as-fill region's guide centerline into a guided_fill.
    # Applied to root_a, so it flows through both the runs-only and the stroke_to_satin paths.
    if spine_cands:
        n_spine = _apply_spine_fills(root_a, spine_cands, originals, thread_hex)
        if n_spine:
            print(f"      spine-fill -> {n_spine} region(s) guided by medial axis")

    n_run = len(run_strokes)

    if not satin_ids:
        # no stroke_to_satin needed (runs only, or every satin was built variable-width) ->
        # finalize directly; regroup still picks up any vwidth satin_column paths.
        _regroup_linework_by_colour(root_a, thread_hex)
        _apply_fill_params(root_a, ctx.config.fill_method, pc, ul, su, sp)
        tree_a.write(str(dst), xml_declaration=True, encoding="UTF-8")
        return n_vwidth, n_run

    tree_a.write(str(tmp_a), xml_declaration=True, encoding="UTF-8")

    # Pass B: centerline strokes -> satin columns (runs pass through untouched).
    tmp_b = dst.with_name(dst.stem + "_B.svg")
    _run_extension(binary, "stroke_to_satin", satin_ids, [], tmp_a, tmp_b,
                   timeout=_SATIN_TIMEOUT_S)

    tree_b = etree.parse(str(tmp_b))
    _regroup_linework_by_colour(tree_b.getroot(), thread_hex)
    _apply_fill_params(tree_b.getroot(), ctx.config.fill_method, pc, ul, su, sp)
    tree_b.write(str(dst), xml_declaration=True, encoding="UTF-8")
    return len(satin_ids) + n_vwidth, n_run


def _regroup_linework_by_colour(root, thread_hex: dict[int, str]) -> None:
    """Move every satin column and running-stitch stroke into its colour's <g>
    (by stroke colour) so each colour stays one contiguous block, then drop the
    empty wrapper groups stroke_to_satin created."""
    groups = {}
    for g in root.iter(f"{{{_SVG_NS}}}g"):
        m = re.match(r"color(\d+)_", g.get("id") or "")
        if m:
            groups[int(m.group(1))] = g
    hex_to_idx = {v.lower(): k for k, v in thread_hex.items()}

    for p in list(root.iter(f"{{{_SVG_NS}}}path")):
        if not (p.get(f"{{{_INKSTITCH_NS}}}satin_column")
                or p.get(f"{{{_INKSTITCH_NS}}}stroke_method")):
            continue
        m = re.search(r"stroke:(#[0-9a-fA-F]{6})", p.get("style") or "")
        idx = hex_to_idx.get(m.group(1).lower()) if m else None
        if idx is not None and idx in groups and p.getparent() is not groups[idx]:
            p.getparent().remove(p)
            groups[idx].append(p)

    for g in list(root.iter(f"{{{_SVG_NS}}}g")):
        if (g.get("id") or "").startswith("centerline_group") and len(g) == 0:
            g.getparent().remove(g)


# --------------------------------------------------------------------------- #
# auto-route post-pass (auto_satin / auto_run)
# --------------------------------------------------------------------------- #
def _auto_route(ctx: PipelineContext, binary: Path, svg: Path) -> None:
    """Thread each colour's satins / runs into one connected, optimally-ordered path.

    Runs Ink-Stitch `auto_satin` / `auto_run` PER COLOUR (each extension makes a single
    path through its whole selection, so mixing colours would splice threads together).
    Underpaths between adjacent pieces instead of trimming and picks entry/exit — cutting
    travel + trims. Best-effort: any failure leaves the pre-routed SVG as-is.

    Crucially the routed pieces have their per-piece `trim_after` **removed first** so the
    extension owns trimming: leaving trim_after on (the prepass sets it on every satin/run)
    forces a trim after each piece and cancels the whole point of auto-routing. Underlay /
    fill params are *not* re-stamped afterwards (auto_* preserves the element attributes),
    which is what previously re-introduced the trims.
    """
    trim_attr = f"{{{_INKSTITCH_NS}}}trim_after"
    try:
        tree = etree.parse(str(svg))
        root = tree.getroot()
    except Exception:
        return

    # auto_satin / auto_run select by id; make sure every satin/run has one.
    for i, p in enumerate(root.iter(f"{{{_SVG_NS}}}path")):
        if (p.get(f"{{{_INKSTITCH_NS}}}satin_column")
                or p.get(f"{{{_INKSTITCH_NS}}}stroke_method")) and not p.get("id"):
            p.set("id", f"ar_{i}")

    satins_by_colour: dict[int, list[str]] = {}
    runs_by_colour: dict[int, list[str]] = {}
    for g in root.iter(f"{{{_SVG_NS}}}g"):
        m = re.match(r"color(\d+)_", g.get("id") or "")
        if not m:
            continue
        idx = int(m.group(1))
        for p in g.iter(f"{{{_SVG_NS}}}path"):
            if p.get(f"{{{_INKSTITCH_NS}}}satin_column"):
                satins_by_colour.setdefault(idx, []).append(p.get("id"))
            elif p.get(f"{{{_INKSTITCH_NS}}}stroke_method"):
                runs_by_colour.setdefault(idx, []).append(p.get("id"))

    # Only colours with >= 2 pieces are worth routing. Strip trim_after from exactly
    # those pieces so auto_* controls the trims, then write the SVG the extensions read.
    route_ids = {pid for ids in satins_by_colour.values() if len(ids) >= 2 for pid in ids}
    route_ids |= {pid for ids in runs_by_colour.values() if len(ids) >= 2 for pid in ids}
    if not route_ids:
        return
    for p in root.iter(f"{{{_SVG_NS}}}path"):
        if p.get("id") in route_ids and p.get(trim_attr) is not None:
            del p.attrib[trim_attr]
    tree.write(str(svg), xml_declaration=True, encoding="UTF-8")

    n_sat = n_run = 0
    for idx, ids in satins_by_colour.items():
        if len(ids) < 2:
            continue  # nothing to connect
        try:
            _run_extension(binary, "auto_satin", ids,
                           ["--trim=true", "--preserve_order=false"],
                           svg, svg, timeout=_SATIN_TIMEOUT_S)
            n_sat += 1
        except Exception as exc:
            print(f"      auto_satin (colour {idx}) skipped: {type(exc).__name__}")
    for idx, ids in runs_by_colour.items():
        if len(ids) < 2:
            continue
        try:
            _run_extension(binary, "auto_run", ids, ["--preserve_order=false"], svg, svg)
            n_run += 1
        except Exception as exc:
            print(f"      auto_run (colour {idx}) skipped: {type(exc).__name__}")

    if not (n_sat or n_run):
        return

    # auto_* keeps element attributes (underlay etc.) but can lift routed paths out of
    # their colour <g>; regroup by stroke colour to restore the background->foreground
    # order. Do NOT re-stamp params here — that would put trim_after back on every piece.
    try:
        thread_hex = {i: "#{:02X}{:02X}{:02X}".format(*m["thread_rgb"])
                      for i, m in enumerate(ctx.thread_map)}
        tree = etree.parse(str(svg))
        _regroup_linework_by_colour(tree.getroot(), thread_hex)
        tree.write(str(svg), xml_declaration=True, encoding="UTF-8")
    except Exception as exc:
        print(f"      auto-route regroup skipped: {type(exc).__name__}")
    print(f"      auto-route -> {n_sat} colour(s) satins, {n_run} colour(s) runs re-routed")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _is_centerline(p) -> bool:
    return "fill:none" in (p.get("style") or "") or p.get("fill") == "none"


def _npts(p) -> int:
    return len(re.findall(r"-?\d+\.?\d*[, ]-?\d+\.?\d*", p.get("d") or ""))


_COORD_RE = re.compile(r"(-?\d+\.?\d*)[, ](-?\d+\.?\d*)")


def _mm_per_uu(root) -> float:
    """mm per SVG user-unit, from the root width (in mm) and viewBox. The trace SVG is
    authored as width='<Wmm>mm' viewBox='0 0 <Wuu> <Huu>', so a length in user-units
    times this is a real millimetre length. Falls back to 1.0 (assume uu == mm)."""
    vb = (root.get("viewBox") or "").split()
    m = re.match(r"([0-9.]+)", root.get("width") or "")
    if len(vb) == 4 and m:
        try:
            w_uu = float(vb[2])
            if w_uu > 0:
                return float(m.group(1)) / w_uu
        except ValueError:
            pass
    return 1.0


def _poly_area_uu2(d: str) -> float:
    """Shoelace area (user-units²) of a polygon path. Reverse-wound holes/counters
    subtract (net = ring area); the tiny sliver from wrapping across subpath breaks is
    negligible at the scale we tier on. vtracer emits polygons, so no curve flattening."""
    pts = [(float(x), float(y)) for x, y in _COORD_RE.findall(d)]
    if len(pts) < 3:
        return 0.0
    a = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def _region_area_mm2(original, mm_per_uu: float) -> float:
    """A tiered region's ink area in mm² (0 when its original path is unavailable —
    the run tier then stays permissive, matching the pre-guard behaviour)."""
    if original is None:
        return 0.0
    return _poly_area_uu2(original.get("d") or "") * mm_per_uu * mm_per_uu


def _run_demotion_ok(w_mm: float, area_mm2: float, longs, lines) -> bool:
    """May a sub-1.6mm-average region be demoted from fill to bean runs? Yes for a
    genuine hairline (small, or its long centerlines carry the skeleton); NO for a
    large spur-dominated region — that is a merged band/mesh whose thin connectors
    drag broad strokes under the width threshold (arb middle arc: 1,090mm² at
    "1.36mm" avg, long_frac 0.16), where runs would cover ~15% and the dropped fill
    never sews (the missing-middle-arc incident). Large regions stay fills (the
    "large regions = tatami" hard rule)."""
    if not (0 < w_mm < _RUN_MAX_WIDTH_MM):
        return False
    return (area_mm2 <= _RUN_MAX_REGION_AREA_MM2
            or _long_frac(longs, lines) >= _BRANCH_COVER_MIN)


def _polyline_len_uu(d: str) -> float:
    """Summed segment length (user-units) of a polyline path."""
    pts = [(float(x), float(y)) for x, y in _COORD_RE.findall(d)]
    return sum(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
               for (x0, y0), (x1, y1) in zip(pts, pts[1:]))


def _long_frac(longs, lines) -> float:
    """Fraction of a block's total centerline length carried by its substantial (long)
    centerlines — i.e. how much of the region dissecting into per-branch satins would
    cover. Low fraction = a fragmented mesh where satins would leave big gaps (keep a fill)."""
    total = sum(_polyline_len_uu(c.get("d") or "") for c in lines)
    if total <= 0:
        return 0.0
    return sum(_polyline_len_uu(c.get("d") or "") for c in longs) / total


def _block_width_mm(original, centerlines, mm_per_uu: float) -> float:
    """A region's typical stroke width in mm: outline area / centerline length. Both
    quantities are translation-invariant, so per-path vtracer translates need no
    bookkeeping. 0.0 if it can't be measured (degenerate) -> caller keeps it a fill."""
    if original is None:
        return 0.0
    area = _poly_area_uu2(original.get("d") or "")
    length = sum(_polyline_len_uu(c.get("d") or "") for c in centerlines)
    if area <= 0 or length <= 0:
        return 0.0
    return (area / length) * mm_per_uu


def _set_stroke_style(p, w: float, color: str) -> None:
    """Set stroke width + colour so the resulting satin keeps the thread colour
    (fill_to_stroke emits black centerlines; stroke_to_satin preserves stroke)."""
    style = p.get("style") or ""
    if "stroke-width" in style:
        style = re.sub(r"stroke-width:[0-9.]+", f"stroke-width:{w:.3f}", style)
    else:
        style = (style + f";stroke-width:{w:.3f}").lstrip(";")
    if re.search(r"stroke:#?[0-9a-zA-Z]+", style):
        style = re.sub(r"stroke:#?[0-9a-zA-Z]+", f"stroke:{color}", style)
    else:
        style = style + f";stroke:{color}"
    p.set("style", style)


def _set_run_style(p, color: str) -> None:
    """Turn a centerline into a running/bean stitch of the thread colour: a thin
    cosmetic stroke width + the colour, plus the Ink-Stitch running-stitch params
    (stroke_to_satin is never run on these, so they stay running stitches)."""
    _set_stroke_style(p, 1.0, color)
    for key, value in _run_params().items():
        p.set(f"{{{_INKSTITCH_NS}}}{key}", value)


# Spine-guided fill (--spine-fill). A region kept as a FILL reuses its longest extracted
# centerline as an Ink-Stitch guided_fill GUIDE, so the fill rows follow the shape's medial
# axis (the PEmbroider hatchSpine idea) instead of a fixed angle. A guide line is a fill:none
# stroke carrying the guide-line marker (which tells Ink-Stitch not to stitch it, only steer
# the fill); it must live in the same <g> as the fill it steers. The marker def below is the
# one Ink-Stitch's `selection_to_guide_line` emits (only its id has to match the style url).
_GUIDE_MARKER_ID = "inkstitch-guide-line-marker"
_GUIDE_MARKER_XML = (
    '<marker xmlns="http://www.w3.org/2000/svg" refX="10" refY="5" orient="auto"'
    f' id="{_GUIDE_MARKER_ID}" markerUnits="userSpaceOnUse" markerWidth="0.1"'
    ' viewBox="0 0 1 1"><path style="fill:#fafafa;stroke:#ff5500;stroke-width:0.5"'
    ' d="M 10.13,5.29 A 4.84,4.84 0 0 1 5.29,10.13 4.84,4.84 0 0 1 0.45,5.29'
    ' 4.84,4.84 0 0 1 5.29,0.45 4.84,4.84 0 0 1 10.13,5.29 Z"'
    ' id="inkstitch-guide-line-marker-circle"/></marker>'
)


# Variable-width satin (--vwidth-satin). A satin column is one <path inkstitch:satin_column>
# whose `d` holds two long "rail" subpaths + short "rung" subpaths (Ink-Stitch treats the two
# longest subpaths as rails, the rest as rungs pairing them). stroke_to_satin builds rails at a
# CONSTANT offset from the centerline (one width) — under-covering a modulated stroke. Here we
# offset each rail by the LOCAL half-width instead: the distance from that centerline point to
# the region boundary (the medial-axis inscribed radius — PEmbroider hatchSpineVF's distance
# field), so the satin fattens over the belly and tapers at the ends like a hand digitize.
_VWIDTH_MIN_PTS = 6
_VWIDTH_N_RUNGS = 14    # floor for short columns; long ones get one rung per _VWIDTH_RUNG_MM
_VWIDTH_RUNG_MM = 4.0   # arc-length between rungs — keeps Ink-Stitch's fractional rail
                        # pairing LOCAL on long snaking centerlines (sparse rungs fan)


def _parse_transform(s: str) -> np.ndarray:
    """SVG transform string -> 3x3 affine. Handles the ops vtracer/Ink-Stitch emit here
    (translate/scale/matrix); unknown ops are skipped (treated as identity)."""
    M = np.eye(3)
    for op, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        v = [float(x) for x in re.split(r"[,\s]+", args.strip()) if x]
        t = np.eye(3)
        if op == "translate" and v:
            t[0, 2], t[1, 2] = v[0], (v[1] if len(v) > 1 else 0.0)
        elif op == "scale" and v:
            t[0, 0], t[1, 1] = v[0], (v[1] if len(v) > 1 else v[0])
        elif op == "matrix" and len(v) == 6:
            t = np.array([[v[0], v[2], v[4]], [v[1], v[3], v[5]], [0, 0, 1]], float)
        else:
            continue
        M = M @ t
    return M


def _ctm(el) -> np.ndarray:
    """Cumulative transform (element + ancestors) mapping the element's local coords to the
    root user-unit frame, so a centerline and its region boundary are comparable."""
    mats = []
    cur = el
    while cur is not None and hasattr(cur, "get"):
        t = cur.get("transform")
        if t:
            mats.append(_parse_transform(t))
        cur = cur.getparent()
    M = np.eye(3)
    for m in reversed(mats):  # outermost (root) first
        M = M @ m
    return M


def _xf(pts: np.ndarray, M: np.ndarray) -> np.ndarray:
    """Apply a 3x3 affine to (N,2) points."""
    if pts.size == 0:
        return pts
    h = np.column_stack([pts, np.ones(len(pts))])
    return (h @ M.T)[:, :2]


def _path_segments(d: str) -> tuple[np.ndarray, np.ndarray]:
    """Boundary segments (A[i]->B[i]) of a polygon path, per subpath and closed. vtracer emits
    polygons, so no curve flattening. Returns two (M,2) arrays of segment endpoints."""
    A: list = []
    B: list = []
    for sub in re.split(r"[Mm]", d):
        pts = [(float(x), float(y)) for x, y in _COORD_RE.findall(sub)]
        if len(pts) < 2:
            continue
        arr = np.asarray(pts, float)
        A.append(arr)
        B.append(np.roll(arr, -1, axis=0))  # close the ring (last -> first)
    if not A:
        return np.empty((0, 2)), np.empty((0, 2))
    return np.concatenate(A), np.concatenate(B)


def _min_dist_to_segments(P: np.ndarray, A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Min distance from each point in P (N,2) to any segment A[i]-B[i]. Local half-width."""
    AB = B - A
    AB2 = (AB * AB).sum(1)
    AB2 = np.where(AB2 == 0, 1e-9, AB2)
    out = np.empty(len(P))
    for i, p in enumerate(P):
        t = np.clip(((p - A) * AB).sum(1) / AB2, 0.0, 1.0)
        proj = A + t[:, None] * AB
        out[i] = np.hypot(*(p - proj).T).min()
    return out


_HAIRPIN_TURN_DEG = 75.0      # chord-direction change (over ~0.75mm steps) that marks a hairpin
_HAIRPIN_MIN_PIECE_MM = 3.0   # don't cut pieces shorter than this
_HAIRPIN_STEP_MM = 0.75       # chord sampling step for the turn measurement


_CHAIN_JOIN_MM = 2.0        # branch ends within this of each other share a junction
                            # (fill_to_stroke trims branch tips short of the true
                            # junction centre, so ends don't exactly coincide; safe
                            # because chains only form INSIDE one region's branches)
_CHAIN_MAX_TURN_DEG = 45.0  # max direction change for a stroke to continue through
_CHAIN_TANGENT_MM = 1.5     # chord length used to measure an end's direction


def _chain_branches_at_junctions(cands: list, mm_per_uu: float) -> list:
    """Merge one region's branch-fragment centerlines into pen-stroke polylines.

    `cands` is [(element, colour idx, w_mm), ...] — ALL of one region. Branch ends
    that meet at a junction are paired by DIRECTION CONTINUITY (incoming vs outgoing
    chord within _CHAIN_MAX_TURN_DEG), then the paired fragments concatenate into one
    root-frame polyline per pen stroke (the first fragment's element carries it; the
    merged elements are removed from the tree). Cycles (a chained loop) are walked
    from an arbitrary link — the downstream net-turning cut halves them. Returns the
    new cands list; on any degenerate geometry the input is returned unchanged."""
    P: list[np.ndarray] = []
    keep_entries: list = []
    passthrough: list = []
    for el, idx, w_mm in cands:
        pts = np.asarray([(float(x), float(y)) for x, y in
                          _COORD_RE.findall(el.get("d") or "")], float)
        if len(pts) < 2:
            passthrough.append((el, idx, w_mm))
            continue
        P.append(_xf(pts, _ctm(el)))
        keep_entries.append((el, idx, w_mm))
    n = len(P)
    if n < 2:
        return cands

    join_uu = _CHAIN_JOIN_MM / mm_per_uu
    tang_uu = _CHAIN_TANGENT_MM / mm_per_uu

    def _end_pt(bi: int, e: int) -> np.ndarray:
        return P[bi][0] if e == 0 else P[bi][-1]

    def _end_dir(bi: int, e: int) -> np.ndarray:
        """Unit travel direction INTO the junction at end e of branch bi, measured
        over the last ~_CHAIN_TANGENT_MM of arc before the end."""
        pts = P[bi] if e == 1 else P[bi][::-1]          # end at pts[-1]
        seg = np.hypot(*np.diff(pts, axis=0).T)
        back = np.cumsum(seg[::-1])                     # arc distance walking back
        k = min(int(np.searchsorted(back, tang_uu)) + 1, len(pts) - 1)
        v = pts[-1] - pts[-1 - k]
        L = float(np.hypot(*v))
        return v / L if L > 1e-9 else np.array([1.0, 0.0])

    ends = [(bi, e) for bi in range(n) for e in (0, 1)]
    # candidate pairs: nearby ends of different branches, scored by continuation turn
    scored = []
    for i in range(len(ends)):
        bi, ei = ends[i]
        for j in range(i + 1, len(ends)):
            bj, ej = ends[j]
            if bi == bj:
                continue
            if float(np.hypot(*(_end_pt(bi, ei) - _end_pt(bj, ej)))) > join_uu:
                continue
            # travel continues: incoming direction at end i vs outgoing at end j
            turn = float(np.degrees(np.arccos(np.clip(
                np.dot(_end_dir(bi, ei), -_end_dir(bj, ej)), -1.0, 1.0))))
            if turn <= _CHAIN_MAX_TURN_DEG:
                scored.append((turn, (bi, ei), (bj, ej)))
    if not scored:
        return cands
    scored.sort(key=lambda t: t[0])
    pair: dict = {}
    for _turn, a, b in scored:
        if a in pair or b in pair:
            continue
        pair[a] = b
        pair[b] = a

    # walk chains (open chains from free ends first, then break any cycles)
    visited: set[int] = set()
    chains: list[list[tuple[int, int]]] = []

    def _walk(start_b: int, enter_e: int) -> list[tuple[int, int]]:
        chain = []
        cur, ent = start_b, enter_e
        while cur not in visited:
            visited.add(cur)
            chain.append((cur, ent))
            nxt = pair.get((cur, 1 - ent))
            if nxt is None:
                break
            cur, ent = nxt
        return chain

    for bi in range(n):
        if bi in visited:
            continue
        free = next((e for e in (0, 1) if (bi, e) not in pair), None)
        if free is not None:
            chains.append(_walk(bi, free))
    for bi in range(n):
        if bi not in visited:
            chains.append(_walk(bi, 0))       # cycle: break at an arbitrary link

    out = list(passthrough)
    for chain in chains:
        parts = []
        for k, (bi, ent) in enumerate(chain):
            pts = P[bi] if ent == 0 else P[bi][::-1]
            parts.append(pts[1:] if k else pts)
        merged = np.vstack(parts)
        el, idx, w_mm = keep_entries[chain[0][0]]
        el.set("d", "M " + " ".join(f"{x:.3f},{y:.3f}" for x, y in merged))
        el.attrib.pop("transform", None)      # merged points are root-frame
        for bi, _ent in chain[1:]:
            other = keep_entries[bi][0]
            if other.getparent() is not None:
                other.getparent().remove(other)
        out.append((el, idx, w_mm))
    return out


def _net_turning_deg(R: np.ndarray) -> float:
    """Net signed turning of a polyline in degrees (~+-360 for a closed loop)."""
    D = np.diff(R, axis=0)
    L = np.hypot(*D.T)
    D = D[L > 1e-9]
    if len(D) < 3:
        return 0.0
    ang = np.arctan2(D[:, 1], D[:, 0])
    turn = (np.diff(ang) + np.pi) % (2 * np.pi) - np.pi
    return float(np.degrees(turn.sum()))


def _hairpin_bounds(R: np.ndarray, mm_per_unit: float) -> list[tuple[int, int]]:
    """Index bounds [(a,b), ...] splitting the polyline R (N,2; units where
    mm = units * mm_per_unit) at hairpin turns. [(0, N-1)] when there is none."""
    n = len(R)
    if n < 8:
        return [(0, n - 1)]
    seg = np.hypot(*np.diff(R, axis=0).T)
    pos_mm = np.concatenate(([0.0], np.cumsum(seg))) * mm_per_unit
    total = float(pos_mm[-1])
    if total < 2 * _HAIRPIN_MIN_PIECE_MM:
        return [(0, n - 1)]
    samples = [0]
    for i in range(1, n):
        if pos_mm[i] - pos_mm[samples[-1]] >= _HAIRPIN_STEP_MM:
            samples.append(i)
    if len(samples) < 4:
        return [(0, n - 1)]
    S = np.asarray(samples)
    D = R[S[1:]] - R[S[:-1]]
    ang = np.arctan2(D[:, 1], D[:, 0])
    turn = np.abs(np.degrees((np.diff(ang) + np.pi) % (2 * np.pi) - np.pi))
    cuts = []
    last_mm = 0.0
    for j in np.nonzero(turn > _HAIRPIN_TURN_DEG)[0]:
        k = int(S[j + 1])
        if (pos_mm[k] - last_mm >= _HAIRPIN_MIN_PIECE_MM
                and total - pos_mm[k] >= _HAIRPIN_MIN_PIECE_MM):
            cuts.append(k)
            last_mm = float(pos_mm[k])
    bounds = [0] + cuts + [n - 1]
    return [(bounds[j], bounds[j + 1]) for j in range(len(bounds) - 1)]


def _split_centerline_at_hairpins(c, mm_per_uu: float) -> list:
    """Split a snaking centerline element at hairpin turns into several short elements
    (clones inserted after it, same transform/style). A satin column built along a
    centerline whose local curvature radius is under the rail offset gets a FOLDED inner
    rail, and Ink-Stitch's fractional rail pairing then throws sunburst fans across the
    shape (measured on the arb merged-calligraphy clusters: 16-29 thread layers on one
    spot). Production digitizes one short column per pen stroke — splitting at hairpins
    is the tracer's approximation of that. Returns [c] when there is no hairpin."""
    verts = [(float(x), float(y)) for x, y in _COORD_RE.findall(c.get("d") or "")]
    if len(verts) < 8:
        return [c]
    P = np.asarray(verts, float)
    # chord directions measured in the ROOT frame (~0.75mm spacing — per-vertex angles
    # on a dense polyline are noise); the d is split on the LOCAL points at the same
    # indices, keeping the element's transform.
    R = _xf(P, _ctm(c))
    pieces = _hairpin_bounds(R, mm_per_uu)
    if len(pieces) == 1:
        # A CLOSED-LOOP centerline (a letter counter, an annular stroke — net turning
        # ~360deg) has no hairpin but still mis-pairs: rails offset around a loop have
        # no free ends, and the fractional pairing skews into sunburst fans on tight
        # curvature (the residual arb fans were exactly these). Cut it into two open
        # half-arcs, like production's per-stroke Column A/C dissection.
        if abs(_net_turning_deg(R)) > 300.0:
            mid = len(P) // 2
            pieces = [(0, mid), (mid, len(P) - 1)]
        else:
            return [c]
    parent = c.getparent()
    base_id = c.get("id") or "hp"
    out = []
    for j, (a, b) in enumerate(pieces):
        dd = "M " + " ".join(f"{x:.3f},{y:.3f}" for x, y in P[a:b + 1])
        if j == 0:
            c.set("d", dd)
            out.append(c)
        else:
            el = etree.fromstring(etree.tostring(c))
            el.set("d", dd)
            el.set("id", f"{base_id}_hp{j}")
            parent.insert(parent.index(c) + j, el)
            out.append(el)
    return out


def _build_vwidth_satin(center_el, poly_el, color: str, mm_per_uu: float,
                        satin_max_mm: float,
                        satin_min_mm: float = _SATIN_MIN_W_MM,
                        rails_out: list | None = None) -> bool:
    """Rewrite `center_el` in place from a centerline stroke into a variable-width satin column
    (two rails offset by the local half-width + rungs). Returns False (leaving it untouched) if
    the geometry is degenerate, so the caller can fall back to fixed-width stroke_to_satin.
    When `rails_out` is given, the (left, right) root-frame rail arrays are appended to it —
    the column's sewn FOOTPRINT, used by the satin-only residual-cover pass."""
    center = np.asarray(
        [(float(x), float(y)) for x, y in _COORD_RE.findall(center_el.get("d") or "")], float)
    if len(center) < _VWIDTH_MIN_PTS:
        return False
    A, B = _path_segments(poly_el.get("d") or "")
    if len(A) == 0:
        return False

    # Resolve both to the root frame — the centerline and its boundary carry DIFFERENT per-path
    # transforms (vtracer translate vs a fill_to_stroke scale), so raw coords aren't comparable.
    center = _xf(center, _ctm(center_el))
    Mp = _ctm(poly_el)
    A, B = _xf(A, Mp), _xf(B, Mp)

    hw = _min_dist_to_segments(center, A, B)                      # local half-width (root uu)
    hw = np.convolve(hw, np.ones(5) / 5, mode="same")            # de-jitter
    lo = (satin_min_mm / 2) / mm_per_uu
    hi = (satin_max_mm / 2) / mm_per_uu
    hw = np.clip(hw, lo, hi)

    tan = np.gradient(center, axis=0)
    tan /= np.hypot(tan[:, 0], tan[:, 1])[:, None] + 1e-9
    nrm = np.stack([-tan[:, 1], tan[:, 0]], axis=1)              # unit normal
    left = center + nrm * hw[:, None]
    right = center - nrm * hw[:, None]
    if rails_out is not None:
        rails_out.append((left, right))

    def _sub(pts):
        return "M " + " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)

    # rails first (longest subpaths), then interior rungs pairing them left<->right.
    # Rungs are placed by ARC LENGTH (~every _VWIDTH_RUNG_MM), with _VWIDTH_N_RUNGS as
    # the floor for short columns: Ink-Stitch pairs the rails FRACTIONALLY between
    # rungs, so sparse rungs on a long snaking centerline let the pairing skew at
    # hairpins and throw giant fan stitches across the shape (measured on the arb
    # top arc: a 297mm-vs-200mm rail pair with 14 rungs fanned 15mm sunbursts).
    parts = [_sub(left), _sub(right)]
    n = len(center)
    seg = np.hypot(*np.diff(center, axis=0).T)
    pos = np.concatenate(([0.0], np.cumsum(seg)))
    total_mm = float(pos[-1]) * mm_per_uu
    n_rungs = max(_VWIDTH_N_RUNGS, int(total_mm / _VWIDTH_RUNG_MM))
    seen: set[int] = set()
    for t in np.linspace(0.0, pos[-1], n_rungs + 2)[1:-1]:
        k = min(max(int(np.searchsorted(pos, t)), 1), n - 2)
        if k in seen:
            continue
        seen.add(k)
        parts.append(f"M {left[k,0]:.3f},{left[k,1]:.3f} {right[k,0]:.3f},{right[k,1]:.3f}")

    center_el.set("d", " ".join(parts))
    center_el.attrib.pop("transform", None)  # rails are already baked into the root frame
    center_el.set(f"{{{_INKSTITCH_NS}}}satin_column", "true")
    # Underlay by width (manual p412; arb video: Double-Tatami underlay ONLY on wide
    # Column-A pieces, narrow Column-C bare): a WIDE column gets zigzag + center-walk —
    # the closest Ink-Stitch analogue of the authored Double Tatami support — set on the
    # ELEMENT so it survives even when the category-level satin underlay is authored off.
    # A narrow column carries nothing extra.
    median_w_mm = float(np.median(hw)) * 2 * mm_per_uu
    if median_w_mm > _SATIN_FIXED_MAX_MM:
        center_el.set(f"{{{_INKSTITCH_NS}}}zigzag_underlay", "true")
        center_el.set(f"{{{_INKSTITCH_NS}}}center_walk_underlay", "true")
    center_el.set("style", f"fill:none;stroke:{color};stroke-width:1")
    return True


_STRIP_MM = 3.0             # width of each satin strip when tiling a broad region (fixed-width band)
_STRIP_MIN_RUN_MM = 2.0     # skip strip runs shorter than this (slivers)
_MAX_STRIPS_PER_REGION = 80
_RESIDUAL_MIN_MM2 = 2.5     # a residual (branch-uncovered) patch smaller than this is left
                            # to the neighbouring columns' pull-comp/overlap


def _stroke_footprint(pts: np.ndarray, half_uu: float) -> np.ndarray | None:
    """Closed polygon swept by a fixed-width column along `pts` (root frame)."""
    if len(pts) < 2:
        return None
    tan = np.gradient(pts, axis=0)
    tan /= np.hypot(tan[:, 0], tan[:, 1])[:, None] + 1e-9
    nrm = np.stack([-tan[:, 1], tan[:, 0]], axis=1)
    return np.vstack([pts + nrm * half_uu, (pts - nrm * half_uu)[::-1]])


def _residual_cover_lines(poly_el, footprints: list, mm_per_uu: float,
                          strip_mm: float) -> list:
    """Cover the part of a region the per-branch columns did NOT sweep: rasterize the
    region, subtract the built columns' footprints, and tile each substantial residual
    component with turning rings (straight strips as fallback). This is what makes the
    satin-only per-stroke dissection COMPLETE — skeleton branches alone leave junction
    lobes and wide spots bare (measured: source-ink coverage 62% vs 91% with full-region
    rings; production tiles everything with columns). Returns root-frame centerlines."""
    from PIL import Image, ImageDraw
    # evenodd: letter counters/holes must stay holes — a union fill would make the
    # residual pass lay patch columns over them
    mask, origin, res = _region_raster(poly_el, mm_per_uu, evenodd=True)
    if mask is None:
        return []
    H, W = mask.shape
    im = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(im)
    for fp in footprints:
        if fp is None or len(fp) < 3:
            continue
        dr.polygon([(float((x - origin[0]) / res), float((y - origin[1]) / res))
                    for x, y in fp], fill=255)
    resid = mask & ~(np.asarray(im) > 0)
    px_mm = res * mm_per_uu
    # open away sub-column slivers along column edges (they're covered by pull/overlap)
    resid = ndimage.binary_opening(
        resid, iterations=max(1, int(round(0.35 / px_mm))))
    if not resid.any():
        return []
    lbl, n = ndimage.label(resid, structure=ndimage.generate_binary_structure(2, 2))
    areas = np.bincount(lbl.ravel(), minlength=n + 1)
    out = []
    for k in range(1, n + 1):
        if float(areas[k]) * px_mm * px_mm < _RESIDUAL_MIN_MM2:
            continue
        comp = lbl == k
        lines = _turning_lines_from_mask(comp, origin, res, mm_per_uu, strip_mm)
        if not lines:
            lines = [np.asarray(seg, float) for seg in
                     _strip_lines_from_mask(comp, origin, res, mm_per_uu, strip_mm)]
        out.extend(lines)
    return out
_RDP_EPS_PX = 0.4           # iso-contour simplification tolerance (marching squares emits ~1
                            # point per pixel; a satin centerline doesn't need that resolution)


def _region_raster(poly_el, mm_per_uu: float, evenodd: bool = False):
    """Rasterise a region path into a bool mask on a ~0.3 mm/px grid (root frame), padded by
    2 background px so the EDT sees the true boundary even where the shape touches its own
    bbox. With `evenodd`, subpaths XOR (holes stay holes — needed when the pass must see the
    counter boundaries, e.g. outline objects); default draws the union (holes filled away,
    the historical turning-satin behaviour). Returns (mask, origin_xy, res_uu_per_px);
    (None, None, 0.0) on degenerate input."""
    from PIL import Image, ImageDraw
    subs = []
    for sub in re.split(r"[Mm]", (poly_el.get("d") if poly_el is not None else "") or ""):
        pts = [(float(x), float(y)) for x, y in _COORD_RE.findall(sub)]
        if len(pts) >= 3:
            subs.append(_xf(np.asarray(pts, float), _ctm(poly_el)))
    if not subs:
        return None, None, 0.0
    allp = np.concatenate(subs)
    x0, y0 = allp.min(0)
    x1, y1 = allp.max(0)
    res = max((0.3 / mm_per_uu), 1e-9)                 # uu per px (~0.3 mm/px)
    W, H = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
    if W < 3 or H < 3 or W * H > 6_000_000:
        return None, None, 0.0
    pad = 2
    mask = np.zeros((H + 2 * pad, W + 2 * pad), bool)
    for s in subs:
        im = Image.new("L", (W + 2 * pad, H + 2 * pad), 0)
        ImageDraw.Draw(im).polygon(
            [((px - x0) / res + pad, (py - y0) / res + pad) for px, py in s], fill=255)
        sub_mask = np.asarray(im) > 128
        mask = (mask ^ sub_mask) if evenodd else (mask | sub_mask)
    if int(mask.sum()) < 9:
        return None, None, 0.0
    return mask, np.array([x0 - pad * res, y0 - pad * res]), res


def _satin_strip_lines(poly_el, mm_per_uu: float, strip_mm: float = _STRIP_MM) -> list:
    """Tile a BROAD region with parallel satin strips ("sombras con satin"): rasterise the region,
    orient the strips along its PRINCIPAL axis (PCA) so columns follow the shape, band across the
    minor axis every `strip_mm`, and return each band's inside run as a straight centerline (2
    root-frame points). Each becomes a fixed-width satin column — so a broad shaded mass sews as
    satin (like production) instead of one tatami fill. Empty on degenerate geometry. NOTE: straight
    parallel columns leave STEPPED edges on irregular boundaries — _turning_satin_lines
    (contour-following) is the quality path and is tried FIRST; this is its fallback."""
    mask, origin, res = _region_raster(poly_el, mm_per_uu)
    if mask is None:
        return []
    return _strip_lines_from_mask(mask, origin, res, mm_per_uu, strip_mm)


def _strip_lines_from_mask(mask, origin, res: float, mm_per_uu: float,
                           strip_mm: float) -> list:
    """PCA-banded straight strip centerlines for an arbitrary mask (see
    _satin_strip_lines) — the mask-level core, shared with the residual-cover pass."""
    x0, y0 = origin
    H, W = mask.shape
    ys, xs = np.where(mask)
    if not len(xs):
        return []
    # Orient strips along the region's PRINCIPAL axis (PCA) so columns FOLLOW the shape (clean
    # ends, not stair-stepped horizontal bands); band across the minor axis every strip_mm.
    P = np.column_stack([xs, ys]).astype(float)
    if len(P) < 3:
        return []
    c = P.mean(0)
    evals, evecs = np.linalg.eigh(np.cov((P - c).T))
    u = evecs[:, int(np.argmax(evals))]                # principal (long) axis -> columns run along u
    v = np.array([-u[1], u[0]])                         # minor axis -> band across v
    pu, pv = (P - c) @ u, (P - c) @ v
    strip_px = max(strip_mm / (res * mm_per_uu), 3.0)
    min_run_px = max(_STRIP_MIN_RUN_MM / (res * mm_per_uu), 3.0)
    ts = np.arange(pu.min(), pu.max(), 1.0)             # sample along u
    lines, p = [], pv.min() + strip_px / 2
    while p <= pv.max() and len(lines) < _MAX_STRIPS_PER_REGION:
        pts = c + p * v[None, :] + ts[:, None] * u[None, :]
        ix = np.round(pts[:, 0]).astype(int)
        iy = np.round(pts[:, 1]).astype(int)
        inside = np.zeros(len(ts), bool)
        ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        inside[ok] = mask[iy[ok], ix[ok]]
        run_ids = np.where(inside)[0]
        if run_ids.size:
            for run in np.split(run_ids, np.where(np.diff(run_ids) > 1)[0] + 1):
                if run.size >= min_run_px:
                    a, b = pts[run[0]], pts[run[-1]]
                    lines.append(((x0 + a[0] * res, y0 + a[1] * res),
                                  (x0 + b[0] * res, y0 + b[1] * res)))
        p += strip_px
    return lines


# marching-squares case -> the pairs of crossed cell edges each contour segment joins
# (corner bits: tl=1, tr=2, br=4, bl=8; edges: t=top, r=right, b=bottom, l=left)
_MS_SEGS = {
    1: [("t", "l")], 2: [("t", "r")], 3: [("l", "r")], 4: [("r", "b")],
    5: [("t", "r"), ("b", "l")], 6: [("t", "b")], 7: [("l", "b")],
    8: [("l", "b")], 9: [("t", "b")], 10: [("t", "l"), ("r", "b")],
    11: [("r", "b")], 12: [("l", "r")], 13: [("t", "r")], 14: [("t", "l")],
}


def _iso_contours(D: np.ndarray, level: float) -> list[np.ndarray]:
    """Marching-squares iso-contours of the scalar field D (indexed [y, x]) at `level`,
    chained into ordered polylines. Returns (N,2) arrays of (x, y) pixel coordinates;
    closed loops get their first point repeated at the end. Hand-rolled — only
    numpy/scipy are available (no skimage/cv2/contourpy)."""
    inside = D >= level
    case = (inside[:-1, :-1].astype(np.uint8)
            + (inside[:-1, 1:].astype(np.uint8) << 1)
            + (inside[1:, 1:].astype(np.uint8) << 2)
            + (inside[1:, :-1].astype(np.uint8) << 3))
    cys, cxs = np.nonzero((case > 0) & (case < 15))
    if cys.size == 0:
        return []

    def edge_key(cy: int, cx: int, e: str):
        if e == "t":
            return ("h", cy, cx)
        if e == "b":
            return ("h", cy + 1, cx)
        if e == "l":
            return ("v", cy, cx)
        return ("v", cy, cx + 1)

    adj: dict = {}
    for cy, cx in zip(cys.tolist(), cxs.tolist()):
        for ea, eb in _MS_SEGS[int(case[cy, cx])]:
            a, b = edge_key(cy, cx, ea), edge_key(cy, cx, eb)
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)

    def point(key) -> tuple[float, float]:
        kind, y, x = key
        v0 = float(D[y, x])
        v1 = float(D[y, x + 1] if kind == "h" else D[y + 1, x])
        f = 0.5 if v1 == v0 else float(np.clip((level - v0) / (v1 - v0), 0.0, 1.0))
        return (x + f, float(y)) if kind == "h" else (float(x), y + f)

    def walk(start, seen) -> list:
        chain = [start]
        seen.add(start)
        cur = start
        while True:
            nxt = [n for n in adj[cur] if n not in seen]
            if not nxt:
                return chain
            cur = nxt[0]
            chain.append(cur)
            seen.add(cur)

    lines: list[np.ndarray] = []
    seen: set = set()
    for node in list(adj):                        # open chains first (degree-1 endpoints)
        if node not in seen and len(adj[node]) == 1:
            lines.append(np.asarray([point(k) for k in walk(node, seen)]))
    for node in list(adj):                        # what remains are closed loops
        if node not in seen:
            chain = walk(node, seen)
            lines.append(np.asarray([point(k) for k in chain] + [point(node)]))
    return [ln for ln in lines if len(ln) >= 2]


def _rdp(pts: np.ndarray, eps: float) -> np.ndarray:
    """Iterative Ramer-Douglas-Peucker simplification: drop points within `eps` of the
    local chord (marching squares emits ~1 point per pixel — far denser than a satin
    centerline needs)."""
    if len(pts) < 3:
        return pts
    keep = np.zeros(len(pts), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        seg = pts[j] - pts[i]
        length = float(np.hypot(seg[0], seg[1]))
        mid = pts[i + 1:j]
        if length < 1e-9:
            d = np.hypot(mid[:, 0] - pts[i, 0], mid[:, 1] - pts[i, 1])
        else:
            d = np.abs(seg[0] * (mid[:, 1] - pts[i, 1])
                       - seg[1] * (mid[:, 0] - pts[i, 0])) / length
        k = int(np.argmax(d))
        if d[k] > eps:
            k += i + 1
            keep[k] = True
            stack += [(i, k), (k, j)]
    return pts[keep]


# Branch-junction mitre (--branch-satin / satin-lean): per-branch satin columns end
# exactly AT the skeleton junction, leaving a small uncovered wedge where they meet.
# Extend each branch's centerline PAST the junction by the local half-width so the
# columns overlap in a mitre, like a hand digitize.
_MITRE_MIN_MM = 0.5
_MITRE_MAX_MM = 2.0
_MITRE_TOL_MM = 1.2       # centerline ends within this of each other = one junction
_MITRE_MAX_ENDS = 4       # more branch-ends than this in one cluster = a dense hub; skip


def _mitre_branch_junctions(centerlines: list, poly_el, mm_per_uu: float) -> int:
    """Where the kept branch centerlines MEET, extend each one past the junction by the
    local half-width (distance from the junction to the region boundary, clamped
    0.5-2mm). Clusters of more than _MITRE_MAX_ENDS ends are left alone (a dense hub —
    extending everything there would pile thread). Returns how many ends were extended."""
    if poly_el is None or len(centerlines) < 2:
        return 0
    A, B = _path_segments(poly_el.get("d") or "")
    if not len(A):
        return 0
    Mp = _ctm(poly_el)
    A, B = _xf(A, Mp), _xf(B, Mp)
    tol_uu = _MITRE_TOL_MM / mm_per_uu

    info = []
    for el in centerlines:
        pts = np.asarray([(float(x), float(y))
                          for x, y in _COORD_RE.findall(el.get("d") or "")], float)
        if len(pts) < 2:
            info.append(None)
            continue
        M = _ctm(el)
        scale = float(np.sqrt(abs(M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]))) or 1.0
        info.append({"el": el, "pts": pts, "root": _xf(pts, M),
                     "scale": scale, "touched": False})

    ends = []                                     # (centerline idx, end 0|-1, root point)
    for i, inf in enumerate(info):
        if inf is not None:
            ends.append((i, 0, inf["root"][0]))
            ends.append((i, -1, inf["root"][-1]))

    used: set[int] = set()
    n_ext = 0
    for a in range(len(ends)):
        if a in used:
            continue
        cluster = [a] + [b for b in range(a + 1, len(ends)) if b not in used
                         and float(np.hypot(*(ends[a][2] - ends[b][2]))) <= tol_uu]
        if len(cluster) < 2:
            continue
        used.update(cluster)
        if len(cluster) > _MITRE_MAX_ENDS:
            continue
        centre = np.mean([ends[x][2] for x in cluster], axis=0)
        hw_mm = float(_min_dist_to_segments(centre[None, :], A, B)[0]) * mm_per_uu
        ext_mm = float(np.clip(hw_mm, _MITRE_MIN_MM, _MITRE_MAX_MM))
        for x in cluster:
            ci, which, _pt = ends[x]
            inf = info[ci]
            pts = inf["pts"]
            tang = (pts[0] - pts[1]) if which == 0 else (pts[-1] - pts[-2])
            norm = float(np.hypot(*tang))
            if norm < 1e-9:
                continue
            step = tang / norm * (ext_mm / mm_per_uu / inf["scale"])
            newpt = (pts[0] if which == 0 else pts[-1]) + step
            inf["pts"] = (np.vstack([newpt[None], pts]) if which == 0
                          else np.vstack([pts, newpt[None]]))
            inf["touched"] = True
            n_ext += 1

    for inf in info:
        if inf is not None and inf["touched"]:
            inf["el"].set("d", "M " + " ".join(f"{x:.4f},{y:.4f}" for x, y in inf["pts"]))
    return n_ext


def _ring_length(pts: np.ndarray) -> float:
    seg = np.diff(pts, axis=0)
    return float(np.hypot(seg[:, 0], seg[:, 1]).sum())


def _normalize_ring(ring: np.ndarray) -> np.ndarray:
    """Open the closed ring (drop the repeated last point) and orient it CCW, so every
    ring in a spiral flows the same way."""
    pts = ring[:-1] if np.allclose(ring[0], ring[-1]) else ring
    x, y = pts[:, 0], pts[:, 1]
    area = float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return pts if area >= 0 else pts[::-1]


def _straightest_vertex(pts: np.ndarray) -> int:
    """Index of the vertex starting the LONGEST edge — after RDP that is the middle of
    the straightest boundary stretch (the seam belongs there, not on a corner)."""
    seg = np.diff(np.vstack([pts, pts[:1]]), axis=0)
    return int(np.argmax(np.hypot(seg[:, 0], seg[:, 1])))


def _segments_cross(p, q, A, B) -> bool:
    """Does the open segment p->q properly cross any segment A[i]->B[i]? (Endpoints of
    p->q are pulled in 2% so touching a ring at the connector's own ends doesn't count.)"""
    d0 = q - p
    p = p + 0.02 * d0
    q = q - 0.02 * d0
    d = q - p
    e = B - A
    f = A - p
    denom = d[0] * e[:, 1] - d[1] * e[:, 0]
    ok = np.abs(denom) > 1e-12
    t = np.where(ok, (f[:, 0] * e[:, 1] - f[:, 1] * e[:, 0]) / np.where(ok, denom, 1), -1)
    u = np.where(ok, (f[:, 0] * d[1] - f[:, 1] * d[0]) / np.where(ok, denom, 1), -1)
    return bool(np.any(ok & (t > 0) & (t < 1) & (u > 0) & (u < 1)))


def _spiral_rings(levels: list[list[np.ndarray]], step_px: float):
    """Chain the concentric ring centerlines into OPEN SPIRALS: each ring is cut at a seam
    (outermost: on its straightest stretch; deeper: at the vertex nearest the previous
    ring's seam), traversed fully, then connected to the next ring by a short radial step —
    ONE satin column per nesting chain instead of one per ring, so there are no per-ring
    trims/locks and no aligned radial seam. A connector that would cross ring geometry, or
    a ring with no unambiguous parent, breaks the chain (those rings stay standalone).
    Returns (spirals, standalone_rings)."""
    max_conn = 1.75 * step_px
    chains: list[dict] = []
    standalone: list[np.ndarray] = []
    for lv, rings in enumerate(levels):
        claimed: set[int] = set()
        if lv > 0:
            for ch in chains:
                if ch["done"]:
                    continue
                # candidate deeper rings reachable from this chain's seam
                cand = [(j, float(np.min(np.hypot(*(rings[j] - ch["seam"]).T))))
                        for j in range(len(rings)) if j not in claimed]
                near = [(j, dmin) for j, dmin in cand if dmin <= max_conn]
                if len(near) != 1:
                    ch["done"] = True              # split / dead end -> close the chain
                    continue
                j, _ = near[0]
                ring = _normalize_ring(rings[j])
                cut = int(np.argmin(np.hypot(*(ring - ch["seam"]).T)))
                rolled = np.roll(ring, -cut, axis=0)
                loop = np.vstack([rolled, rolled[:1]])
                conn_p, conn_q = ch["seam"], loop[0]
                segs = np.vstack([ch["pts"], loop])
                if _segments_cross(conn_p, conn_q, segs[:-1], segs[1:]):
                    ch["done"] = True              # radial step would cross the satin path
                    continue
                claimed.add(j)
                ch["pts"] = np.vstack([ch["pts"], loop])
                ch["seam"] = loop[0]
                ch["levels"] += 1
        for j in range(len(rings)):
            if j in claimed:
                continue
            if lv == len(levels) - 1 and _ring_length(rings[j]) < 6.0 * step_px:
                continue    # tight innermost core: the neighbouring ring's satin covers it
            ring = _normalize_ring(rings[j])
            cut = _straightest_vertex(ring)
            rolled = np.roll(ring, -cut, axis=0)
            chains.append({"pts": np.vstack([rolled, rolled[:1]]),
                           "seam": rolled[0], "levels": 1, "done": False})
    spirals = [ch["pts"] for ch in chains if ch["levels"] > 1]
    standalone += [ch["pts"] for ch in chains if ch["levels"] == 1]
    return spirals, standalone


def _stagger_ring_seams(levels: list[list[np.ndarray]], step_px: float) -> list[np.ndarray]:
    """Re-cut each ring's seam ~1.5 steps FURTHER along the boundary than the previous
    ring's: consecutive seams stay within the travel-drop budget (the chain sews near-
    continuously once the travel planner removes the junction trims) but never line up
    into a visible radial corridor. The outermost seam sits on the straightest boundary
    stretch. (Chaining the rings into ONE spiral column was DISPROVEN empirically: turns
    touch by construction — step == width — so the column's rails graze the neighbouring
    turns and Ink-Stitch's rail pairing degenerates into multi-turn diagonal throws,
    measured median stitch 13.7mm fraction-paired / 14.6mm with explicit rungs, vs the
    3.3mm width. _spiral_rings is kept as tested geometry, unused for emission.)"""
    out: list[np.ndarray] = []
    prev_seam = None
    for rings_k in levels:
        for ring in rings_k:
            r = _normalize_ring(ring)
            if prev_seam is None:
                rolled = np.roll(r, -_straightest_vertex(r), axis=0)
                out.append(_ring_polyline(rolled, step_px))
                prev_seam = rolled[0]
                continue
            # nearest vertex to the previous seam, then advance the seam ~1.5 steps
            # ALONG the ring (interpolated — RDP vertices are sparse on straights, so
            # a vertex-snapped advance can overshoot to the far side of the shape)
            near = int(np.argmin(np.hypot(*(r - prev_seam).T)))
            rolled = np.roll(r, -near, axis=0)
            closed = np.vstack([rolled, rolled[:1]])
            seg = np.diff(closed, axis=0)
            seglen = np.hypot(seg[:, 0], seg[:, 1])
            arc = np.concatenate([[0.0], np.cumsum(seglen)])
            target = min(1.5 * step_px, 0.4 * arc[-1])   # tiny ring: cap the drift
            j = max(0, min(int(np.searchsorted(arc, target, side="right")) - 1,
                           len(seglen) - 1))
            t = (target - arc[j]) / max(float(seglen[j]), 1e-9)
            cut_pt = closed[j] + t * seg[j]
            rest = np.vstack([rolled[j + 1:], rolled[:j + 1]])
            out.append(_ring_polyline(np.vstack([cut_pt[None], rest]), step_px))
            prev_seam = cut_pt
    return out


def _ring_polyline(rolled: np.ndarray, overlap_px: float) -> np.ndarray:
    """Close a ring centerline AND overshoot ~one step past the seam, so the satin column
    double-covers the closure. Without the overshoot the stretch between the column's
    final rung and the seam thins out, leaving a small uncovered wedge at every ring seam
    (visible as a drifting trail of gaps once the seams are staggered)."""
    closed = np.vstack([rolled, rolled[:1]])
    acc = 0.0
    for i in range(1, len(closed)):
        v = closed[i] - closed[i - 1]
        L = float(np.hypot(*v))
        if acc + L >= overlap_px:
            t = (overlap_px - acc) / max(L, 1e-9)
            return np.vstack([closed, closed[1:i], (closed[i - 1] + t * v)[None]])
        acc += L
    return np.vstack([closed, closed[1:]])       # tiny ring: full second lap


def _turning_satin_lines(poly_el, mm_per_uu: float, strip_mm: float = _STRIP_MM,
                         spiral: bool = False) -> list:
    """CONTOUR-FOLLOWING ("turning") satin centerlines for a broad region: onion-peel the
    region by its distance field. Ring k's centerline is the iso-contour of the EDT at depth
    (k+0.5)*step, with the step equalised to <= strip_mm so the deepest core is covered (a
    fixed step can leave an uncovered centre up to half a strip deep). The outermost ring
    hugs the region boundary and every deeper ring turns with the shape — the production
    'turning satin' look; _satin_strip_lines' straight strips (stepped edges on irregular
    boundaries) remain only as the fallback. Rings are emitted with STAGGERED seams (see
    _stagger_ring_seams; the travel planner then drops the ring-to-ring trims, so the
    chain sews near-continuously with no aligned radial seam). `spiral=True` instead
    returns the single-polyline spiral per nesting chain — valid geometry kept for tests,
    but NOT sewable as one satin column (rails graze the touching turns; see
    _stagger_ring_seams). Returns (N,2) root-frame polylines, outermost-first. Empty on
    degenerate geometry (caller falls back)."""
    mask, origin, res = _region_raster(poly_el, mm_per_uu)
    if mask is None:
        return []
    return _turning_lines_from_mask(mask, origin, res, mm_per_uu, strip_mm, spiral)


def _turning_lines_from_mask(mask, origin, res: float, mm_per_uu: float,
                             strip_mm: float = _STRIP_MM,
                             spiral: bool = False) -> list:
    """Onion-peel ring centerlines for an arbitrary mask (see _turning_satin_lines) —
    the mask-level core, shared with the residual-cover pass."""
    D = ndimage.distance_transform_edt(mask)
    dmax = float(D.max())
    strip_px = max(strip_mm / (res * mm_per_uu), 3.0)
    if dmax < strip_px / 2:
        return []                                  # thinner than one strip everywhere
    # A closed ring shorter than ~1.6*pi*strip encloses a radius under ~0.8*strip:
    # the inner rail sits within ~0.3*strip of the center, stroke_to_satin's offset
    # inverts through it, and the column sews a SUNBURST "urchin" fan (measured on
    # the arb dots: 25+ thread layers piled on one spot; plain pi*strip still let
    # radius~strip rings urchin). Such rings are dropped — a dot then falls through
    # to the straight-strip fallback (one clean fixed-width column across it).
    min_len_px = max(_STRIP_MIN_RUN_MM / (res * mm_per_uu), 3.0,
                     1.6 * float(np.pi) * strip_px)
    # Ring depths at FULL strip pitch, so adjacent rings TOUCH instead of overlapping.
    # (The historical `step = dmax/ceil(dmax/strip)` equalisation made every ring pair
    # overlap by (strip-step) — up to ~50% on shallow bands, exactly doubling the sewn
    # thread when the strip narrowed to the production 1.75mm: measured 92k stitches
    # vs the 46k reference. Production columns sit side-by-side; reference stacking
    # peaks at 3.6 layers.) A leftover core deeper than ~15% of a strip gets one final
    # half-inset ring — the only place two rings may overlap.
    depths = list(np.arange(strip_px / 2, dmax - strip_px / 2 + 1e-6, strip_px))
    if not depths:
        depths = [dmax / 2]
    elif dmax - (depths[-1] + strip_px / 2) > 0.15 * strip_px:
        depths.append(dmax - strip_px / 2)
    step = strip_px
    levels: list[list[np.ndarray]] = []
    total = 0
    for depth in depths:
        rings_k: list[np.ndarray] = []
        for line in _iso_contours(D, depth):
            line = _rdp(line, _RDP_EPS_PX)
            if _ring_length(line) < min_len_px:
                continue
            rings_k.append(line)
            total += 1
            if total >= _MAX_STRIPS_PER_REGION:
                break
        levels.append(rings_k)
        if total >= _MAX_STRIPS_PER_REGION:
            break
    if not total:
        return []
    if spiral:
        spirals, single = _spiral_rings(levels, step)
        out_px = spirals + single
    else:
        out_px = _stagger_ring_seams(levels, step)
    return [origin + pts * res for pts in out_px]


# --------------------------------------------------------------------------- #
# outline objects (--outline-objects): the production "outline family"
# --------------------------------------------------------------------------- #
# Production designs are LAYERED: the pink-goku ground-truth pair decomposes into 118 fill
# + 217 OUTLINE objects — satin borders/detail sewn ON TOP of the fills — which is where
# most of its 82.9% satin comes from. Our trace is a flat non-overlapping colour partition,
# so without this pass no border object ever exists. For each substantial fill region we
# ride a CLOSED satin border along its boundary: centerline = the EDT iso-contour at depth
# w/2, so the satin's outer edge kisses the region boundary and its inner half OVERLAPS the
# fill (deliberate, like production — it also acts as a mini-underlap at the seam). Hole
# rings (letter counters etc.) are bordered too (evenodd raster keeps them).
_BORDER_MIN_AREA_MM2 = 40.0   # only substantial fills get a border (production borders shapes,
                              # not specks; small regions are already crisp)
_BORDER_MIN_LEN_MM = 8.0      # skip border rings shorter than this (slivers)
_BORDER_W_MIN_MM = 1.5        # clamp for the border width read from the category profile
_BORDER_W_MAX_MM = 3.0
_MAX_BORDERS = 150            # guard: a design shouldn't explode into border soup


def _outline_border_w_mm(category: str | None) -> float:
    """Border width: what production sews its outline objects at — the PAIR prior's measured
    satin width median when the category has ingested pairs, else the ground-truth profile's
    median satin width; clamped to a sane band. Fallback 2.0 mm."""
    try:
        med = priors.border_width_mm(category)
        if med is None:
            med = (load_profiles().get(category or "", {}).get("satin_w_mm") or {}).get("med")
        return float(np.clip(float(med), _BORDER_W_MIN_MM, _BORDER_W_MAX_MM))
    except Exception:
        return 2.0


def _border_centerlines(poly_el, mm_per_uu: float, w_mm: float) -> list:
    """Closed border centerlines for one fill region: EDT iso-contours at depth w/2 (outer
    satin edge on the region boundary), evenodd so hole boundaries are bordered too.
    Returns (N,2) root-frame polylines; empty when the region is thinner than the border
    or degenerate (caller just skips it)."""
    mask, origin, res = _region_raster(poly_el, mm_per_uu, evenodd=True)
    if mask is None:
        return []
    px_mm = res * mm_per_uu                            # mm per raster px
    if float(mask.sum()) * px_mm * px_mm < _BORDER_MIN_AREA_MM2:
        return []
    D = ndimage.distance_transform_edt(mask)
    depth_px = (w_mm / 2) / px_mm
    if float(D.max()) <= depth_px:
        return []                                      # thinner than the border everywhere
    min_len_px = _BORDER_MIN_LEN_MM / px_mm
    out = []
    for line in _iso_contours(D, depth_px):
        line = _rdp(line, _RDP_EPS_PX)
        seg = np.diff(line, axis=0)
        if np.hypot(seg[:, 0], seg[:, 1]).sum() < min_len_px:
            continue
        out.append(origin + line * res)
    return out


def _fill_colour(p) -> str | None:
    """The region's colour: fill attr or style fill; None for non-fills/centerlines."""
    m = re.search(r"fill:\s*(#[0-9a-fA-F]{6})", p.get("style") or "")
    c = m.group(1) if m else p.get("fill")
    return c if (c and c != "none") else None


def _add_outline_objects(ctx: PipelineContext, binary: Path, ready_svg: Path) -> int:
    """Layer closed satin borders over the substantial fill regions of the ready SVG (see
    the block comment above). Each border is inserted immediately AFTER its fill in the
    same colour group (sews right after it, before the next colour), then stroke_to_satin
    turns the batch into satin columns and they get the standard satin params. Best-effort:
    any failure leaves the ready SVG exactly as it was. Returns how many borders were made."""
    cfg = ctx.config
    w_mm = _outline_border_w_mm(cfg.category)
    tree = etree.parse(str(ready_svg))
    root = tree.getroot()
    mm_per_uu = _mm_per_uu(root)
    w_uu = w_mm / mm_per_uu

    border_ids: list[str] = []
    n = 0
    for p in list(root.iter(f"{{{_SVG_NS}}}path")):
        if n >= _MAX_BORDERS:
            break
        if (p.get(f"{{{_INKSTITCH_NS}}}satin_column") is not None
                or p.get(f"{{{_INKSTITCH_NS}}}stroke_method") is not None
                or p.get(f"{{{_INKSTITCH_NS}}}end_row_spacing_mm") is not None
                or _is_centerline(p)):
            continue
        colour = _fill_colour(p)
        if colour is None:
            continue
        try:
            rings = _border_centerlines(p, mm_per_uu, w_mm)
        except Exception:
            continue
        parent = p.getparent()
        pos = parent.index(p)
        for ring in rings:
            if n >= _MAX_BORDERS:
                break
            el = etree.Element(f"{{{_SVG_NS}}}path")
            el.set("id", f"border{n}")
            el.set("d", "M " + " ".join(f"{x:.3f},{y:.3f}" for x, y in ring))
            _set_stroke_style(el, w_uu, colour)
            pos += 1
            parent.insert(pos, el)                     # right after the fill it borders
            border_ids.append(f"border{n}")
            n += 1

    if not border_ids:
        return 0
    tree.write(str(ready_svg), xml_declaration=True, encoding="UTF-8")
    try:
        _run_extension(binary, "stroke_to_satin", border_ids, [], ready_svg, ready_svg,
                       timeout=_SATIN_TIMEOUT_S)
        # the new columns need the standard satin params (underlay, pull-comp, trim_after);
        # pre-existing satins already carry trim_after, so stamp only the unstamped ones.
        tree = etree.parse(str(ready_svg))
        satin_params = _satin_params(_resolved_pull_comp(ctx),
                                     _resolved_satin_underlay(ctx),
                                     _authored_satin_spacing(ctx))
        for p in tree.getroot().iter(f"{{{_SVG_NS}}}path"):
            if (p.get(f"{{{_INKSTITCH_NS}}}satin_column") is not None
                    and p.get(f"{{{_INKSTITCH_NS}}}trim_after") is None):
                for key, value in satin_params.items():
                    p.set(f"{{{_INKSTITCH_NS}}}{key}", value)
                # marker: this satin is a BORDER bonded to the fill before it (the travel
                # planner must never separate them; stroke_to_satin renamed the ids)
                p.set("data-wilcom-border", "1")
        tree.write(str(ready_svg), xml_declaration=True, encoding="UTF-8")
    except Exception as exc:
        # roll back: strip any border strokes so the design is exactly the pre-pass one
        print(f"      outline objects failed ({type(exc).__name__}); skipped", flush=True)
        try:
            tree = etree.parse(str(ready_svg))
            for p in list(tree.getroot().iter(f"{{{_SVG_NS}}}path")):
                if (p.get("id") or "").startswith("border"):
                    p.getparent().remove(p)
            tree.write(str(ready_svg), xml_declaration=True, encoding="UTF-8")
        except Exception:
            pass
        return 0
    print(f"      outline objects -> {n} satin border(s) @ {w_mm:.1f}mm "
          f"(production outline family)", flush=True)
    return n


# --------------------------------------------------------------------------- #
# travel planning (entry/exit + travel-under-cover): kill the trims
# --------------------------------------------------------------------------- #
# Production sews near-continuously (pink-goku: 15k stitches, 0 trims); we used to trim
# after every region (~71 on joker). PROBED Ink-Stitch controllability (see the goal log):
# the `starting_point` / `ending_point` OBJECT COMMANDS work for fills — a command is a
# <g> holding a connector <path> (inkscape:connection-end = the target) plus a
# <use xlink:href="#inkstitch_starting_point|_ending_point" x= y=>, with the two <symbol>
# defs present in the doc (vendored at vendor/inkstitch/symbols/inkstitch.svg). Ink-Stitch
# snaps the commanded position to the target's NEAREST BOUNDARY POINT, so entry and exit
# are fully steerable; satin columns / runs enter and exit at their fixed path endpoints.
# The planner chains each colour's pieces nearest-neighbour, pins fill entries/exits to
# the junction points, and drops trim_after ONLY where the straight travel exit->entry is
# short and covered by stitching that sews later (or stays inside the colour's own
# regions) — the cover law: never drop a trim where the travel would show.
_TRAVEL_MAX_MM = 12.0     # longest travel we'll leave untrimmed
_TRAVEL_COVER_MIN = 0.90  # fraction of the travel that must be covered
_TRAVEL_RES_MM = 0.5      # raster resolution for the cover masks
_XLINK_NS = "http://www.w3.org/1999/xlink"
_INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"


def _load_command_symbols() -> dict[str, "etree._Element"] | None:
    """The starting/ending-point <symbol> defs from the vendored Ink-Stitch bundle."""
    try:
        sym_file = _candidate_binary().parent.parent / "symbols" / "inkstitch.svg"
        root = etree.parse(str(sym_file)).getroot()
        out = {}
        for s in root.iter(f"{{{_SVG_NS}}}symbol"):
            if s.get("id") in ("inkstitch_starting_point", "inkstitch_ending_point"):
                out[s.get("id")] = s
        return out if len(out) == 2 else None
    except Exception:
        return None


def _ensure_command_symbols(root, symbols) -> None:
    defs = root.find(f"{{{_SVG_NS}}}defs")
    if defs is None:
        defs = etree.Element(f"{{{_SVG_NS}}}defs")
        root.insert(0, defs)
    have = {s.get("id") for s in defs.iter(f"{{{_SVG_NS}}}symbol")}
    for sid, sym in symbols.items():
        if sid not in have:
            defs.append(etree.fromstring(etree.tostring(sym)))


def _add_point_command(target, kind: str, x: float, y: float, n: int) -> None:
    """Attach a starting_point/ending_point command to `target` (inserted right after it,
    same structure Ink-Stitch's own `commands` extension emits, sans the scale transform
    so x/y are plain user units)."""
    g = etree.Element(f"{{{_SVG_NS}}}g", id=f"command_group_tp{n}")
    conn = etree.SubElement(g, f"{{{_SVG_NS}}}path", id=f"command_connector_tp{n}")
    conn.set("d", f"M {x:.3f},{y:.3f} {x + 0.1:.3f},{y:.3f}")
    conn.set("style", "fill:none;stroke:#000000;stroke-width:1;stroke-opacity:0.5;"
                      "display:none")
    conn.set(f"{{{_INKSCAPE_NS}}}connection-start", f"#command_use_tp{n}")
    conn.set(f"{{{_INKSCAPE_NS}}}connection-end", f"#{target.get('id')}")
    conn.set(f"{{{_INKSCAPE_NS}}}connector-type", "polyline")
    use = etree.SubElement(g, f"{{{_SVG_NS}}}use", id=f"command_use_tp{n}")
    use.set(f"{{{_XLINK_NS}}}href", f"#inkstitch_{kind}")
    use.set("x", f"{x:.3f}")
    use.set("y", f"{y:.3f}")
    parent = target.getparent()
    parent.insert(parent.index(target) + 1, g)


def _path_vertices(p) -> np.ndarray:
    """All subpath vertices of a path, in the root user-unit frame."""
    A, _ = _path_segments(p.get("d") or "")
    return _xf(A, _ctm(p)) if len(A) else A


def _closest_pair(P: np.ndarray, Q: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Closest vertex pair between two point sets (brute force; sets are small)."""
    d = ((P[:, None, :] - Q[None, :, :]) ** 2).sum(-1)
    i, j = np.unravel_index(int(np.argmin(d)), d.shape)
    return P[i], Q[j], float(np.sqrt(d[i, j]))


def _piece_kind(p) -> str:
    if p.get(f"{{{_INKSTITCH_NS}}}satin_column") is not None:
        return "satin"
    if p.get(f"{{{_INKSTITCH_NS}}}stroke_method") is not None:
        return "run"
    if p.get(f"{{{_INKSTITCH_NS}}}end_row_spacing_mm") is not None:
        return "gradient"
    return "fill"


def _group_pieces(g) -> list[dict]:
    """The group's stitchable paths in document order, with geometry. A border satin
    (data-wilcom-border) bonds to the piece before it: the chain must never separate a
    fill from its border, so bonded paths share a unit id."""
    pieces = []
    unit = -1
    for p in g:
        if not isinstance(p.tag, str) or etree.QName(p).localname != "path":
            continue
        if (p.get("id") or "").startswith(("frame_anchor", "command_")):
            continue
        pts = _path_vertices(p)
        if len(pts) < 2:
            continue
        if p.get("data-wilcom-border") is None or not pieces:
            unit += 1
        pieces.append({"el": p, "kind": _piece_kind(p), "pts": pts, "unit": unit})
    return pieces


def _chain_units(pieces: list[dict]) -> list[dict]:
    """Greedy nearest-neighbour ordering of the group's units (bonded paths move
    together): each unit is followed by the closest remaining one."""
    units: dict[int, list[dict]] = {}
    for pc in pieces:
        units.setdefault(pc["unit"], []).append(pc)
    ids = sorted(units)
    if len(ids) <= 2:
        return pieces
    order = [ids[0]]
    remaining = set(ids[1:])
    while remaining:
        tail = np.concatenate([pc["pts"] for pc in units[order[-1]]])
        best = min(remaining,
                   key=lambda u: _closest_pair(
                       tail, np.concatenate([pc["pts"] for pc in units[u]]))[2])
        order.append(best)
        remaining.discard(best)
    return [pc for u in order for pc in units[u]]


def _piece_endpoints(pc: dict, prev_exit, next_pts) -> tuple[np.ndarray, np.ndarray]:
    """(entry, exit) points of a piece. Fills are steerable (commands snap to the nearest
    boundary point, so entry = the vertex nearest the previous exit, exit = the vertex
    nearest the next piece); satins/runs enter and exit at their fixed path endpoints
    (a border ring's seam is its first vertex)."""
    pts = pc["pts"]
    if pc["kind"] == "fill":
        entry = (pts[int(np.argmin(((pts - prev_exit) ** 2).sum(1)))]
                 if prev_exit is not None else pts[0])
        exit_ = (
            _closest_pair(pts, next_pts)[0] if next_pts is not None else pts[-1])
        return entry, exit_
    d = pc["el"].get("d") or ""
    verts = [(float(x), float(y)) for x, y in _COORD_RE.findall(d)]
    first = _xf(np.asarray(verts[:1], float), _ctm(pc["el"]))[0]
    last = _xf(np.asarray(verts[-1:], float), _ctm(pc["el"]))[0]
    if pc["kind"] == "satin":
        # a closed border ring starts and ends at its seam; an open linework column
        # sews rail-end to rail-end — approximate exit with the first rail's far end
        return first, (first if np.hypot(*(first - last)) < 1e-6 else last)
    return first, last


def _build_cover_masks(all_pieces: list[dict], mm_per_uu: float):
    """One raster mask per piece on a SHARED ~0.5mm/px canvas (fills as even-odd
    polygons; satins/runs as fat polylines). Returns (masks, origin, res_uu_per_px)."""
    from PIL import Image, ImageDraw
    allp = np.concatenate([pc["pts"] for pc in all_pieces])
    x0, y0 = allp.min(0) - 2
    x1, y1 = allp.max(0) + 2
    res = _TRAVEL_RES_MM / mm_per_uu
    W = int((x1 - x0) / res) + 3
    H = int((y1 - y0) / res) + 3
    if W * H > 12_000_000:
        return None, None, 0.0
    masks = []
    for pc in all_pieces:
        im = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(im)
        M = _ctm(pc["el"])
        wide = max(int(2.0 / mm_per_uu / res), 2)      # ~2mm band for stroked pieces
        acc = np.zeros((H, W), bool)
        subs = []
        for sub in re.split(r"[Mm]", pc["el"].get("d") or ""):
            verts = [(float(x), float(y)) for x, y in _COORD_RE.findall(sub)]
            if len(verts) >= 2:
                subs.append(_xf(np.asarray(verts, float), M))
        if pc["kind"] == "satin" and len(subs) >= 2:
            # a satin column's d holds its two RAILS (the longest subpaths) + rungs;
            # the stitched area is the band BETWEEN the rails — fill that polygon, not
            # thin lines along the rails (thin masks under-measure the cover of travels
            # crossing the column and block legitimate trim drops)
            rails = sorted(subs, key=lambda s: -_ring_length(s))[:2]
            poly = np.vstack([rails[0], rails[1][::-1]])
            px = [((x - x0) / res, (y - y0) / res) for x, y in poly]
            if len(px) >= 3:
                dr.polygon(px, fill=255)
            for s in subs:
                dr.line([((x - x0) / res, (y - y0) / res) for x, y in s],
                        fill=255, width=wide)
        else:
            for pts in subs:
                px = [((x - x0) / res, (y - y0) / res) for x, y in pts]
                if pc["kind"] == "fill" and len(px) >= 3:
                    im2 = Image.new("L", (W, H), 0)
                    ImageDraw.Draw(im2).polygon(px, fill=255)
                    acc ^= np.asarray(im2) > 128       # even-odd: holes stay holes
                else:
                    dr.line(px, fill=255, width=wide)
        masks.append(acc | (np.asarray(im) > 128))
    return masks, np.array([x0, y0]), res


def _segment_covered(p, q, cover: np.ndarray, origin, res) -> float:
    """Fraction of the straight segment p->q covered by the cover mask."""
    n = max(int(np.hypot(*(q - p)) / res), 2)
    ts = np.linspace(0.0, 1.0, n)
    pts = p[None, :] + ts[:, None] * (q - p)[None, :]
    ix = ((pts[:, 0] - origin[0]) / res).astype(int)
    iy = ((pts[:, 1] - origin[1]) / res).astype(int)
    ok = (ix >= 0) & (ix < cover.shape[1]) & (iy >= 0) & (iy < cover.shape[0])
    hit = np.zeros(n, bool)
    hit[ok] = cover[iy[ok], ix[ok]]
    return float(hit.mean())


def _plan_travel(ctx: PipelineContext, ready_svg: Path) -> int:
    """Chain each colour's pieces, steer fill entries/exits to the junctions, and drop
    trim_after wherever the travel is short + covered (see the block comment above).
    Best-effort: any failure leaves the ready SVG untouched. Returns trims dropped."""
    try:
        symbols = _load_command_symbols()
        if symbols is None:
            return 0
        trim_off = priors.trim_after_off(ctx.config.category)
        tree = etree.parse(str(ready_svg))
        root = tree.getroot()
        mm_per_uu = _mm_per_uu(root)
        groups = _colour_groups(root)

        # 1. chain within each group (reorder the group's children; bonded units intact)
        per_group: list[list[dict]] = []
        for g in groups:
            pieces = _chain_units(_group_pieces(g))
            for pc in pieces:                          # apply the new document order
                g.append(pc["el"])
            per_group.append(pieces)

        all_pieces = [pc for pieces in per_group for pc in pieces]
        if len(all_pieces) < 2:
            return 0
        masks, origin, res = _build_cover_masks(all_pieces, mm_per_uu)
        if masks is None:
            return 0
        # union of everything sewn AFTER piece i (cumulative from the end, doc order)
        later = [np.zeros_like(masks[0])] * len(masks)
        acc = np.zeros_like(masks[0])
        for i in range(len(masks) - 1, -1, -1):
            later[i] = acc
            acc = acc | masks[i]

        trim_attr = f"{{{_INKSTITCH_NS}}}trim_after"
        max_uu = _TRAVEL_MAX_MM / mm_per_uu
        n_cmd = 0
        dropped = 0
        base = 0
        for pieces in per_group:
            colour_union = np.zeros_like(masks[0])
            for k in range(len(pieces)):
                colour_union = colour_union | masks[base + k]
            prev_exit = None
            exits: list = []
            entries: list = []
            for k, pc in enumerate(pieces):
                nxt = pieces[k + 1]["pts"] if k + 1 < len(pieces) else None
                entry, exit_ = _piece_endpoints(pc, prev_exit, nxt)
                if pc["kind"] == "fill":               # steer via object commands
                    _add_point_command(pc["el"], "starting_point",
                                       float(entry[0]), float(entry[1]), n_cmd)
                    n_cmd += 1
                    _add_point_command(pc["el"], "ending_point",
                                       float(exit_[0]), float(exit_[1]), n_cmd)
                    n_cmd += 1
                entries.append(entry)
                exits.append(exit_)
                prev_exit = exit_
            for k in range(len(pieces) - 1):           # drop trims where the law allows
                p, q = exits[k], entries[k + 1]
                # Authored-prior override: a category whose production connectors are
                # "Trim after: Off" (arb trio: jump connectors, no tie-in, 2 trims in
                # 46k stitches) trims ONLY at colour changes — every within-colour
                # connector stays a draped jump the operator scissors (the reference
                # sews ~275mm of untrimmed connectors), so neither the 12mm travel cap
                # nor the cover law applies.
                if not trim_off:
                    if np.hypot(*(q - p)) > max_uu:
                        continue
                    cover = later[base + k + 1] | colour_union
                    if _segment_covered(p, q, cover, origin, res) < _TRAVEL_COVER_MIN:
                        continue
                if pieces[k]["el"].get(trim_attr) is not None:
                    del pieces[k]["el"].attrib[trim_attr]
                    dropped += 1
            base += len(pieces)

        if n_cmd:
            _ensure_command_symbols(root, symbols)
        tree.write(str(ready_svg), xml_declaration=True, encoding="UTF-8")
        if dropped:
            law = ("authored Trim-after-Off: colour changes only" if trim_off
                   else f"covered travel <= {_TRAVEL_MAX_MM:g}mm")
            print(f"      travel plan -> {dropped} trim(s) dropped ({law}), "
                  f"{n_cmd} entry/exit command(s)", flush=True)
        return dropped
    except Exception as exc:
        print(f"      travel plan skipped ({type(exc).__name__}: {exc})", flush=True)
        return 0


def _ensure_guide_marker(root) -> None:
    """Add the guide-line marker def once (so `url(#...)` in a guide's style resolves)."""
    for m in root.iter(f"{{{_SVG_NS}}}marker"):
        if m.get("id") == _GUIDE_MARKER_ID:
            return
    defs = root.find(f"{{{_SVG_NS}}}defs")
    if defs is None:
        defs = etree.Element(f"{{{_SVG_NS}}}defs")
        root.insert(0, defs)
    defs.append(etree.fromstring(_GUIDE_MARKER_XML))


def _apply_spine_fills(root, spine_cands, originals, thread_hex) -> int:
    """Turn each (orig, guide, idx) into a guided_fill: mark the guide centerline, tag the
    original fill `guided_fill`, and wrap the pair in their own <g> (a guide steers only the
    fills in its group). Returns how many regions were converted."""
    n = 0
    for orig, guide, idx in spine_cands:
        op = originals.get(orig)
        if op is None or op.getparent() is None or guide.getparent() is None:
            continue
        _set_stroke_style(guide, 1.0, thread_hex.get(idx, "#000000"))
        gs = guide.get("style") or ""
        if _GUIDE_MARKER_ID not in gs:
            guide.set("style", (gs + f";marker-start:url(#{_GUIDE_MARKER_ID})").lstrip(";"))
        op.set(f"{{{_INKSTITCH_NS}}}fill_method", "guided_fill")
        parent = op.getparent()
        pos = list(parent).index(op)
        grp = etree.Element(f"{{{_SVG_NS}}}g", id=f"spine_{orig}")
        parent.insert(pos, grp)
        for el in (op, guide):
            if el.getparent() is not None:
                el.getparent().remove(el)
            grp.append(el)
        n += 1
    if n:
        _ensure_guide_marker(root)
    return n


# meander_fill needs room for at least one pattern cell: on a region much smaller — or
# THINNER — than the pattern, Ink-Stitch raises "Could not build graph for meander
# stitching" and the whole pass dies. A fur sliver has a big bbox but a tiny mean width,
# so the gate needs both: extent in both axes AND mean width (2·area/perimeter).
_MEANDER_MIN_MM = 8.0
_MEANDER_MIN_WIDTH_MM = 5.0


def _svg_mm_per_unit(root) -> float:
    """viewBox-unit -> mm scale from the SVG root (0.0 when unknowable)."""
    w, vb = root.get("width"), root.get("viewBox")
    try:
        wmm = float(w[:-2]) if w and w.endswith("mm") else float(w)
        vw = float(vb.split()[2])
        return wmm / vw if vw else 0.0
    except (TypeError, ValueError, IndexError):
        return 0.0


def _path_scale(p) -> float:
    m = re.search(r"scale\(\s*(-?\d+\.?\d*)", p.get("transform") or "")
    return abs(float(m.group(1))) if m else 1.0


def _path_bbox_units(p) -> tuple[float, float]:
    """Bounding-box (w, h) of a path's coordinates in root units (M/L/C data — every
    number is one half of a coordinate pair — with any scale() transform applied)."""
    nums = [float(v) for v in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", p.get("d", ""))]
    if len(nums) < 4:
        return 0.0, 0.0
    xs, ys = nums[0::2], nums[1::2]
    sc = _path_scale(p)
    return (max(xs) - min(xs)) * sc, (max(ys) - min(ys)) * sc


def _path_mean_width_units(p) -> float:
    """Mean-width proxy 2·|area|/perimeter in root units, shoelace per subpath (signed,
    so opposite-winding holes subtract). A fur sliver measures big in bbox but ~its
    stroke width here — which is what meander actually needs room across."""
    area = 0.0
    perim = 0.0
    for sub in re.split(r"[Mm]", p.get("d", "")):
        nums = [float(v) for v in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", sub)]
        if len(nums) < 6:
            continue
        xs, ys = nums[0::2], nums[1::2]
        n = min(len(xs), len(ys))
        a = 0.0
        for i in range(n):
            j = (i + 1) % n
            a += xs[i] * ys[j] - xs[j] * ys[i]
            perim += math.hypot(xs[j] - xs[i], ys[j] - ys[i])
        area += a / 2.0
    if perim <= 0:
        return 0.0
    return 2.0 * abs(area) / perim * _path_scale(p)


def _authored_satin_spacing(ctx: PipelineContext) -> float | None:
    """The authored satin zigzag density for a SATIN-ONLY category, converted to
    Ink-Stitch semantics, else None (Ink-Stitch default). Only satin-only production
    gets it: elsewhere the authored value would come from a different object mix and
    isn't the satin density the category actually sews. FLAT — the arb video shows
    ALL 1,618 objects selected with one auto-spacing display (0.24mm @ 90%); constant
    spacing means constant areal thread density regardless of column width. (A
    width-opening curve toward the manual-spacing median was tried and DROPPED: it
    under-stitched to 35k vs the 41-51k band.)

    SEMANTICS: Wilcom's Fills-tab "Spacing" is the advance PER NEEDLE PENETRATION
    (measured in the arb reference: 46k stitches over ~19k mm2 of 1.75mm columns =
    4.2 throws/mm = one throw each 0.24mm), while Ink-Stitch's zigzag_spacing_mm is
    PEAK-TO-PEAK — one full zig+zag cycle = TWO stitches. Passing the authored value
    straight through sews exactly double density (measured: 82k vs 46k), so it is
    doubled here."""
    if priors.satin_only(ctx.config.category):
        v = priors.authored_satin_spacing_mm(ctx.config.category)
        return 2.0 * v if v else None
    return None


def _resolved_pull_comp(ctx: PipelineContext) -> float:
    """resolved_pull_comp_mm, zeroed by the authored prior — the trio props show
    production digitizing the category with pull compensation OFF (arb: Process
    Stitches 0.00, per-object checkbox disabled) — unless the user passed
    --pull-comp-mm explicitly."""
    if (ctx.config.pull_compensation_mm is None
            and priors.authored_pull_comp_off(ctx.config.category)):
        return 0.0
    return ctx.config.resolved_pull_comp_mm


def _resolved_satin_underlay(ctx: PipelineContext) -> bool:
    """Config satin_underlay, overridden OFF by the authored underlay prior: a category
    whose trio props show the digitizer sewing satins WITHOUT the default underlay
    passes (arb: ~89% disabled) drops the center-walk/contour default. Wide vwidth
    columns keep their zigzag underlay (the authored Double-Tatami-on-Column-A analogue,
    set independently in _build_vwidth_satin)."""
    return (ctx.config.satin_underlay
            and not priors.authored_underlay_off(ctx.config.category))


def _apply_fill_params(
    root, fill_method: str = "auto_fill",
    pull_comp_mm: float = 0.2, fill_underlay: bool = True,
    satin_underlay: bool = True, satin_spacing_mm: float | None = None,
) -> None:
    """Set fill params on fills and satin params on satin columns.

    `fill_method` selects the Ink-Stitch fill algorithm; auto_fill is the default
    (and is left unset so Ink-Stitch uses its own default). contour_fill etc. are
    set explicitly — used to dodge auto_fill's pathological slowness on long thin
    sprawling regions (calligraphy). `pull_comp_mm` / `fill_underlay` tune the fixed
    thickening that over-fattens fine decoration; `satin_underlay` toggles the
    center-walk + contour underlay under satin columns. Running-stitch strokes
    already carry their params (set in the pre-pass) and are left untouched here.
    `satin_spacing_mm` is the flat authored zigzag density for a satin-only category
    (see _authored_satin_spacing), or None for Ink-Stitch's default.
    """
    fill_params = _fill_params(pull_comp_mm, fill_underlay)
    satin_params = _satin_params(pull_comp_mm, satin_underlay, satin_spacing_mm)
    # gradient blocks carry their own variable row/end spacing + angle from
    # gradient_blocks — give them underlay/pull-comp/trim but DON'T touch row spacing
    # or the fill method (auto_fill honours the per-block angle that makes the gradient).
    grad_params = {k: v for k, v in fill_params.items() if k != "row_spacing_mm"}
    for p in root.iter(f"{{{_SVG_NS}}}path"):
        if p.get(f"{{{_INKSTITCH_NS}}}satin_column"):
            for key, value in satin_params.items():
                p.set(f"{{{_INKSTITCH_NS}}}{key}", value)
        elif p.get(f"{{{_INKSTITCH_NS}}}end_row_spacing_mm") is not None:
            for key, value in grad_params.items():
                p.set(f"{{{_INKSTITCH_NS}}}{key}", value)
        elif p.get("fill") and p.get("fill") != "none" and not _is_centerline(p):
            for key, value in fill_params.items():
                p.set(f"{{{_INKSTITCH_NS}}}{key}", value)
            # Don't override a fill_method already chosen per-region (e.g. spine-fill's
            # guided_fill); only stamp the global one when the region hasn't picked one.
            if (fill_method != "auto_fill"
                    and p.get(f"{{{_INKSTITCH_NS}}}fill_method") is None):
                if fill_method == "meander_fill":
                    mm = _svg_mm_per_unit(root)
                    bw, bh = _path_bbox_units(p)
                    if mm and (min(bw, bh) * mm < _MEANDER_MIN_MM
                               or _path_mean_width_units(p) * mm
                               < _MEANDER_MIN_WIDTH_MM):
                        continue  # no room for a meander cell -> default auto_fill
                p.set(f"{{{_INKSTITCH_NS}}}fill_method", fill_method)


def _inject_params(
    src: Path, dst: Path, fill_method: str = "auto_fill",
    pull_comp_mm: float = 0.2, fill_underlay: bool = True,
    satin_underlay: bool = True, satin_spacing_mm: float | None = None,
) -> None:
    """Fill-only path: every region is a fill; set params on all of them."""
    tree = etree.parse(str(src))
    _apply_fill_params(tree.getroot(), fill_method, pull_comp_mm, fill_underlay,
                       satin_underlay, satin_spacing_mm)
    tree.write(str(dst), xml_declaration=True, encoding="UTF-8")


def _run_extension(
    binary: Path, ext: str, ids: list[str], extra: list[str],
    src: Path, dst: Path, timeout: int = _TIMEOUT_S,
) -> None:
    args = [str(binary), f"--extension={ext}"]
    args += [f"--id={i}" for i in ids]
    args += extra
    args.append(str(src))
    proc = subprocess.run(args, capture_output=True, timeout=timeout)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(
            f"{ext} failed (exit {proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace')[:500]}"
        )
    dst.write_bytes(proc.stdout)


def _read_vp3_from_zip(stdout: bytes, stderr: bytes) -> "pe.EmbPattern":
    try:
        zf = zipfile.ZipFile(io.BytesIO(stdout))
    except zipfile.BadZipFile as exc:
        raise RuntimeError(
            "Ink-Stitch did not return a valid zip. stderr: "
            f"{stderr.decode('utf-8', 'replace')[:1000]}"
        ) from exc

    vp3_names = [n for n in zf.namelist() if n.lower().endswith(".vp3")]
    if not vp3_names:
        raise RuntimeError(f"Ink-Stitch zip contained no .vp3 (got {zf.namelist()}).")

    vp3_bytes = zf.read(vp3_names[0])
    with tempfile.NamedTemporaryFile(suffix=".vp3", delete=False) as tmp:
        tmp.write(vp3_bytes)
        tmp_path = tmp.name
    try:
        return pe.read(tmp_path)
    finally:
        os.unlink(tmp_path)


_WHOLE_DIGITIZE_TIMEOUT_S = 120   # fall back to per-group if the single pass hasn't finished by now
_GROUP_DIGITIZE_TIMEOUT_S = 150   # per-group budget (each group completes in seconds normally)
_GROUP_RETRY_TIMEOUT_S = 90       # degraded retries (underlay off / fills-satins split): a hanging
                                  # group's raw fills complete in seconds, so a tighter budget does
_PREVIEW_TIMEOUT_S = 300          # realistic preview: fall back to the fast polyline draw if the
                                  # stitch_plan_preview pass hangs (same combined-routing risk).
                                  # Per group, not total: a big completed fill group re-runs its
                                  # whole stitch plan here and can legitimately need >2min (anime
                                  # portrait hair group: 130s) — only a true hang should trip it.
_ANCHOR_MARGIN_MM = 5.0           # frame anchors sit this far outside the canvas so no real stitch
                                  # (pull-comp overshoot etc.) can beat them to the bbox extremes
_ANCHOR_COLOURS = ("#010101", "#fe01fe", "#01fe01")


def _digitize(binary: Path, ready_svg: Path) -> tuple["pe.EmbPattern", list[Path] | None]:
    """Digitize the whole design in one Ink-Stitch pass. Ink-Stitch's auto_fill router can
    INFINITE-LOOP on the *combined* design even when every colour group completes fine ALONE
    (measured on joker: each colour digitizes in 2-12s, but the single all-colours pass never
    returns). So on timeout we fall back to digitizing each top-level colour group separately and
    merging the results in sew order — every region then gets proper tatami without the combined-
    routing hang. The fast path (one pass) is unchanged for designs that don't hang.

    Returns (pattern, per-group working SVGs): the SVG list is None on the fast path; on the
    per-group path it holds the file(s) each group was actually digitized from, in sew order,
    so step 6 can composite the realistic preview without re-hitting the combined hang."""
    args = [str(binary), "--extension=zip", "--format-vp3=True", str(ready_svg)]
    try:
        proc = subprocess.run(args, capture_output=True, timeout=_WHOLE_DIGITIZE_TIMEOUT_S)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Ink-Stitch failed (exit {proc.returncode}): "
                f"{proc.stderr.decode('utf-8', 'replace')[:1000]}"
            )
        return _read_vp3_from_zip(proc.stdout, proc.stderr), None
    except subprocess.TimeoutExpired:
        print(f"      whole-design digitize exceeded {_WHOLE_DIGITIZE_TIMEOUT_S}s "
              f"(auto_fill combined-routing hang) -> per-colour-group fallback", flush=True)
        return _digitize_per_group(binary, ready_svg)
    except RuntimeError as exc:
        # A hard CRASH of the combined pass (one bad region poisons the whole design,
        # e.g. meander_fill's "could not build graph" on a speck) gets the same
        # per-group fallback as a hang: the healthy colours digitize, and the failing
        # group walks the retry ladder instead of sinking the entire run.
        print(f"      whole-design digitize failed ({str(exc)[:160]}) "
              f"-> per-colour-group fallback", flush=True)
        return _digitize_per_group(binary, ready_svg)


def _colour_groups(root):
    """Top-level <g> elements that contain at least one path (each ~ one colour sew unit)."""
    out = []
    for g in root:
        if etree.QName(g).localname == "g" and next(g.iter(f"{{{_SVG_NS}}}path"), None) is not None:
            out.append(g)
    return out


def _try_digitize(binary: Path, svg_path: Path, timeout: int = _GROUP_DIGITIZE_TIMEOUT_S):
    """Digitize one SVG; return the pattern, or None on timeout/failure."""
    try:
        proc = subprocess.run(
            [str(binary), "--extension=zip", "--format-vp3=True", str(svg_path)],
            capture_output=True, timeout=timeout)
        if proc.returncode == 0:
            return _read_vp3_from_zip(proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired:
        pass
    except RuntimeError:
        # exit 0 but no valid zip (a region crashed the extension, e.g. meander's
        # "could not build graph") — a failure like any other; let the ladder degrade.
        pass
    return None


# ---- shared coordinate frame for the per-group minis ------------------------------- #
# Ink-Stitch's VP3 export centres each output on its OWN stitch bbox (verified: a mini's
# pattern always reads back exactly symmetric about the origin, while the same group inside
# the whole-design pass keeps its true off-centre position). Concatenating raw per-group
# patterns therefore shifts every group to a common centre and the merge misaligns. The fix:
# sew a tiny "frame anchor" FIRST in every mini — one manual stitch just outside each of two
# opposite canvas corners. Every mini then has identical stitch-bbox extremes, so every group
# is framed identically and absolute coords align; the anchor block is stripped after read-back.

def _anchor_corners(root) -> tuple[tuple[float, float], tuple[float, float]]:
    """Two fixed frame-defining points (user units) outside every stitchable extreme:
    the canvas (viewBox) corners inflated by _ANCHOR_MARGIN_MM."""
    vb = (root.get("viewBox") or "").split()
    x0 = y0 = 0.0
    w = h = 1000.0
    if len(vb) == 4:
        try:
            x0, y0, w, h = (float(v) for v in vb)
        except ValueError:
            pass
    m = _ANCHOR_MARGIN_MM / _mm_per_uu(root)
    return (x0 - m, y0 - m), (x0 + w + m, y0 + h + m)


def _pick_anchor_colour(root) -> str:
    """An anchor thread colour NOT already in the design: Ink-Stitch merges adjacent
    same-colour blocks (no boundary colour change), which would make the anchor strip
    eat the first real group's stitches."""
    used = set()
    for p in root.iter(f"{{{_SVG_NS}}}path"):
        for attr in (p.get("style"), p.get("fill"), p.get("stroke")):
            used.update(hx.lower() for hx in re.findall(r"#[0-9a-fA-F]{6}", attr or ""))
    for c in _ANCHOR_COLOURS:
        if c not in used:
            return c
    for r in range(256):  # design uses all candidates (bizarre) -> scan until free
        c = f"#{r:02x}0203"
        if c not in used:
            return c
    return _ANCHOR_COLOURS[0]


def _add_frame_anchor(root) -> None:
    """Insert the first-sewn frame-anchor group: a 1 mm manual-stitch segment pointing
    INWARD from each anchor corner (lock stitches retrace the segment, so nothing can poke
    past the corner extremes and change the bbox between minis)."""
    (ax0, ay0), (ax1, ay1) = _anchor_corners(root)
    eps = 1.0 / _mm_per_uu(root)
    colour = _pick_anchor_colour(root)
    g = etree.Element(f"{{{_SVG_NS}}}g", id="frame_anchor")
    for i, (x, y, s) in enumerate(((ax0, ay0, 1.0), (ax1, ay1, -1.0))):
        p = etree.SubElement(g, f"{{{_SVG_NS}}}path", id=f"frame_anchor_{i}")
        p.set("d", f"M {x:.3f},{y:.3f} L {x + s * eps:.3f},{y + s * eps:.3f}")
        p.set("style", f"fill:none;stroke:{colour};stroke-width:0.264583")
        p.set(f"{{{_INKSTITCH_NS}}}stroke_method", "manual_stitch")
    root.insert(0, g)


def _strip_anchor_block(pat: "pe.EmbPattern"):
    """Drop the leading frame-anchor colour block: its thread and every stitch through the
    first COLOR_CHANGE. Returns None if nothing but the anchor was stitched."""
    cc = pe.COLOR_CHANGE & 0xFF
    idx = next((k for k, s in enumerate(pat.stitches) if (s[2] & 0xFF) == cc), None)
    if idx is None:
        return None
    out = pe.EmbPattern()
    for th in pat.threadlist[1:]:
        out.add_thread(th)
    out.stitches = [[s[0], s[1], s[2]] for s in pat.stitches[idx + 1:]]
    if not any((s[2] & 0xFF) == (pe.STITCH & 0xFF) for s in out.stitches):
        return None
    return out


def _try_digitize_anchored(binary: Path, svg_path: Path,
                           timeout: int = _GROUP_DIGITIZE_TIMEOUT_S):
    """Digitize an anchored mini-SVG and strip its frame-anchor block; None on failure."""
    pat = _try_digitize(binary, svg_path, timeout)
    return _strip_anchor_block(pat) if pat is not None else None


# ---- degraded retries for a group that hangs even alone ---------------------------- #

def _write_fill_variant(src: Path, dst: Path, *, pull_comp0: bool = False,
                        underlay_off: bool = False) -> None:
    """Degraded variant of an anchored mini, dropping the fill params that can hang the
    auto_fill router while KEEPING tatami. Pull compensation is the measured primary
    trigger (joker's hair: hangs as-is, completes in 8s with pull-comp 0); the underlay
    pass is the secondary weight."""
    tree = etree.parse(str(src))
    for p in tree.getroot().iter(f"{{{_SVG_NS}}}path"):
        is_fill = (p.get(f"{{{_INKSTITCH_NS}}}row_spacing_mm") is not None
                   or p.get(f"{{{_INKSTITCH_NS}}}fill_underlay") is not None)
        if not is_fill:
            continue
        if pull_comp0 and p.get(f"{{{_INKSTITCH_NS}}}pull_compensation_mm") is not None:
            p.set(f"{{{_INKSTITCH_NS}}}pull_compensation_mm", "0")
        if underlay_off:
            p.set(f"{{{_INKSTITCH_NS}}}fill_underlay", "False")
    tree.write(str(dst), xml_declaration=True, encoding="UTF-8")


def _split_fills_satins(mini: Path) -> tuple[Path | None, Path | None]:
    """Write fills-only and satins/runs-only variants of an anchored mini (each keeps the
    anchor, so both halves share the frame). Returns (fills_svg, satins_svg); None where a
    half has no content, in which case there is nothing to split."""
    out: list[Path | None] = []
    for suffix, keep_linework in (("_fill", False), ("_satin", True)):
        tree = etree.parse(str(mini))
        root = tree.getroot()
        kept = 0
        for p in list(root.iter(f"{{{_SVG_NS}}}path")):
            pid = p.get("id") or ""
            if pid.startswith(("frame_anchor", "command_")):
                continue  # anchors stay in both halves; command connectors go with groups
            is_linework = (p.get(f"{{{_INKSTITCH_NS}}}satin_column") is not None
                           or p.get(f"{{{_INKSTITCH_NS}}}stroke_method") is not None)
            if is_linework != keep_linework:
                p.getparent().remove(p)
            else:
                kept += 1
        # drop entry/exit command groups whose target path was removed above (Ink-Stitch
        # must not see a connector pointing at a missing element)
        ids = {p.get("id") for p in root.iter(f"{{{_SVG_NS}}}path")}
        for cg in list(root.iter(f"{{{_SVG_NS}}}g")):
            if not (cg.get("id") or "").startswith("command_group"):
                continue
            conn = cg.find(f"{{{_SVG_NS}}}path")
            target = ((conn.get(f"{{{_INKSCAPE_NS}}}connection-end") or "").lstrip("#")
                      if conn is not None else "")
            if target not in ids:
                cg.getparent().remove(cg)
        if kept:
            dst = mini.with_name(mini.stem + suffix + ".svg")
            tree.write(str(dst), xml_declaration=True, encoding="UTF-8")
            out.append(dst)
        else:
            out.append(None)
    return out[0], out[1]


def _concat_same_colour(a, b) -> "pe.EmbPattern":
    """Rejoin the fills-only + satins-only halves of ONE colour group: one thread, one
    block, a trim between the halves (they were digitized separately, so no meaningful
    travel joins them). Either half may be None."""
    if a is None or b is None:
        return a or b
    _END, _CC = pe.END & 0xFF, pe.COLOR_CHANGE & 0xFF
    out = pe.EmbPattern()
    out.add_thread(a.threadlist[0] if a.threadlist else b.threadlist[0])
    for k, half in enumerate((a, b)):
        if k:
            out.trim()
        for s in half.stitches:
            if (s[2] & 0xFF) in (_END, _CC):
                continue
            out.stitches.append([s[0], s[1], s[2]])
    return out


def _route_group_fills_to_contour(svg_path: Path) -> None:
    """Set fill_method=contour_fill on every fill path (has row_spacing, not a satin) in an SVG —
    the LAST-resort fallback for a region whose auto_fill can't complete even in isolation.
    'Large regions = tatami' is the hard rule; contour is only reached when tatami truly can't
    finish as-is, without underlay, or with the group's fills and satins split apart."""
    tree = etree.parse(str(svg_path))
    for p in tree.getroot().iter(f"{{{_SVG_NS}}}path"):
        if (p.get(f"{{{_INKSTITCH_NS}}}row_spacing_mm") is not None
                and p.get(f"{{{_INKSTITCH_NS}}}satin_column") is None
                and p.get(f"{{{_INKSTITCH_NS}}}fill_method") is None):
            p.set(f"{{{_INKSTITCH_NS}}}fill_method", "contour_fill")
    tree.write(str(svg_path), xml_declaration=True, encoding="UTF-8")


def _route_group_meander_to_auto(svg_path: Path) -> bool:
    """Strip fill_method=meander_fill from every path in an SVG (back to Ink-Stitch's
    default auto_fill). Returns True when anything was stripped."""
    tree = etree.parse(str(svg_path))
    changed = False
    for p in tree.getroot().iter(f"{{{_SVG_NS}}}path"):
        if p.get(f"{{{_INKSTITCH_NS}}}fill_method") == "meander_fill":
            del p.attrib[f"{{{_INKSTITCH_NS}}}fill_method"]
            changed = True
    if changed:
        tree.write(str(svg_path), xml_declaration=True, encoding="UTF-8")
    return changed


def _digitize_group_with_retries(binary: Path, mini: Path,
                                 label: str) -> tuple["pe.EmbPattern | None", list[Path]]:
    """Digitize one anchored mini, degrading only as far as needed to keep tatami:
    ① as-is → ② pull-comp 0 (the measured hang trigger; underlay kept) → ③ pull-comp 0 +
    underlay off → ④ fills-only + satins-only in two passes (rejoined as one colour block)
    → ⑤ contour_fill (last resort: present + flagged, but not tatami).
    Returns (pattern, [svg files actually used]) or (None, [])."""
    pat = _try_digitize_anchored(binary, mini)
    if pat is not None:
        return pat, [mini]

    # meander_fill crashes outright on regions without room for a pattern cell (thin
    # fur slivers pass a bbox test but not the graph build) — strip the group's meander
    # routing back to plain tatami before touching pull-comp, which targets hangs.
    if _route_group_meander_to_auto(mini):
        print(f"        {label}: meander crashed -> meander regions back to tatami",
              flush=True)
        pat = _try_digitize_anchored(binary, mini, timeout=_GROUP_RETRY_TIMEOUT_S)
        if pat is not None:
            return pat, [mini]

    for tag, kw in (("pull-comp 0", {"pull_comp0": True}),
                    ("pull-comp 0 + underlay off",
                     {"pull_comp0": True, "underlay_off": True})):
        print(f"        {label}: auto_fill hung/failed alone -> retrying, {tag}",
              flush=True)
        variant = mini.with_name(mini.stem + ("_pc0.svg" if "underlay" not in tag
                                              else "_pc0nou.svg"))
        _write_fill_variant(mini, variant, **kw)
        pat = _try_digitize_anchored(binary, variant, timeout=_GROUP_RETRY_TIMEOUT_S)
        if pat is not None:
            mini.unlink(missing_ok=True)
            return pat, [variant]
        variant.unlink(missing_ok=True)

    fills_svg, satins_svg = _split_fills_satins(mini)
    if fills_svg is not None and satins_svg is not None:
        print(f"        {label}: still hung -> splitting fills / satins", flush=True)
        pat_f = _try_digitize_anchored(binary, fills_svg, timeout=_GROUP_RETRY_TIMEOUT_S)
        pat_s = _try_digitize_anchored(binary, satins_svg, timeout=_GROUP_RETRY_TIMEOUT_S)
        if pat_f is not None and pat_s is not None:
            mini.unlink(missing_ok=True)
            return _concat_same_colour(pat_f, pat_s), [fills_svg, satins_svg]
    for leftover in (fills_svg, satins_svg):
        if leftover is not None:
            leftover.unlink(missing_ok=True)

    print(f"        {label}: tatami can't complete even split -> contour_fill fallback",
          flush=True)
    _route_group_fills_to_contour(mini)
    pat = _try_digitize_anchored(binary, mini)
    if pat is not None:
        return pat, [mini]
    return None, []


def _digitize_per_group(binary: Path, ready_svg: Path) -> tuple["pe.EmbPattern", list[Path]]:
    """Digitize each top-level colour group on its own (they don't hang alone) and merge.
    Every mini carries the same frame anchor so all groups share one coordinate frame (see
    _add_frame_anchor). A group that hangs alone walks the retry ladder in
    _digitize_group_with_retries before it may fall back to contour_fill; the working
    per-group SVGs are KEPT (in sew order) for step 6's realistic-preview composite."""
    n_groups = len(_colour_groups(etree.parse(str(ready_svg)).getroot()))
    patterns: list = []
    group_svgs: list[Path] = []
    for i in range(n_groups):
        tree = etree.parse(str(ready_svg))
        groups = _colour_groups(tree.getroot())
        for j, g in enumerate(groups):            # keep only group i (defs + other siblings stay)
            if j != i:
                g.getparent().remove(g)
        _add_frame_anchor(tree.getroot())
        mini = ready_svg.with_name(f"{ready_svg.stem}_grp{i}.svg")
        tree.write(str(mini), xml_declaration=True, encoding="UTF-8")
        pat, used = _digitize_group_with_retries(binary, mini, f"group {i}")
        if pat is not None:
            patterns.append(pat)
            group_svgs.extend(used)
        else:
            print(f"        group {i}: every fallback failed — skipped", flush=True)
            mini.unlink(missing_ok=True)
    if not patterns:
        raise RuntimeError("per-group digitize produced no stitches")
    print(f"      merged {len(patterns)}/{n_groups} colour groups", flush=True)
    return _merge_patterns(patterns), group_svgs


def _merge_patterns(patterns: list) -> "pe.EmbPattern":
    """Concatenate per-group patterns into one, in order, with a colour change between groups.
    Every mini was digitized with the SAME frame anchor, so after the anchor block is stripped
    all groups share one coordinate frame and absolute stitch coords align."""
    _END = pe.END & 0xFF
    _CC = pe.COLOR_CHANGE & 0xFF
    merged = pe.EmbPattern()
    for i, gp in enumerate(patterns):
        for th in gp.threadlist:
            merged.add_thread(th)
        if i > 0:
            merged.color_change()
        for s in gp.stitches:
            cmd = s[2] & 0xFF
            if cmd in (_END, _CC):                # drop per-group END + leading colour changes
                continue
            merged.stitches.append([s[0], s[1], s[2]])
    merged.end()
    return merged


def _print_summary(pattern: "pe.EmbPattern", n_satin: int, n_run: int) -> None:
    cmds = Counter(c & 0xFF for _, _, c in pattern.stitches)
    n_stitch = cmds.get(pe.STITCH & 0xFF, 0)
    n_trim = cmds.get(pe.TRIM & 0xFF, 0)
    n_jump = cmds.get(pe.JUMP & 0xFF, 0)
    xs = [s[0] for s in pattern.stitches]
    ys = [s[1] for s in pattern.stitches]
    w = (max(xs) - min(xs)) / 10 if xs else 0  # VP3 is in 0.1mm units
    h = (max(ys) - min(ys)) / 10 if ys else 0
    print(
        f"      Ink-Stitch -> {n_stitch} stitches, {len(pattern.threadlist)} colour(s), "
        f"{n_satin} satin column(s), {n_run} run stroke(s), {n_trim} trim(s), "
        f"{n_jump} jump(s); stitched extent ~{w:.1f}x{h:.1f}mm"
    )
