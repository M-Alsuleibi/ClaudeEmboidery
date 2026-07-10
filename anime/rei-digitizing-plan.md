# Rei Ayanami — production hand-digitizing plan (Wilcom)

A worksheet to digitize Rei the way the instructor does in video **#179**
(`3AY51pJYbwY`), so the result is production-ready — *not* the flat, auto-traced
`rei_ayanami_pro.vp3` the Phase-A pipeline makes. Use this in licensed Wilcom
(Phase B); the pipeline cannot do the manual form-shading below.

### How this is grounded (read before trusting numbers)

This video has **no narration to transcribe** — no captions, and a full Whisper
pass returned only hallucinated filler over background music (see
`best-practices.md`, section O note). So every number here is one of:

- 🎞 **read off a timestamped frame** of the actual Wilcom property panel — verifiable, design-specific;
- 📚 **this instructor's method from the live-class transcripts #3–#8** — verified, general;
- 🧩 **my inference** joining the two — treat as a starting point, test-sew it.

Always confirm against your fabric with a sew-out (the instructor says this
repeatedly across the course).

---

## Design spec

| | |
|---|---|
| Subject | Rei Ayanami, half-body bust |
| Size | **85 mm wide** 🎞 (tab "Rei Ayanami Evangelion 85mm") |
| Colours | ~8–10 cones 🎞 (blue hair, white & tan skin, red eyes, white/grey/black plugsuit, amber accents) |
| Base technique | line-art reference locked under the work; trace each piece with Column B / complex fill 🎞 |

---

## Global object settings (read off the panels)

| Setting | Value | Source |
|---|---|---|
| Outline **run** ("Corrido") length | **2.50 mm**, variable-length **on**, min **1.20 mm**, spacing 0.05 mm | 🎞 t05 / 00:50 |
| **Satin** ("Plumetis") spacing — detail | **0.40 mm** | 🎞 t16 |
| Satin spacing — hair base | **0.66 mm** | 🎞 t48 |
| Satin auto-division length / min | **8.50 mm / 0.40 mm** | 🎞 t16 |
| **Complex fill** overlap (*traslape*) | **1** | 🎞 t28 |
| Complex fill angle — plugsuit | **30°** | 🎞 t28 |
| Complex fill angle — eye/iris | **27°** | 🎞 t40 |
| Connector **jump** (Salto) | **7.0 mm** | 🎞 t05 |
| Connector **trim** when next > | **6.0 mm** | 🎞 t05 |
| Tie-off length / count | **1.00 mm / 2** | 🎞 t05 |
| Pull compensation | per fabric, ~0.2–0.3 mm | 📚 #3,#4 |

Underlay: **tatami underlay** under skin & plugsuit fills (*refuerzo tatami*) 📚;
**by-segment** underlay on Column A/B satins 📚 #6.

---

## Sew order & object-by-object plan (back-to-front)

Sew background/under layers first, top detail last 📚 #3,#4,#8. For a face the
instructor builds skin → shading → hair → highlights → features.

1. **Skin base (face, neck, hands)** — `complex fill` (tatami), angle to the
   plane of the face, **tatami underlay**. 🎞 base under the slivers / 📚
   - Keep it one continuous fill where possible; holes only tatami-on-tatami 📚 #4.

2. **Skin shading / form (*sombras con satin*)** — short **Column B satin
   slivers** in a darker skin shade, laid **along the form** (down the cheek,
   under the jaw, eye sockets), spacing **0.40 mm**. 🎞 t05 / 📚 section O. These
   sit on top of the skin base and *model* the face — this is the part the
   auto-pipeline can't do.

3. **Eyes** — iris/sclera as small **complex fills**, overlap 1, angle **27°**,
   radial to the iris; red iris + dark pupil + white catch-light **last**. 🎞 t40.
   Eyes/features are the very last colour block (foreground-most). 📚 E1.

4. **Plugsuit base (white/grey)** — `complex fill`, overlap **1**, angle **30°**,
   tatami underlay. 🎞 t28. Front pieces flush to their outline, pieces that go
   *behind* extended under the front ("crab method"). 📚 D2.

5. **Plugsuit shadows** — darker-grey **Column B satin** along the folds/edges,
   same idea as skin shading. 🎞 t28 region / 📚 section O.

6. **Amber/red accent panels** — small `complex fill` or satin, their own colour.
   🎞 t28 (orange rectangles).

7. **Hair base** — **directional Column B satin strands** following the hair
   flow, spacing **0.66 mm**, *not* one flat fill. 🎞 t48. Work lock by lock.

8. **Hair shadow strands** — dark-blue/near-black satin slivers between locks for
   depth. 🎞 t16.

9. **Hair relief / highlights (*relieve cabello*)** — **white / light satin
   strands on top**, sewn **last** so they sit raised over the blue. 🎞 t16,t48 /
   📚 section O. This is what makes the hair read 3-D.

10. **Outlines / line-art** — **variable-length run**, length 2.50 / min 1.20 mm,
    drawn **last** so it covers the joins between pieces. 🎞 t05 / 📚 E5.

**Connectors throughout:** connect pieces, keep jumps < 7 mm, trim only when the
next object is > 6 mm away; final tie-off on every object. 🎞 t05 / 📚 F1,F2.

---

## Bootstrapping from the pipeline output

You don't have to start from a blank canvas. Use `output/rei_ayanami_pro.vp3`
(or the layered `rei_ayanami_pro.svg`) as a **rough colour-separation base**:

1. Open it in Wilcom; it already gives you the flat colour regions + back-to-front
   order + thread cones.
2. **Replace, region by region**, the flat fills with the objects above — most
   importantly: convert the hair fill into directional satin strands + highlights
   (steps 7–9), and add the skin/plugsuit **satin shading** (steps 2, 5).
3. Re-cut the outlines as variable-length runs (step 10) and fix the sequence.

That turns the pipeline's ~30-second flat draft into a base for the ~50-minute
hand job, instead of digitizing from zero.

---

## What the pipeline does vs. what stays manual

| | Auto pipeline (Phase A) | Manual in Wilcom (this plan) |
|---|---|---|
| Colour separation, back-to-front order | ✅ | — |
| Flat tatami fills + outline satins | ✅ | — |
| **Form shading with directional satin** | ❌ | ✅ steps 2, 5 |
| **Hair as strands + relief highlights** | ❌ | ✅ steps 7–9 |
| Per-object underlay choice, fold-aware angles | ❌ | ✅ |
| Tie-offs / connectors finalised | partial | ✅ |

The gap in the middle two rows is exactly why the instructor digitizes Rei by
hand and why the auto `.vp3` looks flat. No amount of watching changes that — it's
a tooling boundary, documented honestly so you can plan the manual finish.
