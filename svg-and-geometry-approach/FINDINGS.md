# Learning from (SVG, VP3) production pairs → better photo→VP3

**Goal:** use paired **(CorelDRAW-exported SVG, production VP3)** files — plus the Wilcom manual —
to teach *this pipeline* what real production designs decompose into, so it produces better `.vp3`s
from ordinary photos. This is the object-level ground truth the `.vp3` alone can't give.

Tool: [`extract_pair.py`](extract_pair.py) — `python extract_pair.py <design>.svg <design>.VP3`
→ writes `<design>_objects.json` + prints a summary.

## What each half of a pair is trusted for (learned empirically)

| Source | Gives | Trust |
|---|---|---|
| **CorelDRAW SVG** | object **families** (fill vs outline), **colours**, **sew order**, outline:fill ratio | ✅ reliable (scale-independent) — filled shape `filN` = area object; `fil0 strN` stroke = line/outline object |
| **VP3** | **size (mm)**, density, **satin/fill split**, satin width, stitch count | ✅ reliable (real machine mm) |
| SVG *coordinates* → mm widths | per-object width | ❌ **not without registration** — the export has off-page/clipping paths and its aspect didn't match the VP3 (pink-goku: SVG bbox aspect ~1.15 vs VP3 1.33). Scale-dependent numbers come from the **VP3**, not the SVG. |

So the method is: **SVG for the object decisions, VP3 for the measured realisation.** True per-object
widths would need SVG↔VP3 registration (a similarity transform matching the two) — not yet built.

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
   fill→satin **metric** gap (see below). **Known limitation:** straight parallel columns leave
   STEPPED edges on irregular/blobby regions; production *turning satin* (contour-following) is the
   quality path — the next refinement. Opt-in, so defaults are unchanged.

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

Drop `<name>.svg` + `<name>.VP3` here (or a per-category folder), run `extract_pair.py`, and append
the numbers below. Two–three pairs per category turns a single data point into a profile the
pipeline can safely default from. When enough VP3s exist for a category, they also feed
`orchestrator/scripts/fingerprint_vp3.py` (the drift-check profiles).

| design | category | fill obj | outline obj | out:fill | colours | size mm | satin% | satin w mm |
|---|---|---|---|---|---|---|---|---|
| pink-goku | anime | 118 | 217 | 1.84 | 7 | 120 | 82.9 | 2.25 |
