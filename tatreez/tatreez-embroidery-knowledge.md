# Tatreez (تطريز) — Palestinian/Levantine *fellahi* cross-stitch garment embroidery

> **Status: REGISTERED + INGESTED** (2026-07-12) — `tatreez` is a `SUPPORTED_CATEGORIES` class;
> **11 ground-truth pairs** live in `tatreez/pairs/tatreez-01..11/` and feed
> `data/category_profiles.json` (step-7 drift gate) + `data/pair_priors.json` (step-5 numbers).
> Numbers below are measured from those 11 VP3s; still refine as more pairs arrive (grid-look
> reproduction needs a cross-stitch primitive the pipeline lacks — see below).

## What the category is

Traditional **fellahi tatreez** — the counted cross-stitch embroidery of Palestinian/Levantine
garments (thobe/dress). The deliverables are **garment panels**, not hoop patches:

| pair | Design type | Size (mm) | Colors |
|------|-------------|-----------|--------|
| 01 | Vertical border band (2 rails + central motif chain) | 349 × 65 | 1 |
| 02 | Corner / L-shaped panel border (e.g. neckline corner) | 320 × 450 | 1 |
| 03 | **Full thobe front**: 2 diagonal plackets + central *qabbeh* chest panel | **1061 × 1099** | 1 |
| 04 | Round neck yoke (*qabbeh*) + rosette-grid frame | 234 × 234 | 6 |
| 05 | Horizontal rosette border band (repeating 8-petal flowers) | 191 × 62 | 4 |
| 06 | Square neck yoke + tatreez figure row | 420 × 357 | 3 |
| 07 | Small floral rose motif cluster (central ornament) | 208 | 5 |
| 08 | Square neck yoke + floral rose garland | 360 | 5 |
| 09 | Neck yoke (polychrome) | 396 | 6 |
| 10 | Long V-neck placket / chest panel | 559 | 2 |
| 11 | Geometric square neck yoke (finest grid, 1.4 mm) | 273 | 7 |

Palette across all pairs is the same pure-primary set led by green `(0,153,0)` (see below).

**Recurring layout vocabulary:** straight **rail borders**, repeating **motif chains**
(diamonds, 8-petal **rosettes**), **qabbeh** chest/neck panels, diagonal **plackets**, and rows
of the classic tatreez **figure/cypress** motif. Designs are built by tiling a small set of
counted-thread motifs on a grid.

## The defining technique: counted cross-stitch on a fixed grid

This is a **new stitch primitive** for this repo — we have run / satin / tatami tiers, but no
cross-stitch generator.

