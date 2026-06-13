# Phase B — VP3 → native `.EMB` (Windows + Wilcom EmbroideryStudio)

Phase A (Linux) produces `NAME_pro.vp3`. Phase B opens it in a **licensed**
EmbroideryStudio, rebuilds editable objects, and does the encrypted `Save As .emb`
that only Wilcom can write. `emb_save.ahk` automates that GUI flow.

> The script only presses keys you could press yourself. It does **not** decrypt,
> bypass the dongle, or reverse-engineer the format. It needs an unlocked,
> logged-in desktop with ES running at the **same elevation** as the script.

## One-time Windows setup
1. EmbroideryStudio — installed + licensed.
2. **AutoHotkey v2** — install from autohotkey.com (free).
3. Copy `emb_save.ahk` to a permanent folder, e.g. `C:\embtools\`.

## Per run
1. On Linux: run Phase A → `NAME_pro.vp3` (+ worksheet + preview). **Check the
   preview vs. the source** before sending — that's the quality gate.
2. Copy the VP3 to Windows (e.g. Downloads).
3. On Windows: **launch ES** and unlock the desktop. Do *not* open the VP3
   yourself — the script opens it.
4. Run the script:
   - double-click `emb_save.ahk` (a picker asks for the VP3), **or**
   - `"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe" C:\embtools\emb_save.ahk "C:\Users\you\Downloads\NAME_pro.vp3"`
5. It opens the VP3 → recognises objects → `Save As NAME.emb` (next to the VP3,
   `_pro` stripped) → leaves the design open for QC.

## ⚠️ First run is supervised — confirm the version-specific bits
This script is **authored, not yet tested against a live ES** — menu items and
shortcuts differ across ES versions. Keep `CONFIG.safeMode := true` (the default):
it pauses before every irreversible step so you can watch and correct. Open
`emb_save.ahk` and confirm/adjust the `CONFIG` block:

- `esTitle` — the substring in your ES title bar.
- `openKeys` — File ▸ Open (default `^o`).
- `saveAsKeys` — File ▸ Save As (default `{F12}`; some builds use `^+s` or the
  File menu).
- `recognizeMenu` — Alt-accelerator keystrokes for **Stitch ▸ Recognize
  Objects/Outlines**, e.g. `["!s","r"]`. Leave `[]` to have the script *pause*
  and let you recognise by hand (fine for the MVP).
- timeouts (`tWindow`, `tDialog`, `tProcess`) if your machine is slow.

Once a run goes cleanly end-to-end, set `safeMode := false` for hands-off runs.
Every action is logged to `emb_save.log` beside the script.

## QC after it runs (acceptance check)
With the `.emb` open in ES, confirm the design recognised into real objects:
**Break Apart and Reshape are enabled and work**, resizing recalculates stitches,
stitch types are sane, and TrueView matches the source. Threads should be the
catalog cones from the worksheet, in sew order.

## Notes / gotchas
- A compiled AHK `.exe` can trip AV heuristics — run the `.ahk` via the
  interpreter (as above) or whitelist it.
- Skim the ES EULA once for any "no scripted use" clause (uncommon).
- The VP3 is only read; the `.emb` is new — nothing overwrites your input.
