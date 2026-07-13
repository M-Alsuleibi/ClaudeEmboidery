---
name: thread-chart-by-palette
description: "Which --thread-chart to pick — isacord for bright/clean colours (simple shapes, primaries), madeira-polyneon for muted art palettes"
metadata: 
  node_type: memory
  type: project
  originSessionId: e76c996f-dfe5-4497-8285-ac031b1c8ad1
---

`--thread-chart` is **palette-dependent, not fixed**. Measured nearest-cone ΔE:

- **`isacord`** carries true primaries + clean pastels: pure red ΔE 0, pure blue ΔE 0,
  azure (0,122,204) ΔE 4.1, aqua (51,204,204) ΔE 3.0, light pink ΔE 2.3. **Use it for
  simple shapes / flat icons / any bright-saturated or clean-pastel art.**
- **`madeira-polyneon`** (the pipeline default) is tuned for muted embroidery-art
  palettes and **has no pure blue at all** — pure blue matches "Purple Accent" at
  **ΔE 90**, pure red → Fluo Pink ΔE 14, aqua → Seafrost ΔE 14. Keep it for calligraphy
  / letters / muted designs where its cones are the intended look.

So: bright/clean palette → **isacord**; muted/art palette → **madeira-polyneon**. Check
both with `catalog.load_catalog(key).nearest(rgb)` before committing if unsure.

**This applies to LETTERS too, not just shapes** — it's palette-driven, not
category-driven. Confirmed on a bright-red block "2027" (3_clean.png): Madeira matched the
red to Fluo Pink **ΔE 13.3** + White ΔE 7.4 (2 poor matches the pipeline flagged); flipping
to **isacord** gave Poppy **ΔE 1.49** + White ΔE 0.0 (zero poor matches), gate PASS both
times. Rule of thumb: a *bright primary* letter/logo wants isacord even though letters
usually default to madeira.

**Even pure BLACK wants isacord** — Madeira's `1800 Black` cone is actually rgb
**(47,48,50)** (a dark gray), so pure black `(0,0,0)` matches it at **ΔE 19.9 "poor"**;
isacord's `0020 Black` is true `(0,0,0)`, **ΔE 0**. Measured on a black brush-script "2027"
(1.jpg). This contradicts the impression in the letters/arabic docs that Madeira `1800
Black` matches black — for a *crisp pure-black* design, isacord's black is exact. (The
arabic recipe still defaults to madeira; if its black flags poor, flip the chart.)

**Custom mid-tone azure: drop `--purify-colors`.** Re-confirmed on a sky-blue bubble "2027"
(2.jpg): purify over-saturated the azure → isacord Cerulean **ΔE 19**; *without* purify the
true azure (74,159,232) → isacord Reef Blue **ΔE 7.8**. Purify is for genuine primaries only.

Pairs with the colour-purify rule: `--purify-colors` only snaps **genuine pure
primaries**; it over-saturates custom mid-tones (azure 0,122,204 → 0,152,255 worsened
ΔE 4.1→16.6), so default OFF for shapes. See [[vp3-production-knowledge]] and
[[lettering-mode-vs-purify]].
