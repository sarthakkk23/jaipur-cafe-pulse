#!/usr/bin/env bash
# Rebuild aggregates and the site. Usage: ./build.sh [draft|publish]
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-draft}"
PY=.venv/bin/python
[ -x "$PY" ] || { python3 -m venv .venv && .venv/bin/pip -q install -r requirements.txt; }
"$PY" pipeline/build_insights.py
"$PY" pipeline/check_publish.py --mode "$MODE"
"$PY" pipeline/build_v2.py --mode "$MODE"
