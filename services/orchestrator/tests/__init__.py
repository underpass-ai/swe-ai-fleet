"""Tests for orchestrator service."""

import sys
from pathlib import Path

# Add services/orchestrator to Python path for test imports
# This allows pytest to properly import test modules when running from project root
_orchestrator_dir = Path(__file__).parent.parent
if str(_orchestrator_dir) not in sys.path:
    sys.path.insert(0, str(_orchestrator_dir))
