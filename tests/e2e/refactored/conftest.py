"""Pytest fixtures for refactored e2e tests."""

import os

import pytest
import pytest_asyncio
from tests.e2e.refactored.adapters.grpc_context_adapter import GrpcContextAdapter
from tests.e2e.refactored.adapters.grpc_orchestrator_adapter import GrpcOrchestratorAdapter
from tests.e2e.refactored.adapters.neo4j_validator_adapter import Neo4jValidatorAdapter
from tests.e2e.refactored.adapters.valkey_validator_adapter import ValkeyValidatorAdapter


@pytest.fixture(scope="session")
def context_service_url() -> str:
    """Get Context Service gRPC URL from environment."""
    return os.getenv("CONTEXT_SERVICE_URL", "localhost:50054")


@pytest.fixture(scope="session")
def orchestrator_service_url() -> str:
    """Get Orchestrator Service gRPC URL from environment."""
    return os.getenv("ORCHESTRATOR_SERVICE_URL", "localhost:50055")


@pytest.fixture(scope="session")
def neo4j_uri() -> str:
    """Get Neo4j URI from environment."""
    return os.getenv("NEO4J_URI", "bolt://localhost:7687")


@pytest.fixture(scope="session")
def neo4j_username() -> str:
    """Get Neo4j username from environment."""
    return os.getenv("NEO4J_USERNAME", "neo4j")


@pytest.fixture(scope="session")
def neo4j_password() -> str:
    """Get Neo4j password from environment."""
    return os.getenv("NEO4J_PASSWORD", "testpassword")


@pytest.fixture(scope="session")
def valkey_host() -> str:
    """Get Valkey host from environment."""
    return os.getenv("VALKEY_HOST", "localhost")


@pytest.fixture(scope="session")
def valkey_port() -> int:
    """Get Valkey port from environment."""
    return int(os.getenv("VALKEY_PORT", "6379"))


@pytest_asyncio.fixture
async def context_client(context_service_url: str) -> GrpcContextAdapter:
    """Create and connect Context Service client."""
    client = GrpcContextAdapter(context_service_url)
    await client.connect()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def orchestrator_client(orchestrator_service_url: str) -> GrpcOrchestratorAdapter:
    """Create and connect Orchestrator Service client."""
    client = GrpcOrchestratorAdapter(orchestrator_service_url)
    await client.connect()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def neo4j_validator(
    neo4j_uri: str,
    neo4j_username: str,
    neo4j_password: str
) -> Neo4jValidatorAdapter:
    """Create and connect Neo4j validator."""
    validator = Neo4jValidatorAdapter(neo4j_uri, neo4j_username, neo4j_password)
    await validator.connect()
    yield validator
    await validator.close()


@pytest_asyncio.fixture
async def valkey_validator(valkey_host: str, valkey_port: int) -> ValkeyValidatorAdapter:
    """Create and connect Valkey validator."""
    validator = ValkeyValidatorAdapter(valkey_host, valkey_port)
    await validator.connect()
    yield validator
    await validator.close()

