# Wilcom Reference Manual — the digitizing decision rules (distilled)

**Source:** *Wilcom EmbroideryStudio Reference Manual* (1549 pp.), plus the Beading /
Bling / Chenille / Sequin / Schiffli supplements. The raw PDFs live in `wilcom-manual/`
(gitignored, ~300 MB). This file is the **distilled, citable extract of every rule that
changes what stitch we choose or what parameters we emit** — the official-manual companion
to [`EMBROIDERY-PLAYBOOK.md`](EMBROIDERY-PLAYBOOK.md) (which is measured from ground-truth
`.vp3`s). Page numbers are the **PDF page** of `ReferenceManual.pdf`.

> **Why this matters.** The playbook told us *what* the ground-truth files do; the manual
> tells us *why* and gives the **hard numbers and the decision policy** Wilcom itself uses.
> Where the two agree we have high confidence; where the manual gives a number we were
> guessing, adopt the manual's.

---

## 0. The headline: Wilcom's own auto-digitizer uses our exact model

Chapter 41 ("Automatic Digitizing") describes the **individual auto-digitize tools** — and
they map **one-to-one** onto our per-region tiering (validation, not coincidence):

| Wilcom auto tool (p1057–58) | Applies to | Our tier |
|---|---|---|
| **Centerline Run Object** | "centerlines in **narrow shapes**" | `run` (centerline) |
| **Turning Satin Object** | "fill **narrow column** shapes with turning stitch angles" | `satin` (single/turning column) |
| **Tatami Fill Object** (with/without Holes) | "fill **large areas** with tatami" | `tatami` fill |
| **Outline Run Object** | "outlines of run stitching" | keyline `run` |

And Smart Design's color-level policy (p1052–54) is **exactly our colour routing**:
- "classify image colors as **fills or details** … the image **background is omitted**."
- Sew order: **"Fills should be stitched first, details last."** ← our background-first / foreground-last.
- Details are handled as **Satin, Column C, or Double Run** (p1054) — i.e. thin detail = satin or run.

**Takeaway:** our architecture (region → {run, satin, tatami} by geometry, fills-first) is
the same decision structure Wilcom ships. The gaps are in the *thresholds and parameters*,
which the manual now pins down.

---

## 1. The width → stitch-type decision (with REAL numbers)

The manual never states a single "> X mm ⇒ tatami" constant, because the boundary is set by
**satin stitch length = column width vs. the machine's max stitch length**, not an arbitrary
size. The governing facts:

- **Satin is for narrow columns** where "**each stitch spans the width of the column**"
  (p221). "If a Satin shape is **too wide**, stitches may be **loose or fail to cover** the
  fabric properly. Conversely, in **narrow** columns, stitch density may be **too great** and
  needle penetrations damage the fabric." (p222) → hence *auto-spacing*, below.
- **Max satin stitch length ≈ 7 mm.** Auto Split breaks satin stitches longer than a set max;
  the manual's guidance: **"Use a length of 7.00 mm to preserve the satin effect."** (p452).
  Since a satin stitch spans the column, **~7 mm is the practical satin-width ceiling** before
  the stitch is either split or the object should become a fill.
- **Raised satin ≤ 7 mm wide** — "best applied to objects **7 mm wide or less**. This is a
  safe average for most machines." (p231).
- **Above the ceiling you have two choices, and tatami is only one of them (p454):**
  - **Auto Split satin** — "used primarily to prevent long stitches in **wide columns**. It
    can also be used as an **alternative to tatami**. Auto Split looks **more satin-like** and
    works well with turning stitches … By contrast, **tatami is flat** and can show unwanted
    patterns with tight curves."
  - **Tatami fill** — "suitable for filling **large shapes**" (p229).
- **The scaling rule makes the ceiling explicit (p1050):** "when scaling designs, a Column
  A/B [satin] shape may become **too big for Turning Satin**. By converting to Complex
  Fill/Turning, you can apply … **Tatami**." → there IS a width above which satin is dropped
  for fill; Wilcom converts the *object type* rather than forcing a bad satin.

