"""Tests for Planning Service."""

import sys
from pathlib import Path

# Add services/planning to Python path for test imports
# This allows pytest to properly import test modules when running from project root
_planning_dir = Path(__file__).parent.parent
if str(_planning_dir) not in sys.path:
    sys.path.insert(0, str(_planning_dir))
