# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Phase A** of a photo→embroidery toolchain: a headless Python pipeline (Linux, Python
3.12) that turns a photo into a production-ready `.vp3` + worksheet + preview for Wilcom
EmbroideryStudio. **Phase B** (`phase_b/emb_save.ahk`, Windows + AutoHotkey + a licensed
Wilcom dongle) takes that VP3 and saves the encrypted `.emb` — the only *real* deliverable.
The `.emb` `DesignDocument` stream is proprietary-encrypted and cannot be written by any
script, which is why the split exists. Phase B is out of scope for code changes here.

## Commands

```bash
# Setup (Python 3.12 — Ink-Stitch isn't ready for 3.14)
/usr/bin/python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Run the pipeline. The `wilcom-pipeline` / `pytest` console scripts may have a stale
# shebang (this venv was built at a different absolute path) and fail with "bad
# interpreter"; the `python -m` forms below always work.
PYTHONPATH=src .venv/bin/python -m wilcom_pipeline photo.png --width-mm 80

# Tests
PYTHONPATH=src .venv/bin/python -m pytest                      # 50 tests; ~1 min (stitch/emit cases call Ink-Stitch)
PYTHONPATH=src .venv/bin/python -m pytest tests/test_trace.py  # one file
PYTHONPATH=src .venv/bin/python -m pytest -k "satin"           # one test by name
```

Give a target size with **either** `--width-mm` **or** `--height-mm` (mutually exclusive,
one required); the other dimension is derived from the source aspect ratio.

There is no linter/formatter configured.

### Ink-Stitch (step 5 dependency)

Step 5 digitizes via **Ink-Stitch**, which is *not* a pip package — it's a vendored,
self-contained binary run headless (no Inkscape GUI for export):
`vendor/inkstitch/bin/inkstitch` (override with `$INKSTITCH_BIN`). The `vendor/` dir is
gitignored (~185 MB) — download the Linux portable bundle (currently v3.2.2) per the
README. Stitch/emit/verify tests that need it **skip automatically when it's absent**
(guarded by `stitches.binary_available()`), so the suite stays portable.

## Architecture

A photo flows through **7 ordered steps**, each a `run(ctx)` callable that mutates a shared
context in place. `pipeline.py` runs them in sequence; an unimplemented step raises
`NotImplementedError` and the orchestrator stops cleanly and reports how far it got.

```
① analyze → ② preprocess → ③ thread-match → ④ trace → ⑤ stitches → ⑥ emit → ⑦ verify
```

- **`config.py`** holds the two central types. `PipelineConfig` is the **frozen** run
  request (input, size, knobs) and validates itself in `__post_init__`; it also owns the
  artifact paths (`vp3_path`, `preview_path`, `threadlist_path` = `output/NAME_pro*`).
  `PipelineContext` is the **mutable** bag each step fills a slice of (`analysis`,
  `preprocessed_image`+`palette`, `thread_map`, `svg_path`, `stitch_pattern`,
  `verification`). To add a config knob: add the field + validation here, expose it in
  `cli.py`, then read `ctx.config.<knob>` in the step.
- **`steps/`** — one module per step, each exposing `run(ctx)`. The interesting one is
  **`stitches.py`** (step 5): it writes a stitch-ready SVG (injecting `inkstitch:*` params
  per path), shells out to the Ink-Stitch binary (`--extension=zip --format-vp3=True`),
  and reads the VP3 back out of the returned zip into `ctx.stitch_pattern`.
- **`color.py`** — sRGB→CIELAB + ΔE, shared by quantize (step 2) and thread match (step 3).
- **`catalog.py`** — parses Ink-Stitch `.gpl` palettes (`data/threads/*.gpl`) and finds the
  nearest cone. Supported charts are enumerated in `config.SUPPORTED_THREAD_CHARTS`.
- **`imaging.py`** — image loading + foreground-mask rebuild.

### How the digitizing decisions are made (step 4 → 5)

The core model: a design is **a set of regions, each region becomes exactly one stitch
object chosen by its geometry, sewn back-to-front**. Step 4 (`trace.py`) vectorizes with
vtracer into one SVG `<g>` per thread colour, ordered **background-first / foreground-last
by enclosure depth**, and stamps each group's `inkscape:label` with `"<code> <name>"` (the
Ink-Stitch binary carries that into the VP3 as the thread catalog number + description).
Step 5 then tiers **each region (connected component) by its own width** (region area ÷ full
skeleton length, in mm): **run** (< 1.6 mm — running/bean stitch along the centerline),
**satin** (single clean column up to the ceiling; ≤ 3 mm builds a fixed-width `fill_to_stroke` →
`stroke_to_satin`, **3–7 mm builds variable-width** rails at the local half-width so a wide
modulated stroke covers + gets a zigzag underlay; a *forked* stroke dissects into one satin per
branch only under `--branch-satin`), or **tatami fill** (above the ceiling, or branchy/mesh). The
**ceiling is category-aware** (`_satin_ceiling`): 7 mm (the Wilcom-manual value) for a
**satin-dominant** category — arabic/letters/decoration/simple-shapes/numbers per the fingerprint —
so the satin gap closes by default there; a conservative **3 mm** for 3D/anime/unknown, whose
shaded solids are meant to be fills (raising it over-satins them); 9 mm under `--lettering`/
`--satin-lean`. One colour can therefore mix all three tiers. A colour enters this
pre-pass if its **area-weighted** width is below the satin ceiling, or if it's otherwise
broad but carries a substantial keyline worth splitting out. Fills get underlay, ~0.4 mm
density, pull-comp, and `trim_after` (so a colour's disjoint regions aren't joined by junk
travel — each trim is a Wilcom Break-Apart boundary). The pre-pass is best-effort: anything
that errors falls back to plain fills so the step always yields a valid design.

