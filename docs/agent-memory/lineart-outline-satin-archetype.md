---
name: lineart-outline-satin-archetype
description: Simple-shapes has a second archetype — single-colour line-art/outline drawings sewn 100% satin; plus the inch sizing convention
metadata: 
  node_type: memory
  type: project
  originSessionId: 4eb781bf-2f3b-4338-a7a7-531f35fef6c3
---

A second simple-shapes archetype (from 11 newer `simple-shapes/` refs, the `*_inch_*` +
`Design13/14/Design4 (1)` batch): **single-colour LINE-ART / outline drawings** — flying
dove, deer head, howling wolf + EKG, two cats (yin-yang), seaweed + bubbles, butterfly +
crescent moon + stars. Distinct from the solid-fill icon archetype (paw+heart, stars).

**Why:** these are coloring-book / tattoo-flash line drawings with **no solid body — the
whole subject IS the outline**, sewn **100 % as satin columns** following the strokes
(consistent ~1.2–2.3 mm pen-line weight, 75–80 % turn-reversal). The white interior stays
background. 7 of the 11 new files are this type; it's now the dominant simple-shapes case.

**How to apply:** feed a clean black-line-on-white drawing, `--colors 1`, `--thread-chart
isacord`, **no fill flags** — thin-everywhere strokes route wholesale to satin via the
width classifier (`med width < _SATIN_MAX_WIDTH_MM = 3.0`). Small solid accents inside the
line work (a cat's ears/paws, a strawberry body) get `auto_fill`. Many trims = number of
disjoint strokes (seaweed = 74) = expected intricacy, NOT fragmentation.

**CRITICAL for OUTLINE drawings with enclosed cells (butterfly wings, the holes in a line
drawing): pass `--open-counters`.** Border-flood bg-drop only removes the OUTER white;
white islands *enclosed by the outline strokes* are kept and **filled solid → the whole
subject traces as a solid blob** (verified on a coral butterfly: without it the wings
filled solid; with `--open-counters` the wing cells/veins/centre-heart read through, IoU
80.8 %, source-covered 99.9 %). Silhouette/stroke line-art with no enclosed cells (dove,
seaweed) doesn't need it. NB: where one ink colour holds BOTH thin strokes and wide blobs
(heart+paw trail), the per-colour width classifier picks ONE object for the colour (fill),
so the thin strokes render as thin fills not satin — faithful but satin sheen = Phase B.

**Inch sizing convention:** line-art refs are named by physical size in inches
(`3.50_inch_…` … `7.50_inch_…`); the inch = the design's **LONGEST** side, matched to
±0.01″ → 3.5″=89 mm, 4.5″=114, 5.5″=140, 6.5″=165, 7.5″=191. Pass that on the longer axis
(`--height-mm` for tall art like the dove/deer/seaweed). The SAME artwork is re-exported at
several hoop sizes (two-cats ships at 4.5″ and 7.5″) — quote a size set, not one number.

Full detail: `simple-shapes/simple-shapes-embroidery-knowledge.md` §0/§1b/§5a. See
[[vp3-production-knowledge]] and [[thread-chart-by-palette]].
