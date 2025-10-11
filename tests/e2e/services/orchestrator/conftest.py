"""
Fixtures for Orchestrator Service E2E tests.
Tests assume services are running via docker-compose.e2e.yml.
"""

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


@pytest.fixture(scope="module", autouse=True)
def seed_councils(orchestrator_stub):
    """Create test councils with mock agents for all roles used in testing.
    
    This fixture auto-runs once per session and creates councils for:
    - DEV (for most tests)
    - QA (for quality tests)
    - ARCHITECT (for architecture tests)
    - DATA (for specialized tests)
    """
    from services.orchestrator.gen import orchestrator_pb2
    
    councils_created = []
    
    # Create councils for all roles used in tests
    roles = ["DEV", "QA", "ARCHITECT", "DATA", "DEVOPS"]
    
    for role in roles:
        council_request = orchestrator_pb2.CreateCouncilRequest(
            role=role,
            num_agents=3,
        )
        
        try:
            response = orchestrator_stub.CreateCouncil(council_request)
            councils_created.append((role, response.council_id))
            print(f"✓ Created council for {role}: {response.council_id}")
        except grpc.RpcError as e:
            # ALREADY_EXISTS is OK (councils persist across test modules)
            if e.code() == grpc.StatusCode.ALREADY_EXISTS:
                councils_created.append((role, f"council-{role.lower()}"))
                print(f"→ Council for {role} already exists (reusing)")
            else:
                print(f"✗ Failed to create council for {role}: {e}")
    
    yield councils_created
    
    # Cleanup not needed - councils are in-memory only


@pytest.fixture(scope="function")
def empty_task_id():
    """Return a task ID that doesn't exist (for error testing)."""
    return "NONEXISTENT-TASK-999999"

