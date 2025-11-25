"""Tests for Task Derivation Service."""

import sys
from pathlib import Path

# Ensure the service root is importable regardless of the working directory.
SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

# Note: task_derivation.gen modules are mocked in tests/unit/conftest.py
# which runs BEFORE any test imports (pytest convention)

