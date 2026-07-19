---
name: arb-preprocess-fusion
description: "Bisected arb blobbiness — preprocess downscale fuses 255→137 word components (trace is fine, ~175 regions) + quantize MEANS pull AA edges (red→salmon); two gated fixes proposed, not yet built"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9c5e2d6b-3552-4b6a-b2ce-6712c9d8dc2f
  modified: 2026-07-19T08:18:31.637Z
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
visibly closer (true red, better word separation). REMAINING arb gaps: bottom-arc fusion
(the 1.2mm _CONSOLIDATE_MM neighbourhood still welds), skeletal blue الله (satin width
band clamps at ~3.5mm vs its ~8mm strokes — needs auto-split-style wide columns), and
pure primaries now match Madeira poorly → arb recipe should use isacord
([[thread-chart-by-palette]]).
