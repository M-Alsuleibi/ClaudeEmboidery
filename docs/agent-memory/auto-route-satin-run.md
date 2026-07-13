---
name: auto-route-satin-run
description: "--auto-route step-5 post-pass wiring Ink-Stitch auto_satin/auto_run per colour; strip trim_after first or it backfires; opt-in (helps connected satins, adds visible travel on scattered pieces)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46247877-10fc-48ba-a064-68dfca1bfedc
---

Step 5 (`steps/stitches.py` `_auto_route`) gained `--auto-route / --no-auto-route`
(config `auto_route`, **default OFF**). After the linework prepass it runs Ink-Stitch
`auto_satin` / `auto_run` **PER COLOUR** (each extension threads one path through its whole
selection, so mixing colours would splice threads) to connect a colour's satins/runs into
one optimally-ordered path — underpathing between pieces instead of trimming.

**The critical gotcha (cost a debug cycle):** the prepass stamps `trim_after=True` on every
satin/run. If you leave it on, each piece still trims and auto-route *backfires* — on ritaj
lettering trims went **78 → 98**. Fix: **strip `trim_after` from the routed pieces first**
(let the extension own trimming) and **do NOT re-stamp params afterward** (`_apply_fill_params`
would put trim_after back). auto_satin *preserves* the other attrs (underlay etc.), verified
64/64 satins kept `center_walk_underlay`. With the fix: ritaj **78 → 72 trims, −2% stitches**,
gate PASS.

**When it helps vs hurts (why it's opt-in, not default):**
- Helps: a colour whose satins are **densely connected** (a solid block word, one thread) —
  fewer trims, chosen entry/exit.
- Hurts: **scattered same-colour pieces** — auto_satin underpaths a long travel between them
  and, with no satin to hide under, that travel **shows as a visible line** (a yellow travel
  line appeared across the ritaj accents). And on scattered *runs* (a turtle's disjoint
  outline loops) it added trims (104 → 113), no benefit.

**How to apply:** enable `--auto-route` for connected satin lettering / a bold single-colour
outline; leave it off for scattered accents, dotty art (Arabic tashkeel), or run-dominated
outlines. Ties to [[satin-underlay-and-thin-line-run]].
