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
"""

from __future__ import annotations

import io
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
from ..fingerprint import category_satin_dominant

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


def _satin_params(pull_comp_mm: float, satin_underlay: bool) -> dict[str, str]:
    # Satins get pull-comp + trim_after (so they aren't joined by long travels).
    # Underlay is the "always underlay your satins" rule: a center-walk run down
    # the spine + a contour run inset from each long edge stabilise the column so
    # its edges don't tunnel or pucker. Ink-Stitch's own defaults size the insets/
    # stitch-length; we just switch the two passes on.
    params = {"pull_compensation_mm": f"{pull_comp_mm:g}", "trim_after": "True"}
    if satin_underlay:
        params["center_walk_underlay"] = "True"
        params["contour_underlay"] = "True"
    return params


# Running / bean stitch for sub-satin linework (§0a: "line < ~1.6 mm ->
# run/triple-run"). A thin keyline is stitched *along* its centerline, not
# fattened into a too-narrow satin. bean_stitch_repeats=1 -> a triple (bean) pass
# so the line reads solid; a single running stitch can look sparse on a curve.
_RUN_STITCH_LEN_MM = 2.0
_RUN_BEAN_REPEATS = "1"


def _run_params() -> dict[str, str]:
    return {
        "stroke_method": "running_stitch",
        "running_stitch_length_mm": f"{_RUN_STITCH_LEN_MM:g}",
        "bean_stitch_repeats": _RUN_BEAN_REPEATS,
        "trim_after": "True",
    }

# Satin classification / generation tunables.
_SATIN_MAX_WIDTH_MM = 3.0   # a colour is "linework" if its typical width is below this
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
    if ctx.svg_path is None:
        raise RuntimeError("stitches requires ctx.svg_path; run trace first.")

    binary = _locate_binary()
    ready_svg = ctx.config.output_dir / f"{ctx.config.name}_inkstitch.svg"
    n_satin, n_run = _build_stitch_svg(ctx, binary, ready_svg)

    if ctx.config.auto_route and (n_satin or n_run):
        _auto_route(ctx, binary, ready_svg)

    # keep the stitch-ready SVG for step 6's realistic preview render
    ctx.stitch_svg_path = ready_svg

    proc = subprocess.run(
        [str(binary), "--extension=zip", "--format-vp3=True", str(ready_svg)],
        capture_output=True,
        timeout=_TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Ink-Stitch failed (exit {proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace')[:1000]}"
        )

    pattern = _read_vp3_from_zip(proc.stdout, proc.stderr)
    ctx.stitch_pattern = pattern
    _print_summary(pattern, n_satin, n_run)


def render_realistic_preview(ctx: PipelineContext, svg: Path, dst: Path) -> bool:
    """Render a realistic thread preview of the stitch-ready SVG.

    Ink-Stitch's `stitch_plan_preview` (render-mode realistic-vector) draws the
    stitches as shaded *vector* threads into the SVG (design layer hidden); cairosvg
    then rasterizes that to PNG — no Inkscape needed (the `png_realistic` output
    extension shells out to the `inkscape` binary, which we deliberately don't have).
    Best-effort: returns False on any failure so step 6 falls back to the fast
    polyline preview.
    """
    try:
        binary = _locate_binary()
        import cairosvg  # optional dependency; lazy import
    except Exception:
        return False

    tmp = dst.with_name(dst.stem + "_splan.svg")
    try:
        proc = subprocess.run(
            [str(binary), "--extension=stitch_plan_preview",
             "--render-mode=realistic-vector", "--layer-visibility=hidden",
             "--move-to-side=false", "--overwrite=true", "--render-jumps=false",
             str(svg)],
            capture_output=True, timeout=_TIMEOUT_S,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return False
        tmp.write_bytes(proc.stdout)

        sz = ctx.analysis.get("size_mm", {}) if ctx.analysis else {}
        w_mm = float(sz.get("width_mm", 1) or 1)
        h_mm = float(sz.get("height_mm", 1) or 1)
        if w_mm >= h_mm:
            cairosvg.svg2png(url=str(tmp), write_to=str(dst),
                             output_width=_REALISTIC_PREVIEW_PX, background_color="white")
        else:
            cairosvg.svg2png(url=str(tmp), write_to=str(dst),
                             output_height=_REALISTIC_PREVIEW_PX, background_color="white")
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

    pc, ul = ctx.config.pull_compensation_mm, ctx.config.fill_underlay
    su = ctx.config.satin_underlay
    if not line_idx:
        _inject_params(src_svg, dst, ctx.config.fill_method, pc, ul, su)
        return 0, 0
    try:
        return _linework_prepass(ctx, binary, line_idx, dst, src_svg)
    except Exception as exc:
        print(f"      linework pre-pass failed ({type(exc).__name__}: {exc}); using fills")
        _inject_params(src_svg, dst, ctx.config.fill_method, pc, ul, su)
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
    satin_lean = (ctx.config.satin_lean and category_satin_dominant(ctx.config.category)
                  and not lettering)
    width_ceiling = (_LETTERING_SATIN_MAX_WIDTH_MM if (lettering or satin_lean)
                     else _SATIN_MAX_WIDTH_MM)

    line: set[int] = set()
    for i, rgb in enumerate(ctx.palette):
        mask = opaque & np.all(img[..., :3] == np.array(rgb, np.uint8), axis=-1)
        if mask.sum() < 20:
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
    pc, ul = ctx.config.pull_compensation_mm, ctx.config.fill_underlay
    su = ctx.config.satin_underlay
    src_svg = src_svg or ctx.svg_path
    root = etree.parse(str(src_svg)).getroot()
    line_path_ids: list[str] = []
    for g in root.iter(f"{{{_SVG_NS}}}g"):
        m = re.match(r"color(\d+)_", g.get("id") or "")
        if m and int(m.group(1)) in line_idx:
            line_path_ids += [p.get("id") for p in g.findall(f"{{{_SVG_NS}}}path")]
    if not line_path_ids:
        _inject_params(src_svg, dst, ctx.config.fill_method, pc, ul, su)
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
    satin_lean = (ctx.config.satin_lean and category_satin_dominant(ctx.config.category)
                  and not lettering)
    run_enabled = ctx.config.thin_line_run and not lettering
    branch_satin = (ctx.config.branch_satin or satin_lean) and not lettering
    min_pts = _LETTERING_MIN_SATIN_PTS if lettering else _MIN_SATIN_PTS
    width_ceiling = (_LETTERING_SATIN_MAX_WIDTH_MM if (lettering or satin_lean)
                     else _SATIN_MAX_WIDTH_MM)
    satin_max_mm = _LETTERING_SATIN_MAX_W_MM if (lettering or satin_lean) else _SATIN_MAX_W_MM
    run_strokes: list[tuple[object, int]] = []          # (centerline, colour idx)
    satin_cands: list[tuple[object, int, float]] = []   # (centerline, colour idx, width mm)
    drop_centerlines: list[object] = []
    drop_originals: set[str] = set()
    for orig, lines in centerlines.items():
        idx = int(re.match(r"c(\d+)_", orig).group(1))
        longs = [c for c in lines if _npts(c) >= min_pts]
        if not longs:
            drop_centerlines += lines  # no real centerline (blob/scrap) -> keep as fill
            continue
        # width = region area / FULL skeleton length (all centerlines, incl. spurs);
        # dividing by only the long ones over-estimates a branchy thin region's width.
        w_mm = _block_width_mm(originals.get(orig), lines, mm_per_uu)

        if lettering:
            satin_cands += [(c, idx, w_mm) for c in longs]
            drop_centerlines += [c for c in lines if c not in longs]
            drop_originals.add(orig)
        elif run_enabled and 0 < w_mm < _RUN_MAX_WIDTH_MM:
            run_strokes += [(c, idx) for c in longs]
            drop_centerlines += [c for c in lines if c not in longs]
            drop_originals.add(orig)
        elif 0 < w_mm < width_ceiling:
            # Satin band. A single clean column always satins. A forked/branchy STROKE
            # region — a few long centerlines that are most of the skeleton (so satining
            # them leaves few gaps) — dissects into one satin per branch when --branch-satin
            # is on (generalising lettering's glyph dissection to organic strokes: a letter
            # ر, a forked ornament limb). Otherwise it stays ONE continuous fill.
            if len(longs) == 1 and len(lines) <= _MAX_SPURS_FOR_SATIN:
                keep = longs[:1]
            elif (branch_satin and 2 <= len(longs) <= _MAX_BRANCH_SATINS
                  and _long_frac(longs, lines) >= _BRANCH_COVER_MIN):
                keep = longs
            else:
                keep = []
            if keep:
                satin_cands += [(c, idx, w_mm) for c in keep]
                drop_centerlines += [c for c in lines if c not in keep]
                drop_originals.add(orig)
            else:
                drop_centerlines += lines  # not stroke-like / too meshy -> one fill
        else:
            drop_centerlines += lines  # broad -> one continuous fill

    # Satin-overflow guard (pathological stroke_to_satin slowness): demote the
    # satin candidates back to fills but keep the runs.
    max_columns = _LETTERING_MAX_SATIN_COLUMNS if lettering else _MAX_SATIN_COLUMNS
    if len(satin_cands) > max_columns:
        for c, _idx, _w in satin_cands:
            drop_centerlines.append(c)
            drop_originals.discard(c.get("id").rsplit("_", 1)[0])
        satin_cands = []
    if len(run_strokes) > _MAX_RUN_STROKES:
        _inject_params(ctx.svg_path, dst, ctx.config.fill_method, pc, ul, su)
        return 0, 0

    # Apply the decisions to the tree — each satin at its own region width.
    for c, idx in run_strokes:
        _set_run_style(c, thread_hex.get(idx, "#000000"))
    for c, idx, w_mm in satin_cands:
        w_uu = float(np.clip(w_mm, _SATIN_MIN_W_MM, satin_max_mm)) / mm_per_uu
        _set_stroke_style(c, w_uu, thread_hex.get(idx, "#000000"))
    for c in drop_centerlines:
        if c.getparent() is not None:
            c.getparent().remove(c)
    for orig in drop_originals:
        if orig in originals and originals[orig].getparent() is not None:
            originals[orig].getparent().remove(originals[orig])

    n_run = len(run_strokes)
    satin_ids = [c.get("id") for c, _idx, _w in satin_cands]

    if not satin_ids:
        # runs only (or nothing) -> finalize without a stroke_to_satin pass.
        _regroup_linework_by_colour(root_a, thread_hex)
        _apply_fill_params(root_a, ctx.config.fill_method, pc, ul, su)
        tree_a.write(str(dst), xml_declaration=True, encoding="UTF-8")
        return 0, n_run

    tree_a.write(str(tmp_a), xml_declaration=True, encoding="UTF-8")

    # Pass B: centerline strokes -> satin columns (runs pass through untouched).
    tmp_b = dst.with_name(dst.stem + "_B.svg")
    _run_extension(binary, "stroke_to_satin", satin_ids, [], tmp_a, tmp_b,
                   timeout=_SATIN_TIMEOUT_S)

    tree_b = etree.parse(str(tmp_b))
    _regroup_linework_by_colour(tree_b.getroot(), thread_hex)
    _apply_fill_params(tree_b.getroot(), ctx.config.fill_method, pc, ul, su)
    tree_b.write(str(dst), xml_declaration=True, encoding="UTF-8")
    return len(satin_ids), n_run


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


def _apply_fill_params(
    root, fill_method: str = "auto_fill",
    pull_comp_mm: float = 0.2, fill_underlay: bool = True,
    satin_underlay: bool = True,
) -> None:
    """Set fill params on fills and satin params on satin columns.

    `fill_method` selects the Ink-Stitch fill algorithm; auto_fill is the default
    (and is left unset so Ink-Stitch uses its own default). contour_fill etc. are
    set explicitly — used to dodge auto_fill's pathological slowness on long thin
    sprawling regions (calligraphy). `pull_comp_mm` / `fill_underlay` tune the fixed
    thickening that over-fattens fine decoration; `satin_underlay` toggles the
    center-walk + contour underlay under satin columns. Running-stitch strokes
    already carry their params (set in the pre-pass) and are left untouched here.
    """
    fill_params = _fill_params(pull_comp_mm, fill_underlay)
    satin_params = _satin_params(pull_comp_mm, satin_underlay)
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
            if fill_method != "auto_fill":
                p.set(f"{{{_INKSTITCH_NS}}}fill_method", fill_method)


def _inject_params(
    src: Path, dst: Path, fill_method: str = "auto_fill",
    pull_comp_mm: float = 0.2, fill_underlay: bool = True,
    satin_underlay: bool = True,
) -> None:
    """Fill-only path: every region is a fill; set params on all of them."""
    tree = etree.parse(str(src))
    _apply_fill_params(tree.getroot(), fill_method, pull_comp_mm, fill_underlay,
                       satin_underlay)
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
