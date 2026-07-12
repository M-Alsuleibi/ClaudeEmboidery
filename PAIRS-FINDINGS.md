# Learning from (SVG, VP3) production pairs → better photo→VP3

**Goal:** use paired **(CorelDRAW-exported SVG, production VP3)** files — plus the Wilcom manual —
to teach *this pipeline* what real production designs decompose into, so it produces better `.vp3`s
from ordinary photos. This is the object-level ground truth the `.vp3` alone can't give.

Tools (in `orchestrator/scripts/`; pairs live at `<category>/pairs/<design>/`, e.g.
`anime/pairs/pink-goku/`):
- [`ingest_pairs.py`](orchestrator/scripts/ingest_pairs.py) — **the front door**: drop pairs in
  `pairs-inbox/`, run this; it auto-categorizes, files, labels (runs both tools below), tracks
  the VP3, and rebuilds the fingerprint profiles. See `pairs-inbox/README.md`.
- [`extract_pair.py`](orchestrator/scripts/extract_pair.py) — `python extract_pair.py <design>.svg <design>.VP3`
  → writes `<design>_objects.json` + prints a summary (structure: families, colours, order).
- [`register_pair.py`](orchestrator/scripts/register_pair.py) — `python register_pair.py <design>.svg <design>.VP3`
  → **SVG↔VP3 registration**: fits a similarity transform (scale+rotation+translation) by
  trimmed ICP aligning the SVG ink to the stitch footprint (robust to off-page/clipping
  outlier paths, which are flagged not fitted), then measures **each SVG object in real mm**
  (area, EDT stroke width) and overlays the VP3 stitches per region (count, density,
  effective row spacing, satin-vs-tatami verdict via the fingerprint block classifier).
  Writes `<design>_measures.json` + `<design>_reg.png` (red=SVG ink, blue=stitches,
  purple=match — eyeball the alignment).

## What each half of a pair is trusted for (learned empirically)

| Source | Gives | Trust |
|---|---|---|
| **CorelDRAW SVG** | object **families** (fill vs outline), **colours**, **sew order**, outline:fill ratio | ✅ reliable (scale-independent) — filled shape `filN` = area object; `fil0 strN` stroke = line/outline object |
| **VP3** | **size (mm)**, density, **satin/fill split**, satin width, stitch count | ✅ reliable (real machine mm) |
| SVG *coordinates* → mm widths | per-object width | ✅ **via `register_pair.py`** (trimmed-ICP similarity fit). Naively ❌: the export has off-page/clipping paths and its raw bbox aspect didn't match the VP3 (pink-goku: ~1.15 vs 1.33) — those are exactly the outlier paths the robust fit rejects/flags. |

So the method is: **SVG for the object decisions, VP3 for the measured realisation.** True per-object
widths need SVG↔VP3 registration — now built (`register_pair.py`). On pink-goku it converges to
**0.29 mm trimmed-RMS residual** (scale 0.00469 mm/uu, rotation −0.11°), flags 30/335 paths as
non-stitched outliers (the clipping/off-page junk that skewed the naive bbox aspect), and recovers
per-object labels: fill-object widths median **2.88 mm** (p10 1.20, p90 5.96 — squarely the satin
band, confirming the ~7 mm ceiling), stitch-kind verdicts 72 satin / 26 fill / 14 mixed per object.

## First pair — `pink-goku` (Super Saiyan Rosé, a real anime production design)

```
SVG structure : 118 FILL-family + 217 OUTLINE-family objects   (outline:fill = 1.84 : 1)
                7 colours
VP3 fingerprint: 120 mm, 15176 stitches, density 1.41
                satin 82.9%  ·  fill 4.7%  ·  mixed 12.4%  ·  satin width 2.25 mm  ·  0 trims
```

### The headline: **anime is SATIN-DOMINANT and outline-heavy — the opposite of our assumption**

Our pipeline currently treats anime as a **colourful photo** category: `CATEGORY_COLORS["anime"] = 12`,
**not** satin-dominant (it had *zero* ground-truth files, so `category_satin_dominant("anime")` is
False → conservative 3 mm ceiling, tatami-leaning). The first real pair says otherwise:

- **82.9 % satin, 4.7 % fill** — anime production is *satin*, not tatami. The character is built from
  **narrow satin columns (~2.25 mm)** — the same satin width as arabic (2.02) and letters (2.37).
- **217 outline objects vs 118 fill (1.84 : 1)** — the design is dominated by **outline/detail
  stitching** (the linework), which is satined. Our pipeline emphasises fills and only routes
  sub-1.6 mm strokes to run — it under-produces this outline detail.
- **7 colours**, not 12 — matches the manual's "simple colour photo 7–10" band.
- This **cross-confirms the anime tutorials** already in `anime/best-practices.md` (the REI Ayanami
  build is literally *"SOMBRAS CON SATIN"* — shadows in satin — *"REFUERZO TATAMI"* — tatami only as
  reinforcement/underlay).

### Pipeline changes — INTEGRATED + VALIDATED (flagged n = 1; firm up with more anime pairs)

1. ✅ **anime is now satin-dominant.** `anime/pink-goku.VP3` added → `fingerprint_vp3.py` gives anime
   its first profile (82.9 % satin) → `category_satin_dominant("anime")` = **True** → anime designs
   now get the 7 mm ceiling + variable-width satin automatically (3D correctly stays False).
