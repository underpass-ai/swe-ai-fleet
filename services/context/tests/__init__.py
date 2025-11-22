"""Tests for Context Service."""

import sys
from pathlib import Path

# Add services/context to Python path for test imports
# This allows pytest to properly import test modules when running from project root
_context_dir = Path(__file__).parent.parent
if str(_context_dir) not in sys.path:
    sys.path.insert(0, str(_context_dir))
