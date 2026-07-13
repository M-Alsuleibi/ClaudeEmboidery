---
name: realistic-preview
description: "--realistic-preview (default on) renders the step-6 preview via Ink-Stitch stitch_plan_preview realistic-vector + cairosvg; png_realistic can't be used (needs Inkscape)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46247877-10fc-48ba-a064-68dfca1bfedc
---

Step 6 gained `--realistic-preview / --no-realistic-preview` (config `realistic_preview`,
**default on**). `emit.py` calls `stitches.render_realistic_preview(ctx, svg, dst)` to render
the preview with Ink-Stitch's realistic **thread** renderer instead of the fast polyline draw
(`emit._render_preview`). Honest stroke widths + thread look; falls back to the polyline on any
error. Adds ~2–3 s (an extra stitch-plan pass). Verified on single-colour calligraphy AND the
multi-colour turtle (fills + 10 colours). Needs `ctx.stitch_svg_path` (the stitch-ready
`*_inkstitch.svg`), set in `stitches.run`.

**The blocker + the fix (important):** the obvious extension, **`png_realistic`** (and
`png_simple`), is an *output* extension that shells out to the **`inkscape` binary** to
rasterize → `inkex.command.CommandNotFound: 'inkscape'` in our deliberately Inkscape-free setup
(that's the whole point of the vendored standalone binary). Solution: use the **effect**
extension **`stitch_plan_preview --render-mode=realistic-vector`**, which draws the shaded thread
as **SVG vectors** into the document (no Inkscape), then rasterize with **cairosvg** (already in
the venv). Full args used: `--render-mode=realistic-vector --layer-visibility=hidden
--move-to-side=false --overwrite=true --render-jumps=false`. `realistic-300/600` modes DO invoke
Inkscape — only `realistic-vector` is headless-safe.

Rule of thumb: **an Ink-Stitch OUTPUT extension that produces a raster (png_*) needs Inkscape;
EFFECT extensions that emit SVG are headless-safe.** Ties to [[vp3-production-knowledge]].

**Timeout calibration (2026-07-13):** `_PREVIEW_TIMEOUT_S` raised 120→300 s — it is per group/design, and a big *completed* fill group re-runs its whole stitch plan in stitch_plan_preview (anime portrait hair group: 130 s), so 120 s tripped the polyline fallback on a healthy design; only a true hang should trip it.
