---
name: metallic-3d-lettering
description: "Shiny gold/chrome 3D letters & numbers — keep tonal bands (don't snap to solid), isacord for warm gold; recipe in 3D doc §9"
metadata: 
  node_type: memory
  type: project
  originSessionId: ca36a230-5d16-4263-8ebe-e8a6c15fdb8d
---

Shiny **metallic 3D lettering/numerals** (gold/chrome glossy type with bevels) is a hybrid
documented in `3D/3d-embroidery-knowledge.md` **§9**. Worked example: `3D/image.png` (vertical
gold `2026`) → `3D/output/gold2026_pro.vp3` (gate PASS, IoU 85.7/cov 88.0).

Key rules (counter-intuitive vs the flat-numeral recipe):
- It's a **smooth gradient, NOT flat facets** → run through the **photo pipeline**, do **NOT
  author facets**, and crucially **do NOT snap to a solid-colour mask** (the opposite of the
  textured-*flat*-numeral fix [[halftone-face-flatten]]). **Keep the tonal bands** (`--colors
  3–4`): quantising the gloss into highlight + mid + dark-bronze IS the 3D shading (3D doc §1
  shade-per-region on a gradient). Keep the near-white specular highlight cone — it's the shine.
- **isacord for warm gold**: Wheat ΔE3.3 / Antique ΔE6.6 / Taupe ΔE3.6 / Ghost-White ΔE2.4;
  **Madeira golds skew greenish** (Pistachio/Autumn-Green). [[thread-chart-by-palette]]
- **`--open-counters`** (it's a glyph: 0/6 here), **size by the glyph** (tall stack → `--height-mm`).
- **Many trims are normal** (tonal patches each trim — 104 here = 0.55%/stitch, not fragmentation).

Command: `... 3D/image.png --height-mm 160 --colors 4 --thread-chart isacord --open-counters`.
Related: [[numbers-category-knowledge]] (glyph rules), [[compare-output-to-original-iterate]].
</content>
