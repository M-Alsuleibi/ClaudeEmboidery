---
name: compare-output-to-original-iterate
description: "Standing directive — before finishing any production file, compare the rendered output against the ORIGINAL photo and iterate on drift until faithful"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9b402a86-80d5-4a73-9980-12e5405fd6a4
---

User directive (set via `/goal`, 2026-06-27): **as a pre-finish step of producing any
production-ready file, always compare the output against the original photo; if there
is drift, iterate until the output is faithful.** Applies to every job, not just the
one it was set on.

**Why:** the gate (step 7) only checks self-consistency (stitches exist, density band,
fragmentation). It does NOT check fidelity to the source. A file can PASS the gate yet
drift from the original (over-inked diacritics, clipped tips, muddy ligatures, phantom
colours).

**How to apply** — when there is no ground-truth `.vp3` (a brand-new phrase/name), the
[[vp3-production-knowledge]] §6 `compare_vp3.py` (ref-vs-output) doesn't apply, so
compare the **rendered output against the source PNG** instead. Method (see
[[source-vs-output-fidelity-check]]): render the vp3, bbox-register both ink masks,
dilate the render lines to thread width, report coverage / core-miss / false-ink, and
eyeball a RED=source-only / GREEN=output-only / DARK=match overlay (ship it as
`NAME_compare.png`, matching the example set). Then iterate (usually `--width-mm`) until
the drift is explained-or-gone. Verified on norhan, alameen, jameel (2026-06-27).
