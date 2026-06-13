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

Next: Phase B (Windows AHK → Wilcom `.emb`, out of this repo's scope) and step-5
quality tuning — inject `inkstitch:*` params for fill underlay, ~0.4 mm density, pull
compensation, satin for thin columns, and foreground-last sequencing.

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
