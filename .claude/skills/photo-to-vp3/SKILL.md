---
name: photo-to-vp3
description: >-
  DEPRECATED — do not use. This skill has been superseded by the `orchestrator` skill, which
  is the single entry point for turning any image into a production-ready Wilcom `.vp3`
  (it adds any-format input normalization, output to `orchestrator/output/`, and an
  iterate-until-faithful verify loop). Never trigger this skill; route all photo→embroidery /
  digitize / `.vp3` / stitch-file requests to `orchestrator` instead.
---

# photo-to-vp3 — DEPRECATED, use `orchestrator`

This skill is retired. Its capabilities live in the **`orchestrator`** skill
(`.claude/skills/orchestrator/`), which supersedes it end-to-end:

- accepts **any input format** (PNG/JPG/WEBP/HEIC/TIFF/PSD/SVG/PDF/…) via a normalize step,
- writes artifacts to **`orchestrator/output/`**,
- and **iterates the result against the original** until it is a faithful copy.

For anything you would have used this skill for, use `orchestrator`. The bundled scripts and
eval prompts here are kept only for git history.
