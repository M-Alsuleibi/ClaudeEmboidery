# Animals — fur/feather sketch-stitch embroidery

> **Status: REGISTERED + INGESTED** (2026-07-13) — `animals` is a `SUPPORTED_CATEGORIES`
> class; **10 ground-truth pairs** live in `animals/pairs/1..10/` and feed
> `data/category_profiles.json` (step-7 drift gate) + `data/pair_priors.json` (step-5
> numbers). Created to fix the fox failure: solid tatami/satin coverage is the WRONG
> technique for fur — production animals are airy layered stroke work.

## What the category is

Cute/realistic **animal illustrations rendered as sketch embroidery**: ostrich/emu pair,
highland cow with a bow, kitten on a rope, and similar fur/feather subjects. The defining
look is **"sketch stitch" / scribble fur** — the animal is built from **hundreds of long,
overlapping run/bean strokes that follow the fur or feather direction**, with the fabric
deliberately showing through between strokes. Solid coverage exists only as small accents
(a nose, an eye, a bow) sewn as narrow satin.

| pair | Subject | Size (mm) | Colour blocks | Stitches |
|------|---------|-----------|---------------|----------|
| 1 | Ostrich + emu heads | 89 × 87 | 9 | 19.4k |
| 2 | (fur subject) | 114 × 111 | 5 | 33.8k |
| 3 | (detailed subject) | 122 × 140 | 13 | 61.2k |
| 4 | (fur subject) | 77 × 115 | 6 | 29.1k |
| 5 | Highland cow + bow | 78 × 89 | 11 | 21.3k |
| 6 | (fur subject) | 119 × 165 | 5 | 43.6k |
| 7 | (fur subject) | 140 × 134 | 14 | 34.9k |
| 8 | (fur subject) | 139 × 140 | 8 | 67.5k |
| 9 | Kitten on rope | 216 × 205 | 9 | 109.9k |
| 10 | (fur subject) | 136 × 191 | 17 | 58.5k |

## Measured DNA (n=10 pairs, 1,647 registered objects)

- **ALL OUTLINE, ZERO FILLS.** Every one of the 1,647 SVG↔VP3-registered objects is an
  outline-family object — production never uses an area fill on these designs. "Solid"
  bits are narrow satin columns.
- **Stroke width:** satin_w p10/med/p90 = **0.78 / 1.12 / 1.64 mm** — much thinner than
  anime (1.8–2.2). Crossover 1.64 mm (clamps to the 3 mm step-5 ceiling floor).
- **Block signature:** most colour blocks read **"mixed" at 20–25 % turn-reversal with
  ~2.3–2.4 mm median segments** = long meandering sketch runs (not satin ≥36 %, not
  tatami rows ≤15 %). Satin accents run 36–50 % reversal at 0.5–1.1 mm segments.
- **Colours:** median **9** blocks (IQR 6.5–12.5, up to 17); a natural fur palette
  (creams, tans, greys, rust) + **black sketch linework** + **white highlight strokes**.
  The same cone often appears in several stops (layering passes).
- **Density:** median 2.57 st/mm² over the inked bbox, but the *visual* coverage is airy —
  strokes overlap in ropes rather than tiling the area. Trims 20–464 (fur strokes chain).
- **Size:** 77–216 mm, median ~130 mm.
- **Sew order (consistent across pairs):** base colour wash strokes → mid/dark fur
  layering strokes → **black sketch outline + face details late** → **white
  highlights/whiskers very last** (pair 1's final block: tiny white satin accents at
  84 % reversal; pair 9's whiskers sit on top of everything).

## Fingerprint caveat

`satin_frac` reads ~99 for these files — the same block-granularity artifact as tatreez:
dense overlapping runs reverse often enough to score "satin". The **real discriminator vs
anime/decoration is the mixed-block signature** (rev 20–25 %, medSeg ≥2 mm) plus
all-outline object families. The auto-categorizer scored these decoration/anime (0.3–0.9)
before the profile existed — always sanity-check by eye.

## Recipe — the sketch_stitch primitive (built 2026-07-13, `steps/sketchstitch.py`)

`--category animals` AUTO-routes step 5 into the **sketch-stitch generator** (force with
`--sketch-stitch`/`--no-sketch-stitch`), which builds the stitches directly with
pyembroidery — no Ink-Stitch, no traced SVG (steps 4's trace skips itself):

```bash
digitize.sh photo.png --width-mm 130 --category animals --thread-chart madeira-polyneon \
    [--sketch-spacing-mm 0.98]   # default = the pair prior row spacing
```

How it draws:
- **Fur-direction field** from the SOURCE art (structure tensor of the luminance at
  ~2 mm scale) — strokes follow the fur the artist drew; flat areas fall back to the
  region's own axis. Orientation is resolved per ~9 mm cell, so flow curves.
- **Fur flicks**: each stroke is a ~4.2 mm doubled-back pen stroke (forward-back-forward,
  return passes fanned ~0.3 mm, pivoting at shared endpoints) — the pivot turns are the
  closely-spaced reversals the ground-truth fingerprint reads as satin (a serpentine
  scanline turns 90° at row ends and reads as a FILL — measured satin_frac 4 vs 100).
- **Keyline detail** (`KEYLINE_DETAIL_RGB`, split by preprocess) sews LAST as true
  **bean** runs (re-entering the same penetrations) = the black sketch outline on top.
- Calibrated constants: stitch pitch 1.7 mm, spacing factor 0.75 × the prior (production
  layers repeated stops the per-object prior can't see), jitter ±0.35 mm.

Fox validation (130 mm): gate PASS, satin_frac 100 [92–100], fill 0 [0–0], density 2.38
[2.30–3.24], satin_w 1.68 [1.26–1.674] (0.006 mm over — noise), 36k stitches vs ~39k
expected, coverage 99.6 %, IoU 97.2 %. Other knobs: omit `--colors` (prior 8), madeira
for fur naturals, size ≥ ~120 mm, `--snap-black` on (feeds the keyline layer).
