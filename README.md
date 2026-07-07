# wilcom-pipeline — Phase A

Turn a photo into a **production-ready, editable Wilcom `.EMB`** design.

This repo is **Phase A** only: the headless Python pipeline that runs on Linux and
produces a VP3 + worksheet + preview. The encrypted `.emb` write happens later in a
licensed Wilcom EmbroideryStudio install (**Phase B**, Windows) — `.emb`'s
`DesignDocument` stream is proprietary-encrypted and cannot be written by any script.

```
photo ─▶ ① analyze ─▶ ② preprocess ─▶ ③ thread-match ─▶ ④ trace
      ─▶ ⑤ stitches ─▶ ⑥ emit VP3 + worksheet + preview ─▶ ⑦ self-verify
```

## Artifacts (step 6)

| File | Consumer |
|---|---|
| `NAME_pro.vp3` | the Phase B AHK script (internal intermediate — *not* a deliverable) |
| `NAME_pro_preview.png` | the self-verify gate + your eyes |
| `NAME_pro_threadlist.txt` | thread assignment in ES + the machine operator |

The sole *real* deliverable is the `NAME.emb` that Wilcom saves in Phase B.

## Setup

```bash
/usr/bin/python3.12 -m venv .venv     # Python 3.12 (Ink-Stitch isn't ready for 3.14)
.venv/bin/pip install -e ".[dev]"
```

### Ink-Stitch (step 5)

Step 5 digitizes via **Ink-Stitch**, which isn't a pip package — it's a self-contained
binary we run headless (no Inkscape GUI needed for export). Vendor the Linux portable
bundle once:

```bash
mkdir -p vendor && cd vendor
curl -LO https://github.com/inkstitch/inkstitch/releases/download/v3.2.2/inkstitch-3.2.2-linux-x86_64.tar.xz
tar -xJf inkstitch-3.2.2-linux-x86_64.tar.xz   # -> vendor/inkstitch/bin/inkstitch
```

The step looks for `vendor/inkstitch/bin/inkstitch` (override with `INKSTITCH_BIN`).
The `vendor/` dir is gitignored (~185 MB). Stitch tests skip automatically if it's absent.

## Run

```bash
.venv/bin/wilcom-pipeline photo.png --width-mm 80
# or
.venv/bin/python -m wilcom_pipeline photo.png --height-mm 50 --colors 6 --thread-chart isacord
```

Give a target size with **either** `--width-mm` **or** `--height-mm` (the other
dimension is derived from the source aspect ratio).

## Status

**Phase A runs end-to-end** — all 7 steps implemented (analyze → preprocess →
thread-match → trace → stitches → emit → verify). One command on a photo + size
produces `NAME_pro.vp3` + `NAME_pro_preview.png` + `NAME_pro_threadlist.txt`, with a
pass/fail quality gate. Run `.venv/bin/pytest` (44 tests; stitch/emit cases need the
vendored Ink-Stitch binary and skip without it).

Step 5 tuning so far: `inkstitch:*` params for fill underlay, ~0.4 mm density, pull
compensation, `trim_after` (long hops trimmed → Break-Apart boundaries), **satin
columns for linework colours** (calligraphy/text/thin strokes: `fill_to_stroke` →
`stroke_to_satin`, with a tatami-fill fallback per region), and **foreground-last
sequencing** (sew order by enclosure depth — backgrounds first, enclosed detail last).

Step 6 also **stamps the matched cone into the VP3 threads** (`catalog_number` /
`description` / `brand`), so Wilcom/Hatch opens the file with named cones, not bare
RGB — matching the production reference files. See `letters/letters-embroidery-knowledge.md`
for the measured `.vp3` binary format + the letters/name-calligraphy recipe (the
format & thread-metadata sections there are cross-cutting; the `anime/` and `3D/`
docs cover those categories).

**Picking the right category & flags for any photo** is documented in
[`EMBROIDERY-PLAYBOOK.md`](EMBROIDERY-PLAYBOOK.md) — the router across letters / 3D /
anime (region→object rules, sew order, colour/size, and which flag to use).

**`--lettering` mode** (block / typeset glyphs): calibrated against production
ground-truth (`letters/10000`–`12000.VP3`), it routes letter strokes to **satin
columns** (dissecting each glyph into stroke-columns, not filling it), raises the
satin-width ceiling, and **snaps inks to pure colour**. Use it for block capitals /
typeset words at a size that keeps strokes ~2–4 mm. It *shatters cursive/script*, so
for **mixed** designs (display caps + cursive) use **`--purify-colors`** instead: it
applies only the colour snap — near-pure primaries → pure, **custom/muted brand colours
kept verbatim** (e.g. teal `42,133,143`, never neon) — on the safe default
fill/satin classification. A raster trace only *approximates* typeset lettering; for a
known phrase, typeset directly in Wilcom (Phase B). See knowledge doc §8a–§8b.

A draft **Phase B** script (`phase_b/emb_save.ahk`) takes the VP3 into Wilcom and saves
the `.emb`; it's authored but untested against a live ES (needs Windows + a dongle).

Next: validate Phase B on Windows; per-stroke variable satin width. Note: stitch tests
invoke Ink-Stitch, so the suite takes ~1–2 min.

## Layout

```
src/wilcom_pipeline/
  cli.py            argparse entrypoint
  config.py         PipelineConfig (request) + PipelineContext (shared state)
  pipeline.py       orchestrator: runs steps 1-7 against the context
  color.py          sRGB->CIELAB + dE (quantize + thread match)
  imaging.py        image loader + foreground-mask rebuild
  catalog.py        Ink-Stitch .gpl palette parser + nearest-cone match
  steps/            one module per step, each exposing run(ctx)
data/threads/       Madeira/Isacord catalogs (.gpl) for step 3
vendor/inkstitch/   vendored Ink-Stitch binary for step 5 (gitignored)
samples/            input photos (gitignored)
output/             generated artifacts (gitignored)
tests/              tests per step
```

Phase B (Windows / AutoHotkey) is out of scope for this repo; see the project goal doc.
