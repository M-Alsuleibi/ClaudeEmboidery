# The production-ready workflow (photo → `.vp3` → `.emb`)

How the class builds a finished design, and how our Phase A pipeline performs the
same stages headlessly. Read alongside `best-practices.md` (the *why*).

## The human workflow in the class

1. **Bring in the reference** — paste the artwork into Wilcom (or via Paint).
2. **Cut it into pieces** — Graphics → *Cut bitmap* → *any shape*, one element at
   a time, so each part can be traced on its own (best-practices rule 12).
3. **Plan the order** — decide what's behind and what's in front; decide where
   each object starts and ends so runs don't cross finished work (rules 6, 8).
4. **Digitize each piece with the right object**
   - long constant-width edges → **satin column** (A / B / C), respecting the
     **minimum width** (rules 1, 2);
   - broad areas → **tatami / complex fill** with **underlay** (rules 3, 4);
   - tiny marks → **run / triple-run**.
5. **Clean the connections** — connect objects to kill cuts/jumps; set
   **tie-offs** (~3 mm) and **trim vs jump** per gap (rules 7, 9, 10).
6. **Compensate** — pull compensation + slight overlap so no gaps open (rule 5).
7. **Size & save** — set the physical size (resize recomputes density, rule 13)
   and save the encrypted **`.emb`** in licensed Wilcom.

## The pipeline's equivalent (this repo, Phase A)

```
photo ─▶ ① analyze ─▶ ② preprocess ─▶ ③ thread-match ─▶ ④ trace
      ─▶ ⑤ stitches ─▶ ⑥ emit VP3 + worksheet + preview ─▶ ⑦ self-verify
```

| Stage | Does the class step… | Key best practice |
|---|---|---|
| ① analyze | reads size, colours, background; warns on sub-1.2 mm features | min width (2) |
| ② preprocess | quantizes colours + drops background = **"cut the bitmap into pieces"**; consolidates specks → fewer objects | prep (12), fewer cuts (7) |
| ③ thread-match | snaps each colour to a real cone (Madeira/Isacord) | operator sheet (9) |
| ④ trace | one layer per colour; **back-to-front sew order** by enclosure | sequencing (6) |
| ⑤ stitches | per-colour: **satin** for narrow linework, **tatami + underlay** for areas; pull comp; `trim_after` | object choice (1,3,4,5) |
| ⑥ emit | writes `.vp3` + threadlist + **upright** preview | hand-off |
| ⑦ verify | gate: stitches>0, all colours sewed, density in band, **trims+jumps < 5 %** | no-fragment (7) |

Phase B (`phase_b/emb_save.ahk`, Windows + dongle) takes the `.vp3` into Wilcom
and writes the encrypted `.emb` — where final **tie-offs / connectors** are
confirmed (rules 9, 10), since the `.emb` `DesignDocument` stream can't be
written by any script.

## What "production-ready" means here

A design that, handed to the machine, runs **without surprises**: right object
per region, no sub-minimum columns, stable underlay, compensated pull, clean
back-to-front order, and as few trims/jumps as the shape allows — verified by the
step-7 gate before it ever reaches Phase B. The Totoro `.vp3` in `output/` meets
all of these.