### The resulting decision table (mm are region **narrow-dimension / column width**)

| Column width | Wilcom object | Our tier | Note |
|---|---|---|---|
| **< ~1.5–2 mm** | Centerline Run / Center-Run-underlaid column | **run** (bean/triple for emphasis) | below this, satin density damages fabric (p222) |
| **~2 – 7 mm** | Turning Satin (auto-spacing) | **satin** | the sweet spot; each stitch spans the column |
| **~7 – ~12 mm** | Satin **with Auto Split**, *or* Tatami | **satin (split)** *or* **tatami** | satin-look preserved via split; flat fill via tatami |
| **> ~12 mm / large irregular / branchy** | Tatami Fill | **tatami** | "large shapes" |

> Our current constants (`_RUN_MAX_WIDTH_MM = 1.6`, `_SATIN_MAX_WIDTH_MM = 3.0`) put the
> run/satin boundary about right but the **satin ceiling far too low (3 mm vs the manual's
> ~7 mm)**. See §6 for why we can't just bump it — and what actually closes the gap.

---

## 2. Density / spacing defaults (adopt these)

| Stitch | Manual default / range | Page | Our value |
|---|---|---|---|
| **Normal satin & tatami spacing (typical band)** | **0.3 – 0.6 mm** | p1198 (p1200 PDF) | ~0.4 mm ✓ **validated** |
| **Tatami row spacing (recognized range)** | **0.4 – 1.5 mm** (0.4 dense → 1.5 open) | p1195/1197 | 0.4 mm ✓ |
| **Tatami stitch length** | 1 – 4.5 mm (example set), min-stitch 0.4–1.2 mm | p231 | — |
| **Satin density** | % of preset; **75 % "generally produces high quality"** (lower % = denser) | p223 | — |
| **Satin auto-spacing** | recalculates spacing **wherever column width changes** | p221–25 | (we use fixed) |
| **Run stitch length** | **1.8 mm** for sharp curves → **4.0 mm** to mimic hand look; chord gap 0.07 mm | p219–20 | — |
| **Triple/Bean run** | repeats each stitch **3×** | p220 | ✓ |
| **Auto Split min stitch** | **0.4 mm** | p452 | — |
| **Satin stitch count** | keep ≤ **10** (higher risks thread breaks) | p227 | — |

Satin auto-spacing offsets by thread weight (p226): 40-wt `+0.01`, 30-wt `+0.03`, 80-wt
`−0.03`, 100-wt `−0.06` — i.e. **finer thread ⇒ closer spacing**.

---

## 3. Underlay decision table (by width & fabric)

The **digitizing-presets** table (p161 PDF) is the default cover+underlay per object type:

| Traditional tool | Cover | Underlay 1 | Underlay 2 |
|---|---|---|---|
| **Column A/B/C** (satin) | Satin | **Edge Run** | **Zigzag** |
| **Complex / Turning fill** | Tatami | **Edge Run** | **Tatami** |

The **rule-of-thumb by object size** (p412 PDF):

| Underlay | Use for | Page |
|---|---|---|
| **Center Run** | stabilize **narrow columns — e.g. 2–3 mm wide** | p412/414 |
| **Edge Run** | "somewhat larger shapes such as **letters**" | p412 |
| **Zigzag / Double Zigzag** | support **wide columns**; "best used under **Satin** cover" | p412/417 |
| **Tatami underlay** | stabilize **large filled shapes** (open tatami) | p412 |

- Underlay default **spacing is much wider** than cover (examples 1.5 mm / 3.0 mm) (p410).
- Zigzag underlay spacing 3–4 mm, angle 45°; tatami underlay 2–3 mm, **angle counter to cover**
  (45°/135°) (p416–18).
- **"By shape" underlay** (whole object, not per-segment) is default for lettering and **cuts
  bunching, travel runs, and stitch count** (p413) — worth mirroring for our satin columns.
