"""Tests for monitoring service."""

import sys
from pathlib import Path

# Add services/monitoring to Python path for test imports
# This allows pytest to properly import test modules when running from project root
_monitoring_dir = Path(__file__).parent.parent
if str(_monitoring_dir) not in sys.path:
    sys.path.insert(0, str(_monitoring_dir))
