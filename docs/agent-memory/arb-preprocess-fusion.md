---
name: arb-preprocess-fusion
description: "Bisected arb blobbiness — preprocess downscale fuses 255→137 word components (trace is fine, ~175 regions) + quantize MEANS pull AA edges (red→salmon); two gated fixes proposed, not yet built"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9c5e2d6b-3552-4b6a-b2ce-6712c9d8dc2f
  modified: 2026-07-19T07:17:44.426Z
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

**How to apply:** fix ① work size scales with target mm (~0.15mm/px for large designs, not
flat 1200px); fix ② palette centroids from CORE pixels (erode masks pre-mean, or mode-snap).
Both touch EVERY category — roll out gated + regression battery (letters/joker/tatreez OOM
memory: big work images have blown memory before — check [[edge-touching-bg-separation]]
tatreez OOM before raising work size).
