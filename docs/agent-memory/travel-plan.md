---
name: travel-plan
description: "step-5 --travel-plan (default on): nearest-neighbour chaining + Ink-Stitch starting_point/ending_point commands (snap to target's NEAREST BOUNDARY POINT) + drop trim_after only where travel <=12mm and >=90% covered — letters 123→59 trims, joker 192→132 (cover law floor)"
metadata: 
  node_type: memory
  type: project
  originSessionId: ee38cb46-50c4-4289-9a91-f72500225c4c
---

**Built 2026-07-11 (NEXT-GOALS G3).** `stitches._plan_travel` (flag `travel_plan`, default on),
runs after outline objects, before auto-route/digitize.

**PROBE RESULT (the key unlock):** Ink-Stitch's `starting_point`/`ending_point` OBJECT COMMANDS
work for fills and **snap the commanded position to the target's nearest boundary point** — so
entry AND exit are fully steerable. (First probe looked like ending_point failed — that was a
target-id mix-up; snapping explains everything.) A command = `<g>` holding a connector `<path>`
(`inkscape:connection-end="#target"`) + `<use xlink:href="#inkstitch_starting_point|_ending_point"
x= y=>`; the two `<symbol>` defs come from `vendor/inkstitch/symbols/inkstitch.svg`; the
`object_commands` extension (NOT `commands` — that name crashes) generates them with a
scale(1.05833) group transform (96dpi/uu correction) — emit WITHOUT the transform and x/y are
plain user units. Command groups live INSIDE the colour group right after the target → they ride
along in the per-group fallback minis automatically.

**The planner:** per colour group: bond border satins to their fill (`data-wilcom-border` marker
stamped in _add_outline_objects — stroke_to_satin renames ids so an attr marker is required),
greedy nearest-neighbour chain of units, reorder children, place start/end commands on fills at
the closest-vertex junction pairs, then drop `trim_after` iff travel ≤ `_TRAVEL_MAX_MM` (12) AND
≥ `_TRAVEL_COVER_MIN` (0.90) covered by (union of later-sewn pieces ∪ own colour's regions) on a
shared 0.5mm/px raster. Satins/runs have fixed endpoints (ring seam = first vertex).

**Measured:** letters ritaj 123→59 trims (84 dropped — exactly cancels underlap fragmentation;
at underlap-0: 54→37, all drops covered junctions, background-crossing Break-Aparts kept).
Joker: 192→132 VP3 trims (84 planner drops; Ink-Stitch re-adds trims for floats over its own
jump-collapse threshold, so planner drops ≠ VP3 delta), coverage/IoU unchanged. **Cover-law
floor:** joker has 121/217 junctions genuinely exposed (white-ground crossings) — a "≤20 trims"
target is impossible there without violating the law; scattered-piece designs keep their trims
BY DESIGN (user's Break-Apart preference).

**Gotchas:** ① strip command markers from stitch_plan_preview output before rasterizing
(`_strip_command_markers`) or they render as faint blue dashes. ② `_split_fills_satins` must
drop command groups whose target was removed (dangling connector). ③ commands don't apply to
satin columns/runs — steer only fills. Ties [[outline-objects]], [[underlap]].
