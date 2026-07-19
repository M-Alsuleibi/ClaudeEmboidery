# embroidery-streamlines evaluation — form-following fill direction fields

**Paper:** Liu, Piovarči, Hafner, Charrondière, Bickel — "Directionality-Aware Design
of Embroidery Patterns", CGF (Eurographics) 2023.
**Code:** https://github.com/desmondlzy/embroidery-streamlines (MPL-2.0, research
prototype). Deep-research find #2; closes open gap "stitch-direction/angle fields
for fills".

## Verdict (2026-07-19): ADOPT-worthy for fill-heavy categories

On the anime portrait's hair region with **our own structure-tensor field** (the
sketchstitch recipe verbatim), `main_pipeline` produced **one continuous 4,876-point
line** whose streamlines visibly follow the hair's flow — fringe direction, side
sweep — with even spacing, the face hole respected, and full coverage in the stitched
render. 5,038 stitches at 99 mm, ~28 s CPU. The analytical sanity case (linear
density + constant direction) reproduces the paper exactly: serpentine single line
with mid-row branch insertions where density opens.

## Why it fits our stack unusually well

- **API**: `main_pipeline(xaxis, yaxis, boundary, holes, density_grid,
  direction_grid, inside_indicator_grid, relative_line_width)` → a single (N,2)
  polyline in normalized coords. Region masks, holes, and per-pixel fields are
  exactly what step 5 already has per region.
- It emits through **pyembroidery** (pinned 1.4.36) — same direct-emission path as
  the cross-stitch/sketch primitives. Physical conversion: `line × size_mm × 10`,
  subsample at 1.3 mm.
- **One line per region = zero trims** — production-friendly by construction.
- Their production pattern is a two-pass cover: fg pass (image density + direction
  field) over a bg pass (uniform density, field rotated 90°) — a perpendicular
  underlay analogue we should keep.
- License MPL-2.0; deps: numpy 1.26/scipy 1.12/numba/scikit-image/triangle
  (cp312 wheels fine; python 3.12 works despite the repo's 3.10 pin).

## Integration sketch (next session)

New experimental step-5 primitive `--streamline-fill` (AUTO candidate for 3D/anime
fills later): per FILL region → structure-tensor field from the source art (reuse
`sketchstitch._flow_field`) + constant density → bg pass ⊥ + fg pass → direct
pyembroidery rows appended to the pattern like the sketch primitive. Calibrate
density against our 0.4 mm spacing and the category profiles' density band; keep
tatami as the fallback for degenerate fields (low coherence → flat regions should
stay plain tatami). Vendor like SLD (`vendor/embroidery-streamlines/` + venv) or
inline the `embroidery/` package (compact, pure python + triangle/numba).

## Traps

- Coordinate frames: grids are meshgrid math-up; image-derived fields need the
  y-flip AND the angle negated (mirror flips angle sign).
- The boundary polyline must be explicitly closed (`allclose(first, last)` assert).
- Density semantics are relative (0..1-ish), not mm — calibration required.
- Fingerprint will read streamline fills as FILL (low-reversal running rows) —
  correct for fill-dominant categories; do not expect satin_frac movement.

Eval artifacts: scratchpad `esl_eval.py`, `esl_part1.png`, `esl_part2.png`,
`esl_part2.vp3`, `esl_triptych.png`.
