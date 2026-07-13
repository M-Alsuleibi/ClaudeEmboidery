---
name: animals-category
description: "NEW category (2026-07-13) = fur/feather animals sewn as SKETCH STITCH (airy layered runs, all-outline, zero fills); 10 pairs ingested; exists to fix the fox solid-coverage failure; sketch primitive not built yet"
metadata: 
  node_type: memory
  type: project
  originSessionId: 924bc32f-b27b-45e3-9c66-e94ee4b9f18d
---

**animals** = fur/feather animal illustrations (ostrich/emu, highland cow, kitten — `animals/pairs/1..10/`) sewn as **sketch stitch**: hundreds of overlapping run/bean strokes along the fur direction, fabric showing through. Measured: **1,647 registered objects, ALL outline-family, ZERO fills**; stroke width p10/med/p90 = 0.78/1.12/1.64 mm; blocks read "mixed" 20–25 % reversal @ ~2.3 mm segments (the anti-anime signature — anime is solid satin coverage); median 9 colours (fur naturals + black sketch linework + white highlights, cones repeat across stops); sizes 77–216 mm; sew order = base wash → fur layers → black sketch/face detail → white highlights LAST (matches the [[keyline-detail-sew-last]] split exactly).

**Why it exists:** the fox run sewed solid tatami/satin coverage — a heavy sticker, the opposite of production. Auto-categorizer scored these pairs decoration/anime (fingerprint satin_frac ~99 is the same block-granularity artifact as tatreez) — route animals BY EYE (fluffy/sketchy subject), not by fingerprint.

**Recipe (approximation):** `--category animals` (priors clamp ceiling 3 mm, vwidth 0.78–1.64) + prior 8 colours + madeira + `--fill-method meander_fill` for fur regions (scribble ≈ sketch) + ≥120 mm. **The real fix — the `sketch_stitch` primitive — is now BUILT** (see [[sketch-stitch-primitive]]; tatreez-style: direction field + overlapping bean runs at ~1 mm spacing, calibrate vs `animals/pairs/*/_measures.json` density 1.6–2.3 st/mm², row spacing ~0.95 mm). Related: [[cross-stitch-primitive]], [[svg-vp3-pairs]], [[pair-priors]].
