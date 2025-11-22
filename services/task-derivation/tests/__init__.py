"""Tests for Task Derivation Service."""

import sys
from pathlib import Path

# Add services/task-derivation to Python path for test imports
# This allows pytest to properly import test modules when running from project root
_task_derivation_dir = Path(__file__).parent.parent
if str(_task_derivation_dir) not in sys.path:
    sys.path.insert(0, str(_task_derivation_dir))

