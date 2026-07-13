---
name: large-regions-tatami
description: "user's HARD rule: large/broad regions must be TATAMI (auto_fill), never contour_fill; but auto_fill HANGS on broad wispy geometry (hair) and simplification doesn't reliably fix it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d236c827-c714-4db2-82d2-79216f18217b
---

**User's hard production requirement:** large/broad regions must be filled with **TATAMI**
(`auto_fill`), NOT `contour_fill` and NOT satin. `contour_fill` is for **thin sprawling
stroke-ornament only** (calligraphy, vines, thin borders) — it makes concentric rings, not the
production tatami rows. Do NOT silently ship `contour_fill` on a broad region as if it were tatami
just because `auto_fill` was slow.

**Why:** tatami rows are the production norm for packing an area (Wilcom manual + the user's
ground-truth). Contour rings ≠ tatami rows; on a broad shape contour also reads hollow/cross-hatched.

**The blocker (measured on `input/joker.png`, anime, 2026-07):** `auto_fill` (tatami) **HANGS**
(infinite-loops in Ink-Stitch's fill router) on the wispy green hair. Tried and FAILED to unblock:
disabling `underpath`, median-5 smoothing, downscaling the source to 420px (32 paths), fewer
colours. The `contour_fill` run completes fine → it's specifically `auto_fill`'s routing on the
hair's many concavities. So joker's broad hair can't be auto-tatami'd by the current pipeline; the
shipped joker uses contour_fill (honest caveat: rings, not tatami rows).

**FIX BUILT (2026-07): per-region (per-colour-group) digitize fallback** in `stitches._digitize`.
KEY diagnostic that unlocked it: each colour digitizes fine ALONE (probe: 2-12s each) — only the
*combined* single Ink-Stitch pass infinite-loops. So: try the whole-design pass with a 120s timeout
(`_WHOLE_DIGITIZE_TIMEOUT_S`); on timeout, split by top-level colour <g>, digitize each on its own
(`_digitize_per_group`), and merge in sew order (`_merge_patterns`, colour-change between groups).
The merge only aligns because of the **frame anchor** (see [[per-group-frame-anchor]] — Ink-Stitch
centres each VP3 on its own stitch bbox, so raw minis misalign by 10s of mm).

**HANG TRIGGER FOUND (2026-07-10): `pull_compensation_mm`.** Joker's green hair group hangs even
alone WITH pull-comp 0.2 but completes in **8 s with pull-comp 0** (underlay on/off is irrelevant —
underlay-off alone still hung). So a group that hangs alone now walks a retry ladder in
`_digitize_group_with_retries`, degrading only as far as needed while KEEPING tatami:
① as-is → ② pull-comp 0 → ③ pull-comp 0 + fill underlay off → ④ fills-only + satins-only split
(two anchored passes, rejoined as one colour block) → ⑤ contour_fill LAST resort (present+flagged).
Validated on joker: 8/8 groups tatami (group 0 via ②), source-coverage 90.6% / IoU 86.4%, extent
~112x200mm — matches the single-pass baseline. The realistic preview no longer times out either:
step 6 composites per-group `stitch_plan_preview` rasters from the kept `*_grpN.svg` files
(`ctx.per_group_svgs`), alpha-stacked in sew order on the shared canvas.
Slow only on hang-designs (~10 min: 120s whole-timeout + per-group). Tests:
tests/test_per_group_merge.py (pure) + test_stitches.py alignment test (binary).
Ties [[per-region-tiering]].
