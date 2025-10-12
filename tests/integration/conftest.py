"""
Global conftest for integration tests.

Integration tests require Docker/Podman with services running.
Tests that fail to import due to missing generated code (services.*.gen)
should be skipped gracefully.
"""
import pytest


def pytest_ignore_collect(collection_path, config):
    """
    Ignore test files that require generated code or are archived.
    
    This runs BEFORE Python tries to import the test files, preventing
    import errors from missing generated modules.
    """
    path_str = str(collection_path)
    
    # Ignore all tests in archived/ directory (obsolete)
    if "archived" in path_str:
        return True
    
    # Ignore tests that require services.*.gen (run in Docker only)
    # These tests need protobuf code generated inside containers
    if "_e2e.py" in path_str and ("services/context" in path_str or "services/orchestrator" in path_str):
        # Check if gen modules are available
        try:
            if "services/context" in path_str:
                import services.context.gen  # noqa: F401
            elif "services/orchestrator" in path_str:
                import services.orchestrator.gen  # noqa: F401
        except (ImportError, ModuleNotFoundError):
            return True  # Ignore this file
    
    return False

