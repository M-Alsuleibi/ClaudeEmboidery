---
name: arabic-no-outline-objects
description: "Arabic runs must pass --no-outline-objects; the auto-on satin border wraps fills = the \"outline-satin + fill\" hybrid the user rejects as non-production"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9cd6d6c4-69de-4dc2-bd21-0a41c3a0f079
---

For **Arabic** calligraphy, always add **`--no-outline-objects`** to the recipe. `--outline-objects`
is AUTO-on for satin-dominant categories (incl. arabic), and on thin script it lays a **satin
border around each contour_fill core** — the user calls this out as wrong: "you did the first
letter right, then did outline satin and fill ... its hard requirement to follow production-ready
work." Production Arabic is one clean object per stroke, never a border-wrapped fill.

**Why:** the border hybrid is double structure production never uses, and it inflated density
(1.1 → 0.84 st/mm², back into the reference 0.4–0.8 band) once removed.

**How to apply:** the faithful Arabic recipe is `--colors 1 --purify-colors --fill-method
contour_fill --no-outline-objects --pull-comp-mm 0.05` (madeira). contour_fill runs stitches
ALONG each stroke, so the fingerprint reads satin_frac=100 and coverage ~90%.

**Do NOT "fix" it by forcing full satin** (`--satin-lean --vwidth-satin`): tested on tawfiq it
made 30 satin columns / 0 fill but the tracer can't dissect connected cursive without
fragmenting — coverage collapsed 90% → 70%, word illegible. That's the [[contour-fill-for-calligraphy]]
/ arabic-knowledge §7 honest boundary: literal all-satin on connected cursive is a Phase-B
hand-digitize job in Wilcom, not something a raster tracer delivers. See [[vp3-fingerprint-and-satin-gap]].
