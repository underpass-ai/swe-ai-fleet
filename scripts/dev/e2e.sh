#!/usr/bin/env bash
set -euo pipefail

# For now, run the PoC CLI (cluster-from-yaml) in dry-run mode.
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi
source .venv/bin/activate
pip install -U pip
pip install -e .

echo "Running PoC e2e (cluster-from-yaml) with dry-run..."
swe_ai_fleet-e2e --spec examples/cluster_from_yaml/input.yaml --dry-run

echo "Note: This is a legacy PoC. Full agile multi-agente e2e will replace this."
