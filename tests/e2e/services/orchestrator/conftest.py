"""
Fixtures for Orchestrator Service E2E tests.
Tests assume services are running via docker-compose.e2e.yml.
"""

import json
import os
import time

import grpc
import pytest
from redis import Redis

# ============================================================================
# CLIENT FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def redis_client():
    """Create Redis client for seeding data."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = 6379 if host == "redis" else 16379
    
    client = Redis(host=host, port=port, decode_responses=True)
    
    # Wait for Redis to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            client.ping()
            break
        except Exception:
            if i == max_retries - 1:
                pytest.skip(
                    "Redis not available. Run: podman-compose -f "
                    "tests/e2e/services/orchestrator/docker-compose.e2e.yml up -d"
                )
            time.sleep(1)
    
    yield client
    client.close()


@pytest.fixture(scope="module")
def grpc_channel():
    """Create gRPC channel to Orchestrator Service."""
    host = os.getenv("ORCHESTRATOR_HOST", "localhost")
    port = 50055 if host == "orchestrator" else 50055
    
    channel = grpc.insecure_channel(f"{host}:{port}")
    
    # Wait for service to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            grpc.channel_ready_future(channel).result(timeout=1)
            break
        except Exception:
            if i == max_retries - 1:
                pytest.skip(
                    "Orchestrator Service not available. Run: podman-compose -f "
                    "tests/e2e/services/orchestrator/docker-compose.e2e.yml up -d"
                )
            time.sleep(1)
    
    yield channel
    channel.close()


@pytest.fixture(scope="module")
def orchestrator_stub(grpc_channel):
    """Create Orchestrator Service gRPC stub."""
    from services.orchestrator.gen import orchestrator_pb2_grpc
    
    return orchestrator_pb2_grpc.OrchestratorServiceStub(grpc_channel)


# ============================================================================
# DATA FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_task_id():
    """Generate unique task ID for each test."""
    import random
    return f"TEST-TASK-{random.randint(10000, 99999)}"


@pytest.fixture(scope="function")
def seed_council_data(orchestrator_stub):
    """Create a test council with mock agents for testing."""
    from services.orchestrator.gen import orchestrator_pb2
    
    # Create council for DEV role
    council_request = orchestrator_pb2.CreateCouncilRequest(
        role="DEV",
        num_agents=3,
        agent_profile="mock"  # Use mock agents for E2E tests
    )
    
    response = orchestrator_stub.CreateCouncil(council_request)
    
    yield response.council_id
    
    # Cleanup not needed - councils are in-memory only


@pytest.fixture(scope="function")
def empty_task_id():
    """Return a task ID that doesn't exist (for error testing)."""
    return "NONEXISTENT-TASK-999999"

