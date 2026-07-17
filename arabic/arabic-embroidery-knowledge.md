# Arabic Calligraphy Embroidery — Production Knowledge

> **Routing:** which category a photo belongs to, and the rules common to every
> category (back-to-front sew order, min width, the `.vp3` container, thread
> stamping), live in [`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md) and the
> cross-cutting §7–§8 of [`../letters/letters-embroidery-knowledge.md`](../letters/letters-embroidery-knowledge.md).
> Arabic calligraphy is the **script sub-type of LETTERS**; this file is the
> Arabic-specific detail and the **calibrated, end-to-end-tested recipe**.

Distilled from **3 reference `.VP3` files** the user supplied as production examples
(`Design6`, `Design8`, `Design9`), parsed byte-for-byte with `pyembroidery`, **and
validated end-to-end**: each reference was rendered to a clean raster "photo", run
back through this repo's pipeline, and the output `.vp3` compared against the
ground-truth file (size, colour, object type, stitch count, areal density, ink-mask
IoU). Every number below is **measured**, not guessed. Reproduce any of it with the
scripts in [`orchestrator/scripts/`](../orchestrator/scripts/).

---

## 0. The one rule for Arabic: it is single-colour, 100 % SATIN script ⭐⭐

All three references are the **same DNA**, with *zero* exceptions:

- **One thread — pure Black `(0,0,0)`**, stamped as catalog `8`, description `Black`,
  brand `Default` (the same named-black cone the Latin letters references use).
- **100 % satin — zero tatami fills.** Turn-angle reversal rate (consecutive-segment
  turn > 120° = a satin zig-zag) is **77–79 % in every file**, top to bottom. Every
  stroke, every diacritic, every decorative dot, and the enclosing frame is a **satin
  column**, never a fill.
- **Satin width 1.8–2.5 mm** (median cross-segment) — the calligraphic pen width.
- **Every disjoint piece ends in a trim.** Arabic is full of disconnected pieces —
  dots (نقاط), hamzas, the tashkeel (تشكيل: ـَ ـِ ـُ ـّ), and the ornaments — so a
  **single-colour** design still shows **17–30 trims**. That is *normal*, not
  fragmentation.

This is the letters §0 rule ("letterforms are satin") in its purest form: an Arabic
design is **one black thread of pure satin script**. Decoration above / under /
around the words is *the same black satin*, just more pieces (§4).

> Like the rest of the family this file splits into the **Arabic recipe (§1–§6)** and
> a pointer to the **cross-cutting container/thread reference** (letters §7–§8), which
> is category-independent.

---

## 1. What the reference files are (measured)

| File | Phrase | Size (mm) | Colours | Stitches | Trims | Object (rev%) | Satin median |
|------|--------|-----------|---------|----------|-------|---------------|--------------|
| **Design6** | رمضان مبارك (*Ramadan Mubarak*) | 165.4 × 87.8 | 1 — Black `(0,0,0)` `8,Default,Black` | 6 149 | 17 | **SATIN** (79.2 %) | 2.40 mm |
| **Design8** | السلام عليكم (*As-salāmu ʿalaykum*) | 140.0 × 58.9 | 1 — Black | 6 164 | 25 | **SATIN** (76.7 %) | 2.02 mm |
| **Design9** | بسم الله الرحمن الرحيم (*Basmala*, round) | 117.3 × 139.8 | 1 — Black | 9 326 | 30 | **SATIN** (77.4 %) | 1.94 mm |

**Areal density** (pure stitches ÷ bounding area) — the number to match: **Design6
0.42, Design8 0.74, Design9 0.57 st/mm².** Satin script is *sparse* — a column lays
two stitches per pen-width, not a packed fill.

**Piece geometry (split by trim):** Design6 = 18 pieces, Design8 = 24, Design9 = 29.
Both the **big pieces** (span > 15 mm — main strokes & the enclosing frame) **and the
small pieces** (span ≤ 15 mm — dots, diacritics, ornaments) are satin (73–78 %
reversals). The decoration is satin too.

**Reading → the Arabic design DNA:**

- **Size:** medium. A horizontal phrase is **~140–165 mm wide**; a stacked / round
  composition (Basmala) is **~117 × 140 mm**. Big enough that pen strokes land at
  satin width.
- **Palette = 1.** Classic Arabic calligraphy art is *monochrome black*. (A
  multicolour piece — gold on black, a coloured frame — just adds a thread per shade;
  the script itself stays one black.)
- **The dominant — only — object is the satin column.**
- **Trims scale with dottiness,** not with quality. The Basmala (most diacritics +
  the frame) has the most pieces (30 trims) and the most stitches.

---

## 2. The core recipe — building an Arabic design

Sew order is strict **back-to-front** (the family painter's algorithm). For a
monochrome script this mostly means *background frame/large strokes first, fine
diacritics and dots last*, all in the one black:

1. **Enclosing frame / ground ornament** (the oval, cartouche, or baseline swash that
   sits *behind* the words) → satin, sewn **first**.
2. **Main word strokes** (the body of each word) → satin columns, ~2–2.5 mm.
3. **Connecting / overlapping strokes** that cross in front.
4. **Diacritics (tashkeel) and dots** → short satins, near the end; each its own piece
   → trim after.
5. **Tiny top ornaments** (the diamond مَعِين dots, star florets) → last.

Per object:

| Object | Stitch type | Settings (measured / best-practice) |
|--------|-------------|--------------------------------------|
| Main calligraphic stroke (1.8–2.5 mm) | **satin column** | pull-comp 0.2 mm; trim between disjoint strokes |
| Enclosing frame / long swash (1.8–2 mm) | **satin column** (thin) | same; it is just a long thin stroke |
| Diacritic / dot / hamza (< ~15 mm span) | **short satin** | trim after each |
| Diamond / floret ornament | **short satin** | trim after |
| A hairline flourish < ~1.6 mm at final size | **run / triple-run** | will not satin — bold it or accept a run |

This maps onto the pipeline's existing classifier: the black colour's median width
(~2 mm) is well under the 3.0 mm "linework" ceiling (`steps/stitches.py
_SATIN_MAX_WIDTH_MM`), so the **whole design routes to the satin/linework path** with
no flags needed. Clean separable strokes become real satin columns; the connected,
branch-heavy body stays a **continuous contour-fill** (see §3 — the honest limit).

---

## 3. The fill method is the Arabic-specific lever — use `contour_fill` ⭐⭐

Arabic script is **thin and sprawling**: long, narrow, curved strokes that branch and
weave. This is the worst case for Ink-Stitch's default **`auto_fill`**, which routes
one serpentine path across a whole colour with a travel-graph — on sprawling
calligraphy it **over-stitches and can hang for minutes** (it stalled outright on the
Basmala). **`contour_fill` follows each stroke's contour inward**, so the stitches run
*along* the pen stroke like a satin would — fast, natural, and far closer to the
reference satin density.

**Measured, both methods, same input:**

| | Design8 ref | `auto_fill` | **`contour_fill`** | Design9 ref | `auto_fill` | **`contour_fill`** |
|---|---|---|---|---|---|---|
| Stitches | 6 164 | 5 677 | **4 795** | 9 326 | *(stalled)* | **6 276** |
| Density st/mm² | **0.74** | 0.91 (over) | **0.77 ✓** | **0.57** | — | **0.56 ✓** |
| Ink-mask coverage of ref | — | 90.2 % | 85.3 % | — | — | **98.5 %** |
| Speed | — | slow | **fast** | — | **hung** | **fast** |

`contour_fill` lands the **areal density almost exactly on the reference** (0.77 vs
0.74; 0.56 vs 0.57) — `auto_fill` over-stitches. **Always pass
`--fill-method contour_fill` for Arabic calligraphy.** (See the
[contour-fill-for-calligraphy] memory.)

---

## 4. Decoration — above, under, around the words ⭐

The user's case: a photo of Arabic words **with decoration above, under and around**.
In every reference the decoration is **the same black satin as the script** — there is
no separate technique, only more pieces and the right sew order:

- **Above (tashkeel / florets / diamond dots):** small disjoint satins, each ending in
  a trim. Design8's two diamond مَعِين dots and Design6/8's تشكيل are exactly these.
  They are **fine** — keep them ≥ ~1.6 mm so they don't get eaten by the step-2
  consolidation; sew them **last** (top layer).
- **Under (baseline swash / kashida flourish):** a long thin satin stroke; sew it with
  the body or just before, since the words sit on it.
- **Around (enclosing frame — oval cartouche, teardrop, medallion):** a long thin
  satin loop. **Sew it FIRST** (it is the farthest / background layer; the words
  overlap it). Verified on **Design9** — the Basmala's oval frame traced and stitched
  cleanly and the output covered **98.5 %** of the reference ink including the frame.

So for a decorated photo: it is still **one black design**; the only judgement is
**sequence** — frame → words → diacritics/ornaments last. The pipeline's
enclosure-depth ordering does most of this automatically; if a frame must come first
and the auto-order puts it late, split it to its own colour/run or reorder in Phase B.

A **coloured** frame or **gold** script is just a second/third thread — quantise to
that many `--colors`, and the back-to-front order still holds (frame colour first).

---

## 5. Preparing the source photo (what to feed the pipeline)

1. **Crisp pure-black-on-white.** This is the single biggest input rule. A soft scan,
   JPEG ringing, or anti-aliased halo **spawns a phantom second cone** — in testing a
   blurred edge quantised to a gray "Stainless Steel" thread. Threshold the photo to
   solid black on clean white first (or photograph high-contrast art flat-lit).
2. **One colour.** Monochrome Arabic art → `--colors 1`. The background white is
   dropped automatically.
3. **Strokes ≥ ~1.6 mm at final size.** The references sit at 1.8–2.5 mm. Pick the
   width so the pen strokes land in that band:
   - horizontal phrase (السلام عليكم, رمضان مبارك): `--width-mm 140–165`
   - stacked / round composition (Basmala): `--width-mm ~117` (taller than wide)
4. **`--purify-colors`** so the near-black ink snaps to **pure `(0,0,0)`** and matches
   the reference's pure-black cone. Without it the trace edges average the ink to
   ~`(37,37,37)` (a poor, off-black match).
5. **`--fill-method contour_fill`** (§3) and `--thread-chart madeira-polyneon`.

**The calibrated production command:**

```bash
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline arabic/<photo>.png \
    --width-mm 140 --colors 1 --purify-colors \
    --fill-method contour_fill --thread-chart madeira-polyneon \
    --name <name> --output-dir arabic/output
```

(The console script `wilcom-pipeline` is stale — always invoke via
`PYTHONPATH=src .venv/bin/python -m wilcom_pipeline`; see [pipeline-run-stale-venv].)

**Worked examples shipped in [`output/`](output/):** `salam_alaykum_pro.vp3`
(السلام عليكم, from Design8) and `bismillah_pro.vp3` (Basmala + frame, from Design9),
each with its preview, threadlist, and a RED/BLUE/MAGENTA compare-overlay vs the
ground truth. Both gate **PASS**, both stamp **`1800 Black (0,0,0)`**.

---

## 6. Compare-to-original & iterate — the mandatory last step ⭐⭐

**Before delivering, always render the output and measure it against the source/ground
truth; iterate until the drift is explained or gone.** The tools in [`orchestrator/scripts/`](../orchestrator/scripts/)
do exactly this:

- `analyze_vp3.py <file.vp3>` — threads, bounds, satin-vs-fill (reversal %), trims,
  per-block geometry. Confirm: **1 black thread, reversals high, density in band.**
- `render_vp3.py <out> <file.vp3>` — PNG of the stitches + piece geometry.
- `vp3_to_photo.py <ref.vp3> <photo.png>` — turn a reference into a clean raster (how
  the calibration set was built).
- `compare_vp3.py <ref.vp3> <cand.vp3> <overlay.png>` — **IoU, ref-coverage, and a
  RED=reference / BLUE=output / MAGENTA=match overlay.** This is the drift meter.

**What "good" looks like (from the calibration):** ink-mask **coverage of the source
≥ ~85 %** (Design9 reached 98.5 %), **areal density within ±0.05 st/mm² of the
reference band (0.4–0.8)**, **1 pure-black cone**, **gate PASS**, every word legible in
the preview. If coverage is low at the *tips*, the strokes are clipping — enlarge
slightly or bold the source. If a phantom colour appears, the input wasn't crisp
(§5.1) — re-threshold and re-run.

**Checklist before export:**

- [ ] Palette **1 colour**, pure Black `(0,0,0)`; background separable & dropped.
- [ ] Strokes **≥ 1.6 mm**, in the **1.8–2.5 mm** satin band (§1).
- [ ] `--purify-colors` (pure black) + `--fill-method contour_fill` (§3, §5).
- [ ] Sew order **frame → words → diacritics/ornaments last** (§4).
- [ ] Trims modest (dots/diacritics excepted); fragmentation gate < 5 %.
- [ ] **Areal density ≈ reference 0.4–0.8 st/mm²** (contour, not over-stitched auto).
- [ ] **Thread metadata stamped** — `1800 Black` cone in the VP3 (letters §8).
- [ ] **`compare_vp3.py` run**, coverage ≥ ~85 %, drift explained, preview legible.
- [ ] Size set once via `--width-mm`; don't rescale the `.vp3` afterward.

---

## 7. Honest boundary — tracer vs hand-digitized satin ⭐

The references are **100 % satin** (77–79 % reversals); a raster tracer makes them
**mostly contour-fills with a few clean satins** (Design8: 5 satin columns + contour;
3–7 satins on the others). So two true, documented drifts remain — both inherent to
tracing a raster, neither a bug:

1. **Technique** — fills/contour vs all-satin. `contour_fill` gets the *look* and the
   *density* very close (stitches run along the stroke), but it is not the reference's
   variable-width hand satin. Connected cursive **cannot** be made all-satin by a
   tracer without fragmenting (the letters §8a lesson — never use `--lettering` on
   Arabic; it shatters cursive into illegible pieces).
2. **Thin extremities** — pen strokes taper to a point; the trace clips the last
   ~1 mm, so coverage at the very tips runs ~85–90 % (the bulk and the frame reach
   98 %).

**The real production rule:** the `.vp3` this pipeline emits is a **byte-faithful,
legible, density-accurate, editable intermediate** — excellent for a stitch-out and a
strong starting point. For *gallery-grade* Arabic calligraphy (true variable-width
satin, crisp tapered tips, the master's stroke modulation), the reference quality is
reached by **digitizing the satin columns by hand in Wilcom (Phase B)** — or, if the
phrase is a *known* text, typing it in an Arabic satin font. Trace when the
calligraphy exists only as an image; hand-satin to finish. See
[`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md) §4.

