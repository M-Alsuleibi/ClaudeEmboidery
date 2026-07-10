---
name: orchestrator
description: >-
  End-to-end orchestrator that turns ANY image the user drops — any format (PNG, JPG, WEBP,
  HEIC/iPhone, TIFF, PSD, GIF, BMP, AVIF, SVG, PDF) — into a flawless, production-ready Wilcom
  embroidery `.vp3` (plus preview + thread list), organized in a per-design folder under
  `orchestrator/output/<name>/`, then iterates the result against the original photo until it
  is a faithful copy. The user drops photos to digitize in `input/` at the repo root. Use this
  WHENEVER the user supplies a photo, logo, name/lettering, number/year, Arabic calligraphy,
  icon, character,
  ornament, or any artwork and wants it embroidered — a stitch file, a digitized design, a
  `.vp3`/`.emb`, something to "stitch out", "make embroiderable", "digitize", or "put on a
  cap/patch" — even when they just drop an image without naming the format or the category,
  and even for HEIC/SVG/PDF that other tools can't open. This is the single entry point: it
  normalizes the input, analyzes it to pick the category (letters, numbers, Arabic, 3D,
  anime/portrait, simple shapes, decoration, or a mixed logo), applies that category's
  measured recipe (size, colours, thread chart, fill method, mode flags), runs the Phase-A
  pipeline, and verifies + re-runs against the source until the drift is gone or explained.
---

# Orchestrator — any photo → a faithful, production-ready `.vp3`

This skill is the **single front door** to this repo's photo→embroidery toolchain. It drives
**Phase A**: normalize whatever the user gives you into a clean raster, route it to its
category, apply that category's *measured* recipe, run the headless pipeline, and **loop
verify-against-the-original until the output is a faithful copy of the source.** The encrypted
`.emb` (the only *real* deliverable) is written later in licensed Wilcom (**Phase B**, Windows)
— out of scope; you hand off the `.vp3`.

> Run from the repo root (where `.venv/`, `src/`, `vendor/inkstitch/` live). All bundled
> scripts locate the repo root themselves, so they work from anywhere.

### Files & folders — the strict convention ⭐
- **Input:** the user drops the photo(s) to digitize in **`input/`** at the repo root. Process
  whatever is there (any format). If `input/` is empty, ask the user for the photo (or accept a
  path they give directly).
