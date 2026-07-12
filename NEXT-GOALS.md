# NEXT-GOALS — closing the production-composition gap

Six sequential goals for a Claude session (Opus or better). **Give them ONE AT A TIME, in
order** — each assumes the previous ones are merged. Copy the fenced block into `/goal`
(each is < 4,000 chars). Every goal is self-contained: context, measured evidence, task,
acceptance, rules. After each goal finishes, skim its acceptance numbers before starting
the next.

Shared background (the model will re-read it in CLAUDE.md anyway): the pipeline turns a
photo into a `.vp3` via 7 steps; step 5 (`src/wilcom_pipeline/steps/stitches.py`) tiers
each region run/satin/fill. What production has and we lack: **object composition** —
outline objects sewn over fills, underlap at seams, connected entry/exit routing (0 trims
in production vs ~70 in ours), continuous turning satin, artwork repair, and pair-derived
priors consumed by code. Ground truth: `anime/pairs/pink-goku/` (labels) +
`data/category_profiles.json`.

---

## GOAL 1 — outline objects over fills (the satin gap's missing generator)

```
Repo /home/mohammad/Projects/new-wilcom-v1, branch per-region-tiering. Read CLAUDE.md +
PAIRS-FINDINGS.md first. Run:
  PYTHONPATH=src .venv/bin/python -m wilcom_pipeline <img> --width-mm N --category C
  PYTHONPATH=src .venv/bin/python -m pytest -q   # 86 tests, keep green
Core file: src/wilcom_pipeline/steps/stitches.py. Kill stray processes: pkill -f inkstitch.

WHY (measured): production designs are layered — pink-goku = 118 fill + 217 OUTLINE
objects (1.84:1): satin borders/detail sewn ON TOP of fills. Our trace is a flat
non-overlapping colour partition; no code path ever creates a border object. That is why
anime output reads satin_frac ~25-40% vs the 82.9% ground truth
(anime/pairs/pink-goku/pink-goku_objects.json + data/category_profiles.json).

TASK: add an outline-generation pass to step 5 (flag --outline-objects; default ON for
satin-dominant categories incl. anime, OFF otherwise):
1. For each region kept as a FILL (and >= ~40mm2), build a CLOSED satin border riding its
   boundary: centerline = EDT iso-contour at depth w/2 (reuse _region_raster +
   _iso_contours + _rdp from turning satin) so the satin's outer edge kisses the region
   boundary and its inner half OVERLAPS the fill (deliberate, like production).
2. Border width w: read the category profile's satin_w_mm median from
   data/category_profiles.json (fallback 2.0), clamp 1.5-3.0mm. Emit like the existing
   strip_lines (stroke via _set_stroke_style -> stroke_to_satin), id prefix "border".
3. Sequencing: a region's border sews immediately AFTER its fill, same colour group,
   before the next colour. v1 = same colour as the region. Skip borders whose centerline
   is shorter than ~8mm; cap borders per design (guard like _MAX_STRIPS_PER_REGION).
4. Holes: iso-contours yield hole rings too — border them (counters need edges most).

ACCEPTANCE:
- Render the anime ground truth to a photo (orchestrator/scripts/vp3_to_photo.py on
  anime/pairs/pink-goku/pink-goku.VP3), run the pipeline on it with --category anime
  (NO --satin-lean): satin_frac must rise by >= +25 points vs the same run with
  --outline-objects off, moving toward 82.9; report both numbers.
- compare_to_photo coverage/IoU within 2 points of the no-border run (borders must not
  distort geometry).
- Joker run (orchestrator/output/joker/joker_src.png --height-mm 200 --category anime)
  still completes via the per-group path, gate PASS.
- Pure-geometry tests for the border builder (style: tests/test_turning_satin.py). All
  tests green; non-satin-dominant categories byte-identical output (flag off).
RULES: large regions stay TATAMI underneath (borders are ADDITIONS, never replace the
fill). Fast path unchanged. Compare output to source and iterate before finishing.
```

---

## GOAL 2 — underlap: fills extend under later-sewn neighbours

