---
name: spine-guided-fill
description: "--spine-fill (guided_fill from dropped centerlines) improves fill DIRECTION but does NOT move fingerprint satin_frac; only real satin does"
metadata: 
  node_type: memory
  type: project
  originSessionId: 276e6574-a37d-4aef-b3d7-db0a5af1466f
---

Prototyped PEmbroider's hatchSpine idea as **`--spine-fill`** (opt-in, step 5 `stitches.py`): a region kept as a FILL (branchy stroke / broad blob) reuses its longest `fill_to_stroke` centerline as an Ink-Stitch **`guided_fill` guide** (fill + guide wrapped in one `<g id="spine_*">`; guide marked `marker-start:url(#inkstitch-guide-line-marker)`, marker def injected once — the exact def `selection_to_guide_line` emits), so fill rows follow the medial axis instead of a fixed angle. Reuses the centerlines the tier already computes and used to discard.

**KEY FINDING** (measured on `samples/ritaj-name.png` @140mm, `--category arabic`): the fingerprint's `satin_frac` is a per-COLOUR-BLOCK reversal metric (`fingerprint._block_kind`: satin = >35% of vertices reverse >120°). A directional fill is still long low-reversal rows → stays classified FILL. So:
- baseline `auto_fill`: satin_frac=0, fill_frac≈38
- `--spine-fill` (guided_fill, 5 regions converted): satin_frac=**0 (unchanged)** — but fill DIRECTION visibly follows the stroke (the ج sweep grain runs lengthwise along the medial axis vs baseline's cross-cutting tatami)
- `--fill-method contour_fill` (directional-fill proxy): satin_frac=0
- `--satin-lean` (13 real satin columns): satin_frac **0→59**

=> spine/guided/contour fill = a VISUAL/directional quality lever only; the fingerprint can't see it. The `satin_frac` gap closes ONLY with real satin columns (`--satin-lean` / `--branch-satin`). The remaining satin frontier is **variable-width satin** (PEmbroider `hatchSpineVF` = distance-transform flow along the medial axis) so real satins COVER bold/modulated strokes — satin-lean's known weakness (source coverage 99.9→81.6% when it forces fixed-width satins).

Other PEmbroider takeaways worth mining (see the repo clone under scratchpad if still there): `PEmbroiderTSP.solve()` = NN+2-opt polyline orderer (endpoint-aware, reverses pieces) — reference for owning sew-order instead of blanket `trim_after`/`--auto-route`; `PEmbroiderWriter.VP3` = independent VP3 byte-writer (back-patched block lengths, `catalognumber`/hex/`brand` thread triplet, no trim commands — colour-block boundaries only) to cross-check the letters-doc VP3 format.

Links: [[per-region-tiering]], [[vp3-fingerprint-and-satin-gap]], [[satin-underlay-and-thin-line-run]].
