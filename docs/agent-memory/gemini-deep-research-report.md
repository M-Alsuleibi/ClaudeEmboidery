---
name: gemini-deep-research-report
description: "Gemini Deep Research report (docs/research/deep-research-results.{docx,md}) triaged 2026-07-19 — 2 verified code-available hits for the two biggest gaps + 3 medium ideas; rest is re-proposals/fluff"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9c5e2d6b-3552-4b6a-b2ce-6712c9d8dc2f
  modified: 2026-07-19T18:06:20.003Z
---

The Gemini Deep Research report (prompt/brief in `docs/research/`, repo made public at
github.com/M-Alsuleibi/ClaudeEmboidery for it) landed 2026-07-19. Triage verdict:

**Verified, code-available, maps to our top gaps:**
- **SLD-Vectorization** (Magne & Sorkine-Hornung, CGF 2025, github.com/tanguymagne/SLD-Vectorization):
  CNN classifies stroke intersections + fits one parametric Bézier spline to a raster
  single-line drawing → the external raster **stroke recovery** tool [[arabic-satin-only-law]]
  says didn't exist. **EVALUATED on arb, ADOPT-worthy** (docs/research/sld-vectorization-eval.md):
  allah glyph = 5 calligraphically-correct ordered strokes, red arcs = 406 strokes, skeleton
  coverage 89 %/83 % — right topology+order, small gaps (tips/diacritics) for residual cover.
  THREE required patches: CPU torch+torchvision same index, torch.load map_location=cpu,
  fat-stroke merge guard (merge_3_neighbords collapses deep branches — on wide calligraphy
  the whole centerline is deep → skip merge when branch length > 3× junction radius), plus
  NaN-guard in svg export (one degenerate stroke aborts a 9-min run at save). Runtime: glyph
  19 s, dense band 8m50s CPU / 2.7 GB. **WIRED as step-5 `--sld-strokes`** (sldvec.py bridge +
  _try_sld hook in BOTH the satin band and _keep_as_fill — broad merged glyphs otherwise go
  to rings; vendored at vendor/sld-vectorization, $SLDVEC_BIN override): allah A/B stacking
  5.0→4.4 layers, IoU +2.3, solid strokes vs hollow rims; per-region fallback to chaining;
  flag off = byte-identical. FULL-ARB A/B verdict: columns 749→613 (real consolidation),
  gates PASS, but local direction vs production ~45° median for base AND sld AND sld@0.15mm/px
  — renders equally blobby; bottleneck is UPSTREAM (preprocess word-cluster fusion at ~1200px
  work size + light coverage), NOT stroke recovery. Next arb lever = preprocess fusion, not SLD
  tuning.
- **embroidery-streamlines** (Liu et al., "Directionality-Aware Design of Embroidery
  Patterns", CGF 2023, github.com/desmondlzy/embroidery-streamlines): **EVALUATED,
  ADOPT-worthy** (docs/research/embroidery-streamlines-eval.md): anime hair region +
  our sketchstitch structure-tensor field → ONE continuous 4,876-pt line following the
  hair flow, holes respected, 28s CPU; emits via pyembroidery (direct-primitive path,
  zero trims/region); their production cover = fg field pass over bg ⊥ uniform pass.
  Integration = new step-5 `--streamline-fill` primitive for 3D/anime fills; TRAPS:
  y-flip negates angles, boundary must be closed, density is relative (calibrate vs
  0.4mm), reads as FILL in fingerprint (correct). Python 3.12 works despite 3.10 pin.

**Solid medium-effort ideas (no turnkey code):**
- ~~Auto-spacing satin~~ **CLOSED — DISPROVEN 2026-07-19**: 7,500+ pair-corpus satin objects
  show r(width,spacing) ≈ 0 in every category (flat penetration advance; density mildly
  NEGATIVE with width) + the arb width-opening curve under-stitched 35k vs 41-51k band.
  Production = constant pitch; our flat authored spacing already matches. Documented in
  wilcom-manual-rules.md §2. Do not re-propose.
- Anisotropic pull-comp: apply comp perpendicular to each object's stitch angle instead of a
  uniform buffer; report's physics citations are vague — needs own calibration.
- Sibling-repo dataset loop [[ai-digitizer-repo]]: pyembroidery-parse public stitch archives →
  realistic-render → (render, sequence) pairs; Bhunia CVPR21 cross-modal pretraining.
- TRACE (Archibald, ICDAR 2021) differentiable handwriting stroke recovery — backup to SLD.

**Ignore:** its DT/medial-axis region classification, auto-route/branching, gradient fills =
already built (it re-proposed them despite the brief). **Wrong:** "fractional spacing = pass
floats" (it's curve penetration offsets); roadmap items 1–2 have empty citations; ESA
lettering engine (#1) is a typesetting product track, not the photo path. Useful format
facts: EMB = OLE + zlib payload (unwritable, confirms [[vp3-production-knowledge]]); the
parameterized inkstitch SVG we already emit IS the editable-master answer to "can we make
.emb" — ship it alongside the VP3.
