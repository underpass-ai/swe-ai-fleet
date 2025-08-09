#!/usr/bin/env bash
set -euo pipefail
# For now, just run the CLI with dry-run; later integrate KinD + kubectl apply --dry-run=server.
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi
source .venv/bin/activate
pip install -U pip
pip install -e .
edgecrew-e2e --spec specs/cluster-from-yaml-example.yaml --dry-run

#!/usr/bin/env bash
set -euo pipefail
echo "TODO: create KinD cluster and run end-to-end smoke tests"
