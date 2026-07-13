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

import re
from pathlib import Path

import numpy as np
import vtracer
from lxml import etree
from scipy import ndimage

from ..color import delta_e, srgb_to_lab
from ..config import KEYLINE_DETAIL_RGB, PipelineContext

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"
INKSTITCH_NS = "http://inkstitch.org/namespace"
# Stamp emitted SVGs as the current Ink/Stitch SVG version so opening them in
# Inkscape doesn't trigger the "Unversioned Ink/Stitch SVG file detected"
# upgrade prompt. Matches INKSTITCH_SVG_VERSION in the bundled Ink/Stitch 3.2.2
# (the newest bundled designs carry version 3). Metadata only — no effect on
# geometry, threads, or the digitized output.
INKSTITCH_SVG_VERSION = "3"

# Foreground-last sequencing tunables.
_RING_PX = 6          # how far out to sample the ring around a colour's regions
_ENCLOSE_FRAC = 0.5   # ring must be >=this fraction one colour to count as "under" it

# Gradient shade-cluster tunables (--gradient). Two palette colours are linked into a
# shade cluster when they are the SAME hue (Lab a,b close), DIFFERENT lightness, and
# spatially ADJACENT; connected components with >=2 members become a smooth gradient.
_GRAD_MIN_AREA_PX = 60    # ignore tiny colours when clustering
_GRAD_HUE_TOL = 16.0      # max Lab (a,b) distance to count as the same hue
_GRAD_L_MIN = 6.0         # lightness must differ by at least this (a real shade)
_GRAD_L_MAX = 65.0        # ...but not black<->white
_GRAD_ADJ_PX = 3          # dilation radius (px) for the adjacency test
_GRAD_BORDER_MIN = 40     # min shared-border pixels to link two colours
_GRAD_CONTIG_FRAC = 0.75  # the cluster's union must be mostly ONE blob (largest connected
                          # component >= this fraction) — a single gradient axis streaks
                          # across separated regions (same-hue colours scattered over art)


