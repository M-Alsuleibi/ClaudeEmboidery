---
name: underlap
description: "step-4 --underlap-mm (default 0.5): earlier-sewn colour re-traced from a dilated mask so it extends UNDER later-sewn neighbours; cross-seam stitch overlap 1.1→1.6mm; trace is ONE vtracer cutout pass so overlap requires per-colour re-trace"
metadata: 
  node_type: memory
  type: project
  originSessionId: ee38cb46-50c4-4289-9a91-f72500225c4c
---

**Built 2026-07-11 (NEXT-GOALS G2).** `--underlap-mm` (default 0.5, 0 = byte-identical old
trace): production objects overlap — an earlier-sewn fill extends under its later-sewn
neighbour so fabric pull can't open a seam gap.

**Key architectural fact:** trace.py runs vtracer ONCE on the whole image
(`hierarchical="cutout"`) — a flat image can't express overlap, so underlap RE-TRACES each
seam-adjacent colour alone from its dilated mask (`_underlap_masks`: dilation clipped to the
union of later-sewn colours' pixels, walking `_sew_order` backwards; background + opened
counters are transparent = in no mask = never claimed) and replaces that colour's paths
(`_trace_single_colour`). Later colour untouched. Gradient-cluster members skipped.
`_linework_indices`/width gating read the IMAGE masks, not the SVG — unaffected.

**Measured:** abutting rects — cross-seam stitched overlap 1.1 → 1.6 mm (+exactly
underlap_mm; the 1.1 base is pull-comp + zigzag edge stagger). Joker: extent identical,
coverage −0.1, IoU −0.2, gate PASS, per-group/pc0 ladder intact. Letters: +0.4 coverage.

**Gotchas:** ① don't measure the seam as "white px in a band" — a rendered tatami never
covers ≥~75% of any band (inter-row texture), so that metric is noise; measure the two
blocks' cross-seam OVERLAP WIDTH + absence of a void column (tests/test_underlap.py
`_seam_overlap_mm`). ② scipy `binary_dilation(iterations=0)` means "until convergence" —
guard r_px >= 1. ③ per-colour re-trace fragments colours into more pieces than the
whole-image cutout pass → trims rise (joker 93→192, still 0.4% ≪ 5% gate) — the systematic
fix is entry/exit planning ([[NEXT-GOALS]] G3). ④ underlap ≠ pull-comp: geometry-at-seams
vs uniform stitch widening (documented in stitches.py docstring). Ties [[outline-objects]],
[[large-regions-tatami]].
