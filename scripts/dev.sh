#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .

echo "Dev env ready. Example PoC (cluster-from-yaml):"
echo "  swe_ai_fleet-e2e --spec examples/cluster_from_yaml/input.yaml --dry-run"
