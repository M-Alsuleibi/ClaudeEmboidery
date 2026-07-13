---
name: source-vs-output-fidelity-check
description: "How to measure fidelity of an Arabic vp3 against its SOURCE photo (no ground-truth vp3), and the enlarge lever that fixes over-inked tashkeel"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9b402a86-80d5-4a73-9980-12e5405fd6a4
---

For a **new** Arabic phrase/name there is no reference `.vp3`, so
[[vp3-production-knowledge]] §6 `compare_vp3.py` (ref-vs-output) can't run. Compare the
**rendered output against the source PNG** instead:

1. `tools/render_vp3.py <outdir> <vp3>` → writes `<outdir>/<stem>.png` (arg1 is a DIR,
   not a file; it appends the vp3 stem). Render draws **thin 1-px stitch lines** — a
   naive `coverage` vs a solid-filled source reads ~50-66 %, which is a render artifact,
   not real. **Dilate the render mask to thread half-width (~0.45 mm)** before comparing.
2. **Bbox-crop both ink masks** (`g<128` source, `<200` render) and resize render→source
   grid — removes the render canvas's margin/offset so they register (check aspects match).
3. Report three numbers: **coverage of source ink** (≥~96 % good), **core-miss**
   (source core not covered, after eroding the source — should be ~0-1 %; high = real
   clipping), **false-ink** (output ink outside source+tolerance — over-inking).
4. Build a **RED=source-only / GREEN=output-only / DARK=match** overlay, save as
   `NAME_compare.png` (the shipped example convention).

**Cross-size caveat:** the dilation radius `r=round(0.45/mm_per_px)` shrinks as the
design grows, so coverage/core-miss are NOT comparable across different `--width-mm`.
Use the **gate's areal density** and **false-ink** as the size-independent signals.

**Three levers for "decoration too thick / fine detail muddy" (2026-06-27 findings):**

1. **Enlarge** (`--width-mm` up to ~200): fine diacritics at ~160 mm fall below the
   1.2 mm satin minimum and balloon into solid fans; bigger clears the floor. But it
   does NOT recover detail a low-res source never had, and density is only weakly
   size-dependent for an intrinsically dense piece.
2. **Slim the fixed additive thickening — NOT erosion.** The over-fattening of thin
   tashkeel is dominated by the **trace polygon + pull-comp (0.2 mm/side) + fill
   underlay**. New CLI flags (added this session): **`--pull-comp-mm 0.05 --no-fill-underlay`**
   slim every fill/satin uniformly **without breaking thin marks** (alameen
   الحمد لله رب العالمين: density 0.81→0.49, decorations match source weight, core-miss
   stayed 0.9 %). **Pre-eroding the source is the WRONG tool** — a 1 px binary erosion
   removes whole thin marks (core-miss jumped to ~4.6 %); a missing diacritic is worse
   than a slightly-heavy one. Defaults (0.2 mm, underlay on) are unchanged/back-compat.
3. **Upscale a low-res source to resolve fine internal structure.** jameel
   إن الله جميل يحب الجمال is only 305 px; its tiny **صدق رسول الله** seal traced as a
   muddy blob (internal white gaps lost). **3× Lanczos upscale → re-threshold crisp →
   `--open-counters`** resolves the seal's gaps into distinct calligraphic lines
   (trims 32→54, density 0.81→0.53, false-ink ~0.1 %, seal recognizable). Kept the
   upscaled input as `jameel_source3x.png`. Combine with lever 2 for thin strokes.

**Tooling caveat:** `render_vp3.py` draws **contour-fill as 1-px line-art with gaps**, so
the RED/GREEN pixel overlay is too noisy to judge fine thickness — judge from the solid
**emit `_preview.png`** (stack source / old / new at equal width) and trust **gate
density** + **false-ink**, not raw coverage, across sizes.

Shipped 2026-06-27: `norhan_pro` (110 mm), `alameen_pro` (200 mm, `--pull-comp-mm 0.05
--no-fill-underlay`), `jameel_pro` (200 mm, 3× upscaled source + `--open-counters` + thin
params), each with `_preview.png`, `_threadlist.txt`, `_compare.png` in `arabic/output/`.
See [[compare-output-to-original-iterate]], [[contour-fill-for-calligraphy]].
