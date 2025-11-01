"""
Fixtures for Orchestrator Service E2E tests.

These tests require:
- Orchestrator Service running in cluster (orchestrator.swe-ai-fleet.svc.cluster.local:50055)
"""

import time

import pytest


@pytest.fixture
def test_task_id():
    """Generate unique task ID for each test."""
    return f"test-task-{int(time.time() * 1000)}"

