---
name: arabic-satin-only-law
description: "satin_only prior = the category law (arb trio absolute truth): auto all-satin (no flags), authored 0.24 flat spacing / underlay-off / pull-comp-0, trims at colour changes only + STITCH→JUMP connectors; NO contour_fill; converged 100/0/3 trims/~46k"
metadata:
  type: project
---

**The arb trio (`arabic/pairs/arb/`) is the ABSOLUTE source of truth for arabic** — and
the mechanism is generic: any category whose pairs measure `satin_only` (< 5 % fill
verdicts, build_pair_priors) inherits the whole behaviour with zero category-name code
(session 2026-07-17, goal-driven convergence from satin 93.2 %/33 trims/37k).

**The law, all prior-driven (`priors.py` → step 5):**
1. `priors.satin_only(cat)` **auto-enables the satin-lean path** (no `--satin-lean`
   flag): every colour enters the linework pre-pass, every region satins — vwidth
   columns for strokes, turning-satin rings for broad bands, single-strip fallback for
   dots. `_MAX_SATIN_COLUMNS`/`_MAX_RUN_STROKES` overflow demotions are lifted
   (production digitizes 1,618 columns). Satin-only ceiling = authored Auto-Split
   length (7 mm), outranking even lettering/satin-lean regimes; vwidth clamps = the
   measured width band (arb 0.8–3.5 mm) even on the lean path.
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
   draped). **A STITCH→JUMP thresholding pass was tried and REVERTED**: measured, the
   reference VP3 encodes its connectors as plain long STITCH movements (max 275.7 mm,
   only 2 jump commands in 46k) — Wilcom's VP3 convention lets the machine drape an
   overlong stitch itself; converting bloated the file with 7k writer-split jumps.
   Leave connectors exactly as Ink-Stitch emits them.
5. **Geometry guards found once everything satins** (all were 16–29 thread layers
   piled on a spot; reference max 3.6): rings shorter than **1.6π·strip** "urchin"
   (inner rail inverts) → dropped to the straight-strip fallback; snaking vwidth
   centerlines AND ring/strip arcs are **split at hairpins** (`_hairpin_bounds`,
   >75° chord turn over 0.75 mm steps, ≥3 mm pieces — stroke_to_satin's rail-split
   pairs a tiny rail with the whole outline on a folded arc = sunburst fan) = the
   tracer's version of production's per-stroke dissection (939→701 columns, vs
   production's 1,618); ring depths at **full strip pitch** so rings TOUCH (the old
   equalise-down step overlapped rings up to ~50 % = 2× thread); strip width from
   the **reference fingerprint's stitch-length median** (arabic 2.4 mm), NOT the
   register column-width median (1.75 — under-shoots satin_w band + over-stitches).
6. **Step-7 drift bands recalibrated FROM the references**: profiles carry lo/hi
   (observed min/max) and `drift_check` bounds on them (p25–p75 fallback) — the
   reference VP3 itself must never flag DRIFT (it did: n_colors 3 vs [1,1]).

**Converged result** (rebuild `samples/arb_input.png --width-mm 302 --category arabic
--colors 2 --purify-colors --no-outline-objects --thread-chart isacord`): satin_frac
100, fill_frac 0, 3 trims, **50,359 stitches** (reference 46,081; band 41–51k),
satin_w 2.38 (band 1.94–5.73), stacking worst 7.0 layers, production_fit all ok,
source-ink coverage 90.8 % (the tip-clipping honest limit), all three arcs + Allah
glyph complete.

**The old arabic recipe is DEAD: never pass `--fill-method contour_fill`** — see
[[contour-fill-for-calligraphy]] (now other-categories-only) and
[[arabic-no-outline-objects]] (`--no-outline-objects` still required). Honest residual
drift: the tracer sweeps MERGED regions (~300 columns, med ~3 mm) where production
hand-digitizes ~1,600 per-stroke columns (med 1.75 mm), so local stacking stays above
reference; the stacking gate warn is expected on arabic rebuilds. See
[[arb-trio-video-ground-truth]], [[pair-priors]], [[travel-plan]].
