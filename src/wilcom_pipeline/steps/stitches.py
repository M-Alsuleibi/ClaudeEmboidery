"""Step 5 - Generate stitches (Ink-Stitch headless).

Build a stitch-ready SVG, then invoke the vendored, self-contained Ink-Stitch
binary to digitize it and read the VP3 back into ctx.stitch_pattern.

Headless (no Inkscape GUI needed for export):
    inkstitch --extension=zip --format-vp3=True design.svg > out.zip

Stitch-type assignment (the goal doc's "right stitch type per region"):
  - "linework" colours (regions whose typical width is small — calligraphy,
    text, thin columns) get their *substantial* strokes converted to real satin
    columns: fill_to_stroke (centerline) -> stroke_to_satin. A region's fill is
    kept (tatami) if it has no substantial centerline (blobs, tiny fragments).
  - all remaining fills get best-practice params: fill underlay, ~0.4mm density,
    pull compensation, and trim_after (so a colour's disjoint regions aren't
    joined by long travel stitches; each trim is a Wilcom Break-Apart boundary).

True variable-width satin on freeform script is the human-refinement step; here
a single approximate width per colour is used. Anything that errors in the satin
pre-pass falls back to plain fills, so the step always produces a valid design.
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

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BIN = _REPO_ROOT / "vendor" / "inkstitch" / "bin" / "inkstitch"
_TIMEOUT_S = 300
_SATIN_TIMEOUT_S = 300

_SVG_NS = "http://www.w3.org/2000/svg"
_INKSTITCH_NS = "http://inkstitch.org/namespace"

# Best-practice fill params injected onto every fill region before digitizing.
_FILL_PARAMS = {
    "fill_underlay": "True",
    "row_spacing_mm": "0.4",
    "pull_compensation_mm": "0.2",
    "trim_after": "True",
}

# Satin columns: pull compensation + trim_after (so satins aren't joined by long
# travel stitches, same as fills).
_SATIN_PARAMS = {
    "pull_compensation_mm": "0.2",
    "trim_after": "True",
}

# Satin classification / generation tunables.
_SATIN_MAX_WIDTH_MM = 3.0   # a colour is "linework" if its median width is below this
_MIN_SATIN_PTS = 15         # a centerline needs at least this many points to satin
_MAX_SATIN_COLUMNS = 80     # guard against pathological slowness
_SATIN_MIN_W_MM = 1.0       # clamp satin width
_SATIN_MAX_W_MM = 7.0


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
    n_satin = _build_stitch_svg(ctx, binary, ready_svg)

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
    _print_summary(pattern, n_satin)


# --------------------------------------------------------------------------- #
# stitch-ready SVG (satin pre-pass + fill params)
# --------------------------------------------------------------------------- #
def _build_stitch_svg(ctx: PipelineContext, binary: Path, dst: Path) -> int:
    """Write the stitch-ready SVG; return the number of satin columns made."""
    try:
        satin_idx, widths = _satin_color_indices(ctx)
    except Exception:  # classification is best-effort
        satin_idx, widths = set(), {}

    if not satin_idx:
        _inject_params(ctx.svg_path, dst)
        return 0
    try:
        return _satin_prepass(ctx, binary, satin_idx, widths, dst)
    except Exception as exc:
        print(f"      satin pre-pass failed ({type(exc).__name__}: {exc}); using fills")
        _inject_params(ctx.svg_path, dst)
        return 0


def _satin_color_indices(ctx: PipelineContext) -> tuple[set[int], dict[int, float]]:
    """Palette indices whose regions are thin enough to satin, + a satin width
    (in SVG user-units == working px) for each."""
    img = np.asarray(ctx.preprocessed_image)
    opaque = img[..., 3] > 128
    mm_per_px = ctx.analysis["size_mm"]["width_mm"] / img.shape[1]

    satin: set[int] = set()
    widths: dict[int, float] = {}
    for i, rgb in enumerate(ctx.palette):
        mask = opaque & np.all(img[..., :3] == np.array(rgb, np.uint8), axis=-1)
        if mask.sum() < 20:
            continue
        dist = ndimage.distance_transform_edt(mask)
        ridge = (dist >= ndimage.maximum_filter(dist, size=3)) & (dist > 0)
        rv = dist[ridge]
        if rv.size == 0:
            continue
        median_width_mm = 2 * float(np.median(rv)) * mm_per_px
        if median_width_mm < _SATIN_MAX_WIDTH_MM:
            satin.add(i)
            # bias toward covering the substantial strokes (75th pct), clamped
            w_px = 2 * float(np.percentile(rv, 75))
            widths[i] = float(np.clip(w_px, _SATIN_MIN_W_MM / mm_per_px,
                                      _SATIN_MAX_W_MM / mm_per_px))
    return satin, widths


def _satin_prepass(
    ctx: PipelineContext, binary: Path, satin_idx: set[int],
    widths: dict[int, float], dst: Path,
) -> int:
    root = etree.parse(str(ctx.svg_path)).getroot()
    satin_path_ids: list[str] = []
    for g in root.iter(f"{{{_SVG_NS}}}g"):
        m = re.match(r"color(\d+)_", g.get("id") or "")
        if m and int(m.group(1)) in satin_idx:
            satin_path_ids += [p.get("id") for p in g.findall(f"{{{_SVG_NS}}}path")]
    if not satin_path_ids:
        _inject_params(ctx.svg_path, dst)
        return 0

    # Pass A: fill -> centerline strokes, keeping the original fills.
    tmp_a = dst.with_name(dst.stem + "_A.svg")
    _run_extension(binary, "fill_to_stroke", satin_path_ids,
                   ["--keep_original=True", "--threshold_mm=2"], ctx.svg_path, tmp_a)

    # thread colour per palette index (satin must keep its colour, not black)
    thread_hex = {
        i: "#{:02X}{:02X}{:02X}".format(*m["thread_rgb"])
        for i, m in enumerate(ctx.thread_map)
    }

    tree_a = etree.parse(str(tmp_a))
    root_a = tree_a.getroot()
    centerlines: dict[str, list] = {}
    originals: dict[str, object] = {}
    for p in root_a.iter(f"{{{_SVG_NS}}}path"):
        pid = p.get("id") or ""
        if _is_centerline(p) and re.match(r"c\d+_\d+_", pid):
            centerlines.setdefault(pid.rsplit("_", 1)[0], []).append(p)
        elif re.fullmatch(r"c\d+_\d+", pid):
            originals[pid] = p

    # Per original region: satin its substantial centerlines, else keep the fill.
    satin_ids: list[str] = []
    for orig, lines in centerlines.items():
        idx = int(re.match(r"c(\d+)_", orig).group(1))
        w = widths.get(idx, 4.0)
        longs = [c for c in lines if _npts(c) >= _MIN_SATIN_PTS]
        if longs:
            for c in lines:
                if c in longs:
                    _set_stroke_style(c, w, thread_hex.get(idx, "#000000"))
                    satin_ids.append(c.get("id"))
                else:
                    c.getparent().remove(c)  # drop spur fragments
            if orig in originals:
                originals[orig].getparent().remove(originals[orig])
        else:
            for c in lines:
                c.getparent().remove(c)  # keep the original fill instead

    if not satin_ids or len(satin_ids) > _MAX_SATIN_COLUMNS:
        _apply_fill_params(root_a)
        tree_a.write(str(dst), xml_declaration=True, encoding="UTF-8")
        return 0

    tree_a.write(str(tmp_a), xml_declaration=True, encoding="UTF-8")

    # Pass B: centerline strokes -> satin columns.
    tmp_b = dst.with_name(dst.stem + "_B.svg")
    _run_extension(binary, "stroke_to_satin", satin_ids, [], tmp_a, tmp_b,
                   timeout=_SATIN_TIMEOUT_S)

    tree_b = etree.parse(str(tmp_b))
    _regroup_satins_by_colour(tree_b.getroot(), thread_hex)
    _apply_fill_params(tree_b.getroot())
    tree_b.write(str(dst), xml_declaration=True, encoding="UTF-8")
    return len(satin_ids)


def _regroup_satins_by_colour(root, thread_hex: dict[int, str]) -> None:
    """Move every satin column into its colour's <g> (by stroke colour) so each
    colour stays one contiguous block, then drop the empty wrapper groups
    stroke_to_satin created."""
    groups = {}
    for g in root.iter(f"{{{_SVG_NS}}}g"):
        m = re.match(r"color(\d+)_", g.get("id") or "")
        if m:
            groups[int(m.group(1))] = g
    hex_to_idx = {v.lower(): k for k, v in thread_hex.items()}

    for p in list(root.iter(f"{{{_SVG_NS}}}path")):
        if not p.get(f"{{{_INKSTITCH_NS}}}satin_column"):
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
# small helpers
# --------------------------------------------------------------------------- #
def _is_centerline(p) -> bool:
    return "fill:none" in (p.get("style") or "") or p.get("fill") == "none"


def _npts(p) -> int:
    return len(re.findall(r"-?\d+\.?\d*[, ]-?\d+\.?\d*", p.get("d") or ""))


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


def _apply_fill_params(root) -> None:
    """Set fill params on fills and satin params on satin columns."""
    for p in root.iter(f"{{{_SVG_NS}}}path"):
        if p.get(f"{{{_INKSTITCH_NS}}}satin_column"):
            for key, value in _SATIN_PARAMS.items():
                p.set(f"{{{_INKSTITCH_NS}}}{key}", value)
        elif p.get("fill") and p.get("fill") != "none" and not _is_centerline(p):
            for key, value in _FILL_PARAMS.items():
                p.set(f"{{{_INKSTITCH_NS}}}{key}", value)


def _inject_params(src: Path, dst: Path) -> None:
    """Fill-only path: every region is a fill; set params on all of them."""
    tree = etree.parse(str(src))
    _apply_fill_params(tree.getroot())
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


def _print_summary(pattern: "pe.EmbPattern", n_satin: int) -> None:
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
        f"{n_satin} satin column(s), {n_trim} trim(s), {n_jump} jump(s); "
        f"stitched extent ~{w:.1f}x{h:.1f}mm"
    )
