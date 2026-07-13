---
name: per-region-tiering
description: "step-5 stitch-type tiering is now PER-REGION + AREA-weighted (not per-colour ridge-median); disproves the old 'enlarge→satin' advice; width calibration gotcha"
metadata: 
  node_type: memory
  type: project
  originSessionId: d236c827-c714-4db2-82d2-79216f18217b
---

Step 5 (`steps/stitches.py`) tiers each stroke object **per REGION (connected component),
by that region's own width** — so one colour can mix a thin keyline (run), a medium stroke
(satin), and a solid blob (fill). A colour only *enters* the linework pre-pass if its
**area-weighted** width is below the satin ceiling (a solid fill isn't skeletonised); the
run/satin/fill verdict is then taken per block in `_linework_prepass`.

**Why area-weighted, not the ridge-pixel median (`_area_weighted_width`):** a thin line is
nearly all ridge, so by ridge-pixel *count* a scatter of thin scraps out-votes a colour
whose bulk is one bold band. Measured on `input/turtul.jpeg`: the Old Gold shell band tiered
satin@280/360 mm but **flipped to a thin `run`@480 mm** — non-monotonic, i.e. *enlarging made
it worse*. This **disproves the earlier "just enlarge so the outline clears 1.6 mm → satin"
advice** (see [[satin-underlay-and-thin-line-run]], corrected). Weighting the width by region
AREA fixed it: Old Gold is satin at 280/360/480 mm, stable.

**Per-region width = region outline area ÷ FULL skeleton length, in mm** (`_block_width_mm`,
`_poly_area_uu2` / `_polyline_len_uu`; trace SVG has `viewBox` in working-px and `width` in
mm, so `_mm_per_uu` converts; area & length are translation-invariant → vtracer per-path
translates need no bookkeeping). **Calibration gotcha:** divide by the length of **all**
centerlines (incl. spurs), not just the substantial (`_MIN_SATIN_PTS`) ones — dividing by the
long ones alone made a branchy 1.2 mm band read **9.96 mm** (→ wrongly fill).

**Proven** with a synthetic: one black colour, a 0.8 mm wavy band + a 1.9 mm wavy band →
Ink-Stitch reports **1 run stroke + 1 satin column** from that single colour (per-colour
tiering structurally can't). Turtle output at 360 mm is **unchanged** (its colours are
uniform per-colour, so per-region == per-colour there — no regression; 50/50 tests pass).

**Broad-colour splitting — DONE:** the entry gate now also admits a *broad* colour (solid
blob dominates its area-weighted width) if it carries a **substantial** sub-ceiling region
(area >= `_MIN_LINEWORK_PX` = 250 px on the ~1200px work canvas) — so a logo whose black is a
big wordmark PLUS a thin keyline splits the keyline out (run/satin) while the blob stays a
fill. Proven: one black colour = solid disk + long thin keyline → OLD gate = 0 satin/all fill
(keyline buried), NEW = 1 satin column + disk fill. The 250 px floor keeps quantisation
scraps out, so the turtle is unchanged (green's only thin region is 104 px). Downstream
`_MIN_SATIN_PTS` + the `_MAX_RUN_STROKES`/`_MAX_SATIN_COLUMNS` guards bound any noise/blowup.

**Branchy-satin — DONE (opt-in `--branch-satin`, default OFF):** dissects a *forked* stroke
region in the satin band into one satin per branch (generalising lettering's glyph
dissection to organic art — a calligraphic ر, an ornament limb). Guarded so it fires only on
a FEW long branches (2..`_MAX_BRANCH_SATINS`=12) whose length is >=`_BRANCH_COVER_MIN`=0.6 of
the skeleton — a dense **mesh** stays one fill. Key mechanic learned here: `fill_to_stroke`
DOES centerline wide bands (its `--threshold_mm` prunes dead-ends, it's NOT a width gate),
but a turtle-shell-type band skeletonises into ~80 SHORT (<`_MIN_SATIN_PTS`) segments — 0
longs — so it correctly stays a fill; a clean forked band gives a few long branches → satins.
Proven: a Y band → 0 satin/all-fill when off, **3 satin columns** when on. Off by default
because per-branch satins leave small junction gaps (measured 100%→97.8% source-cover on the
Y) and restructure the sew path. No-op under `--lettering` (already dissects). All three tiers
(run/satin/fill) are now per-region, broad-colour-reachable, and branch-capable. Ties to
[[vp3-production-knowledge]].

**CEILING RAISED to ~7mm but CATEGORY-GATED (2026-07, see [[wilcom-manual-rules]]).** `_satin_ceiling(
lettering, satin_lean, satin_dominant)`: 9mm (lettering/satin-lean) · **7mm if the category is
satin-dominant** (arabic/letters/decoration/simple-shapes/numbers per `category_satin_dominant`) ·
**3mm otherwise** (3D/anime/unknown — their shaded solids are tatami fills; a blanket 7mm
over-satins them). Constants: `_SATIN_MAX_WIDTH_MM`=3.0 (conservative default), `_SATIN_DOMINANT_
CEILING_MM`=7.0. Within the satin band: ≤`_SATIN_FIXED_MAX_MM`(3mm) → fixed-width `stroke_to_satin`;
3–7mm → **variable-width by default** (`vwidth_all or w_mm > 3` triggers `_build_vwidth_satin`) since
a uniform width under-covers a wide modulated stroke. So the gap closes BY DEFAULT on satin-dominant
stroke art: Design6 arabic, no flags → satin_frac 0→100, coverage 99.3%. **CAVEAT LEARNED:** a
blanket raise (my first cut) over-satined — hence the gating. Note gold-2026 (3D metallic lettering)
reads ~92% satin at EITHER ceiling because its strokes are ~1.2mm (satin at any ceiling) — that's
pre-existing per-region behaviour + a 3D category-granularity mismatch (geometric-solid truth vs
lettering), NOT caused by the raise; its output is actually a faithful gold 2026. **Underlay-by-width**
(manual p412): a wide vwidth column (built median >3mm) stamps `zigzag_underlay`; narrow → center-walk.
Tests: test_vwidth_satin.py (4). 65 pass. Ties [[vwidth-satin]].
