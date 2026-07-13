# Routing + recipes — the distilled knowledge of every category

This is the orchestrator's **memory of all seven category knowledge docs at once**: one
row of DNA + the calibrated recipe (size · colours · chart · fill · flags · sew order) per
category, plus a pointer to the full doc to open once you've routed the photo. Every number
is **measured from the user's ground-truth `.VP3` files** — read it as fact, not guess.

**The master source is [`EMBROIDERY-PLAYBOOK.md`](../../../../EMBROIDERY-PLAYBOOK.md)** at the
repo root (router §1, self-contained recipes §2, flag table §5a, verify loop §5c, `.vp3`
container §6, cheat sheet §8). This file is the working condensation; drill into the linked
category doc for the provenance behind each number.

---

## The one model (true in every category)

A design is **a set of regions; each region becomes exactly one stitch object chosen by its
geometry at final size, sewn back-to-front.** Categories differ only in *which object
dominates* and *which shading trick* sells the illusion.

Region → object, by width at final size:
- narrow band, clean centerline, ~1.6–6 mm → **satin column**
- **any letterform stroke, however bold → satin** (dissect the glyph; letters are *never* tatami)
- broad/branching solid ≥ ~5–6 mm → **one continuous tatami fill** (never shattered)
- a shaded **facet** of a 3-D solid → **tatami fill + its own angle** (angle = the 3-D trick)
- line < ~1.6 mm → **run / triple(bean) run**

