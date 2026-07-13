# Embroidery Production Master Guide — any photo → a production-ready `.vp3`

This is the **general-purpose, self-contained knowledge** that turns *any* image into a
production-ready Wilcom `.vp3` (Phase A) ready for the licensed `.emb` save (Phase B).
It is the **router + the distilled recipe** for every category, consolidated from the
per-domain knowledge docs:

- [`letters/letters-embroidery-knowledge.md`](letters/letters-embroidery-knowledge.md) — words / names / Latin & numeric lettering & calligraphy
- [`numbers/numbers-embroidery-knowledge.md`](numbers/numbers-embroidery-knowledge.md) — years / scores / numerals (digit glyphs: open counters, block vs script vs 3-D)
- [`arabic/arabic-embroidery-knowledge.md`](arabic/arabic-embroidery-knowledge.md) — Arabic calligraphy (monochrome satin script + decoration)
- [`3D/3d-embroidery-knowledge.md`](3D/3d-embroidery-knowledge.md) — geometric shaded solids (cube, prism, cylinder…)
- [`anime/best-practices.md`](anime/best-practices.md) — characters / portraits / detailed illustration
- [`simple-shapes/simple-shapes-embroidery-knowledge.md`](simple-shapes/simple-shapes-embroidery-knowledge.md) — flat icons / vector shapes (stars, hearts, arrows, swirls, frames)
- [`decoration/decoration-embroidery-knowledge.md`](decoration/decoration-embroidery-knowledge.md) — ornamental embellishment (florals, vines, mandalas, wreaths, frames, lace collars, borders)
- [`animals/animals-embroidery-knowledge.md`](animals/animals-embroidery-knowledge.md) — fur/feather animal illustrations sewn as **sketch stitch** (airy layered run strokes along the fur, fabric showing through; all-outline, zero fills — NOT anime's solid satin/fill coverage)
- [`falahi/falahi-embroidery-knowledge.md`](falahi/falahi-embroidery-knowledge.md) — Palestinian tatreez counted cross-stitch garment panels (fixed grid of X's; its own step-5 primitive)
- [`wilcom-manual-rules.md`](wilcom-manual-rules.md) — **the official Wilcom Reference Manual, distilled**: hard numbers for the width→stitch-type boundary (satin ≤ ~7 mm, density 0.3–0.6 mm), underlay-by-width, pull-comp-by-fabric, colour counts, and why the satin gap is a variable-width-satin problem. Where this file and the manual disagree on a number, prefer the manual's.

> **How to read this file.** §0 is the *one model* under every category. §1 routes a
> photo to its category. §2 gives the **complete, self-contained production recipe** for
> each (size · colours · chart · fill-method · flags · sew order) — enough to run without
> opening the category doc, which holds the *measured ground-truth detail* behind each
> number. §3 handles mixed art, §4 the honest "trace vs build" boundary, §5 the pipeline
> (flags + run + the mandatory verify/compare loop), §6 the `.vp3` container facts, §7
> the **protocol for adding a new category** (this file is meant to grow), §8 the
> one-glance cheat sheet.
>
> Every number here is **measured from the user's ground-truth `.VP3` files** — not
> guessed. Reason from the **region geometry and the subject**, never "this looked like
> that other picture."

---

## 0. The one model under every category ⭐⭐

Every design — a word, a cube, a face, a star — is the **same pipeline**: *a set of
regions, each region becomes exactly one stitch object chosen by its geometry, sewn
back-to-front.* Categories differ only in **which object dominates** and **which shading
trick** creates the illusion. Apply the universal rules first, then the category flavour.

### 0a. Region → object — the universal classifier ⭐

Choose per region by its **shape and width at final size** — never "one fill for
everything":

| Region geometry (at final size) | Object | Key settings |
|---|---|---|
| Narrow elongated band, single clean centerline, ~1.6–6 mm wide | **satin column** | pull-comp 0.2 mm; trim between disjoint pieces |
| **Any letterform stroke** (however bold) | **satin column(s)** — dissect the glyph into stroke-columns | letters are *always* satin, never tatami |
| Broad / branching solid area (≥ ~5–6 mm, junctions) | **tatami fill** | row 0.4 mm; underlay on; one continuous fill, never shattered |
| Shaded **facet** of a geometric solid | **tatami fill + a distinct angle per facet** | angle separates the planes (the 3D trick) |
| Line thinner than ~1.6 mm | **run / triple-run** | ~2.2 mm run; triple (bean) for a bolder line |
| Foliage / fur / hair / texture | motif / random / chenille / directional satin | manual Wilcom (Phase B) |

These rows are Wilcom's own **two stitch-type families** applied per region (verbatim from
EmbroideryStudio's tooltips): **Outline stitches** — running / triple-bean / satin-column /
motif — *"for simple or decorative borders and details; apply to **open OR closed** objects"*;
and **Fill stitches** — tatami / satin-fill / decorative fills — *"for simple or decorative
fills; apply to **CLOSED objects ONLY**."* So classifying a region *is* choosing its family:
skeletonise it to an **open centerline** and lay an outline stitch on it (run, or satin column),
or keep it a **closed area** and fill it (tatami). **Invariant:** a fill needs a closed object;
run/satin ride the open centerline — honour it or the object won't sew. (Both families also have
*decorative* forms — motif runs, pattern fills — the pipeline doesn't emit yet: a future ornament tier.)

The pipeline implements this **per region** (`steps/stitches.py`): each connected component is
tiered by its *own* area-weighted width — **run** (< ~1.6 mm), **satin column** (~1.6–3 mm and a
single clean column; a forked stroke dissects into per-branch satins under `--branch-satin`), or
**tatami fill** (broader, branchy, or a dense mesh) — so one colour can mix all three. A colour
enters the linework pre-pass if its area-weighted width is below `_SATIN_MAX_WIDTH_MM` (3.0 mm,
raised by `--lettering`), or if it is broad but still holds a substantial keyline to split out.

### 0b. Cross-cutting invariants — true in *every* category ⭐

1. **Sew back-to-front** (painter's algorithm): background / farthest first, top detail
   last, **all outlines / borders / keylines-as-front absolutely last** — except a
   **keyline / 3-D edge / shadow**, which is a *back* facet and sews **first** (§2.1).
2. **Minimum satin/feature width ≈ 1.6 mm** at final size. Below it, step-2 consolidation
   (1.2 mm majority filter) **erases** the stroke before it's ever stitched — bold it,
   enlarge the design, or drop to a run. Step 1 warns when the smallest feature < ~1.2 mm.
3. **Underlay** on fills; **pull-comp 0.2 mm**; slight **overlap** of neighbours — the
   element in front is flush, the one behind extends under it ("crab method").
4. **Connected, few cuts:** trims + jumps must stay **< 5 %** (the step-7 gate). Each
   genuinely disjoint piece ends in a clean trim (= a Wilcom *Break-Apart* boundary).
   Many trims on inherently dotty art (Arabic diacritics, a star scatter) is *normal*,
   not fragmentation.
5. **Palette stays small** — one thread per shade, reused across regions.
6. **Size is set once** via `--width-mm` / `--height-mm`; density is computed *for that
   size*. Re-run to resize — never rescale the `.vp3` afterward.
7. **The `.vp3` container is category-independent** (§6). Satin and fill are just stitch
   patterns inside the same big-endian VSM file; the writer (`pe.write_vp3`) and the
   thread-metadata stamping are shared by every category.

### 0c. The min-width law in one line

> **A satin stroke must land ≥ ~1.6 mm wide at the final size.** This single fact ties
> §0b.2 to size selection: choose `--width-mm` so the design's *intended satin strokes*
> fall in their category's measured band (letters ~2–4 mm, Arabic 1.8–2.5 mm, shapes
> 2–6 mm). Too small → strokes vanish; too big → strokes exceed the satin ceiling and
> fall back to heavy tatami fill, exploding the stitch count.

---

## 1. Category router — what *is* the subject? ⭐

Look at the photo and route it. A design can be **mixed** — then decompose and route each
part (§3).

```
Is the subject primarily TEXT — words, a name, numbers, a monogram, calligraphy?
│   └─ YES → LETTERS.  Dominant object: SATIN (everything, even bold display caps).
│            → letters-embroidery-knowledge.md   (recipe §2.1)
│            ├─ DIGITS specifically (a YEAR / score / numeral — 2026, 2027)? Same family,
│            │  but OPEN THE COUNTERS (0 4 6 8 9), isacord for bright digits, and block
│            │  vs brush-script vs 3-D sub-styles → numbers-embroidery-knowledge.md.
│            └─ ARABIC SCRIPT specifically (cursive, usually monochrome black, with
│               decoration above/under/around)? → arabic-embroidery-knowledge.md (§2.2).
│
├─ Is it a GEOMETRIC SOLID with flat shaded facets (cube, prism, box, cylinder,
│   isometric / low-poly), edges drawn in?
│   └─ YES → 3D.  TATAMI FILL per facet + a distinct ANGLE per facet + wireframe LAST.
│            → 3d-embroidery-knowledge.md   (recipe §2.3)
│
├─ Is it a CHARACTER / PORTRAIT / detailed ILLUSTRATION with shading & many colours?
│   └─ YES → ANIME/PORTRAIT.  Flat tatami fills + directional SHADOW SATINS + outline
│            satins; higher colour count (~8–12). → anime/best-practices.md  (recipe §2.4)
│
├─ Is it a FLAT ICON / VECTOR SHAPE — star, heart, arrow, balloon, swirl, frame,
│   constellation: bold solid silhouettes, 1–4 clean colours, no shading?
│   └─ YES → SIMPLE SHAPES.  One object per shape by width; --thread-chart isacord.
│            → simple-shapes/simple-shapes-embroidery-knowledge.md  (recipe §2.5)
│
├─ Is it ORNAMENTAL EMBELLISHMENT — a floral spray, vine, scroll/flourish, mandala /
│   rosette / doily, wreath, frame/cartouche, lace collar/neckline, or a repeating
│   border — symmetric or repeating thin ornament meant to ADORN a garment/panel?
│   └─ YES → DECORATION.  Satin-dominant thin ornament; contour_fill; size by PLACEMENT.
│            → decoration/decoration-embroidery-knowledge.md   (recipe §2.7)
│
└─ Otherwise a FLAT LOGO / ICON / simple vector graphic
    └─ HYBRID: small palette, flat fills for areas + satin/run for outlines & thin marks
       (§2.6).  For clean single icons use SIMPLE SHAPES above.
```

**Tell-tales that disambiguate quickly:**

- **Zig-zag satin sheen along strokes** in a stitch render ⇒ letters (satin).
- **Same colour appearing as two planes at different stitch angles** ⇒ 3D (the angle is
  the whole trick; a flat object has one angle).
- **Smooth tonal gradients / skin / hair flow** ⇒ anime (shadow satins over fills).
- **A thin offset colour hugging one side of each letter** ⇒ a **keyline / 3-D edge**: its
  own colour, sewn *first*; the face overlaps it (the 3D painter's order applied to type).
- **Bold flat closed silhouettes in 1–4 bright/clean colours, no shading** (star, heart,
  arrow) ⇒ **simple shapes**: one object per shape by width, and flip the chart to
  **isacord** (Madeira Polyneon has no pure blue — ΔE 90 on blue).
- **Symmetric/repeating thin SATIN ornament that adorns** (radial mandala, a vine/scroll, a
  lace collar, a border run) ⇒ **decoration**: satin-everywhere like Arabic but botanical/
  geometric and multi-colour-capable; **size by placement** (a border can be > 1 m), and
  many trims = intricacy, not fragmentation. (A single bold icon ⇒ simple shapes instead.)

---

## 2. The per-category production recipes (self-contained) ⭐⭐

Each block below is enough to run the job. Open the linked category doc only for the
measured ground-truth tables and the provenance behind the numbers.

### 2.0 The shared defaults (apply unless a category overrides)

`--pull-comp-mm 0.2`, `--fill-underlay` on, `auto_fill`, `madeira-polyneon`,
enclosure-depth sew order (automatic). Underlay + pull-comp on every fill/satin; each
disjoint piece trims. Drop these only when a recipe says so.

### 2.1 Letters / names / Latin & numeric lettering ⭐

- **DNA:** letterforms are **100 % satin** — zero tatami, *even bold display caps*
  (confirmed across the whole `10000`–`12000` calibration set). A *background panel*
  behind text may be a tatami fill; a **letter, any weight, is always satin.**
- **Palette:** 1–4 colours. **Size:** short word/number 90–120 mm, long phrase 140–165 mm
  — chosen so strokes land **~2–4 mm**. **Chart:** madeira-polyneon (or isacord for bright
  primaries). **Satin band:** keyline ~1.8 < cursive ~2.4 < display-cap face ~3.7 mm.
- **Three satin idioms:** *stroke satin* (script — each stroke a column, disjoint loops
  trim); *filled-face satin* (solid caps packed with ~3–4 mm columns); *outline satin*
  (open caps — only the outline satined).
- **Sew order:** keyline / 3-D edge / shadow **first** → cap faces → cursive/script →
  outline/diacritics **last**. A 3-D edge is a *back facet* (painter's order, ties to 3D).
- **Flags — the decision that makes or breaks it:**
  - **Plain, separable, *complete* block / typeset glyphs** → **`--lettering`** (satins
    the strokes, raises the satin ceiling, snaps inks to pure colour). Keep strokes ~2–4 mm.
  - **Ornate caps, cursive/script, connected calligraphy, or any crop with partial
    glyphs** → **default path** + **`--purify-colors`** (faithful colours, no
    dissection). `--lettering` **shatters** cursive into illegible fragments — never use
    it there.
  - **Thin sprawling brush-script** (long thin letters) → add **`--fill-method
    contour_fill`** (auto_fill over-stitches / can hang).
  - **Open counters** (holes in e/B/g/0/9) auto-drop in letter modes (`--open-counters`).
- **Colour rule:** snap obvious primaries to pure (Black 0,0,0 · Red 255,0,0 · Yellow
  255,255,0) but **keep custom/muted brand colours verbatim** (teal 42,133,143 → *not*
  neon). `_purify_ink` encodes exactly this.
- **Honest limit:** a tracer *approximates* typeset satin lettering; for a *known* word,
  typing it in Wilcom's satin lettering tool (Phase B) beats tracing a picture of it (§4).
- **Numbers (years / scores / numerals)** are this same family — see
  `numbers/numbers-embroidery-knowledge.md`. Digit-specific levers: **open the counters**
  (`0 4 6 8 9`), **isacord** for bright digits (Madeira has no pure blue), three sub-styles
  (block/bubble → purify+fill · brush-script → purify+contour_fill · shaded/3-D → isacord +
  flatten any textured face; the 3-D edge is a sewn-first back facet / Phase-B finish).

### 2.2 Arabic calligraphy ⭐

- **DNA:** **single-colour, 100 % satin script.** One thread, **pure Black `(0,0,0)`**;
  every stroke, diacritic, dot, ornament and the enclosing frame is a satin column
  (77–79 % turn-angle reversals in every reference). Decoration above/under/around is *the
  same black satin* — just more pieces.
- **Palette:** 1 (`--colors 1`). **Size:** horizontal phrase 140–165 mm; stacked/round
  composition (Basmala) ~117 mm tall. **Satin band:** 1.8–2.5 mm. **Areal density to
  match:** 0.4–0.8 st/mm² (satin script is *sparse*).
- **Sew order:** enclosing **frame / cartouche first** (it's the background) → main word
  strokes → connecting strokes → **tashkeel / dots / florets last**.
- **Flags — the Arabic levers:**
  - **`--fill-method contour_fill`** — *mandatory.* Arabic is thin and sprawling;
    auto_fill over-stitches and **hangs** on it. contour_fill follows the stroke, landing
    density almost exactly on the reference.
  - **`--purify-colors`** — snaps the near-black ink to pure `(0,0,0)` (else trace edges
    average to a poor off-black ~`(37,37,37)`).
  - **Input must be crisp pure-black-on-white** — a soft scan / JPEG ringing spawns a
    phantom gray cone. Threshold first.
  - For **fine tashkeel**, lower `--pull-comp-mm 0.05` (and/or `--no-fill-underlay`) so
    thin marks don't read heavier than the art.
- **Honest limit:** connected cursive **cannot** be made all-satin by a tracer without
  fragmenting; contour_fill gets the *look* and *density*, not the master's variable-width
  hand satin. Tips clip ~1 mm (coverage ~85–90 % at extremities, ~98 % in the bulk).

### 2.3 3D geometric solids ⭐

- **DNA:** a 3-D shape is **not one object** — it's a set of **flat facets**, each its
  **own tatami fill**, and the illusion is three layered tricks: (1) **shade per facet**
  (lit = lighter thread, shadow = darker); (2) **a distinct fill ANGLE per facet** (the key
  trick — even two faces of the *same* colour need different angles so light separates the
  planes); (3) a **wireframe outline stitched LAST** over every fill.
- **Settings (measured, identical in both references):** tatami, **max stitch 4.0 mm**, row
  ~0.4 mm, underlay on, pull-comp 0.2 mm, trim between facets; outline = **running/triple
  (bean) ~2.2 mm**, not satin. Small palette (one thread per shade).
- **Sew order:** ground/background → each solid's **back/shadow** facets → its **front/lit**
  facets → tiny surface details (seeds, speculars) → **all outlines absolutely last.**
- **Build, don't trace.** Geometric solids are **best authored facet-by-facet as an SVG**
  (`3D/make_3d_test.py` is a complete reusable implementation: per-facet `inkstitch:angle`,
  `fill_underlay`, `row_spacing_mm 0.4`, `max_stitch_length_mm 4`, `trim_after`; outline
  paths get `stroke_method running_stitch`, `bean_stitch_repeats 1`). Feeding a 3-D photo
  through the tracer loses the per-facet angle control. See §4.
- **Shape templates** (cube/prism/box, cylinder, cone, sphere) and geometry-extraction
  recipe are in the 3D doc §5–§6.

### 2.4 Anime / portrait / illustration

- **DNA:** flat **tatami fills** for base colour + **directional shadow satins** over the
  base to model form + **outline satins**; hair built as many thin directional satin
  strands with **light highlight satins on top, sewn last**.
- **Palette:** **~8–12** colours. **Size:** portrait ≥ ~120 mm. **Chart:** default;
  high `--colors`.
- **Sew order for a face:** skin & base fills → colour-shading satins → hairline & outlines
  → hair base → hair highlights → **eyes/iris detail last.** Back-to-front throughout.
- **Flags:** **default path**, high `--colors` (8–12). Feed flat colour with a **clean
  separable background** and **crisp dark outlines** (the outlines survive as satin
  linework and hold the shape even where light fills merge with a light ground).
- **Honest limit:** the pipeline makes **simplified** flat fills + outline satins; it will
  **not** reproduce manual form-shading or hair relief — that's Phase-B Wilcom craft. The
  anime doc is mostly the *full Wilcom course* (object choice, underlay, sequencing,
  effects) — read it for the craft behind the automation.

### 2.5 Simple shapes / flat icons ⭐

- **DNA:** a handful of **bold flat closed silhouettes** (star, heart, balloon, arrow,
  swirl, frame, constellation), each one flat colour on a clean ground. Each shape = **one
  object by width**: solid body → **fill**, ribbon/border/swirl → **satin**, hairline
  connector → **run**.
- **Palette:** 1–4, bright/clean. **Size:** single icon 25–40 mm; icon set / star cluster
  120–165 mm — sized so the **narrowest part of every shape clears 1.6 mm** (star points,
  arrow tips taper). **Satin band:** chunky, ~2–6 mm.
- **Flags — the shapes levers:**
  - **`--thread-chart isacord`** — *the* lever. Shapes use bright saturated primaries;
    **Madeira Polyneon has no pure blue (ΔE 90)**; isacord nails red/blue/azure/aqua.
  - **`--purify-colors` only for *genuinely pure primaries*** (a flag, a pure-cyan frame).
    For custom/pastel colours, *keep them verbatim* — purify worsened an azure arrow from
    ΔE 4.1 to 16.6.
  - **`--fill-method contour_fill`** only for **swirl/ribbon/long-thin-border** designs;
    compact solid icons stay on default `auto_fill`.
- **Honest limit:** the references are satin-dominant (a digitizer satined star arms for
  sheen); a tracer **fills** the bodies (clean, production-correct, just no satin sheen).
  Because shapes are *known primitives*, lean toward **build** (author the star/heart/arrow
  as a crisp SVG and satin it) over trace (§4).

### 2.6 Flat logo / hybrid

- Small palette; **flat tatami fills for areas + satin/run for outlines and thin marks**;
  outline/border **last**. Decompose into parts and route each (§3). For a clean single
  icon, use simple shapes (§2.5); for text-in-logo, use letters (§2.1).

### 2.7 Decoration / ornamental embellishment ⭐

- **DNA:** **symmetric or repeating thin SATIN ornament** that *adorns* — florals, vines,
  scrolls, mandalas/rosettes/doilies, wreaths, frames/cartouches, lace collars/necklines,
  borders. **94 % of reference blocks are satin** (the same satin-everywhere DNA as Arabic,
  but botanical/geometric and **multi-colour-capable**). Structure = **radial / bilateral /
  translational** symmetry. Seven sub-types in the decoration doc.
- **Palette:** often **1 (tone-on-tone** — white-on-white, gold-on-gold; the references'
  recurring `(0,153,0)` "Dark Green" is a placeholder cone); florals/crests 4–7; up to 9.
- **Size by PLACEMENT, not a hoop number:** border by the **edge length** (150 mm → **1.16 m**,
  aspect ratio to 10:1); mandala/doily/wreath/frame by **hoop** (79–280 mm); FSL motif
  **33–55 mm**; collar/neckline by the **garment opening** (100–380 mm). Satin band
  ~1.2–3.5 mm; features ≥ ~1.2 mm.
- **Flags — the decoration levers:**
  - **`--fill-method contour_fill`** — *default.* Ornament is thin and sprawling; auto_fill
    over-stitches / can hang (same as Arabic & swirls).
  - **Chart by palette:** **`isacord`** for bright clean ornament (aqua lace, red/blue
    mandalas, rainbow); **`madeira-polyneon`** for muted botanical florals.
  - **`--purify-colors`** only for genuinely pure primaries — most decoration is custom
    mid-tone / tone-on-tone, kept verbatim.
  - **Fine lace:** **`--pull-comp-mm 0.05`** (± `--no-fill-underlay`) so thin marks don't
    read heavy.
- **Source prep is the decoration trap (decoration §5):** thin ink on white + `--colors 1`
  **washes pale** — *solid-fill* the ornament (don't draw hollow outlines) and **don't trap
  page-colour inside an enclosing frame/ring** (it averages ink+trapped-white to grey and
  **no flag recovers it**). Feed crisp flat colour.
- **Sew order:** frame / ground / net-fill body → vines/stems → petals/leaves → beads/
  dots/florets/keyline **last.** Many trims = disjoint elements (up to 231), not fragmentation.
- **Honest limit:** the tracer renders closed-cell ornament as **clean fills** (production-
  correct, gate-passing), not the references' hand-satin sheen; the `djanna` collar's
  **open net/mesh lace** is a Wilcom net-fill the tracer doesn't synthesise. Because
  ornament is *known, symmetric, repeating*, lean **build**: author one motif as open-
  centerline SVG, satin it, mirror/array for the symmetry (§4).

---

## 3. Mixed designs — decompose, route, sequence

Most real artwork is mixed (a logo = illustration + text; "Let the ADVENTURE Begin" =
display caps + cursive + keyline). Don't force one recipe:

1. **Segment** into parts by subject (text block, illustration, geometric panel, border).
2. **Route each part** through §1 to its category recipe and object choice (§2).
3. **Merge palettes** (keep the total small) and **sequence everything back-to-front**
   across parts: panels/background → fills → satins → text → outlines/border **last**.
4. In the pipeline this mostly happens automatically (colour-quantize + enclosure-depth
   sew order). The manual lever is the **per-part object choice** above. For a mixed
   caps-+-cursive design, use **`--purify-colors`** (not `--lettering`, which shatters the
   script) so colours stay faithful without fragmenting the cursive.

---

## 4. Trace it or build it? — the honest boundary ⭐

This pipeline **traces a raster** and *approximates*. It does **not** equal a design
**typed or hand-digitized in Wilcom**:

- **Clean block / typeset text** is best **typed in Wilcom's satin lettering tool** (exact
  satins, low stitch count). `--lettering` (per-stroke satin dissection) works for **plain,
  separable, complete block glyphs** and **fragments on ornate caps, cursive/script, or
  cropped glyphs** — for those use the **default fill path**.
- **Geometric 3-D** is best **authored facet-by-facet as an SVG** (3D doc's
  `make_3d_test.py`), not traced — tracing loses per-facet angle control.
- **Known primitives** (a perfect star/heart/arrow) are best **authored as SVG** and
  satined, exactly like 3D facets.
- **Portraits** trace to *simplified* flat fills + outline satins; manual form-shading
  (shadow satins, hair relief) is **Phase-B Wilcom** craft.

So the decision is also **"trace it or build it?"**: if the subject is *known* (a word you
can type, a solid you can model, a primitive you can draw) → **build it**; if it exists
only as an image → **trace + hand-tidy**. Either way the `.vp3` we emit is a byte-faithful,
editable intermediate; the final licensed `.emb` / tidy pass is Phase B.

---

## 5. The pipeline — flags, run, verify ⭐

### 5a. Full flag reference

| Flag | Default | What it does / when to use |
|---|---|---|
| `--width-mm` / `--height-mm` | — (one **required**) | Target size; the other dimension follows the aspect ratio. Sets stroke widths → pick so satins land in band (§0c). |
| `--colors N` | 8 | Threads to quantize to. Letters/Arabic/shapes **1–4**; anime **8–12**. |
| `--thread-chart` | `madeira-polyneon` | `madeira-polyneon` for muted art / calligraphy; **`isacord` for bright clean primaries** (shapes — Madeira lacks pure blue). |
| `--fill-method` | `auto_fill` | `auto_fill` for compact shapes; **`contour_fill` for thin sprawling regions** (calligraphy, swirls, long borders — auto_fill over-stitches / hangs); `meander_fill`/`guided_fill`/`circular_fill` special. |
| `--lettering` | off | Block/typeset glyphs: satin the strokes (dissect glyphs), raise satin ceiling, **snap inks to pure**. **Shatters cursive — don't.** Implies `--purify-colors`. |
| `--purify-colors` | off | Colour snap only (near-pure → pure, custom kept verbatim), **no dissection**. Use for mixed caps+cursive and Arabic. |
| `--open-counters` / `--no-open-counters` | auto (on for letter modes) | Drop ink-*enclosed* page-coloured regions (hole in e/B/g/0) to background so they read through. |
| `--pull-comp-mm` | 0.2 | Widening band per side. **Lower to ~0.05** for fine decoration (thin tashkeel) so it isn't fattened. |
| `--fill-underlay` / `--no-fill-underlay` | on | Underlay under fills. Drop to keep thin decoration crisp. |
| `--name` / `--output-dir` | stem / `./output` | Output stem and directory. Artifacts: `NAME_pro.vp3`, `NAME_pro_preview.png`, `NAME_pro_threadlist.txt`. |

### 5b. Run command

```bash
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline <photo> \
    --width-mm <by §2> --colors <by §2> --thread-chart <by §2> \
    [--lettering] [--purify-colors] [--fill-method contour_fill] \
    [--pull-comp-mm 0.05] [--no-fill-underlay] \
    --name <name> --output-dir <dir>
```

> The console script `wilcom-pipeline` is **stale** (the venv was built at an old path);
> **always invoke via `PYTHONPATH=src .venv/bin/python -m wilcom_pipeline`.** Step 5 needs
> the vendored Ink-Stitch binary at `vendor/inkstitch/bin/inkstitch` (override
> `$INKSTITCH_BIN`). A run takes ~30 s–2 min.

The 7 ordered steps: ① analyze → ② preprocess (background drop + colour quantize + ink
purify) → ③ thread-match (nearest cone) → ④ trace (vtracer → layered SVG, enclosure-depth
sew order, stamped labels) → ⑤ stitches (Ink-Stitch: satin for linework colours, tatami
+ underlay + trim_after for fills) → ⑥ emit (VP3 + preview + threadlist, **cones stamped
into the VP3 threads**) → ⑦ verify (the gate).

### 5c. The mandatory verify + compare-to-original loop ⭐

**Step 7 is a real gate, not a crash.** `ctx.verification = {passed, checks, metrics}`; a
**fail** is the signal to re-run with adjusted flags. **Before delivering, always render the
output and measure it against the source (and any ground-truth `.VP3`); iterate until the
drift is explained or gone** (the standing convention — enlarge/inspect, don't assume).

`orchestrator/scripts/` holds the reusable measurement scripts (one shared copy — the old
per-category `tools/` dirs were consolidated there) — use them for any new job:

- `analyze_vp3.py <file.vp3>` — threads, bounds, satin-vs-fill (turn-angle reversal %),
  trims, per-block geometry. Confirm object type, palette, density.
- `render_vp3.py <out> <file.vp3>` — PNG of the stitches + piece geometry.
- `compare_to_photo.py <source.png> <cand.vp3> <overlay.png>` — **IoU + source-coverage vs
  the original photo** (no ground-truth needed) — the drift meter for a fresh design.
- `compare_vp3.py <ref.vp3> <cand.vp3> <overlay.png>` — IoU / coverage vs a ground-truth VP3.

**What "good" looks like:** gate **PASS**; ink-mask **coverage of the source ≥ ~85 %**
(clean icons ~99 %); **areal density in the category band** (Arabic 0.4–0.8, solid icons
up to ~15 st/mm²); palette = the intended cones within ΔE; object type per block sane
(satin where it should satin); every element legible in the preview. If coverage falls at
*tips/points*, strokes are clipping → **enlarge** so the narrow part clears 1.6 mm. If a
**phantom colour** appears, the input wasn't crisp → re-threshold.

---

## 6. Cross-cutting container reference — the `.vp3` + thread stamping ⭐

(Full measured detail + the read→write→read round-trip proof are in
[`letters/letters-embroidery-knowledge.md`](letters/letters-embroidery-knowledge.md) §7–§8;
this is the working summary that applies to **every** category.)

- **`.vp3` is the Husqvarna Viking / Pfaff "VSM" format.** Magic `%vsm%`; producer string
  "Produced by ⎵⎵⎵⎵ Software Ltd" (Wilcom emits the same). **Big-endian** ints;
  length-prefixed strings (UTF-16BE header, UTF-8 body). **Stitch unit = 0.1 mm**;
  single-byte delta ±127 = ±12.7 mm, longer moves use the `80 01 … 80 02` escape. **Y is
  stored negated** (file is y-up) — don't double-flip previews.
- **No JUMP command:** pyembroidery's writer drops `JUMP` (the needlebar just moves); only
  **TRIM** (`80 03`) connects. **`END` is written as a trailing trim** → a round-trip shows
  +1 trim (harmless artifact).
- **Round-trip fidelity is proven:** reading a reference and re-writing with
  `pe.write_vp3` reproduces it within ±2 bytes and re-reads identically (same stitch
  count, bounds within ±1 unit, all thread metadata preserved). **No custom VP3 writer is
  needed** — `pe.write_vp3` is the trusted path for all categories.
- **Thread metadata — carry the cones into the file.** Each thread stores
  `catalog_number` (cone **code**, e.g. `1801`), `description` (cone **name**), `brand`
  (the **chart**). `emit._stamp_thread_metadata` stamps these from step-3's `thread_map`
  **before** `write_vp3`, so Wilcom/Hatch opens the file with **named cones, not bare
  RGB** — matching the production references. Both "named cone" and "bare RGB" styles open
  fine; we write named.

---

## 7. Adding a new category — the update protocol ⭐

This file is meant to **grow**. When the user supplies ground-truth `.VP3` files for a new
subject (e.g. florals, mascots, monograms), capture it the same way every existing
category was captured, so the knowledge stays *measured, not guessed*:

1. **Create `>category</>/` with `<category>-embroidery-knowledge.md`** and drop the
   reference `.VP3` files there (the category dirs hold knowledge + reference VP3s, not
   pipeline code).
2. **Measure the references** with the `orchestrator/scripts/` toolbox (`analyze_vp3.py`,
   `compare_vp3.py`, `render_vp3.py`, …): threads & palette, size, **satin-vs-fill via consecutive-segment
   turn-angle (>120° = a satin reversal)**, trims, per-piece geometry split on
   `TRIM`/`COLOR_CHANGE`, and **areal density** (pure stitches ÷ bounding area). Every
   number in the doc must be measured.
3. **Distil the DNA** into the doc's §0 (the one rule), §1 (what the references are,
   measured table), §2 (core recipe + per-object settings), and a **calibrated production
   command** (size band, `--colors`, chart, fill-method, flags).
4. **Validate end-to-end:** turn a reference into a clean raster (`vp3_to_photo.py`), run
   it back through the pipeline with the recipe, and `compare_vp3.py` against the
   ground-truth — coverage ≥ ~85 %, density in band, gate PASS, drift explained (§5c).
5. **Document the honest boundary** (what the tracer can't reach vs hand-digitized Wilcom).
6. **Wire it into THIS file:** add the doc to the list at the top, add a branch to the §1
   router with its tell-tale, add a §2.x self-contained recipe, and a row to the §8 cheat
   sheet. Keep the §0 universal model and §6 container reference unchanged — those are
   category-independent.
7. **Update the skill** (`.claude/skills/orchestrator/`) — its
   `references/routing-and-recipes.md` cheat sheet — to match, and add a memory pointer if a
   non-obvious lever was learned.

The discriminator across all categories is always **"which object dominates and which
shading trick creates the illusion"** (§0). A new category is just a new answer to that.

---

## 8. One-glance cheat sheet ⭐

| Category | Dominant object | Illusion trick | Palette | Size | Chart | Fill | Flags | Sew order |
|---|---|---|---|---|---|---|---|---|
| **Letters (block)** | satin (filled-face) | keyline/3-D edge first | 1–4 | strokes ~2–4 mm (word 90–120, phrase 140–165) | madeira / isacord | auto | **`--lettering`** | keyline → faces → script → outline last |
| **Letters (cursive/ornate/mixed)** | satin / fills | — | 1–4 | 90–165 | madeira | auto (or **contour** for brush) | **`--purify-colors`** (NOT `--lettering`) | back-to-front |
| **Arabic** | satin script | sparse pen satin | **1 (black)** | phrase 140–165 / round ~117 | madeira | **`contour_fill`** | **`--purify-colors`** | frame → words → diacritics last |
| **3D solid** | tatami facets | **distinct angle/facet** + shade | small | facets fill cleanly | — | tatami (author SVG) | **build, don't trace** | ground → back → front → wireframe last |
| **Anime/portrait** | tatami fills + **shadow satins** | directional shadow/highlight satins | **8–12** | ≥ ~120 mm | default | auto | default, high `--colors` | fills → shadows → outlines → hair → eyes last |
| **Simple shapes** | fill (body) + satin (ribbon) + run | clean flat silhouette | 1–4 | icon 25–40 / set 120–165 | **isacord** | auto (**contour** for swirls) | purify **only** pure primaries | frame → bodies → highlights/connectors last |
| **Decoration** | **satin ornament** (+ net-fill lace) | symmetry / repetition | **1** (tone-on-tone) – 9 | **by placement**: border 150–1160, mandala 79–280, FSL 33–55 | isacord (bright) / madeira (botanical) | **contour_fill** | solid-fill source, don't trap page-colour; purify only pure primaries | frame/ground → vines → petals → beads/keyline last |
| **Flat logo/hybrid** | fills + satin/run | — | 2–6 | by use | by colours | auto | decompose & route (§3) | fills → outline last |

**Universal, every row:** min satin **≥ 1.6 mm** · underlay + pull-comp 0.2 mm · trims < 5 %
· small palette · size once · cones stamped into the VP3 · **verify + compare to original**.
