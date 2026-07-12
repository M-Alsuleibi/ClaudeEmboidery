# Production-ready digitizing — best practices (full course)

> **⚑ Measured ground truth (first real anime pair, `pink-goku`, 2026-07 — see
> [`../PAIRS-FINDINGS.md`](../PAIRS-FINDINGS.md)):**
> anime is **SATIN-DOMINANT, not fill/photo-heavy** — `satin 82.9% / fill 4.7%`, **narrow satin
> columns ~2.25 mm**, **outline-heavy** (217 outline objects : 118 fill = 1.84 : 1), **7 colours**,
> 120 mm. This confirms the tutorials below (REI = *"sombras con SATIN, refuerzo TATAMI"*). It
> **overturns the pipeline's current anime defaults** (`--colors 12`, not satin-dominant): anime
> should lean satin (variable-width), use ~7–8 colours, and dedicate satin/run objects to the
> character linework. Flagged n=1 — confirm with ~2 more anime pairs before changing defaults.

Distilled from **Arzefera's "CURSO WILCOM OCTUBRE"** playlist
(`PLXWJF8NA42UMoc5RkzDmnOaDqXNZ2_KdA`). Coverage:

| # | Video | Topics | Transcript |
|---|---|---|---|
| 1 | `gGIgefJXuho` | (intro) | **Private — not accessible** |
| 2 | `IFDRHQd2yoc` | (basics) | **Private — not accessible** |
| 3 | `xsI7-k7Ji3U` | Column A/B/C, points/stars, **Totoro** practice | ✅ full |
| 4 | `EmclG8ifaBQ` | Tatami gradient, trapunto, Florentine, faux chenille | ✅ full |
| 5 | `OL7HQrm2-Eo` | Letter deformation, downloading fonts | ⚠️ rate-limited; covered via the lettering Q&As in #4 & #6 |
| 6 | `C6jA0Eg9nBM` | Hoops, design center, motifs, **3D foam/puff** | ✅ full |
| 7 | `hbLmgIbVQw0` | Badges/appliqué, offset borders, 3D buckling | ✅ full |
| 8 | `E-4YTeyrEXQ` | Vectors, dissection, drawing fundamentals | ✅ full |

**Second playlist — "Aprendiendo Wilcom · Alumnos Febrero" (Clases 1–4)**
`PLXWJF8NA42UOyWd0XEmYRz4R3r-Shreq3`: Class 1 `iA6Mfw52Ens`, Class 2
`WouGKHXSKME`, Class 3 `I2npo4Zszs0`, Class 4 `IVCTCWf_kck`. **Access validated**
(enumerated, metadata + descriptions read, captions exist, frames extracted).
These are the same instructor's **beginner** classes and re-teach material already
captured above — layers, **running/double-run (`Shift+X`)**, **Column A/B**,
jumps/cuts, drawing notion. Concrete settings read off frames: running length
**3.50 mm / min 1.20 mm / spacing 0.05**; accordion/gradient **Máx 2.22 / Mín
0.55 mm**; Column-C borders for emblems. No new technique beyond #3–#8, so nothing
is duplicated here — the rules above already cover them. (Captions were
CDN-throttled (HTTP 429); content confirmed via the property panels in frames.)

**Bonus — end-to-end character digitize** (same channel, standalone #179):
`3AY51pJYbwY` — *"REI AYANAMI ✔️ SOMBRAS CON SATIN ✔️ REFUERZO TATAMI ✔️ RELIEVE
CABELLO"* (~50 min). A full portrait digitize of **Rei Ayanami** (Evangelion).
**This video has no usable narration.** It has no caption track (`yt-dlp
--list-subs` → "no automatic captions, no subtitles"), and a full Whisper
transcription (faster-whisper, small model) of the extracted audio returned only
hallucinated filler over background **music** — i.e. it's a "digitize-with-music,
minimal-talking" video, which is why there's nothing to caption. So section **O**
and the Rei plan (`rei-digitizing-plan.md`) are grounded in **(a) the exact
on-screen Wilcom settings read off timestamped frames**, and **(b) this same
instructor's verified methodology from the live-class transcripts (#3–#8)** —
*not* on this video's audio.

Each item notes the **video(s)** it came from and whether our Phase A pipeline
**encodes** it or it's **manual Wilcom / Phase-B** craft (knowledge for the human
or the AHK step, not automated here).

---

## The three pillars (the instructor's whole philosophy)

Repeated in every class: a production-ready design is

