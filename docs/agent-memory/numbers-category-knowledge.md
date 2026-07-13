---
name: numbers-category-knowledge
description: "Numbers/digits embroidery category — recipe for years/numerals (open counters, isacord, block vs script vs 3-D), and the 3 worked 2027 examples"
metadata: 
  node_type: memory
  type: project
  originSessionId: ca36a230-5d16-4263-8ebe-e8a6c15fdb8d
---

`numbers/numbers-embroidery-knowledge.md` is the category doc for **digit glyphs**
(years/scores/numerals). Numbers are the **LETTERS family** (playbook routes them there);
the wired-in pointers live in `EMBROIDERY-PLAYBOOK.md` (header list, §1 router sub-branch,
§2.1). Reference VP3s analysed: `Design10` (`2026` bold-rounded, 1 orange, contour fill),
`Design15` (`2026` blackletter, black+white inline keyline, 27 alternating blocks, satin),
`Design2` (single ornate `1`), `1212` (529 mm font-specimen scatter — outlier).

**Digit-specific levers (what's NEW vs letters):**
- **Open the counters `0 4 6 8 9`** — digits are counter-heavy; always `--open-counters`. [[open-letter-counters]]
- **Three sub-styles:** block/bubble → `--purify-colors` + `auto_fill` (never `--lettering`, it shatters rounded — [[lettering-mode-vs-purify]]); brush/script → `--purify-colors` + `--fill-method contour_fill` ([[contour-fill-for-calligraphy]]); shaded/3-D → isacord + flatten textured face.
- **isacord for bright digits** (blue/red); madeira has no pure blue. [[thread-chart-by-palette]]
- **Purify ONLY true primaries:** photo-2 sky-blue purified worsened ΔE 9.8→19; drop purify, use `--open-counters` directly. (Same trap as simple-shapes.)
- **⭐ Snap textured/anti-aliased digit art to a crisp SOLID-colour mask before tracing** (the biggest quality lever, fixes two failures with one move): a **halftone/sequin face** traced raw goes **spiky+sheared** (phantom satin columns fan out as radial spikes — photo 3 first pass was unreadable); **anti-aliased bold art** traced raw **fattens & blocks up** (photo 2 first pass: heavy, first `2` bowl half-closed). Fix: binary mask the true ink → closing(bridge star gaps, not counters)+opening+keep big components → repaint solid BRIGHT ink (red→Poppy ΔE0, not muted median→Cardinal ΔE9.6) on white. Worked sources `2_clean.png`/`3_clean.png`. [[halftone-face-flatten]] Also: composite transparent PNG ground onto white first (else convert→black field).
- **3-D extrude / drop-shadow = Phase-B hand-finish** (a sewn-first back facet) — tracing a 2nd dark cone muddied the palette. Cleanest faithful pass = face-only solid numeral, counters open.

**3 worked `2027` examples in `numbers/output/` (all gate PASS, single clean cone each):** `num1_script` (1.jpg direct: black madeira, purify, contour_fill — IoU 88.6/cov 99.3), `num2_bubble` (2_clean.png: isacord open-counters, Reef Blue ΔE9.6 — IoU 79.1/cov 90.9), `num3_varsity` (3_clean.png: isacord purify, Poppy ΔE0 — IoU 70.7/cov 99.9). Tools copied to `numbers/tools/`. **Lesson the hard way: never ship the first render of textured number art — eyeball it vs the original; #2 and #3 both needed the solid-mask re-prep.**

Standing directive applied: compared every output to its source photo and explained each drift before delivering. [[compare-output-to-original-iterate]]
</content>
