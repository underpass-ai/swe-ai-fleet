"""
Workflow Orchestration Service - Test Suite.

Implements comprehensive testing for RBAC Level 2:
- Unit tests: Domain, Application, Infrastructure
- Integration tests: Neo4j, Valkey, NATS
- E2E tests: Complete workflow flows

Target coverage: >90%
"""

import sys
from pathlib import Path

# Add services/workflow to Python path for test imports
# This allows pytest to properly import test modules when running from project root
_workflow_dir = Path(__file__).parent.parent
if str(_workflow_dir) not in sys.path:
    sys.path.insert(0, str(_workflow_dir))
