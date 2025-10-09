"""
Configuration for Orchestrator integration tests.
"""

import subprocess
import sys

import pytest


def is_docker_available():
    """Check if Docker is available."""
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_image_available(image_name):
    """Check if Docker image exists."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def pytest_configure(config):
    """Configure pytest for integration tests."""
    # Add marker for integration tests
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring Docker"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if Docker is not available."""
    if not is_docker_available():
        skip_docker = pytest.mark.skip(reason="Docker is not available")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_docker)
        return
    
    # Check if the orchestrator image is available
    image_name = "localhost:5000/swe-ai-fleet/orchestrator:latest"
    if not is_image_available(image_name):
        skip_image = pytest.mark.skip(
            reason=f"Docker image '{image_name}' not found. "
                   f"Build it with: docker build -t {image_name} "
                   f"-f services/orchestrator/Dockerfile ."
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_image)