```
Repo /home/mohammad/Projects/new-wilcom-v1, branch per-region-tiering. Read CLAUDE.md.
Run/tests as in CLAUDE.md (pytest -q must stay green; 86+ tests).
Files: src/wilcom_pipeline/steps/trace.py (+ preprocess.py), stitches.py only if needed.

WHY: production overlaps objects — an earlier-sewn fill extends UNDER its later-sewn
neighbour so fabric pull can't open a white gap at the seam. Our colour regions abut
edge-to-edge (vtracer on exclusive masks); the only mitigation is uniform pull-comp
(0.2mm) which fattens everything instead of overlapping seams. Verify first: make a
two-colour abutting-rectangles PNG, run the pipeline, render the vp3
(orchestrator/scripts/render_vp3.py), measure the seam: count background-coloured pixels
in a +-0.4mm band along the shared boundary. Record the baseline.

TASK:
1. In the per-colour mask pipeline feeding vtracer (find where trace.py builds each
   colour's mask), dilate each colour's mask by `underlap_mm` (default 0.5, new config
   knob --underlap-mm, 0 disables) but ONLY into pixels owned by colours sewn LATER
   (trace already orders groups background-first by enclosure depth — reuse that order).
   Earlier-sewn colour gains the overlap; the later colour keeps its full shape and
   covers the seam. Background/page pixels are never claimed.
2. Keep step-5 width measurement on the ORIGINAL masks (region tiering must not see the
   fattened widths — check _linework_indices/_region_widths input), only the traced
   geometry gets the underlap.
3. Respect open-counters: dropped counter holes must not be re-filled by dilation.

ACCEPTANCE:
- The seam metric on the two-colour test: background gap pixels in the seam band drop to
  ~0 with underlap on, and the LATER colour's region is unchanged (its mask identical).
- Add that as a test (pure mask logic testable without the binary; plus one binary-gated
  seam test).
- Joker + one letters sample run end-to-end: coverage/IoU within 1 point of baseline,
  extent unchanged (underlap must not grow the design), gate PASS.
- Grep the working SVG: earlier colour paths overlap later ones by ~underlap_mm.
RULES: fast path unchanged; per-group fallback still works (masks change upstream of it).
Do not confuse underlap with pull-comp — both exist, document the difference in the
step-5 docstring. All tests green.
```

---

## GOAL 3 — entry/exit planning: travel under cover, kill the trims

```
Repo /home/mohammad/Projects/new-wilcom-v1, branch per-region-tiering. Read CLAUDE.md.
Run/tests per CLAUDE.md. Core: src/wilcom_pipeline/steps/stitches.py.
Watch for hung inkstitch (pkill -f inkstitch).

WHY (measured): production pink-goku sews 15k stitches with 0 trims; our joker emits ~71
(trim_after on every region). Trims are the slowest, most failure-prone machine op. A
digitizer chains objects: each object EXITS where the next ENTERS, and travel runs are
hidden under later stitching.

TASK:
1. PROBE Ink-Stitch's controllability first (vendored binary, see _run_extension):
   (a) can fill/satin start+end points be set per element (params like
   inkstitch:starting_point / ending_point, or the "commands" marker symbols the
   `commands` extension attaches)? Write a 2-region SVG, set them, digitize, verify the
   first/last stitch positions moved. Document what works in the step-5 docstring.
2. Within each colour group, order regions by nearest-neighbour chaining (greedy from
   previous exit). If (1) works: set each region's entry/exit to the closest boundary
   points of its neighbours in the chain.
3. Replace trim_after with plain travel WHEN SAFE: drop the trim between consecutive
   same-colour regions iff the straight line exit->entry is covered (>=90% of its length)
   by the union of regions sewn LATER in the whole design (any colour) OR stays inside
   the current colour's own regions, AND is shorter than ~12mm. Else keep the trim.
   Compute coverage on the raster masks (they exist in step 5's prepass context).
4. Keep --auto-route intact; this pass is the default-path improvement.

ACCEPTANCE:
- Joker (anime recipe): trims fall from ~71 to <= 20 with gate PASS and coverage/IoU
  within 1 point of baseline; report before/after trims + any exposed-travel check.
- Render pink-goku.VP3 to photo, run the pipeline: trims <= 10.
- An explicit no-exposed-travel assertion: every dropped trim's travel segment passes the
  cover test; add unit tests for the cover test + chaining order (pure geometry).
- All tests green; letters sample unchanged trim count within +-2 (its trims are
  Break-Apart boundaries the user wants — keep trims BETWEEN disjoint far-apart pieces).
RULES: never drop a trim when the travel would show (cover test is the law). Fast path +
per-group fallback preserved (merge inserts its own colour changes — chain only within
groups).
```