2. ✅ **`CATEGORY_COLORS["anime"]` 12 → 8** (config.py; cli/CLAUDE docs updated).
3. ✅ **Broad-region satin strip-tiling ("sombras con satin") — BUILT** (`stitches._satin_strip_lines`,
   under `--satin-lean`). A broad region that would tatami-fill is instead sliced into parallel satin
   columns oriented along its PCA axis — so shaded masses sew as satin like production. Closes the
   fill→satin **metric** gap (see below). Opt-in, so defaults are unchanged.
4. ✅ **TURNING SATIN (contour-following) — BUILT** (`stitches._turning_satin_lines`, tried FIRST on
   the same `--satin-lean` path; straight strips remain only as its fallback). The region is
   onion-peeled by its distance field: each ring's centerline is a marching-squares iso-contour of
   the EDT at an equalised ≤3 mm depth step, so the outermost ring *hugs the boundary* and every
   deeper ring turns with the shape — fixing the strips' stepped edges on irregular/blobby regions.
   Validated end-to-end: a wavy 45 mm blob sews as 7 nested satin rings, satin_frac = 100, edges
   smooth and contour-faithful (hand-rolled marching squares + RDP; scipy only, no cv2/skimage).
   **Refined (G4):** ring seams are now **staggered** (each drifts ~1.5 steps along the boundary,
   with a one-step overshoot double-covering each closure) and the travel planner drops the
   ring-to-ring trims — the blob sews near-continuously (blob region: 1 trim, was ~7) with **no
   aligned radial seam** and no closure wedges. Chaining the rings into ONE spiral column was
   **disproven by measurement**: turns touch by construction (step = width), the column's rails
   graze the neighbouring turns, and Ink-Stitch's rail pairing degenerates into multi-turn throws
   (median stitch 13.7 mm fraction-paired / 14.6 mm with explicit rungs, vs the 3.3 mm width) —
   `_spiral_rings` stays as tested geometry, unused for emission. **Branch junctions are mitred**
   (`_mitre_branch_junctions`): each per-branch satin centerline extends past a shared junction by
   the local half-width (clamped 0.5–2 mm; >4 ends = dense hub, skipped) — measured junction
   coverage ≈100 % (2.6 % bare in the ±0.5 mm disc) on a wavy-Y fixture.
5. ✅ **OUTLINE OBJECTS (the production "outline family") — BUILT** (`--outline-objects`,
   AUTO-on for satin-dominant categories). The pair's headline structure — 217 outline objects
   layered OVER 118 fills — now has a generator: every substantial (≥40 mm²) fill gets a CLOSED
   satin border riding its boundary (centerline = EDT iso-contour at w/2 → outer edge kisses the
   boundary, inner half overlaps the fill, exactly the production layering; counters/holes are
   bordered too). Border width = the category profile's median satin width (pink-goku ⇒ 2.2 mm).
   Validated on the pink-goku render: 38 borders, satin_frac 91.9→**100**, satin_w_mm
   1.37→**2.2 (truth: 2.25)**, source-coverage unchanged at 99.7 %, IoU −0.9 pt (borders are
   additions, not distortions). On broad-region anime art (joker, the input where the gap
   actually lives): 22 borders; per-piece satin 20.4→**53.6 %** (+33 pts; step-7's
   block-granularity metric reads 25→100 because fills+borders share colour blocks); the hair
   stays TATAMI underneath (fills still 46 % of stitches); coverage 90.6 % unchanged, IoU −0.4,
   gate PASS through the per-group fallback. Density rises where borders overlap fills (the
   deliberate production layering); a stacking check is the planned NEXT-GOALS G5 gate.

**Validation (knowledge → measurably changed capability).** Rendered the design as a photo input and
ran the pipeline. Same input, progressive levers:

| pipeline behaviour (same input) | satin_frac | note |
|---|---|---|
| non-satin-dominant, 3 mm ceiling (*before any fix*) | **20.9 %** | fill-dominant |
| `anime` now satin-dominant, 7 mm + vwidth | **40.9 %** | satin width ✓, 7 colours ✓ |
| + `--satin-lean` broad-region **strip-tiling** | **90.1 %** | **matches the 82.9 % truth** (edges stepped — see #3) |

Each extracted insight moved the output: 20.9 % → 40.9 % (satin-dominant + colours) → **90.1 %**
(strip-tiling). The satin-frac gap to the 82.9 % ground truth is **closed**; the remaining work is
**edge quality** (turning satin), not "does it satin". 67 tests pass.

## Adding more pairs

Drop `<name>.svg` + `<name>.vp3` (matching stems) into **`pairs-inbox/`** and run

```bash
.venv/bin/python orchestrator/scripts/ingest_pairs.py     # --dry-run to preview
```

It auto-categorizes the pair (VP3 fingerprint vs the category profiles; near-ties inside the
satin-dominant family are flagged for review, unplaceable pairs go to `pairs-inbox/unknown/`),
files it under `<category>/pairs/<design>/`, generates the labels (`_objects.json`,
`_measures.json`, `_reg.png`), tracks the VP3 in git, rebuilds
`data/category_profiles.json` (the step-7 drift gate), and prints the row to append to the
table below. **Two–three pairs per category** turns a single data point into a profile the
pipeline can safely default from.

| design | category | fill obj | outline obj | out:fill | colours | size mm | satin% | satin w mm |
|---|---|---|---|---|---|---|---|---|
| pink-goku | anime | 118 | 217 | 1.84 | 7 | 120 | 82.9 | 2.25 |