Invariants: sew **back-to-front** (a keyline / 3-D edge / shadow is a *back* facet → sews
**first**; all other outlines/borders **last**); **min satin ≥ ~1.6 mm** at final size (below
it step-2's 1.2 mm majority filter *erases* the stroke); underlay + **pull-comp 0.2 mm**;
trims+jumps **< 5 %** (the gate) but many trims on dotty art (Arabic diacritics, a star
scatter, lace) is *normal*; small palette; **size set once** via `--width-mm`/`--height-mm`.

---

## Router — what *is* the subject?

| If the subject is… | Category | Dominant object | Open this doc |
|---|---|---|---|
| words / a name / a monogram / calligraphy | **Letters** | satin (even bold caps) | [`letters/letters-embroidery-knowledge.md`](../../../../letters/letters-embroidery-knowledge.md) |
| a **year / score / numeral** (2026, a jersey #) | **Numbers** (letters family) | satin, open counters | [`numbers/numbers-embroidery-knowledge.md`](../../../../numbers/numbers-embroidery-knowledge.md) |
| **Arabic script** (cursive, usually black, + decoration) | **Arabic** | satin script, 1 colour | [`arabic/arabic-embroidery-knowledge.md`](../../../../arabic/arabic-embroidery-knowledge.md) |
| a **geometric solid** with flat shaded facets (cube, prism, cylinder) | **3D** | tatami facets, distinct angle each | [`3D/3d-embroidery-knowledge.md`](../../../../3D/3d-embroidery-knowledge.md) |
| a **character / portrait / detailed illustration** with shading | **Anime/portrait** | satin-dominant (outline + shadow satins), `--satin-lean` | [`anime/best-practices.md`](../../../../anime/best-practices.md) |
| a **bold flat icon / vector shape** (star, heart, arrow, swirl, frame) | **Simple shapes** | one object per shape by width | [`simple-shapes/simple-shapes-embroidery-knowledge.md`](../../../../simple-shapes/simple-shapes-embroidery-knowledge.md) |
| **ornamental embellishment** (floral, vine, mandala, wreath, frame, lace, border) | **Decoration** | thin satin ornament | [`decoration/decoration-embroidery-knowledge.md`](../../../../decoration/decoration-embroidery-knowledge.md) |
| a **fur/feather animal** (pet portrait, bird, farm animal — sketchy/fluffy texture) | **Animals** | sketch-stitch: airy layered run strokes, fabric shows through | [`animals/animals-embroidery-knowledge.md`](../../../../animals/animals-embroidery-knowledge.md) |
| **Palestinian tatreez / counted cross-stitch** (blocky grid motifs, garment panels) | **Falahi** | cross-stitch X's on a fixed grid (own step-5 primitive) | [`falahi/falahi-embroidery-knowledge.md`](../../../../falahi/falahi-embroidery-knowledge.md) |
| a **flat logo / mixed** artwork | **Hybrid** | decompose & route each part | playbook §3 |

**Tell-tales:** zig-zag satin sheen along strokes ⇒ letters · same colour as two planes at
different stitch angles ⇒ 3D · smooth skin/hair tonal flow ⇒ anime · a thin offset colour
hugging one side of each letter ⇒ a keyline (own colour, sewn first) · bold flat closed
silhouettes in 1–4 bright colours ⇒ simple shapes (→ **isacord** chart) · symmetric/repeating
thin satin ornament that adorns ⇒ decoration (size by placement).

A **mixed** design (e.g. display caps + cursive + a keyline): segment it, route each part,
merge to a small palette, sequence everything back-to-front. Use `--purify-colors` (never
`--lettering`, which shatters the script).

---

## Per-category recipes (self-contained — enough to run)

Shared defaults unless a row overrides: `--pull-comp-mm 0.2`, `--fill-underlay` on,
`auto_fill`, `madeira-polyneon`, enclosure-depth sew order (automatic).

### Letters
- **DNA:** letterforms are **100 % satin** — zero tatami even for bold display caps. A
  background *panel* may be tatami; a letter never is.
- **Size** so strokes land ~2–4 mm: short word 90–120 mm, phrase 140–165 mm. **Colours** 1–4.
  **Chart** madeira (isacord if bright). Satin band: keyline ~1.8 < cursive ~2.4 < cap face ~3.7 mm.
- **Flag decision (makes or breaks it):** plain **separable complete block/typeset glyphs →
  `--lettering`**; **ornate caps / cursive / connected calligraphy / any cropped-partial glyph
  → default path + `--purify-colors`** (`--lettering` *shatters* cursive into illegible
  fragments). Thin brush script → add `--fill-method contour_fill`. Counters (holes in
  e/B/g/0/9) auto-open in letter modes.
- **Colour:** snap obvious primaries to pure (black 0,0,0 · red 255,0,0 · yellow 255,255,0);
  **keep custom/muted brand colours verbatim** (a teal stays teal, not neon).
- **Sew:** keyline/3-D edge/shadow first → cap faces → cursive/script → outline/diacritics last.

### Numbers (letters family; drill into the numbers doc)
- Same as letters, plus: **open the counters** on `0 4 6 8 9`; **isacord** for bright digits
  (Madeira has no pure blue). Three sub-styles: block/bubble → purify + fill · brush-script →
  purify + `contour_fill` · shaded/3-D → isacord + flatten any textured face (the 3-D edge is
  a sewn-first back facet / Phase-B finish).

### Arabic
- **DNA:** single-colour **100 % satin script**, pure **Black (0,0,0)**; strokes, diacritics,
  dots, ornament and frame are all the same black satin.
- **Colours `1`.** Size: phrase 140–165 mm; round/stacked (Basmala) ~117 mm tall. Satin band
  1.8–2.5 mm; target areal density **0.4–0.8 st/mm²** (script is sparse).
- **Flags — mandatory:** `--fill-method contour_fill` (auto_fill over-stitches and *hangs* on
  thin sprawling script) + `--purify-colors` (else the near-black averages to a muddy off-black
  and spawns a phantom gray cone). Input must be **crisp pure-black-on-white** — threshold a
  soft scan first. Fine tashkeel → `--pull-comp-mm 0.05` (± `--no-fill-underlay`).
  - **Exception — BOLD display calligraphy** (thick chunky strokes, not thin pen script): those
    strokes are *broad-solid*, so use plain **`auto_fill`**; `contour_fill` hatches a thick
    stroke **hollow** (concentric rings). `contour_fill` is for *thin* script only.
- **Sew:** frame/cartouche first → main word → connecting strokes → tashkeel/dots last.

### 3D geometric solids
- **DNA:** not one object — a set of **flat facets**, each its own **tatami fill**, illusion =
  (1) shade per facet, (2) **a distinct fill ANGLE per facet** (even two same-colour faces need
  different angles), (3) a **wireframe outline stitched last** (running/bean ~2.2 mm, not satin).
- **Build, don't trace** — author facet-by-facet as an SVG; `3D/make_3d_test.py` is the reusable
  template (per-facet `inkstitch:angle`, `fill_underlay`, `row_spacing_mm 0.4`,
  `max_stitch_length_mm 4`, `trim_after`; outline paths → `running_stitch`, `bean_stitch_repeats 1`).
  Tracing a 3-D photo loses per-facet angle control.
- **Sew:** ground → back/shadow facets → front/lit facets → surface details → outlines last.

### Anime / portrait / illustration
- **DNA:** **satin-DOMINANT** — measured from the first real anime ground-truth pair (pink-goku:
  **82.9 % satin**, ~2.25 mm columns, 217 outline : 118 fill objects). The character linework is
  **outline satins**, form is **directional shadow satins**, and even broad shaded masses are sewn
  as satin columns ("sombras con satin"), NOT flat tatami. Hair = many thin directional satins with
  highlight satins on top, sewn last. (See `PAIRS-FINDINGS.md`.)
- **Colours ~7–8** — omit `--colors` and the category prior (8) applies. Size ≥ ~120 mm. Feed flat
  colour with a clean separable background and **crisp dark outlines** (they satin and hold shape).
- **Flags: add `--satin-lean`.** anime is satin-dominant, so lean broad regions to satin (7 mm
  ceiling + variable-width + broad-region satin **strip-tiling**) instead of tatami. Measured on the
  goku render: `satin_frac 21 % → 90 %`, matching the 82.9 % truth. **Caveat:** strip-tiling uses
  straight parallel columns, so broad/blobby regions get **stepped edges** — production *turning
  satin* (contour-following) is the clean path, not yet built. **Drop `--satin-lean`** for a design
  where the stepped edges read worse than a clean tatami fill; keep it when the satin look wins.
- **Honest limit:** the pipeline makes *simplified* satin/fill; manual form-shading, hair relief,
  and clean turning-satin edges are Phase-B Wilcom craft.

### Simple shapes / flat icons
- **DNA:** a few **bold flat closed silhouettes**, each one flat colour. Each shape = one object
  by width: body → fill, ribbon/border/swirl → satin, hairline connector → run.
- **Colours 1–4** bright. Size: single icon 25–40 mm; icon set / star cluster 120–165 mm — sized
  so the **narrowest part clears 1.6 mm** (star points, arrow tips taper). Satin band ~2–6 mm.
- **Flags:** **`--thread-chart isacord`** is *the* lever (Madeira Polyneon has no pure blue,
  ΔE 90). `--purify-colors` **only for genuinely pure primaries** — it worsened an azure arrow
  ΔE 4→17; keep custom/pastel verbatim. Swirls/ribbons/long borders → `contour_fill`.
- Known primitives are best **built** (author the star/heart/arrow as SVG and satin it).

### Decoration / ornament
- **DNA:** symmetric or repeating **thin satin ornament** that adorns (florals, vines, scrolls,
  mandalas, wreaths, frames, lace, borders). 94 % of reference blocks are satin;
  multi-colour-capable. Structure = radial / bilateral / translational symmetry.
- **Colours** often **1 (tone-on-tone)**; florals/crests 4–7, up to 9. **Size by PLACEMENT, not
  a hoop number:** border by edge length (150 mm garment → up to ~1.16 m, aspect to 10:1);
  mandala/doily/wreath/frame by hoop (79–280 mm); FSL motif 33–55 mm; collar/neckline by the
  garment opening (100–380 mm). Satin band ~1.2–3.5 mm.
- **Flags:** `--fill-method contour_fill` (default here). Chart by palette — **isacord** for
  bright ornament, **madeira** for muted botanicals. `--purify-colors` only for pure primaries.
  Fine lace → `--pull-comp-mm 0.05` (± `--no-fill-underlay`).
- **The decoration trap:** thin ink on white + `--colors 1` **washes pale** — solid-fill the
  ornament (don't draw hollow outlines) and **don't trap page-colour inside an enclosing
  frame/ring** (it averages to grey; no flag recovers it). Feed crisp flat colour.
- **Fine hairline line-art** (delicate tattoo-style florals/celestial, single colour): the
  trace renders hairlines as *bold filled strokes* (loses the fineness — an honest limit), and
  `--colors 1` lands **gray** from upscale halos. First choice: `--purify-colors` → black. If
  that **crashes** `contour_fill` (`NoneType … length`) or **hangs** `auto_fill` on the thin
  geometry, don't purify — **binarize the source** to crisp black/white (threshold ~<200),
  trace plain `contour_fill`, and if the cone still lands gray, **stamp it black** in the `.vp3`
  (`pe.read` → `thread.set_color(0,0,0)` → `pe.write_vp3`). Enlarge so strokes clear ~1.6 mm.
- **Sew:** frame/ground → vines/stems → petals/leaves → beads/dots/keyline last.

### Animals — fur/feather sketch stitch (n=10 pairs, 2026-07-13)
- **DNA:** the animal is **hundreds of long overlapping run/bean strokes following the
  fur/feather direction, fabric showing through** — ALL 1,647 registered ground-truth
  objects are outline-family, ZERO area fills. Stroke width med **1.12 mm** (p10 0.78 /
  p90 1.64); blocks read "mixed" at 20–25 % reversal, ~2.3 mm segments. Small satin
  accents only (nose, eye, bow). **Do NOT sew an animal as solid tatami/satin coverage —
  that's the fox failure this category exists to fix.**
- **Colours:** median **9** (natural fur tones + black sketch linework + white highlights;
  cones repeat across stops for layering). **Chart madeira** (muted naturals). Size
  77–216 mm, median ~130 mm.
- **Recipe (approximation — the sketch/fur primitive isn't built yet):**
  `--category animals` (priors: 3 mm ceiling, 0.78–1.64 vwidth clamps) + omit `--colors`
  (prior 8) + **`--fill-method meander_fill`** on fur regions (scribble texture ≈ sketch
  fur; keep `auto_fill` only for genuinely solid props) + size ≥ ~120 mm + `--snap-black`
  on (the keyline-detail layer sews last = production's black-sketch-then-white-highlights
  order).
- **Sew order (measured):** base wash strokes → mid/dark fur layers → black sketch
  outline + face detail → white highlights/whiskers LAST.

---

## The honest boundary (say it in the handoff)

This pipeline **traces a raster and approximates**; it does not equal a design **typed or
hand-digitized in Wilcom**. If the subject is *known* — a word you can type, a solid you can
model, a primitive you can draw — **build it** (Wilcom satin lettering / an authored SVG /
`3D/make_3d_test.py`) rather than trace a picture of it. Trace only when the art exists solely
as an image, and expect to hand-tidy branchy glyphs. The `.vp3` we emit is a byte-faithful,
editable intermediate; the licensed `.emb` save is **Phase B** (Windows + Wilcom dongle).

## Full flag reference

See [`EMBROIDERY-PLAYBOOK.md`](../../../../EMBROIDERY-PLAYBOOK.md) §5a. Quick list:
`--width-mm`/`--height-mm` (one required) · `--colors N` · `--thread-chart
{madeira-polyneon,isacord}` · `--fill-method {auto_fill,contour_fill,meander_fill,…}` ·
`--lettering` · `--purify-colors` · `--open-counters`/`--no-open-counters` · `--pull-comp-mm` ·
`--fill-underlay`/`--no-fill-underlay` · `--name` · `--output-dir`.
