---
name: svg-vp3-pairs
description: "(CorelDRAW-SVG, VP3) pairs give object-level ground truth the vp3 hides; first pair pink-goku overturns anime = satin-dominant + outline-heavy + 7 colours (not fill/12-colour)"
metadata: 
  node_type: memory
  type: project
  originSessionId: d236c827-c714-4db2-82d2-79216f18217b
---

The user is feeding THIS pipeline (not the AI repo) **(CorelDRAW-exported SVG, production VP3)
pairs** + the Wilcom manual, to learn what real designs decompose into and produce better vp3 from
photos.

**Structure (2026-07-10):** user drops pairs (matching stems) in **`pairs-inbox/`** →
`orchestrator/scripts/ingest_pairs.py` auto-categorizes (VP3 fingerprint vs
data/category_profiles.json; 9/11 top-1 on known VP3s — misses are flagged near-ties inside the
satin-dominant twin family; unplaceable → `pairs-inbox/unknown/` with new-category instructions),
files under **`<category>/pairs/<design>/`**, labels (extract_pair + register_pair), `git add -f`s
the VP3 (VP3s are globally gitignored — ground truth must be force-added!), rebuilds profiles,
prints the PAIRS-FINDINGS table row. Target 2-3 pairs per category. Tools all in
`orchestrator/scripts/` (extract_pair.py, register_pair.py, ingest_pairs.py + the consolidated
analyze/render/compare toolbox). Method doc: `PAIRS-FINDINGS.md` (repo root). First pair lives at
`anime/pairs/pink-goku/`.

**What each half is trusted for (learned empirically):**
- **CorelDRAW SVG** → object FAMILIES (filled shape `filN` = area/fill object; `fil0 strN` stroke =
  outline/line object), COLOURS, sew ORDER, outline:fill ratio. SCALE-INDEPENDENT, reliable.
- **VP3** → SIZE, density, satin/fill split, satin width. Real mm, reliable (use `features_from_pattern`).
- **SVG coords → mm widths: via `register_pair.py` (BUILT 2026-07-10).** Naively unreliable (the
  export has off-page/clipping paths; raw bbox aspect mismatched the VP3, pink-goku ~1.15 vs 1.33)
  — but a trimmed-ICP similarity fit (init from median+MAD, cKDTree nearest-stitch
  correspondences, keep best 75%, closed-form Umeyama) aligns SVG ink→stitch cloud at **0.29 mm
  RMS** on pink-goku, auto-flagging 30/335 paths as non-stitched outliers. Output
  `<design>_measures.json`: per-object area/width in real mm (fill widths median 2.88, p10 1.20,
  p90 5.96 — the satin band, confirming the 7 mm ceiling), per-object stitch density, effective
  row spacing (area/thread-length), and satin-vs-tatami verdict (fingerprint `_block_kind` on the
  stitch runs inside each object mask; pink-goku: 72 satin / 26 fill / 14 mixed objects). Check
  `<design>_reg.png` (red=SVG, blue=stitches, purple=match) before trusting numbers. (Also:
  `.convert("L")` on a transparent PNG makes bg black → use the ALPHA channel as the mask.)

**First pair `pink-goku` (anime) — BIG finding, overturns our anime defaults:** 118 fill + 217
outline objects (outline:fill 1.84:1), 7 colours; VP3 = 120mm, **satin 82.9% / fill 4.7%**, satin
width 2.25mm. So **anime is SATIN-DOMINANT + outline-heavy**, NOT the fill/photo-heavy 12-colour
thing the pipeline assumes (`CATEGORY_COLORS[anime]=12`, `category_satin_dominant(anime)=False`
because anime had ZERO ground truth — see [[vp3-fingerprint-and-satin-gap]]). Cross-confirms the
anime tutorials (REI = "sombras con satin, refuerzo tatami"). RECOMMENDED (flagged n=1, confirm w/
~2 more anime pairs before changing defaults): anime → satin-dominant (7mm ceiling + satin-lean/
vwidth), colours 12→~7-8, dedicate satin/run objects to the character linework. Callout added atop
`anime/best-practices.md`. Ties [[per-region-tiering]], [[vwidth-satin]], [[wilcom-manual-rules]].

**INTEGRATED + BUILT (2026-07):** ① added `anime/pink-goku.VP3` → regen fingerprint → anime profile
(82.9% satin) → `category_satin_dominant(anime)=True`. ② `CATEGORY_COLORS[anime]` 12→8. ③ NEW
**broad-region satin strip-tiling** (`stitches._satin_strip_lines`, under `--satin-lean`): a broad
region that would tatami-fill is sliced into parallel PCA-oriented satin columns ("sombras con
satin") via `_keep_as_fill` (routed through it from all 3 fill sites). Validated on the goku render:
satin_frac **20.9%→40.9%** (satin-dominant+colours) **→90.1%** (strip-tiling) = matches the 82.9%
truth. ④ **TURNING SATIN built (2026-07-10)** (`stitches._turning_satin_lines`, tried FIRST on the
satin-lean path; straight strips = fallback only): onion-peel the region by its EDT — each ring's
centerline is a marching-squares iso-contour at an equalised ≤3mm depth step, so the outer ring
hugs the boundary and edges stay clean on blobby shapes (the strips' stepped-edge limitation is
FIXED). Hand-rolled marching squares + RDP, scipy only. NOTE the gate: a colour only reaches
`_keep_as_fill` if it entered the linework pre-pass (`_linework_indices`) — a PURE solid-blob
colour with no sub-ceiling linework never gets strips/rings (stays tatami); and a blob whose
area÷skeleton width lands UNDER the ceiling (~9mm satin-lean) goes branch-satin instead. Tests:
test_turning_satin.py; validated end-to-end (wavy blob → 7 nested rings, satin_frac 100).
G4 refinements (2026-07-11): ring seams STAGGERED ~1.5 steps + one-step closure overshoot (no
aligned radial seam, no closure wedge) and the travel planner drops the ring-to-ring trims (blob
region 1 trim, was ~7). SPIRAL-AS-ONE-COLUMN DISPROVEN by measurement: turns touch (step=width) →
the column's rails graze neighbouring turns → Ink-Stitch rail pairing degenerates (median stitch
13.7mm fraction-paired / 14.6mm with explicit rungs, vs the 3.3mm width); `_spiral_rings` kept as
tested geometry only, never emitted. Branch junctions MITRED (`_mitre_branch_junctions`: each
branch centerline extends past a shared junction by the local half-width, clamp 0.5-2mm, >4 ends
= dense hub skipped); wavy-Y fixture junction ~100% covered (2.6% bare in the ±0.5mm disc). Travel
cover masks now fill the satin column area (polygon between rails) — thin rail-line masks
under-measured cover and blocked the ring-chain trim drops.
