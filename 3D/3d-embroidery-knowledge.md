# 3D-Shape Embroidery — Production Knowledge

Distilled from two reference designs the user supplied as "perfect" examples, each
with a stitch-out video:

| Reference | File | Video | What it is |
|-----------|------|-------|------------|
| Cube | `مكعب.VP3` | `1 فيديو مكعب.mp4` (98 s) | 3D cube, each of 3 visible faces a 2×2 blue / yellow-green checker, bright outline |
| Watermelon | `البطيخ (1).VP3` | `2 فيديو بطيخ.mp4` (64 s) | Watermelon wedge on a two-tone background |

The videos are **TrueView stitch-out simulations** (grey grid, design built in
running order). They were analysed frame-by-frame; the `.vp3` files were parsed
with `pyembroidery`. The numbers below are *measured from the actual files*, not
guessed.

---

## 1. The core idea

A 3D shape is **not** one object. It is a set of **flat facets** (the visible
faces / regions of the drawing), each digitized as its **own tatami fill**, and
the 3D illusion comes from three things layered on flat fills:

1. **Shade per facet** — lit face = lighter thread, shadow face = darker thread.
   (Cube ref: navy vs yellow-green; melon: light/dark red flesh, aqua vs pink bg.)
2. **A distinct fill ANGLE per facet** — this is the key trick. Even two faces of
   the *same colour* must use *different* stitch angles so light reflects
   differently off each plane and the eye separates them. Verified in the cube
   file: the single "dark blue" colour block contained **three** dominant fill
   angles (≈120°, 0°, 75°) — one per face. The melon's two background halves are
   30° vs 135° (near-perpendicular).
3. **A wireframe outline stitched LAST**, on top of every fill, tracing every
   visible edge (silhouette + internal seams). Cube ref = a bright running-stitch
   wireframe over the finished faces.

## 2. Stitch settings (measured, identical in both files)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Fill type | **tatami** | flat parallel rows |
| Max stitch length | **4.0 mm** | median segment length in every large fill block was 3.96–4.00 mm |
| Row spacing | **~0.4 mm** | standard density |
| Underlay | on | |
| Pull compensation | ~0.2 mm | |
| Trim between regions | yes | each disjoint region ends in a trim (= clean Wilcom Break-Apart boundary). Cube=2 trims, melon=10 |
| Outline | **running / triple (bean) stitch**, ~2 mm | the cube wireframe was running stitch ~2 mm segments, not satin |

Colour counts: cube = 3 threads, watermelon = 10 threads. Keep the palette small —
one thread per shade, reused across facets.

## 3. Sequencing — strict back-to-front (painter's algorithm)

The videos make the order explicit. Stitch from the **farthest** layer to the
**nearest**, smallest top-details last:

- **Watermelon:** aqua background → pink background → pale rind → red flesh
  (shadow then light) → green rind → **black seeds** → **white highlight**.
- **Cube:** all dark-blue squares (all 3 faces) → all yellow-green squares →
  bright **outline** last.

Rules of thumb for ordering:
1. Background / ground plane first.
2. Then each solid: its **back/shadow** facets before its **front/lit** facets;
   for a curved object, the **body** before the **near cap**.
3. Tiny surface details (seeds, specular highlights) near the end.
4. **All black outlines absolutely last.**

In an Ink-Stitch SVG, *document order = stitch order*, so just emit the `<path>`
elements in this sequence. Group same-colour facets adjacently where the layering
allows, to avoid needless colour changes.

## 4. The build recipe (headless, no Inkscape / no Wilcom for the VP3)

Mirrors the repo's step-5. Author an SVG, run the vendored Ink-Stitch binary:

```
inkstitch --extension=zip --format-vp3=True design.svg > out.zip   # extract embroidery.vp3
```

Per facet `<path>` set fill + these Ink-Stitch attrs (namespace
`http://inkstitch.org/namespace`):

```
inkstitch:angle            = <distinct degrees per facet>
inkstitch:fill_underlay    = True
inkstitch:row_spacing_mm   = 0.4
inkstitch:max_stitch_length_mm = 4
inkstitch:pull_compensation_mm = 0.2
inkstitch:trim_after       = True
```

Per outline `<path>` (`fill:none;stroke:#000000`):

```
inkstitch:stroke_method          = running_stitch
inkstitch:running_stitch_length_mm = 2.2
inkstitch:bean_stitch_repeats    = 1     # triple pass -> bold edge
inkstitch:trim_after             = True
```

SVG header sets physical size: `width/height` in `mm`, `viewBox` in px
(e.g. `width="240mm" viewBox="0 0 1200 1200"` → 0.2 mm/px).

`make_3d_test.py` in this folder is a complete, reusable implementation.

## 5. Geometry extraction (for a clean vector-style source image)

The test image has flat colour facets separated by black edges, so each facet is a
connected component. Recipe used (`PIL` + `scipy` + `numpy`, no OpenCV needed):

1. Nearest-colour (winner-take-all) classify every pixel against the palette →
   disjoint facet masks.
2. Per facet, `scipy.ndimage.label` → keep large components.
3. Polygon facets (cube, pyramid): `scipy.spatial.ConvexHull` then simplify to k
   corners (drop the hull vertex of least perpendicular importance until k remain).
4. Curved facets (cylinder caps): fit an ellipse from the mask's covariance
   (eigenvectors → axis angle, 2·√eigenvalue → semi-axes).

