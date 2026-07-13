---
name: consolidate-erases-interior-linework
description: "preprocess._consolidate (k×k mode filter, k scales with mm/px) erases interior facial linework (mouth/nose/brows); fixed by re-imposing the snapped black mask after it"
metadata: 
  node_type: memory
  type: project
  originSessionId: 11ef90c1-fba9-412f-9741-30aafef68345
---

**The "featureless face" failure** (anime-enhanced, both the 120mm disaster and the first 250mm re-run): eyes/mouth/nose/brows vanish even though they are crisp pure-black in the 1200px work image. NOT the speck merge, NOT the trace, NOT Ink-Stitch.

**Why:** `preprocess._consolidate` is a k×k majority (mode) filter; `k = round(1.2mm / mm_per_px)` — at 250mm width k=7, at 120mm k=13 (work img fixed at `_WORK_MAX_DIM`=1200px, so bigger designs = coarser mm/px = bigger kernel). Any interior stroke thinner than ~k/2 loses every neighbourhood vote and is reassigned to the surrounding colour. Only strokes on transparent *background* are safe (their own colour is the only voter there). Symptom chain: palette lists a colour → thread-match matches it → trace emits fewer groups (the colour's pixels were consolidated away, e.g. 9 matched cones but 7 traced groups).

**Fix (in code, 2026-07-13):** after `_consolidate`, re-impose `black_mask` (the `--snap-black` ink mask: hi<70, chroma<40). Facial features/keylines/pupils are exactly that ink; AA transition bands stay consolidated (mid-tone, fail the black test); speck repair still cleans sub-sewable leftovers. Test: `test_interior_black_linework_survives_consolidate` (1px line — a 4px line survives k=3 on its own, so a too-thick synthetic line makes the test pass vacuously).

**Still unsolved at any size:** non-black tiny detail (yellow iris ≈0.05% of px) never gets a k-means cluster even at `--colors 10` — needs a detail-colour reservation feature, not more colours. Related: [[auto-repair-sewability]], [[snap-black-outline]], [[edge-touching-bg-separation]].
