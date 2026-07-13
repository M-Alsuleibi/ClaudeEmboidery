---
name: gradient-shading
description: "--gradient (default off) de-posterizes shading via Ink-Stitch gradient_blocks; merges same-hue/diff-lightness/adjacent palette colours into one compound-path gradient"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46247877-10fc-48ba-a064-68dfca1bfedc
---

`--gradient` (config `gradient`, **default OFF**, experimental) reproduces smooth tonal
areas as density-modulated gradients instead of hard posterized bands, via Ink-Stitch
`gradient_blocks`. Flow:
- **trace.py `_shade_clusters`**: link palette colours that are same hue (Lab a,b within
  `_GRAD_HUE_TOL`), different lightness (`_GRAD_L_MIN..MAX`), and spatially adjacent
  (dilated masks share `_GRAD_BORDER_MIN`+ px). Connected components ≥2 → a gradient.
- **`_emit_gradient_cluster`**: concatenate the members' vtracer subpaths into ONE
  compound path (shared borders cancel under nonzero winding → the union) filled
  `style=fill:url(#gradN)` + a userSpaceOnUse `<linearGradient>` (light→dark centroid axis,
  stops = matched thread colours).
- **stitches.py `_apply_gradient_blocks`**: run gradient_blocks per `fill:url` path →
  variable-density colour blocks. They live in `gradient*` groups (ignored by the linework
  pass); `_apply_fill_params` gives them underlay/pull-comp/trim but keeps their
  row/end-spacing + angle (detected by `inkstitch:end_row_spacing_mm`).

**Three gotchas that each cost a debug cycle (headless):**
1. gradient_blocks reads stop colour from the **`style`** attr (`stop-color:#hex;stop-opacity:1`),
   NOT the `stop-color=` presentation attribute → `KeyError: 'stop-color'`.
2. It needs **one continuous path** per region. Two separate paths sharing a gradient
   **seam** (one collapses to solid). Hence the compound-path union.
3. **vtracer emits `translate(tx,ty)` per path** → must **bake the translate into the
   coordinates** (`_bake_translate`) before concatenating, or the compound path silently
   falls back to flat groups (symptom: cluster detected in the log but no `linearGradient`
   in the trace SVG).

**Contiguity guard (`_GRAD_CONTIG_FRAC`):** a cluster is dropped unless its union is mostly
ONE connected blob — a single gradient axis **streaks** across separated regions. Without it,
the turtle's greens (scattered across head/flippers/belly) merged into one gradient and drew
ugly diagonal streaks over the face; with it, only contiguous clusters gradient.

**When it helps vs not:** shines on GENUINELY shaded contiguous art (a shaded sphere/blob, a
3-D solid facet, a face with tonal ramps) — validated on a synthetic light→dark blob (hard
3-band posterization → density-blended transitions). It does **little for FLAT cartoons** like
the turtle (the "shades" are stylistic flat regions, not a real ramp) and can leave a faint
directional streak — which is why it's **default off**. Effect is bounded by thread-colour
count (more colours = smoother). ~+40–50 s (gradient_blocks + realistic preview). Ties to
[[realistic-preview]], [[vp3-production-knowledge]].
