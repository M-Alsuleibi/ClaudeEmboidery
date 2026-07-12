# pairs-inbox — drop production (SVG, VP3) pairs here

Drop both halves of each pair in this folder — **matching filenames**, any case:

```
pairs-inbox/
  my-design.svg     <- CorelDRAW vector export of the design
  my-design.vp3     <- the production stitch file of the SAME design
```

Then run (or just ask Claude to "ingest the pairs"):

```bash
.venv/bin/python orchestrator/scripts/ingest_pairs.py            # or --dry-run first
```

That's all you do. The script:

1. **auto-categorizes** each pair (VP3 fingerprint vs `data/category_profiles.json`)
   and moves it to **`<category>/pairs/<design>/`** — you do NOT sort anything by hand;
2. **labels** it (`extract_pair.py` structure + `register_pair.py` SVG↔VP3 registration:
   per-object mm widths, density, row spacing, satin-vs-tatami per region);
3. **tracks** the VP3 in git (`add -f`; VP3s are gitignored by default) and **rebuilds**
   the category profiles that step 7's drift gate scores against **plus
   `data/pair_priors.json` — pairs now steer step 5 automatically**: the category's
   measured satin/fill width crossover becomes its satin ceiling, its satin-width band
   sets the variable-width clamps, and its satin-width median sets the border width.
   Every pair you drop recalibrates the digitizer with zero code changes;
4. prints the table row to append to `PAIRS-FINDINGS.md`.

Notes:

- **Target: 2–3 pairs per category.** One pair is a flagged single data point (n=1);
  2–3 make a profile the pipeline can safely default from.
- A pair the classifier can't place lands in `pairs-inbox/unknown/<design>/` with
  printed next steps — it may be a genuinely **new category** (the script tells you
  how to promote it: create `<category>/` + knowledge doc, add it to
  `SUPPORTED_CATEGORIES` + `CATEGORY_COLORS` in `src/wilcom_pipeline/config.py`,
  re-ingest).
- Satin-dominant categories (letters/arabic/simple-shapes/numbers/decoration) look
  alike to the VP3 fingerprint, so near-ties are flagged `~ ambiguous` — glance at the
  printed scores and move the folder if the call is wrong.
- A lone `.svg` or `.vp3` without its partner is skipped with a warning — a pair
  needs both.
