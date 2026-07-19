---
name: arb-preprocess-fusion
description: "Bisected arb blobbiness — preprocess downscale fuses 255→137 word components (trace is fine, ~175 regions) + quantize MEANS pull AA edges (red→salmon); two gated fixes proposed, not yet built"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9c5e2d6b-3552-4b6a-b2ce-6712c9d8dc2f
  modified: 2026-07-19T17:44:53.793Z
---

The full-arb blobbiness ([[gemini-deep-research-report]] A/B) is bisected to PREPROCESS,
with numbers (2026-07-19, docs/research/sld-vectorization-eval.md):

- **Downscale fusion**: source red script 255 components ≥1.5mm² → work image 137. The
  flat 1200px work-size cap = 0.23mm/px at 280mm, so sub-0.5mm inter-word gaps are 1-2px
  and close under quantize+consolidate. TRACE IS NOT AT FAULT — it emitted ~175 regions
  (ids to c0_174); the final working.svg keeps only the ~20 originals step 5 didn't
  consume, so counting originals there UNDER-COUNTS the trace (mis-read trap).
- **AA colour drift**: quantization takes cluster MEANS incl. anti-aliased edge px —
  pure red (237,28,36) → salmon (254,109,110) → washed-out renders + drifted cone match.

**Why:** these two account for the visible fused-word blobs and light colour that neither
[[per-region-tiering]] nor --sld-strokes can repair downstream.

**BOTH FIXES BUILT (2026-07-19):** ① `_work_max_dim` — satin-only categories derive the
work cap from physical size at 0.15mm/px clamped [1200, 2200] (small designs byte-identical,
tatreez-OOM-safe cap); `--work-res-mm` forces any category. ② `_refine_palette` (median
Lloyd) now runs EVERY run, not purify-only; snapped-black slot pinned. Measured: red
components 137→182 of 255, palette salmon→pure (255,0,0), full arb gate PASS, render
visibly closer (true red, better word separation). FOLLOW-UP ALL FIXED (same day): ① wide-column
escape in _build_vwidth_satin — p90 width over the band ceiling opens rails to true width
capped at 7mm + stamps inkstitch:max_stitch_length_mm=7 (probed: the vendored binary DOES
split satin throws; blue glyph med 3.39/p90 5.16 vs production 2.25/4.44 — full-bodied);
② satin-only consolidate 1.2→0.6mm (_CONSOLIDATE_SATIN_ONLY_MM); ③ arb runs should pass
--thread-chart isacord (pure red/blue cones; Madeira gives Fluo Pink/Purple Accent) —
recipe-level, default unchanged. TRAP: a hand-built satin-column probe SVG with rungs at
rail ENDPOINTS hangs the router — probe with interior rungs or a real working SVG.
Residual smaller gaps: bottom-arc heavy patches, visible connector at the alif top.
