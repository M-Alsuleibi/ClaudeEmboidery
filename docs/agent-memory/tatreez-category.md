---
name: tatreez-category
description: tatreez category (RENAMED from falahi 2026-07-13) = Palestinian tatreez cross-stitch garment embroidery; cross-stitch primitive built (steps/crossstitch.py)
metadata: 
  node_type: memory
  type: project
  originSessionId: 1bb2285a-9c69-47d2-bb5e-fb3d9982dbf6
---

**Tatreez (فلاحي)** is a NEW embroidery category: traditional Palestinian/Levantine **tatreez
counted cross-stitch** on **garments** (thobe/dress) — necklines (*qabbeh*), plackets, rosette
border bands, full dress fronts. **REGISTERED + INGESTED 2026-07-12**: added to
`config.SUPPORTED_CATEGORIES` + `CATEGORY_COLORS` (=4); **11 pairs** ingested to
`tatreez/pairs/tatreez-01..11/` → priors built (`data/pair_priors.json`: satin-w 1.4/2.1/2.41mm,
crossover 2.41→3mm ceiling, 0 fill objects = all-outline grid) + profile
(`data/category_profiles.json`: 11 files, 100% "satin"). Knowledge doc
`tatreez/tatreez-embroidery-knowledge.md`. NOTE: fixed `register_pair.py` to resolve CSS **named**
colours (blue/red/yellow) — polychrome CorelDRAW exports use names not hex (was crashing
`int('LU',16)`).

Key facts:
- **Defining stitch = counted cross-stitch on a fixed square grid** (per-design cell pitch = the
  fingerprint's `satin_w_mm`: 3.8mm coarse banners, 2.0–2.4mm fine qabbeh). The pipeline now HAS a
  [[cross-stitch-primitive]] for this (built 2026-07-12, `steps/crossstitch.py`, `--cross-stitch`
  AUTO-on for tatreez) — no longer a gap.
- The step-7 fingerprint **mislabels cross-stitch as "100% satin"** (each X arm = short
  high-reversal segment); do NOT read tatreez as satin-dominant art. Real satin appears ONLY as
  the neckline binding (magenta/red U-curve).
- Palette = **pure counted-thread primaries** (green (0,153,0) ALWAYS cone #1, then blue/red/
  yellow/cyan/magenta); color count 1 (mono banner) → 3–6 (polychrome qabbeh).
- **Garment-scale**: 20–110cm (a full dress front measured 1061×1099mm), beyond hoop → multi-
  hooping/large-field; size by garment placement.

`/tatreez/*.svg` is gitignored (large scratch); the knowledge doc + future `tatreez/pairs/` track.
Related: [[vp3-fingerprint-and-satin-gap]] (satin_frac artifact), [[wilcom-stitch-type-taxonomy]]
(cross-stitch/motif = the "unbuilt future tier"), [[pair-priors]], [[svg-vp3-pairs]].
