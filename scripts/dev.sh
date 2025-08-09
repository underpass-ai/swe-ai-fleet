#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
pip install -U pip
echo "TODO: install dev dependencies"
echo "Dev environment ready."
