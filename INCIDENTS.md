# Incident log — embroidery pipeline

Append-only record of production bugs: what broke, at which pipeline stage, the root
mechanism, and what now guards it. **Purpose: diagnosis speed** — before debugging a new
symptom, grep this file (and run `/drift-debug`, whose known-mechanisms list mirrors it).
The *prevention* lives in the regression tests named here; an entry without a guarding
test is an open risk. One `##` section per incident, newest first.

Template:

```
## YYYY-MM-DD — <category> — <one-line symptom>
- **Stage:** <pipeline step or component>
- **Mechanism:** <the actual cause, one paragraph max>
- **Fix:** <commit sha + one line>
- **Guard:** <test name / gate check / "none — open risk">
```

---

## 2026-07-17 — arabic — rebuild drifted from the arb trio (93% satin, 33 trims, 37k stitches vs 100%/2/46k)
- **Stage:** step 5 (tiering gates + travel planner) and step 7 (drift bands)
- **Mechanism:** five generic gates blocked convergence on the trio truth: ① the
  satin-lean path needed the `--satin-lean` flag, so the recipe's default run kept
  broad regions as fills; ② `_MAX_SATIN_COLUMNS = 80` demoted all satin candidates
  back to fills on a design production digitizes as 1,618 columns; ③ the travel
  planner's 12 mm cap + cover law kept trims the authored Connectors (Jump /
  Trim-after Off / Tie-in Off) never sew; ④ satin density/underlay/pull-comp used
  Ink-Stitch defaults, not the authored 0.24 mm @ 90 % auto-spacing / underlay-off /
  pull-comp-0; ⑤ step 7's drift bands were p25–p75, so the reference VP3 *itself*
  flagged DRIFT (n_colors 3 vs the [1,1] band). Two secondary geometry defects
  surfaced once everything satined: sub-π·strip turning rings and hairpin-folded
  vwidth rails both sunburst-fan (16–29 thread layers on a spot vs reference max 3.6).
- **Fix:** all prior-driven, never category-named — `satin_only` in pair_priors
  auto-enables the lean path + lifts the column/run caps; `authored` block gained
  satin (auto-)spacing, parsed per Fills-tab type + auto-checkbox state; authored
  underlay/pull-comp/trim-after read from the props; `_plan_travel` drops
  within-colour trims unconditionally for trim_after_off categories (connectors stay
  plain long STITCH movements — a STITCH→JUMP thresholding pass was tried and
  REVERTED: the reference VP3 itself encodes its 275.7 mm connector as a stitch, 2
  jump commands total; converting bloated the file with 7k writer-split jumps).
  Calibration findings, each measured against the reference: ① Wilcom's authored
  "Spacing" is per-penetration advance while Ink-Stitch's zigzag_spacing_mm is
  peak-to-peak (one full cycle = 2 stitches) — the authored value must be DOUBLED or
  density sews exactly 2× (82k vs 46k); ② turning rings must TOUCH (depths at full
  strip pitch): the old equalise-down step made rings overlap up to ~50 % (92k
  stitches); ③ ring/strip arcs and snaking centerlines are split at hairpins (>75°
  chord turn over 0.75 mm steps) — stroke_to_satin's rail-split pairs a tiny rail
  with the whole outline on a folded arc and sews sunburst fans (16–29 thread layers
  vs reference max 3.6); ④ rings shorter than 1.6π·strip "urchin" (inner rail
  inverts) and are dropped to the straight-strip fallback; ⑤ strip width comes from
  the reference fingerprint's stitch-length median (arabic 2.4 mm — the register
  pass's column-width median 1.75 under-shoots the band and over-stitches);
  ⑥ fingerprint profiles now carry lo/hi (observed range) and drift_check bounds on
  them, so a reference file can never drift against its own category.
  Converged rebuild: satin 100 / fill 0 / 3 trims / 50,359 stitches (reference
  46,081) / stacking worst 7.0 layers / production_fit all ok / coverage 90.8 %.
- **Guard:** tests/test_pair_priors.py (satin-only law, ceiling precedence, authored
  spacing aggregation), tests/test_travel_plan.py (trim-after-off drops the 60 mm
  uncovered travel; cover law intact without the prior), tests/test_vwidth_satin.py
  (hairpin split), plus the arb rebuild acceptance (satin 100/fill 0/trims 3/
  stitches in band, production_fit all ok)