## 6. Shape templates

- **Flat-faced solids (cube, pyramid, prism, box):** one polygon fill per visible
  face; distinct angle per face; outline = silhouette + all internal seams.
- **Cylinder:** `body` = convex hull of the front + back rim ellipses (one fill);
  `near cap` = the front ellipse, stitched on top of the body; outline = full near
  ellipse + body silhouette (the two tangent side lines) + the far rim's visible
  arc. Body angle ≈ across the axis; cap angle distinct from body.
- **Cone:** triangle-ish body fill + base ellipse, same idea.
- **Sphere:** approximate with 2–3 concentric/offset shade bands (terminator
  crescent darker) each its own angle; highlight last. (Not in the references —
  extrapolated from the shading principle.)

## 7. Known limits / human-refinement notes

- Outline is a triple running stitch (~1 mm visual), matching the reference. For
  very thick drawn edges a hand satin pass in Wilcom looks richer.
- Fill angles here are chosen for plane separation; a digitizer may fine-tune.
- Tiny strokes below ~1.2 mm get eaten by the repo's step-2 consolidation — not a
  problem here (we author facets directly, bypassing tracing), but relevant if you
  feed a 3D shape through the full photo pipeline instead.
- Final `.emb` still requires the Phase-B Wilcom save; this VP3 is the editable
  intermediate (see project-overview memory).

---

## 8. Test application — `3d-knowlege-test.png`

Input: a pyramid (2 greens), a cube (3 reds), a cylinder (2 blues), black edges.
Output: **`3d-knowlege-test.vp3`** — 31,160 stitches, 8 colours, 17 trims,
231.6 × 230.9 mm. Eight blocks, back-to-front:

1. Pyramid shadow face `#6d9432` @70°  2. Pyramid lit face `#81ba27` @115°
3. Cube shadow face `#cd141d` @72°  4. Cube front face `#e32328` @112°
5. Cube top face `#e9544a` @18°  6. Cylinder body `#40aad4` @65°
7. Cylinder near cap `#60c4e6` @158°  8. Black wireframe outline (running) — last.

See `preview_compare.png` (original vs stitch render) and `preview_render.png`.
Regenerate anytime with `python3 make_3d_test.py`.

---

## 9. 3D **metallic lettering / numerals** (gold/chrome shiny type) ⭐

A second 3D family the references didn't cover: **shiny metallic letters or numbers** —
gold/chrome/bronze, glossy gradient shading, bevelled edges, a specular highlight. The
worked example is `image.png` → **`output/gold2026_pro.vp3`** (a vertical gold **`2026`**).
This is a **hybrid**: a *glyph* (so the [letters/numbers](../numbers/numbers-embroidery-knowledge.md)
rules apply — **open the counters** `0 4 6 8 9`, size by the glyph) wearing a *3D metallic
treatment* (so §1's **shade-per-region** principle applies). The decisions that make it work:

- **It is a smooth GRADIENT, not flat facets → run it through the PHOTO PIPELINE, do NOT
  author facets** (§4 is for hard-edged solids). And critically, **do NOT snap it to a
  solid-colour mask** the way you flatten a textured *flat* numeral
  ([[halftone-face-flatten]]) — snapping kills the metal. **Keep the tonal bands**
  (`--colors 3–4`): the pipeline quantises the gloss into a **light highlight band + mid
  metal + dark bronze shadow**, and *that banding is the 3D shading* (§1.1 shade-per-region,
  applied to a gradient). A near-white **specular highlight** lands its own pale cone
  (e.g. Ghost White) — keep it, it's the shine.
- **`--thread-chart isacord` for warm gold** — measured: isacord **Wheat ΔE 3.3 · Antique
  ΔE 6.6 · Taupe ΔE 3.6 · Ghost-White ΔE 2.4**, all warm/clean; **Madeira's golds skew
  GREENISH** (Pistachio, "Autumn Green") on the same input. (Chrome/steel → grey cones,
  either chart.) Consistent with [[thread-chart-by-palette]].
- **`--open-counters`** (the `0` and `6` here) and **size by the glyph** — a tall stacked
  numeral is `--height-mm` (here 160 → 71 × 160 mm); a wide word is `--width-mm`.
- **Many trims are normal**: the tonal bands are disjoint patches that each trim (104
  trims here = 0.55 % per stitch, well under the 5 % gate — *not* fragmentation).

**Calibrated command:**

```bash
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline 3D/image.png \
    --height-mm 160 --colors 4 --thread-chart isacord --open-counters \
    --name gold2026 --output-dir 3D/output
```

**Result (gate PASS):** 4 isacord gold cones (Wheat · Antique · Taupe · Ghost-White),
19 353 stitches, 104 trims, 71 × 160 mm; **IoU 85.7 % / source-covered 88.0 %** vs the
photo (the ~12 % gap is the thin bevel/specular edge highlights). Tools mirrored in
[`tools/`](tools/); overlay `output/gold2026_compare.png`.

> **Compare-to-original & iterate** (the standing directive [[compare-output-to-original-iterate]]):
> the all-purple overlay confirmed the glyph shapes/counters match; the drift is only the
> hairline bevel highlight, explained not chased. **Richer finish (Phase B):** for a true
> metallic *sheen* lay the highlight band as a satin and add a bevel keyline by hand —
> the traced VP3 is the clean, faithful, editable intermediate.
