---
name: vwidth-satin
description: "--vwidth-satin builds variable-width satin from centerline+boundary (medial-axis distance / hatchSpineVF); fixes satin-lean's single-average-width; must bake per-path transforms to root frame"
metadata: 
  node_type: memory
  type: project
  originSessionId: 276e6574-a37d-4aef-b3d7-db0a5af1466f
---

Prototyped **variable-width satin** (`--vwidth-satin`, opt-in, step 5 `stitches.py`) = PEmbroider `hatchSpineVF` idea. Instead of setting one average stroke width (`area/length`) on the centerline and running Ink-Stitch `stroke_to_satin` (which builds CONSTANT-offset rails → can't match a modulated stroke), it builds the satin column DIRECTLY: for each centerline point, half-width = distance from that point to the region boundary (the medial-axis inscribed radius, `_min_dist_to_segments`), offset the two rails by that local half-width, emit a native `inkstitch:satin_column` path (2 long rail subpaths + short rung subpaths). Per-column fallback to fixed-width `stroke_to_satin` on geometry failure. Files: config.py `vwidth_satin`, cli.py `--vwidth-satin`, stitches.py `_build_vwidth_satin` + transform helpers.

**CRITICAL gotcha (the "bake vtracer translate" trap):** after `fill_to_stroke`, the original fill polygon carries e.g. `transform="translate(309,29)"` while the centerlines carry `transform="scale(1.08669)"` — DIFFERENT per-path frames. Computing distance from raw `d` coords gives garbage (everything pinned at the width clamp). Fix: resolve both to the ROOT frame via each element's cumulative transform (`_ctm` composes element+ancestors; groups here have no transform), compute there, and strip the satin's own `transform` after baking rails in. `mm_per_uu` is root-frame so clamps convert correctly.

**Results (samples/ritaj-name.png @140mm arabic, `--satin-lean [--vwidth-satin]`):** runs clean, 13 satin columns, valid VP3, satin_frac stays ~59 (real satin preserved), 7/7 stitches tests pass. Width now varies 1.5–4.4× per column (0.5–2.2mm) vs fixed uniform ~2.2mm; ~6% leaner thread bulk. Visual: modulated calligraphic thick-belly/thin-tail vs fixed uniform over-bold.

**Honest finding:** vwidth's win is width **fidelity** (rails track the true local stroke), not "more coverage" per se. On ritaj the fixed `--satin-lean` was actually OVER-bold because `area/length` over-estimates width on branchy strokes; vwidth corrects it DOWN. The 99.9→81.6% under-coverage the satin-lean docstring cites was a DIFFERENT design where fixed width was too narrow for a bold modulated stroke — vwidth fixes both directions. Caveat: the medial estimate runs slightly thin (fill_to_stroke centerline isn't a perfect medial axis; end-smoothing thins tips) — tunable with a small coverage-gain factor (`hw *= ~1.1`). This is exactly the trace-vs-hand-digitize boundary [[per-region-tiering]] / satin-lean flag.

**PROMOTED (2026-07): `--satin-lean` now IMPLIES `--vwidth-satin`** (`vwidth = ctx.config.vwidth_satin
or satin_lean` in stitches.py, ~line 533). Clean A/B on the Ramadan calligraphy (Design6_src.png,
`--category arabic --colors 1 --fill-method contour_fill`): fixed-width → satin_frac 0, source-ink
covered 97.9%, IoU 67%, over-ink 1.43x, visible rail artifacts + merged blobs; vwidth → satin_frac
100 (satin_w 2.12 in truth band), covered 99.3%, IoU 81%, over-ink 1.22x, clean tapered strokes.
So vwidth beats fixed-width on coverage AND shape AND leanness here (no thin-running on this design;
the `hw*=1.1` gain factor was NOT needed). Measure 1-colour art by ink-mask IoU vs source, not
satin_frac (one block → unreliable). 61 tests pass.

**BROADENED (2026-07): vwidth now fires BY DEFAULT for wide columns, no flag needed.** With the
satin ceiling raised 3→7mm (`_SATIN_MAX_WIDTH_MM`, manual value), any column wider than
`_SATIN_FIXED_MAX_MM=3mm` builds variable-width automatically (`vwidth_all or w_mm > 3` in the tier
loop) — a uniform width under-covers there. So the gap closes on stroke art with plain flags
(Design6 default → satin_frac 100, cover 99.3%). Underlay-by-width: `_build_vwidth_satin` stamps
`zigzag_underlay` when its built median width >3mm (manual p412); narrow columns keep center-walk
only. Tests: test_vwidth_satin.py (4). 65 pass. See [[per-region-tiering]] for the full band table.

Links: [[spine-guided-fill]], [[vp3-fingerprint-and-satin-gap]], [[per-region-tiering]].
