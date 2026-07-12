#!/usr/bin/env python3
"""Extract OBJECT-LEVEL ground truth from a (CorelDRAW-SVG, VP3) production pair.

A .vp3 is stitch-soup (no object types). The CorelDRAW vector export of the SAME design recovers
the object STRUCTURE the .vp3 hides:
  - filled closed shapes (class "filN")      -> FILL-family objects (areas)
  - fill:none + colour stroke ("fil0 strN")  -> OUTLINE-family objects (lines/borders/detail)

What each half is trusted for (learned the hard way):
  * SVG  -> object FAMILIES, COLOURS, sew ORDER, outline:fill ratio  (scale-INDEPENDENT, reliable)
  * VP3  -> SIZE, density, satin/fill split, satin width             (in real mm, reliable)
  The SVG's own coordinates DON'T map cleanly to mm (off-page/clipping paths, aspect mismatch vs
  the VP3), so per-object widths from the SVG alone need true SVG<->VP3 registration — not done
  here. Scale-dependent numbers come from the VP3.

    python extract_pair.py pink-goku.svg pink-goku.VP3   # writes <stem>_objects.json

Feeds THIS pipeline's knowledge (priors, fingerprints, tiering), not a separate model.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import pyembroidery as pe  # noqa: E402
from wilcom_pipeline.fingerprint import features_from_pattern  # noqa: E402


def _hex(c: str) -> str:
    return "#000000" if c == "black" else c.upper()


def svg_structure(svg_path: Path) -> dict:
    svg = svg_path.read_text()
    style = {}
    for name, body in re.findall(r"\.(\w+)\s*\{([^}]*)\}", svg):
        d = style.setdefault(name, {})
        if m := re.search(r"fill:\s*([^;}\s]+)", body):
            d["fill"] = None if m.group(1) == "none" else _hex(m.group(1))
        if m := re.search(r"stroke:\s*([^;}\s]+)", body):
            d["stroke"] = _hex(m.group(1))

    fills, outlines, order = {}, {}, []
    for cls, _d in re.findall(r'<path\s+class="([^"]*)"\s+d="([^"]*)"\s*/>', svg):
        toks = cls.split()
        if toks[0] != "fil0":                                 # single filN = FILL family (area)
            colour = style.get(toks[0], {}).get("fill")
            fills.setdefault(colour, []).append(cls)
            order.append(["fill", colour])
        else:                                                  # fil0 + strN = OUTLINE family (line)
            strk = next((t for t in toks if t.startswith("str")), None)
            colour = style.get(strk, {}).get("stroke") if strk else None
            outlines.setdefault(colour, []).append(cls)
            order.append(["outline", colour])

    nfill = sum(len(v) for v in fills.values())
    noutl = sum(len(v) for v in outlines.values())
    return {
        "n_fill_objects": nfill,
        "n_outline_objects": noutl,
        "outline_to_fill_ratio": round(noutl / max(nfill, 1), 2),
        "n_colours": len({c for c in fills if c} | {c for c in outlines if c}),
        "colours": sorted({c for c in fills if c} | {c for c in outlines if c}),
        "fill_objects_by_colour": {str(c): len(v) for c, v in fills.items()},
        "outline_objects_by_colour": {str(c): len(v) for c, v in outlines.items()},
        "sew_order": order,
    }


def vp3_fingerprint(vp3_path: Path) -> dict:
    p = pe.read(str(vp3_path))
    f = features_from_pattern(p.stitches, p.threadlist)
    keep = ("longest_mm", "aspect", "n_colors", "n_stitch", "n_blocks", "density",
            "satin_frac", "fill_frac", "mixed_frac", "satin_w_mm", "stitch_len_mm", "trim_rate")
    return {k: (None if f[k] is None else round(f[k], 2)) for k in keep}


def summarise(rec: dict) -> None:
    s, v = rec["svg"], rec.get("vp3")
    print(f"\n=== {rec['design']} — object-level ground truth from the pair ===")
    print("SVG (object structure, scale-independent):")
    print(f"   {s['n_fill_objects']} FILL-family + {s['n_outline_objects']} OUTLINE-family objects"
          f"   (outline:fill = {s['outline_to_fill_ratio']} : 1)")
    print(f"   {s['n_colours']} colours   sew-order: {len(s['sew_order'])} objects")
    if v:
        print("VP3 (stitch realisation, real mm):")
        print(f"   size {v['longest_mm']}mm   density {v['density']}   {v['n_stitch']} stitches")
        print(f"   satin {v['satin_frac']}%  fill {v['fill_frac']}%  mixed {v['mixed_frac']}%"
              f"   satin width {v['satin_w_mm']}mm")


if __name__ == "__main__":
    svg = Path(sys.argv[1])
    rec = {"design": svg.stem, "svg": svg_structure(svg)}
    if len(sys.argv) > 2:
        rec["vp3"] = vp3_fingerprint(Path(sys.argv[2]))
    out = svg.with_name(svg.stem + "_objects.json")
    out.write_text(json.dumps(rec, indent=1))
    summarise(rec)
    print(f"\nwrote {out.name}")