- Every design sits on a **fixed square grid**; the cell pitch is per-design and shows up as
  the fingerprint's `satin_w_mm`: **3.80 mm** for the coarse 1-color banners (#1/#2/#3),
  **2.0–2.4 mm** for the fine multi-color qabbeh panels (#4/#5). Segment lengths are almost
  perfectly uniform (p25≈p75), which is the grid signature.
- **The fingerprint mislabels it "100 % satin"** (satin_frac 98–100, fill_frac ~0) because each
  cross arm is a short, high-reversal zigzag — but it is NOT satin columns and NOT tatami. It is
  a **motif/cross-stitch fill on a lattice**. Do not read these as satin-dominant art in the
  arabic/decoration sense; the number is an artifact of the cross-stitch texture.
- **Real satin appears only as the neckline binding** — the magenta (#4) / red (#6) U-curve that
  finishes the neck opening (this is the 1.5 % genuine satin in #6). Everything else is
  cross-stitch.

## Thread & color model

- **Pure counted-thread primaries only** (DMC/cross-stitch model, not muted art):
  green `(0,153,0)`, blue `(0,0,255)`, red `(255,0,0)`, yellow `(255,255,0)`,
  cyan `(51,204,204)`, magenta `(192,0,192)`.
- **Green `(0,153,0)` is always cone #1** / the sew-order lead. Yellow tends to be the
  background-frame color of a rosette; red/blue/green/cyan are the petal accents.
- Color count scales with ornamentation: **1** for monochrome banners/plackets, **3–6** for
  polychrome qabbeh/rosette panels. So the category prior is *not* a single number — pick by
  design type (banner=1, rosette panel=3–6).

## Measured numbers (the 11 pairs → priors)

Cell pitch = the fingerprint's `satin_w_mm`; density = thread spacing.

| pair | density (mm) | cell pitch | satin_frac | notes |
|------|--------------|-----------|-----------|-------|
| 01 | 0.31 | 3.80 | 100 % | loose coarse banner |
| 02 | 0.28 | 3.85 | 100 % | corner panel |
| 03 | 0.10 | 3.83 | 100 % | full dress front (huge) |
| 04 | 0.91 | 2.01 | 100 % | dense fine qabbeh |
| 05 | 1.00 | 2.42 | 100 % | rosette band |
| 06 | 0.39 | 2.25 | 98.5 % | qabbeh + figure row, red satin neck binding |
| 07 | 0.63 | 2.24 | 100 % | rose motif cluster |
| 08 | 0.59 | 2.10 | 100 % | square neck + rose garland |
| 09 | 0.49 | 2.24 | 99.98 % | polychrome neck yoke |
| 10 | 0.60 | 2.24 | 100 % | long V-neck placket |
| 11 | 0.50 | 1.41 | 100 % | geometric square yoke (finest grid) |

Density (thread spacing) spans **0.1–1.0 mm** and tracks how filled/coarse the grid is — coarse
open banners ≈ 0.1–0.3, dense polychrome panels ≈ 0.5–1.0.

**Learned priors** (`data/pair_priors.json`, n=11): satin-width p10/med/p90 = **1.4 / 2.1 / 2.41 mm**,
crossover **2.41 mm** (→ clamped to a **3 mm** satin ceiling in step 5), **0 fill objects** across
all 11 (all-outline = the counted-grid look), median **4** colours. Profile
(`data/category_profiles.json`): 11 files, 100 % "satin", satin-w 2.24 mm, density 0.50, longest 360 mm.

## The cross-stitch primitive (BUILT — `steps/crossstitch.py`)

Tatreez is generated by a dedicated **counted cross-stitch** primitive, not the run/satin/tatami
tiers. It is selected by `--cross-stitch` (AUTO-on for `config.CROSS_STITCH_CATEGORIES` = tatreez;
force with `--cross-stitch`/`--no-cross-stitch`) and short-circuits the whole SVG/Ink-Stitch path
in step 5.

- **Grid.** A fixed square grid over the palette-quantised image; cell pitch = the pair prior
  (tatreez's satin-width median ≈ 2.1 mm) or `--cross-stitch-pitch-mm`. Each cell takes the
  **majority** palette colour among its opaque pixels (background-dominated cells are skipped) —
  a clean single-colour-per-cell counted partition.
- **Each covered cell = an X** (BL→TR→TL→BR = both diagonals + a short edge connector). The
  sharp per-corner **reversals give the high-reversal "satin-like" character** the fingerprint
  reads as counted cross-stitch (satin_frac ≈ 100, matching the ground truth). A smooth
  diagonal-hatch *looks* cleaner but reads as a FILL — measured satin_frac 100 → 7 — so it was
  rejected. Colours sew in palette order (COLOR_CHANGE between), disjoint cell clusters per
  colour are separated by a TRIM (Break-Apart).
- **Built directly with pyembroidery** (no Ink-Stitch): the penetrations are known, so there is
  nothing to trace; and Ink-Stitch's only exact-node mode (`manual_stitch`) *hangs* the router
  (measured: a 6-node manual path never returned in 280 s). Thread cones are still named in step 6
  by RGB match, so the VP3 stays consistent with every other category.
- **Verified**: a rasterised tatreez-05 run scores in-band on satin_frac (100), fill_frac (0),
  colours, and satin width; density runs marginally high (≈0.66 vs the 0.35–0.61 band) because the
  per-cell X adds an edge connector — a `[~]` note, not a failure.

## Still open (refinements, in priority)
1. **Match production's connector-free diagonal lattice.** Production weaves crosses so every
   segment is a diagonal arm (no axis-aligned edge connectors) on a 2:1 (3.4 mm × 1.7 mm) lattice
   — cleaner than our per-cell X's edge connector — while *keeping* high reversal. Reproducing
   that exact weave would drop the small density drift and match the look precisely.
2. **Satin neckline binding** — the one true-satin object (the magenta/red U-curve around a neck
   opening); currently cross-stitched like everything else. Detect the neck edge and satin it.
3. **Garment-scale handling** — targets are 20–110 cm, beyond a single hoop; large fronts imply
   multi-hooping/split. `--width-mm`/`--height-mm` drive it, but expect big values.
4. **Motif/tile library** — rosettes/diamonds/rails/figures are a reusable vocabulary; a motif
   catalog would let us assemble rather than quantise onto the grid.
5. Collect more pairs (esp. plackets/bands vs qabbeh); the median colour prior (4) is a
   mono-banner-vs-qabbeh compromise — consider picking colours by design sub-type at run time.
6. Add tatreez to the router docs (`EMBROIDERY-PLAYBOOK.md`, orchestrator routing) so a dropped
   garment photo routes here.
