---
name: contour-fill-for-calligraphy
description: "auto_fill times out (900s) on long thin sprawling calligraphy; use --fill-method contour_fill (fast, follows strokes)"
metadata: 
  node_type: memory
  type: project
  originSessionId: c41db47b-4cc9-455a-b28b-2d7f15e2ff13
---

Ink-Stitch's default **`auto_fill`** routes one continuous travel path through a fill
region; that routing is O(region complexity) and **times out (>900s)** on a long,
thin, sprawling region — e.g. the `hamdollelah.jpg` Arabic calligraphy ("الحمد لله")
at 160 mm. It is NOT a vertex-count or area problem (traced SVG was only 617 pts,
main path 292 pts); a thin stroke makes countless short fill rows + a huge travel
graph. Reducing size barely helped (100 mm still >120 s).

**Fix:** added `--fill-method` (config `fill_method`, default `auto_fill`;
`SUPPORTED_FILL_METHODS` in config.py; wired through `stitches._apply_fill_params` /
`_inject_params`, which sets `inkstitch:fill_method` when ≠ auto_fill). For calligraphy
use **`--fill-method contour_fill`** — follows the shape contour inward: **~10 s**
(vs >900 s), and the directional stitching looks natural on strokes. `meander_fill`
also fast (~9 s) but stipple-textured. Measured by timing inkstitch directly on the
traced `*_pro.svg` (avoid 15-min full re-runs).

Recipe for **cursive/calligraphy** (solid black): `--width-mm N --colors 1
--purify-colors --fill-method contour_fill`. (NOT `--lettering` — see
[[lettering-mode-vs-purify]].) Counters open via [[open-letter-counters]]. Result:
hamdollelah → 8189 stitches, gate PASS, faithful. See [[vp3-production-knowledge]].
