"""Pytest fixtures for planning_ceremony_processor tests."""

import os

import pytest


@pytest.fixture(scope="session")
def ceremonies_dir() -> str:
    """Provide ceremonies directory from CEREMONIES_DIR env (injected by test harness).

    The path is injected via config/env (e.g. make test-module exports it).
    Use 'make test-module MODULE=services/planning_ceremony_processor' or set
    CEREMONIES_DIR to <repo_root>/config/ceremonies when running tests manually.
    """
    path = os.getenv("CEREMONIES_DIR", "").strip()
    if not path:
        raise ValueError(
            "CEREMONIES_DIR must be set for planning_ceremony_processor tests. "
            "Use 'make test-module MODULE=services/planning_ceremony_processor' "
            "or set CEREMONIES_DIR to <repo_root>/config/ceremonies."
        )
    return path