- Fabric-model split (p288–90): Wilcom keeps **separate defaults for Narrow Satin vs Wide
  Satin** ("narrow objects will require a different underlay type") — confirms underlay must
  scale with width, not be one fixed band.

---

## 4. Pull compensation by fabric (adopt this table)

Overstitch allowance in mm (p429 PDF):

| Fabric | Pull comp (mm) |
|---|---|
| drills, cotton | **0.20** |
| T-shirt | **0.35** |
| fleece / jumper | **0.40** |
| lettering | **0.2 – 0.3** |

Also: **Denim = Low, Silk = Medium, Terry Toweling = High** pull-comp tier (p287). Fine
decoration (thin tashkeel) → the low end. This directly calibrates our `--pull-comp-mm`
(default should be ~0.2–0.4 by fabric, not a single fixed band).

---

## 5. Colour reduction — how many threads (per photo type)

From Color PhotoStitch guidance (p1091 PDF) — directly usable as our `--colors` prior:

| Source | Colours | 
|---|---|
| grayscale photo | **5 – 6** shades |
| simple colour photo | **7 – 10** |
| complicated photo | **14 – 16** (cap **≤ 20** — "every thread change counts") |

- **A colour occupying > 5 % of total area is auto-included**; below that it's droppable
  noise (p1082/1091) — matches our speck-consolidation + area gate.
- Color PhotoStitch colour blocks are **run stitching**; defaults **length 3 mm, spacing
  0.4 mm, trim-if-next ≥ 2 mm** (p1084–86). "Fewest colours/threads for fewest stitches and
  trims for a good result."
- **Prepare Bitmap Colors** (p1042–44): "flattens colors, sharpens outlines, reduces noise;
  areas **enclosed by a black outline** are reduced to a single color … These areas become
  the embroidery objects." ← exactly our step-2 consolidate + step-4 enclosure segmentation,
  and the rationale for `--snap-black` (the black keyline defines objects).

---

## 6. The satin gap — the manual explains it, and confirms the fix

Two manual facts reframe our measured "ground truth is ~100 % satin but we emit fills" gap:

1. **Why wide satin works in Wilcom and not for us:** Wilcom satin uses **Auto Spacing that
   recalculates density wherever the column width changes** (p221–25), *plus* Auto Split to
   keep stitches ≤ ~7 mm. Our satin is **fixed-width, fixed-spacing**, so forcing it onto wide
   strokes under-covers — which is exactly the coverage crash we measured (99.9 % → 81.6 %).
   → **The fix is variable-width / variable-density satin, NOT bumping `_SATIN_MAX_WIDTH_MM`.**
   The manual independently confirms the [[vwidth-satin]] direction is the right one.

2. **Part of the "gap" is a measurement artifact.** The machine-file reader note (p1197 PDF):
   *"Recognize auto splits in Satin objects. **Otherwise, patterns created with Auto Split will
   be recognized as Tatami.**"* Our fingerprint uses the same stitch-level turn-angle heuristic
   with no Auto-Split awareness, so **ground-truth wide Auto-Split satin is being counted as
   fill by our own metric.** Some of the satin_frac gap is us mis-reading the truth, not the
   pipeline mis-stitching. → add an Auto-Split detector to `fingerprint.py` before trusting the
   satin_frac delta as pure pipeline error. Ties to [[vp3-fingerprint-and-satin-gap]].

---

## 7. Quality knobs worth wiring (sharp corners, small stitches)

- **Auto Split vs Auto Jump** (p451–54): Auto Split re-breaks long satin **and randomizes the
  penetration line** (avoids the split line down the middle); Auto Jump *preserves* long
  stitches as jumps (only when a *few* are too long). Max stitch = format frame-movement limit.
- **Fractional spacing** for satin on curves (p446–47): offset fraction **0.00 = outside edge,
  1.00 = inside**; **0.33 reduces inside-edge bunching**, 0.66 eliminates it but risks
  under-cover. Combine with **stitch shortening** (shorten inside-curve stitches to 50–80 %,
  ≤ 5 consecutive) — the correct answer to satin-on-tight-curves instead of dropping to fill.
