---
name: contour-fill-for-calligraphy
description: "auto_fill times out on long thin sprawling FILL regions; contour_fill is the dodge — but NOT for arabic any more (satin_only prior sews zero fills; see arabic-satin-only-law)"
metadata:
  node_type: memory
  type: project
  originSessionId: c41db47b-4cc9-455a-b28b-2d7f15e2ff13
---

**SCOPE CHANGE (2026-07-17): this memory no longer applies to Arabic.** The arb trio
proved arabic production sews **zero fills**, and the `satin_only` pair prior now makes
step 5 digitize every arabic region as satin automatically — there is no fill whose
method could time out, and passing `--fill-method contour_fill` on arabic is the
obsolete pre-trio recipe (a fill-structure violation). See [[arabic-satin-only-law]].
The mechanism below still applies to *other* categories with real thin sprawling
fills (swirl decoration, ribbon borders).

Ink-Stitch's default **`auto_fill`** routes one continuous travel path through a fill
region; that routing is O(region complexity) and **times out (>900s)** on a long,
thin, sprawling region — measured on the `hamdollelah.jpg` calligraphy at 160 mm. It
is NOT a vertex-count or area problem (traced SVG was only 617 pts, main path 292
pts); a thin stroke makes countless short fill rows + a huge travel graph. Reducing
size barely helped (100 mm still >120 s).

**Fix:** `--fill-method` (config `fill_method`, default `auto_fill`;
`SUPPORTED_FILL_METHODS` in config.py; wired through `stitches._apply_fill_params` /
`_inject_params`, which sets `inkstitch:fill_method` when ≠ auto_fill). For thin
sprawling FILL ornament use **`--fill-method contour_fill`** — follows the shape
contour inward: **~10 s** (vs >900 s), and the directional stitching looks natural on
strokes. `meander_fill` also fast (~9 s) but stipple-textured. Measured by timing
inkstitch directly on the traced `*_pro.svg` (avoid 15-min full re-runs).

(NOT `--lettering` — see [[lettering-mode-vs-purify]].) Counters open via
[[open-letter-counters]]. See [[vp3-production-knowledge]].