---

## 8. The arb trio — how the master digitizer actually builds Arabic (video ground truth) ⭐⭐

The `pairs/arb/` trio (SVG + VP3 + `arb.webm`, an 18-minute EmbroideryStudio screen
recording — the video replaces the props-screenshot JSON for this design) is the first
*process*-level ground truth: it shows the .emb being inspected object by object and the
machine simulation sewing it. Ayat-al-Kursi composition, 279.6 × 245.2 mm, 46k stitches,
3 stops (Red holder → Blue "Allah" → Red arcs), **1,618 objects and only 2 trims**.

What the UI showed (all transcribed into `pairs/arb/arb_props.json`):

- **Construction = dissection into ~1,600 tiny column objects.** The calligraphy is cut
  into ~10 mm stroke pieces: 909 closed **Column A** shapes (two-rail, variable width)
  + 703 **Column C** centerlines (base width 0.80 mm) — the SVG carries exactly these
  as filled paths + stroke polylines, a 1:1 object map. Median piece = ~27 stitches.
- **Everything is satin.** Fills tab for all 1,618 objects: Satin, **Auto spacing ON,
  0.24 mm base @ 90 % adjust**, satin count 7, **Auto split ON: length 7.00 mm, min
  0.40 mm**. Sewn rungs: red arcs median ~2.0 mm, blue Allah median ~4.1 mm, p95 7.5 mm
  — the 7 mm satin width is REAL and auto-split keeps it sewable; nothing becomes
  tatami.