- **Smart corners** (p439–45): Mitre for corners **20–45°**, Cap for **very sharp** (cap-below
  20° default), Lap-below **110°** default. Relevant to lettering/serifs.
- **Remove small stitches** (p438): a min-stitch-length filter for scaled designs — matches our
  post-scale cleanup need.

---

## 8. Concrete pipeline changes this unlocks

**Adopt now (low-risk, calibration):**
1. ✅ **DONE — Pull-comp by fabric** (`--fabric`, `config.FABRIC_PULL_COMP`): 0.20 cotton/denim/
   drill · 0.30 silk · 0.35 tee/knit/jersey · 0.40 fleece/jumper/terry. Explicit `--pull-comp-mm`
   still overrides; `resolved_pull_comp_mm` picks. Default (no fabric) stays 0.2.
2. ✅ **DONE — Colour-count priors by category** (`config.CATEGORY_COLORS`, `resolved_num_colors`):
   arabic/decoration/simple-shapes 1 · letters 2 · numbers 4 · 3D 8 · anime 12 (manual mid photo
   band). Used when `--colors` is omitted; explicit `--colors` wins (the monochrome-median
   washout trap cuts both ways). The **≥ 5 % area** inclusion is approximated by step-2 speck
   consolidation (majority filter) rather than a hard gate — left as-is.
3. **Density stays 0.4 mm** — now *validated* against the manual's 0.3–0.6 mm band; keep it.
4. **Underlay by width** (§3): Center Run for 2–3 mm satin, Zigzag for wide satin, Edge Run for
   letters, Tatami underlay for large fills. *Deferred*: our satins are all narrow (center-walk =
   Center Run is already correct); the Zigzag-for-wide-satin branch only bites once we emit wide
   satin, and the satins are produced by an external `stroke_to_satin` call so per-satin width
   isn't available at param time — do it together with (6).
5. ✅ **DONE — Variable run length** (`stitches._run_params`): nominal `running_stitch_length_mm`
   raised 2.0 → **4.0 mm** (manual's straight-run max) with `running_stitch_tolerance_mm = 0.2`
   (the manual's chord gap) so Ink-Stitch auto-shortens stitches toward ~1.8 mm on tight curves.
   Fewer penetrations on straights, tight on curves; the bean/triple pass keeps the line solid.

**Variable-width satin — the satin-gap fix, now working:**
6. ✅ **`--vwidth-satin` validated + wired into `--satin-lean`.** Building satin rails at the
   LOCAL medial-axis half-width (not one average) closes the gap the fixed-width ceiling couldn't:
   on the Ramadan calligraphy, satin_frac 0→100 (matches truth) **with** coverage 97.9→99.3 %,
   shape-IoU 67→81 %, over-ink 1.43×→1.22× — strictly better than the fixed-width satin AND the
   fill it replaces. `--satin-lean` now IMPLIES `--vwidth-satin`, so leaning a satin-dominant
   category to satin no longer regresses coverage. **Still open:** the effective ~7 mm ceiling
   raise for genuinely wide columns + the underlay-by-width branch (4) — bring those in next.

**Fingerprint fix (§6):**
7. ✅ **DONE — Auto-Split satin detection** (`fingerprint._is_split_satin`): a narrow oscillating
   ribbon (many reversals, rail-to-rail crossing ≤ 8 mm) reads as satin regardless of splits.
   Re-measured delta: numbers 71→84 % satin (+13, recovered from "mixed"); 3D unchanged (genuine
   tatami); satin-dominant categories already 100 % (narrow unsplit satin — no artifact there,
   their gap is genuinely pipeline-output-side).

---

*Kept intentionally to the rules that change an output. The supplements (Chenille, Sequin,
Bead, Bling, Schiffli) cover specialty decoration techniques out of scope for photo→vp3 and are
left in `wilcom-manual/` for reference.*
