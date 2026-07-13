---
name: sketch-stitch-primitive
description: "step-5 sketch_stitch primitive (steps/sketchstitch.py, AUTO for animals) — fur flicks along a source-art direction field; the two turn-geometry traps (90° jogs read as fill) and the calibrated constants"
metadata: 
  node_type: memory
  type: project
  originSessionId: 924bc32f-b27b-45e3-9c66-e94ee4b9f18d
---

**Built 2026-07-13** (closes the gap noted in [[animals-category]]): `steps/sketchstitch.py`, AUTO for `SKETCH_STITCH_CATEGORIES=("animals",)` via `resolved_sketch_stitch`; `--sketch-stitch`/`--no-sketch-stitch`/`--sketch-spacing-mm` (default = pair prior `row_spacing_mm` ≈ 0.98 × internal `_SPACING_FACTOR` 0.75). Direct pyembroidery like [[cross-stitch-primitive]]; trace (step 4) skips itself.

**Geometry:** fur-direction field = structure tensor of the SOURCE luminance (not the flat quantized image) at ~2 mm; per ~9 mm cell orientation; rows split into **~4.2 mm fur flicks**, each sewn forward-back-forward with return passes fanned ±0.3 mm; keyline-detail layer ([[keyline-detail-sew-last]]) sews last as true bean (re-enters the same penetrations).

**The two traps (both cost a full iteration):**
1. **Serpentine scanlines read as FILL** — 90° turns at row ends never count as reversals (fingerprint `_REV_TURN_DEG` > 150°). satin_frac measured 4 vs the truth's 92–100.
2. **Lateral-offset return passes read as FILL too** — starting the back pass 0.3 mm beside the forward end splits the 180° turn into two 90° jogs (rev 3%!). Passes must **pivot at shared endpoints** and fan out at the far end. (The fingerprint's `_is_split_satin` rule — reversals closely spaced along the path — is what makes production's 20–25% block reversal still read "satin"; flicks put a pivot every ~2 stitches.)

**Calibration (fox, 130 mm):** pitch 1.7 mm (satin_w 1.68 vs band [1.26–1.674]), spacing 0.75×prior (density 2.38 in [2.30–3.24]), satin 100/fill 0 in band, 36k st vs ~39k budget, coverage 99.6%, IoU 97.2%. Tests: `tests/test_sketch_stitch.py` (9) incl. direction-following on synthetic stripes and empty-colour-block guard (a colour whose strokes all fall below min length must not claim a thread block — gate `all_colours_sewed`).
