---
name: snap-black-outline
description: "--snap-black step-2 knob — dedicate a thread to pure black for logo outlines/pupils WITHOUT purify's neon side effect on muted colours"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46247877-10fc-48ba-a064-68dfca1bfedc
---

Step 2 (`steps/preprocess.py`) gained `--snap-black / --no-snap-black` (config
`snap_black`, **default on**, flag-gated no-op when there's no black ink). It reserves
one palette slot for pure `(0,0,0)` and routes the near-black, near-neutral foreground
pixels (`_black_ink_mask`: brightest channel < 70 AND chroma < 40) onto it, so a thin
anti-aliased outline/keyline + eye pupils stay crisp black instead of quantisation
averaging them into a dark brown. Implementation: rebuild the chromatic palette at
`num_colors - 1` and append black, then force `idx_map[black_mask] = black_idx`.

**Why:** on `input/turtul.jpeg` (cartoon turtle, muted olive green + soft orange), plain
quantisation at 8–10 colours **lost the black outline entirely** (merged to brown), and
the *only* lever that recovered black — `--purify-colors` — also snapped the muted orange
to **neon** and pushed the green toward brown (purify snaps every near-primary; see
[[lettering-mode-vs-purify]]). snap-black recovers black surgically, leaving muted colours
verbatim.

**How to apply:** for a logo/cartoon/icon with a black outline on muted/custom colours,
prefer **`--snap-black` (default) WITHOUT `--purify-colors`**. Use `--purify-colors` only
when the art's non-black colours are themselves near-pure primaries.

**Honest ceiling (turtle):** snap-black fixes the *colour*, but a cartoon **face's** fine
black detail (eye-rings, pupils, smile, nostril) still traces *busy* at logo size — that's
the tracer resolution limit ([[compare-output-to-original-iterate]], playbook §4
trace-vs-build), cleaned by a larger size or a Phase-B hand-tidy, not a flag. How the black
is *sewn* matters too: a thin outline reads best as a bean **run** (`--thin-line-run`, the
default), not a fattened satin — see [[satin-underlay-and-thin-line-run]].
