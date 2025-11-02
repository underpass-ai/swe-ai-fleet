"""Pytest configuration for Planning Service tests."""



def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real infrastructure)"
    )

