---
name: vp3-production-knowledge
description: How this repo turns photos into production .vp3 files; per-category knowledge docs; VP3 format & thread-metadata facts
metadata: 
  node_type: memory
  type: project
  originSessionId: 5529922d-7230-459c-87fb-a41b243f58ab
---

Goal of this repo: turn a photo into a production-ready, editable `.vp3` (Husqvarna
Viking / Pfaff "VSM" format), one recipe per **category**. **`EMBROIDERY-PLAYBOOK.md`
(repo root) is the cross-category router** — given any photo it decides category
(letters/3D/anime/logo) + per-region object (the universal region→object rule) + colour/
size/sew-order, linking all three domain docs. Each category has its own knowledge doc,
learned from user-supplied reference `.vp3` files:

- `letters/letters-embroidery-knowledge.md` — any word/name rendered beautifully.
  **THE rule (§0): letterforms are 100 % SATIN** — zero tatami fills, confirmed across
  all ground-truth (10000, 11000, 12000, and 11/13 blocks of 1000–8000). Only a
  *background panel behind text* is a fill. Three satin idioms: stroke satin (script),
  filled-face satin (solid display caps), outline satin (open caps). §7–§8 are
  **cross-cutting** (VP3 binary format + thread metadata). Calibration: §8a (10000 =
  "LET'S CELEBRATE" block caps, pure Black+Red, ~58 mm); **§8b (11000 + 12000)** —
  12000.VP3 IS the production master for `let-the-adventure.jpeg` ("Let the ADVENTURE
  Begin", 140 mm, all satin, Yellow+teal+Black). Lessons: a **keyline/3D-edge is its
  own colour sewn FIRST** (back-to-front, links 3D); **snap primaries to pure but keep
  custom/muted colours verbatim** (teal 42,133,143 NOT → neon cyan). Flags: **`--lettering`**
  (block caps: satin-dissect + pure-snap) *shatters cursive*; **`--purify-colors`** (added
  this session) = colour-snap only, on the safe default classification, for **mixed**
  designs (display caps + cursive). `_purify_ink` only purifies near-pure colours
  (max≈255,min≈0); muted brand colours kept. Limit unchanged: raster trace approximates;
  exact all-satin lettering = Wilcom Phase B.
- `arabic/arabic-embroidery-knowledge.md` — Arabic calligraphy (the **script sub-type of
  letters**), calibrated end-to-end against 3 refs (Design6 رمضان مبارك, Design8 السلام
  عليكم, Design9 Basmala+oval frame). DNA: **single pure-Black (0,0,0) thread, 100 % satin**
  (77–79 % reversals), pen width 1.8–2.5 mm, areal density **0.4–0.8 st/mm²** (satin is
  sparse), 17–30 trims (dots/tashkeel/ornaments each a piece — normal). **Recipe (tested):**
  default path + `--colors 1 --purify-colors --fill-method contour_fill` (NOT `--lettering`,
  which shatters cursive). **contour_fill is THE Arabic lever** — auto_fill over-stitches
  (0.91 vs ref 0.74) and HANGS on sprawling script; contour_fill matched ref density
  (0.77/0.56 vs 0.74/0.57) and ran fast. Input MUST be crisp pure-black-on-white (soft/JPEG
  halo → phantom gray cone). Decoration (above/under/around) = same black satin, just more
  pieces; **enclosing frame sewn FIRST** (verified: Basmala output covered 98.5 % of ref ink
  incl. frame). Always `compare_vp3.py` (in `arabic/tools/`) ref vs output before delivery,
  iterate on drift; ship examples in `arabic/output/`. See [[contour-fill-for-calligraphy]].
- `anime/best-practices.md` — character/portrait digitizing (satin shading, hair relief).
- `3D/3d-embroidery-knowledge.md` — 3D shapes (per-facet tatami + distinct angles).
- `simple-shapes/simple-shapes-embroidery-knowledge.md` — **flat icons / vector shapes**,
  now calibrated against **17 refs**. **TWO archetypes** (§0/§1b): **(A) solid-fill icon**
  (stars, hearts, arrows, swirls, frames, paw+heart `5.5_inch_03ltz5`) — bold flat
  silhouette, body→tatami fill, ribbon/border→satin ~2–6 mm; **(B) single-colour LINE-ART /
  outline drawing** (dove, deer head, howling wolf+EKG, two cats, seaweed, butterfly+moon —
  the `*_inch_*` batch) — **no solid body, the whole subject is a satin OUTLINE**, one
  colour, consistent ~1.2–2.3 mm pen-line stroke, 75–80 % reversal; thin-everywhere art
  routes wholesale to satin so **--colors 1, no fill flags needed**; small solid accents
  (cat ears/paws) get auto_fill inside the line work. Trims = # disjoint strokes (seaweed
  74) = expected intricacy, not fragmentation. **Inch sizing convention** (§5a): line-art
  files named by physical size in inches (3.5/4.5/5.5/6.5/7.5″ = 89/114/140/165/191 mm) set
  on the **LONGEST** axis (±0.01″); same art re-exported at several sizes (two-cats at 4.5″
  & 7.5″) — quote a hoop-size set. Refs carry generic `brand='Default'` cones (8=Black,
  3=Red, 5=Aqua, 12=Orange, 16=Sand) — pipeline still stamps **isacord**. **Recipe (tested):
  default path + `--thread-chart isacord` + `--colors 1–4`, NO `--purify-colors`** (isacord
  nails clean colours; purify only for genuine pure primaries — over-saturates custom
  mid-tones, azure 0,122,204 → ΔE 4.1→16.6). **isacord is THE shapes lever** — Madeira
  Polyneon has no pure blue (ΔE 90) / red (14); isacord lands red/blue/aqua/pastels ΔE 0–5.
  `contour_fill` for swirl/ribbon designs only. Validated (archetype A): star cluster
  ref-covered 99.7 % (IoU 84.4), synthetic heart/star/arrow sheet source-covered 100 %
  (IoU 91.5), both gate PASS. Tools mirror arabic/ (+ colour-aware `vp3_to_photo.py`,
  `compare_to_photo.py`); worked examples in `simple-shapes/output/`. Honest limit: tracer
  fills solids; satin sheen on star arms/swirls = Phase B (or author the primitive as SVG).

Cross-cutting VP3 facts (verified, apply to every category):
- `pyembroidery.write_vp3` is the trusted writer — a read→write→read round-trip on the
  refs is byte-faithful (±2 B), preserving RGB + catalog#/description/brand. No custom
  writer needed. (Writer adds +1 trim because END is written as a trailing trim.)
- `steps/stitches.py` Ink-Stitch subprocess timeout raised 300→900 s this session: a
  dense cursive fill at 140 mm exceeded 300 s and timed out mid-fill.
- Stitch unit = **0.1 mm**; single-byte delta ±12.7 mm; VP3 has **no JUMP** (jumps
  become plain moves); TRIM = `80 03`. Y is stored negated; designs are upright.
- `steps/emit.py::_stamp_thread_metadata` stamps the matched cone (code/name/chart)
  onto VP3 threads from step-3 `thread_map` before writing — so Wilcom/Hatch shows
  named cones, not bare RGB (matching the refs). Added this session.

Final `.emb` still needs the Windows Phase-B Wilcom save; the `.vp3` is the editable
intermediate. See [[pipeline-run-stale-venv]] for how to run the pipeline.