## 2026-07-17 — arabic — middle calligraphy arc largely unstitched (region demoted to bean runs)
- **Stage:** step 5 `_linework_prepass` run tier (per-region width tiering)
- **Mechanism:** the middle arc traced as ONE 1,090 mm² connected region whose
  **area-weighted average width was 1.36 mm** — thin inter-letter connectors dragged a
  band full of 3–4 mm strokes under the 1.6 mm run threshold — so the run tier turned
  the whole region into 6 bean runs and dropped its fill (~15 % coverage; verify still
  PASSed — density/budget gates don't see a missing region). A first theory
  ("fill_to_stroke consumed originals") was disproved by a standalone pass-A probe:
  the on-disk `working_A.svg` is post-decision state, its "missing" originals were the
  deliberately dropped run/satin regions. Found by stage bisection: quantized ok →
  step-4 SVG ok (27.5k px in window) → working SVG 9k px.
- **Fix:** `_run_demotion_ok` — a sub-1.6 mm region only demotes to runs when it is
  small (≤ 150 mm²) OR its long centerlines carry ≥ 60 % of the skeleton (a genuine
  hairline); a large spur-dominated region stays a fill (the "large regions = tatami"
  hard rule) and the satin tier routes it via `_keep_as_fill`.
- **Guard:** `test_run_demotion_guard_keeps_large_meshy_region_as_fill`
  (tests/test_stitches.py, pure unit — proven to fail with the guard reverted)

---

## 2026-07-13 — animals — sketch strokes read as FILL (satin_frac 4 vs truth 92–100)
- **Stage:** step 5 (`steps/sketchstitch.py`), twice during construction
- **Mechanism:** two turn-geometry traps: ① serpentine scanline rows turn 90° at row
  ends — never counted as reversals (fingerprint needs >150°); ② return passes starting
  at a lateral offset split the 180° pivot into two 90° jogs (block reversal 3%). Strokes
  must pivot at shared endpoints and fan out at the far end; short flicks (~4.2 mm) give
  the closely-spaced reversals the split-satin rule keys on.
- **Fix:** sketch_stitch primitive commit; calibrated pitch 1.7 mm / spacing 0.75×prior
- **Guard:** `tests/test_sketch_stitch.py` (structure + direction tests); step-7
  production_fit satin/fill/density bands vs the animals profile

## 2026-07-13 — animals — meander_fill crash sank whole runs
- **Stage:** step 5 Ink-Stitch digitize
- **Mechanism:** meander_fill raises "Could not build graph" on regions without room for
  a pattern cell — fur slivers pass a bbox test but not the graph build (thinness, not
  extent, is the constraint); a hard crash bypassed the timeout-only per-group fallback.
- **Fix:** `1fed579` — mean-width gate (2·area/perimeter ≥5 mm + 8 mm extent), crash →
  per-group fallback, strip-meander-to-tatami retry rung
- **Guard:** exception paths in `_digitize`/`_try_digitize`; superseded for animals by
  the sketch primitive (meander no longer the recipe)

## 2026-07-13 — falahi/tatreez — OOM-killed run (5.1 GB python) on a garment panel
- **Stage:** step 4 (vtracer) — which cross-stitch never needed
- **Mechanism:** frame-hugging design made the border-ring MEDIAN the navy ink colour, so
  background keyed on ink → white ground stayed foreground → AA speckle exploded into
  thousands of components → vtracer allocated unboundedly. Trace was running for a
  category that builds stitches directly from the quantized grid.
- **Fix:** `f9125e0` — cross-stitch (and later sketch) categories skip trace; recipe
  side: pad 6% white margin when the border median isn't the page colour, snap near-white
  ground to pure white
- **Guard:** trace skip is structural; border-median check is a drift-debug/memory
  diagnostic (no automated gate — open risk for frame-hugging designs in traced categories)

## 2026-07-13 — anime — facial linework invisible (three stacked causes)
- **Stage:** steps 2, 5-order, and 4 — found by stage bisection, one cause hiding the next
- **Mechanism:** ① `preprocess._consolidate` (k×k mode filter, k grows with design mm)
  erased interior black strokes; ② black = base panels AND detail linework in ONE sew
  stop — depth order sewed black early and the skin fill's pull-comp closed the sub-mm
  hole over it; ③ vtracer's whole-image cutout culls 1–2 px strokes even at
  filter_speckle=0 (isolated trace keeps them) — and the sew-last detail layer was the
  one colour underlap never isolated-re-traced.
- **Fix:** `6db1cae` — snap-black re-imposed after consolidate; `_split_keyline_detail`
  → sentinel (1,1,1) layer pinned last; detail layer always isolated-re-traced
- **Guard:** `test_interior_black_linework_survives_consolidate`,
  `test_sew_order_keyline_detail_layer_sews_last`, `test_keyline_detail_group_keeps_thin_stroke`

## 2026-07-13 — anime — white shirt never stitched (subject cut off by frame)
- **Stage:** step 2 background flood (`imaging.py`)
- **Mechanism:** any bg-like component touching the border was background — including a
  white garment exiting the bottom of the frame.
- **Fix:** `2112d1c` — background needs an image corner or ≥25% border-contact
- **Guard:** mask behaviour covered by `tests/test_preprocess.py` /
  `tests/test_analyze.py` suites; edge-touching modes catalogued in drift-debug
