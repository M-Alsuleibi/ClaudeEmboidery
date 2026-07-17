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
| falahi-01 | falahi | 0 | 1 | — | 1 | 348.9 | 100.0 | 3.8 |
| falahi-02 | falahi | 0 | 2 | — | 1 | 450.2 | 100.0 | 3.85 |
| falahi-03 | falahi | 0 | 10 | — | 1 | 1098.8 | 100.0 | 3.83 |
| falahi-04 | falahi | 0 | 38 | — | 6 | 234.2 | 100.0 | 2.01 |
| falahi-05 | falahi | 0 | 32 | — | 4 | 190.6 | 100.0 | 2.42 |
| falahi-06 | falahi | 0 | 77 | — | 3 | 420.2 | 98.48 | 2.25 |
| falahi-07 | falahi | 0 | 12 | — | 5 | 208.0 | 100.0 | 2.24 |
| falahi-08 | falahi | 0 | 52 | — | 5 | 360.0 | 100.0 | 2.1 |
| falahi-09 | falahi | 0 | 18 | — | 6 | 396.0 | 99.98 | 2.24 |
| falahi-10 | falahi | 0 | 11 | — | 2 | 558.9 | 100.0 | 2.24 |
| falahi-11 | falahi | 0 | 136 | — | 7 | 273.4 | 100.0 | 1.41 |
| 1b | arabic | 258 | 48 | 0.19 | 1 | 592.5 | 100.0 | 5.73 |
| 2 | arabic | 68 | 62 | 0.91 | 0 | 207.3 | 100.0 | 5.1 |
| 6 | arabic | 59 | 80 | 1.36 | 1 | 165.4 | 100.0 | 2.4 |
| 7 | arabic | 81 | 109 | 1.35 | 1 | 140.0 | 100.0 | 2.02 |
| 3 | arabic | 0 | 10 | 10.0 | 1 | 144.6 | 100.0 | 2.55 |
| 4 | arabic | 0 | 3 | 3.0 | 1 | 147.7 | 100.0 | 4.7 |
| arb | arabic | 909 | 703 | 0.77 | 2 | 279.5 | 100.0 | 2.14 |

### Falahi — new category (n = 11), Palestinian tatreez cross-stitch

