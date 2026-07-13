---
name: open-letter-counters
description: "Letter counters (holes in e/B/g, open g-tail loop) were filled solid; fixed by dropping enclosed page-coloured regions to alpha + median palette refine"
metadata: 
  node_type: memory
  type: project
  originSessionId: c41db47b-4cc9-455a-b28b-2d7f15e2ff13
---

**Symptom:** pipeline output filled the interior gaps of letters (the holes in
e/B/g, the open loop in a script `g` descender tail) solid, so `let-the-adventure`
read as black blobs. User flagged it: counters must read through.

**Root cause:** `imaging.foreground_mask` returns `~border_connected_background` —
it only drops background-coloured pixels *connected to the image edge*. A page-white
**counter** enclosed by ink is not border-connected, so it survived as foreground,
got snapped to the surrounding ink, and (since this is a `--purify-colors` mixed
design, the black cursive stays ONE tatami fill) was filled solid.

**Fix (step 2 preprocess):**
- `preprocess._open_counters(mask, rgb, bg_color)` = `mask & ~background_like(rgb, bg_color)`
  — reclassifies enclosed page-coloured pixels as background. AA rim between stroke
  and hole is mid-tone (not page-like) so strokes are untouched → clean open hole.
- Gated by `cfg.should_open_counters` (config): `None`=auto (on when `cfg.purify`,
  i.e. letter modes), CLI `--open-counters/--no-open-counters` to force. Off for
  e.g. a logo with a real white shape inside.
- VTracer already preserves the hole as a compound path (`M…Z M…Z`, outer+inner)
  in `stacked` mode; Ink-Stitch fill respects it. No trace/stitch change needed.

**Also fixed the teal drift** (same design): `_reduce_palette` merges by area-weighted
average, dragging the teal toward gray (126,169,169) by absorbing AA/sheen edge px.
Added `preprocess._refine_palette` = one Lloyd update using the **median** of each
cluster's assigned pixels, run *before* `_purify_ink` (so it still snaps bright
primaries to pure, keeps muted teal verbatim). Teal → (97,161,165), true median
~(90,157,162). In purify mode thread-match RENDERS the palette ink (`thread_rgb=rgb`),
so the refined RGB shows directly; the cone (Stone Blue) is just the operator label.

Residual (not a flaw): black cursive renders as tatami fill w/ hatch texture, not
satin — exact all-satin script = Wilcom Phase B, per [[vp3-production-knowledge]].
Run cmd: `PYTHONPATH=src .venv/bin/python -m wilcom_pipeline letters/output/let-the-adventure.jpeg
--width-mm 140 --colors 3 --thread-chart madeira-polyneon --purify-colors --name
let_the_adventure --output-dir letters/output`. See [[pipeline-run-stale-venv]].
