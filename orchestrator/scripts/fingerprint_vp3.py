#!/usr/bin/env python3
"""Build per-category statistical fingerprints from the ground-truth production VP3s and
write them to `data/category_profiles.json` (read by step 7 to flag drift).

    .venv/bin/python orchestrator/scripts/fingerprint_vp3.py         # rebuild + print

Scans each category dir for *.vp3 (excluding any */output/ = pipeline-produced files), so it
only ever learns from the user's real production files. Re-run whenever ground-truth is added.
Feature extraction + aggregation live in wilcom_pipeline.fingerprint (shared with verify)."""
import glob
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import pyembroidery as pe  # noqa: E402
from wilcom_pipeline.fingerprint import (  # noqa: E402
    CATEGORIES, PROFILES_PATH, aggregate, features_from_pattern,
)


def collect(cat: str) -> list[dict]:
    rows = []
    seen = set()
    for pat in (f"{cat}/**/*.vp3", f"{cat}/**/*.VP3"):
        for path in glob.glob(str(REPO / pat), recursive=True):
            if "/output/" in path or path in seen:
                continue
            seen.add(path)
            try:
                p = pe.read(path)
                rows.append(features_from_pattern(p.stitches, p.threadlist))
            except Exception as exc:  # a corrupt/odd file shouldn't sink the batch
                print(f"  !! skip {path}: {type(exc).__name__}: {exc}", file=sys.stderr)
    return rows


def main() -> int:
    profiles = {}
    for cat in CATEGORIES:
        rows = collect(cat)
        profiles[cat] = aggregate(rows) if rows else {"n_files": 0}
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2))

    def med(cat, k):
        a = profiles[cat].get(k)
        return "  —" if not a else f"{a['med']:g}"

    print(f"wrote {PROFILES_PATH.relative_to(REPO)}\n")
    print(f"{'category':<14}{'files':>6}{'colors':>7}{'satin%':>7}{'fill%':>6}"
          f"{'satinW':>7}{'density':>8}{'longmm':>7}")
    for cat in CATEGORIES:
        p = profiles[cat]
        if not p.get("n_files"):
            print(f"{cat:<14}{0:>6}   (no ground-truth files)")
            continue
        print(f"{cat:<14}{p['n_files']:>6}{med(cat,'n_colors'):>7}{med(cat,'satin_frac'):>7}"
              f"{med(cat,'fill_frac'):>6}{med(cat,'satin_w_mm'):>7}{med(cat,'density'):>8}"
              f"{med(cat,'longest_mm'):>7}")
    print("\n(median across each category's ground-truth files; p25–p75 in the JSON)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
