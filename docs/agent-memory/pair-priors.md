---
name: pair-priors
description: "G6: pairs now STEER step 5 automatically — build_pair_priors.py → data/pair_priors.json → priors.py (measured crossover = satin ceiling 3-9mm clamp, satin band = vwidth clamps, satin med = border width); anime's measured crossover is 2.86mm NOT 7mm"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1bb2285a-9c69-47d2-bb5e-fb3d9982dbf6
---

**Built 2026-07-11 (NEXT-GOALS G6, the last one).** The pairs learning loop is CLOSED: every
pair the user drops recalibrates the digitizer with zero code changes.

**Chain:** `<cat>/pairs/*/_measures.json` (per-object labels from register_pair) →
`orchestrator/scripts/build_pair_priors.py` (aggregation; called by ingest_pairs after the
profiles rebuild) → `data/pair_priors.json` → `src/wilcom_pipeline/priors.py` (consumer) →
step 5: ① `_satin_ceiling` uses the MEASURED satin/fill width crossover (midpoint of
satin-verdict p90 and fill-verdict p10; clamped 3-9mm; logs "pair prior: satin ceiling X.Xmm
(n=K pair)"); ② vwidth clamps from the measured satin band (p10..p90, only outside
lettering/satin-lean regimes — explicit user regimes always win); ③ border width prefers the
prior's satin med over the profile med. Trust gate: n_pairs>=1; missing/corrupt file → {} →
constants, byte-identical (verified: letters run with priors file present vs absent differs
ONLY in Ink-Stitch's random path ids).

**Bulk ingest 2026-07-12 (61→63 pairs):** ingested the 51-pair pairs-inbox backlog. Auto-cat
flagged **29/51 ambiguous** (satin-dominant blind spot). REVIEW MATTERS: the fingerprint filed
ALL 8 "numbers" pairs wrong — they were illustrations (hat/truck/peacocks/logo), zero digits,
matched to numbers only via its 3D-digit-with-fills profile. Corrected visually → final ingested
pairs: **decoration 33, anime 18, tatreez 12, numbers 0**. Lesson: always eyeball auto-categorized
pairs before trusting the priors; numbers/letters especially attract mixed-satin/fill illustrations.
`register_pair.py` `_rgb` now resolves ANY CSS colour name via PIL `ImageColor` + fails soft
(CorelDRAW uses the extended set — `antiquewhite` crashed the hex parser, like blue/red/yellow did).
Tatreez pitch prior dropped 2.1→1.45mm when fine #20 (tatreez-12) joined.

**The headline measurement:** anime's pair says the satin/fill boundary is **2.86mm**
(production FILLS objects down to ~1.8mm wide and satins up to ~4mm; fill widths med 2.88) —
NOT the blanket 7mm satin-dominant ceiling. So anime now: narrow satin (<3mm) + tatami +
satin borders on top = exactly pink-goku's 217-outline/118-fill structure. The 7mm ceiling
remains for satin-dominant categories WITHOUT pairs (letters/arabic/etc. until their pairs
arrive). Tests: tests/test_pair_priors.py (aggregation, crossover, clamps, trust gate,
corrupt-file). Priors tune NUMBERS only — structure rules ([[large-regions-tatami]]) stand.
Ties [[svg-vp3-pairs]], [[outline-objects]], [[vwidth-satin]].
