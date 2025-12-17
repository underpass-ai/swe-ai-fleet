"""Unit tests for ServiceConfig domain value object."""

import pytest
from core.context.domain.service_config import ServiceConfig


def test_service_config_creation_with_valid_values() -> None:
    """Test that ServiceConfig can be created with valid values."""
    config = ServiceConfig(
        grpc_port="50054",
        neo4j_uri="bolt://neo4j:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        redis_host="redis",
        redis_port=6379,
        nats_url="nats://nats:4222",
        enable_nats=True,
    )

    assert config.grpc_port == "50054"
    assert config.neo4j_uri == "bolt://neo4j:7687"
    assert config.neo4j_user == "neo4j"
    assert config.neo4j_password == "secret"
    assert config.redis_host == "redis"
    assert config.redis_port == 6379
    assert config.nats_url == "nats://nats:4222"
    assert config.enable_nats is True


def test_service_config_is_immutable() -> None:
    """Test that ServiceConfig is frozen (immutable)."""
    config = ServiceConfig(
        grpc_port="50054",
        neo4j_uri="bolt://neo4j:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        redis_host="redis",
        redis_port=6379,
        nats_url="nats://nats:4222",
        enable_nats=True,
    )

    with pytest.raises(Exception):  # FrozenInstanceError
        config.grpc_port = "50055"  # type: ignore


def test_service_config_rejects_empty_grpc_port() -> None:
    """Test that ServiceConfig rejects empty gRPC port."""
    with pytest.raises(ValueError, match="gRPC port cannot be empty"):
        ServiceConfig(
            grpc_port="",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            redis_host="redis",
            redis_port=6379,
            nats_url="nats://nats:4222",
            enable_nats=True,
        )


def test_service_config_rejects_empty_neo4j_uri() -> None:
    """Test that ServiceConfig rejects empty Neo4j URI."""
    with pytest.raises(ValueError, match="Neo4j URI cannot be empty"):
        ServiceConfig(
            grpc_port="50054",
            neo4j_uri="",
            neo4j_user="neo4j",
            neo4j_password="secret",
            redis_host="redis",
            redis_port=6379,
            nats_url="nats://nats:4222",
            enable_nats=True,
        )


def test_service_config_rejects_empty_neo4j_user() -> None:
    """Test that ServiceConfig rejects empty Neo4j user."""
    with pytest.raises(ValueError, match="Neo4j user cannot be empty"):
        ServiceConfig(
            grpc_port="50054",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="",
            neo4j_password="secret",
            redis_host="redis",
            redis_port=6379,
            nats_url="nats://nats:4222",
            enable_nats=True,
        )


def test_service_config_rejects_empty_neo4j_password() -> None:
    """Test that ServiceConfig rejects empty Neo4j password."""
    with pytest.raises(ValueError, match="Neo4j password cannot be empty"):
        ServiceConfig(
            grpc_port="50054",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="",
            redis_host="redis",
            redis_port=6379,
            nats_url="nats://nats:4222",
            enable_nats=True,
        )


def test_service_config_rejects_empty_redis_host() -> None:
    """Test that ServiceConfig rejects empty Redis host."""
    with pytest.raises(ValueError, match="Redis host cannot be empty"):
        ServiceConfig(
            grpc_port="50054",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            redis_host="",
            redis_port=6379,
            nats_url="nats://nats:4222",
            enable_nats=True,
        )


def test_service_config_rejects_invalid_redis_port_zero() -> None:
    """Test that ServiceConfig rejects Redis port 0."""
    with pytest.raises(ValueError, match="Redis port must be between 1 and 65535"):
        ServiceConfig(
            grpc_port="50054",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            redis_host="redis",
            redis_port=0,
            nats_url="nats://nats:4222",
            enable_nats=True,
        )


def test_service_config_rejects_invalid_redis_port_negative() -> None:
    """Test that ServiceConfig rejects negative Redis port."""
    with pytest.raises(ValueError, match="Redis port must be between 1 and 65535"):
        ServiceConfig(
            grpc_port="50054",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            redis_host="redis",
            redis_port=-1,
            nats_url="nats://nats:4222",
            enable_nats=True,
        )


def test_service_config_rejects_invalid_redis_port_too_high() -> None:
    """Test that ServiceConfig rejects Redis port above 65535."""
    with pytest.raises(ValueError, match="Redis port must be between 1 and 65535"):
        ServiceConfig(
            grpc_port="50054",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            redis_host="redis",
            redis_port=65536,
            nats_url="nats://nats:4222",
            enable_nats=True,
        )


def test_service_config_rejects_empty_nats_url() -> None:
    """Test that ServiceConfig rejects empty NATS URL."""
    with pytest.raises(ValueError, match="NATS URL cannot be empty"):
        ServiceConfig(
            grpc_port="50054",
            neo4j_uri="bolt://neo4j:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            redis_host="redis",
            redis_port=6379,
            nats_url="",
            enable_nats=True,
        )


def test_service_config_redis_url_property() -> None:
    """Test that redis_url property builds correct URL."""
    config = ServiceConfig(
        grpc_port="50054",
        neo4j_uri="bolt://neo4j:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        redis_host="localhost",
        redis_port=6380,
        nats_url="nats://nats:4222",
        enable_nats=True,
    )

    assert config.redis_url == "redis://localhost:6380/0"


def test_service_config_with_nats_disabled() -> None:
    """Test that ServiceConfig works with NATS disabled."""
    config = ServiceConfig(
        grpc_port="50054",
        neo4j_uri="bolt://neo4j:7687",
        neo4j_user="neo4j",
        neo4j_password="secret",
        redis_host="redis",
        redis_port=6379,
        nats_url="nats://nats:4222",
        enable_nats=False,
    )

    assert config.enable_nats is False


def test_service_config_with_custom_values() -> None:
    """Test that ServiceConfig works with custom non-default values."""
    config = ServiceConfig(
        grpc_port="50060",
        neo4j_uri="bolt://custom-neo4j:7688",
        neo4j_user="admin",
        neo4j_password="complex-password-123",
        redis_host="custom-redis",
        redis_port=7379,
        nats_url="nats://custom-nats:5222",
        enable_nats=True,
    )

    assert config.grpc_port == "50060"
    assert config.neo4j_uri == "bolt://custom-neo4j:7688"
    assert config.neo4j_user == "admin"
    assert config.neo4j_password == "complex-password-123"
    assert config.redis_host == "custom-redis"
    assert config.redis_port == 7379
    assert config.nats_url == "nats://custom-nats:5222"
    assert config.redis_url == "redis://custom-redis:7379/0"
