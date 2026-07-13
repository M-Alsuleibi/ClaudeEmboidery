---
name: wilcom-manual-rules
description: "Distilled official Wilcom Reference Manual (1549pp) → repo doc wilcom-manual-rules.md: hard numbers for width→stitch-type, density, underlay, pull-comp, colour counts; confirms our tiering + the variable-width-satin fix"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d236c827-c714-4db2-82d2-79216f18217b
---

The user provided `wilcm.rar` (~300MB, Wilcom EmbroideryStudio manuals). Extracted to
`wilcom-manual/` (gitignored) — ReferenceManual.pdf (1549pp) is the main one. Distilled the
decision-relevant rules into tracked repo doc **`wilcom-manual-rules.md`** (companion to
[[vp3-production-knowledge]] EMBROIDERY-PLAYBOOK; playbook = measured from ground-truth vp3s,
this = from the official manual). To re-mine: `pdftotext -layout ReferenceManual.pdf`, split on
`\f` = PDF pages. Key chapters: 9 Stitch Types (p219), 17 Reinforcement/underlay/pull-comp
(p409), 18 Stitch Quality/Auto-Split (p433), 41 Automatic Digitizing (p1040), 42 Photos (p1063).

**The big confirmations:**
- Wilcom's OWN auto-digitize tools = our tiers 1:1: Centerline Run (narrow) / Turning Satin
  (narrow column) / Tatami Fill (large area) / Outline Run. Sew order "fills first, details
  last" = our background-first. Validates [[per-region-tiering]].
- **Satin width ceiling ≈ 7 mm** ("use 7.00mm to preserve the satin effect", p452; raised satin
  "7mm wide or less", p231) — our `_SATIN_MAX_WIDTH_MM=3.0` is far too low. BUT do NOT bump it:
  Wilcom wide-satin works via AUTO-SPACING (density recalculated as width changes) + Auto Split;
  fixed-width bump regresses coverage (proven). Confirms [[vwidth-satin]] is the real fix.
- **Density 0.3–0.6 mm normal band (p1200)** → validates our 0.4 mm. Tatami row spacing 0.4–1.5.
- **Satin gap is partly a MEASUREMENT artifact**: p1197 "Auto Split satin, otherwise recognized
  as Tatami" — our fingerprint's turn-angle heuristic has no Auto-Split awareness, so ground-
  truth wide satin gets counted as fill. Add Auto-Split detection before trusting satin_frac.
  Ties [[vp3-fingerprint-and-satin-gap]].

**Adopt-now numbers:** pull-comp by fabric (cotton 0.20 / tee 0.35 / fleece 0.40 / lettering
0.2–0.3, p429); colour counts (grayscale 5–6, simple 7–10, complex 14–16, cap 20; ≥5% area
auto-included, p1091); underlay by width (Center Run 2–3mm, Zigzag wide satin, Edge Run letters,
Tatami underlay large fills, p412); presets Column A/B/C→Satin+EdgeRun+Zigzag, Complex/Turning→
Tatami+EdgeRun+Tatami (p161). Full change list in §8 of the repo doc.

**SHIPPED (2026-07):** ① Auto-Split satin detector in fingerprint.py (see
[[vp3-fingerprint-and-satin-gap]]). ② `--fabric` → pull-comp table (`config.FABRIC_PULL_COMP`,
`resolved_pull_comp_mm`). ③ per-category colour priors (`config.CATEGORY_COLORS`,
`resolved_num_colors`): --colors omitted → arabic/decoration/simple 1, letters 2, numbers 4, 3D 8,
anime 12; explicit --colors wins. Both knobs changed default None + resolver so explicit-vs-derived
is distinguishable. ④ variable run length (`stitches._run_params`): nominal 2.0→4.0mm +
`running_stitch_tolerance_mm=0.2` (manual chord gap) so runs auto-shorten on curves, long on
straights. Tests: test_config.py, test_fingerprint.py, test_stitches.py (hairline asserts the run
attrs). All 61 pass. STILL DEFERRED (gated on
[[vwidth-satin]]): raising the ~7mm satin ceiling + underlay-by-width (Zigzag for wide satin) —
satins come from an external stroke_to_satin call so per-satin width isn't available at param time,
and ours are all narrow (center-walk already = Center Run).
