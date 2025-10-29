"""
Fixtures for Context Service E2E tests.

These tests require:
- Context Service running in cluster (context.swe-ai-fleet.svc.cluster.local:50054)
- Neo4j running (neo4j.swe-ai-fleet.svc.cluster.local:7687)
- Redis/Valkey running (valkey.swe-ai-fleet.svc.cluster.local:6379)
"""

import os

import grpc
import pytest
from neo4j import GraphDatabase


@pytest.fixture(scope="module")
def context_host():
    """Get Context Service host."""
    return os.getenv("CONTEXT_HOST", "localhost")


@pytest.fixture(scope="module")
def context_port():
    """Get Context Service port."""
    return int(os.getenv("CONTEXT_PORT", "50054"))


@pytest.fixture(scope="module")
def context_channel(context_host, context_port):
    """Create gRPC channel to Context Service in cluster."""
    address = f"{context_host}:{context_port}"
    channel = grpc.insecure_channel(address)

    # Wait for service to be ready
    try:
        grpc.channel_ready_future(channel).result(timeout=5)
    except Exception:
        pytest.skip(
            f"Context Service not available at {address}. "
            f"Run: kubectl port-forward -n swe-ai-fleet svc/context 50054:50054"
        )

    yield channel
    channel.close()


@pytest.fixture(scope="module")
def context_stub(context_channel):
    """Create Context Service gRPC stub."""
    from services.context.gen import context_pb2_grpc

    return context_pb2_grpc.ContextServiceStub(context_channel)


@pytest.fixture(scope="module")
def neo4j_client():
    """Create Neo4j client for direct database access."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        # Test connection
        driver.verify_connectivity()
        yield driver
        driver.close()
    except Exception as e:
        pytest.skip(f"Neo4j not available at {uri}: {e}")


@pytest.fixture(scope="module")
def redis_client():
    """Create Redis/Valkey client for direct cache access."""
    try:
        import redis

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD")

        client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
        )
        # Test connection
        client.ping()
        yield client
        client.close()
    except Exception as e:
        pytest.skip(f"Redis/Valkey not available at {host}:{port}: {e}")


@pytest.fixture
def seed_case_data(neo4j_client, redis_client):
    """Seed test data (case, decisions, subtasks) and return case ID."""
    import json
    import time

    case_id = f"E2E-TEST-{int(time.time())}"

    # Seed Neo4j with case node
    with neo4j_client.session() as session:
        session.run(
            """
            MERGE (c:Case {id: $case_id})
            SET c.title = "Test Case for E2E",
                c.phase = "BUILD",
                c.status = "ACTIVE",
                c.created_at = datetime()
            RETURN c.id as id
            """,
            case_id=case_id,
        )

    # Seed Redis with case header
    redis_client.set(
        f"swe:case:{case_id}:header",
        json.dumps({
            "case_id": case_id,
            "title": "Test Case for E2E",
            "phase": "BUILD",
        }),
    )

    yield case_id

    # Cleanup (optional - tests might want to inspect data)
    # with neo4j_client.session() as session:
    #     session.run("MATCH (n {id: $case_id}) DETACH DELETE n", case_id=case_id)


@pytest.fixture
def empty_case_id():
    """Return a non-existent case ID for negative testing."""
    return "NONEXISTENT-CASE-999"