1. **Right object per region** — satin column vs tatami fill vs run, chosen by the
   region's shape and width, never "complex fill for everything."
2. **Sequenced back-to-front** — backgrounds first, top detail last; plan where
   each object starts and ends.
3. **Connected** — minimise trims and jumps; *"the sequence is the most beautiful
   thing… when they pass you the `.emb` it's a disaster"* if it's not thought out.
   A design embroidered many times makes **every second of trims multiply**.

> "The basics are everything: double-running stitch, Column A/B, open satin,
> tatami, connect the pieces, manage the layers, think the sequence. You don't
> need all the fancy tools." (#7)

---

## A. Object types — when to use which

### A1. Satin columns: Column A vs B vs C  (#3)
A satin column stitches back-and-forth; two side rails + angle rungs.
- **Column A** — place nodes in **pairs**, alternating base↔top; per-segment choice
  of straight vs curved. Most angle control; favoured for 3D/quality. Decide start
  & end first (start one end → must finish the other).
- **Column B** — trace one whole side, then the other; rungs auto-generated; 2
  nodes can suffice. Faster, less fiddly.
- **Column C** — width/entry-exit variant; used heavily for **borders** (set width
  e.g. 3.0–3.5 mm). Fix a bad rung with **Ctrl+H / `H`**.
- **Pipeline:** step 5 makes real satins from a region's clean single centerline
  (`fill_to_stroke`→`stroke_to_satin`). A/B/C aren't exposed; the satin generator
  picks rungs.

### A2. Tatami / complex fill  (#3,#4)
Broad areas; stable, no over-long stitches. Don't satin a branching shape.
- **Pipeline:** colours with median width ≥ 3 mm stay tatami fills; a block that
  would branch is kept as **one continuous fill**, never shattered.

### A3. Run / double-run  (#7,#8)
Thin lines, stems, outlines you travel out-and-back. **Trees are the ideal
double-run practice** (out and back along the same path). Triple-run for slightly
thicker. **Pipeline:** sub-minimum strokes should be run, not satin (see B1).

### A4. Manual stitch  (#4)
Full manual control of individual **straight** stitches (no curves). For grass
blades, fur, hand-drawn effects. *Manual Wilcom.*

### A5. Motifs / pattern fills  (#6)
A repeating drawn unit (leaf, rope, flower, chain, fire). See section G4.

---

## B. Minimum width & small features

