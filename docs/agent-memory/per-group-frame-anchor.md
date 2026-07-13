---
name: per-group-frame-anchor
description: Ink-Stitch VP3 export centres each output on its OWN stitch bbox — per-group minis need the shared frame-anchor trick (2 manual stitches outside opposite canvas corners) or the merge misaligns by 10s of mm
metadata: 
  node_type: memory
  type: project
  originSessionId: ee38cb46-50c4-4289-9a91-f72500225c4c
---

**Fact (verified empirically, 2026-07-10):** Ink-Stitch's VP3 export re-frames every output to
its own content: a mini-SVG's pattern always reads back exactly symmetric about the origin, while
the same group inside a whole-design pass keeps its true off-centre position. (pyembroidery's own
Vp3Writer/Reader round-trip absolute coords fine — the centring happens in Ink-Stitch's export
path.) So concatenating per-colour-group VP3s shifts every group to a common centre: on joker the
merged design lost ~32 mm of height and source-coverage fell 90→65%.

**The fix (`stitches._add_frame_anchor`):** every mini gets a first-sewn "frame anchor" group —
one 1 mm `manual_stitch` segment pointing INWARD from each of two opposite canvas corners
(viewBox inflated by 5 mm, so no real stitch/pull-comp overshoot can beat the anchors to the bbox
extremes). All minis then share identical stitch-bbox extremes → identical VP3 framing → absolute
coords align. After read-back `_strip_anchor_block` drops the anchor thread + everything through
the first COLOR_CHANGE. The anchor colour must NOT collide with a design colour
(`_pick_anchor_colour`) or Ink-Stitch merges the adjacent same-colour blocks and the strip eats
real stitches. Measured residual after the fix: ≤0.15 mm (VP3 writer int truncation).

**How to apply:** any time separate Ink-Stitch invocations must land in ONE coordinate frame
(sub-splitting a hanging group, fills/satins split, future parallel digitizing), anchor every
mini the same way. The per-group preview does NOT need anchors — `stitch_plan_preview` keeps the
SVG canvas, so rasters align by construction (anchors sit outside the viewBox and clip away).
Ties [[large-regions-tatami]].
