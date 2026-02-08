#!/usr/bin/env bash
# Backward-compatible wrapper: generate protobuf files for all modules.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/protos/generate-all.sh" "$@"
