#!/usr/bin/env python3
"""Ingest production (CorelDRAW-SVG, VP3) pairs dropped in `pairs-inbox/`.

The user drops `<design>.svg` + `<design>.vp3` (matching stems, any case) into
`pairs-inbox/` — no sorting needed. For each pair this script:

  1. AUTO-CATEGORIZES it: the VP3's fingerprint (features_from_pattern) is scored
     against every category profile in data/category_profiles.json (median/IQR
     z-like distance over the production-style features). Best score under the
     threshold wins; otherwise the pair goes to pairs-inbox/unknown/ for review
     (it may be a genuinely NEW category — see the printed instructions).
  2. MOVES it to `<category>/pairs/<design>/` (the category dirs are the repo's
     knowledge homes; profiles are rebuilt from `<category>/**/*.vp3`).
  3. LABELS it: runs extract_pair.py (structure: families/colours/order) and
     register_pair.py (SVG<->VP3 registration: per-object mm widths, density,
     row spacing, satin-vs-tatami) — outputs land next to the pair.
  4. `git add -f`s the VP3 (VP3s are gitignored by default; ground truth is
     tracked deliberately) and rebuilds data/category_profiles.json.
  5. Prints the PAIRS-FINDINGS.md table row to append.

Usage:
    .venv/bin/python orchestrator/scripts/ingest_pairs.py                # ingest inbox
    .venv/bin/python orchestrator/scripts/ingest_pairs.py --dry-run     # classify only
    .venv/bin/python orchestrator/scripts/ingest_pairs.py --category arabic   # override
    .venv/bin/python orchestrator/scripts/ingest_pairs.py --classify x.vp3    # score one VP3
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import pyembroidery as pe  # noqa: E402
from wilcom_pipeline.fingerprint import (  # noqa: E402
    CATEGORIES, features_from_pattern, load_profiles,
)

INBOX = REPO / "pairs-inbox"
SCRIPTS = Path(__file__).resolve().parent

# Features used for categorization + a robustness floor per feature: with n=1..3 files a
# category's IQR collapses to ~0, so deviations are normalized by max(IQR, floor).
# Validated on 11 known ground-truth VP3s: 9/11 top-1 (the misses are inside the
# satin-dominant twin family — letters/arabic/simple-shapes/numbers share ~100% satin,
# ~2mm width, 1-2 colours, which is exactly the VP3 blind spot — and land as flagged
# near-ties; review the printed scores and move the folder if the call is wrong).
_SCORE_FEATURES = {
    "satin_frac": 12.0,   # percent points
    "fill_frac": 12.0,
    "density": 0.35,      # stitches/mm^2
    "satin_w_mm": 0.6,
    "stitch_len_mm": 0.6,
    "n_colors": 2.0,
    "trim_rate": 0.01,
    "longest_mm": 30.0,
    "aspect": 0.5,
    "n_blocks": 4.0,
    "n_stitch": 8000.0,
    "frag": 0.01,
}
_ASSIGN_MAX_SCORE = 2.0   # best score above this -> "unknown" (review; maybe a new category)
_AMBIGUOUS_MARGIN = 0.25  # runner-up this close -> flag the call as ambiguous


def vp3_features(vp3: Path) -> dict:
    p = pe.read(str(vp3))
    return features_from_pattern(p.stitches, p.threadlist)


def category_scores(feats: dict) -> list[tuple[str, float]]:
    """(category, score) sorted best-first; lower = closer to that category's ground truth."""
    profiles = load_profiles()
    out = []
    for cat in CATEGORIES:
        prof = profiles.get(cat) or {}
        if not prof.get("n_files"):
            continue
        devs = []
        for key, floor in _SCORE_FEATURES.items():
            band = prof.get(key)
            x = feats.get(key)
            if band is None or x is None:
                continue
            spread = max(float(band["p75"]) - float(band["p25"]), floor)
            devs.append(abs(float(x) - float(band["med"])) / spread)
        if devs:
            out.append((cat, sum(devs) / len(devs)))
    return sorted(out, key=lambda t: t[1])


def classify(vp3: Path) -> tuple[str | None, list[tuple[str, float]]]:
    scores = category_scores(vp3_features(vp3))
    if not scores:
        return None, scores
    best_cat, best = scores[0]
    if best > _ASSIGN_MAX_SCORE:
        return None, scores
    return best_cat, scores


def find_pairs(inbox: Path) -> tuple[list[tuple[Path, Path, Path | None]], list[Path]]:
    """Match svg+vp3 by stem (case-insensitive); a `<stem>-props.json` (authored Object
    Properties transcribed from Wilcom screenshots — the TRIO's third element) rides
    along when present. Returns (trios, unmatched files)."""
    svgs, vp3s, props = {}, {}, {}
    for f in sorted(inbox.iterdir()):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext == ".svg":
            svgs[f.stem.lower()] = f
        elif ext == ".vp3":
            vp3s[f.stem.lower()] = f
        elif ext == ".json" and f.stem.lower().endswith("-props"):
            props[f.stem.lower()[:-len("-props")]] = f
    pairs = [(svgs[k], vp3s[k], props.get(k)) for k in sorted(svgs.keys() & vp3s.keys())]
    loners = [f for k, f in sorted((svgs | vp3s).items()) if (k in svgs) != (k in vp3s)]
    return pairs, loners


