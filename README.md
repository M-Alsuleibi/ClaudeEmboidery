# wilcom-pipeline

Turn a photo into a **production-ready Wilcom `.vp3` embroidery file** (+ worksheet + preview),
headless on Linux (Python 3.12).

```
photo ─▶ ① analyze ─▶ ② preprocess ─▶ ③ thread-match ─▶ ④ trace
      ─▶ ⑤ stitches ─▶ ⑥ emit VP3 + worksheet + preview ─▶ ⑦ self-verify
```

The **`.vp3` is the deliverable** — a complete, machine-stitchable embroidery file with named
thread cones, in sew order. If you also want Wilcom's *editable native* `.emb`, open the VP3 in a
licensed EmbroideryStudio and **File ▸ Save As** (a one-off manual step: the `.emb`
`DesignDocument` stream is proprietary-encrypted and can't be written by any script — that's a
Wilcom-only save, not something this pipeline needs to do).

## Artifacts (step 6)

| File | Consumer |
|---|---|
| `NAME_pro.vp3` | the deliverable — the machine / any embroidery software / Wilcom |
| `NAME_pro_preview.png` | the self-verify gate + your eyes |
| `NAME_pro_threadlist.txt` | thread assignment + the machine operator |
| `NAME_working.svg` | the editable object-level design (inkstitch params) before flattening |

## Setup

```bash
/usr/bin/python3.12 -m venv .venv     # Python 3.12 (Ink-Stitch isn't ready for 3.14)
.venv/bin/pip install -e ".[dev]"
```

### Ink-Stitch (step 5)

Step 5 digitizes via **Ink-Stitch**, which isn't a pip package — it's a self-contained binary we
run headless (no Inkscape GUI needed). Vendor the Linux portable bundle once:

```bash
mkdir -p vendor && cd vendor
curl -LO https://github.com/inkstitch/inkstitch/releases/download/v3.2.2/inkstitch-3.2.2-linux-x86_64.tar.xz
tar -xJf inkstitch-3.2.2-linux-x86_64.tar.xz   # -> vendor/inkstitch/bin/inkstitch
```

The step looks for `vendor/inkstitch/bin/inkstitch` (override with `INKSTITCH_BIN`). `vendor/` is
gitignored (~185 MB). Stitch tests skip automatically if it's absent.

## Run

Two entry points:

```bash
# 1) direct — one photo, one size
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline photo.png --width-mm 80 --category anime

# 2) orchestrator (recommended) — drop any image in input/, it categorises + iterates
#    (invoked as the `orchestrator` skill; normalises HEIC/SVG/PDF, picks the recipe, verifies)
```

Give a target size with **either** `--width-mm` **or** `--height-mm` (the other dimension follows
the source aspect ratio). Pass `--category` so the run is tiered + scored against that category's
ground-truth recipe; see `--help` for the full flag set.

## How it works

A photo flows through **7 ordered steps** (`pipeline.py` runs them against a shared context). The
core model: a design is **a set of regions, each becoming one stitch object chosen by its
geometry, sewn back-to-front**. Step 4 vectorizes per thread-colour; step 5 tiers **each region by
its own width** — **run** (< 1.6 mm, running/bean along the centerline), **satin** (a clean column;
≤ 3 mm fixed-width, 3–7 mm variable-width following the local half-width), or **tatami fill**
(broad/branchy). The satin/fill ceiling is **category-aware** (7 mm for satin-dominant categories,
3 mm otherwise). Step 7 renders and scores the run against its category's **fingerprint**
(`data/category_profiles.json`) so drift from real production is visible per run.

Decisions are documented — read before working on a category:
- [`EMBROIDERY-PLAYBOOK.md`](EMBROIDERY-PLAYBOOK.md) — router: category + technique for any photo.
- [`wilcom-manual-rules.md`](wilcom-manual-rules.md) — the official Wilcom Reference Manual
  distilled (satin ≤ 7 mm, density 0.3–0.6 mm, pull-comp by fabric, underlay, colour counts).
- [`PAIRS-FINDINGS.md`](PAIRS-FINDINGS.md) — learning
  object-level ground truth from (CorelDRAW-SVG, VP3) production pairs.
- category detail: `letters/`, `arabic/`, `3D/`, `anime/`, `simple-shapes/`, `decoration/`,
  `numbers/` (`*-embroidery-knowledge.md` / `best-practices.md`).

## Status

**Phase A runs end-to-end** — one command on a photo + size produces the VP3 + preview +
threadlist + working SVG, with a pass/fail quality gate and a production-fit drift check.

```bash
PYTHONPATH=src .venv/bin/python -m pytest        # 67 tests; ~1 min (stitch cases call Ink-Stitch)
```

Recent capability: per-region tiering, **variable-width satin** (rails follow the local stroke
width), Auto-Split satin detection, category-aware satin ceiling + colour priors, manual-calibrated
densities / pull-comp / run length, and **learning from (SVG, VP3) pairs** to sharpen each
category's recipe (see FINDINGS). Next: contour-following *turning* satin (clean edges on broad
satin regions); SVG↔VP3 registration for per-object width labels.

## Layout

```
src/wilcom_pipeline/
  cli.py            argparse entrypoint
  config.py         PipelineConfig (request) + PipelineContext (shared state)
  pipeline.py       orchestrator: runs steps 1-7 against the context
  color.py          sRGB->CIELAB + dE (quantize + thread match)
  imaging.py        image loader + foreground-mask rebuild
  catalog.py        Ink-Stitch .gpl palette parser + nearest-cone match
  fingerprint.py    per-category stitch-type profiles (step-7 drift check)
  steps/            one module per step, each exposing run(ctx)
data/threads/       Madeira/Isacord catalogs (.gpl) for step 3
data/category_profiles.json   per-category ground-truth fingerprints
vendor/inkstitch/   vendored Ink-Stitch binary for step 5 (gitignored)
input/              drop photos here for the orchestrator (gitignored)
output/             generated artifacts (gitignored)
<category>/         knowledge docs + that category's reference production VP3s
tests/              tests per step
```
