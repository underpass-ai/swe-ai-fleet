"""Unit tests for ServerConfigurationDTO.

Tests validation and fail-fast behavior.
"""

import pytest

from services.workflow.infrastructure.dto.server_configuration_dto import (
    ServerConfigurationDTO,
)


def test_server_configuration_dto_valid():
    """Test valid ServerConfigurationDTO creation."""
    config = ServerConfigurationDTO(
        grpc_port=50056,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password123",
        valkey_host="localhost",
        valkey_port=6379,
        nats_url="nats://localhost:4222",
        fsm_config={"states": [], "transitions": []},
    )

    assert config.grpc_port == 50056
    assert config.neo4j_uri == "bolt://localhost:7687"
    assert config.neo4j_user == "neo4j"
    assert config.neo4j_password == "password123"
    assert config.valkey_host == "localhost"
    assert config.valkey_port == 6379
    assert config.nats_url == "nats://localhost:4222"
    assert "states" in config.fsm_config


def test_server_configuration_dto_invalid_grpc_port_too_low():
    """Test that port < 1 raises ValueError."""
    with pytest.raises(ValueError, match="Invalid gRPC port"):
        ServerConfigurationDTO(
            grpc_port=0,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            valkey_host="localhost",
            valkey_port=6379,
            nats_url="nats://localhost:4222",
            fsm_config={"states": [], "transitions": []},
        )


def test_server_configuration_dto_invalid_grpc_port_too_high():
    """Test that port > 65535 raises ValueError."""
    with pytest.raises(ValueError, match="Invalid gRPC port"):
        ServerConfigurationDTO(
            grpc_port=70000,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            valkey_host="localhost",
            valkey_port=6379,
            nats_url="nats://localhost:4222",
            fsm_config={"states": [], "transitions": []},
        )


def test_server_configuration_dto_empty_neo4j_uri():
    """Test that empty neo4j_uri raises ValueError."""
    with pytest.raises(ValueError, match="neo4j_uri cannot be empty"):
        ServerConfigurationDTO(
            grpc_port=50056,
            neo4j_uri="",
            neo4j_user="neo4j",
            neo4j_password="password",
            valkey_host="localhost",
            valkey_port=6379,
            nats_url="nats://localhost:4222",
            fsm_config={"states": [], "transitions": []},
        )


def test_server_configuration_dto_empty_neo4j_password():
    """Test that empty neo4j_password raises ValueError."""
    with pytest.raises(ValueError, match="neo4j_password cannot be empty"):
        ServerConfigurationDTO(
            grpc_port=50056,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="",
            valkey_host="localhost",
            valkey_port=6379,
            nats_url="nats://localhost:4222",
            fsm_config={"states": [], "transitions": []},
        )


def test_server_configuration_dto_empty_nats_url():
    """Test that empty nats_url raises ValueError."""
    with pytest.raises(ValueError, match="nats_url cannot be empty"):
        ServerConfigurationDTO(
            grpc_port=50056,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            valkey_host="localhost",
            valkey_port=6379,
            nats_url="",
            fsm_config={"states": [], "transitions": []},
        )


def test_server_configuration_dto_invalid_valkey_port():
    """Test that invalid Valkey port raises ValueError."""
    with pytest.raises(ValueError, match="Invalid Valkey port"):
        ServerConfigurationDTO(
            grpc_port=50056,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            valkey_host="localhost",
            valkey_port=0,
            nats_url="nats://localhost:4222",
            fsm_config={"states": [], "transitions": []},
        )


def test_server_configuration_dto_empty_fsm_config():
    """Test that empty fsm_config raises ValueError."""
    with pytest.raises(ValueError, match="fsm_config cannot be empty"):
        ServerConfigurationDTO(
            grpc_port=50056,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            valkey_host="localhost",
            valkey_port=6379,
            nats_url="nats://localhost:4222",
            fsm_config={},
        )


def test_server_configuration_dto_missing_fsm_states_key():
    """Test that fsm_config without 'states' raises ValueError."""
    with pytest.raises(ValueError, match="FSM config missing required key: states"):
        ServerConfigurationDTO(
            grpc_port=50056,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            valkey_host="localhost",
            valkey_port=6379,
            nats_url="nats://localhost:4222",
            fsm_config={"transitions": []},
        )


def test_server_configuration_dto_missing_fsm_transitions_key():
    """Test that fsm_config without 'transitions' raises ValueError."""
    with pytest.raises(ValueError, match="FSM config missing required key: transitions"):
        ServerConfigurationDTO(
            grpc_port=50056,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            valkey_host="localhost",
            valkey_port=6379,
            nats_url="nats://localhost:4222",
            fsm_config={"states": []},
        )


def test_server_configuration_dto_immutable():
    """Test that ServerConfigurationDTO is immutable (frozen=True)."""
    config = ServerConfigurationDTO(
        grpc_port=50056,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        valkey_host="localhost",
        valkey_port=6379,
        nats_url="nats://localhost:4222",
        fsm_config={"states": [], "transitions": []},
    )

    with pytest.raises(AttributeError):
        config.grpc_port = 9999  # type: ignore

