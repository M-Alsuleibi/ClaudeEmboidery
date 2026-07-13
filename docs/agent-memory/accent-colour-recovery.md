---
name: accent-colour-recovery
description: analyze now recovers tiny chromatic accents (red eyes on monochrome art) that the 2% coverage filter dropped — they could never reach the palette at any --colors
metadata: 
  node_type: memory
  type: project
  originSessionId: 7a5b49c9-3bdb-4789-816d-712d54c83ce2
---

Step-1 `_cluster_colors` dropped every k-means cluster under `_MIN_CLUSTER_COVERAGE`
(2 % of foreground), so a tiny vivid accent — red eyes on the black/white anime girl
portrait (~0.6 % of fg) — could NEVER reach the palette, at any `--colors`: k-means
splits big gray clusters by variance instead, and preprocess's "merge closest so
accents survive" never sees the accent at all. Same failure class `--snap-black`
fixed for black ink.

**Why:** the palette is born in analyze; preprocess only *reduces* it. Any colour
missing from `analysis["colors"]` is unrecoverable downstream.

**How to apply:** `_recover_accents` (analyze.py) now runs after the coverage filter:
foreground pixels with Lab ΔE > 25 (`_ACCENT_MIN_DE`) to every kept centre form an
accent pool; if the pool ≥ 0.1 % of fg (`_MIN_ACCENT_COVERAGE`) its k≤2 colours are
appended. Red eyes → 1878 Saffron + 1638 Cherry Jubilee on the anime portrait; all
150 tests unchanged. See [[edge-touching-bg-separation]] for the same design's
background fight.
