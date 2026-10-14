#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi
PYTHONPATH=src "$PYTHON" -m demand_poc.cli \
  --direct data/input/direct_sample.csv \
  --indirect data/input/indirect_sample.csv \
  --roles data/reference/role_estimates.csv \
  --snapshot-date "${1:-2026-09-25}" \
  --output-dir data/output
open data/output/dashboard.html
