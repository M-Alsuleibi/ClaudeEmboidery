---
name: arabic-satin-only-law
description: "satin_only prior = the category law (arb trio absolute truth): PER-BRANCH dissection (all skeleton branches -> vwidth columns, throws perpendicular to strokes) + residual patch cover, authored 0.24 spacing (x2 for Ink-Stitch) / underlay-off / pull-comp-0 / <=7mm connector chains; STITCH DIRECTION is the drift the fingerprint can't see"
metadata:
  type: project
---

**The arb trio (`arabic/pairs/arb/`) is the ABSOLUTE source of truth for arabic** — and
the mechanism is generic: any category whose pairs measure `satin_only` (< 5 % fill
verdicts, build_pair_priors) inherits the whole behaviour with zero category-name code
(sessions 2026-07-17/18; converged from satin 93.2 %/33 trims/37k).

**THE DEEPEST LESSON (2026-07-18, user showed Wilcom side-by-side): the aggregate
fingerprint (satin_frac 100, count in band) can be satisfied while the STITCH DIRECTION
is wrong everywhere.** The first "converged" build covered merged regions with
turning-satin RINGS — boundary-parallel throws — and read 100 % satin while looking
nothing like production in Wilcom (spiky chaos, `input/arb-v2.svg`). Production sews
~1,600 columns whose throws run PERPENDICULAR to each pen stroke. Direction/structure
must be verified by RENDER comparison (and the fan detector + movement histogram), never
by satin_frac alone.

**The law, all prior-driven (`priors.py` → step 5):**
1. `priors.satin_only(cat)` **auto-enables the satin-lean path** (no `--satin-lean`
   flag) and **dissects EVERY region into ALL its skeleton branches** (`keep = longs`,
   uncapped/ungated; min_pts lowered to the vwidth floor 6; run demotion OFF — thin
   linework = narrow Column-C satin, not bean runs). Each branch → hairpin-split →
   vwidth column at local width (band clamps 0.8–3.5). **Then the RESIDUAL COVER pass**
   (`_residual_cover_lines`): rasterize the region (evenodd — keep counters), subtract
   the built columns' swept footprints, tile substantial leftovers (≥2.5 mm²) with
   ring/strip patch columns — branch columns alone leave junction lobes bare (measured
   62 % source-ink coverage; with residual cover 95.7 %). Rings only ever appear as
   residual patches or for centerline-less dots. Ceiling = authored Auto-Split (7 mm).
2. **Authored Fills-tab density**: `authored.satin_auto_spacing_mm` (0.24 @ 90 %,
   parsed per tab type + auto-checkbox state incl. greyed `checked`) → flat
   `zigzag_spacing_mm` on every column. **FLAT, not width-curved** (a curve opening
   to the manual median under-stitched to 35k vs the 41–51k band) — and **DOUBLED**:
   Wilcom spacing = per-penetration advance, Ink-Stitch zigzag_spacing_mm =
   peak-to-peak (full cycle = 2 stitches); passing 0.24 straight sews exactly 2×
   density (measured 82k vs 46k). `_authored_satin_spacing` returns 0.48.
3. **Authored underlay/pull-comp**: `underlay_disabled_frac` ≥ 0.5 → satin underlay
   off; wide (>3 mm) vwidth columns still get zigzag + center-walk on the ELEMENT (the
   video's "Double-Tatami only on wide Column-A pieces"). `pull_comp_disabled_frac`
   ≥ 0.5 → pull-comp 0 unless `--pull-comp-mm` passed.
4. **Authored Connectors (Jump / Trim-after Off / Tie-in Off)**: `_plan_travel` drops
   every within-colour trim (no 12 mm cap, no cover law — reference sews ~275 mm
   draped). **A STITCH→JUMP thresholding pass was tried and REVERTED** (VP3 has no
   jump opcode; converting bloated the file with 7k writer-split jumps). What
   production ACTUALLY does with connectors — its movement histogram: 812 @4–6 mm,
   338 @6–8 mm, only 15 >8 mm in 46k — is **split every mid-length travel into ≤ the
   authored Jump length (7.0 mm) segment chains**; only big arc-to-arc repositioning
   moves (>20 mm) stay single. `_split_long_travels` (post-digitize) implements this
   via `priors.authored_jump_mm`; our un-split 8–13 mm hops were what fragmented the
   design on Wilcom import (the scattered CorelDRAW view).
5. **Geometry guards found once everything satins** (all were 16–29 thread layers
   piled on a spot; reference max 3.6): rings shorter than **1.6π·strip** "urchin"
   (inner rail inverts) → dropped to the straight-strip fallback; snaking vwidth
   centerlines AND ring/strip arcs are **split at hairpins** (`_hairpin_bounds`,
   >75° chord turn over 0.75 mm steps, ≥3 mm pieces — stroke_to_satin's rail-split
   pairs a tiny rail with the whole outline on a folded arc = sunburst fan);
   **closed loops (net turning >300°) are cut into two open half-arcs** (closed-loop
   rail pairing fans; a FAN DETECTOR now exists: windows where one rail's ends
   cluster <1.6 mm while the other spreads >6 mm — reference 0, first build 26,
   final 2); ring depths at **full strip pitch** so rings TOUCH (the old
   equalise-down step overlapped rings up to ~50 % = 2× thread); strip width from
   the **reference fingerprint's stitch-length median** (arabic 2.4 mm), NOT the
   register column-width median (1.75 — under-shoots satin_w band + over-stitches).
   NOTE: stroke_to_satin does NOT emit rails — it emits the swept OUTLINE as one
   subpath (net turning ~360°) and Ink-Stitch splits it at sew time, so "single
   subpath satin" in the working SVG is normal, not a failure.
6. **Step-7 drift bands recalibrated FROM the references**: profiles carry lo/hi
   (observed min/max) and `drift_check` bounds on them (p25–p75 fallback) — the
   reference VP3 itself must never flag DRIFT (it did: n_colors 3 vs [1,1]).

**Converged result** (rebuild `samples/arb_input.png --width-mm 302 --category arabic
--colors 2 --purify-colors --no-outline-objects --thread-chart isacord, 2026-07-18
structure convergence): satin_frac 100, fill_frac 0, 3 trims, **47,601 stitches**
(reference 46,081), **987 columns** (production 1,618; 198 of them residual patches),
satin_w 2.22 (reference 2.14), density 0.75 (ref 0.68), stacking worst 5.7 layers /
2.2 mm² (ref 3.6/0 — gate PASSES), fans 2 (ref 0), moves 8–20 mm 0 (ref 8),
source-ink coverage **95.7 %**, stroke-following stitch direction verified by render.

**The old arabic recipe is DEAD: never pass `--fill-method contour_fill`** — see
[[contour-fill-for-calligraphy]] (now other-categories-only) and
[[arabic-no-outline-objects]] (`--no-outline-objects` still required). See
[[arb-trio-video-ground-truth]], [[pair-priors]], [[travel-plan]].
