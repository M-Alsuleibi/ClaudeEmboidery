---
name: satin-underlay-and-thin-line-run
description: "two new step-5 Ink-Stitch knobs — satin underlay (①, pure win) + thin-line run (②); ② thins BOLD sub-1.6mm outlines, enlarge to satin instead"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46247877-10fc-48ba-a064-68dfca1bfedc
---

Step 5 (`steps/stitches.py`) gained two Ink-Stitch levers, both **default ON**, gated
by flags `--satin-underlay/--no-satin-underlay` and `--thin-line-run/--no-thin-line-run`
(config fields `satin_underlay`, `thin_line_run`):

- **① satin_underlay** — center_walk + contour underlay under every satin column
  (`_satin_params`). Pure quality win: satin edges don't tunnel/pucker. Costs ~+1 %
  stitches; **coverage/IoU unchanged** because underlay sits *beneath* the satin and is
  invisible to the footprint metric. Verify by grepping the `*_inkstitch.svg` for
  `inkstitch:center_walk_underlay` on `satin_column` paths.
- **② thin_line_run** — a linework colour whose median stroke width < **1.6 mm**
  (`_RUN_MAX_WIDTH_MM`) becomes a **running/bean (triple) stitch** along its centerline
  instead of a fattened narrow satin (the playbook's "line < 1.6 mm → run/triple-run").
  Cuts stitch count (~−17 % on the turtle). Ignored under `--lettering`.

**Why:** measured on `input/turtul.jpeg` (a bold-outline cartoon turtle) at 280 mm / 8
colours. ② thinned the turtle's **bold** outlines — they were 1.4 mm (< 1.6 mm) at that
size — so coverage fell 87.6 %→83.5 % and the outlines/eyes/smile read too light in the
preview. The artist drew those outlines BOLD; a single bean run makes them delicate.

**How to apply:** ② is correct for lines that are *genuinely* thin (Arabic tashkeel, fine
detail). **CORRECTION — the old "just enlarge the bold outline until it clears 1.6 mm →
satin" advice is disproven:** enlarging the turtle to 480 mm flipped the shell band the
*wrong* way (satin→run), because the old per-colour tier used a ridge-pixel median that a
scatter of thin scraps dominated. Fixed by making the tier **area-weighted + per-region**
(see [[per-region-tiering]]). So now: leave ① on everywhere (safe); ② goes auto-dormant on
a bold region once it's tiered by its OWN area-weighted width; pass `--no-thin-line-run`
only to force narrow satins. Ties to [[per-region-tiering]],
[[lineart-outline-satin-archetype]], [[compare-output-to-original-iterate]].
