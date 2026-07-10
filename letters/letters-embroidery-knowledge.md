# Letters / Name-Calligraphy Embroidery — Production Knowledge

> **Routing:** which category a photo belongs to, and the rules common to letters /
> 3D / anime, live in [`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md). This
> file is the **letters domain detail** it points to.

Distilled from **11 reference `.VP3` files** the user supplied as production examples
(`1000`–`8000`, plus the ground-truth calibration set `10000`, `11000`, `12000`),
parsed byte-for-byte with `pyembroidery` and cross-checked against the VP3 binary
format (pyembroidery's own reader/writer). Every number below is **measured from the
actual files**, not guessed.

The category is **any word/name rendered beautifully** — Arabic calligraphy, Latin
monograms, block/display capitals, hand-lettered phrases, logos with text. The single
governing fact, now confirmed across the whole calibration set, is **§0 below**.

## 0. The one rule for this category: letterforms are SATIN ⭐⭐

Across **every** ground-truth file whose subject is letters (10000, 11000, 12000, and
11 of 13 colour blocks in 1000–8000), **100 % of the letterform blocks are satin —
zero tatami fills.** A *background panel* behind text can be a tatami fill; a
**letter, of any weight or size, is always satin.** Three satin idioms appear:

- **Stroke satin** (calligraphy / script): each connected stroke is a satin column;
  disjoint loops/dots end in trims.
- **Filled-face satin** (solid display caps, e.g. 12000 "ADVENTURE"): the cap face is
  packed with satin columns ~3–4 mm wide; if it carries a 3D edge, a **keyline colour
  is offset behind and sewn first** (painter's order — see §8b, links to `3D/`).
- **Outline satin** (open/outlined caps, e.g. 11000 "SENIOR"): only the glyph outline
  is satined, interior left open.

Everything else in this file is *how* to realise that with a photo tracer and where it
falls short of true Wilcom satin lettering.

> This file has two halves: **§1–§6** are the *letters-category recipe*; **§7 (VP3
> binary format) and §8 (thread metadata)** are *cross-cutting* — they apply to
> **every** category (`anime/`, `3D/`, future ones), because they describe the file
> container itself, not the artwork.

---

## 1. What the reference files are (measured)

| File | Size (mm) | Colours | Threads — `rgb (catalog#, brand, name)` | Stitches | Trims | Dominant object |
|------|-----------|---------|------------------------------------------|----------|-------|-----------------|
| 1000 | 140.0 × 77.6 | 2 | (0,0,0) `8,Default,Black` · (255,126,204) `15,Default,Pink` | 16 286 | 15 | **satin** |
| 2000 | 64.5 × 55.3 | 1 | (115,85,3) `—,—,R115 G85 B3` | 3 759 | 36 | **satin** |
| 3000 | 87.5 × 71.0 | 2 | (255,218,51) `—,—,…` · (0,0,0) `8,Default,Black` | 6 856 | 30 | **satin** |
| 4000 | 165.5 × 59.9 | 2 | (255,242,215) cream · (59,0,0) dark-red | 15 550 | 18 | tatami **fill** + satin |
| 5000 | 99.6 × 66.3 | 2 | (255,1,153) magenta · (0,0,0) `8,Default,Black` | 5 952 | 14 | **satin** |
| 6000 | 88.8 × 55.1 | 1 | (231,120,23) `9,Wilcom,Orange` | 4 762 | 1 | **satin** |
| 7000 | 135.8 × 127.4 | 1 | (0,0,0) `8,Default,Black` | 4 443 | 20 | **satin / run** |
| 8000 | 114.7 × 63.8 | 3 | (56,167,204) blue · (255,255,255) `9,Default,White` · (0,0,89) navy | 13 354 | 32 | fill + **satin** |
| **10000** | 57.8 × 68.8 | 2 | (0,0,0) Black · (255,0,0) Red | 3 439 | 12 | **satin** (block caps "LET'S CELEBRATE") |
| **11000** | 63.0 × 32.0 | 2 | (255,0,0) `3,Default,Red` · (0,0,0) `8,Default,Black` | 4 643 | 22 | **all satin** — outline caps + red script |
| **12000** | 140.0 × 104.5 | 3 | (255,255,0) `4,Default,Yellow` · (42,133,143) teal · (0,0,0) `8,Default,Black` | 14 738 | 57 | **all satin** — filled-face caps + keyline + cursive |

**Reading of the table → the category's design DNA:**

- **Size:** medium, **~65–165 mm wide**. Name designs are not tiny; the large
  script needs room for satin strokes.
- **Palette is tiny: 1–3 colours.** Most are 1–2 (the letters + an outline/shadow).
  Keep `--colors` low (≈2–4).
- **The dominant object is the SATIN column.** Detecting zigzag reversals
  (consecutive-segment turn-angle > 120°), **11 of 13 colour blocks are satin**
  (45–84 % reversals). The two exceptions are *solid panels* — 4000's cream
  background and 8000's blue field — which are **tatami fills**. ⭐ This is the
  single most important fact: **letter strokes = satin, solid areas = tatami fill.**
- **Satin width** (≈ median cross-segment length): **1.2 – 3.8 mm**. That is the
  width band of the strokes in these names. Anything thinner reads as a lump
  (see §3) → run/triple-run instead.
- **Trims:** modest but real (1–36). Each disjoint stroke/diacritic ends in a trim
  (a clean Wilcom *Break-Apart* boundary). A connected single-colour script
  (`2000`) still had **36 trims** — Arabic has many disconnected dots, hamzas and
  diacritics, each its own piece.

---

## 2. The core recipe — building a name design

Sew order is strict **back-to-front** (same painter's algorithm as `3D/` and
`anime/`):

1. **Solid background panel** (if any) → **tatami fill**, ~0.4 mm rows, underlay on.
2. **Letter bodies** → **satin columns**, one per stroke, in the body colour.
3. **Outline / shadow colour** (often black) → satin or run, on top of the bodies.
4. **Diacritics, dots, small detail** → short satin or run, near the end.
5. **Any border / frame → last** (covers the connecting threads).

Per object:

| Object | Stitch type | Settings (measured / best-practice) |
|--------|-------------|--------------------------------------|
| Letter stroke (1.6–4 mm wide) | **satin column** | pull-comp 0.2 mm; `trim_after` between disjoint strokes |
| Display letter / solid panel (≥ ~5 mm, branching) | **tatami fill** | row 0.4 mm; fill underlay; pull-comp 0.2 mm |
| Thin flourish / subtitle text (< ~1.6 mm) | **run / triple-run** | ~2.2 mm run; triple for a bolder line |
| Small figure/illustration (e.g. the girl in `ritaj`) | flat fills + satin outline | treat like an `anime/` mini-portrait |

This maps **exactly** onto the existing pipeline (`steps/stitches.py`): a colour
whose median stroke width is `< 3 mm` is auto-classified "linework" and its clean
single-centerline strokes become real satin columns (`fill_to_stroke` →
`stroke_to_satin`); branching shapes stay **one continuous fill** (never shattered);
everything gets underlay + pull-comp + `trim_after`. **No code change is needed to
route a letters photo correctly** — the satin classifier already does it.

---

## 3. Minimum width — the rule that makes or breaks letters ⭐

A satin has a minimum workable width (~1.2 mm); below it the needle penetrations
collide and it reads as a lump, and the pipeline's step-2 consolidation (1.2 mm)
**erases** sub-floor strokes before they're ever stitched. The reference satins sit
at **1.2–3.8 mm** — right above the floor.

**Therefore, when preparing a name photo:** the strokes must be **≥ ~1.6 mm in the
final size**. For Arabic calligraphy this usually holds for the main name but
**fails for the thin subtitle line** (`ritaj`'s lower text) and hairline flourishes
— expect those to either drop out or need bolding/enlarging, or to be accepted as
run-stitch. Step 1 warns when the smallest feature is below ~1.2 mm; heed it.

---

## 4. Arabic / cursive specifics

- **RTL is irrelevant to stitching** — the design is geometry; sew order is by
  layer/enclosure, not reading direction.
- **Connected cursive = long satin runs with many branch points.** A whole word is
  one connected blob of strokes; the pipeline keeps a branching block as **one
  continuous fill** rather than fragmenting it (machine-friendly). A cleaner result
  comes from letters whose strokes are *separable* into single columns.
- **Diacritics / dots (ـِ ـُ نقاط):** small disjoint pieces → each ends in a trim.
  This is why even a 1-colour Arabic name shows 20–36 trims. That's normal, not a
  fragmentation failure — but the step-7 gate counts trims, so very dotty scripts
  can approach the 5 % gate; keep the name reasonably large.
- **Decorative fills** (the swash/leaf ornaments common in these designs) → tatami,
  their own colour, sewn before the letters they sit behind.

---

## 5. Preparing the source photo (what to feed the pipeline)

1. **Flatten to few colours** with a clean, separable background (the name on a
   plain field). The background is *dropped*, not stitched.
2. **Bold the main strokes** to ≥ 1.6 mm equivalent at the chosen `--width-mm`.
3. **Crisp dark edges** survive as satin/run linework and hold the shape.
4. Pick size so the **main name strokes land in the 1.6–4 mm satin band**:
   - short name (3–5 glyphs): `--width-mm 90–120`
   - long phrase / with subtitle: `--width-mm 140–165`
5. `--colors 2–4`, `--thread-chart madeira-polyneon` (or `isacord`).

Run, exactly like the other categories:

```bash
.venv/bin/wilcom-pipeline letters/ritaj-name.png \
    --width-mm 120 --colors 4 --thread-chart madeira-polyneon \
    --name ritaj --output-dir letters/output
```

Expect: a **simplified** result — flat fills + satin/run letters. The pipeline does
not reproduce hand calligraphy weight modulation or the illustration's shading;
that stays a Phase-B / human refinement. The thin subtitle line may not survive
(see §3) — if the name itself is clean, that's a PASS for this category.

---

## 6. Letters-category checklist (before export)

- [ ] Palette **1–4 colours**; background separable & dropped.
- [ ] Main strokes **≥ 1.6 mm**, inside the **1.2–3.8 mm** satin band (§3).
- [ ] Letter strokes route to **satin**; solid panels to **tatami fill** (§1, §2).
- [ ] Sew order **panel → letters → outline → diacritics → border last** (§2).
- [ ] Underlay on fills; **pull-comp 0.2 mm**; `trim_after` on disjoint pieces.
- [ ] Trims modest (diacritics excepted); gate fragmentation < 5 %.
- [ ] **Thread metadata stamped** into the VP3 (cone code + name + chart) — §8.
- [ ] Size set once via `--width-mm`; don't rescale the `.vp3` afterward.

---

# Cross-cutting reference (applies to every category)

## 7. The `.vp3` binary format — what we actually write ⭐

`.vp3` is the **Husqvarna Viking / Pfaff** ("VSM" — *Viking Sewing Machines*)
format. All 8 references begin with the magic `%vsm%` and the producer string
**"Produced by ⎵⎵⎵⎵⎵ Software Ltd"** (the brand is space-masked; Wilcom emits this
same VSM string). The layout, confirmed from `pyembroidery`'s `Vp3Reader`/`Vp3Writer`
and verified by a **read→write→read round-trip on all 8 files** (see below):

```
%vsm%\0
UTF-16BE str   "Produced by     Software Ltd"
00 02 00  <int32 offset-to-end>            ← FILE block
UTF-16BE str   ""                          ← global notes/settings ("Setting:" …)
int32×4        bounds: right, -top, left, -bottom        (×100)
int32          stitch count (minus END)
… colour-block count, flags …
  00 03 00 <int32>  center_x, -center_y, extents…        ← DESIGN block
  "xxPP" 01 00
  UTF-16BE str "Produced by     Software Ltd"
  int16  colour-block count
    00 05 00 <int32>  start-from-centre x,y               ← COLOUR block
      THREAD:  01 00 | RGB(24b) | 00 00 00 05 28 (Rayon 40wt) |
               str8 catalog# | str8 description | str8 brand
      block-shift x,y
      00 01 00 <int32>  0A F6 00                           ← STITCH block
         signed-byte dx,dy pairs  (1 unit = 0.1 mm)
         80 03                = TRIM
         80 01 <16be dx><16be dy> 80 02 = long stitch (|d| > 127 = >12.7 mm)
      00 (block terminator)
```

Key facts that govern how we generate VP3:

- **Big-endian** integers throughout; strings are length-prefixed (UTF-16BE in the
  header, UTF-8 in the body).
- **Stitch unit = 0.1 mm.** Single-byte delta range is **±127 = ±12.7 mm**; longer
  moves use the `80 01 … 80 02` escape. So our internal "1 unit = 0.1 mm" assumption
  (e.g. `emit._render_preview`, `stitches._print_summary`) is correct.
- **Y is stored negated** (file is y-up; pyembroidery reads to y-down). Designs are
  upright — do **not** double-flip in previews (a fixed bug; see `anime/README.md`).
- **VP3 has no JUMP command.** pyembroidery's writer *drops* `JUMP` (the needlebar
  just moves); only **TRIM** (`80 03`) exists as a connector. So jumps in our
  pattern silently become plain moves — fine, but it means "jump count" is
  meaningless in a written VP3.
- **`END` is written as a trailing trim** (`80 03` + break). This is why a
  round-trip shows **+1 trim** vs the original (16 vs 15, etc.) — a harmless writer
  artifact, not corruption.

### Round-trip fidelity (proof our writer is production-valid)

Reading each reference and re-writing it with `pyembroidery.write_vp3` reproduces it
**within ±2 bytes** and re-reads **identically**: same stitch count, same command
histogram (+1 trim from END), bounds within ±1 unit (0.1 mm integer rounding), and
**all thread metadata preserved** (RGB + catalog# + description + brand). ⇒ A VP3 we
emit is byte-faithful to what Wilcom/Husqvarna produced. **No custom VP3 writer is
needed** — `pe.write_vp3` is the trusted path for all categories.

## 8. Thread metadata — carry the cones into the VP3 ⭐

The reference threads carry three string fields per colour:

| Field (`EmbThread`) | Reference values seen | We now write |
|---|---|---|
| `catalog_number` | `8`, `15`, `9` (needle/chart index) or empty | cone **code** (e.g. `1801`) |
| `description` | `Black`, `Pink`, `Orange`, `White`, or auto `R115 G85 B3` | cone **name** |
| `brand` | `Default`, `Wilcom`, or empty | **chart** (e.g. `Madeira Polyneon`) |

Two valid styles appear in the wild: **named cones** (`8,Default,Black`) and **bare
RGB** (empty catalog/brand, auto name `R115 G85 B3`). Both open fine.

**Gap that was fixed:** Ink-Stitch leaves these fields unset, and the old
`emit.py` wrote the VP3 with bare RGB threads — the matched cone codes lived only in
the side-car `threadlist.txt`, not in the file Wilcom opens. `emit._stamp_thread_metadata`
now stamps each thread's `catalog_number`/`description`/`brand`/`chart` from step-3's
`thread_map` (matched by RGB, nearest-RGB fallback) **before** `write_vp3`, so the
VP3 itself names its cones — exactly like the references. Verified to survive the
write→read round-trip.

---

## 8a. Calibration against a ground-truth file (`10000.VP3` vs my first output) ⭐⭐

The user supplied **`letters/10000.VP3`** as the *production-ready* version of
`letters/output/9000.png` ("LET'S CELEBRATE" block capitals, black + red). Comparing
it to my first machine output exposed the **single biggest mistake**:

| Aspect | **Production `10000.VP3`** | My first output (`lets_celebrate_pro.vp3`) | Lesson |
|---|---|---|---|
| Object type | **SATIN columns** (74–76 % reversals) | **tatami FILLS** (3–5 % reversals) | ⭐ letters = satin, *even bold block caps* |
| Stitches | **3,439** | 14,336 (**4.2×**) | satin is far leaner than filling the glyph |
| Size | **57.8 × 68.8 mm** | 110.7 × 143.8 mm | small enough that strokes are satin-width |
| Satin width | ~3.4 mm median | — | the stroke *is* the satin column |
| Threads | **pure Black (0,0,0) + Red (255,0,0)**, `Default` chart | gray (97,93,86) + (226,62,40), Madeira | snap inks to the *intended* colour, not render sheen |
| Trims | 12 | 23 | fewer pieces = fewer cuts |

**Why I got it wrong, and the corrected rules:**

1. **Block capitals are SATIN, not fills.** My §1–§2 said "solid panels = tatami
   fill" and I over-applied it to bold letters. A *background panel* is a fill; a
   **letter stroke is always a satin column**, however bold. Each glyph is
   **dissected into its straight/curved stroke-columns** (the "despiece" of
   `anime/best-practices.md` §L) and each stroke satined. `E` = spine + 3 arms (4
   columns); `B` = spine + 2 bowls; etc.

2. **Size sets the stroke width — keep strokes in the ~2–4 mm satin band.** The pro
   sized the design to **~58 mm**, which puts the strokes at ~3.4 mm — a clean satin
   width. My 110 mm pushed strokes to ~6 mm, above the old 3 mm satin threshold, so
   they fell back to tatami fill and the stitch count exploded. **Lesson: choose
   `--width-mm` so the letter strokes land ~2–4 mm, or raise the satin-width ceiling
   so wide strokes still satin.**

3. **Snap inks to pure/intended colour.** The source is a *stitch render* whose black
   has sheen; 2-colour quantization averaged it to gray (97,93,86) → matched
   `Black Chrome`. Production used **pure Black + pure Red**. For lettering, push a
   near-neutral dark ink to true black and a saturated ink to full chroma before
   thread-matching.

4. **The production tool was almost certainly Wilcom *lettering* (a satin font)**,
   not a photo trace — which is why it's so lean and exact. A photo-tracer (this
   pipeline) can only *approximate* it by dissecting strokes into satins. For real
   typeset words, **typing the text in Wilcom's lettering tool beats tracing a
   picture of it** — keep that as the Phase-B option when the input is plain text.

**Pipeline change made in response:** a **lettering mode** (`--lettering`) that
(a) raises the satin-width ceiling so block-letter strokes satin instead of fill,
(b) **dissects each colour block into multiple satin columns** (every substantial
centerline becomes its own satin, not just the single-column case), and (c) snaps
each ink to its pure colour (near-neutral dark → black; saturated → full chroma).
Run block-letter / typeset designs with `--lettering` and a size that keeps strokes
~2–4 mm. Expect a satin result with a stitch count in the low thousands, not tens of
thousands.

> The earlier §1 table still holds for **calligraphy** (Arabic script, `ritaj`):
> those connected cursive strokes branch heavily and the *non-lettering* path keeps
> them as continuous fills + a few clean satins. `--lettering` is for **separable
> block/typeset glyphs**, where per-stroke satin dissection is the production norm.

**Regeneration outcome (measured) & the honest limit.** Re-running `9000.png` with
`--lettering --width-mm 58 --colors 2` flips the object type to **satin** (it went
0 → 62 satin columns), renders **true black + red** (pure inks, not the sheen-gray),
and lands at the production size. The fully-visible top row (**"LET'S"**, the **"C"**)
comes out clean. **But two things keep a raster trace below typeset quality:**

1. **Junction-heavy / cut-off glyphs fragment.** `9000.png` is a *crop* — the lower
   letters run off the right edge, so they trace as partial glyphs whose medial-axis
   skeleton splinters into mis-shaped satin pieces. Skeleton→satin is clean for
   simple, complete strokes (L, T, I, C) and rough for branchy or clipped ones.
2. **Dissected columns overlap → over-stitch.** Density came in ~2.0 st/mm² vs the
   production ~0.86; the many narrow satins double-cover at junctions.

**Conclusion (the real production rule):** a photo-tracer *approximates* block
lettering; it does not equal **typeset satin lettering**. The ground-truth `10000.VP3`
(3,439 st, exact satins, pure colour) was almost certainly made by **typing the text
in Wilcom's lettering tool with a satin font** — the right production workflow for any
*known word*. So: for clean block/typeset text, **type it in Wilcom (Phase B)** rather
than trace a picture of it; reserve the trace pipeline (`--lettering`) for when the
lettering only exists as an image, and expect to hand-tidy the branchy glyphs.

**Second test — `patience-tested.jpeg` ("PATIENCE" ornate green caps + "Tested" black
cursive), and when NOT to use `--lettering`.** ⭐ Running it *with* `--lettering`
**shattered** both words into disjoint satin fragments (illegible) and the pure-ink
snap made the green neon — because the caps are *ornate* (serifs/swashes/curves) and
the script is *cursive*, both junction-heavy. Running it on the **default path** (no
`--lettering`) produced a **clean, legible, colour-accurate** result (continuous fills,
real cones: `1749 Medium Green` + `1800 Black`, 11.3k st, 0.97 st/mm², gate PASS).
**Decision rule:** `--lettering` is only for **plain, separable, complete block
glyphs**. For *ornate display caps, cursive/script, connected calligraphy, or any
crop with partial glyphs*, use the **default path** — accurate fills beat fragmented
satins. (Watch for a thin dark bar if the source JPEG has a hard top/bottom edge — crop
the source border first.)

## 8b. Second calibration set (`11000` + `12000.VP3`) — all-satin & multicolour display ⭐⭐

A second ground-truth pair sharpened the rules. **`12000.VP3` is the production master
for `let-the-adventure.jpeg`** ("Let the ADVENTURE Begin"): rendering its stitches
reproduces the photo exactly. `11000.VP3` is a graduation design (open/outline display
caps + a red script word). Both, like `10000`, are **100 % satin** (70–76 % turn-angle
reversals in *every* colour block — see §0). Generalised lessons, decoupled from these
specific photos:

1. **Even bold, multicolour, 3-D-edged display lettering is all satin.** 12000 has no
   tatami anywhere — the chunky teal "ADVENTURE" faces are *filled with satin columns*
   (median ~3.7 mm), not tatami. Confirms §0 at the hardest case.

2. **A keyline / 3-D edge is its own colour, sewn FIRST.** 12000's sew order is
   **Yellow → Teal → Black**: the yellow keyline/extrusion and the swash sit *behind*,
   the teal cap faces overlap them, the black cursive script is the top layer. This is
   the **back-to-front painter's order of `3D/`** applied to type — the dimensional edge
   is a *back facet*. So when a design has an offset edge/shadow on its letters, give it
   a separate colour and sew it before the face.

3. **Per-stroke satin width follows the role.** Measured satin segment medians: keyline
   ~1.8 mm < cursive ~2.4 mm < display-cap face ~3.7 mm. Thin accent strokes are tighter
   satins, fat display faces are wide satins. Size the design so each lands in its band.

4. **Colour: snap obvious primaries to pure, keep custom/muted colours verbatim.** 12000
   stored **pure Yellow (255,255,0)** and **pure Black (0,0,0)** as named `Default`-chart
   cones, but kept its **teal as exact custom RGB (42,133,143)** — *not* pushed to neon.
   The signature of a "snap-to-pure" colour is one/two channels maxed and the rest near
   zero (max≈255, min≈0); a muted mid-tone (teal, navy, olive) has a mid-range max and
   must be preserved. `preprocess._purify_ink` now encodes exactly this (low-chroma →
   black/white; near-pure chromatic → full chroma; otherwise unchanged).

5. **Decouple colour-purify from satin-dissection (`--purify-colors`).** The old
   `--lettering` did both, but its satin dissection **shatters cursive/script** (§8a) —
   fatal for a *mixed* design like 12000 (display caps + heavy cursive). The new
   `--purify-colors` flag applies only the colour snap (rule 4) on the **safe default
   fill/satin classification**, so a mixed design gets faithful colours without the
   script fragmenting. Decision: pure block caps → `--lettering`; mixed caps + script,
   or any cursive → `--purify-colors` (or plain default).

**Measured outcome — `let_the_adventure_pro.vp3`** (the test deliverable). Run:
`--width-mm 140 --colors 3 --purify-colors`. Result: gate **PASS**, 20 230 st,
1.55 st/mm², 0.30 % trims; cones **stamped** into the VP3 — `1995 Bright Yellow`
(dE 0.85), `1800 Black`, `1761 Stone Blue` (the teal). Versus the 12000 master:
**layout, colour assignment, and proportions match the photo; the cursive script stays
legible** (the win over `--lettering`, which shattered it). Two honest, documented
drifts: (a) **technique** — my blocks are fills (6–13 % reversals) + a partial-satin
yellow, vs the master's all-satin (70–76 %); (b) **teal saturation** — quantizing the
JPEG to 3 colours lightened the teal to (126,169,169), **dE ≈ 19 from the master's
custom (42,133,143)**, because the photo's anti-aliased teal edges average toward white.
Both are inherent to *tracing a raster*; neither is fixable without guessing the target
colour or hand-satining in Wilcom. Yellow + black snapped cleanly because they are
near-pure (the `_purify_ink` rule); the teal was *kept verbatim* (correctly) and just
quantized light. **Takeaway for custom brand colours: a tracer reproduces a muted custom
colour only as well as the quantizer samples it; for an exact cone, set it in Phase B.**

**Honest boundary (unchanged, reinforced).** 12000's 14.7 k exact satins were made in
**Wilcom's satin lettering tool** (typed font + hand-digitized swashes), not a trace.
A raster tracer can match the photo's *look* and *colours* closely on the default path,
and can satin clean block caps with `--lettering`, but it **cannot** make connected
cursive all-satin without fragmenting. For a *known* phrase, type it in Wilcom (Phase B);
trace only when the lettering exists solely as an image. See
[`../EMBROIDERY-PLAYBOOK.md`](../EMBROIDERY-PLAYBOOK.md) §4.

## 9. Provenance & how to reproduce the analysis

- Files parsed with `pyembroidery` (stitch list, threads, bounds, per-block stitch
  geometry); satin-vs-fill via consecutive-segment turn-angle (>120° = satin
  reversal); format from `pyembroidery/Vp3Reader.py` + `Vp3Writer.py`.
- Analysis scripts live in the session scratchpad; the measured tables above are the
  durable output. Re-derive on any new reference set the same way.
- Everything here is consistent with `anime/best-practices.md` (object choice, sew
  order, min width, trims) and `3D/3d-embroidery-knowledge.md` (back-to-front,
  tatami norms) — letters just shift the **dominant object to the satin column**.