---

## GOAL 4 — continuous turning satin + branch junctions (de-seam the rings)

```
Repo /home/mohammad/Projects/new-wilcom-v1, branch per-region-tiering. Read CLAUDE.md;
study _turning_satin_lines/_iso_contours/_rdp + _build_vwidth_satin in
src/wilcom_pipeline/steps/stitches.py and tests/test_turning_satin.py.

WHY: turning satin currently emits CONCENTRIC closed rings (fixed width). Edges are clean
but (a) each ring is a separate column -> a trim/seam per ring and a visible radial seam
where rings start, (b) branch satins (--branch-satin / satin-lean) leave small gaps at
junctions where two columns meet.

TASK:
1. SPIRAL the rings: convert the n concentric ring centerlines of one region into ONE
   open spiral polyline — cut every ring at the same angular seam (choose the seam on the
   straightest boundary stretch, not a corner), then connect ring k's cut end to ring
   k+1's cut start with a short radial step. One satin column per region (or per nested
   component) instead of n -> one trim, no aligned seam ring-to-ring. Feed it through the
   same stroke_to_satin emission (id "strip*"). Fall back to plain rings if the spiral
   self-intersects (test with the wavy-blob fixture).
2. JUNCTION overlap for branch satins: where per-branch centerlines meet, EXTEND each
   branch's centerline past the junction point by its local half-width (clamp 0.5-2mm)
   so columns overlap in a mitre instead of gapping. Guard: skip when >4 branches meet.
3. Rungs: verify stroke_to_satin's rung orientation on the spiral is sane (rungs ~
   perpendicular to the local rail direction). If it degenerates on tight inner rings,
   drop the innermost ring below ~2x strip width and let the core be covered by overlap.

ACCEPTANCE:
- Blob test (see the fat-blob PNG recipe in the git log / make one: wavy disc ~45mm +
  thin same-colour keyline, --category decoration --satin-lean --colors 1): trims for
  the blob region drop from ~n_rings to <= 2; the realistic preview shows NO radial seam
  line (attach/describe the preview); satin_frac stays 100.
- Branch test: a Y-shaped stroke image digitized with --branch-satin shows junction
  coverage — background-pixel count at the junction (+-0.5mm disc) ~0 in the render.
- Pure-geometry tests: spiral is a single polyline, monotonically deepening, no
  self-intersection on the fixtures; junction extension length clamped. All tests green.
RULES: straight-strip and plain-ring fallbacks must survive (degenerate geometry). Do not
regress test_turning_satin.py — extend it.
```

---

## GOAL 5 — auto artwork repair + sewability gate

