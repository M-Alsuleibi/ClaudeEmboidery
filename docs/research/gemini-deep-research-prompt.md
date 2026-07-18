# Gemini Deep Research — paste-ready prompt

There is no GitHub "connect" button in Gemini — Deep Research reads public URLs
straight from the prompt text. The repo is public at
`https://github.com/M-Alsuleibi/ClaudeEmboidery`, so just paste the prompt below
(the links are embedded in it). Optionally also attach
`gemini-deep-research-brief.md` via the + button for redundancy.

---

I am building an automatic embroidery digitizing system: a headless Python pipeline
that converts a photo/artwork into a production-ready `.vp3` machine-embroidery file,
aiming to match the output quality of a professional digitizer using Wilcom
EmbroideryStudio.

The full source code and documentation are public here — browse them:
https://github.com/M-Alsuleibi/ClaudeEmboidery

Read these documents first (raw text links), in this order:
1. Research brief — the system summary, open gaps, and constraints for this research:
   https://raw.githubusercontent.com/M-Alsuleibi/ClaudeEmboidery/main/docs/research/gemini-deep-research-brief.md
2. Architecture & pipeline guide:
   https://raw.githubusercontent.com/M-Alsuleibi/ClaudeEmboidery/main/CLAUDE.md
3. Distilled Wilcom Reference Manual rules (the production target):
   https://raw.githubusercontent.com/M-Alsuleibi/ClaudeEmboidery/main/wilcom-manual-rules.md
4. Ground-truth pair findings (measured production behaviour):
   https://raw.githubusercontent.com/M-Alsuleibi/ClaudeEmboidery/main/PAIRS-FINDINGS.md
5. Category playbook (how designs are routed):
   https://raw.githubusercontent.com/M-Alsuleibi/ClaudeEmboidery/main/EMBROIDERY-PLAYBOOK.md
The digitizing core is `src/wilcom_pipeline/steps/stitches.py`; inspect any source
file in the repo as needed.

The brief (link 1) describes the architecture, what is already implemented, the
measured ground-truth calibration loop, the known open gaps, and the hard constraints
(headless Linux, Ink-Stitch binary + pyembroidery as the only stitch engines, `.vp3`
output).

Research the following and produce a report with concrete, source-cited findings.
Do NOT re-propose anything listed in the brief's "already implemented" section, and
respect the "hard constraints" section — proposals requiring a Wilcom license, a GUI,
or Windows automation are out of scope.

**Part A — capabilities to enhance the ultimate goal (photo → production-quality
embroidery, fully automatic):**

1. State of the art in automatic embroidery digitizing: academic papers, patents,
   theses, and commercial systems (Wilcom Smart Design / PhotoStitch, Pulse, Hatch,
   Brother PE-Design, Embrilliance, Chroma, SewArt, Stitch Era, etc.). What algorithms
   do they document for region→stitch-type decisions, stitch angle estimation, and
   satin column extraction? Anything published beyond what my brief already encodes?
2. Raster **stroke recovery** for calligraphy/script: algorithms or tools that recover
   ordered pen strokes (centerline + width + direction + overlap order) from raster
   images — stroke-extraction papers (e.g. for Chinese calligraphy, handwriting
   vectorization, font reverse-engineering), and any open-source implementations.
3. **Stitch-direction / angle-field generation** for fills: methods to compute
   form-following direction fields over 2D regions (structure tensor, PolyVector
   fields, medial-axis-guided fields, neural approaches) applicable to tatami and
   turning satin.
4. **Learning-based digitizing**: any public datasets pairing artwork with embroidery
   stitch files; papers on generative stitch synthesis, imitation learning from
   digitizer behaviour, or differentiable embroidery rendering; feasibility of
   building a dataset from community file archives legally.
5. **Push–pull distortion modelling**: published models (industry or academic, incl.
   textile engineering) predicting fabric distortion per stitch object, usable to
   replace static pull-compensation tables.
6. Stitch-sequence **segmentation/classification**: methods to parse a raw stitch
   sequence back into objects and stitch types (for our verify gate and pair
   labelling), better than turn-angle heuristics.

**Part B — Wilcom production functionality parity:**

7. For each feature in the brief's section 6 (auto-spacing satin, fractional spacing,
   smart corners, motif fills, program splits, gradient/blend fills, raised satin,
   ESA-style lettering, Color PhotoStitch, first-class branching objects): assess
   implementability in an open pipeline. Specifically: (a) does Ink-Stitch (v3.x)
   already expose it or have it on its roadmap/issues? (b) if not, what published
   algorithm or open-source code (Ink-Stitch internals, PEmbroider, libembroidery,
   Embroidermodder, TurtleStitch, academic code) could implement it, given that we can
   write arbitrary stitches directly with pyembroidery? Rank these by
   effort-vs-production-impact.
8. `.vp3` and related format ecosystems: any public documentation or reverse-
   engineering of Wilcom `.emb`, ESA fonts, or richer interchange formats that would
   let our output round-trip into editable objects rather than raw stitches.

**Output format:** for every finding give the source (paper/repo/manual/issue link),
a 2–3 sentence summary of the technique, and a one-line assessment of how it maps
onto the pipeline in the brief (which step, which gap it closes, expected impact).
End with a prioritized top-10 roadmap: highest production-impact items first, each
with estimated integration difficulty under the stated constraints.
