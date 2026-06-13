"""Step 4 - Vector trace.

Raster -> SVG via VTracer (fed the preprocessed RGBA pixels directly; VTracer
honours alpha, so the dropped background produces no path). Then post-process:

  - group the disjoint paths VTracer emits per colour into one <g> per colour
  - recolour each group to its matched thread RGB (ctx.thread_map)
  - label each group with the catalog code/name via inkscape:label (Ink-Stitch,
    step 5, reads this) and a stable id
  - set the physical size: width/height in mm + a pixel viewBox, so the design
    is the requested real-world size while paths keep pixel coordinates

Writes the layered SVG and sets ctx.svg_path.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import vtracer
from lxml import etree

from ..color import delta_e, srgb_to_lab
from ..config import PipelineContext

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"


def run(ctx: PipelineContext) -> None:
    if ctx.preprocessed_image is None:
        raise RuntimeError("trace requires ctx.preprocessed_image; run preprocess first.")
    if not ctx.thread_map:
        raise RuntimeError("trace requires ctx.thread_map; run thread-match first.")

    img = ctx.preprocessed_image
    px_w, px_h = img.size

    # Smooth outlines for photos, crisp corners for graphics/text. Photos
    # posterise into many tiny regions, so drop bigger speckles there to keep
    # the path count (and stitch count) sane for embroidery.
    is_photo = ctx.analysis.get("kind") == "photo"
    mode = "spline" if is_photo else "polygon"
    filter_speckle = 10 if is_photo else 4

    arr = np.asarray(img)  # H x W x 4
    pixels = [tuple(p) for p in arr.reshape(-1, 4).tolist()]
    raw_svg = vtracer.convert_pixels_to_svg(
        pixels,
        size=(px_w, px_h),
        colormode="color",
        hierarchical="stacked",
        mode=mode,
        filter_speckle=filter_speckle,
        color_precision=8,
        path_precision=8,
    )

    groups = _group_paths_by_palette(raw_svg, ctx.palette)
    svg_path = ctx.config.output_dir / f"{ctx.config.name}_pro.svg"
    n_paths = _write_layered_svg(
        svg_path, groups, ctx.thread_map, ctx.analysis["size_mm"], (px_w, px_h)
    )
    ctx.svg_path = svg_path

    print(
        f"      traced ({mode}) -> {len(groups)} colour group(s), {n_paths} path(s); "
        f"{ctx.analysis['size_mm']['width_mm']}x{ctx.analysis['size_mm']['height_mm']}mm "
        f"-> {svg_path.name}"
    )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _group_paths_by_palette(
    raw_svg: str, palette: list[tuple[int, int, int]]
) -> dict[int, list[tuple[str, str | None]]]:
    """Bucket VTracer's <path>s by nearest palette index -> [(d, transform), ...]."""
    pal_lab = srgb_to_lab(np.array(palette, dtype=float))

    def nearest_idx(fill: str) -> int:
        lab = srgb_to_lab(np.array(_hex_to_rgb(fill), dtype=float))
        return int(np.argmin(delta_e(pal_lab, lab)))

    root = etree.fromstring(raw_svg.encode("utf-8"))
    groups: dict[int, list[tuple[str, str | None]]] = {}
    for path in root.findall(f"{{{SVG_NS}}}path"):
        fill = path.get("fill")
        d = path.get("d")
        if not fill or not d:
            continue
        idx = nearest_idx(fill)
        groups.setdefault(idx, []).append((d, path.get("transform")))
    return groups


def _write_layered_svg(
    svg_path: Path,
    groups: dict[int, list[tuple[str, str | None]]],
    thread_map: list[dict],
    size_mm: dict,
    size_px: tuple[int, int],
) -> int:
    px_w, px_h = size_px
    nsmap = {None: SVG_NS, "inkscape": INK_NS}
    svg = etree.Element(f"{{{SVG_NS}}}svg", nsmap=nsmap)
    svg.set("version", "1.1")
    svg.set("width", f"{size_mm['width_mm']}mm")
    svg.set("height", f"{size_mm['height_mm']}mm")
    svg.set("viewBox", f"0 0 {px_w} {px_h}")

    n_paths = 0
    # Palette order = coverage desc, so larger fills sit under smaller detail.
    # (True foreground-last stacking is step 5's job.)
    for idx in sorted(groups):
        m = thread_map[idx]
        tr, tg, tb = m["thread_rgb"]
        fill = f"#{tr:02X}{tg:02X}{tb:02X}"
        g = etree.SubElement(svg, f"{{{SVG_NS}}}g")
        g.set("id", f"color{idx}_{m['code']}")
        g.set(f"{{{INK_NS}}}label", f"{m['code']} {m['name']}".strip())
        for d, transform in groups[idx]:
            p = etree.SubElement(g, f"{{{SVG_NS}}}path")
            p.set("d", d)
            p.set("fill", fill)
            if transform:
                p.set("transform", transform)
            n_paths += 1

    tree = etree.ElementTree(svg)
    tree.write(str(svg_path), pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return n_paths