- **Connectors: Jump, Trim after OFF, Tie in OFF** (whole-design selection). Travel
  between pieces is walked/jumped without trimming — that's the 2-trim total. Wide
  Column A pieces carry Double-Tatami by-segment underlay (3.0/4.0/45°, margins 0.2);
  pull comp is *disabled* (0.17 mm shown greyed).
- **Machine run** (Stitch Player, TrueView): one continuous sew per stop, arc by arc,
  pieces chained along the stroke direction.

**Pipeline consequences (all prior-driven, wired 2026-07-17):**

1. `register_pair.py` now classifies stitch-kind on a 2 mm-dilated object mask — the
   tight mask chopped satin rungs into co-linear fragments that voted "fill"
   (arb: 1,523/1,556 verdicts satin after the fix, matching the video).
2. A category whose pairs are **satin-only** (< 5 % fill verdicts) takes its satin
   ceiling from the digitizer's own **Auto-Split length (7.00 mm)** instead of a width
   percentile → arabic ceiling is now 7.0 mm (was 3.6): wide strokes like the Allah
   glyph stay satin, as production does.
3. `authored.trim_after_off_frac` (from the Connectors tab) → step 5's travel planner
   drops trims by travel length alone for arabic (the ≤ 12 mm cap stays; the cover law
   is waived because production provably sews uncovered short travels).

---

## 9. Provenance & how to reproduce

- Files parsed with `pyembroidery`; satin-vs-fill via consecutive-segment turn-angle
  (> 120° = reversal); pieces split on `TRIM`/`COLOR_CHANGE`.
- The end-to-end calibration: `vp3_to_photo.py` → `python -m wilcom_pipeline` (recipe
  §5) → `compare_vp3.py` against the ground truth. All four scripts are in
  [`orchestrator/scripts/`](../orchestrator/scripts/); the worked outputs are in [`output/`](output/).
- Consistent with [`../letters/letters-embroidery-knowledge.md`](../letters/letters-embroidery-knowledge.md)
  (Arabic = the script sub-type of letters; satin dominant, §0 there) and the
  cross-cutting `.vp3`/thread reference (letters §7–§8). The Arabic-specific additions
  are **monochrome single black**, **`contour_fill` for sprawling script**, and the
  **frame-first decoration sequence**.
</content>
