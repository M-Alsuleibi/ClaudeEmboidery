---
name: lettering-mode-vs-purify
description: When to use --lettering (satin-dissect) vs --purify-colors (solid fill) for block caps; --lettering shatters bold/rounded/solid display caps
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c41db47b-4cc9-455a-b28b-2d7f15e2ff13
---

`--lettering` satin-dissection (fill_to_stroke → stroke_to_satin) only works on caps
whose strokes are **roughly constant-width thin columns** (the 10000.VP3 "LET'S
CELEBRATE" calibration). It **shatters** anything thick, rounded, or solid: the obada
job (heavy rounded "OBADA MOHAMMOD ALSULIBE") came out as fragmented satin columns
going every direction — barely legible. Memory already noted it shatters cursive;
this adds: it also shatters **bold/rounded/solid display caps**.

**How to apply:** for **solid display caps** (filled-face letters) use `--purify-colors`,
NOT `--lettering`. That keeps the default classifier (each complex glyph stays ONE
continuous tatami fill = clean solid letter), snaps ink to pure, and — via
[[open-letter-counters]] — opens the O/B/A/D counters. Verified: obada1/obada2 →
21 solid filled letters, 0 satin, gate PASS, faithful to original. A tatami fill
with underlay IS best-practice for solid block letters; satin is for stroke/script
weight. Reserve `--lettering` for thin-stroke block caps only.

obada inputs had design-tool artifacts (purple Illustrator selection box, red
registration crosshair, black corner handles) — stripped in a pre-clean pass that
keeps only large, dark, low-chroma connected components (the letters), then crops to
them. Run: `--width-mm 150 --colors 1 --purify-colors`. See [[vp3-production-knowledge]].
