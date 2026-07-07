"""Step 6 - Emit the three artifacts.

  NAME_pro.vp3            -> the Phase B AHK script's only input (carries the
                            matched thread RGBs + catalog codes).
  NAME_pro_preview.png    -> the self-verify gate (step 7) + a human visual check.
  NAME_pro_threadlist.txt -> thread assignment in ES + the machine operator's
                            sheet (threads, catalog #s, sew order).

Consumes ctx.stitch_pattern (pyembroidery) + ctx.thread_map.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pyembroidery as pe
from PIL import Image, ImageDraw

from ..config import PipelineConfig, PipelineContext
from . import stitches

# command codes, masked the same way pyembroidery stores them in the stitch list
_STITCH = pe.STITCH & 0xFF
_JUMP = pe.JUMP & 0xFF
_TRIM = pe.TRIM & 0xFF
_COLOR_CHANGE = pe.COLOR_CHANGE & 0xFF

_PREVIEW_MAX_PX = 800
_MARGIN_PX = 12


def run(ctx: PipelineContext) -> None:
    cfg = ctx.config
    if ctx.stitch_pattern is None:
        raise RuntimeError("emit requires ctx.stitch_pattern; run stitches first.")
    pattern = ctx.stitch_pattern

    _stamp_thread_metadata(pattern, ctx.thread_map)
    pe.write_vp3(pattern, str(cfg.vp3_path))
    # Realistic thread preview (Ink-Stitch render, no Inkscape) when enabled and the
    # stitch-ready SVG is available; else the fast polyline draw. render_realistic_preview
    # is best-effort and returns False on any failure, so we always get a preview.
    realistic = (
        cfg.realistic_preview
        and ctx.stitch_svg_path is not None
        and stitches.render_realistic_preview(ctx, ctx.stitch_svg_path, cfg.preview_path)
    )
    if not realistic:
        _render_preview(pattern, cfg.preview_path)
    _write_threadlist(pattern, ctx.thread_map, cfg)

    print(
        f"      wrote {cfg.vp3_path.name}, {cfg.preview_path.name} "
        f"({'realistic' if realistic else 'polyline'}), {cfg.threadlist_path.name}"
    )


# --------------------------------------------------------------------------- #
# thread metadata (carried into the VP3 itself)
# --------------------------------------------------------------------------- #
def _stamp_thread_metadata(pattern: "pe.EmbPattern", thread_map: list[dict]) -> None:
    """Stamp the matched cone code/name/chart onto each VP3 thread.

    Real production VP3s (the letters/ references) carry per-thread catalog_number
    + description + brand, so Wilcom/Hatch and the operator see a named cone, not a
    bare RGB. pyembroidery's VP3 writer preserves these three string fields, and a
    read→write→read round-trip keeps them intact. Ink-Stitch leaves them unset, so
    we fill them here from step-3's thread_map, matching threads to records by RGB.
    """
    if not thread_map:
        return
    by_rgb = {tuple(m["thread_rgb"]): m for m in thread_map}
    for t in pattern.threadlist:
        rgb = (t.get_red(), t.get_green(), t.get_blue())
        m = by_rgb.get(rgb) or _nearest(rgb, thread_map)
        if not m:
            continue
        # description = human colour name; catalog_number = cone code; brand = chart.
        t.description = m["name"]
        t.catalog_number = str(m["code"])
        t.brand = m["catalog"]
        t.chart = m["catalog"]


def _nearest(rgb: tuple[int, int, int], thread_map: list[dict]) -> dict | None:
    """Fallback when a VP3 thread's RGB isn't an exact thread_map key (e.g.
    Ink-Stitch nudged a colour): pick the record with the closest cone RGB."""
    best, best_d = None, None
    for m in thread_map:
        tr = m["thread_rgb"]
        d = sum((a - b) ** 2 for a, b in zip(rgb, tr))
        if best_d is None or d < best_d:
            best, best_d = m, d
    return best


# --------------------------------------------------------------------------- #
# preview
# --------------------------------------------------------------------------- #
def _thread_rgb(pattern: "pe.EmbPattern", block_idx: int) -> tuple[int, int, int]:
    threads = pattern.threadlist
    if not threads:
        return (0, 0, 0)
    t = threads[min(block_idx, len(threads) - 1)]
    return (t.get_red(), t.get_green(), t.get_blue())


def _render_preview(pattern: "pe.EmbPattern", path: Path) -> None:
    """Draw the stitch path as coloured polylines per colour block, on white."""
    stitches = pattern.stitches
    if not stitches:
        Image.new("RGB", (64, 64), "white").save(path)
        return

    xs = [s[0] for s in stitches]
    ys = [s[1] for s in stitches]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w_u, h_u = max(1, maxx - minx), max(1, maxy - miny)
    scale = _PREVIEW_MAX_PX / max(w_u, h_u)

    W = int(w_u * scale) + 2 * _MARGIN_PX
    H = int(h_u * scale) + 2 * _MARGIN_PX
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Pen ~0.3mm. A physical thread is ~0.4mm, but drawing every stitch that wide
    # overshoots each stroke edge by half the pen (~0.2mm/side) and lets stitch ends
    # poke out as fuzz, so the preview reads noticeably fatter than the true fill
    # geometry (and the source art). 0.3mm keeps solid fills covered while making the
    # drawn stroke width track the actual sewn width more honestly.
    line_w = max(1, round(scale * 3))  # ~0.3mm thread (honest stroke width)

    last: tuple[float, float] | None = None
    block = 0
    for x, y, cmd in stitches:
        c = cmd & 0xFF
        px = _MARGIN_PX + (x - minx) * scale
        # pyembroidery reads VP3 into Y-down coords (design top == min Y), so map
        # Y straight to screen rows. (The earlier `maxy - y` double-flipped and
        # rendered every preview upside-down — the VP3 itself is upright.)
        py = _MARGIN_PX + (y - miny) * scale
        if c == _STITCH:
            if last is not None:
                draw.line([last, (px, py)], fill=_thread_rgb(pattern, block), width=line_w)
            last = (px, py)
        else:
            if c == _COLOR_CHANGE:
                block += 1
            last = None  # pen up across jumps / trims / colour changes

    img.save(path)


# --------------------------------------------------------------------------- #
# threadlist
# --------------------------------------------------------------------------- #
def _write_threadlist(
    pattern: "pe.EmbPattern", thread_map: list[dict], cfg: PipelineConfig
) -> None:
    by_rgb = {}
    for m in thread_map:
        by_rgb.setdefault(tuple(m["thread_rgb"]), m)

    cmds = Counter(c & 0xFF for _, _, c in pattern.stitches)
    catalog = thread_map[0]["catalog"] if thread_map else "?"

    lines = [
        f"# {cfg.name} — thread list (sew order)",
        f"# catalog: {catalog}",
        "#",
        "#  Stop  Code      RGB                Thread name",
    ]
    for i, t in enumerate(pattern.threadlist, start=1):
        rgb = (t.get_red(), t.get_green(), t.get_blue())
        m = by_rgb.get(rgb)
        code = m["code"] if m else (t.catalog_number or "?")
        name = m["name"] if m else (t.description or "")
        lines.append(f"  {i:>4}  {code:<8}  {str(rgb):<17}  {name}")

    lines += [
        "#",
        f"# total stitches: {cmds.get(_STITCH, 0)} | colours: {len(pattern.threadlist)} "
        f"| trims: {cmds.get(_TRIM, 0)} | jumps: {cmds.get(_JUMP, 0)}",
    ]
    cfg.threadlist_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
