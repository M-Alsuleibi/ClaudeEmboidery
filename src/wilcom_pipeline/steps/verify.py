"""Step 7 - Self-verify (the gate).

Sanity-check the result before it goes to Phase B (Wilcom). Records
ctx.verification = {"passed": bool, "checks": [...], "metrics": {...}}.

Checks (v1, thresholds documented for calibration against the reference set):
  - nonzero stitches
  - every colour actually sewed (a zero-stitch block = a region eaten by the
    background drop, or a fill that failed) -> hard fail
  - colour changes == colours - 1                                 -> hard fail
  - fill density within a plausible band                          -> warn
  - not over-fragmented (trims+jumps per stitch)                  -> warn
Plus carry-forward of analyze's quality flags (smallest feature, contrast).

A "fail" should trigger a Phase A re-run with adjusted flags — that's the
caller's job; this step only judges and reports.
"""

from __future__ import annotations

from collections import Counter

import pyembroidery as pe

from ..config import PipelineContext

_STITCH = pe.STITCH & 0xFF
_JUMP = pe.JUMP & 0xFF
_TRIM = pe.TRIM & 0xFF
_COLOR_CHANGE = pe.COLOR_CHANGE & 0xFF

_MIN_DENSITY = 0.3    # stitches/mm^2 below this: suspiciously sparse / missing fill
_MAX_DENSITY = 15.0   # above this: over-dense
_MAX_FRAG = 0.05      # (trims+jumps)/stitches above this: over-fragmented


def run(ctx: PipelineContext) -> None:
    if ctx.stitch_pattern is None:
        raise RuntimeError("verify requires ctx.stitch_pattern; run stitches first.")
    pattern = ctx.stitch_pattern

    blocks = _stitches_per_colour_block(pattern.stitches)
    cmds = Counter(c & 0xFF for _, _, c in pattern.stitches)
    n_stitch = cmds.get(_STITCH, 0)
    n_color = len(pattern.threadlist)
    n_changes = cmds.get(_COLOR_CHANGE, 0)

    xs = [s[0] for s in pattern.stitches]
    ys = [s[1] for s in pattern.stitches]
    w_mm = (max(xs) - min(xs)) / 10 if xs else 0.0
    h_mm = (max(ys) - min(ys)) / 10 if ys else 0.0
    area = max(w_mm * h_mm, 1e-6)
    density = n_stitch / area
    frag = (cmds.get(_TRIM, 0) + cmds.get(_JUMP, 0)) / max(n_stitch, 1)

    checks: list[dict] = []

    checks.append(_chk("nonzero_stitches", n_stitch > 0, "error",
                       f"{n_stitch} stitches"))
    empty = [i + 1 for i, c in enumerate(blocks) if c == 0]
    checks.append(_chk("all_colours_sewed", not empty and len(blocks) == n_color, "error",
                       "every colour has stitches" if not empty
                       else f"colour block(s) {empty} have no stitches"))
    checks.append(_chk("colour_changes_consistent", n_changes == max(n_color - 1, 0), "error",
                       f"{n_changes} change(s) for {n_color} colour(s)"))
    checks.append(_chk("density_in_band", _MIN_DENSITY <= density <= _MAX_DENSITY, "warn",
                       f"{density:.2f} stitches/mm^2 (band {_MIN_DENSITY}-{_MAX_DENSITY})"))
    checks.append(_chk("not_fragmented", frag <= _MAX_FRAG, "warn",
                       f"{frag*100:.2f}% trims+jumps per stitch (max {_MAX_FRAG*100:.0f}%)"))

    # Carry forward analyze's quality flags as informational notes.
    notes = list(ctx.analysis.get("warnings", []))

    passed = all(c["passed"] for c in checks if c["severity"] == "error")
    ctx.verification = {
        "passed": passed,
        "checks": checks,
        "notes": notes,
        "metrics": {
            "stitches": n_stitch,
            "colours": n_color,
            "trims": cmds.get(_TRIM, 0),
            "jumps": cmds.get(_JUMP, 0),
            "extent_mm": (round(w_mm, 1), round(h_mm, 1)),
            "density_per_mm2": round(density, 2),
            "fragmentation": round(frag, 4),
        },
    }
    _print_report(ctx.verification)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _chk(name: str, passed: bool, severity: str, detail: str) -> dict:
    return {"name": name, "passed": bool(passed), "severity": severity, "detail": detail}


def _stitches_per_colour_block(stitches) -> list[int]:
    """STITCH counts split at each COLOR_CHANGE (one entry per colour block)."""
    blocks: list[int] = []
    count = 0
    for _, _, cmd in stitches:
        c = cmd & 0xFF
        if c == _STITCH:
            count += 1
        elif c == _COLOR_CHANGE:
            blocks.append(count)
            count = 0
    blocks.append(count)
    return blocks


def _print_report(v: dict) -> None:
    verdict = "PASS" if v["passed"] else "FAIL"
    print(f"      gate: {verdict}")
    for c in v["checks"]:
        mark = "ok " if c["passed"] else ("!! " if c["severity"] == "error" else "~  ")
        print(f"        [{mark}] {c['name']}: {c['detail']}")
    for n in v["notes"]:
        print(f"        (note) {n}")
