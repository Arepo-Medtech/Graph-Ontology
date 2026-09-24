#!/usr/bin/env bash
# One rebuild, every guard: stops at the first failure. Sources are prepared by the scripts listed in
# docs/multigraph-build.md (Rebuild); this runs the build and everything that checks it.
#   scripts/rebuild.sh                 # ~10 min
#   scripts/rebuild.sh --allow-missing NAME   # passed to build_edges.py
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY scripts/build_edges.py "$@"      # refuses if a source is missing; validates every edge against the register
$PY scripts/graph_report.py         # earns the tiers, applies hand-check rejections, writes out/graph_report.json
$PY scripts/consistency.py          # equivalence clusters and one-to-one conflicts -> out/consistency.json
$PY scripts/completeness.py         # completeness by group; exits 1 if a cell's share fell
$PY scripts/release_guard.py        # edge / node / conflict / island limits; exits 1 if one broke
echo "rebuild: every guard passed"
