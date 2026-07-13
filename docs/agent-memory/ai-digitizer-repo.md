---
name: ai-digitizer-repo
description: "sibling repo ~/Projects/wilcom-ai-digitizer — the AI auto-digitizer project (photo→.vp3); hybrid learn-the-decisions approach; gated on paired (artwork,.vp3) data; new-wilcom-v1 is its renderer + eval harness"
metadata: 
  node_type: memory
  type: project
  originSessionId: d236c827-c714-4db2-82d2-79216f18217b
---

A **separate git repo** `/home/mohammad/Projects/wilcom-ai-digitizer` holds the AI auto-digitizer
project (learn photo → production `.vp3`). This pipeline repo (`new-wilcom-v1`) is its **renderer,
region segmentation, priors, and fingerprint eval harness** — the AI repo depends on it, doesn't
fork it.

**Approach (decided):** learn the **object-level decisions** (region → satin/fill/run + params +
sew order), render deterministically with the pipeline so output stays sewable — NOT a monolithic
image→stitch net (data-hungry + un-sewable). First model = **learned tiering** replacing the
rule-based thresholds, plus **variable-width satin** (the fix for the measured satin gap — see
[[vp3-fingerprint-and-satin-gap]]).

**The blocker is data:** paired `(original artwork, .vp3)` — the source image each vp3 was
digitized from, matched by filename stem in `pairs/`. Unpaired vp3s give priors, not the mapping.
A Wilcom screenshot/render of the vp3 is NOT valid input (leakage). Synthetic render-and-degrade is
pretraining-only (`synth.py`), never eval.

**The whole LABEL pipeline works today** (validated), so a `(artwork, .vp3)` pair → per-region
supervised rows end-to-end via `scripts/build_dataset.py`:
- `extract_objects` — `.vp3` → object-level labels (`objects.json`); 83/83 files → 193 objects
  (144 satin / 22 mixed / 27 fill).
- `align.py` — registers artwork↔vp3 ink masks (similarity transform over 8 dihedral orientations);
  render-perturb-recover self-test recovers known distortions at IoU ≥ 0.98. + `object_masks`,
  `label_regions`.
- `segment.py` — artwork → region labels by reusing the pipeline's OWN quantization (analyze+
  preprocess), so regions match the renderer.
- `link.pair_to_region_rows` — segment + align + match → `region_rows.json` (one row = region +
  the human's object {type,width,angle,order}). Validated: synthetic letters pair → 5/5 regions
  labeled, align IoU ~0.88.
Still stubs: `features.py` (enrich region features), `tiering_model.py`, `synth.py`, `eval.py`.
**The only blocker is real pairs.** Run its tools with the pipeline venv
(`PYTHONPATH=src ../new-wilcom-v1/.venv/bin/python ...`). Ties to [[per-region-tiering]].
