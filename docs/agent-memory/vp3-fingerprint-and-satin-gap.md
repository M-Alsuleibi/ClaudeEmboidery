---
name: vp3-fingerprint-and-satin-gap
description: "step-7 scores each run vs per-category ground-truth fingerprints (data/category_profiles.json); headline drift: truth is ~100% satin for letters/arabic/simple/decoration but pipeline emits fills = #1 fidelity gap"
metadata: 
  node_type: memory
  type: project
  originSessionId: d236c827-c714-4db2-82d2-79216f18217b
---

`src/wilcom_pipeline/fingerprint.py` + `orchestrator/scripts/fingerprint_vp3.py` build
per-category statistical profiles from the **83 ground-truth production VP3s** (the user's real
files, excluding `*/output/`) into `data/category_profiles.json`. Step 7's **`production_fit`**
warn scores each run against its category's p25–p75 bands (satin%, colours, density, satin
width); category comes from `--category` or an inferred nearest-match. Deliberately **not deep
learning** — 83 unpaired *output* files (no source photos; some categories ≤4), so we fit
distributions, not weights. Rebuild with `.venv/bin/python orchestrator/scripts/fingerprint_vp3.py`
whenever ground truth is added.

**Headline finding the fingerprints expose (the #1 fidelity target):** the ground truth is
**~100% SATIN** for letters / arabic / simple-shapes / decoration (2–2.5 mm columns), but the
pipeline emits **mostly tatami FILLS** for them. Measured on the Arabic run: `satin_frac 0%` vs
truth `100%`. This is now flagged on every run, so drift is visible continuously.

**CLOSED (2026-07) — variable-width satin is the fix, now wired.** History: `--satin-lean`
(`category_satin_dominant()` → raise ceiling + branch-dissect) pushed satin_frac 0→100 but with
FIXED-width columns coverage crashed (under-covers modulated strokes). The real fix = build rails
at the LOCAL medial-axis half-width. Re-tested on the Ramadan calligraphy (input:
`orchestrator/output/Design6/Design6_src.png`, `--category arabic --colors 1 --fill-method
contour_fill`): **fixed-width → satin_frac 0, coverage 97.9%, IoU 67%, over-ink 1.43x; vwidth →
satin_frac 100 (matches truth, satin_w 2.12 in band), coverage 99.3%, IoU 81%, over-ink 1.22x** —
strictly better than BOTH fixed-width satin and the fill it replaces. So **`--satin-lean` now
IMPLIES `--vwidth-satin`** (`vwidth = ctx.config.vwidth_satin or satin_lean` in stitches.py); the
coverage regression is gone. NOTE: for a 1-colour design the fingerprint sees one big block so
satin_frac is unreliable there UNLESS the satins dominate — vwidth's clean zig-zag rungs make it
read 100, fixed-width's diluted output read 0. Measure coverage via ink-mask IoU vs the source PNG,
not satin_frac alone, on 1-colour art. Ties [[vwidth-satin]], [[wilcom-manual-rules]].
Caveat: solid MASSES (a filled character like lufi, >ceiling wide) legitimately stay fill — vwidth
only helps genuinely stroke-based art; a filled-character satin gap is a category mismatch, not a
vwidth target.

**Auto-Split detector wired (2026-07, see [[wilcom-manual-rules]]).** Manual p1197: a WIDE satin
column split into co-linear sub-stitches ("Auto Split") reads as tatami because the per-vertex
reversal fraction drops below the 35% satin threshold — our turn-angle heuristic hit the same
trap. `fingerprint._is_split_satin` now recovers it geometrically: many reversals whose along-path
rail-to-rail crossing distance is ≤ 8 mm (the ~7 mm satin ceiling) = a narrow oscillating ribbon =
satin, split or not. **Measured re-fingerprint delta: numbers 71→84% satin (+13, out of "mixed");
3D unchanged (7.8% — genuine tatami, correctly NOT inflated); letters/arabic/simple/decoration
unchanged at 100% (narrow unsplit satin, already maxed).** So the satin-dominant categories have NO
measurement artifact — their gap is genuinely pipeline-output-side; the detector's forward value is
scoring OUR future wide/variable-width satin correctly at verify time (no false fill-drift). Tests:
`tests/test_fingerprint.py`. Constants: `_SPLIT_MIN_REV=6`, `_SPLIT_CROSS_MAX_MM=8.0`.

Other data-derived facts: sizes match the playbook (letters ~100 mm, arabic 140, decoration 138);
decoration/simple-shapes are typically **monochrome** (median 1 colour) vs the pipeline's default
`--colors 8`; **anime had ZERO ground-truth files** — but the first real anime pair (pink-goku, via
[[svg-vp3-pairs]]) now gives one data point and it OVERTURNS the assumption: anime is **satin-
dominant (82.9% satin, 2.25mm columns) + outline-heavy + 7 colours**, not fill/photo-heavy — so the
`--colors 12` + not-satin-dominant anime defaults are wrong (confirm with ~2 more pairs before
changing). Ties to [[per-region-tiering]], [[wilcom-stitch-type-taxonomy]], [[svg-vp3-pairs]].
