"""
Configuration for Orchestrator integration tests.
Supports both Docker and Podman.
"""

import os
import subprocess
import sys

import pytest


def detect_container_runtime():
    """Detect which container runtime is available (Docker or Podman)."""
    # Check for Podman first (since user prefers it)
    try:
        subprocess.run(
            ["podman", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return "podman"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Check for Docker
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return "docker"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return None


def is_container_runtime_available():
    """Check if any container runtime (Docker or Podman) is available."""
    return detect_container_runtime() is not None


def get_container_command():
    """Get the container runtime command (docker or podman)."""
    runtime = detect_container_runtime()
    return runtime if runtime else "docker"


def is_image_available(image_name):
    """Check if container image exists."""
    cmd = get_container_command()
    try:
        result = subprocess.run(
            [cmd, "images", "-q", image_name],
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def pytest_configure(config):
    """Configure pytest for integration tests."""
    # Detect container runtime and set environment for Testcontainers
    runtime = detect_container_runtime()
    if runtime == "podman":
        # Configure Testcontainers to use Podman
        os.environ["DOCKER_HOST"] = "unix:///run/podman/podman.sock"
        os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"  # Ryuk doesn't work well with Podman
        print(f"\n🐳 Using Podman as container runtime")
    elif runtime == "docker":
        print(f"\n🐳 Using Docker as container runtime")
    
    # Add marker for integration tests
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring container runtime (Docker/Podman)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if container runtime is not available."""
    runtime = detect_container_runtime()
    
    if not runtime:
        skip_runtime = pytest.mark.skip(
            reason="No container runtime available. Install Docker or Podman."
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_runtime)
        return
    
    # Check if the orchestrator image is available
    image_name = "localhost:5000/swe-ai-fleet/orchestrator:latest"
    if not is_image_available(image_name):
        cmd = get_container_command()
        skip_image = pytest.mark.skip(
            reason=f"Container image '{image_name}' not found. "
                   f"Build it with: {cmd} build -t {image_name} "
                   f"-f services/orchestrator/Dockerfile ."
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_image)