```
Repo /home/mohammad/Projects/new-wilcom-v1, branch per-region-tiering. Read CLAUDE.md.
Files: steps/preprocess.py, steps/analyze.py, steps/verify.py (+config/cli for knobs).

WHY: the pipeline WARNS ("smallest feature ~1.0mm is below the ~1.2mm satin minimum")
but never acts; a production digitizer repairs the artwork (thicken hairlines, drop
sub-sewable specks, merge near-identical colours). And step 7 checks global density but
not per-area STACKING (needed now that borders/underlap overlap objects) nor a stitch
budget.

TASK (two halves):
A. REPAIR (step 2, flag --auto-repair, default on; every action LOGGED):
 1. Sub-sewable specks: connected components < ~1.5mm2 at target size -> merge into the
    surrounding colour (not background) unless part of a dotted pattern (>=3 similar
    specks in a row -> keep).
 2. Hairlines: isolated linework thinner than the run minimum (0.8mm) that step 5 would
    drop/starve -> thicken the mask to 0.9-1.0mm (morphological, along the line only);
    if a design is >30% hairline, instead print the "enlarge the design" advice and
    leave it (don't fatten calligraphy wholesale).
 3. Palette: merge colours with deltaE < 5 that map to the SAME thread cone (step 3
    already notes shared cones — act on it before tracing so regions merge).
B. GATE (step 7):
 1. Density stacking map: rasterize stitch segments (0.5mm/px), warn when local thread
    length exceeds ~3x the single-layer norm over >2mm2 (borders+fill overlap is fine,
    triple-stack is not) — report worst spot + mm2 affected.
 2. Penetration spacing: fraction of consecutive stitches < 0.3mm apart (needle-cut
    risk); warn > 5%.
 3. Stitch budget: expected = area_mm2 * category density med (profiles); warn when
    actual > 1.8x expected.

ACCEPTANCE: joker + one letters + one decoration sample run end-to-end: the old
min-feature warning becomes "auto-repaired: ..." lines, gate PASS, coverage/IoU within 1
point (repair must not visibly change the design); new checks appear in
ctx.verification["checks"] with sane values on all three; unit tests for each repair rule
+ each check (pure numpy fixtures). All tests green; --no-auto-repair restores byte-
identical old behaviour.
```

---

## GOAL 6 — pair priors consumed by code (close the learning loop)

```
Repo /home/mohammad/Projects/new-wilcom-v1, branch per-region-tiering. Read CLAUDE.md +
PAIRS-FINDINGS.md + orchestrator/scripts/{ingest_pairs,register_pair}.py first.

WHY: pairs now yield per-object labels (<category>/pairs/<design>/_measures.json: width
mm, density, row spacing, satin-vs-tatami per object) but nothing CONSUMES them —
step 5's numbers (satin ceiling 7mm, border width, density 0.4mm, outline strength) are
constants or profile medians chosen by hand. The loop closes when new pairs
automatically move the digitizing decisions.

TASK:
1. New script orchestrator/scripts/build_pair_priors.py -> data/pair_priors.json:
   per category, aggregated from ALL <cat>/pairs/*/_measures.json (skip outlier-flagged
   objects): satin width band (p10/med/p90 of satin-verdict object widths), the
   width CROSSOVER (widest satin-verdict object p90 vs narrowest fill-verdict p10 -> the
   measured satin/fill boundary), fill density + row-spacing med, outline:fill object
   ratio, borders-per-fill estimate. Include n_objects + n_pairs per category (trust
   gates).
2. ingest_pairs.py calls it after rebuilding profiles.
3. Step 5 reads data/pair_priors.json when present (helper in fingerprint.py or a new
   priors.py): a category with n_pairs>=1 uses the measured crossover as its satin
   ceiling (clamped 3-9mm, log the substitution), the satin width band for vwidth
   clamps, and Goal-1's border width from the outline-object width med. n_pairs==0 ->
   today's constants, byte-identical output.
4. Document in CLAUDE.md (one short paragraph) + pairs-inbox/README.md ("pairs now
   steer step 5 automatically").

ACCEPTANCE:
- With only pink-goku present: anime runs log "pair prior: satin ceiling X.Xmm (n=1
  pair)" and use it; categories without pairs are byte-identical (assert via one
  regression run diff).
- Corrupt/missing priors file -> constants fallback, no crash (test).
- Unit tests: aggregation math on a synthetic _measures.json; crossover logic; trust
  gate (n_pairs). All tests green.
- Print, at the end, a table: category | ceiling used | source (constant vs pairs n=K).
RULES: priors may TUNE numbers, never change object structure decisions' hard rules
(large regions = tatami stands). Keep ingest idempotent.
```

---

## Order rationale

G1 moves the headline metric most (satin_frac toward truth). G2 is cheap and makes G1's
overlaps principled. G3 attacks machine-efficiency (trims), needing G1/G2's layering to
hide travel under. G4 polishes what G1 mass-produces. G5 makes step 7 catch what
G1-G4 could over-do (stacking). G6 turns the user's incoming pairs into automatic
calibration for everything above. After G6, each new pair the user drops improves the
system with zero code changes.
