---
name: outline-objects
description: "step-5 --outline-objects (AUTO-on for satin-dominant categories): closed satin border over each substantial fill = the production 'outline family' (pink-goku 217:118); joker satin +33pts, geometry unchanged"
metadata: 
  node_type: memory
  type: project
  originSessionId: ee38cb46-50c4-4289-9a91-f72500225c4c
---

**Built 2026-07-11 (NEXT-GOALS G1).** `--outline-objects` (tri-state; AUTO = on iff
`category_satin_dominant`, resolved in `stitches.run`): every substantial (≥40 mm²) fill region
gets a CLOSED satin border riding its boundary — centerline = EDT iso-contour at depth w/2
(`_border_centerlines`, evenodd `_region_raster` so counters/holes get rings too), emitted as a
stroke right AFTER its fill in the same colour group → one `stroke_to_satin` batch → satin
params stamped on the unstamped columns. Border width = category profile satin_w_mm med clamped
1.5–3.0 (`_outline_border_w_mm`). Best-effort with rollback. This is the generator for the
production "outline family" the pink-goku pair exposed (217 outline vs 118 fill objects).

**Measured:** goku render — 38 borders, satin_frac 91.9→100, satin_w 1.37→2.2 (truth 2.25),
coverage 99.7 unchanged, IoU −0.9. Joker — 22 borders, per-piece satin 20.4→53.6 % (+33), fills
still tatami (46 %), coverage 90.6 unchanged, IoU −0.4, per-group path + pull-comp-0 rung intact.

**Gotchas:** ① `stroke_to_satin` RENAMES the border ids — assert structure (fill followed by
same-colour satin_column in the group), never `id="border*"`, in tests. ② step-7's satin_frac
splits on COLOR_CHANGE only, so fills+borders in one block read 100 % satin — measure honestly
at TRIM+CC piece granularity (joker: 53.6 %). ③ a render-of-satin input (vp3_to_photo of a
production file) is already ~90 % satin at baseline — don't calibrate satin-gap acceptance on
it; use broad-region art (joker). ④ density rises at fill/border overlap (deliberate, like
production) — the stacking gate is [[NEXT-GOALS]] G5. Ties [[svg-vp3-pairs]],
[[vp3-fingerprint-and-satin-gap]], [[large-regions-tatami]].