### B1. Minimum column width — *ANCHO MÍNIMO DE COLUMNA*  (#3) ⭐
A satin has a minimum workable width; thinner and the needle penetrations collide
and it reads as a lump. Below it, use **run/triple-run** or widen the shape.
- **Pipeline:** the step-2 consolidation filter is **1.2 mm**; anything thinner is
  voted away before stitching. **Keep intended satin linework ≥ ~1.6 mm in the
  final size.** (Totoro's outline at 0.7 mm vanished; at 2.4 mm it satins cleanly.)
  Step 1 warns when the smallest feature is below ~1.2 mm.

### B2. Remove tiny stitches  (#6,#7)
Patterns/buckling/cuts create stitches too small to sew well. Set **minimum stitch
length 0.5 mm** in design settings (auto-removes them); save as a default. Refine
to ~0.7 mm on pattern fills. *Manual Wilcom / machine-format.*

---

## C. Underlay & reinforcement

### C1. Underlay exists to stabilise  (#3,#4)
Lay an edge/base under the top stitches so they don't sink or ripple
(*desplazamiento simple + borde*).
- **Pipeline:** every fill gets `fill_underlay=True`.

### C2. By shape vs by segment  (#6) ⭐
Zigzag/edge reinforcement **by shape** runs a single direction (can wrinkle, can
miss points). **By segment** gives each segment its own angle — fills better.
**Use by-segment for Column A/B.** Sometimes you must switch to by-segment just to
*see* the underlay. *Manual Wilcom.*

### C3. Reinforcement type per fill  (#4,#7)
- Large **tatami** → a **tatami underlay + an edge-run** (NOT zigzag — zigzag
  compresses toward points). Still compressing? add a 2nd tatami underlay, both
  spaced ~6 so they're apart.
- Letters → **centered run** underlay (not by-shape). 
- *Manual Wilcom.*

### C4. General reinforcement for big designs  (#7) ⭐
Put **one giant tatami underlay under the whole design**; the fabric is then
"planted"/firm and most pieces need no own reinforcement — only the large tatami
pieces do. For a shape too small for a full underlay, lay a **strip down the
middle** to anchor against shifting. *Manual Wilcom.*

### C5. Skeleton / anchor reinforcement for caps & 3D  (#6) ⭐
Before the design, run a **zigzag from center to the sides** to anchor the
fabric/cap to the hoop so pieces don't shift while you embroider one area.
*Manual Wilcom.*

### C6. Reinforcement & density by fabric  (#4)
Hard fabrics (denim/jean, caps) → low underlay + lower density (tatami ~7 + run),
**thick needle**. Piqué → lower padding, use **topping**, spacing ~0.60, **thin
needle** for delicate. Backing (pellón) tears easily one way, rigid the other —
orient so the design sits across the rigid direction. *Manual Wilcom / operator.*

---

## D. Compensation, overlap, holes

### D1. Pull compensation & overlap (*traslape*)  (#3,#4)
Thread pulls a column narrower and opens **gaps** at seams. Counter with **pull
compensation** (digitize wider than drawn) + **overlap** adjacent objects slightly.
Increase compensation on difficult/stretchy fabric (~0.30+).
- **Pipeline:** `pull_compensation_mm=0.2` on fills & satins; trace keeps adjacent
  colour regions edge-to-edge.

### D2. The overlap/layer rule — "crab method"  (#4) ⭐
The element **in front** is drawn **flush to its boundary**; the element **behind**
is drawn **over** (extended under the front one). Work top-layer-backwards: e.g.
tree (front, flush) → mountains (overlap under tree) → sky (overlap most) → border
last. *Manual Wilcom; the pipeline approximates via sew order (E1).* 

### D3. When to make holes in a fill  (#4)
- **Tatami on tatami** → make a hole (don't double-stitch underneath).
- **Satin, or tiny holes** → don't; holes *increase* stitches and distort the fill
  (extra runs in/out). Omit very small holes. *Manual Wilcom.*

---

## E. Sequence, layers, connecting

### E1. Back-to-front sew order  (#3,#4,#8)
Background/underneath first, top/detail last. With flat **black 2D** shapes the
boundary disappears — practice on coloured/shaded art first, then flat black.
- **Pipeline:** step 4 `_sew_order` orders colours by **enclosure depth**.

### E2. Connect objects; kill cuts & jumps  (#3,#7,#8)
Bring an object's start to the **closest point** of the previous one; aim to draw
the whole design **in one stroke** (cuts only at true start/finish). Connect
similar-size points (long-to-long); pull separated leaves closer so no center gap
shows. A design run **many times** → trims multiply; a **one-off** → cuts/jumps are
OK to save digitizing time.
- **Pipeline:** step 2 consolidates specks into few blocks; step 5 `trim_after`
  breaks only genuinely disjoint regions; step-7 gate fails if trims+jumps > 5 %.

### E3. Travel runs must not cross finished areas  (#4)
Run to the far end **first**, then fill back, so the return run travels under
not-yet-stitched regions. *Consequence of E1 + `trim_after`.*

### E4. Two workflows: order→chaos vs chaos→order  (#7) 
- **Order→chaos:** draw placement/run first, connect pieces with slides.
- **Chaos→order:** draw freely with cuts, then **re-layer** with the *traveling
  thread* — `T`+`Home`, then **Ctrl+X / Ctrl+V** on a piece removes it from its
  layer and re-inserts it in order, erasing the cut. Send objects to the **first
  layer** to make them sew first.
- Instructor uses chaos→order for complex pieces, order for simple. *Manual.*

### E5. Border last  (#4,#6)
Draw the border **last** so it covers the connecting threads between pieces.

---

## F. Tie-offs, trims, jumps (connectors)

### F1. Final tie-off on every object  (#3,#6)
Without a **final tie**, clipping a thread unravels the object. Auto ties use a
**length threshold ≈ 3–4 mm**: gaps below it stay connected (no tie/cut), above it
tie/cut. With **motifs** each repeat can add a tie (4 mm) → deactivate the
object's final tie to save many stitches (re-enable if that thread will be cut).
- **Pipeline / Phase B:** ties finalised in Wilcom on the `.vp3`; keep ~3 mm.

### F2. Trim vs jump  (#3,#6,#7)
Per gap the connector is a **Trim** (cut) or **Jump** (carry). Choose by the gap
length vs the threshold (≈8 mm: shorter→jump, longer→cut). Press **`T`** to reveal
cuts (circles) & jumps (triangles); raise the in-object connector value to turn
cuts into jumps. *Pipeline marks colour-boundaries as trims; final tuning Phase B.*

---

## G. Effects

### G1. Tatami gradient — accordion + trapunto (+ Florentine)  (#4,#8) ⭐
Density gradient = a base tatami + a duplicate (`Ctrl+C/V`) with the **accordion
spacing** tool, different colour. Two musts:
- **Remove reinforcement** on the gradient layer.
- **Trapunto** tool — moves the carry-thread to the **side** (not the middle) so it
  doesn't show through the open fill.
- Optional **Florentine** tool → curved flow lines (add curve nodes with `H`).
- **Angle:** offset the gradient ~**15°** from the base so they don't blend (same
  angle = a "water" effect — sometimes wanted). Values: min stitch ~0.66, max ~3.69
  (or experiment 0.40→0.60 spacing; extreme stitch 2→4).
- A **manual double-stroke gradient** (draw gradient as a reference, then trace
  over it) looks denser/nicer than a single-stroke. *Manual Wilcom.*

### G2. Faux/false chenille  (#4)
Random maze-like texture for trees/foliage. Draw the area (start=end same point),
apply the **dotted-stem** tool, set the maze value to min (1), tune spacing &
thickness (~1.5–2). *Manual Wilcom.*

### G3. Random stitch & jagged satin (grass/fur)  (#4)
- **Random stitch**: max **50–60 %** (100 % makes the stitch-length range too
  extreme). Good for fur.
- **Jagged/serrated satin** on Column A/B: "roughness" controls randomness (2 =
  very random, 10 = regular up/down); an **open** satin fill looks nicer.
- **Manual stitch** for full control of grass blades. *Manual Wilcom.*

### G4. Motifs — create & apply  (#6) ⭐
Draw a unit, duplicate+mirror, **Object → Create Motif** → group + subgroup name →
click **bottom point then top point** (defines start→end direction). Apply with:
- **Pattern/motif run**: draw a line, Enter → motif repeats along it (resize via
  the guide). Start & end at **extreme points** so repeats connect without jumps;
  else add a connecting run.
- **Motif column** (Column A/B): fills a column with the motif, auto-scaling
  smallest→largest (gradient-capable). Complex fill can't carry motifs.
- Values: size/spacing, plus **size-gradient** and **spacing-gradient**.
- Motifs are saved in a Wilcom documents folder (copy to move between PCs).
- *Manual Wilcom.*

### G5. 3D buckling pattern (motivo 3D circular)  (#7)
A pattern fill + the **buckling** tool bulges it on a **circle/wave/balloon**
(outward or inward toward the background); `H` shows the circle control. Clean
small stitches afterward (refine ~0.7 mm). *Manual Wilcom.*

---

## H. 3D foam / puff (*Fuami*)  (#6) ⭐

- **Density:** spacing **0.17–0.25, default 0.22** (lower to 0.18/0.13 if it opens).
- **End at points/extremes, never in the middle** — mandatory; otherwise the foam
  escapes. Two ways: (a) close each end in a tiny point; (b) **close by
  overlapping pieces** (the next piece covers the previous end) — preferred,
  cleaner. Draw end edges **slightly inside** the boundary so foam can't peek.
- **Remove the auto-division**; keep max division ~12–13, or angle it smaller.
- **Foam colour must match thread colour** (foam always peeks a little).
- **Curved letters (L, O):** disable shortening and **dissect into pieces** — 0.22
  + a curve piles stitches on the inner radius and the machine fails.
- Cap workflow: skeleton-anchor run (C5) → mark letter → place foam → mark → embroider.
- *Manual Wilcom / Phase B.*

---

## I. Lettering & fonts  (#4,#5,#6)

- **Pull/tire offset depends on font weight** — not fixed; add ~**+0.15 to +0.20**
  over how you want it to look. Thinner fonts need more.
- **Small letters deform** below ~1 cm; prefer **simpler fonts** at small size
  (fewer sub-objects). Recommended: **Folio**, "Teams", College (for outlined
  words). Wilcom fonts can error on some glyphs (a, e) at small size.
- **Reinforcement:** centered run (not by-shape; switch to by-segment to see it);
  spacing ~0.50–0.55; use **water-soluble topping** for letters.
- **Outline-a-word trick:** type word → `H` (set to *any shape*) → curved angle →
  Column C width 0.0 → delete the letter = a word outline.
- **Balance stitch distribution** so stitches don't pile at one corner; remove
  *shortening* + *fractional spacing* on thick satin letters.
- **Branching (auto-piece sequencing):** don't branch **> 4–5 pieces**; branch
  *connected* pieces, not separated ones; for letters branch piece-by-piece.
- **3D letters** must be manual (not auto-lettering) — see H.
- *Manual Wilcom / Phase B.*

---

## J. Badges, appliqué, symmetry  (#7) ⭐

- **Symmetric digitizing:** work from the **zero axis** (0 at top-center). Digitize
  **one half** only (offset tool from center). Duplicate → **remove the minus sign**
  on the X-coordinate (mirrors to the other side) → **Reflect Horizontally** →
  select both → **Weld** (right-click → Shape → Weld) into one object so Column C
  connects. If weld fails, **overlap** the halves more (top & bottom).
- **Double / layered borders:** duplicate a Column C and use **offset** — side 1 =
  inward, side 2 = outward; set **10 % / 90 %**, **never 0 % / 100 %** (0 opens and
  shows fabric). Border width ~3–3.5 mm.
- **Appliqué:** double-run **placement** line (colour 1) → place fabric → run →
  **cut** fabric → **Column C border** (colour 2) covers the cut edge; start/end at
  top center. Cut-outs need holes.
- *Manual Wilcom / Phase B; the pipeline's per-colour borders are the nearest
  automated analogue.*

---

## K. Hooping & the design center point  (#6) ⭐

- **Show/hide hoop:** `Shift+P`; right-click for hoop options. Configure "my
  frames" to keep only the hoops you use (12, 15, 18, 24…); create custom hoops
  (shape, size in mm, corner radius).
- **Save errors** ("some objects not covered by hoops" in DST/JEF) = design too big
  for the hoop → pick a bigger hoop or **auto-hoop** (wand).
- **Center point (the white X) must sit in the middle of the design** or the hoop
  can crash. **Design → Auto Start & End → apply** centers it. "Auto hold" makes
  the center follow the design when you move it.
- **Move center independently:** "digitize start & end point" → click to place it
  (fit a triangular/letter design in a small hoop; or align the center stitch with
  a garment's placket). Lock the **hoop** center the same way (right-click hoop).
- *Manual Wilcom / Phase B.*

---

## L. Vectors & drawing fundamentals  (#4,#8) ⭐

- **Vectors are guides, not stitches.** Use **"digitize in open mode" + Vector
  Fill** at width **0.1 mm**, a contrasting colour (light blue), to **dissect** the
  artwork into traceable pieces before digitizing — the digital "cut the bitmap
  into pieces."
- **Dissection (despiece):** you can't satin a 3-pronged shape — split it so each
  piece is one column/fill, sequenced front-to-back. Two valid dissections often
  exist; interpret the image.
- **Rectangle/ellipse vectors for perfect borders:** snap a small **circle vector**
  as a tangent at each corner, duplicate with constrain, then `H` → delete node →
  convert to curve = clean curved corners (the "anime" chest/cap border).
- **Drawing skill:** practice on shapes where the boundary is visible, then flat
  black; mentally digitize logos you see on the street; think 3D on 2D art.
- *Manual Wilcom; the pipeline's background-drop + colour-quantize automates the
  "cut into pieces" step (= old best-practices rule 12).*

---

## M. Machine format, resizing & format limits  (#6,#7)

- **Machine format** (Tajima/Happy/…) mainly sets max/min stitch length + jump.
- **Resize at digitize time** (density recomputes). Crucially:
  - **`.emb`/`.EMB`:** satin **auto-refills** when enlarged — the format's big
    advantage; you *can* scale up (e.g. 10→20 cm for a back), but **zoom in (set
    width ~300 mm) and review gaps/reinforcements**.
  - **DST/STP/other:** satin is already broken into running stitches → only resize
    **±10 %**, beyond that it falls apart.
- **Pipeline:** size is set once via `--width-mm` / `--height-mm` (physical mm on
  the SVG → density for the target size). Re-run for a new size; don't scale the
  `.vp3`.

---

## N. Visualization keys & habits  (#4,#6,#7)

The instructor's "X-ray vision":
- **`T`** — stitch penetrations, **cuts (circles)**, **jumps (triangles)**, the
  travel thread, and the underlay shape. Recolor the points for visibility. *Check
  `T` on every Column-C corner* (the corner fill piles stitches — turn it off,
  saves ~200 stitches & embroiders smoother).
- **`S`** — view vectors only (hide thread render). **`D`** — toggle the background
  image. **`K`** — lock image. **`Home`/`End`** — first/last layer.
- Study the **"traveling thread"** concept to understand layers/cuts/order.
- **Buying designs:** check `T` for hidden threads / excessive cuts — pretty PNG
  previews hide bad sequencing.

---

## O. Character & portrait shading (end-to-end #179)  ⭐

From the Rei Ayanami digitize — how a full anime portrait is built. Almost all of
it is **manual Wilcom craft**; the pipeline can only approximate it (it has no
notion of "form" or "highlight"), but the principles guide what source art to feed
it and what to expect.

- **Shadows with satin (*sombras con satin*).** Model 3-D form by laying
  **directional satin** in the shadow zones, in a darker shade of the region's
  colour, *adjacent to / over* the base fill. Satin's sheen catches light and
  reads as shading. The satin **direction follows the form** (down a cheek, along
  a fold of the plugsuit), not a fixed angle. Sequence: base fill first, shadow
  satin on top.
- **Hair relief (*relieve cabello*).** Build hair as **many thin directional satin
  strands** that follow the hair flow (not one flat fill). Then add **white /
  light highlight satins on top** of the base-colour hair for sheen and dimension
  — the highlights sew **last** (foreground-last). This "relief" is what makes the
  hair look raised rather than printed.
- **Tatami reinforcement for skin/fabric (*refuerzo tatami*).** Large smooth
  regions (skin, the white plugsuit) get a **tatami underlay** so the top fill is
  stable and doesn't ripple — see C1/C3. Skin is a tatami fill; its shadows are
  satin (rule 1 above).
- **Variable-length running stitch for outlines.** The line art / contours use a
  **variable-length run** (e.g. length 2.5 mm, min 1.2 mm) so curves stay smooth
  without over-stitching straights. (Panel: *"Longitud variable del corrido"*.)
- **Layer order for a face:** skin & base fills → colour shading satins → hairline
  & outlines → hair base → hair highlights → eyes/iris detail last. Back-to-front
  throughout (E1), connected (E2), border/outline covering the joins (E5).

**Feeding a portrait to the pipeline:** give it flat colour with a **clean,
separable background** and crisp dark outlines (the outlines survive as satin
linework and hold the shape even where light fills merge with a light background).
Use a higher `--colors` (≈8–12). Expect a **simplified** result: the pipeline
makes flat tatami fills + outline satins; it will **not** reproduce the manual
form-shading or hair relief — that stays a human/Phase-B refinement.

## Pipeline mapping — what Phase A already encodes

| Best practice | Encoded in |
|---|---|
| Right object (satin vs fill) by width | step 5 width classification |
| Minimum column width warning | step 1 + step 2 (1.2 mm consolidation) |
| Underlay on fills | step 5 `fill_underlay` |
| Pull compensation | step 5 `pull_compensation_mm` |
| Back-to-front sew order | step 4 `_sew_order` (enclosure depth) |
| "Cut bitmap into pieces" | steps 1–2 (bg drop + colour quantize) |
| Connect / few trims | step 2 consolidation + step 5 `trim_after`; gate < 5 % |
| Thread cones + sew-order sheet | step 3 + step 6 threadlist |
| Size→density at digitize time | trace writes physical mm |
| Quality gate before hand-off | step 7 verify |

Everything marked *Manual Wilcom / Phase B* above is craft the **human** or the
manual Wilcom save (Phase B) applies in licensed Wilcom — it's reference knowledge,
not automated here.

---

## Quick checklist (before exporting)

- [ ] Intended satin linework **≥ ~1.6 mm** (B1); thinner → run/triple-run.
- [ ] Narrow band = satin; broad/branching = tatami; foliage = chenille/random/motif (A, G).
- [ ] Fills have **underlay**; Column A/B use **by-segment** underlay (C1, C2).
- [ ] Big design → one **general tatami underlay**; caps/3D → **skeleton anchor** (C4, C5).
- [ ] **Pull compensation** + slight **overlap**; front flush, back overlaps ("crab") (D1, D2).
- [ ] Holes only **tatami-on-tatami** (D3).
- [ ] Sew **background → foreground**; **border last** (E1, E5).
- [ ] **Connected**; trims+jumps few — check **`T`** (E2, F2) — gate < 5 %.
- [ ] **Final tie-off** on every object; threshold ≈ 3 mm (F1).
- [ ] 3D: **0.22** fill, **end at points**, **foam = thread colour**, dissect curves (H).
- [ ] Badges: **weld** symmetric halves; offset borders **10/90** not 0/100 (J).
- [ ] **Center point centered**; hoop fits (K).
- [ ] Size set at digitize time; **EMB** scales, other formats only **±10 %** (M).