### The mode flags (config.py / cli.py)

These change step 2/3/5 behaviour and are central to output quality:

- **`--lettering`** — block/typeset glyphs: dissect each glyph into stroke-columns and satin
  *all* of them (not just single-column shapes), raise the satin-width ceiling, snap inks to
  pure colour. **Shatters cursive/script** — don't use it there.
- **`--purify-colors`** — colour snap only (no satin dissection): near-pure primaries → pure,
  custom/muted brand colours kept verbatim. Use for *mixed* designs (display caps + cursive)
  that `--lettering` would shatter. Implied by `--lettering` (see `PipelineConfig.purify`).
- **`--fill-method`** — `auto_fill` (default) routes one continuous path but its travel
  routing can time out on long thin sprawling shapes (e.g. calligraphy); use `contour_fill`
  there.
- **`--open-counters`** — drop ink-*enclosed* page-coloured regions (the hole in e/B/g) to
  background so they read through. Auto-on for letter modes (`should_open_counters`).
- **`--pull-comp-mm` / `--fabric` / `--no-fill-underlay`** — control the fixed widening band.
  `--fabric` (cotton/denim 0.20, silk 0.30, tee/knit 0.35, fleece/terry 0.40 mm — Wilcom manual
  table, see `wilcom-manual-rules.md`) sets the pull-comp default; `--pull-comp-mm` overrides it
  (lower it, e.g. 0.05, so FINE decoration like thin Arabic tashkeel doesn't read heavier than the
  source); `--no-fill-underlay` drops the underlay pass. Resolved via `cfg.resolved_pull_comp_mm`.
- **`--colors`** — thread-colour count. When omitted it defaults to the **category prior**
  (`CATEGORY_COLORS`: arabic/decoration/simple-shapes 1, letters 2, numbers 4, 3D 8, anime 12) if
  `--category` is set, else 8. Pass an explicit value for a colourful design in a monochrome-median
  category. Resolved via `cfg.resolved_num_colors`.
- **`--satin-underlay` / `--thin-line-run`** (both default **on**) — satin-quality knobs:
  underlay every satin column (center-walk + contour); route sub-1.6 mm linework to a
  running/bean stitch rather than a too-narrow satin. **`--branch-satin`** (default off)
  extends satin to *forked* strokes (per-branch dissection; guarded so a dense mesh stays a
  fill and it can leave small junction gaps — hence opt-in).
- **`--snap-black`** (default on) — dedicate one thread to pure black for a logo keyline /
  pupils on MUTED art, without `--purify-colors`' neon side effect; no-op if there's no real
  black.
- **`--auto-route`** (default off) — per-colour Ink-Stitch `auto_satin`/`auto_run` threading a
  colour's pieces into one ordered path (cuts trims/travel on satin-heavy designs; can *add*
  travel on spatially-scattered pieces like Arabic dots).
- **`--gradient`** (default off, experimental) — de-posterize smooth shading: merge
  same-hue/different-lightness adjacent palette colours into one density-modulated gradient
  region instead of hard flat bands.
- **`--realistic-preview`** (default on) — render the step-6 preview with Ink-Stitch's
  realistic thread renderer (falls back to the fast polyline draw on error).

### Step 7 is a real gate

`verify.py` renders the stitched pattern and produces `ctx.verification = {passed, checks,
metrics}`. A **fail** is the signal to re-run Phase A with adjusted flags — not a crash.

## Domain knowledge (read before working on a category)

The pipeline encodes recipes measured from the user's ground-truth `.VP3` files. Per-photo
decisions (category, region→object mapping, colours, size, sew order, which flags) are
documented — **consult these rather than re-deriving**:

- **`EMBROIDERY-PLAYBOOK.md`** — the router: how to pick category + technique for any photo.
- Category detail: `letters/`, `arabic/`, `3D/`, `anime/`, `simple-shapes/`
  (`*-embroidery-knowledge.md`). `letters/letters-embroidery-knowledge.md` also documents the
  measured `.vp3` binary format + thread-metadata, which is cross-cutting.

## Standing conventions

- **Before finishing, compare the output against the original photo and iterate on drift** —
  enlarge/inspect rather than assuming the run was faithful.
- Artifacts land in `output/` (gitignored); input photos in `samples/` (gitignored). The
  category dirs (`letters/`, `anime/`, etc.) hold knowledge docs + that category's reference
  VP3s, not pipeline code.