Registered `falahi` and ingested 11 pairs (garment tatreez: neck yokes/*qabbeh*, plackets,
rosette bands, full dress fronts). All 11 are **0 fill objects / all outline motifs** — the
counted **cross-stitch** grid reads as thousands of tiny outline strokes, not areas. The
fingerprint calls it ~100 % "satin" (each cross arm = a short high-reversal segment), so falahi
lands as satin-dominant, but it is really a *counted-grid* look our tiers can't yet reproduce
(no cross-stitch primitive — see `falahi/falahi-embroidery-knowledge.md`). Priors learned:
satin-w 1.4 / 2.1 / 2.41 mm (grid pitch: 3.8 mm coarse banners → 1.4–2.4 mm fine qabbeh),
crossover 2.41 mm (→ 3 mm ceiling), colours 1 (mono banner) → 3–7 (polychrome), pure primaries
led by green `(0,153,0)`. Registration RMS 0.38–0.69 mm on the fine panels (1–2.2 mm on the
coarse repetitive banners). Note: `register_pair.py` was fixed to resolve CSS **named** colours
(`blue`/`red`/`yellow`) — the polychrome exports use them instead of hex.

### Bulk ingest (51 pairs) + reviewed categorization

Ingested the 51-pair `pairs-inbox/` backlog. Auto-categorization (VP3 fingerprint vs profiles)
was **uncertain on 29/51** — the satin-dominant blind spot (letters/arabic/decoration/numbers all
read ~100 % satin, ~2 mm, few colours). Reviewed every flagged pair visually and corrected the
clear misfilings before committing:

- **numbers was 100 % wrong** — all 8 auto-filed "numbers" pairs are illustrations with **no
  digits** (a beach hat, a dump truck, peacocks, a Nike logo, …); the fingerprint matched them to
  numbers only because that category's ground truth has 3-D digits with fills. Moved all 8 out
  (7 → decoration, the walking figure → anime); **numbers keeps 0 ingested pairs** (its profile
  reverts to its 4 real digit reference VP3s).
- **anime florals → decoration**: #15 (sunflowers), #27 (parrot) were nature motifs, not characters.
- **2 UNKNOWN pairs resolved**: #3 (Kakashi) + #4 are framed anime manga panels → anime; #20 is
  textbook falahi (green-first primaries, 100 % satin, fine grid) → falahi-12.

Final ingested-pair counts: **decoration 33, anime 18, falahi 12, numbers 0** (63 total). Priors
rebuilt: anime crossover 2.12, satin-w med 1.38; decoration crossover 1.57, med 0.94; falahi
pitch med 1.45 (dropped from 2.1 as the fine #20 joined). The borderline anime↔decoration calls
left as-filed are low-harm (both satin-dominant multicolour). `register_pair.py` `_rgb` now
resolves **any** CSS colour name (via PIL `ImageColor`) and fails soft — CorelDRAW uses the full
extended set (`antiquewhite` crashed the old hex parser).

### Trio drop — 4 Arabic calligraphy trios ingested (1b, 2, 6, 7); 3/4/5 held for re-export

First real **trio** ingest (SVG + VP3 + authored `-props.json` Object Properties per
`GEMINI-PROPS-PROMPT.md`). All four are Arabic calligraphy (1b "أكثروا من الصلاة على النبي",
2 "صلى الله عليه وسلم" roundel, 6 "رمضان مبارك", 7 "السلام عليكم"); the fingerprint wanted
1/2 under numbers — overridden with `--category arabic` after visual check. Inbox "1"
collided with the existing (different) `arabic/pairs/1/` band design → renamed **1b**.
Registrations are the tightest yet: trimmed RMS **0.12–0.17 mm** on all four.

- **Arabic now has fill objects** — 1b/2 are fill-heavy (out:fill 0.19/0.91), unlike the
  older all-satin arabic ground truth; arabic priors now: satin-w 1.04/2.45/6.4 mm,
  **crossover 3.6 mm** (was ~2), o:f 0.90 (n = 5).
- **Authored props vs stitch inference**: authored fill spacing **0.475 mm** vs inferred row
  spacing 0.79 mm (Δ40 %) — trust the authored value; inference counts underlay/travel rows.
- **Trios 3, 4, 5 NOT ingested** — their SVGs are incomplete CorelDRAW exports (3: 10
  unfilled paths; 4: 3 paths; 5: one stroke on an empty A4 page, roundel missing vs its
  VP3). Parked in `pairs-inbox/needs-reexport/` awaiting re-export; their props.json and
  VP3s are there too, ready to re-drop.

### Trios 3 and 4 ingested (refined props; wireframe SVGs accepted); 5 stays parked

The user refined the three `-props.json` transcriptions; the SVGs are unchanged — they are
**stitch-wireframe exports** (the CorelDRAW page holds the stitch polylines, stroke-only
`fill:none`, not the filled artwork). Rendered against their VP3s: 3 and 4 carry the FULL
design as wireframe; 5's SVG holds only the bottom rosette/signature fragment of its roundel.

- **Wireframe SVGs register fine** — the SVG *is* the stitch trace, so trimmed-ICP locks on
  (RMS 0.51–0.52 mm for 3/4) and `stitch_kind`/`satin_w_mm` come from the real VP3 stitches
  inside each object mask: genuine ground truth, just COARSE (3 → 10 giant compound paths,
  4 → 3), with no fill-family objects (everything parses as outline, o:f rows above read 0
  fills). All-satin verdicts, satin-w medians 0.36–3.56 mm (3) and 3.24–4.89 mm (4).
- **Trio 5 stays in `pairs-inbox/needs-reexport/`** — its fragment SVG registered (RMS 0.60)
  but the single object mask mixes the rosette with cross-design connector lines, so the
  registration measures aren't trustworthy. The user will re-export 5's real artwork SVG;
  its refined `5-props.json` + VP3 are parked beside it, ready to re-drop as a full trio.
- Arabic priors after: measures n_pairs 5 → **7**, satin-w 1.03/2.45/6.4 (unchanged shape),
  crossover stays **3.6 mm**; authored n_designs 5 → **7**, fill spacing med 0.475 → 0.45 mm,
  pull-comp med 0.17 mm (n 3 → 7), pull-comp-disabled 0.73 → 0.53, underlay-disabled 0.92 → 0.89.
- Oddity: 3's props Design tab claims **8,618 stitches** but 3.VP3 holds 5,545 commands
  (4 and 5 match within ~3 %) — the screenshot may predate the exported VP3 state; the
  per-object settings still correspond (dims match 144.6 × 109.3 mm).

### arb — the first VIDEO trio (SVG + VP3 + screen recording), 2026-07-17

The trio's third element is an 18-min EmbroideryStudio screen recording (`arb.webm`)
instead of a props JSON — the assistant transcribed the UI dialogs frame-by-frame into
`arabic/pairs/arb/arb_props.json` (Fills: satin, auto-spacing 0.24 mm @ 90 %, Auto-Split
7.00/0.40 mm; Special: Column C 0.80 mm centre input; Connectors: **Jump, Trim after
Off, Tie in Off**; obj 61 Column A: Double-Tatami by-segment underlay, pull comp
disabled). Ayat-al-Kursi, 279.6 × 245.2 mm, 46k stitches, **1,618 objects, 2 trims**:
909 Column A closed shapes + 703 Column C centerlines — the CorelDRAW SVG carries the
digitizing geometry 1:1 (fil1/fil2 filled paths = Column A, str0/str1 stroke polylines =
Column C centerlines), so this SVG is the digitizer's dissection itself, not artwork or
stitch wireframe. Ingest fallout: ① register_pair's stitch-kind verdicts now use a 2 mm
dilated mask (tight masks chopped satin rungs into "fill" votes); ② arabic became
`satin_only` → its ceiling is the authored Auto-Split length (7.0 mm, was 3.6 crossover);
③ authored `trim_after_off_frac` → step 5 drops trims by travel length alone for arabic;
④ the missing-middle-arc incident (see INCIDENTS.md) was found comparing the pipeline
rebuild against this VP3.
