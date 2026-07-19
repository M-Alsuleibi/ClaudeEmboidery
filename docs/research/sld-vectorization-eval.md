# SLD-Vectorization evaluation — raster stroke recovery for Arabic calligraphy

**Paper:** Magne & Sorkine-Hornung, "Single-Line Drawing Vectorization", CGF 44(7)
(Pacific Graphics 2025) — https://github.com/tanguymagne/SLD-Vectorization
**Why:** the deep-research report's top find for our #1 open gap: recovering ordered
pen strokes (centerline + traversal order through intersections) from a raster.
The arb-trio work concluded no external tool existed; this is that tool.

## Verdict (arb pair, 2026-07-19)

**Adopt-worthy with one patch.** On a clean raster of the arb "الله" glyph
(rendered from `arabic/pairs/arb/arb.svg`, fills only), the patched tool recovers
**5 continuous strokes matching the natural calligraphic decomposition** — alif
top-to-bottom through every crossing, lam bowl sweeping *under* the alif (CNN
intersection resolution), crescent + teardrop as one pen stroke, shadda separate.
19 s on CPU. Output is centerline Bézier splines only (no width) — width comes from
our own EDT sampling along the recovered centerline, which we already have.

## Stress test: the red arcs (Ayat al-Kursi, 3 dense bands)

406 strokes recovered in 8m50s wall / 31m CPU (2.7 GB peak). **Skeleton coverage
83.2 %** (allah glyph: 89.0 %) at 5 px tolerance — long word-body strokes come back
as continuous ordered centerlines with crossings resolved. The 16.8 % miss is
1,121 fragments, only 45 substantial (largest 421 px): stroke tips, junction spurs,
small diacritics, plus a few surviving chord shortcuts. That residue is exactly what
the arabic path's existing residual-patch cover mops up. Our current skeleton
chaining covers ~100 % of the skeleton by construction but gets stroke direction and
continuity wrong — SLD is the complement: right topology/order, small coverage gaps.
Runtime scales with graph size; tiling per arc (or per connected component) would
parallelize it. Coverage metric: `coverage_sld2.py` (skeleton px within tolerance of
a recovered centerline — do NOT gate ink-pixel-vs-own-radius, edge pixels always fail).

## The fat-stroke failure + fix

Out of the box the entire left crescent (the thickest stroke) came back as a
straight chord: `merge_3_neighbords_node` collapses, at each Y-junction, the branch
**deepest inside the shape** — correct for thin line drawings where deep branches
are short medial-axis artifacts, but on fat calligraphy the whole centerline is
deep, so real geometry gets collapsed. Diagnosis chain: raw Voronoi medial axis is
perfect → vanishing-angle pruning harmless → the merge step is the culprit.

Patch (in `src/SLDvec/skeleton/simplification.py::get_target_merge_node`): skip the
merge when the selected branch's polyline length > 3× the junction's local radius
(`max_distance`, the max of per-branch min distance to the outline). Artifact
bridges are ~1 radius long; real branches are much longer. Upstream-worthy.

## Setup (Linux, CPU-only) — the three traps

```bash
python3.12 -m venv sldvenv
sldvenv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
#  ^ BOTH from the CPU index; mixing PyPI torchvision with CPU torch →
#    "operator torchvision::nms does not exist"
sldvenv/bin/pip install cmake potracer
git clone https://github.com/tanguymagne/SLD-Vectorization && cd SLD-Vectorization
git fetch origin potracer && git checkout -b potracer FETCH_HEAD   # pure-python potrace
sldvenv/bin/pip install -e .
PATH="$PWD/../sldvenv/bin:$PATH" sh build.sh    # two pybind11 modules, needs cmake
curl -L -o src/SLDvec/assets/model.pth https://igl.ethz.ch/projects/sld-vectorization/model.pth
# patch classification.py torch.load(..., map_location="cpu")  (weights saved on CUDA)
# apply the fat-stroke merge guard (above)
# patch utils/svg.py export: skip strokes with non-finite control points — on dense
#   multi-stroke inputs one degenerate stroke fits to NaN and aborts the whole export
#   at the end of a ~9-minute run (arb red arcs: 8m50s compute, crash at save)
sldvenv/bin/SLDvec run input.png --output-path out.svg --multiple-lines
```

Input prep: render artwork fills only (no digitizer guide strokes), black on white;
`load_image` downscales to max 1000 px (`max_size` in `preprocessing/image.py`).

## Integration — `--sld-strokes` (WIRED, 2026-07-19)

Implemented as an experimental flag on the satin-only path:

- `src/wilcom_pipeline/sldvec.py` — subprocess bridge to the vendored tool
  (`vendor/sld-vectorization/venv/bin/SLDvec`, override `$SLDVEC_BIN`); parses the
  output SVG's cubic splines into sampled polylines; everything degrades to `[]`
  when the tool is absent/fails/times out.
- `steps/stitches.py::_sld_region_strokes` — region mask via `_region_raster`
  (holes kept), px→root-frame mapping, 20 mm² region gate, 1 mm stroke gate.
- The `_try_sld` hook fires in BOTH the satin band and `_keep_as_fill` (broad
  merged glyphs are where strips/rings used to take over — production dissects
  everything into per-stroke columns). Recovered strokes flow through the
  unchanged hairpin-split → vwidth-column → residual-cover machinery; junction
  chaining is skipped for SLD regions (their strokes are already whole).
- Per-region fallback to skeleton chaining on any failure; flag off ⇒ byte-
  identical old behaviour. Tests: `tests/test_sld_strokes.py` (pure parsing/
  mapping + a tool-gated end-to-end bar; suite 185 green).

A/B on the allah glyph (90 mm, `--category arabic --no-outline-objects`):
baseline 34 columns / 5,119 st / worst stacking 5.0 layers (0.2 mm² over 5);
`--sld-strokes` 43 columns (3 recovered strokes + 19 residual patches) / 5,357 st
/ **stacking 4.4 layers, 0.0 mm² over 5**; both gate PASS, satin_frac 100.
Coverage 65.0→66.2 %, IoU 39.1→41.4, over-ink 1.31→1.26×. The visual difference
is bigger than the numbers: solid full-width pen strokes vs the ring cover's
hollow boundary-hugging rims. Cost: ~20-40 s per word-sized region (CPU).

## Full-arb A/B (280 mm, 2 colours) — honest verdict

Baseline 749 columns / 43.7k st; SLD 613 columns from 104 recovered strokes /
43.4k st; SLD at 0.15 mm/px raster (the `res_mm` param) 632 columns / 44.2k st.
All gate PASS, trims equal. **Local stitch direction vs the production VP3
(trimmed-ICP registered, RMS 0.85 mm): ~45° median for ALL variants** — metric
partly saturated by underlay/travel mixing, but the renders agree: production is
crisp and legible; every variant of ours is equally blobby, with fused
word-clusters and light coverage. SLD's microbenchmark win does not transfer to
the dense full design because the damage is upstream of step 5: the traced
regions themselves are fused blobs (preprocess consolidation at the ~1200 px
work size), and coverage/density reads lighter than production. Conclusion:
keep `--sld-strokes` (structural consolidation, no regressions, glyph-scale
wins) but the next fidelity lever on arb-class designs is preprocess region
fusion + coverage, not stroke-recovery tuning.

Scratch artifacts from this eval (overlays, diagnostics): session scratchpad
`arb_allah_overlay*.png`, `arb_allah_graph_cover.png`, `diag_sld*.py`.
