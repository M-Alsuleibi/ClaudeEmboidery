#!/usr/bin/env bash
# digitize.sh — canonical Phase-A wrapper for the wilcom-pipeline.
#
# Why this exists: the installed `wilcom-pipeline` console script is stale (the venv was
# built at an old path), so the supported invocation is `PYTHONPATH=src .venv/bin/python
# -m wilcom_pipeline`. This wrapper does that from the repo root and fails early with a
# clear message if the venv or the vendored Ink-Stitch binary (needed by step 5) is missing.
#
# Usage (run from anywhere; it locates the repo root relative to itself):
#   digitize.sh <photo> --width-mm 120 --colors 2 --thread-chart madeira-polyneon \
#               --purify-colors --fill-method contour_fill --name foo --output-dir output
# All arguments are passed straight through to the pipeline. See `--help` of the module
# and EMBROIDERY-PLAYBOOK.md §5a for the full flag reference.
set -euo pipefail

# Repo root = four levels up from this script (.claude/skills/photo-to-vp3/scripts/).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
    echo "error: $REPO_ROOT/.venv not found. Set up first (see README.md):" >&2
    echo "  /usr/bin/python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2
    exit 1
fi

INKSTITCH="${INKSTITCH_BIN:-vendor/inkstitch/bin/inkstitch}"
if [ ! -x "$INKSTITCH" ]; then
    echo "error: Ink-Stitch binary not found at '$INKSTITCH' (step 5 needs it)." >&2
    echo "  Vendor the Linux portable bundle per README.md, or set \$INKSTITCH_BIN." >&2
    exit 1
fi

if [ "$#" -eq 0 ]; then
    echo "usage: digitize.sh <photo> --width-mm N [flags...]   (see EMBROIDERY-PLAYBOOK.md §5a)" >&2
    exit 2
fi

echo ">> (cd $REPO_ROOT && PYTHONPATH=src $PY -m wilcom_pipeline $*)" >&2
exec env PYTHONPATH=src "$PY" -m wilcom_pipeline "$@"
