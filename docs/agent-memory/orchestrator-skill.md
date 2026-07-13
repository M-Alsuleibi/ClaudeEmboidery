---
name: orchestrator-skill
description: "The `orchestrator` skill is the single entry point for photo→.vp3; supersedes photo-to-vp3; any-format normalize + iterate-to-faithful loop"
metadata: 
  node_type: memory
  type: project
  originSessionId: c3a6df67-7006-4cb7-8134-3f688b1abc45
---

`.claude/skills/orchestrator/` is now the **single front-door skill** for turning any image
into a production-ready `.vp3`. It **supersedes `photo-to-vp3`**, whose trigger is neutralized
(its SKILL.md is a deprecation stub pointing here) — route all photo→embroidery / digitize /
`.vp3` requests to `orchestrator`.

**Folder convention (the user's standing rule):** the user drops the photo(s) to digitize in
**`input/`** at the repo root; the skill collects **each design's results in its own subfolder
`orchestrator/output/<name>/`** (original photo moved in + `<name>_src.png` + `_pro.svg/.vp3/
_preview/_threadlist` + `_overlay.png`), never loose files in `orchestrator/output/` itself, and
**leaves `input/` empty** when done. `.gitignore` ignores `/input/*` (keep `.gitkeep`) and
`/orchestrator/output/`.

What it adds over the old skill:
- **Any input format** via `scripts/normalize_input.py`: Pillow (PNG/JPG/WEBP/AVIF/TIFF/PSD/GIF/
  BMP) + pillow-heif (HEIC) + cairosvg (SVG/PDF), each with a PATH fallback
  (`heif-convert`/`rsvg-convert`/`pdftoppm`/ImageMagick). Applies EXIF rotation, flattens
  alpha, rasterizes vector big. Emits a JSON line with px size + aspect + alpha.
- A real **iterate-until-faithful** verify loop (symptom→cause→fix table in SKILL.md).
- `scripts/compare_to_photo.py` here is **background-aware** (samples the image border like the
  pipeline does) — the category `tools/` copies assume white bg and understate coverage on a
  tan/coloured/textured ground (e.g. `samples/ritaj-name.png` read 25% → ~59% after the fix).

Env change made for this: **installed `pillow-heif` + `cairosvg` into `.venv`**. Install via
`.venv/bin/python -m pip …` — **`.venv/bin/pip` has a stale shebang** (old path
`/home/mohammad/new-wilcom-v1/...`), same reason the `wilcom-pipeline` console script is stale;
always drive the pipeline through `scripts/digitize.sh`.

Gotchas seen: system `grep` is **ugrep** — a `-E` pattern beginning with `->` is read as an
option; use `grep -E -- "…"` or avoid a leading `-`. Madeira-Polyneon matched pure black
(0,0,0) at dE ~20 and pure red poorly → for bright/pure primaries (incl. block black+red
lettering) use **isacord** (extends [[thread-chart-by-palette]]).

Two fill-choice rules learned on a 10-photo batch (now in the skill's iterate table + refs):
(1) **`contour_fill` is for THIN sprawling ornament only** — thick display calligraphy, broad
cut-paper shapes, chunky logos are *broad-solid* → `auto_fill`, else contour hatches them
**hollow** (concentric rings). (2) **Fine hairline line-art** (tattoo florals/celestial,
`--colors 1`) reads **pale gray** from upscale halos; `--purify-colors` → black, but on very
thin geometry purify **crashes** `contour_fill` (`NoneType … length`) and `auto_fill` **hangs**
— then instead **binarize the source** (threshold ~<200) + plain `contour_fill`, and if the
cone still lands gray, **stamp it black** post-hoc (`pe.read`→`set_color(0,0,0)`→`write_vp3`).

Validated end-to-end on 3 formats×categories: HEIC block-caps (letters, 91% cov after dropping
--lettering which shattered them), SVG icon set (simple-shapes, 100% cov, isacord), PNG Arabic
mixed name (contour_fill + purify, density 0.69 in band). Related: [[vp3-production-knowledge]],
[[compare-output-to-original-iterate]], [[lettering-mode-vs-purify]].
