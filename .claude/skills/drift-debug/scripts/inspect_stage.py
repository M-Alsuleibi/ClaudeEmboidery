#!/usr/bin/env python
"""Stage-bisection helpers for drift-debug (see ../SKILL.md).

Run with the repo venv from the repo root:
    PYTHONPATH=src .venv/bin/python .claude/skills/drift-debug/scripts/inspect_stage.py <cmd> ...

Commands
--------
preprocess IMG --width-mm W [--colors N] [--category C] [--chart CH] --out DIR
    Reproduce steps 1-2 in-process; save the quantized RGBA (quantized.png) and print
    pixel counts per palette colour. The first bisection stop: is the feature still
    present, and which palette colour owns it?

window PNG X0 Y0 X1 Y1 [--dark-below S] [--save CROP.png]
    Programmatic pixel-window check (NEVER eyeball crops — content can carry scale
    transforms). Prints dark-pixel count and the top colour values in the window.

group WORKING_SVG (--id COLORID | --index I) --out PNG [--width PX] [--bg HEX]
    Render ONE colour group of a traced working SVG in isolation at native work
    resolution (default 1200). --index -1 = last group = the keyline-detail layer.

vp3 FILE [--near X_MM Y_MM --radius MM]
    Per-colour stitch-block counts in sew order (compare against the threadlist!) and,
    with --near, how many stitches fall within radius of a design-mm location.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path


def cmd_preprocess(a):
    import contextlib
    import io

    import numpy as np
    from wilcom_pipeline.config import PipelineConfig, PipelineContext
    from wilcom_pipeline.steps import analyze, preprocess

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = PipelineConfig(
        input_path=Path(a.image), output_dir=out, name="probe",
        target_width_mm=a.width_mm, num_colors=a.colors, category=a.category,
        thread_chart=a.chart,
    )
    ctx = PipelineContext(config=cfg)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        analyze.run(ctx)
        preprocess.run(ctx)
    print(buf.getvalue())
    arr = np.asarray(ctx.preprocessed_image)
    opaque = arr[..., 3] >= 128
    print(f"work size: {ctx.preprocessed_image.size}")
    for i, c in enumerate(ctx.palette):
        n = int((opaque & (arr[..., :3] == np.array(c)).all(axis=2)).sum())
        print(f"  palette[{i}] {tuple(c)}: {n} px")
    ctx.preprocessed_image.save(out / "quantized.png")
    print(f"saved {out / 'quantized.png'}")


def cmd_window(a):
    import numpy as np
    from PIL import Image

    im = Image.open(a.png).convert("RGB")
    arr = np.asarray(im)
    win = arr[a.y0:a.y1, a.x0:a.x1]
    dark = win.sum(axis=2) < a.dark_below
    print(f"window {a.x0},{a.y0}..{a.x1},{a.y1} of {im.size}: "
          f"{int(dark.sum())} px darker than sum<{a.dark_below}")
    vals = Counter(map(tuple, win.reshape(-1, 3).tolist()))
    for v, n in vals.most_common(8):
        print(f"  {v}: {n}")
    if a.save:
        Image.fromarray(win).resize((win.shape[1] * 4, win.shape[0] * 4),
                                    Image.NEAREST).save(a.save)
        print(f"saved 4x crop -> {a.save}")


def cmd_group(a):
    import cairosvg
    from lxml import etree

    NS = {"svg": "http://www.w3.org/2000/svg"}
    t = etree.parse(a.svg)
    root = t.getroot()
    gs = root.findall("svg:g", NS)
    ids = [g.get("id") for g in gs]
    if a.id:
        keep = a.id
    else:
        keep = ids[a.index]
    print(f"groups (document = sew order): {ids}\nkeeping: {keep}")
    for g in gs:
        if g.get("id") != keep:
            root.remove(g)
    cairosvg.svg2png(bytestring=etree.tostring(t), write_to=a.out,
                     output_width=a.width, background_color=a.bg)
    print(f"rendered {keep} at {a.width}px -> {a.out}  "
          "(now check it with the `window` command, not your eyes)")


def cmd_vp3(a):
    import pyembroidery

    p = pyembroidery.read(a.file)
    blocks, cur = [], 0
    for st in p.stitches:
        cmd = st[2] & pyembroidery.COMMAND_MASK
        if cmd == pyembroidery.STITCH:
            cur += 1
        elif cmd == pyembroidery.COLOR_CHANGE:
            blocks.append(cur)
            cur = 0
    blocks.append(cur)
    names = [t.description for t in p.threadlist]
    print("sew order (block: stitches, cone):")
    for i, n in enumerate(blocks):
        cone = names[i] if i < len(names) else "?"
        print(f"  {i + 1}: {n:6d}  {cone}")
    xs = [s[0] for s in p.stitches]
    ys = [s[1] for s in p.stitches]
    print(f"extent: {(max(xs) - min(xs)) / 10:.1f} x {(max(ys) - min(ys)) / 10:.1f} mm")
    if a.near:
        mx, my = (v * 10 for v in a.near)
        r = a.radius * 10
        hit = sum(1 for s in p.stitches
                  if (s[0] - mx) ** 2 + (s[1] - my) ** 2 <= r * r)
        print(f"stitches within {a.radius}mm of ({a.near[0]},{a.near[1]})mm: {hit}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("preprocess")
    p.add_argument("image")
    p.add_argument("--width-mm", type=float, required=True)
    p.add_argument("--colors", type=int, default=None)
    p.add_argument("--category", default=None)
    p.add_argument("--chart", default="madeira-polyneon")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_preprocess)

    p = sub.add_parser("window")
    p.add_argument("png")
    p.add_argument("x0", type=int)
    p.add_argument("y0", type=int)
    p.add_argument("x1", type=int)
    p.add_argument("y1", type=int)
    p.add_argument("--dark-below", type=int, default=300)
    p.add_argument("--save", default=None)
    p.set_defaults(fn=cmd_window)

    p = sub.add_parser("group")
    p.add_argument("svg")
    p.add_argument("--id", default=None)
    p.add_argument("--index", type=int, default=-1)
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--bg", default="#ffffff")
    p.set_defaults(fn=cmd_group)

    p = sub.add_parser("vp3")
    p.add_argument("file")
    p.add_argument("--near", type=float, nargs=2, default=None)
    p.add_argument("--radius", type=float, default=8.0)
    p.set_defaults(fn=cmd_vp3)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
