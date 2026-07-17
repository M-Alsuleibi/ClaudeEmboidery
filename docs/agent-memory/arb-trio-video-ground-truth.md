---
name: arb-trio-video-ground-truth
description: "arb trio (SVG+VP3+webm video) = arabic process ground truth; video replaces props-JSON; drove 3 prior-driven fixes (verdict-mask dilation, satin-only ceiling=auto-split 7mm, trim-after-off)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 49ae602c-1ce3-4a54-9644-a7bcb418e244
---

The arb trio in `arabic/pairs/arb/` (Ayat al-Kursi, 279.6×245.2mm, 46k st, 1,618 objects,
2 trims) is the FIRST trio whose third element is an 18-min EmbroideryStudio screen
recording (`input/arb.webm`) instead of a props JSON — I transcribed the video's dialogs
into `arb_props.json` myself (2026-07-17). The user will switch other categories' trios to
(vp3, svg, screenrecord) too.

**What the video proved (arabic construction):** calligraphy dissected into ~1,600 tiny
column objects (909 Column A two-rail + 703 Column C centerline 0.80mm — the CorelDRAW SVG
carries exactly these paths 1:1); ALL satin (auto spacing 0.24mm@90%, satin count 7,
**Auto split 7.00/0.40mm**); **Connectors = Jump, Trim after OFF, Tie in OFF** (hence 2
trims in 46k stitches — production sews uncovered short travels); pull comp disabled
(0.17 greyed); Double-Tatami underlay only on wide Column A pieces. Machine sim: continuous
arc-by-arc sew per stop.

**Why:** the pipeline's arabic output drifted (satin 91.8 vs 100, fills 8.2 vs 0, 135
trims vs 2) because (a) register_pair's tight object mask chopped satin rungs into
co-linear fragments voting "fill" → priors crossover collapsed to 2.2-3.6mm, and (b) the
travel cover law kept trims production doesn't sew.

**Missing-middle-arc incident (found comparing rebuild vs this VP3):** the 1,090mm²
middle band traced as ONE region; thin connectors dragged its area-weighted width to
1.36mm → run tier demoted it to 6 bean runs and dropped the fill (~15% coverage, verify
green). Fix = `_run_demotion_ok` (small OR long_frac≥0.6 to demote; large spur-dominated
regions stay fills). TRAP for future drift-debugging: `*_working_A.svg` on disk is
POST-decision state — its "missing originals" are deliberately dropped satin/run regions,
NOT fill_to_stroke eating paths (first theory, disproved by a standalone pass-A probe).

**How to apply:** three prior-driven fixes (never hardcode the category): ①
register_pair.py VERDICT_DILATE_MM=2.0 dilated mask for stitch-kind only; ②
build_pair_priors marks a category `satin_only` when <5% fill verdicts → priors.py
satin_ceiling uses authored fill_length_mm (= the Fills-tab Auto-Split length, 7.00) →
arabic ceiling 7.0; ③ Connectors-tab "Trim after: Off" → authored.trim_after_off_frac →
_plan_travel drops trims by ≤12mm length alone. Video frame mining: ffmpeg scene-select
0.12 + 1fps sweep, montage 3x3/6x6, then full-res Read of dialog frames. See
[[svg-vp3-pairs]], [[pair-priors]], [[travel-plan]], [[contour-fill-for-calligraphy]].
