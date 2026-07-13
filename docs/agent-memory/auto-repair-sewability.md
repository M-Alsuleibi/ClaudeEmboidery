---
name: auto-repair-sewability
description: "step-2/3 --auto-repair (default on: speck-merge, hairline-thicken, same-cone palette merge) + step-7 sewability gate (stacking/penetration/budget) — stacking thresholds CALIBRATED on production VP3s (peak ≤5.2 satin-layers), our outputs genuinely over-stack"
metadata: 
  node_type: memory
  type: project
  originSessionId: f4a1b0dc-611a-4120-9de3-3283680b480e
---

**Built 2026-07-11 (NEXT-GOALS G5).** Two halves:

**A. `--auto-repair` (default on; off = byte-identical):** `preprocess._auto_repair` on the
palette-index map after consolidation — ① specks <1.5mm² merge into the ring-dominant
NEIGHBOUR colour (≥60% of the ring one colour; never into background; ≥3 same-colour specks
= dotted pattern → kept — that guard fires a LOT on posterised designs, ritaj kept 119+40);
② components entirely thinner than 0.8mm (width ≈ 2·EDT_max−1 px) dilate ~1px into
BACKGROUND only, toward 1mm; >30% hairline ink → "enlarge the design" advice instead
(calligraphy guard — a LONE hairline is 100% of its ink, fixtures need a solid block);
③ `thread_match._merge_shared_cones`: palette pairs with the SAME cone AND ΔE<5 merge before
tracing (rewrites palette/thread_map/preprocessed_image); distinct colours sharing a cone
(joker's two greens on 5510, ΔE>5) correctly stay separate. Hairline repair replaces
analyze's "satin minimum" warning.

**B. step-7 sewability checks (all warn-level):** `_stacking_check` (0.5mm/px thread-length
map, 3×3 de-alias — raw cells alias a single 0.4mm-row layer to 2.2×), `_penetration_check`
(<0.3mm consecutive penetrations, warn >5%), `_budget_check` (bbox area × category profile
med density, warn >1.8×).

**KEY calibration lesson:** the first stacking thresholds (tatami-layer norm 2.5mm/mm², warn
>3 layers over >2mm²) flagged EVERY production ground-truth file — satin+underlay legitimately
measures 4-8 tatami-equivalents. Calibrate against production: norm = SATIN layer (5mm/mm²);
production peaks ≤5.2 satin-layers with ≤0.8mm² above 5 → warn when >5 layers covers >10mm².
Under that, production passes wide, and OUR outputs genuinely warn (letters 51.5mm² @ up to
14.8 layers; joker ~229mm²) — a true finding: underlap scraps + satin + borders pile locally.
That's future repair-work signal, not a false alarm. Ties [[outline-objects]], [[underlap]],
[[travel-plan]], [[NEXT-GOALS]].
