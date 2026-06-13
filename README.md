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

> **Ink/Stitch** is not a plain pip dependency — it's an Inkscape extension and gets
> vendored separately. Step 5 (`stitches`) is where it (or an equivalent digitizer)
> plugs in. Until then the pipeline runs as a skeleton and stops at the first
> unimplemented step.

## Run

```bash
.venv/bin/wilcom-pipeline photo.png --width-mm 80
# or
.venv/bin/python -m wilcom_pipeline photo.png --height-mm 50 --colors 6 --thread-chart isacord
```

Give a target size with **either** `--width-mm` **or** `--height-mm` (the other
dimension is derived from the source aspect ratio).

## Status

Scaffold only. Every step in `src/wilcom_pipeline/steps/` is a documented stub that
raises `NotImplementedError`; the orchestrator stops cleanly at the first one. Build
order = step order. Run `.venv/bin/pytest` for the smoke tests.

## Layout

```
src/wilcom_pipeline/
  cli.py            argparse entrypoint
  config.py         PipelineConfig (request) + PipelineContext (shared state)
  pipeline.py       orchestrator: runs steps 1-7 against the context
  steps/            one module per step, each exposing run(ctx)
data/threads/       Madeira/Isacord catalogs (CSV) for step 3
samples/            input photos (gitignored)
output/             generated artifacts (gitignored)
tests/              smoke tests
```

Phase B (Windows / AutoHotkey) is out of scope for this repo; see the project goal doc.
