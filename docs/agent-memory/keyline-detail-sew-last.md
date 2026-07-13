---
name: keyline-detail-sew-last
description: "Black linework restored by the consolidate fix was then BURIED by sew order (skin fill after black + pull-comp closes sub-mm holes); fixed by splitting black into base + KEYLINE_DETAIL_RGB (1,1,1) sew-last layer"
metadata: 
  node_type: memory
  type: project
  originSessionId: 924bc32f-b27b-45e3-9c66-e94ee4b9f18d
---

**Second face-erasure mechanism** (found after [[consolidate-erases-interior-linework]] was fixed): the mouth stitches existed in the VP3 but were invisible — `trace._sew_order` put Black 2nd and the skin fill (Twine) 7th, because black plays TWO roles: hair/jacket = base panels (enclose the face → depth says sew early) and mouth/brows = detail linework (must sew last). One colour = one sew stop, so aggregation picks wrong for one role; the skin fill's pull-comp (~0.2mm/side) then closes the 0.3–0.4mm mouth-shaped hole in the cutout trace, burying the earlier-sewn line. Playbook rule this violates: "skin & base fills → shading → hairline & outlines LAST".

**Fix (2026-07-13):** preprocess `_split_keyline_detail` — after the black re-impose, thin black components (EDT half-width ≤ `_KEYLINE_HALF_MM`=1.0mm) move to sentinel palette colour `config.KEYLINE_DETAIL_RGB=(1,1,1)`; thick black stays (0,0,0) at its enclosure depth (white-text-on-black-panel unaffected). The sentinel matches the same Black cone in step 3 (two stops, one cone — production-normal) but is EXEMPT from `_merge_shared_cones` (would undo the split), and `_sew_order` pins it last. Underlap then automatically extends the fills UNDER the detail strokes.

**Third mechanism (also fixed 2026-07-13): vtracer's whole-image cutout culls 1-2px strokes.** The full multi-colour `convert_pixels_to_svg` pass drops the thinnest strokes of a layer even at `filter_speckle=0`, while the SAME mask traced alone (`_trace_single_colour`) keeps them. Every colour except the last-sewn gets an isolated re-trace via the underlap loop — the keyline-detail layer sews LAST (no later neighbour) so it was the one colour left on the lossy cutout paths. Fix: trace.run always isolated-re-traces the KEYLINE_DETAIL_RGB group. Test: `test_keyline_detail_group_keeps_thin_stroke`.

**Diagnosis pattern for "detail invisible in preview":** check in order ① preprocess quantized image (consolidate/repair loss) → ② traced group renders per colour at NATIVE work resolution with a programmatic pixel-window check — do NOT eyeball crops; the working SVG content carries a scale transform (fg-crop) and mislocated crops caused two wrong intermediate conclusions here → ③ VP3 stitch probe at the location (pyembroidery) + per-colour block order (sew-order burial). Related: [[snap-black-outline]], [[underlap]], [[wilcom-stitch-type-taxonomy]].
