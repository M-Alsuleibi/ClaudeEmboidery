# Simple Shapes Embroidery — Production Knowledge

> **Routing:** which category a photo belongs to, and the rules common to every
> category (back-to-front sew order, min width, the `.vp3` container, thread
> stamping), live in [`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md) and the
> cross-cutting §7–§8 of [`../letters/letters-embroidery-knowledge.md`](../letters/letters-embroidery-knowledge.md).
> "Simple shapes" is the **flat-icon / vector-graphic** branch of the playbook's
> *flat logo / icon* row; this file is the shape-specific detail and the
> **calibrated, end-to-end-tested recipe.**

Distilled from **17 reference `.VP3` files** the user supplied as production examples,
parsed byte-for-byte with `pyembroidery`. The **first 6** (`6`, `Design2`, `Design3`,
`Design4`, `Design11`, `Design18`) are the *flat-icon* set and were also **validated
end-to-end**: a multi-colour reference was rendered to a clean flat raster "photo", run
back through this repo's pipeline, and the output `.vp3` compared against the ground
truth (size, colour, object type, stitch count, areal density, ink-mask IoU); plus an
**independent** synthetic shape sheet was traced from scratch and measured against its
own source. A **second batch of 11** (the `*_inch_*` and `Design13/14/Design4 (1)` files,
§1b) adds a whole new archetype — **single-colour line-art / outline drawings sewn 100 %
as satin** (dove, deer, wolf, cats, seaweed, butterfly-moon) — plus a measured
**inch-based sizing convention** (§5). Every number below is **measured**, not guessed.
Reproduce any of it with the scripts in [`orchestrator/scripts/`](../orchestrator/scripts/).

---

## 0. The one rule for simple shapes: bold flat silhouettes, tiny clean palette ⭐⭐

A "simple shape" design is a **handful of bold, flat, closed icon silhouettes** — a
star, a heart, a balloon, an arrow, a spiral/swirl, a frame/border, a constellation of
small stars — each a single solid colour, on a clean ground. The DNA across all six
references:

- **Tiny palette: 1–4 colours.** Never shaded, never a gradient. Each shape is one
  flat colour; colours are **bright and clean** — either **pure primaries**
  (Design3: Black + Red + Yellow + Cyan, named cones) or **clean pastels** (`6`/`Design2`:
  coral · light-pink · olive · aqua). One- and two-colour designs are common
  (`Design4` 1 black, `Design18` 1 grey, `Design11` 2).
- **Each shape = exactly one stitch object, chosen by its width** (the universal
  classifier, playbook §0a). Bold compact body → **fill**; narrow ribbon/stroke/border
  → **satin column**; hairline connector → **run**. The references are
  **satin-dominant** because a digitizer chose satin for the sheen, but a *tracer*
  fills the broad bodies and satins the thin parts — both are production-correct.
- **Satin/feature width is WIDER than calligraphy: ~2–6 mm** (median cross-segment).
  Calligraphy sits at 1.8–2.5 mm; shapes run from a 2 mm arrow up to 5.6 mm swirls and
  ~6 mm frame bars. Shapes are *chunky*.
- **Trims = number of disjoint motifs**, nothing more. A single clean icon has 0–2
  trims (`Design11` 0, `Design18` 2); a 21-star constellation has 21 (`Design4`). Many
  trims on a scatter is *normal*, not fragmentation.
- **Sew each shape as one unit, back-to-front.** Layered shape → base body first,
  highlight/string last (`Design11`: pink balloon then white highlight). Frame → outer
  ring → inner. Constellation → stars + run connectors.

This is the playbook §0a region→object rule applied to **clean geometric icons**: small
palette, one object per shape, painter's-order sew. The category-specific levers are
the **thread chart** (§3) and the **per-shape object choice** (§2).

### The two archetypes: solid-fill icons **and** single-colour line-art ⭐⭐

The 11-file second batch (§1b) makes clear there are **two** simple-shape archetypes, and
they sew differently:

- **(A) Solid-fill icon** — a bold filled silhouette: paw print, heart, star, balloon,
  strawberry. The body is a **tatami fill**; thin ribbons/borders satin. This is the
  archetype §0/§2 already described (`6`, `Design3`, `Design11`, `5.5_inch_03ltz5`).
- **(B) Single-colour line-art / outline drawing** — a coloring-book / tattoo-flash style
  **line drawing** (flying dove, deer head, howling wolf, two cats, seaweed, butterfly +
  crescent moon). There is **no solid body**: the *entire subject is the outline*, sewn
  **100 % as satin columns** following the strokes (median width a consistent **~1.2–2.3 mm
  pen-line weight**, reversal 75–80 %). The white interior stays background. Most are
  **one colour**; small solid accents (a cat's ears/paws) get tatami fill *inside* the
  line work. **7 of the 11 new files are this archetype** — it's now the dominant one.

For the pipeline this is the easy case: a thin-everywhere line drawing routes **wholesale
to satin** by the width classifier (`med width < _SATIN_MAX_WIDTH_MM = 3.0`), so feeding a
clean black-line-on-white drawing gives an all-satin outline with no flags. The trims just
count the disjoint strokes (seaweed = 74, butterfly-moon = 14) — that is **expected
intricacy, not fragmentation**.

> Like the rest of the family this file splits into the **shapes recipe (§1–§6)** and a
> pointer to the **cross-cutting container/thread reference** (letters §7–§8), which is
> category-independent.

---

## 1. What the reference files are (measured)

| File | Subject | Size (mm) | Colours | Stitches | Trims | Dominant object | density |
|------|---------|-----------|---------|----------|-------|-----------------|---------|
| **6** | cluster of **9 five-point stars** | 165.1 × 158.5 | 4 — coral `(255,108,100)` · lt-pink `(255,178,174)` · olive `(196,187,116)` · **Aqua** `(51,204,204)` | 4 895 | 1 | satin-filled stars (rev 35–76 %, med 2.2 mm) | 0.19 |
| **Design2** | **spirals / swirls** (flourish) | 107.5 × 158.6 | 3 — coral · Aqua · lt-pink | 9 364 | 3 | **satin columns** (rev 81 %, med 5.6 mm) | 0.55 |
| **Design3** | **rectangular frame / border** | 81.4 × 127.4 | 4 — Black `(31,26,23)` · Red `(218,27,29)` · Yellow `(255,245,0)` · Cyan `(0,147,221)` | 3 208 | 1 | satin border bars + filled corners | 0.31 |
| **Design4** | **constellation** (star scatter + run connectors) | 87.2 × 43.9 | 1 — Black `(0,0,0)` | 3 303 | 21 | satin stars + **run** lines | 0.86 |
| **Design11** | **balloon / heart** | 20.4 × 27.6 | 2 — pink `(255,97,144)` + White highlight | 892 | 0 | fill body + satin highlight | 1.58 |
| **Design18** | **up arrow** | 11.7 × 26.4 | 1 — grey `(189,189,189)` | 427 | 2 | satin | 1.38 |

**Reading → the simple-shapes DNA:**

- **Size:** a *single icon* is tiny — **12–30 mm** (arrow, balloon). An *icon set or
  star cluster* is **80–165 mm**; a whole composition is sized by use. Pick the size so
  each shape's narrowest part still lands ≥ 1.6 mm.
- **Palette = 1–4**, bright/clean, one thread per shape colour.
- **Areal density** (stitches ÷ bounding box) is **low for scatters** (`6` = 0.19,
  `Design3` frame = 0.31 — most of the box is empty) and **higher for solid icons**
  (`Design11` 1.58, `Design18` 1.38). The number to match is *per covered shape*, not
  per bounding box; the gate band 0.3–15 st/mm² covers solid icons.
- **The dominant object follows width:** swirls/borders (≥ ~3 mm thin ribbons) are
  **satin columns**; solid bodies are **fills**; connectors are **runs**.

---

## 1b. The line-art / outline batch (11 newer references, measured) ⭐

| File | Subject | Size (mm) | Long-dim inch | Colours | Object | medW / rev | trims |
|------|---------|-----------|------|---------|--------|------------|-------|
| **3.50_inch_mxsuuk** | flying **dove** | 64.2 × 89.2 | 3.5″ (H) | 1 — blue `(48,103,166)` | all-satin outline | 2.06 mm / 79 % | 6 |
| **3.50_inch_x38dxh** | **deer / stag head** | 61.3 × 89.2 | 3.5″ (H) | 1 — Sand `(255,204,126)` | all-satin outline | 2.06 mm / 77 % | 9 |
| **4.50._inch_6p1jgh** | **howling wolf + heartbeat (EKG)** | 114.3 × 105.7 | 4.5″ (W) | 1 — Black | all-satin outline, thin | 1.17 mm / 80 % | 3 |
| **4.50_inch_k8l9tg** | **butterfly + crescent moon + stars** | 114.6 × 102.2 | 4.5″ (W) | 1 — Aqua `(51,204,204)` | all-satin ornate swirl | 1.50 mm / 76 % | 14 |
| **4.50_inch_ri4hfj** | **two cats** (yin-yang) | 114.6 × 106.4 | 4.5″ (W) | 1 — Black | satin outline **+ fill accents** | 1.58 mm / 54 % | 2 |
| **7.50._inch_7pgeq7** | **two cats** — *same art, bigger* | 190.8 × 177.1 | 7.5″ (W) | 1 — Black | satin outline **+ fill accents** | 2.26 mm / 46 % | 1 |
| **6.50_inch_70qibn** | **seaweed + bubbles** | 88.1 × 165.4 | 6.5″ (H) | 1 — Black | all-satin outline, many strokes | 1.60 mm / 79 % | **74** |
| **5.5_inch_03ltz5** | **paw print + red heart** | 139.9 × 135.9 | 5.5″ (W) | 2 — Black + Red | **tatami FILL** (solid icon) | 3.94 mm / 10 % | 4 |
| **Design13** | party **noisemaker / horn** | 45.4 × 19.0 | — | 2 — pink `(204,164,197)` + navy `(0,0,71)` | satin | 2.5 mm / 32–40 % | 5 |
| **Design14** | party **blower + streamers** | 84.0 × 34.2 | — | 2 — Orange `(255,153,51)` + pink | satin streamers | 2.3 mm / 37–46 % | 2 |
| **Design4 (1)** | **strawberry** (≠ the constellation Design4) | 26.0 × 34.0 | — | 3 — red `(191,0,0)` + yellow + green | satin/fill (body, seeds, leaf) | 1.0–2.4 mm | 10 |

**Reading → what the new batch adds:**

- **Line-art is the dominant subject here** (dove, deer, wolf, cats, seaweed, butterfly-
  moon): one colour, **100 % satin outline**, no solid body, consistent ~1.2–2.3 mm stroke
  weight (archetype B, §0). High reversal (75–80 %) confirms pure satin. Where reversal
  drops (cats 46–54 %) it's because a few **solid accents are tatami-filled inside the line
  work** (the cat ears/paws — the dark blobs in the render).
- **Same design ships at several standard sizes:** the two-cats art appears at **4.5″ and
  7.5″** — the digitizer re-exports one drawing across the hoop sizes (§5 inch convention).
- **"Default"-brand named cones**: these files carry a generic **`brand='Default'`** thread
  set (catalog `8`=Black, `3`=Red, `5`=Aqua, `12`=Orange, `16`=Sand) — basic colours, not
  isacord/madeira names; custom mid-tones (the navy `(0,0,71)`, muted pink `(204,164,197)`)
  carry **no catalog** at all (`desc='R204 G164 B197'`). The pipeline should still stamp
  **isacord** (§3); "Default" is just what this particular digitizer left in.
- **`5.5_inch_03ltz5`** is the lone solid-fill icon in the batch (paw + heart) and behaves
  exactly like archetype A: tatami rows (3.94 mm, 10 % reversal), density ≈ 0.88.

---

## 2. The core recipe — building a simple-shapes design

Sew order is strict **back-to-front** (the family painter's algorithm). For a small
icon set this means *farthest/background shapes first, top highlights and connectors
last*:

1. **Frame / border / ground panel** (the thing the other shapes sit on or inside) →
   sewn **first** (`Design3`).
2. **Main shape bodies** — star, heart, arrow, balloon — each its own object, each
   ending in a trim.
3. **Layered highlights / strings** on top of a body (`Design11` white highlight) →
   **last**, over the base.
4. **Connector run lines** of a constellation → run stitch, with the small star motifs
   (`Design4`).

Per object (the playbook §0a classifier, with the shape widths measured here):

| Shape region | Object | Settings |
|--------------|--------|----------|
| Solid compact body (star, heart, balloon, arrow head) ≥ ~3 mm | **fill** (tatami/`auto_fill`) | row 0.4 mm; underlay on; one continuous fill per shape |
| Ribbon / swirl / spiral / frame bar, ~2–6 mm wide | **satin column** | follows the stroke; pull-comp 0.2 mm |
| Thin outline / arrow shaft / small-star arm < ~3 mm | **satin column** (auto) | classifier satins it by width |
| Hairline connector (constellation lines) < ~1.6 mm | **run / triple-run** | ~2.2 mm run |

This maps onto the pipeline's existing classifier: a colour whose median width is below
`_SATIN_MAX_WIDTH_MM = 3.0 mm` routes to **satin/linework**; anything broader becomes a
**fill** (`steps/stitches.py`). For bold solid icons (stars, hearts) that means the body
fills — which is the correct, clean production object for a flat solid shape. Thin
ribbons/borders satin automatically. **No flags needed** for the common case.

---

## 3. The thread chart IS the simple-shapes lever — use `isacord` ⭐⭐

This is the one number that separates shapes from calligraphy. Simple shapes are drawn
in **bright, saturated, clean colours**; **Madeira Polyneon** (the default, tuned for
muted embroidery-art palettes) **does not carry true primaries** — it has *no pure
blue at all*. **Isacord** (a fuller polyester chart) nails them. Measured nearest-cone
ΔE, same input colours:

| Source colour | Madeira Polyneon | **Isacord** |
|---|---|---|
| pure red `(255,0,0)` | Fluo Pink **ΔE 14.3** ✗ | Poppy **ΔE 0.0** ✓ |
| pure blue `(0,0,255)` | Purple Accent **ΔE 90** ✗✗ | Electric Blue **ΔE 0.0** ✓ |
| azure `(0,122,204)` | Fire Blue **ΔE 15.6** ✗ | Cerulean **ΔE 4.1** ✓ |
| aqua `(51,204,204)` | Seafrost **ΔE 14.1** ✗ | Island Green **ΔE 3.0** ✓ |
| pure yellow `(255,255,0)` | Bright Yellow ΔE 0 ✓ | Citrus ΔE 0 ✓ |
| lt-pink `(255,178,174)` | Emily Pink ΔE 6.2 | Corsage **ΔE 2.3** ✓ |

**Always pass `--thread-chart isacord` for simple shapes.** (Calligraphy/letters stay on
madeira-polyneon; shapes flip to isacord.)

### Colour rule: keep the art's real colours — purify ONLY pure primaries ⭐

Same lesson as letters §8b, sharpened by a measured trap. **Default to NO
`--purify-colors`** for shapes: isacord already lands clean colours, and purify
*snaps near-pure colours toward a primary* — which **breaks any custom mid-tone**. In
testing, purify pushed an azure arrow `(0,122,204) → (0,152,255)` and its match
**worsened from ΔE 4.1 to ΔE 16.6**. Only turn `--purify-colors` on when the shapes are
**genuinely pure primaries** (a flag, a pure-cyan/red/yellow frame like `Design3`); for
anything custom/pastel, keep it verbatim.

---

## 4. The fill method — `auto_fill` for bodies, `contour_fill` for swirls ⭐

- **Compact solid icons** (star, heart, arrow, balloon body): **`auto_fill`** (the
  default). It routes one clean serpentine through a compact shape — exactly right, and
  fast on small areas.
- **Thin sprawling ribbons / spirals / swirls** (`Design2`-type flourishes) and **long
  thin frame borders**: **`--fill-method contour_fill`** — same lesson as Arabic
  (auto_fill's travel routing over-stitches and can hang on long thin sprawling
  regions; contour_fill follows the stroke). Use it whenever a shape is a *long thin
  ribbon* rather than a *compact blob*.

(`meander_fill` stipples — only for a deliberately sketchy texture, not standard icons.)

- **Line-art / outline drawings (archetype B)** have **no fill at all** — every stroke is
  satin, so the fill method is moot. The only place a fill appears is a small **solid
  accent inside the line work** (a cat's ears/paws, a strawberry's body): those are
  compact blobs → `auto_fill`.

---

## 5. Preparing the source photo (what to feed the pipeline)

1. **Flat, clean, hard-edged colour on a clean ground.** Shapes are vector art — feed
   crisp solid fills, not photographed/shaded artwork. Anti-alias haloes spawn phantom
   cones (the calligraphy §5 lesson applies). A sticker/clip-art style image is ideal.
2. **Count the colours** → `--colors N` (1–4). One thread per shape colour; the ground
   is dropped automatically.
3. **Size so the narrowest part of every shape lands ≥ 1.6 mm.** Star points and arrow
   tips taper — a too-small design clips them (see §6). Single icon `--width-mm 25–40`;
   icon set / star cluster `--width-mm 120–165`. **Line-art outlines** are sized larger so
   the satin strokes are crisp — typically **one of the standard hoop inch sizes** (§5a).
4. **`--thread-chart isacord`** (§3). **No `--purify-colors`** unless pure primaries.
5. **`--fill-method contour_fill`** only for swirl/ribbon designs (§4); else default.

### 5a. Size to a standard inch — set by the **longest** dimension ⭐

The line-art batch is named by physical size in **inches** (`3.50_inch_…`, `4.50_inch_…`,
…, `7.50_inch_…`) and the inch is the design's **longest side**, matched to within 0.01″:
3.5″ → 89 mm, 4.5″ → 114 mm, 5.5″ → 140 mm, 6.5″ → 165 mm, 7.5″ → 191 mm. Whichever of
width/height is larger gets that inch value (the dove/deer/seaweed are *tall*, so the 3.5″
/ 6.5″ is their **height**; the wolf/cats/paw are *wide*, so the inch is their **width**).

Practical rule: pick a **standard hoop inch** (3.5/4.5/5.5/6.5/7.5″ = `--width-mm` /
`--height-mm` of **89/114/140/165/191**) and pass it on the **longer axis**. The same
artwork is commonly re-exported at several of these (the two-cats design ships at 4.5″ and
7.5″) — so quote a size set, not one number, when the customer hasn't picked a hoop.

**The calibrated production command (clean icon set):**

```bash
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline simple-shapes/<photo>.png \
    --width-mm 150 --colors 3 --thread-chart isacord \
    --name <name> --output-dir simple-shapes/output
# swirls/ribbons: add --fill-method contour_fill
# pure-primary flag-style art: add --purify-colors
```

**Line-art / outline drawing (archetype B — one colour, all satin):** feed a clean
black-line-on-white drawing, size on the longest axis to a standard inch, keep colours = 1.
The thin-everywhere strokes route wholesale to satin — **no fill flags needed**:

```bash
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline simple-shapes/<lineart>.png \
    --width-mm 114 --colors 1 --thread-chart isacord \
    --name <name> --output-dir simple-shapes/output
# longest side = 114mm (4.5") here; use --height-mm for tall art (dove/deer/seaweed)
```

(The console script `wilcom-pipeline` is stale — always invoke via
`PYTHONPATH=src .venv/bin/python -m wilcom_pipeline`; see [pipeline-run-stale-venv].)

**Worked examples shipped in [`output/`](output/):** `stars_pro.vp3` (the 4-colour star
cluster, calibrated from `6.VP3`) and `shapes_test_pro.vp3` (an independent heart +
star + arrow sheet), each with its preview, threadlist, and a RED/BLUE/PURPLE
compare-overlay. Both gate **PASS**.

---

## 6. Compare-to-original & iterate — the mandatory last step ⭐⭐

**Before delivering, always render the output and measure it against the source/ground
truth; iterate until the drift is explained or gone.** The tools in [`orchestrator/scripts/`](../orchestrator/scripts/):

- `analyze_vp3.py <file.vp3>` — threads, bounds, satin-vs-fill (reversal %), trims,
  per-block geometry. Confirm: **1–4 clean cones, object per shape sane, density in
  band.**
- `render_vp3.py <outdir> <file.vp3>` — PNG of the stitches + per-piece geometry.
- `vp3_to_photo.py <ref.vp3> <photo.png>` — turn a **multi-colour** reference into a
  clean flat raster (colour-accurate, per-block) to calibrate against ground truth.
- `compare_vp3.py <ref.vp3> <cand.vp3> <overlay.png>` — IoU / coverage vs a ground-truth VP3.
- `compare_to_photo.py <source.png> <cand.vp3> <overlay.png>` — **IoU + source-coverage
  vs the original photo** (no ground-truth VP3 needed). This is the drift meter for a
  fresh design.

**What "good" looks like (from this calibration):**

| Check | Star cluster (`6`) | Shape sheet (synthetic) |
|---|---|---|
| IoU vs source/ref | **84.4 %** | **91.5 %** |
| source/ref-covered | **99.7 %** | **100 %** |
| palette | 4 isacord cones (ΔE ≤ 8.9) | 3 isacord cones (red ΔE 5.2, yellow 0.6, blue 4.1) |
| gate | PASS | PASS |
| density | 0.20 (sparse scatter) | 0.90 (solid icons) |

Coverage ≥ ~99 % means **no shape was dropped**; the IoU gap is the fill running a hair
fat (pull-comp) plus clipped tapered tips. If coverage falls at the *points* of a star
or the *tip* of an arrow, the shape is too small — **enlarge** so the narrow part clears
1.6 mm and re-run.

**Checklist before export:**

- [ ] Palette **1–4 colours**, bright/clean; ground separable & dropped.
- [ ] **`--thread-chart isacord`**; `--purify-colors` only for true pure primaries (§3).
- [ ] Each shape one object by width: body→fill, ribbon/border→satin, connector→run (§2).
- [ ] `--fill-method contour_fill` only for swirl/ribbon designs (§4).
- [ ] Narrowest part of every shape **≥ 1.6 mm** at final size (§5.3, §6).
- [ ] Sew order **frame/background → bodies → highlights/connectors last** (§2).
- [ ] Trims ≈ number of disjoint motifs; fragmentation gate < 5 %.
- [ ] **Thread metadata stamped** — named isacord cone in the VP3 (letters §8).
- [ ] **`compare_to_photo.py` run**, source-coverage ≥ ~99 %, drift explained, preview clean.
- [ ] Size set once via `--width-mm`; don't rescale the `.vp3` afterward.

---

## 7. Honest boundary — tracer fill vs hand-satin sheen ⭐

The references are **satin-dominant** (a digitizer satined the star arms and swirls for
the directional sheen). A raster tracer **fills** the broad bodies and satins only the
thin parts. Two true, documented drifts remain — both inherent to tracing a flat raster,
neither a bug:

1. **Object** — a tatami-filled star vs a satin-filled star. The fill is a **clean,
   production-correct** rendering of a solid shape (it stitches out flat and even); it
   just lacks the satin *sheen* the hand-digitized reference has. For the satin look on
   star arms / swirls, lay satin columns by hand in **Wilcom (Phase B)** — or, for a
   *known* primitive (a perfect star/heart/arrow), author it as an SVG and satin it
   there, exactly like the 3D doc builds facets instead of tracing.
2. **Thin extremities** — star points and arrow tips taper to nothing; the trace clips
   the last ~1 mm, so coverage at the very tips runs slightly under 100 % while the
   bodies reach 99–100 %.

**The real production rule:** the `.vp3` this pipeline emits is a **byte-faithful,
clean, density-accurate, editable intermediate** — excellent for a stitch-out and a
strong starting point. Because simple shapes are *known primitives*, the playbook's
"**trace it or build it?**" question (playbook §4) leans toward **build**: a star, heart,
or arrow you can author as a crisp SVG and satin/fill exactly, rather than tracing a
picture of one. Trace when the shape exists only as an image; author/hand-satin to
finish.

---

## 8. Provenance & how to reproduce

- Files parsed with `pyembroidery`; satin-vs-fill via consecutive-segment turn-angle
  (> 120° = reversal); pieces split on `TRIM`/`COLOR_CHANGE`.
- The end-to-end calibration: `vp3_to_photo.py` (colour-accurate) → `python -m
  wilcom_pipeline` (recipe §5) → `compare_vp3.py` against the ground truth; plus a
  from-scratch `assets/make_shapes_test.py` sheet measured with `compare_to_photo.py`.
  All scripts in [`orchestrator/scripts/`](../orchestrator/scripts/); the worked outputs in [`output/`](output/).
- Consistent with [`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md) (simple shapes
  = the flat-logo/icon branch) and the cross-cutting `.vp3`/thread reference
  (letters §7–§8). The shape-specific additions are **isacord for bright clean
  colours**, **one object per shape by width**, and **purify-only-pure-primaries**.
