#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
echo "Dev env ready. Run: edgecrew-e2e --spec specs/cluster-from-yaml-example.yaml --dry-run"

#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
pip install -U pip
echo "TODO: install dev dependencies"
echo "Dev environment ready."
