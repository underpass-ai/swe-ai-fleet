"""Tests for Ray Executor Service."""

import sys
from pathlib import Path

# Add services/ray_executor to Python path for test imports
# This allows pytest to properly import test modules when running from project root
_ray_executor_dir = Path(__file__).parent.parent
if str(_ray_executor_dir) not in sys.path:
    sys.path.insert(0, str(_ray_executor_dir))

