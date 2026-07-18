# Research Brief — Photo→Embroidery Auto-Digitizing Pipeline (for Gemini Deep Research)

> **How to use this file:** it is linked from the prompt in
> `gemini-deep-research-prompt.md` and read by Gemini Deep Research as the system
> summary. It is self-contained, so it also works standalone (uploaded/pasted) if the
> public repo (https://github.com/M-Alsuleibi/ClaudeEmboidery) is unreachable.

## 1. What the system is

A headless Python 3.12 pipeline (Linux, no GUI) that converts a **photo/artwork image
into a production-ready `.vp3` embroidery machine file** plus worksheet and preview,
targeting the quality of a professional digitizer working in **Wilcom EmbroideryStudio**.
Stitch generation goes through the open-source **Ink-Stitch** engine (vendored binary,
run headless) or, for two special primitives, **directly via pyembroidery**.

**Ultimate goal:** fully automatic, category-aware digitizing whose output is
indistinguishable from human-made production embroidery files — correct stitch types,
object composition, sew order, densities, underlay, compensation, and machine
efficiency (minimal trims, hidden travel).

## 2. Architecture (7 ordered steps)

```
① analyze → ② preprocess → ③ thread-match → ④ trace → ⑤ stitches → ⑥ emit → ⑦ verify
```

- **① analyze** — category fingerprinting (letters / numbers / arabic / 3D / anime /
  simple-shapes / decoration / tatreez / animals), foreground separation, feature-size
  warnings.
- **② preprocess** — colour quantization (CIELAB), speck/hairline auto-repair, black
  keyline snap, palette purification modes.
- **③ thread-match** — nearest cone in commercial thread charts (Isacord,
  Madeira Polyneon) via ΔE in Lab.
- **④ trace** — vtracer vectorization into one SVG group per thread colour, ordered
  background-first by enclosure depth; seam **underlap** (earlier-sewn regions extend
  0.5 mm under later-sewn neighbours).
- **⑤ stitches** — the core digitizer. Each connected region is tiered **by its own
  width** (area ÷ skeleton length): `run` (< 1.6 mm centerline bean stitch), `satin`
  (single column; fixed-width ≤ 3 mm, **variable-width rails from local medial-axis
  half-width** 3–7 mm), or `tatami fill` (wider / branchy). Satin ceiling is
  category-aware (7 mm for satin-dominant categories per the Wilcom manual, 3 mm
  conservative default). Closed **satin border objects** are layered over substantial
  fills (the production "outline family"). **Travel planning** chains regions
  nearest-neighbour, pins fill entry/exit points, and drops trims only when travel is
  ≤ 12 mm and ≥ 90 % covered by later stitching.
- **⑥ emit** — VP3 with named cones in sew order + realistic thread-render preview.
- **⑦ verify** — a real gate: coverage/IoU vs source, density stacking map (warn > 5
  satin-layers over > 10 mm²), needle-penetration spacing (< 0.3 mm risk), stitch
  budget vs category profile, drift score vs per-category ground-truth fingerprints.

Two categories bypass the tiering with dedicated primitives built directly in
pyembroidery: **counted cross-stitch** (Palestinian tatreez: fixed ~2.1 mm grid, one X
per majority-covered cell) and **sketch stitch** (animals: ~4 mm doubled-back "fur
flick" strokes along a structure-tensor direction field measured from the source art).

## 3. The learning loop (measured ground truth)

The system calibrates itself from **production pairs**: (CorelDRAW SVG, production VP3)
files made by professional digitizers. An ingestion script registers SVG↔VP3
(trimmed-ICP, ~0.29 mm RMS), labels every object (width in mm, density, row spacing,
satin-vs-tatami verdict), and rebuilds two data files consumed by the pipeline:

- `category_profiles.json` — step ⑦'s drift gate (per-category stitch-type fractions,
  width/density medians).
- `pair_priors.json` — steers step ⑤ automatically: the measured satin/fill width
  crossover becomes the satin ceiling, the measured satin-width band becomes the
  variable-width clamps, the satin median becomes the border width. A category with no
  pairs keeps hand-calibrated constants.

Current corpus: ~25+ ingested pairs across anime, tatreez (11), animals (10), plus
per-category reference VP3s and a distillation of the official **Wilcom Reference
Manual (1549 pp.)** into decision rules (satin ceiling ≈ 7 mm via Auto Split, density
0.3–0.6 mm, pull-comp by fabric 0.20–0.40 mm, underlay by column width, colour-count
priors per photo type).

## 4. What is already implemented (do not re-propose)

- Per-region run/satin/tatami tiering with category-aware satin ceiling; variable-width
  satin rails; turning satin (EDT iso-contour rings); per-branch satin dissection with
  junction-continuity chaining (Arabic calligraphy: branch fragments merged into
  continuous pen strokes).
- Outline/border satin objects over fills; seam underlap; entry/exit travel planning
  with covered-travel trim elimination; per-colour digitize fallback with retry ladder
  (Ink-Stitch's router can hang; pull-comp 0 is a measured hang trigger).
- Auto artwork repair (speck merge, hairline thicken, same-cone palette merge);
  sewability gate (stacking / penetration / stitch budget) calibrated on production
  VP3s; pull-comp by fabric table; satin & fill underlay by width.
- Counted cross-stitch and sketch-stitch primitives (direct pyembroidery); accent
  colour recovery; open letter counters; gradient de-posterization (experimental);
  category colour-count priors; automated pair ingestion → priors loop.

## 5. Known open gaps (the research targets)

1. **Raster stroke recovery.** For calligraphy/script, recovering the *pen-stroke
   structure* (ordered centerline strokes with width, overlap and stroke direction)
   from a raster image has no good off-the-shelf tool. Current approach: skeleton +
   per-branch dissection + junction chaining — works but is heuristic. Stitch
   *direction* can still be wrong even when stitch-type fractions match ground truth.
2. **Stitch direction / angle fields for fills.** Production tatami and turning satin
   follow form-aware stitch angles. We have a structure-tensor field only for the
   sketch primitive; general fills use Ink-Stitch defaults.
3. **Satin quality on curves/corners.** Wilcom has auto-spacing (density recalculated
   wherever column width changes), fractional spacing (inside-curve bunching),
   stitch shortening, and smart corners (mitre/cap/lap by angle). Ink-Stitch exposes
   only some of this; none is wired in our pipeline.
4. **Learning-based digitizing.** A sibling project (photo→VP3 via ML) is blocked on
   paired (artwork, stitch-file) training data. Are there public datasets, generative
   or imitation-learning approaches, or papers on embroidery auto-digitizing?
5. **Fingerprint/metric blind spots.** Stitch-type classification from raw stitch
   sequences is heuristic (turn-angle based); Auto-Split satin reads as tatami without
   a dedicated detector. Better sequence-level stitch-object segmentation/classification
   would improve both the verify gate and pair labelling.
6. **Photo realism tier.** True photo-stitch (Wilcom Color PhotoStitch: run-stitch
   colour blocks; also cross-hatch/sfumato styles) is not implemented — current
   photo handling is posterize-and-fill.
7. **Push–pull distortion modelling.** We apply static pull-comp tables; production
   quality would benefit from a fabric/stitch physical model predicting distortion per
   object (direction-dependent), not a uniform widening band.
8. **Editable-format interop.** `.emb` (Wilcom native) is proprietary-encrypted; the
   deliverable is `.vp3`. Any public research on richer editable interchange (e.g.
   Wilcom ESA fonts, OFM/PXF ecosystems, Tajima DST-with-metadata conventions) could
   improve round-tripping.

## 6. Wilcom production features not yet matched (from its own manual)

Auto-spacing satin density; Auto Split penetration-line randomization; fractional
spacing + stitch shortening on curves; smart corners (mitre/cap); "by shape" underlay;
motif/decorative fills and motif runs; program splits / textured fills; gradient &
blend fill effects (accordion spacing, colour blending); raised satin / 3D foam;
sequin/bead/chenille (out of scope); keyboard lettering engine with ESA fonts;
Color PhotoStitch; branching objects as first-class (single object with multiple
branches, automatic underpathing); automatic small-stitch removal on scale.

## 7. Hard constraints (proposals must respect these)

- **Headless Linux**, Python 3.12; no Wilcom license at runtime; no GUI automation.
- Stitch engines available: **Ink-Stitch binary** (headless CLI; its router can hang —
  we have a retry ladder) and **pyembroidery** (direct stitch-level writing, proven by
  the cross-stitch/sketch primitives — so *any* stitch pattern we can compute, we can
  emit without Ink-Stitch).
- Output format: `.vp3` (validated); ground truth arrives as production VP3s.
- Structural laws from the user: large regions are TATAMI (never contour-fill
  replacements); trims between visibly disjoint pieces are deliberate Break-Apart
  boundaries; priors tune numbers, never overturn structure rules.