def run(ctx: PipelineContext) -> None:
    if ctx.preprocessed_image is None:
        raise RuntimeError("trace requires ctx.preprocessed_image; run preprocess first.")
    if not ctx.thread_map:
        raise RuntimeError("trace requires ctx.thread_map; run thread-match first.")

    # Cross-stitch categories build their stitches directly from the quantized image
    # (steps/crossstitch.py) and never read the traced SVG — and vtracer on a counted-grid
    # mock-up (thousands of AA speck regions) allocates unboundedly (measured: OOM-killed
    # at ~5GB on a 400mm falahi panel). Skip the whole trace.
    if ctx.config.resolved_cross_stitch:
        print("      cross-stitch category: skipping trace "
              "(stitches are built directly from the quantized grid)")
        return

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
        # cutout (not stacked): each colour becomes exactly its own region. stacked
        # makes each lower layer a cumulative blob (its region + everything meant to
        # paint on top), which is WRONG once we re-order layers by sew depth below —
        # a big background blob then paints over the foreground (a tan body over green).
        hierarchical="cutout",
        mode=mode,
        filter_speckle=filter_speckle,
        color_precision=8,
        path_precision=8,
    )

    groups = _group_paths_by_palette(raw_svg, ctx.palette)
    order = _sew_order(img, ctx.palette)  # background first, foreground last
    clusters = _shade_clusters(img, ctx.palette) if ctx.config.gradient else []

    # Underlap (--underlap-mm): production objects OVERLAP — an earlier-sewn colour extends
    # UNDER its later-sewn neighbours so fabric pull can't open a white gap at the seam.
    # vtracer's single cutout pass can't express overlap (each pixel belongs to one path),
    # so each colour that borders a later-sewn colour is RE-traced alone from its dilated
    # mask (expansion clipped to later-sewn pixels — never background, never the dropped
    # counter holes, which are transparent and in no colour's mask) and replaces its paths.
    # The later colour keeps its full shape and covers the seam. 0 = exact old behaviour.
    # Distinct from pull-comp (step 5): pull-comp widens STITCHES uniformly; underlap moves
    # the traced GEOMETRY, only along seams, only under later colours.
    if ctx.config.underlap_mm > 0:
        px_per_mm = px_w / ctx.analysis["size_mm"]["width_mm"]
        r_px = int(round(ctx.config.underlap_mm * px_per_mm))
        grad_members = {i for cl in clusters for i in cl["members"]}
        if r_px >= 1:
            masks = _palette_masks(img, ctx.palette)
            expanded = _underlap_masks(masks, order, r_px)
            n_under = 0
            for i, mask in expanded.items():
                if i in grad_members:      # gradient clusters build their own union path
                    continue
                traced = _trace_single_colour(mask, ctx.palette[i], (px_w, px_h),
                                              mode, filter_speckle)
                if traced:
                    groups[i] = traced
                    n_under += 1
            if n_under:
                print(f"      underlap -> {n_under} colour(s) extended "
                      f"{ctx.config.underlap_mm:g}mm under later-sewn neighbours")

    # The keyline-detail layer sews LAST, so the underlap loop above never re-traces
    # it (no later-sewn neighbour). But the whole-image cutout pass culls its thinnest
    # strokes — vtracer drops 1-2 px linework when clustering all colours together,
    # while the same stroke traced alone survives — so always re-trace it from its
    # own mask, the isolated trace every other colour already gets via underlap.
    detail_idx = next(
        (i for i, c in enumerate(ctx.palette) if tuple(c) == KEYLINE_DETAIL_RGB), None
    )
    if detail_idx is not None:
        arr4 = np.asarray(img)
        kmask = (arr4[..., 3] >= 128) & np.all(
            arr4[..., :3] == np.array(KEYLINE_DETAIL_RGB, np.uint8), axis=-1
        )
        traced = _trace_single_colour(
            kmask, ctx.palette[detail_idx], (px_w, px_h), mode, filter_speckle
        )
        if traced:
            groups[detail_idx] = traced

    svg_path = ctx.config.output_dir / f"{ctx.config.name}_pro.svg"
    n_paths = _write_layered_svg(
        svg_path, groups, order, ctx.thread_map, ctx.analysis["size_mm"], (px_w, px_h),
        clusters,
    )
    ctx.svg_path = svg_path

    grad_note = (
        f", {len(clusters)} gradient cluster(s) [" +
        "; ".join("+".join(str(i) for i in c["members"]) for c in clusters) + "]"
        if clusters else ""
    )
    print(
        f"      traced ({mode}) -> {len(groups)} colour group(s), {n_paths} path(s)"
        f"{grad_note}; "
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


def _palette_masks(img, palette: list[tuple[int, int, int]]) -> list[np.ndarray]:
    """One boolean mask per palette colour (opaque pixels only — the dropped background
    and any opened counter holes are transparent, so they belong to NO colour's mask)."""
    arr = np.asarray(img)
    opaque = arr[..., 3] > 128
    rgb = arr[..., :3]
    return [opaque & np.all(rgb == np.asarray(c, np.uint8), axis=-1) for c in palette]


def _underlap_masks(masks: list[np.ndarray], order: list[int],
                    r_px: int) -> dict[int, np.ndarray]:
    """Expand each colour's mask by r_px, but ONLY into pixels owned by colours sewn
    LATER (walk the sew order backwards accumulating the later-sewn union). The earlier
    colour gains the overlap; the later colour is untouched and covers the seam.
    Background / transparent pixels (incl. opened counters) are in no mask, so they are
    never claimed. Returns {palette idx: expanded mask} only for colours that gained."""
    if r_px < 1:  # guard: scipy treats iterations<1 as "repeat until convergence"
        return {}
    out: dict[int, np.ndarray] = {}
    later = np.zeros_like(masks[0])
    for pos in range(len(order) - 1, -1, -1):
        i = order[pos]
        m = masks[i]
        if m.any() and later.any():
            grow = ndimage.binary_dilation(m, iterations=r_px) & later
            if grow.any():
                out[i] = m | grow
        later = later | m
    return out


def _trace_single_colour(mask: np.ndarray, rgb: tuple[int, int, int],
                         size_px: tuple[int, int], mode: str,
                         filter_speckle: int) -> list[tuple[str, str | None]]:
    """vtracer one colour's (expanded) mask alone — colour on transparent, same tracing
    params as the main pass — and return its [(d, transform), ...] path list."""
    h, w = mask.shape
    canvas = np.zeros((h, w, 4), np.uint8)
    canvas[mask] = (*rgb, 255)
    pixels = [tuple(p) for p in canvas.reshape(-1, 4).tolist()]
    raw = vtracer.convert_pixels_to_svg(
        pixels, size=size_px, colormode="color", hierarchical="cutout", mode=mode,
        filter_speckle=filter_speckle, color_precision=8, path_precision=8,
    )
    root = etree.fromstring(raw.encode("utf-8"))
    out = []
    for path in root.findall(f"{{{SVG_NS}}}path"):
        d = path.get("d")
        fill = path.get("fill")
        if d and fill and fill != "none":
            out.append((d, path.get("transform")))
    return out


def _sew_order(img, palette: list[tuple[int, int, int]]) -> list[int]:
    """Order palette indices background-first, foreground-last.

    A colour is "foreground" of another if it's enclosed by it: if the ring of
    pixels just outside a colour's regions is dominated by another colour, this
    colour sits on top and must sew later. Depth = how many enclosures deep; sew
    by depth ascending, larger area first as a tiebreak.
    """
    n = len(palette)
    masks = _palette_masks(img, palette)
    areas = [int(m.sum()) for m in masks]

    surround: list[int | None] = [None] * n
    for i in range(n):
        if areas[i] == 0:
            continue
        ring = ndimage.binary_dilation(masks[i], iterations=_RING_PX) & ~masks[i]
        ring_total = int(ring.sum())
        if ring_total == 0:
            continue
        best_cnt, best_j = max(
            ((int((ring & masks[j]).sum()), j) for j in range(n) if j != i),
            default=(0, -1),
        )
        if best_cnt / ring_total >= _ENCLOSE_FRAC:
            surround[i] = best_j

    def depth(i: int) -> int:
        seen, d = set(), 0
        while surround[i] is not None and i not in seen:
            seen.add(i)
            i = surround[i]
            d += 1
        return d

    # The keyline-detail layer (thin black linework split off by preprocess) always
    # sews last: it decorates the fills beneath it (mouth on a skin fill), and its
    # aggregate enclosure ring is too mixed for the depth heuristic to place it.
    return sorted(
        range(n),
        key=lambda i: (tuple(palette[i]) == KEYLINE_DETAIL_RGB, depth(i), -areas[i]),
    )


def _shade_clusters(img, palette: list[tuple[int, int, int]]) -> list[dict]:
    """Group palette indices into shade clusters for gradient stitching.

    Two colours link when they are the SAME hue (Lab a,b close), a DIFFERENT lightness
    (a real shade, not black<->white), and spatially ADJACENT (a real shared border).
    Connected components of that graph with >=2 members become a gradient. Returns, per
    cluster: {members: [idx...] light->dark, dir: (x1,y1,x2,y2), stops: [(offset, idx)...]}
    in viewBox (working-pixel) coordinates.
    """
    n = len(palette)
    masks = _palette_masks(img, palette)
    areas = [int(m.sum()) for m in masks]
    labs = srgb_to_lab(np.array(palette, dtype=float))  # (n,3): L, a, b

    link = [[False] * n for _ in range(n)]
    for i in range(n):
        if areas[i] < _GRAD_MIN_AREA_PX:
            continue
        di = ndimage.binary_dilation(masks[i], iterations=_GRAD_ADJ_PX)
        for j in range(i + 1, n):
            if areas[j] < _GRAD_MIN_AREA_PX:
                continue
            dab = float(np.hypot(labs[i][1] - labs[j][1], labs[i][2] - labs[j][2]))
            dL = abs(float(labs[i][0] - labs[j][0]))
            if dab > _GRAD_HUE_TOL or dL < _GRAD_L_MIN or dL > _GRAD_L_MAX:
                continue
            if int((di & masks[j]).sum()) >= _GRAD_BORDER_MIN:
                link[i][j] = link[j][i] = True

    seen: set[int] = set()
    out: list[dict] = []
    for start in range(n):
        if start in seen or areas[start] < _GRAD_MIN_AREA_PX:
            continue
        stack, comp = [start], []
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            comp.append(k)
            stack += [j for j in range(n) if link[k][j] and j not in seen]
        if len(comp) < 2:
            continue
        # spatial contiguity: the merged region must be mostly one blob, else a single
        # gradient axis streaks across separated regions (scattered same-hue colours).
        union = np.zeros(masks[comp[0]].shape, dtype=bool)
        for k in comp:
            union |= masks[k]
        lbl, nlbl = ndimage.label(union)
        if nlbl == 0:
            continue
        comp_sizes = np.bincount(lbl.ravel())[1:]
        if int(comp_sizes.max()) < _GRAD_CONTIG_FRAC * int(union.sum()):
            continue  # too scattered -> leave these colours flat
        comp = sorted(comp, key=lambda k: labs[k][0], reverse=True)  # light -> dark
        cents = {}
        for k in comp:
            ys, xs = np.nonzero(masks[k])
            cents[k] = (float(xs.mean()), float(ys.mean()))
        (x1, y1), (x2, y2) = cents[comp[0]], cents[comp[-1]]
        dx, dy = x2 - x1, y2 - y1
        if dx * dx + dy * dy < 1.0:
            continue  # degenerate direction (centroids coincide)
        denom = dx * dx + dy * dy
        stops = []
        for k in comp:
            cx, cy = cents[k]
            t = ((cx - x1) * dx + (cy - y1) * dy) / denom
            stops.append((float(np.clip(t, 0.0, 1.0)), k))
        stops.sort()
        stops[0] = (0.0, stops[0][1])
        stops[-1] = (1.0, stops[-1][1])
        out.append({"members": comp, "dir": (x1, y1, x2, y2), "stops": stops})
    return out


def _write_layered_svg(
    svg_path: Path,
    groups: dict[int, list[tuple[str, str | None]]],
    order: list[int],
    thread_map: list[dict],
    size_mm: dict,
    size_px: tuple[int, int],
    clusters: list[dict] | None = None,
) -> int:
    px_w, px_h = size_px
    nsmap = {None: SVG_NS, "inkscape": INK_NS, "inkstitch": INKSTITCH_NS}
    svg = etree.Element(f"{{{SVG_NS}}}svg", nsmap=nsmap)
    svg.set("version", "1.1")
    svg.set("width", f"{size_mm['width_mm']}mm")
    svg.set("height", f"{size_mm['height_mm']}mm")
    svg.set("viewBox", f"0 0 {px_w} {px_h}")

    # Mark the document as the current Ink/Stitch SVG version so Inkscape doesn't
    # prompt to upgrade an "unversioned" file every time it's opened.
    metadata = etree.SubElement(svg, f"{{{SVG_NS}}}metadata")
    ver = etree.SubElement(metadata, f"{{{INKSTITCH_NS}}}inkstitch_svg_version")
    ver.text = INKSTITCH_SVG_VERSION

    clusters = clusters or []
    defs = etree.SubElement(svg, f"{{{SVG_NS}}}defs") if clusters else None
    # member colour index -> cluster index; a cluster is emitted at its first member.
    member_of = {idx: ci for ci, cl in enumerate(clusters) for idx in cl["members"]}
    emitted: set[int] = set()

    n_paths = 0
    # Document order = sew order: background first, foreground (enclosed) last,
    # so the top layers' stitches sit on top (see _sew_order).
    for idx in order:
        if idx in member_of:
            ci = member_of[idx]
            if ci in emitted:
                continue
            emitted.add(ci)
            n_paths += _emit_gradient_cluster(svg, defs, ci, clusters[ci], groups, thread_map)
            continue
        if idx not in groups:
            continue
        n_paths += _emit_flat_group(svg, idx, groups, thread_map)

    tree = etree.ElementTree(svg)
    tree.write(str(svg_path), pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return n_paths


_TRANSLATE_RE = re.compile(r"^translate\(\s*(-?\d+\.?\d*)[ ,]+(-?\d+\.?\d*)\s*\)$")
_COORD_RE = re.compile(r"(-?\d+\.?\d*),(-?\d+\.?\d*)")


def _bake_translate(d: str, transform: str | None) -> str | None:
    """Fold a `translate(tx,ty)` transform into an absolute path's coordinates so paths
    with different transforms can be concatenated into one compound path. VTracer emits
    only absolute commands with `translate` transforms, so offsetting every x,y pair is
    correct. Returns None for any other (non-translate) transform, which can't be baked."""
    if not transform:
        return d
    m = _TRANSLATE_RE.match(transform.strip())
    if not m:
        return None
    tx, ty = float(m.group(1)), float(m.group(2))

    def repl(mm: "re.Match") -> str:
        return f"{float(mm.group(1)) + tx:g},{float(mm.group(2)) + ty:g}"

    return _COORD_RE.sub(repl, d)


def _emit_flat_group(svg, idx: int, groups, thread_map) -> int:
    """Emit one colour's paths as a flat-fill <g> (the normal, non-gradient path)."""
    m = thread_map[idx]
    tr, tg, tb = m["thread_rgb"]
    fill = f"#{tr:02X}{tg:02X}{tb:02X}"
    g = etree.SubElement(svg, f"{{{SVG_NS}}}g")
    g.set("id", f"color{idx}_{m['code']}")
    g.set(f"{{{INK_NS}}}label", f"{m['code']} {m['name']}".strip())
    n = 0
    for j, (d, transform) in enumerate(groups[idx]):
        p = etree.SubElement(g, f"{{{SVG_NS}}}path")
        p.set("id", f"c{idx}_{j}")
        p.set("d", d)
        p.set("fill", fill)
        if transform:
            p.set("transform", transform)
        n += 1
    return n


def _emit_gradient_cluster(svg, defs, ci: int, cluster: dict, groups, thread_map) -> int:
    """Emit a shade cluster as ONE compound path filled with a linear gradient.

    The member colours' vtracer subpaths are concatenated into a single compound path
    (their shared borders cancel under nonzero winding -> the union region); a
    userSpaceOnUse linearGradient from the light member's centroid to the dark member's
    carries the matched thread colours as stops. Step 5's gradient_blocks then converts
    it to variable-density blocks. If any member path carries a transform (which would
    break the naive concat) the cluster falls back to flat groups.
    """
    parts, bakeable = [], True
    for idx in cluster["members"]:
        for d, transform in groups.get(idx, []):
            baked = _bake_translate(d, transform)
            if baked is None:  # a transform we can't fold in -> can't build the union
                bakeable = False
                break
            parts.append(baked.strip())
        if not bakeable:
            break
    if not bakeable or not parts:
        return sum(_emit_flat_group(svg, idx, groups, thread_map)
                   for idx in cluster["members"] if idx in groups)

    x1, y1, x2, y2 = cluster["dir"]
    grad = etree.SubElement(defs, f"{{{SVG_NS}}}linearGradient")
    grad.set("id", f"grad{ci}")
    grad.set("gradientUnits", "userSpaceOnUse")
    grad.set("x1", f"{x1:.2f}"); grad.set("y1", f"{y1:.2f}")
    grad.set("x2", f"{x2:.2f}"); grad.set("y2", f"{y2:.2f}")
    for offset, idx in cluster["stops"]:
        tr, tg, tb = thread_map[idx]["thread_rgb"]
        stop = etree.SubElement(grad, f"{{{SVG_NS}}}stop")
        stop.set("offset", f"{offset:.4f}")
        # gradient_blocks reads the stop colour from the *style* attribute, not the
        # stop-color presentation attribute (that raises KeyError).
        stop.set("style", f"stop-color:#{tr:02X}{tg:02X}{tb:02X};stop-opacity:1")

    g = etree.SubElement(svg, f"{{{SVG_NS}}}g")
    g.set("id", f"gradient{ci}_grad")
    lm = thread_map[cluster["members"][0]]
    g.set(f"{{{INK_NS}}}label", f"{lm['code']} {lm['name']}".strip())
    p = etree.SubElement(g, f"{{{SVG_NS}}}path")
    p.set("id", f"grad{ci}_0")
    p.set("d", " ".join(parts))
    p.set("style", f"fill:url(#grad{ci})")
    # base row spacing gradient_blocks reads (it emits row_sp -> 2x at the sparse end)
    p.set(f"{{{INKSTITCH_NS}}}row_spacing_mm", "0.4")
    return 1
