---
name: decoration-category-knowledge
description: Decoration category recipe (ornamental embellishment) + the thin-ink-on-white --colors-1 washout trap
metadata: 
  node_type: memory
  type: project
  originSessionId: 25ee8a10-83bc-42e6-a22b-cfb4f483f294
---

**Decoration** = the ornamental-embellishment category (7th), distilled from 45 ground-truth
`.VP3` in `decoration/` (knowledge: `decoration/decoration-embroidery-knowledge.md`; wired
into [[vp3-production-knowledge]] / the playbook router+§2.7+§8, and the photo-to-vp3 skill).

DNA: **symmetric/repeating thin SATIN ornament that adorns** — florals, vines, scrolls,
mandalas/rosettes/doilies, wreaths, frames/cartouches, lace collars/necklines, borders.
**94% of reference blocks are satin** (satin-everywhere like Arabic but botanical/geometric
& multi-colour-capable). 7 sub-types; structure = radial / bilateral / translational.
Recipe: **size by PLACEMENT not hoop** (border 150–1160 mm & AR to 10:1, mandala 79–280 mm,
FSL 33–55 mm, collar 100–380 mm); **`--colors 1`** tone-on-tone typical (the recurring
`(0,153,0)` "Dark Green" is a placeholder cone) up to 9 for florals; **`--fill-method
contour_fill`** default; **isacord** for bright clean / **madeira-polyneon** for muted
botanical; many trims (up to 231) = disjoint elements not fragmentation. One special object:
**open net/mesh lace fill** (`djanna` collar). Honest boundary: tracer renders closed-cell
ornament as **clean fills** (gate-passing), not the references' hand-satin sheen → **build**
(open-centerline SVG + satin + mirror/array) like 3D facets.

**Why:** new category the user supplied as a zip; same measured-not-guessed capture approach
as the others.

**How to apply:** route ornamental/adorning art here (not simple-shapes, which is single
icons). KEY non-obvious trap learned calibrating the test: **thin ink on white + `--colors 1`
washes the colour pale** — the k=1 quantiser centroid = weighted mean of (ink + kept
white from trapped interiors/anti-alias halos), so pure green `(8,84,54)` came back grey
`(95,145,125)` ΔE 8.3. **`--open-counters` fixes the trace mask but NOT the colour** (the
centroid is computed before the counter-drop) and can crash step 5 on sub-1.2 mm slivers.
Real fixes: **solid-fill the ornament** (no hollow outlines — the tracer fills it anyway)
and **don't trap page-colour inside an enclosing frame/ring** (leave it open to the border);
render synthetic art at the ~1200 px work resolution so no downscale halo. With that, the
test (radial leaf-rosette, 130 mm, isacord, contour_fill) hit **source-coverage 99.9%, IoU
86.4%, Green Dust ΔE 6.1, gate PASS** — `decoration/output/decoration_test_pro.vp3`.
