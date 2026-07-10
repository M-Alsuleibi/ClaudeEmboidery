# Decoration Embroidery — Production Knowledge

> **Routing:** which category a photo belongs to, and the rules common to every
> category (back-to-front sew order, min width, the `.vp3` container, thread
> stamping), live in [`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md) and the
> cross-cutting §7–§8 of [`../letters/letters-embroidery-knowledge.md`](../letters/letters-embroidery-knowledge.md).
> "Decoration" is the **ornamental-embellishment** branch of the playbook — florals,
> vines, scrollwork, mandalas/rosettes, wreaths, frames, lace collars/necklines and
> borders applied *to* a garment or panel. This file is the decoration-specific detail
> and the **calibrated, end-to-end-tested recipe.**

Distilled from **45 reference `.VP3` files** the user supplied as production examples
(`decoration/re.zip` → `decoration/unzipped/`), parsed byte-for-byte with `pyembroidery`.
One synthetic motif was also **validated end-to-end** (§6): a clean radial rosette was
authored from scratch, run through this repo's pipeline with the decoration recipe, and
measured against its own source (size, colour, object type, density, ink-mask IoU +
source-coverage). Every number below is **measured**, not guessed. Reproduce any of it with
the scripts in [`tools/`](tools/).

---

## 0. The one rule for decoration: symmetric/repeating SATIN ornament ⭐⭐

A "decoration" design is **ornamental embellishment** — a flourish, vine, spray, rosette,
wreath, frame, lace collar or border — meant to *adorn* a garment or panel, not to be the
subject itself. The DNA across all 45 references:

- **Satin-dominant thin ornament.** **94 % of the colour blocks are satin** (78 satin / 5
  fill / 2 mixed across 45 files), reversal **50–97 %**. Every petal, leaf, scroll, vine
  and frame-bar is a narrow satin column following the stroke — the same satin-everywhere
  DNA as Arabic (§2.2), but the subject is **botanical / geometric ornament**, not script,
  and decoration is **multi-colour-capable.** Satin width band **~1.2–3.5 mm** (median
  1.8 mm), widening to ~4–5 mm on big bold scrolls/borders, narrowing to ~0.9–1.5 mm on
  small dense lace.
- **Structure = SYMMETRY & REPETITION** — this is the category's signature (a *simple
  shape* is one icon; a *decoration* is a **pattern**). Three structural idioms: **radial**
  (mandala / rosette / doily / snowflake), **bilateral** (collar / neckline / crest /
  corner spray), and **translational** (a motif run/repeated along a border).
- **Mostly monochrome tone-on-tone.** **32 of 45 are single-colour;** 21 of those carry the
  exact same **`(0,153,0)` "Dark Green", brand `Default`, catalog `1`** — a *working
  placeholder*, not the real thread. Tone-on-tone decoration (white-on-white abaya, gold on
  gold, self-colour lace) is the norm; the customer picks the cone at stitch-out. Multi-
  colour florals/crests/rainbows exist (2–9 colours).
- **Sizing is PLACEMENT-driven, not hoop-driven** (the big difference from simple shapes).
  Borders are sized to the **garment edge** and can be enormous (up to **1160 mm** wide,
  **1008 mm** tall — a full sleeve/placket/hem run, aspect ratios to **10:1**); mandalas /
  doilies / wreaths are **hoop-sized 79–202 mm**; free-standing-lace motifs are **small
  33–55 mm.**
- **Many trims = intricacy, not fragmentation.** Lacy mandalas and scatter florals run
  **up to 231 trims** (each disjoint petal/leaf/bead its own piece); continuous vines run
  **0–1.** Both are correct — the trim count just equals the number of disjoint elements.
- **Sew back-to-front.** Frame/ground first → vines/sprays → petals/leaves → beads/dots/
  florets and any keyline **last**. Standard family painter's order.

This is the playbook §0a region→object rule applied to **ornament**: small palette (often
1), satin per stroke, painter's-order sew. The category-specific levers are the **fill
method** (`contour_fill`, §4 — ornament is thin and sprawling), the **chart by palette**
(§3), and **placement sizing** (§5a).

### The seven sub-types (all measured) ⭐⭐

| # | Sub-type | Structure | Typical size | Reference examples |
|---|----------|-----------|--------------|--------------------|
| 1 | **Border / running strip** | translational | edge-length, AR ≥ 2 (152–1160 mm long) | `0788`, `ROMA RABAB100`, `MONCHE48/53`, `26 abaya`, `600_x_137`, `Design17` |
| 2 | **Mandala / rosette / doily** | radial | hoop 79–202 mm | `5x5-1`, `7x7-1`, `4x4-1`, `5x5_wi9kz6`, `400_x_400_lqeb17`, `3x3-1` |
| 3 | **Free-standing lace (FSL) motif** | radial, openwork | small 33–55 mm (also up to 114) | `130/150/200_x_*_inch`, `4.5_inch_f5z6c2` |
| 4 | **Wreath / garland / corner spray** | bilateral / curved | 70–138 mm | `33 Motif`, `500_x_544` (holly), `3.50_inch_vhdgav` (corner) |
| 5 | **Frame / cartouche / crest** | bilateral, enclosing | 59–280 mm | `31 25cm` (frame), `4.50_l5qlzn` (crest), `545` (hamsa) |
| 6 | **Collar / neckline / placket** | bilateral, garment-fit | 102–379 mm | `djanna` (net-fill), `2`/`3 G gola menina`, `26 abaya` |
| 7 | **All-over / diaper fill** | translational tiling | by area | `AMIRA BKB 1` (trellis), `66 september 2025` (corners) |

> Like the rest of the family this file splits into the **decoration recipe (§1–§6)** and a
> pointer to the **cross-cutting container/thread reference** (letters §7–§8), which is
> category-independent.

---

## 1. What the reference files are (measured)

A representative slice across the seven sub-types (full data in
[`output/_analysis.json`](output/); regenerate with `tools/batch_analyze.py`):

| File | Sub-type / subject | Size (mm) | Colours | Object (rev / medW) | Trims | density |
|------|--------------------|-----------|---------|---------------------|-------|---------|
| **0788** | ① border — 4 paisley motifs, 1.16 m run | 1160 × 503 | 1 — green | satin 86 % / 2.66 mm | 1 | 0.26 |
| **ROMA RABAB100** | ① border — leafy vine, 1 m tall | 100 × 1009 | 1 — green | satin 89 % / 3.58 mm | 0 | 0.33 |
| **MONCHE53** | ① border — mirrored floral spray | 574 × 140 | 1 — green | satin 90 % / 3.06 mm | 1 | 0.39 |
| **26 abaya** | ① abaya placket vine | 161 × 558 | 1 — green | satin 71 % / 2.91 mm | 1 | 0.40 |
| **600_x_137** | ① poinsettia border strip | 152 × 35 | 4 | satin 36–64 % / 0.8–2.3 mm | 58 | 1.39 |
| **5x5-1_5ooea4** | ② red rosette / mandala | 131 × 132 | 1 — Red (Wilcom) | satin 93 % / 2.62 mm | 1 | 0.51 |
| **7x7-1_ildwnt** | ② blue feather mandala | 202 × 200 | 1 — Cyan | satin 69 % / 1.73 mm | 1 | 0.92 |
| **4x4-1_toz6on** | ② dense green doily | 120 × 119 | 1 — Green | satin 65 % / 1.30 mm | 1 | 2.14 |
| **400_x_400_lqeb17** | ② rainbow radial burst | 102 × 102 | **9** | satin 75–81 % / 1.7–2.3 mm | 37 | 1.64 |
| **150_x_160_j59g0f** | ③ FSL aqua snowflake | 38 × 41 | 1 — Aqua | satin 70 % / 1.43 mm | 12 | 2.05 |
| **4.5_inch_f5z6c2** | ③ big lacy aqua snowflake | 114 × 107 | 1 — Aqua | satin 69 % / 1.20 mm | **160** | 1.79 |
| **33 Motif 7x8cm** | ④ laurel wreath | 83 × 70 | 1 — green | satin 85 % / 2.79 mm | 0 | 0.57 |
| **500_x_544** | ④ holly wreath | 127 × 138 | 5 | satin 38–71 % / 0.9–1.6 mm | **231** | 1.21 |
| **3.50_inch_vhdgav** | ④ holly corner spray | 89 × 91 | 5 | satin/mix / 0.9–1.4 mm | 34 | 1.27 |
| **31 25cm** | ⑤ scalloped rectangular frame | 280 × 277 | 1 — green | satin 97 % / 3.83 mm | 1 | 0.11 |
| **4.50_l5qlzn** | ⑤ heraldic crest (crown/heart) | 115 × 92 | 4 | satin 56–71 % / 1.4–1.8 mm | 17 | 0.77 |
| **545** | ⑤ hamsa / khamsa hand | 59 × 66 | 1 — green | satin 78 % / 1.30 mm | 1 | 2.37 |
| **djanna** | ⑥ neckline — **net/mesh lace FILL** | 379 × 328 | 1 — green | **FILL 0 % / 1.56 mm** | 1 | 0.16 |
| **3 G gola …com flor** | ⑥ girl's collar + floral spray | 102 × 178 | **7** | satin + 1 fill / 1.5–3.2 mm | 26 | 0.39 |
| **AMIRA BKB 1** | ⑦ all-over trellis fill | 354 × 185 | 1 — green | satin 85 % / 1.75 mm | 0 | 1.08 |
| **66 september 2025** | ⑦ mirrored corner flourishes | 532 × 303 | 2 — green+blue | satin + fill / 4.2–4.9 mm | 1 | 0.29 |

**Reading → the decoration DNA:**

- **Object is overwhelmingly satin** (94 % of blocks). The lone **FILL** archetype is
  `djanna` — a collar whose **body is an open net/mesh lace fill** (low-density, 0 %
  reversal) inside satin scalloped edges. A few floral leaves are filled inside the satin
  line work (`2/3 G gola menina`); `66 september`'s corner bodies are broad fills.
- **Size spans 38 mm → 1.16 m**; aspect ratio 1:1 (mandalas/frames) → **10:1** (borders).
  Density is **low-to-medium** (0.11–2.37, median 0.78) — ornament is *open* satin, sparse.
- **Trims = disjoint elements:** 0–1 for continuous vines, **up to 231** for lacy
  wreaths/scatter florals. Never read a high trim count as fragmentation here.
- **Palette is small** — 32 of 45 are one colour; the multi-colour cases are florals
  (5–7), crests (4), and one **9-colour rainbow** burst. The recurring `(0,153,0)` "Dark
  Green Default" is a **placeholder working colour** (tone-on-tone production).
- **Charts in the references** are a mixed bag — generic `brand='Default'`
  (Green/Red/Aqua/Pink/Orange/Black), some `brand='Wilcom'` (Cyan/Green/Red/Orange), and
  many **bare-RGB no-catalog** custom mid-tones (`desc='R.. G.. B..'`). The pipeline should
  stamp a real chart (§3); "Default/Wilcom/bare" is just what each digitizer left in.

---

## 2. The core recipe — building a decoration design

Sew order is strict **back-to-front** (the family painter's algorithm):

1. **Enclosing frame / ground / net-fill body** (the thing ornament sits on or inside) →
   **first** (`31 25cm` frame; `djanna` net-fill collar body).
2. **Main vines / stems / scroll armatures** — the structural strokes.
3. **Petals / leaves / feathers** radiating off the armature, each its own satin column.
4. **Beads / dots / florets / tashkeel-style accents and any keyline** → **last**.

Per object (the playbook §0a classifier, with decoration widths measured here):

| Region geometry (at final size) | Object | Settings |
|--------------------------------|--------|----------|
| Petal / leaf / scroll / vine / frame-bar, ~1.2–3.5 mm wide | **satin column** | follows the stroke; pull-comp 0.2 mm (↓0.05 for fine lace); trim between disjoint pieces |
| Big bold scroll / wide border bar, ~3.5–5 mm | **satin column** (wide) | classifier still satins below the 3 mm ceiling — above it, falls to fill |
| Solid leaf/petal body or crest panel ≥ ~3 mm | **tatami fill** | row 0.4 mm; underlay on; one continuous fill per region |
| **Open net / mesh lace ground** (collar body, `djanna`) | **low-density fill** (net/grid) | open fill (Wilcom net-fill); the lace illusion |
| Hairline connector / vein < ~1.2 mm | **run / triple-run** | ~2.2 mm run |

This maps onto the pipeline's classifier: a colour whose **median width < `_SATIN_MAX_WIDTH_MM`
= 3.0 mm** routes to **satin/linework**; broader colours become **one continuous tatami
fill** (`steps/stitches.py`). **But see §7** — the non-lettering satin path only fires for
a *single clean open column*; **closed-cell ornament** (a hollow leaf, a ring, a frame
outline) reduces to looped/branching centerlines and **falls back to clean fill.** That is
the honest decoration boundary.

---

## 3. The thread chart — by palette, like simple shapes ⭐

Decoration splits two ways on colour:

- **Bright, clean, saturated ornament** — aqua FSL snowflakes, the red/blue/cyan mandalas,
  the 9-colour rainbow burst, pure-primary borders → **`--thread-chart isacord`** (the
  fuller polyester chart). **Madeira Polyneon has no pure blue (ΔE 90)** and misses clean
  primaries (simple-shapes §3); isacord nails red/blue/azure/aqua. This is the **default
  for decoration** because so much of it is bright clean ornament.
- **Muted / botanical florals** — holly-and-berry sprays, the pink girl's collar, the
  poinsettia border, tone-on-tone greens/golds → **`--thread-chart madeira-polyneon`**
  (tuned for muted embroidery-art palettes), same as the calligraphy/art default.

For the dominant **single-colour tone-on-tone** case the chart barely matters (one cone),
but still stamp a real named cone (§6) — open clean in Wilcom/Hatch, not bare RGB.

### Colour rule: keep the art's real colours — purify ONLY pure primaries

Same lesson as letters §8b / simple-shapes §3. **Default to NO `--purify-colors`** for
decoration: the references are full of **custom mid-tones** (the navy, the muted pinks, the
botanical greens, the bare-RGB cones) and purify snaps near-pure colours toward a primary,
**breaking any custom tone.** Turn it on only when the ornament is **genuinely pure
primaries** (a pure-cyan/red mandala, a primary border). For tone-on-tone or botanical,
keep verbatim. **Caution (§5):** with `--colors 1` on thin ink, purify *cannot* rescue a
washed colour — the k=1 centroid is computed before the snap.

---

## 4. The fill method — `contour_fill` for ornament ⭐

- **Thin sprawling ornament** (vines, scrolls, mandala arms, lace, sprays) → **`--fill-method
  contour_fill`** — the **default for decoration.** Same lesson as Arabic (§2.2) and
  simple-shapes swirls: `auto_fill`'s travel routing over-stitches and **can hang** on long
  thin sprawling regions; contour_fill follows the stroke and lands density near the
  references. The validated test (§6) used contour_fill.
- **Compact solid blobs** (a crest panel, a filled leaf body, a small motif) are fine on
  the default `auto_fill`.
- **Open net / mesh lace** (`djanna` collar body) is a **low-density open fill** — author
  it in Wilcom (Phase B) as a net-fill; the tracer does not synthesise the lace grid.

(`meander_fill` stipples — only for a deliberately sketchy texture, not standard ornament.)

---

## 5. Preparing the source photo (what to feed the pipeline) ⭐⭐

Decoration is the category where **source prep matters most**, because the art is **thin
ink on white** and that interacts badly with quantization. The lessons, learned the hard
way calibrating the §6 test:

1. **Feed crisp, flat, hard-edged colour on a clean ground.** Anti-alias haloes (from
   scanning, JPEG, or *programmatic rotation/scaling*) wash thin ink pale — see #4.
2. **Count colours → `--colors N`.** Tone-on-tone ornament = **`--colors 1`**; florals/
   crests 4–7; a rainbow up to 9. The ground is dropped automatically.
3. **Do NOT trap page-colour inside an enclosing outline.** ⭐ A fully-enclosing **frame or
   ring** turns every interior gap into an enclosed "counter" that the background-drop
   keeps as foreground; with `--colors 1` the quantiser then **averages ink + trapped white
   into a pale grey (washout)** — and **no flag recovers it** (the k=1 centroid is computed
   *before* `--open-counters` drops the counters; open-counters fixed the *mask* but the
   colour stayed grey, and on fine art it crashed step 5). Two robust fixes: **(a)** leave
   the design *open to the border* (radiating, not framed) so gaps drop as background; or
   **(b)** draw the ornament **solid-filled** (no hollow cells) so the kept foreground is
   all-ink and the single colour quantises true.
4. **Thin ink + `--colors 1` washes pale.** Even crisp, a *hollow* leaf/ring traps its own
   interior; the weighted mean of (ink + trapped/halo white) pulls the one centroid toward
   white (measured: pure `(8,84,54)` green came back as `(95,145,125)` grey, ΔE 8.3).
   **Solid-fill the ornament** (the tracer fills it anyway, §7) — pure green `(8,84,54)`
   then matched **Green Dust ΔE 6.1.** This is the single most important decoration prep
   step.
5. **Render synthetic art at the pipeline's work resolution (~1200 px long side)** so the
   pipeline never has to downscale (downscaling re-introduces pale edge haloes). Threshold
   to pure colour, resize with **NEAREST**.
6. **Size by placement, features ≥ ~1.2 mm** (§5a). Below ~1.2 mm, step-2 consolidation
   erases the stroke and step-1 warns ("smallest feature … below the 1.2 mm satin minimum").

### 5a. Size by PLACEMENT, not a hoop number ⭐

Decoration is sized to **where it goes**, by the relevant garment dimension — *then* check
it fits a hoop, not the other way round:

| Sub-type | Drive size by | Measured band |
|----------|---------------|---------------|
| Border / strip | the **edge length** it runs along (sleeve, hem, placket, neckline) | 150 mm → **1160 mm**; AR up to 10:1 |
| Mandala / doily / wreath / frame | the **hoop** it centres in | **79–280 mm** (3″–11″) |
| FSL motif | small free-standing ornament | **33–55 mm** |
| Collar / neckline | the **garment opening** | **100–380 mm** |

The `*_inch_*` files follow the same standard-hoop inch convention as simple-shapes §5a
(3.5″→89 mm, 4.5″→114 mm, 5.5″→140 mm, 6.5″→165 mm, 7.5″→191 mm) on the **longer** axis.

**The calibrated production command (mandala / rosette / motif):**

```bash
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline decoration/<photo>.png \
    --width-mm 130 --colors 1 --thread-chart isacord \
    --fill-method contour_fill \
    --name <name> --output-dir decoration/output
# tone-on-tone single colour shown; florals: --colors 4-7 [--thread-chart madeira-polyneon]
# long border: drive the long axis (--width-mm 600 / --height-mm 1000), keep --colors small
# fine lace: add --pull-comp-mm 0.05 [--no-fill-underlay] so it doesn't read heavy
```

(The console script `wilcom-pipeline` is stale — always invoke via
`PYTHONPATH=src .venv/bin/python -m wilcom_pipeline`; see [pipeline-run-stale-venv].)

**Worked example shipped in [`output/`](output/):** `decoration_test_pro.vp3` (a radial
leaf-rosette mandala, 130 mm, 1 colour, isacord, contour_fill) with its preview,
threadlist, and a RED/BLUE/PURPLE compare-overlay. Gate **PASS**; **source-coverage 99.9 %,
IoU 86.4 %,** colour Green Dust ΔE 6.1.

---

## 6. Compare-to-original & iterate — the mandatory last step ⭐⭐

**Before delivering, always render the output and measure it against the source; iterate
until the drift is explained or gone.** The tools in [`tools/`](tools/):

- `batch_analyze.py <files…>` — threads, size, satin-vs-fill (reversal %), trims, density
  for many files at once (the survey behind §1). Writes `output/_analysis.json`.
- `analyze_vp3.py <file.vp3>` — per-file threads, bounds, object per block.
- `montage.py <out.png> <files…>` — colour-accurate thumbnail grid (how the sub-types were
  identified). See `output/_montage_A.png`, `_montage_B.png`.
- `render_vp3.py <outdir> <file.vp3>` — PNG + per-piece geometry.
- `compare_to_photo.py <source.png> <cand.vp3> <overlay.png>` — **IoU + source-coverage vs
  the original** (no ground-truth VP3 needed) — the drift meter for a fresh design.
- `compare_vp3.py <ref.vp3> <cand.vp3> <overlay.png>` — IoU / coverage vs a ground-truth VP3.

**What "good" looks like (from the §6 calibration of `decoration_test`):**

| Check | Value |
|---|---|
| gate | **PASS** |
| source-covered | **99.9 %** (no element dropped) |
| IoU vs source | **86.4 %** (the gap = pull-comp running a hair fat) |
| palette | 1 isacord cone, Green Dust **ΔE 6.1** |
| density | **0.59** (decoration's sparse-medium band) |
| trims | 62 (= disjoint leaves + beads; expected intricacy) |

Coverage ≥ ~99 % means **no ornament element was dropped**; the IoU gap is the satin/fill
running slightly fat (pull-comp). If coverage falls at fine lace tips, the feature is
< 1.2 mm — **enlarge** or drop it to a run. If the colour comes back **grey/washed**, you
hit the §5 trap — solid-fill the ornament and don't trap page-colour.

**Checklist before export:**

- [ ] Sub-type identified (§0) and **sized by placement** (§5a); features ≥ ~1.2 mm.
- [ ] Palette small (often **1**, tone-on-tone); ground separable & dropped.
- [ ] Source **crisp & flat**; ornament **solid-filled / not page-colour-trapping** (§5.3–5).
- [ ] **`--fill-method contour_fill`** (thin sprawling ornament, §4).
- [ ] Chart by palette: **isacord** for bright clean, **madeira-polyneon** for muted
      botanical (§3); `--purify-colors` only for true pure primaries.
- [ ] Sew order **frame/ground/net-fill → vines → petals → beads/keyline last** (§2).
- [ ] Trims ≈ number of disjoint elements; fragmentation gate < 5 %.
- [ ] **Thread metadata stamped** — named cone in the VP3 (letters §8).
- [ ] **`compare_to_photo.py` run**, source-coverage ≥ ~99 %, colour ΔE explained, preview
      clean. Size set once via `--width-mm`/`--height-mm`; don't rescale the `.vp3` after.

---

## 7. Honest boundary — tracer fills vs hand-satin ornament ⭐⭐

The references are **satin-dominant** (94 % of blocks): a digitizer laid a satin column
along every petal, leaf and scroll for the directional sheen. The pipeline's **non-lettering
satin path only fires for a single clean open column** (`stitches.py`: `fill_to_stroke`
must yield exactly one substantial centerline). **Ornament is closed-cell** — a leaf is a
loop, a ring is a loop, a frame is an outline — so it reduces to looped/branching
centerlines and **falls back to a clean tatami/contour fill.** Three true, documented
drifts, none a bug:

1. **Object** — traced ornament comes out as **clean fills**, not satin columns (the §6
   test: 0 satin, all fill). The fill is **production-correct** (it stitches flat and even,
   passes the gate, covers 99.9 %); it just lacks the satin *sheen* and directional flow of
   the hand-digitized reference.
2. **The lace illusion** — `djanna`'s **open net/mesh fill** is a deliberate Wilcom net-fill;
   the tracer renders a collar body as a solid/contour fill, not an openwork grid.
3. **Fine extremities & beads** — sub-1.2 mm lace tips and tiny beads clip during step-2
   consolidation; size up so they clear 1.2 mm or drop them to runs.

**The real production rule:** the `.vp3` this pipeline emits is a **byte-faithful, clean,
density-accurate, editable intermediate** — excellent for a stitch-out and a strong starting
point. Because decoration ornament is **known, symmetric and repeating**, the playbook's
"**trace it or build it?**" question (§4) leans **build** here even more than for simple
shapes: author one motif as **open-centerline SVG and satin it** (exactly like
`3D/make_3d_test.py` builds facets with `inkstitch:*` params), then **mirror/array it** for
the symmetry — that recovers the satin sheen the tracer can't. Trace when the ornament
exists only as an image; author/hand-satin (Phase B) to finish.

---

## 8. Provenance & how to reproduce

- 45 files parsed with `pyembroidery`; satin-vs-fill via consecutive-segment turn-angle
  (> 120° = reversal); pieces split on `TRIM`/`COLOR_CHANGE`; density = pure stitches ÷
  bounding area. Survey via `tools/batch_analyze.py` → `output/_analysis.json`; sub-types
  identified from `tools/montage.py` grids.
- End-to-end validation: `assets/make_decoration_test.py` authors a clean radial rosette →
  `python -m wilcom_pipeline` (recipe §5) → `compare_to_photo.py` against its own source
  (coverage 99.9 %, IoU 86.4 %, ΔE 6.1, gate PASS). All scripts in [`tools/`](tools/); the
  worked outputs in [`output/`](output/).
- Consistent with [`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md) (decoration =
  the ornamental-embellishment branch) and the cross-cutting `.vp3`/thread reference
  (letters §7–§8). The decoration-specific additions are **symmetric/repeating satin
  ornament**, **placement-driven sizing**, **contour_fill by default**, the **§5 thin-ink
  washout / don't-trap-page-colour prep traps**, and the **net/mesh lace** object.
