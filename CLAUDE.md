# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A headless Python pipeline (Linux, Python 3.12) that turns a photo into a **production-ready
`.vp3`** + worksheet + preview for Wilcom EmbroideryStudio. The **`.vp3` is the deliverable** — a
complete, machine-stitchable embroidery file with named cones in sew order.

If a caller needs Wilcom's *editable native* `.emb`, that's a one-off **manual** step in a licensed
EmbroideryStudio (open the VP3 → File ▸ Save As): the `.emb` `DesignDocument` stream is
proprietary-encrypted and can't be written by any script, so it's a Wilcom-only save — **not**
something this pipeline does or depends on. (An earlier untested AHK "Phase B" automation for that
manual save was dropped; recover from git history if ever needed.)

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
  and reads the VP3 back out of the returned zip into `ctx.stitch_pattern`. If the whole-
  design pass exceeds 120 s (Ink-Stitch's auto_fill router can infinite-loop on a combined
  design whose every colour digitizes fine alone), it falls back to **digitizing each colour
  group separately and merging**: each mini-SVG carries a shared *frame anchor* (Ink-Stitch
  centres every VP3 on its own stitch bbox, so without it the merged groups misalign), and a
  group that hangs even alone degrades stepwise — pull-comp 0 (the measured hang trigger) →
  + underlay off → fills/satins split — before the contour_fill last resort, so large
  regions stay TATAMI. The kept `*_grpN.svg` files also feed step 6's realistic-preview
  composite (`ctx.per_group_svgs`).
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

**Cross-stitch categories bypass all of the above.** A `config.CROSS_STITCH_CATEGORIES` category
(currently **falahi** — Palestinian tatreez) is *counted cross-stitch*, a distinct primitive, not
run/satin/tatami. When `resolved_cross_stitch` is on (AUTO for those categories; force with
`--cross-stitch`/`--no-cross-stitch`), step 5 short-circuits into `steps/crossstitch.py`: a fixed
square grid (pitch = the pair prior ≈ 2.1 mm, or `--cross-stitch-pitch-mm`), each majority-covered
cell becomes an **X** (the per-corner reversals give the high-reversal character the fingerprint
reads as ~100 % satin, matching the ground truth). It's built **directly with pyembroidery** — no
Ink-Stitch (whose `manual_stitch` exact-node mode hangs the router), no trace SVG; cones are still
named in step 6 by RGB match. See `falahi/falahi-embroidery-knowledge.md`.

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
- **`--auto-repair`** (default on) — act on the analyzer's warnings the way a digitizer edits
  artwork before digitizing: sub-sewable specks (<1.5 mm²) merge into their surrounding colour
  (never into background; ≥3 same-colour specks = a dotted pattern, kept), isolated sub-0.8 mm
  hairlines thicken to ~1 mm into background only (a >30 %-hairline design gets the "enlarge"
  advice instead), and palette colours within ΔE<5 that matched the SAME thread cone merge
  before tracing. Every action logs as `auto-repaired: …`. Step 7 gained the matching
  **sewability gate**: local density *stacking* (thread-length map, calibrated on the production
  VP3s — they peak ≤5.2 satin-layers; warn >5 layers over >10 mm²), *penetration spacing*
  (<0.3 mm needle-cut risk, warn >5 %), and a *stitch budget* vs the category profile (warn
  >1.8× expected).
- **`--travel-plan`** (default on) — production near-continuous sewing: chains each colour's
  pieces nearest-neighbour (a fill's border satins stay bonded to it), pins fill entry/exit to
  the junction points via Ink-Stitch's `starting_point`/`ending_point` object commands (probed:
  they snap the commanded position to the target's **nearest boundary point**), and drops
  `trim_after` only where the straight travel is ≤ 12 mm **and** ≥ 90 % covered by later-sewn
  stitching or the colour's own regions — never where the thread would show (uncovered
  background crossings keep their Break-Apart trims). Measured: letters 123→59 trims (exactly
  cancelling underlap's fragmentation), joker 192→132 (121 of 217 junctions are genuinely
  exposed on this scattered design — the cover law keeps them).
