---
name: cross-stitch-primitive
description: Cross-stitch primitive (steps/crossstitch.py) for tatreez — built directly with pyembroidery; key gotchas
metadata: 
  node_type: memory
  type: project
  originSessionId: 1bb2285a-9c69-47d2-bb5e-fb3d9982dbf6
---

Step 5 has a **counted cross-stitch primitive** (`src/wilcom_pipeline/steps/crossstitch.py`),
built 2026-07-12 for the [[tatreez-category]] (Palestinian tatreez). Selected by `--cross-stitch`
(AUTO-on for `config.CROSS_STITCH_CATEGORIES` = tatreez; `--cross-stitch-pitch-mm` overrides pitch,
default = pair prior ≈2.1mm). It short-circuits `run()` in stitches.py BEFORE `_locate_binary()`.

How: fixed square grid over the palette-quantised image; each cell's MAJORITY palette colour → an
**X** (4 penetrations BL→TR→TL→BR); colours in palette order (COLOR_CHANGE between), disjoint cell
clusters per colour separated by TRIM. `build_cross_stitch_pattern(ctx, pitch_mm)` → pattern.

**Hard-won gotchas (don't re-learn):**
- **Built DIRECTLY with pyembroidery, NOT Ink-Stitch.** Ink-Stitch's only exact-node mode
  (`inkstitch:manual_stitch`) HANGS the router — a 6-node manual path never returned in 280s
  (warm). A dense qabbeh (50k cells) would be hopeless. Direct build is exact + fast + needs no
  binary. Thread cones still named in step 6 (`_stamp_thread_metadata` matches block RGB to
  thread_map) — so no Ink-Stitch label needed; color each block's thread with `thread_rgb[k]`.
- **Use `pat.add_stitch_absolute(pe.STITCH,x,y)`, NOT `pat.stitches.append([x,y,cmd])`** — the
  latter leaves pyembroidery's internal position at (0,0) so trim()/color_change()/end() land at
  (0,0), polluting the bbox.
- **Per-cell X (high reversal) BEATS smooth diagonal-hatch.** The X's sharp per-corner reversals
  give satin_frac≈100 matching tatreez ground truth; a cleaner-LOOKING continuous diagonal hatch
  reads as a FILL (measured satin_frac 100→7) — REJECTED. Fingerprint fidelity > visual neatness.
- Coordinates: pyembroidery is Y-DOWN (design top = min Y), NO flip (per emit._render_preview
  comment) — matches the normal pe.read→pe.write_vp3 flow. pe unit = 0.1mm; upp = mm_per_px*10.

Verified: rasterised tatreez-05 run PASSES step 7, production_fit in-band (satin_frac=100, fill=0,
colours, satin_w); density marginally high (0.66 vs 0.35-0.61 band) from the per-cell edge
connector. Tests: tests/test_cross_stitch.py (10). Open refinement: production's connector-free
2:1 diagonal LATTICE (all-diagonal arms, still high reversal) would drop the density drift.
Related [[vp3-fingerprint-and-satin-gap]] [[wilcom-stitch-type-taxonomy]] [[pair-priors]].
