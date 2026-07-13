---
name: wilcom-stitch-type-taxonomy
description: "Wilcom's own model: two stitch families — Outline (open/closed; borders+details) vs Fill (CLOSED only; areas); validates + names the pipeline's per-region tiers"
metadata: 
  node_type: memory
  type: project
  originSessionId: d236c827-c714-4db2-82d2-79216f18217b
---

Wilcom EmbroideryStudio (the Phase-B target) classifies every stitch object into exactly
**two families**, per its own UI tooltips (user-supplied `wilcom-manual/fill.jpeg` / `wilcom-manual/outline.jpeg`):

- **Outline stitches** — *"create simple as well as decorative BORDERS and DETAILS. Can be
  applied to **OPEN or CLOSED** objects."* Sub-types (toolbar icons): running stitch, triple /
  bean run, satin-as-a-line (column), motif run. They follow a **line** (a path).
- **Fill stitches** — *"create simple as well as decorative FILLS. Can **ONLY** be applied to
  **CLOSED** objects."* Sub-types: tatami, satin-fill, decorative/pattern fills. They pack an
  **area** (a closed region).

**This is exactly the model [[per-region-tiering]] implements**, and it names it + gives a hard
invariant:

| Wilcom family | applies to | our tier |
|---|---|---|
| Outline (borders/details) | open **or** closed | **run** + **satin-column** — built on a `fill_to_stroke` centerline (an *open* path) |
| Fill (areas) | **closed only** | **tatami fill** — on a closed vtracer region |

**Invariant we honour:** a fill needs a CLOSED object; outline stitches (run / satin) ride an
open centerline. The pipeline is correct here — `fill_to_stroke` produces the open centerline for
run/satin, and tatami only ever goes on closed regions. So "region → skeletonise → run/satin" vs
"region → tatami" is literally Wilcom's outline-vs-fill choice made per region.

**Unbuilt direction it points to:** Wilcom's **decorative / motif** variants (motif runs, pattern
/ decorative fills — the extra icons in both rows) are a stitch-type family the pipeline doesn't
emit yet; a natural future tier for ornament ([[decoration-category-knowledge]]). Also note both
outline and fill can be "simple OR decorative" — our run/satin/tatami are the *simple* forms.