- **`--underlap-mm`** (default 0.5, 0 disables) — production object-overlap at step 4: an
  earlier-sewn colour's traced region extends this far UNDER its later-sewn neighbours (re-traced
  from its dilated mask, expansion clipped to later-sewn pixels — never background or opened
  counters), so fabric pull can't open a white gap at the seam. Distinct from pull-comp: pull-comp
  widens *stitches* uniformly at digitize time; underlap moves *traced geometry*, only along seams
  (measured: cross-seam stitch overlap 1.1 → 1.6 mm on abutting rects).
- **`--pull-comp-mm` / `--fabric` / `--no-fill-underlay`** — control the fixed widening band.
  `--fabric` (cotton/denim 0.20, silk 0.30, tee/knit 0.35, fleece/terry 0.40 mm — Wilcom manual
  table, see `wilcom-manual-rules.md`) sets the pull-comp default; `--pull-comp-mm` overrides it
  (lower it, e.g. 0.05, so FINE decoration like thin Arabic tashkeel doesn't read heavier than the
  source); `--no-fill-underlay` drops the underlay pass. Resolved via `cfg.resolved_pull_comp_mm`.
- **`--colors`** — thread-colour count. When omitted it defaults to the **category prior**
  (`CATEGORY_COLORS`: arabic/decoration/simple-shapes 1, letters 2, numbers 4, 3D/anime 8) if
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
- **`--outline-objects`** (default **auto**: on for satin-dominant categories incl. anime, off
  otherwise) — layer a **closed satin border** over each substantial (≥40 mm²) fill region:
  centerline = EDT iso-contour at half the border width, so the satin's outer edge kisses the
  region boundary and its inner half overlaps the fill (the production "outline family" — the
  pink-goku pair is 217 outline vs 118 fill objects, where its 82.9 % satin lives). Border width
  = the category profile's median satin width (clamped 1.5–3 mm). Holes/counters are bordered
  too. Borders sew right after their fill, same colour.
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
- **Production pairs** — the user drops (CorelDRAW-SVG, production-VP3) pairs (matching stems)
  into **`pairs-inbox/`**; run `orchestrator/scripts/ingest_pairs.py` (see `pairs-inbox/README.md`).
  It auto-categorizes each pair, files it under **`<category>/pairs/<design>/`**, labels it
  (`extract_pair.py` structure + `register_pair.py` SVG↔VP3 registration → per-object mm widths,
  density, satin-vs-tatami), force-adds the VP3 (VP3s are gitignored; ground truth is tracked
  deliberately), and rebuilds `data/category_profiles.json` (step 7's drift gate) **and
  `data/pair_priors.json`** (`build_pair_priors.py`). The priors **steer step 5's numbers
  automatically** (`src/wilcom_pipeline/priors.py`): a category with ≥1 ingested pair uses its
  *measured* satin/fill width crossover as the satin ceiling (clamped 3–9 mm, logged as
  `pair prior: satin ceiling …`; anime's pair measures 2.86 → 3.0), its measured satin-width
  band as the vwidth clamps, and its satin-width median as the border width — categories
  without pairs keep the hand-calibrated constants byte-identically, and priors tune numbers
  only (structure rules like "large regions = tatami" stand). Method + findings:
  **`PAIRS-FINDINGS.md`**. Shared VP3 measurement scripts live in
  `orchestrator/scripts/` (one copy; the old per-category `tools/` were consolidated).

## Standing conventions

- **Before finishing, compare the output against the original photo and iterate on drift** —
  enlarge/inspect rather than assuming the run was faithful.
- Artifacts land in `output/` (gitignored); input photos in `samples/` (gitignored). The
  category dirs (`letters/`, `anime/`, etc.) hold knowledge docs + that category's reference
  VP3s, not pipeline code.
