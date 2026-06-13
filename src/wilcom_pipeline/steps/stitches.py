"""Step 5 - Generate stitches (Ink-Stitch headless).

Invoke the vendored, self-contained Ink-Stitch binary on the layered SVG to
digitize it. Ink-Stitch auto-fills the colour groups (with automatic routing,
trims, jumps and colour sequencing), reads the inkscape:label cones we set, and
exports a VP3. We read that back into a pyembroidery pattern as ctx.stitch_pattern.

Run headless (no Inkscape needed for export):
    inkstitch --extension=zip --format-vp3=True design.svg > out.zip

NOTE (v1): we run with Ink-Stitch defaults, which already give clean fills with
good routing/trims. The goal doc's deeper tuning — fill underlay, ~0.4 mm
density, pull compensation, satin for thin columns, foreground-last sequencing —
is the next refinement, injected as inkstitch:* params onto the SVG before this
call. The integration itself is what this step establishes.
"""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import pyembroidery as pe

from ..config import PipelineContext

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BIN = _REPO_ROOT / "vendor" / "inkstitch" / "bin" / "inkstitch"
_TIMEOUT_S = 300


def _candidate_binary() -> Path:
    env = os.environ.get("INKSTITCH_BIN")
    return Path(env) if env else _DEFAULT_BIN


def binary_available() -> bool:
    return _candidate_binary().is_file()


def _locate_binary() -> Path:
    cand = _candidate_binary()
    if not cand.is_file():
        raise RuntimeError(
            f"Ink-Stitch binary not found at {cand}.\n"
            "Vendor the Linux portable bundle under vendor/inkstitch/ or set "
            "INKSTITCH_BIN (see README)."
        )
    return cand


def run(ctx: PipelineContext) -> None:
    if ctx.svg_path is None:
        raise RuntimeError("stitches requires ctx.svg_path; run trace first.")

    binary = _locate_binary()
    proc = subprocess.run(
        [str(binary), "--extension=zip", "--format-vp3=True", str(ctx.svg_path)],
        capture_output=True,
        timeout=_TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Ink-Stitch failed (exit {proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace')[:1000]}"
        )

    pattern = _read_vp3_from_zip(proc.stdout, proc.stderr)
    ctx.stitch_pattern = pattern
    _print_summary(pattern)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _read_vp3_from_zip(stdout: bytes, stderr: bytes) -> "pe.EmbPattern":
    try:
        zf = zipfile.ZipFile(io.BytesIO(stdout))
    except zipfile.BadZipFile as exc:
        raise RuntimeError(
            "Ink-Stitch did not return a valid zip. stderr: "
            f"{stderr.decode('utf-8', 'replace')[:1000]}"
        ) from exc

    vp3_names = [n for n in zf.namelist() if n.lower().endswith(".vp3")]
    if not vp3_names:
        raise RuntimeError(f"Ink-Stitch zip contained no .vp3 (got {zf.namelist()}).")

    vp3_bytes = zf.read(vp3_names[0])
    # pyembroidery picks the format from the file extension, so use a .vp3 temp.
    with tempfile.NamedTemporaryFile(suffix=".vp3", delete=False) as tmp:
        tmp.write(vp3_bytes)
        tmp_path = tmp.name
    try:
        return pe.read(tmp_path)
    finally:
        os.unlink(tmp_path)


def _print_summary(pattern: "pe.EmbPattern") -> None:
    cmds = Counter(c & 0xFF for _, _, c in pattern.stitches)
    n_stitch = cmds.get(pe.STITCH & 0xFF, 0)
    n_trim = cmds.get(pe.TRIM & 0xFF, 0)
    n_jump = cmds.get(pe.JUMP & 0xFF, 0)
    xs = [s[0] for s in pattern.stitches]
    ys = [s[1] for s in pattern.stitches]
    w = (max(xs) - min(xs)) / 10 if xs else 0  # VP3 is in 0.1mm units
    h = (max(ys) - min(ys)) / 10 if ys else 0
    print(
        f"      Ink-Stitch -> {n_stitch} stitches, {len(pattern.threadlist)} colour(s), "
        f"{n_trim} trim(s), {n_jump} jump(s); stitched extent ~{w:.1f}x{h:.1f}mm"
    )