def label_pair(svg: Path, vp3: Path) -> None:
    """Run extract_pair + register_pair; outputs land next to the SVG. Best-effort."""
    for script in ("extract_pair.py", "register_pair.py"):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), str(svg), str(vp3)],
                           capture_output=True, text=True)
        tail = (r.stdout or r.stderr).strip().splitlines()
        print(f"    {script}: " + (tail[-1] if tail else f"exit {r.returncode}"))


def git_track(path: Path) -> None:
    subprocess.run(["git", "-C", str(REPO), "add", "-f", str(path)], capture_output=True)


def findings_row(design: str, cat: str, pair_dir: Path) -> str:
    try:
        obj = json.loads((pair_dir / f"{design}_objects.json").read_text())
        s, v = obj["svg"], obj.get("vp3") or {}
        return (f"| {design} | {cat} | {s['n_fill_objects']} | {s['n_outline_objects']} | "
                f"{s['outline_to_fill_ratio']} | {s['n_colours']} | {v.get('longest_mm', '?')} | "
                f"{v.get('satin_frac', '?')} | {v.get('satin_w_mm', '?')} |")
    except Exception:
        return f"| {design} | {cat} | ? | ? | ? | ? | ? | ? | ? |"


def ingest(args) -> int:
    pairs, loners = find_pairs(INBOX)
    for f in loners:
        print(f"! {f.name}: no matching {'.vp3' if f.suffix.lower() == '.svg' else '.svg'} "
              f"with the same stem — skipped (a pair needs both)")
    if not pairs:
        print("pairs-inbox/ has no complete (svg, vp3) pairs.")
        return 0 if not loners else 1

    rows = []
    for svg, vp3, props in pairs:
        design = svg.stem
        print(f"\n== {design} ==")
        cat, scores = (args.category, category_scores(vp3_features(vp3))) \
            if args.category else classify(vp3)
        for c, s in scores[:3]:
            print(f"    {c:14s} score {s:.2f}")
        if cat is None:
            print(f"    -> UNKNOWN (best score above {_ASSIGN_MAX_SCORE}). This may be a NEW "
                  f"category: review the design, then either re-run with --category <cat>, or "
                  f"create the category (dir + knowledge doc, add it to config."
                  f"SUPPORTED_CATEGORIES and CATEGORY_COLORS) and re-ingest.")
            dest = INBOX / "unknown" / design
        else:
            if len(scores) > 1 and scores[1][1] - scores[0][1] < _AMBIGUOUS_MARGIN and not args.category:
                print(f"    ~ ambiguous ({scores[0][0]} vs {scores[1][0]}) — filing under "
                      f"{cat}; move manually if wrong")
            dest = REPO / cat / "pairs" / design
        print(f"    -> {dest.relative_to(REPO)}/")
        if args.dry_run:
            continue
        if dest.exists():
            print(f"    ! {dest.relative_to(REPO)} already exists — skipped (rename the files)")
            continue
        dest.mkdir(parents=True)
        svg_d = dest / (design + ".svg")
        vp3_d = dest / (design + vp3.suffix)
        shutil.move(str(svg), svg_d)
        shutil.move(str(vp3), vp3_d)
        if props is not None:
            props_d = dest / f"{design}_props.json"
            shutil.move(str(props), props_d)
            try:
                pj = json.loads(props_d.read_text())
                objs = pj.get("objects", [])
                tabs = sorted({t for o in objs for t in o.get("tabs_captured", [])})
                print(f"    props: authored settings for {len(objs)} object(s), "
                      f"tabs {'/'.join(tabs) or '-'}")
            except Exception as exc:
                print(f"    ! props file unreadable ({exc}) — kept as-is")
        label_pair(svg_d, vp3_d)
        git_track(dest)  # -f: VP3s are gitignored by default, ground truth is tracked
        if cat is not None:
            rows.append(findings_row(design, cat, dest))

    if not args.dry_run and rows:
        print("\nrebuilding data/category_profiles.json ...")
        subprocess.run([sys.executable, str(SCRIPTS / "fingerprint_vp3.py")],
                       capture_output=True)
        print("rebuilding data/pair_priors.json (steers step 5's numbers) ...")
        subprocess.run([sys.executable, str(SCRIPTS / "build_pair_priors.py")],
                       capture_output=True)
        print("append to the pairs table in PAIRS-FINDINGS.md:")
        for r in rows:
            print("  " + r)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="classify + report, move nothing")
    ap.add_argument("--category", choices=CATEGORIES, help="override auto-categorization")
    ap.add_argument("--classify", type=Path, metavar="VP3",
                    help="score one VP3 against the profiles and exit")
    args = ap.parse_args()
    if args.classify:
        for c, s in category_scores(vp3_features(args.classify))[:5]:
            print(f"{c:14s} score {s:.2f}")
        return 0
    return ingest(args)


if __name__ == "__main__":
    raise SystemExit(main())
