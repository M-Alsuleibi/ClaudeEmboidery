# anime — production-ready digitizing, learned from a live Wilcom class

This folder distills the **Wilcom EmbroideryStudio** course *"CURSO WILCOM
OCTUBRE"* by **Arzefera (khael_artemb)** into reusable best practices, and proves
them out by generating a `.vp3` for the design the course digitizes: **Studio
Ghibli's Totoro** (*My Neighbor Totoro*).

> Playlist `PLXWJF8NA42UMoc5RkzDmnOaDqXNZ2_KdA` — 8 videos (#1–#8). Analyzed:
> **#3–#8** (full transcripts via `yt-dlp`); **#1–#2 are Private**; **#5**
> (lettering/fonts) was rate-limited but is covered through the lettering Q&As in
> #4 and #6. See the coverage table in `best-practices.md`.
>
> The lead video, #3 (`xsI7-k7Ji3U`, 2 h 11 m), has a practice tab reading
> **"PRACTICA GHIBLI PEDRO"** — rows of Totoro silhouettes traced with Column A /
> Column B satin tools. Hence `anime/`.

## What's here

| File | What it is |
|---|---|
| `best-practices.md` | The **full course's** digitizing rules (videos #3–#8), each mapped to our Phase A pipeline or flagged manual/Phase-B. **The skill candidate.** |
| `process.md` | The end-to-end "photo → production-ready design" workflow, step by step. |
| `rei-digitizing-plan.md` | **Hand-digitizing worksheet for Rei** (video #179) — object-by-object plan to make a *production-ready* Rei in Wilcom, grounded in timestamped frame settings + the #3–#8 methodology (the video has no narration to transcribe). |
| `assets/make_totoro.py` | Redraws Totoro as a clean, flat-colour, embroidery-friendly source PNG. |
| `assets/totoro.png` | The generated source logo (900×1000, transparent bg). |
| `output/totoro_pro.vp3` | **Deliverable** — the stitch file (90 mm wide, 4-colour request). |
| `output/totoro_pro_preview.png` | Stitch preview (self-verify gate + human check). |
| `output/totoro_pro_threadlist.txt` | Thread list + sew order for the operator. |
| `assets/rei_ayanami.png` | Source for the 2nd deliverable: a **frame from video #179** (Rei Ayanami / Evangelion), cropped + smoothed so the pipeline can trace it. |
| `output/rei_ayanami_pro.vp3` | **Deliverable** — the stitch file (85 mm wide, 8-colour). |
| `output/rei_ayanami_pro_preview.png` / `_threadlist.txt` | Preview + thread list. |
| `assets/make_kitsune.py` / `kitsune.png` | Original kawaii **fox mascot** — the clean, flat, bold design authored for the 2nd-playlist deliverable. |
| `output/kitsune_pro.vp3` | **Deliverable** — production-ready stitch file (90 mm wide, 4-colour); gate PASS, 6.9k st, 0.23 % trims. |
| `output/kitsune_pro_preview.png` / `_threadlist.txt` / `kitsune_pro.svg` | Preview + thread list + editable layered SVG. |
| `assets/killua.png` | Source for a head-portrait deliverable: a frame from `killya.mp4`, with the purple gradient background keyed out (hue+saturation) and the thin line-art rebuilt bold so it survives the 1.2 mm min width. |
| `output/killua_pro.vp3` | **Deliverable** — stitch file (105 mm wide, 7-colour); gate PASS, 21.9k st, 0.27 % trims, 6 satin columns. |
| `output/killua_pro_preview.png` / `_threadlist.txt` / `killua_pro.svg` | Preview + thread list + editable layered SVG. |

## Reproduce

```bash
# 1) Totoro (clean original art → crisp, near-flat source)
.venv/bin/python anime/assets/make_totoro.py          # -> assets/totoro.png
.venv/bin/wilcom-pipeline anime/assets/totoro.png \
    --width-mm 90 --colors 4 --thread-chart madeira-polyneon \
    --name totoro --output-dir anime/output

# 2) Rei Ayanami (a frame from video #179, cropped + median-smoothed)
.venv/bin/wilcom-pipeline anime/assets/rei_ayanami.png \
    --width-mm 85 --colors 8 --thread-chart madeira-polyneon \
    --name rei_ayanami --output-dir anime/output

# 3) Kitsune fox mascot (2nd-playlist deliverable — clean original flat art)
.venv/bin/python anime/assets/make_kitsune.py        # -> assets/kitsune.png
.venv/bin/wilcom-pipeline anime/assets/kitsune.png \
    --width-mm 90 --colors 5 --thread-chart madeira-polyneon \
    --name kitsune --output-dir anime/output

# 4) Head portrait from killya.mp4 (frame → bg-key → bold-outline prep → digitize)
.venv/bin/wilcom-pipeline anime/assets/killua.png \
    --width-mm 105 --colors 7 --thread-chart madeira-polyneon \
    --name killua --output-dir anime/output
```

Both runs pass the step-7 quality gate (nonzero stitches, every colour sewed,
consistent colour changes, density in band, fragmentation < 5 %).

> **Rei is a hard input on purpose** — a detailed anime portrait taken from a
> *stitch render*, not clean flat art. It exercises section **O** of
> `best-practices.md`: the pipeline produces flat tatami fills + outline satins
> and **simplifies** the portrait (it can't do the instructor's manual satin
> shading or hair relief). Two early failures, both instructive:
> 1. **Ink-Stitch 300 s timeout** at 10 colours → 705 traced paths (stitch
>    texture + canvas grid fragmented into hundreds of regions). Fixed by
>    median-smoothing the source and dropping to 8 colours (238 paths).
> 2. At very few colours the **skin tone merges to grey**; 8 colours restores it.

## How the design maps to the lesson

The class is *entirely* about **when to use a satin column vs a fill**, and how
to sequence and connect objects so the design is clean and machine-friendly.
Totoro is the perfect exercise for it, and the pipeline encodes the same calls:

| Totoro part | Stitch type | Lesson it demonstrates |
|---|---|---|
| Body + belly outline (≈2.4 mm dark border) | **satin column** | Column A / Column B around a shape |
| Gray body, cream belly | **tatami fill** + underlay | complex/tatami fill; fill underlay ("borde") |
| Eyes / nose / chevrons / whiskers | small fills / short satins | minimum column width; run vs satin for thin marks |
| Sew order (body → belly → face → outline) | back-to-front | "what goes behind, what goes in front" |

## One real bug this exercise caught

Two, actually — both documented in `best-practices.md`:

1. **Minimum column width** (the class's *ANCHO MÍNIMO COLUMNA*): the first draft
   drew the outline at 0.7 mm — below the pipeline's 1.2 mm consolidation floor —
   so the linework was *erased* before stitching. Widening to ≈2.4 mm fixed it.
   This is the lesson, learned the hard way.
2. **Upside-down previews**: `emit.py` flipped the preview Y (`maxy - y`) and
   double-flipped every design upside-down. The `.vp3` itself was always upright
   (Ink-Stitch is correct); only the preview was wrong. Fixed in `emit.py`.
