# Numbers Embroidery — Production Knowledge

> **Routing:** numbers are the **LETTERS family** — the playbook router sends "words, a
> name, **numbers**, a monogram, calligraphy" to LETTERS. The cross-cutting rules
> (back-to-front sew order, the universal width→object classifier, min width, the `.vp3`
> container, thread stamping) live in [`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md)
> §0 and the §7–§8 of [`../letters/letters-embroidery-knowledge.md`](../letters/letters-embroidery-knowledge.md).
> This file is the **digit-specific** detail and the **calibrated, end-to-end-tested
> recipe** for years / scores / numerals.

Distilled from **4 reference `.VP3` files** the user supplied as production examples
(`Design10`, `Design15`, `Design2`, `1212`), parsed byte-for-byte with `pyembroidery`,
**and validated end-to-end**: the three supplied `2027` photos (`output/1.jpg`,
`output/2.jpg`, `output/3.png`) were run through this repo's pipeline and the output
`.vp3`s measured against their own source photos (palette ΔE, object type, stitch count,
density, ink-coverage IoU). Every number below is **measured**, not guessed. Reproduce
any of it with the scripts in [`tools/`](tools/).

---

## 0. The one rule for numbers: a short numeric string of bold digit glyphs ⭐⭐

A "numbers" design is almost always a **year / score / short numeric string** (`2026`,
`2027`) or a **single decorated digit** — a handful of **bold digit glyphs** on a clean
ground. A digit is just a glyph, so **everything in the letters playbook applies**; the
digit-specific facts are:

- **Tiny palette: 1–3 colours.** Either one solid colour (`Design10` orange), or a
  **face + a white inline keyline** for a shaded/engraved look (`Design15` black+white),
  or **face + inline + a 3-D edge / drop-shadow** (the `2027` photos). Never a gradient.
- **Each digit = one (or a few) stitch objects, chosen by its stroke width** (the
  universal classifier, playbook §0a). A **chunky rounded digit body → tatami fill**
  (`Design10`); a **narrow serif/script stroke → satin column** (`Design15`, 79 % turn
  reversals on the main strokes). Bold *bubble* digits fill; thin *brush/serif* digits
  satin.
- **Digits have lots of counters — `0 4 6 8 9` — and they MUST read through.** This is
  the single most digit-specific lever: **open the counters** (drop the enclosed
  page-colour) or a `0` fills in solid and reads as a blob. Auto-on in purify/lettering
  modes (`should_open_counters`). See [[open-letter-counters]].
- **Trims = disjoint digit parts**, nothing more. `Design10`'s `2026` = **5 trims** (the
  closed counters of `0`/`6` + the digit gaps); a per-digit two-colour numeral
  (`Design15`) racks up **11 trims / 26 colour-changes** because it alternates
  body→keyline *per digit*. Many trims on a multi-digit number is **normal**, not
  fragmentation.
- **Sew order is strict back-to-front:** 3-D edge / drop-shadow **first** → digit body →
  white inline keyline / highlight **last** (`Design15` sews each digit body-then-white).

This is the playbook §0a region→object rule applied to **digit glyphs**: small palette,
one object per digit-part by width, painter's-order sew, counters open. The
category-specific levers are the **thread chart** (§3), the **mode flag** (§2), and
**counter-opening** (§0).

---

## 1. What the reference files are (measured)

| File | Subject | Size (mm) | Colours | Stitches | Trims | Dominant object | density |
|------|---------|-----------|---------|----------|-------|-----------------|---------|
| **Design10** | **`2026`** bold-rounded, one colour | 122.5 × 66.1 | 1 — **Orange** `(255,153,51)` | 5 992 | 5 | **contour/radial fill**, whole digit (rev 26 %, med 3.3 mm) | 0.74 |
| **Design15** | **`2026`** blackletter, shaded | 128.5 × 46.0 | 2 — **Black** `(0,0,0)` + **White** keyline (27 alternating blocks) | 7 386 | 11 | **satin strokes** (main strokes rev 79 %, med 2.3 mm) + white inline | 1.25 |
| **Design2** | single ornate **`1`** | 75.6 × 81.8 | 1 effective — coral `(255,139,147)` (3 other cones degenerate ≤4 pts) | 3 381 | 2 | satin-filled solid digit | 0.55 |
| **1212** | **font specimen**: `1` digits in 3 styles/colours, scattered with big jumps | 529.3 × 296.6 | 4 — Black · White · Pink · White | 16 947 | 0 | satin, **OUTLIER** (a sampler, not one composition) | 0.11 |

**Reading → the numbers DNA:**

- **Size:** a year string (`2026`) is **~120–130 mm** wide so each stroke lands the
  letters band **~2–4 mm**; a single digit is **75–80 mm**. `1212` (529 mm) is a *specimen
  sheet*, not a target size — ignore it for sizing.
- **Palette = 1–3**, one thread per element colour. One-colour numbers are common
  (`Design10`); the second/third colour is a **white inline keyline** or a **3-D edge**.
- **Object follows stroke width:** chunky rounded digits **fill** (`Design10`, only 26 %
  reversals = serpentine fill); thin serif/script digits **satin** (`Design15`, 79 %
  reversals on the main strokes = satin sheen). The `_SATIN_MAX_WIDTH_MM = 3.0 mm`
  classifier routes each automatically.
- **Areal density** lands **0.5–1.6 st/mm²** for covered digits — inside the gate band
  (0.3–15). `Design10`'s contour fill is sparser (0.74), `Design15`'s packed satin denser
  (1.25).

---

## 2. The core recipe — three number sub-styles ⭐⭐

Numbers come in **three flavours**; pick by how the digits are drawn. (Sew order in every
case is **back-to-front**: 3-D edge / shadow → body → inline keyline / highlight.)

### 2A · Solid block / bubble number (`Design10`; photo 2)
Bold rounded or block digits, one flat colour (± a white inline). The bodies are chunky
blobs → they **fill**.
- **`--purify-colors`** (solid-fill mode — keeps colours, no satin shatter). **Never
  `--lettering`** on rounded/bubble digits: it dissects them into stroke columns and
  **shatters** the round body (the [[lettering-mode-vs-purify]] trap — same as bold caps).
- `auto_fill` (default); `--open-counters` (auto-on with purify).

### 2B · Brush / script number (photo 1)
Thin sprawling hand-lettered digits, usually one colour (black).
- **`--purify-colors`**, **never `--lettering`** (shatters cursive — [[lettering-mode-vs-purify]]).
- **`--fill-method contour_fill`** — `auto_fill`'s travel routing over-stitches / hangs on
  long thin sprawling strokes ([[contour-fill-for-calligraphy]]); contour follows the stroke.
- Single colour; `madeira-polyneon` (black is ΔE 0 on either chart).

### 2C · Shaded / outlined / 3-D number (`Design15`; photo 3)
A digit **face** + a **white inline keyline** + optionally a **3-D extruded edge** or
**drop-shadow**. Sewn per-digit, back-to-front.
- **`--thread-chart isacord`** for the bright face colour (§3); **snap the face to a crisp
  solid mask first** (§5.3, [[halftone-face-flatten]]) — a halftone/sequin face traced raw
  goes **spiky and sheared**, not just hollow.
- **The cleanest faithful pass is the face-only solid numeral** (drop the rim + inline,
  keep counters open) — a crisp bright-red `2027` reads true. If you want the white inline,
  keep it as the **open page-colour** between face and rim (`--open-counters` leaves a clean
  white line for free, no third thread).
- **The 3-D extrude / drop-shadow is a Phase-B hand-finish.** Tracing it as a *second
  dark-red* fought the palette: it either merged into the face (purify snaps both reds to
  pure) or muddied the whole numeral into brown (no-purify → face `Poinsettia ΔE 7` + rim
  `Burnt Orange ΔE 11`). **Ship the clean bright-face numeral and lay the dark 3-D keyline
  by hand in Wilcom**, sewn *first* (a back facet — the 3D painter's order applied to
  type; §7, ties to the 3D doc).

Per digit-part, the playbook §0a classifier with the widths measured here:

| Digit region | Object | Settings |
|--------------|--------|----------|
| Chunky rounded / block body ≥ ~3 mm (`Design10`, bubble) | **fill** (tatami/`auto_fill`) | row 0.4 mm; underlay; one continuous fill per digit |
| Serif / script / brush stroke, ~2–4 mm (`Design15`, photo 1) | **satin column** | follows the stroke; pull-comp 0.2 mm |
| White inline keyline / hairline | **open page-colour** (drop) or thin satin | `--open-counters`; if stitched, ≥ 1.2 mm |
| 3-D extrude edge / drop-shadow | **its own colour, sewn FIRST** (or Phase-B) | a back facet — painter's order |

---

## 3. The thread chart IS a number lever — `isacord` for bright digits ⭐⭐

Same rule as simple shapes. Bright primary digits (a **blue** bubble, a **red** varsity)
need **Isacord**; **Madeira Polyneon has no pure blue (ΔE 90)** and a poor red (ΔE 14).
Black/grey/muted script stays on **madeira-polyneon**. Measured on the `2027` photos:

| Photo digit colour | madeira-polyneon | **isacord** |
|---|---|---|
| photo 3 red face `(255,0,0)` (after purify) | poor | **Poppy ΔE 0.0** ✓ |
| photo 2 sky-blue `(65,167,244)` | — (no pure blue) | **Reef Blue ΔE 9.8** ✓ |
| photo 1 black `(0,0,0)` | Black ΔE 0 ✓ | Black ΔE 0 ✓ |

### Colour rule: purify ONLY true pure primaries — keep custom mid-tones verbatim ⭐
The same measured trap as simple-shapes §3 / letters §8b. **Purify on photo 2's sky-blue
pushed it `(65,167,244) → (0,146,255)` and the match WORSENED from `Reef Blue ΔE 9.8` to
`Cerulean ΔE 19`.** A sky-blue is a *custom mid-tone*, not a pure primary → **drop
`--purify-colors`, use `--open-counters` directly** to keep counters open without the
colour snap. Purify *is* right when the digit colour is a **true primary** (photo 3's red
→ pure `(255,0,0)` → Poppy ΔE 0) or you want solid-fill mode on block digits (§2A).

---

## 4. Fill method — `auto_fill` for block digits, `contour_fill` for script ⭐
- **Block / bubble / rounded digits** (`Design10`, photo 2): **`auto_fill`** (default) —
  one clean serpentine per compact digit body.
- **Brush / script / long-thin digits** (photo 1): **`--fill-method contour_fill`** —
  `auto_fill` over-stitches and can hang on sprawling strokes ([[contour-fill-for-calligraphy]]).

---

## 5. Preparing the source photo (what to feed the pipeline)
1. **Flat, clean, hard-edged colour on a clean ground.** Crisp vector-style art, not a
   photo. Anti-alias haloes spawn phantom cones.
2. **Composite transparency onto white first.** `2027/3.png` had a **transparent** ground
   → a naïve `convert('RGB')` makes it *black* and the whole design sews on a black field.
   Always `alpha_composite` over white before quantizing.
3. **⭐ Snap the digit art to a crisp SOLID-COLOUR mask before tracing — do NOT feed the
   raw textured / anti-aliased picture.** This is the single biggest number-quality lever,
   and it fixes **two different failures with the same move**:
   - **Textured face → spiky, sheared, illegible.** Photo 3's red face was stippled with
     white stars; traced raw it produced **spurious satin columns that fan out as long
     radial spikes** and the digits mush together. (First attempt: 17 phantom satins,
     unreadable.)
   - **Anti-aliased bold art → fattened & blocky.** Photo 2's blue bubble traced raw pulled
     the soft anti-alias halo into the blue, **swelling every stroke and shrinking the
     counters** so the bubble curves read heavy and the first `2`'s bowl half-closed.

   **The fix (recipe in `tools` / shown below):** build a binary mask of the *true* ink
   (e.g. `(B>140)&(B-R>40)` for the blue; `(R>150)&(R-G>45)` for the bright red face),
   `binary_closing` to bridge small gaps (a ~5-px close fills halftone stars but NOT a
   wide inline keyline or a real `0`-counter), `binary_opening` to despeckle, then
   **repaint solid** in one clean, *bright* ink colour and render on white. Use a **bright
   pure** ink so it lands a clean cone (red → Poppy ΔE 0; not the muted median
   `(190,48,48)→Cardinal ΔE 9.6`). The worked sources are `output/2_clean.png` and
   `output/3_clean.png`. See [[halftone-face-flatten]].
   - **⭐ Drop stray components or they become auxiliary stitches that DEFORM the design.**
     A textured-face flatten leaves crumbs — bits of the 3-D rim / drop-shadow that leak
     into the mask as small disjoint blobs. Traced, each becomes its own fill piece + trim,
     and they read as **stray underlines / specks** hanging off the digits. Filter the mask
     **by connected-component shape**: real digit parts are **tall** (h ≳ 300 px here);
     the strays are **wide-and-short baseline bars** (h ≈ 34–73 px) and tiny specks. A
     `height > 180 px` keep-filter removed exactly the 3 deforming bars on photo 3 (11→8
     trims, the spiky/underline crumbs gone) while keeping all 7 real digit parts. **Always
     render the actual stitches (`render_vp3.py`), not just the colour preview, and check
     for span ≤ 15 mm "small pieces" — those are the deformers.**
4. **Count the element colours → `--colors N` (1–3).** Ground drops automatically.
5. **Pick size so the narrowest stroke lands ~2–4 mm.** Year string `--width-mm 115–130`;
   single digit `--width-mm 75–80`.
6. **`--thread-chart isacord`** for bright digits (§3); **`--open-counters`** always
   (digits `0 4 6 8 9`); `--fill-method contour_fill` only for script (§4).

**The calibrated production commands (the three worked `2027` examples):**

```bash
# 1 · brush SCRIPT number (black, one colour) — clean hi-res art, trace directly
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline numbers/output/1.jpg \
    --width-mm 115 --colors 1 --thread-chart madeira-polyneon --purify-colors \
    --fill-method contour_fill --name num1_script --output-dir numbers/output

# 2 · bold BUBBLE number — snap blue to a CRISP SOLID mask first (2_clean.png, §5.3),
#     then trace. NO purify (custom sky-blue); open the counters.
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline numbers/output/2_clean.png \
    --width-mm 120 --colors 2 --thread-chart isacord --open-counters \
    --name num2_bubble --output-dir numbers/output

# 3 · VARSITY number — snap the HALFTONE face to a CRISP SOLID red mask first
#     (3_clean.png, §5.3: face only, stars filled, counters kept), then trace.
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline numbers/output/3_clean.png \
    --width-mm 120 --colors 2 --thread-chart isacord --purify-colors \
    --name num3_varsity --output-dir numbers/output
```

(The console script `wilcom-pipeline` is stale — always invoke via
`PYTHONPATH=src .venv/bin/python -m wilcom_pipeline`; see [[pipeline-run-stale-venv]].)

**Worked examples shipped in [`output/`](output/)** (all gate **PASS**):

| Output | Source | Threads | Stitches | IoU / source-covered |
|---|---|---|---|---|
| `num1_script_pro.vp3` | brush `2027` (`1.jpg`) | Black (ΔE 0) | 2 731 | **88.6 % / 99.3 %** |
| `num2_bubble_pro.vp3` | blue bubble (`2_clean.png`) | Reef Blue (ΔE 9.6) | 2 532 | **79.1 % / 90.9 %** |
| `num3_varsity_pro.vp3` | red varsity (`3_clean.png`) | Poppy (ΔE 0) | 2 617 | **72.6 % / 99.8 %** |

(IoU vs the **original** `2.jpg` for the bubble is held down only by the photo's white
outline + grey drop-shadow we don't stitch; vs the cleaned source it's tighter. Both
single-cone outputs are crisp — one path per digit, counters open.)

---

## 6. Compare-to-original & iterate — the mandatory last step ⭐⭐

**Before delivering any number, render the output and measure it against the source
photo; iterate until the drift is explained or gone.** (Standing directive
[[compare-output-to-original-iterate]]; tools in [`tools/`](tools/):
`analyze_vp3.py`, `render_vp3.py`, `vp3_to_photo.py`, `compare_to_photo.py`.)

What "good" looked like on the three `2027` jobs, and **how each drift was explained**:

- **Brush script (photo 1) — IoU 88.6 %, covered 99.3 %.** Near-perfect overlay
  (all-purple); the only source-only red is the **stock watermark** in the photo, correctly
  *not* stitched. Counters of `0` open. Flawless on the first pass (clean hi-res art).
- **Blue bubble (photo 2) — IoU 79.1 %, covered 90.9 %.** The ~9 % gap vs the original
  `2.jpg` is its **white outline halo + grey drop-shadow**, dropped by design. Reef Blue is
  the closest isacord cone to a sky-blue (ΔE 9.6 — the colour sits between cones, not a
  fault). **This one took an iteration** (see below).
- **Red varsity (photo 3) — IoU 72.6 %, covered 99.8 %** against the cleaned source. **This
  one took a major iteration** (see below); the 3-D extrude depth is dropped as a Phase-B
  hand-finish (§2C, §7).

**The two iterations — the directive in action.** Both first passes *traced the raw
textured/anti-aliased picture* and both failed; **comparing the preview to the original
caught it, and the same fix (§5.3, snap to a crisp solid mask) rescued both**:

- **Photo 3 was catastrophic first** — tracing the halftone star-field raw produced
  **long radial spikes (17 phantom satin columns) and sheared, mushed digits**, barely
  readable. Rebuilding a **face-only solid-red mask** (`3_clean.png`) → **0 satin columns**,
  upright evenly-spaced digits, IoU **49 % → 70.7 %**, coverage **→ 99.9 %**.
- **Photo 2 was subtly wrong** — the raw trace's anti-alias halo **fattened the strokes and
  half-closed the first `2`'s bowl** (blocky, heavy). Snapping to a **crisp solid-blue
  mask** (`2_clean.png`) → smooth bubble curves, white highlight cuts preserved, **one path
  per digit, 25→5 trims**.

**A low IoU is a prompt to LOOK, not an automatic fail** — explain it (watermark, dropped
shadow, omitted 3-D depth) or *fix the source* (snap to a solid mask if spiky/blocky,
enlarge if a stroke clipped, re-quantize if a counter filled). **Never ship the first
render of textured number art without eyeballing it against the original.**

**Checklist before export:**

- [ ] Subject framed as a clean numeric string / digit; transparency composited on white (§5.2).
- [ ] Palette **1–3 colours**; **`--thread-chart isacord`** for bright digits, madeira for black/muted (§3).
- [ ] **`--purify-colors` only for true pure primaries** or block-digit solid-fill; **drop it for custom mid-tones** (§3).
- [ ] **`--open-counters`** — every `0 4 6 8 9` reads through (§0).
- [ ] Object per digit-part by width: rounded body→fill, serif/script stroke→satin (§2).
- [ ] **`--fill-method contour_fill`** only for brush/script digits (§4).
- [ ] **Textured / halftone / anti-aliased digit art snapped to a crisp solid mask** before
      tracing — else spiky (textured) or fattened/blocky (anti-aliased) (§5.3).
- [ ] Narrowest stroke **≥ ~2 mm** at final size; year string ~115–130 mm (§5.5).
- [ ] Sew order **3-D edge / shadow → body → inline keyline last** (§0, §2C).
- [ ] Trims ≈ disjoint digit parts; fragmentation gate < 5 %.
- [ ] **Thread metadata stamped** — named cone in the VP3 (letters §8).
- [ ] **`compare_to_photo.py` run**, coverage ≥ ~92 %, **every drift explained**, preview clean (§6).
- [ ] Size set once via `--width-mm`; don't rescale the `.vp3` afterward.

---

## 7. Honest boundary — traced face vs hand-built 3-D depth ⭐

The references and photos show two finishes a raster tracer can't fully reach, both
inherent to tracing a flat picture — neither a bug:

1. **The 3-D extrude / shaded depth** (`Design15`'s engraved white inline, photo 3's
   dark-red side). A faithful **bright-face numeral with open counters** is production-correct
   and clean; the **depth** — a dark keyline sewn *first* under the face — is best added by
   hand in **Wilcom (Phase B)**, exactly as the [`../3D/3d-embroidery-knowledge.md`](../3D/3d-embroidery-knowledge.md)
   doc *builds* facets rather than tracing them. Forcing a second dark cone via the tracer
   muddied the palette (§2C).
2. **Hand-satin sheen on serif/script strokes** (`Design15`'s 79 %-reversal satins). The
   tracer fills broad bodies and satins thin strokes by width; for the directional satin
   *sheen* on every stroke, lay satin columns by hand in Wilcom — or, because a year is a
   *known string*, **type it in Wilcom's satin lettering tool** (playbook §4: a known
   numeral beats tracing a picture of it).

**The real production rule:** the `.vp3` this pipeline emits for a number is a
**byte-faithful, clean, density-accurate, counter-open editable intermediate** — an
excellent stitch-out and a strong Phase-B starting point. Trace when the numeral exists
only as an image; type/hand-finish when you want typeset satin sheen or a 3-D edge.

---

## 8. Provenance & how to reproduce
- Files parsed with `pyembroidery`; satin-vs-fill via consecutive-segment turn-angle
  (> 120° = reversal); pieces split on `TRIM`/`COLOR_CHANGE`. Scripts in [`tools/`](tools/)
  (copied from simple-shapes, identical methodology).
- End-to-end calibration: the three supplied `2027` photos → flatten/composite (§5) →
  `python -m wilcom_pipeline` (recipe §5) → `compare_to_photo.py` against each source.
  Worked outputs + overlays in [`output/`](output/).
- Consistent with [`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md) (numbers = the
  LETTERS branch) and the cross-cutting `.vp3`/thread reference (letters §7–§8). The
  digit-specific additions are **open the digit counters `0 4 6 8 9`**, **isacord for
  bright digits / purify only true primaries**, **flatten textured faces**, and **the 3-D
  edge is a sewn-first back facet (Phase-B hand-finish).**
</content>
</invoke>
