---
name: drift-debug
description: >
  Stage-bisection debugging loop for when a pipeline run's output does not match the
  source image. Use this WHENEVER stitched output visibly diverges from the original —
  a missing shirt/region, a featureless or blank face, linework (mouth/nose/brows/folds)
  that vanished, a colour that is in the threadlist but invisible in the preview, traced
  groups fewer than matched cones, step-7 production_fit DRIFT, "every fallback failed —
  skipped" in the step-5 log, or the user says the result "is a disaster", "looks wrong",
  "lost the details", or "doesn't look like the photo". Also re-enter it after ANY fix:
  the same visible symptom routinely has multiple stacked causes, so a fix that "didn't
  work" usually means the next cause down, not a wrong fix.
---

# Drift debug: find the stage that lost the feature

The pipeline is a chain of **lossy stages with inspectable artifacts**. Every visible
defect (a missing mouth, a vanished shirt, a buried outline) was destroyed or hidden at
exactly one stage — your job is to find the **first stage where the feature is absent**,
prove the mechanism with a minimal in-process reproduction, fix at the root, and prove
the fix with a regression test that fails without it.

The proven case study (anime-enhanced, 2026-07-13): one symptom — "the face is blank" —
had **three independent stacked causes**, each hidden behind the previous one:
① `_consolidate`'s mode filter erased the linework at quantize, ② after fixing that, sew
order buried it under the skin fill, ③ after fixing that, vtracer's whole-image cutout
culled the 1-2 px strokes at trace. A fix that doesn't cure the symptom is usually
correct anyway — re-bisect from the top and you'll find the next mechanism.

## The bisection chain

Work through the artifact chain in order. Stop at the first stage where the feature is
missing — that stage (or the boundary before it) owns the bug. Use
`scripts/inspect_stage.py` (in this skill's directory) for stages 2–5 instead of
re-writing the same lxml/cairosvg/pyembroidery code every time.

| # | Stage | Artifact to inspect | How |
|---|-------|--------------------|-----|
| 1 | Source | the `_src.png` | Read it; name each defect concretely ("mouth missing", "shirt not stitched") — never just "looks bad" |
| 2 | Downscale | source resized to work size (1200 px cap) | `inspect_stage.py window` on the plain resize — is the feature still there in pixels? |
| 3 | Preprocess (quantize + repair + consolidate + split) | the quantized RGBA | `inspect_stage.py preprocess` — reproduces steps 1-2 in-process, saves the image, prints px-per-palette-colour; check the feature's pixel window and which palette colour owns it |
| 4 | Trace | per-colour groups in `*_working.svg` | `inspect_stage.py group` — renders ONE group at native work resolution; check the window programmatically |
| 5 | Stitches | the `.vp3` | `inspect_stage.py vp3` — per-colour block counts, sew order vs threadlist, stitch probe near a location |
| 6 | Preview | `*_pro_preview.png` | visual confirm only after 2–5 agree |

## Non-negotiable guardrails (each one earned the hard way)

- **Pixel windows, not eyeballed crops.** The working SVG content carries a scale
  transform (foreground-crop, e.g. ×1.2706), so hand-mapped crop boxes silently land on
  the wrong body part — that caused two wrong intermediate conclusions in the case
  study. Always render at native work resolution and count dark/colour pixels in a
  computed window.
- **A palette colour can exist and still sew nothing.** Compare: colours quantized →
  cones matched (step-3 log) → groups traced (step-4 log) → colour blocks in the VP3.
  Any narrowing between those counts is a finding, not noise.
- **Visible-but-buried is a distinct failure.** If the stitches exist in the VP3 but the
  preview doesn't show them, check sew order: an earlier-sewn detail under a later fill
  is covered — the fill's pull-comp (~0.2 mm/side) closes sub-mm holes completely.
- **Prove the regression test fails.** Disable the fix (sed the line out, rerun, restore)
  and watch the test fail. A synthetic that's slightly too thick/big passes vacuously —
  a 4 px line survives the k=3 kernel that kills a 1 px line.
- **Fix at the root, aligned with production knowledge.** Before changing behaviour,
  check `EMBROIDERY-PLAYBOOK.md` and the category knowledge docs — e.g. "hairline &
  outlines sew LAST" is a documented production rule, not a preference. The smallest
  change that encodes the rule beats a symptom patch.
- **After every fix: full test suite, full pipeline re-run, re-check the SAME defect**,
  then record the mechanism in memory (these bugs mis-attribute easily).

## Known mechanisms (check these hypotheses first)

- **Border flood eats cut-off subject regions** — white garment exiting the frame ⇒
  background. Fixed by corner rule + 25 % border-contact in `imaging.py`; a white
  subject *connected* to the white page still needs an RGBA alpha cutout upstream.
- **`_consolidate` erases interior thin strokes** — k×k mode filter, k grows with design
  mm (k=13 at 120 mm!). Snap-black mask is re-imposed after it; non-black thin detail
  inside a fill is still at risk.
- **Sew-order aggregation** — one colour, one stop: a colour that is both base panels
  and detail linework gets averaged to the wrong depth. The keyline-detail split
  (`KEYLINE_DETAIL_RGB` sentinel) exists for black; other colours could need the same.
- **vtracer whole-image cutout culls 1-2 px strokes** (even `filter_speckle=0`); the
  same mask traced alone survives. Isolated re-trace is the cure (underlap already does
  this for every colour except the last-sewn).
- **Step-5 group skipped** — "every fallback failed — skipped" in the log means that
  colour is silently absent from the output; check which cone is missing from the
  threadlist.
- **Tiny accents never get a k-means cluster** (~0.1 % of pixels: an iris, a gold trim)
  regardless of `--colors`; needs accent recovery/reservation, not more colours.

## When NOT to use this

A crashed run (traceback), a gate failure with a stated cause, or routine recipe tuning
(size/colours/flags per category) — those are the orchestrator skill's territory. This
skill is for *silent information loss*: output that runs green but doesn't match the
source.
