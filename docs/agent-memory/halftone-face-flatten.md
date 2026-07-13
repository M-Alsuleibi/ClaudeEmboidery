---
name: halftone-face-flatten
description: textured/halftone-filled letter faces trace as hollow sparse fills; pre-flatten the dot field to a solid colour before running the pipeline
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d7864143-e204-4a61-882d-9e9dd0ccb54e
---

A letter/shape **face printed as a halftone or knit texture** (red dots on light gaps)
traces as a **hollow, sparse fill** — vtracer keeps the white gaps as holes and the
tatami fill only covers the thin ink between them. The step-2 majority filter does NOT
reliably flatten it. (Seen on 3.png, red 3D "2027".)

**Why:** the dot field is real geometry at trace time; quantization preserves dots+gaps as
separate regions, so the "fill" is a lattice, not a solid.

**How to apply:** pre-flatten the source before the pipeline. Build a colour mask
(`R > G+25 & R > B+25` for red), `scipy.ndimage.binary_closing` (~11px disk, 2 iters) +
`binary_fill_holes` + `binary_opening` to merge dots into a solid region, repaint that
region one solid ink, keep the darker 3D-extrusion side (`R<150`) and the white keyline
(light, low-sat, not in the filled face) as separate inks, save RGBA, then run with
`--colors 3 --purify-colors`. Result: solid face + dark-red 3D side + white keyline,
Poppy red dE 1.49. See [[vp3-production-knowledge]], [[lettering-mode-vs-purify]].

**Same trick reconstructs a drop-shadow / keyline that the source hides:** when a layer
shares the page colour (e.g. a white outline that is the SAME RGB as a white background,
2.jpg blue bubble "2027"), colour quantization drops it. Rebuild on a TRANSPARENT bg so
white becomes a real ink: blue = `B>165 & R<150`; grey shadow = detected grey pixels
(`190≤R≤232 & sat<20`); white outline = `binary_dilation(blue,~11px) & ~blue` ring. Paint
shadow→outline→blue (back to front), save RGBA.

**Gotcha:** `--purify-colors` snaps near-white greys to pure white, so a light-grey shadow
(216,216,216 ≈ isacord 0145 Skylight) collapses INTO the white outline and disappears.
For a light-grey shadow ink, **drop `--purify-colors`** (the reconstructed source is already
flat, so purify buys nothing) and give the quantizer headroom with `--colors 4`.