- **Output:** collect **every design's results in its own subfolder** `orchestrator/output/<name>/`
  — one folder per photo — so the output tree never becomes a flat pile of loose files. `<name>`
  is a short slug from the design (the pipeline's `--name`). Each folder holds the **moved
  original photo** plus its siblings: `<name>_src.png` (normalized), `<name>_pro.svg`,
  `<name>_pro.vp3`, `<name>_pro_preview.png`, `<name>_pro_threadlist.txt`, `<name>_overlay.png`
  (drift vs source).
- **Move, don't copy, the original in — and leave `input/` empty** when the job finishes, so the
  drop zone is clear for the next photo. Never write loose artifacts to `orchestrator/output/`
  itself; always into a `<name>/` subfolder.

**The whole job is one decision, repeated under a feedback loop:** *route the image, pick the
recipe the category demands, run it, measure the output against the source, and adjust and
re-run until it matches.* The measured knowledge behind every recipe is the seven category
docs — condensed for you in [`references/routing-and-recipes.md`](references/routing-and-recipes.md)
(read it first: it holds all seven categories' DNA + recipes at once) and, in full, in
[`EMBROIDERY-PLAYBOOK.md`](../../../EMBROIDERY-PLAYBOOK.md) and the per-category
`*-embroidery-knowledge.md`. **The numbers there are measured from the user's ground-truth
`.VP3` files — trust them over any resemblance to a past job.**

## The workflow

### 0. Load the category knowledge
Read [`references/routing-and-recipes.md`](references/routing-and-recipes.md) — the distilled
memory of all seven category docs (DNA + recipe + which full doc to open). Once you've routed
the photo (step 2), open that **one** category's `*-embroidery-knowledge.md` for the measured
detail before finalizing flags. Don't reason from a past picture — reason from *this* photo's
region geometry and the measured recipe.

### 1. Pick the photo from `input/` and normalize it — accept any format ⭐
The user drops the photo in **`input/`** at the repo root (`ls input/`). Pick a short slug
`<name>` for it (e.g. a name/word in the art, or the file stem), make its design folder
`orchestrator/output/<name>/`, and normalize into it. The pipeline ingests a raster; the user
may hand you HEIC, SVG, PDF, WEBP, TIFF, PSD, a sideways phone JPEG, anything. The bundled
normalizer applies EXIF rotation, flattens transparency onto a clean ground, rasterizes vector
art big, and collapses CMYK/16-bit to 8-bit:

```bash
mkdir -p orchestrator/output/<name>
.venv/bin/python .claude/skills/orchestrator/scripts/normalize_input.py input/<file> \
    --out orchestrator/output/<name>/<name>_src.png
```

It prints one JSON line (`width_px`, `height_px`, `aspect_w_over_h`, `has_alpha`,
`source_format`, `loaded_via`). **Use `aspect_w_over_h` and the pixel size to sanity-check
your `--width-mm`.** If it reports a missing codec (rare — HEIC/SVG/PDF/RAW), say exactly which
converter is needed rather than failing silently. Feed the **normalized PNG** to every later
step. (If several photos are in `input/`, process each one through the whole workflow into its
own `<name>/` folder.)

### 2. Look at the image and route it ⭐
Actually view the normalized PNG. Decide the category from the **subject and the region
geometry** using the router in `references/routing-and-recipes.md`:

- **Text / a name / a monogram / calligraphy** → **Letters** (Arabic script → **Arabic**;
  a year/score/numeral → **Numbers**). Dominant object: satin.
- **Geometric solid with flat shaded facets** (cube, prism, cylinder) → **3D**. Tatami per
  facet + a distinct angle each + wireframe last. *Prefer to build as SVG, not trace.*
- **Character / portrait / detailed illustration with shading** → **Anime/portrait**. Flat
  fills + shadow satins; 8–12 colours.
- **Bold flat icon / vector shape** (star, heart, arrow, swirl, frame) → **Simple shapes**.
  One object per shape by width; **isacord** chart.
- **Ornamental embellishment** (floral, vine, mandala, wreath, frame, lace, border) →
  **Decoration**. Symmetric/repeating thin satin ornament; **contour_fill**; **size by
  placement** (a border can exceed 1 m).
- **Flat logo / mixed** → decompose into parts, route each, sequence back-to-front.

If the design is **mixed**, segment it and route each part; keep the merged palette small and
use `--purify-colors` (never `--lettering`, which shatters any script).

### 3. Pick the recipe ⭐
Pull size · colours · chart · fill-method · flags from `references/routing-and-recipes.md` (or
playbook §2) for that category. **Why each lever matters — get it wrong and the output is
ruined:**
- **Size sets stroke width.** Too small → satins fall below ~1.6 mm and step-2 *erases* them;
  too big → strokes exceed the satin ceiling and become heavy tatami, exploding the stitch
  count. Choose the size so intended satins land in the category band.
- **`--lettering` vs `--purify-colors`.** `--lettering` dissects glyphs into satin columns —
  right for plain separable block caps, *fatal* for cursive/ornate/cropped glyphs (it shatters
  them). For anything cursive, use the default path + `--purify-colors`.
- **`contour_fill` for thin sprawling shapes *only*** (thin calligraphy/script, swirls, vines,
  long borders) — `auto_fill` over-stitches and can *hang* there. **But broad or thick solid
  shapes** (bold display calligraphy, chunky logos, cut-paper silhouettes, filled facets) must
  stay on `auto_fill` — `contour_fill` traces a wide area as concentric rings and it reads
  **hollow / cross-hatched**. Rule of thumb: contour follows a *stroke*; fill packs an *area*.
- **`isacord` for bright primaries** — Madeira Polyneon has **no pure blue** (ΔE 90). Keep
  `--purify-colors` *off* for custom/pastel colours; it snaps them toward a primary and worsens
  the match.

### 4. Run the pipeline → `orchestrator/output/<name>/`
Point `--output-dir` at the design folder so every artifact lands inside it:
```bash
.claude/skills/orchestrator/scripts/digitize.sh orchestrator/output/<name>/<name>_src.png \
    --width-mm <size> --colors <N> --thread-chart <chart> --category <category> \
    [--lettering | --purify-colors] [--fill-method contour_fill] \
    [--pull-comp-mm 0.05] [--no-fill-underlay] \
    --name <name> --output-dir orchestrator/output/<name>
```
**Always pass `--category`** (the class you routed to in step 2: letters/arabic/3D/anime/
simple-shapes/decoration/numbers). Step 7 then scores the run against that category's
ground-truth fingerprint (`data/category_profiles.json`) and reports **production-fit drift**
— e.g. *"satin_frac 0% vs the truth's 100%; density too sparse"* — so you can see, per run, how
far the output sits from real production files for its class. It never fails the gate; it's
guidance for the iterate loop (§5). Rebuild the profiles with `orchestrator/scripts/fingerprint_vp3.py`
when new ground-truth `.vp3`s are added.
A run takes ~30 s–2 min; it prints a per-step summary and the step-7 gate result. Artifacts:
`orchestrator/output/<name>/<name>_pro.vp3`, `<name>_pro.svg`, `<name>_pro_preview.png`,
`<name>_pro_threadlist.txt`.

### 5. Verify + iterate against the original until it's a faithful copy ⭐⭐
This is the point of an *orchestrator*, not a one-shot: **a gate fail — or any visible drift
from the source — is a signal to adjust flags and re-run, not a stopping point.** Measure every
run objectively with the bundled tools, then loop:

```bash
D=orchestrator/output/<name>
.venv/bin/python .claude/skills/orchestrator/scripts/analyze_vp3.py $D/<name>_pro.vp3
.venv/bin/python .claude/skills/orchestrator/scripts/compare_to_photo.py \
    $D/<name>_src.png $D/<name>_pro.vp3 $D/<name>_overlay.png
```
(`compare_to_photo.py` samples the background from the image border, so a photo on a tan /
coloured / textured ground is measured against its real subject — not counted as ink. Raise
`--bg-tol` on a noisy ground if the overlay shows background bleeding into the source mask.)

`analyze_vp3.py` reports palette, satin-vs-fill (turn-angle reversal %), trims, and per-block
geometry — confirm the object type is right (satin where letters/script should satin).
`compare_to_photo.py` reports **IoU + how much of the source ink the stitches cover** and
writes a RED=source / BLUE=output / PURPLE=match overlay — **view that overlay**; red with no
blue over it is source you dropped.

**"Faithful copy" = ship it when:** gate **PASS** · source coverage **≥ ~85 %** (clean icons
~99 %) · areal density in the category band (Arabic 0.4–0.8, solid icons up to ~15 st/mm²) ·
palette = the intended cones within ΔE · object type per block sane · every element legible in
the preview — **and any remaining drift is *explained* (an inherent raster-trace limit), not a
fixable mistake.** Otherwise diagnose and re-run:

| Symptom (in overlay / analyze / gate) | Likely cause | Fix and re-run |
|---|---|---|
| Coverage < ~85 % overall; whole strokes red-only | design too small → thin strokes erased, or too few colours | raise `--width-mm`; check `--colors` covers each ink |
| Red only at **tips / points / thin marks** | narrow features below 1.6 mm clipping | enlarge so the narrowest part clears ~1.6 mm |
| Gate FAIL on fragmentation; script in illegible pieces | `--lettering` shattered cursive/ornate/cropped glyphs | drop `--lettering` → default path + `--purify-colors` |
| Gate FAIL / hang / density way over band on thin sprawling art | `auto_fill` travel routing over-stitches | add `--fill-method contour_fill` |
| Broad areas / **thick** strokes come out **hollow / cross-hatched** (a woven mesh, not solid) | `contour_fill` traced a wide shape as concentric rings — it is for *thin sprawling* ornament **only** | switch to solid `auto_fill` (bold display calligraphy, cut-paper shapes, chunky logos are broad-solid, not thin) |
| A **phantom extra cone** appears | input wasn't crisp (JPEG ringing / soft scan) | re-threshold to clean flat colour; Arabic → pure-black-on-white |
| Colour reads **neon** where the source is muted/custom | `--purify-colors` snapped a custom colour, or wrong chart | drop `--purify-colors` for that colour; try the other chart |
| Fine hairline **line-art reads pale gray**, not black (single colour) | thin strokes upscale with anti-alias halos → `--colors 1` averages to gray | add `--purify-colors`; **but** if the fill then **crashes** (`contour_fill` `NoneType … length`) or **hangs** (`auto_fill`), do NOT purify — **binarize the source** to crisp black-on-white (threshold ~<200), trace plain `contour_fill`, then if the lone cone still lands gray, **stamp it black** in the `.vp3` (`pe.read` → `thread.set_color(0,0,0)` + catalog/desc → `pe.write_vp3`) and recolour the preview to match |
| Fills where a **letter/script should satin** | strokes above the satin ceiling | smaller `--width-mm`, or `--lettering` (block caps only) to raise the ceiling |
| Output reads **heavier/fatter** than the source (thick tashkeel) | pull-comp/underlay fattening fine marks | `--pull-comp-mm 0.05` (± `--no-fill-underlay`) |
| No pure **blue/red** on a bright icon | Madeira lacks pure blue | `--thread-chart isacord` |

Keep iterating until the ship criteria are met or the only remaining gap is a documented
trace-vs-build limit (§ below). Record what you changed and why between runs.

### 6. Collect, empty `input/`, and hand off
Once the design meets the ship criteria, tidy up so the folders stay clean:
```bash
# move the original photo in beside its results, then clear the drop zone
mv input/<file> orchestrator/output/<name>/
# drop ONLY the fill_to_stroke / stroke_to_satin intermediates — KEEP <name>_working.svg
rm -f orchestrator/output/<name>/<name>_working_[AB].svg
```
Leave **`input/` empty** for the next photo (only its `.gitkeep` remains). The design folder
should now hold: the original, `<name>_src.png`, `<name>_pro.svg`, **`<name>_working.svg`**
(the editable object-level design — every path carries its `inkstitch:*` stitch type + params,
which the VP3 discards), `<name>_pro.vp3`, `<name>_pro_preview.png`, `<name>_pro_threadlist.txt`,
`<name>_overlay.png`.

Then report: the **category and why**, the recipe used, the folder `orchestrator/output/<name>/`
and what's in it, the gate result, the measured coverage/density, and the drift you checked
(with the overlay). State the **honest boundary** when relevant: a raster trace *approximates*
typeset/hand-digitized Wilcom — for a *known* word/solid/primitive, **building** it (Wilcom satin
lettering, an authored SVG, `3D/make_3d_test.py`) beats tracing a picture of it. The `.vp3` is a
faithful, editable intermediate; the licensed `.emb` save is **Phase B** (Windows + Wilcom
dongle, `phase_b/emb_save.ahk`).

## When to *build* instead of trace
For **geometric 3-D solids** and **known primitives** (a perfect star/heart/arrow), author the
design facet-by-facet as an SVG and stitch that rather than tracing — `3D/make_3d_test.py` is
the reusable pattern (per-facet `inkstitch:angle`, underlay, `trim_after`; outline = running
stitch, last). Tracing a 3-D photo loses per-facet angle control. For a *known word*, typing it
in Wilcom's satin lettering tool (Phase B) beats tracing a picture of it.

## Adding a new category
If the user supplies ground-truth `.VP3` files for a subject not covered, follow the **update
protocol in playbook §7**: create `<category>/<category>-embroidery-knowledge.md`, measure the
references with the `tools/` scripts, distil the DNA + a calibrated command, validate
end-to-end, then wire it into the playbook (§1 router, §2 recipe, §8 cheat sheet) and update
`references/routing-and-recipes.md` here.

## Bundled scripts & references
- `scripts/normalize_input.py` — any format → clean RGB(A) PNG (Pillow + pillow-heif + cairosvg,
  with `heif-convert`/`rsvg-convert`/`pdftoppm`/ImageMagick PATH fallbacks).
- `scripts/digitize.sh` — the canonical pipeline wrapper (sets `PYTHONPATH=src`, avoids the
  stale `wilcom-pipeline`/`pip` shebangs, checks Ink-Stitch is vendored).
- `scripts/analyze_vp3.py` — palette, satin-vs-fill, trims, density from a `.vp3`.
- `scripts/compare_to_photo.py` — IoU + source coverage + overlay vs the original (no
  ground-truth needed) — the drift meter for step 5.
- `references/routing-and-recipes.md` — all seven categories' DNA + recipes, condensed.
- [`EMBROIDERY-PLAYBOOK.md`](../../../EMBROIDERY-PLAYBOOK.md) — the master guide (full detail).
