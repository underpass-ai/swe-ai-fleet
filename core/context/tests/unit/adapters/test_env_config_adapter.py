"""Unit tests for EnvironmentConfigAdapter."""

import os
from unittest.mock import patch

import pytest
from core.context.adapters.env_config_adapter import EnvironmentConfigAdapter
from core.context.domain.service_config import ServiceConfig


@pytest.fixture
def adapter() -> EnvironmentConfigAdapter:
    """Create EnvironmentConfigAdapter instance."""
    return EnvironmentConfigAdapter()


def test_load_config_with_all_defaults(adapter: EnvironmentConfigAdapter) -> None:
    """Test loading config with default values (only password required)."""
    env_vars = {
        "NEO4J_PASSWORD": "test-password",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert isinstance(config, ServiceConfig)
    assert config.grpc_port == "50054"
    assert config.neo4j_uri == "bolt://neo4j:7687"
    assert config.neo4j_user == "neo4j"
    assert config.neo4j_password == "test-password"
    assert config.redis_host == "redis"
    assert config.redis_port == 6379
    assert config.nats_url == "nats://nats:4222"
    assert config.enable_nats is True


def test_load_config_with_custom_values(adapter: EnvironmentConfigAdapter) -> None:
    """Test loading config with custom environment values."""
    env_vars = {
        "GRPC_PORT": "50060",
        "NEO4J_URI": "bolt://custom-neo4j:7688",
        "NEO4J_USER": "admin",
        "NEO4J_PASSWORD": "secret123",
        "REDIS_HOST": "custom-redis",
        "REDIS_PORT": "7379",
        "NATS_URL": "nats://custom-nats:5222",
        "ENABLE_NATS": "true",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.grpc_port == "50060"
    assert config.neo4j_uri == "bolt://custom-neo4j:7688"
    assert config.neo4j_user == "admin"
    assert config.neo4j_password == "secret123"
    assert config.redis_host == "custom-redis"
    assert config.redis_port == 7379
    assert config.nats_url == "nats://custom-nats:5222"
    assert config.enable_nats is True


def test_load_config_fails_without_neo4j_password(adapter: EnvironmentConfigAdapter) -> None:
    """Test that loading config fails when NEO4J_PASSWORD is not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="NEO4J_PASSWORD environment variable must be set"):
            adapter.load()


def test_load_config_fails_with_empty_neo4j_password(adapter: EnvironmentConfigAdapter) -> None:
    """Test that loading config fails when NEO4J_PASSWORD is empty."""
    env_vars = {"NEO4J_PASSWORD": ""}

    with patch.dict(os.environ, env_vars, clear=True):
        with pytest.raises(ValueError, match="NEO4J_PASSWORD environment variable must be set"):
            adapter.load()


def test_load_config_fails_with_invalid_redis_port(adapter: EnvironmentConfigAdapter) -> None:
    """Test that loading config fails when REDIS_PORT is not a valid integer."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "REDIS_PORT": "invalid",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        with pytest.raises(ValueError, match="REDIS_PORT must be a valid integer"):
            adapter.load()


def test_load_config_with_nats_disabled_false(adapter: EnvironmentConfigAdapter) -> None:
    """Test loading config with ENABLE_NATS=false.

    Note: While the adapter allows NATS to be disabled, the Context Service
    will fail-fast at startup if NATS is disabled (required for system to function).
    """
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "ENABLE_NATS": "false",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.enable_nats is False


def test_load_config_with_nats_disabled_zero(adapter: EnvironmentConfigAdapter) -> None:
    """Test loading config with ENABLE_NATS=0."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "ENABLE_NATS": "0",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.enable_nats is False


def test_load_config_with_nats_disabled_no(adapter: EnvironmentConfigAdapter) -> None:
    """Test loading config with ENABLE_NATS=no."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "ENABLE_NATS": "no",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.enable_nats is False


def test_load_config_with_nats_enabled_yes(adapter: EnvironmentConfigAdapter) -> None:
    """Test loading config with ENABLE_NATS=yes."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "ENABLE_NATS": "yes",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.enable_nats is True


def test_load_config_with_nats_enabled_one(adapter: EnvironmentConfigAdapter) -> None:
    """Test loading config with ENABLE_NATS=1."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "ENABLE_NATS": "1",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.enable_nats is True


def test_load_config_with_nats_enabled_on(adapter: EnvironmentConfigAdapter) -> None:
    """Test loading config with ENABLE_NATS=on."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "ENABLE_NATS": "on",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.enable_nats is True


def test_load_config_with_nats_enabled_case_insensitive(adapter: EnvironmentConfigAdapter) -> None:
    """Test that ENABLE_NATS is case insensitive."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "ENABLE_NATS": "TRUE",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.enable_nats is True


def test_load_config_validates_redis_port_range(adapter: EnvironmentConfigAdapter) -> None:
    """Test that ServiceConfig validation is triggered for invalid port range."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "REDIS_PORT": "0",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        with pytest.raises(ValueError, match="Redis port must be between 1 and 65535"):
            adapter.load()


def test_load_config_validates_redis_port_too_high(adapter: EnvironmentConfigAdapter) -> None:
    """Test that ServiceConfig validation is triggered for port above 65535."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "REDIS_PORT": "70000",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        with pytest.raises(ValueError, match="Redis port must be between 1 and 65535"):
            adapter.load()


def test_load_config_returns_immutable_object(adapter: EnvironmentConfigAdapter) -> None:
    """Test that loaded config is immutable (frozen dataclass)."""
    env_vars = {"NEO4J_PASSWORD": "secret"}

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    with pytest.raises(Exception):  # FrozenInstanceError
        config.grpc_port = "50055"  # type: ignore


def test_load_config_redis_url_property(adapter: EnvironmentConfigAdapter) -> None:
    """Test that loaded config has correct redis_url property."""
    env_vars = {
        "NEO4J_PASSWORD": "secret",
        "REDIS_HOST": "my-redis",
        "REDIS_PORT": "7000",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = adapter.load()

    assert config.redis_url == "redis://my-redis:7000/0"


def test_adapter_implements_config_port(adapter: EnvironmentConfigAdapter) -> None:
    """Test that adapter has load method (implements ConfigPort protocol)."""
    assert hasattr(adapter, "load")
    assert callable(adapter.load)


def test_multiple_loads_return_independent_configs(adapter: EnvironmentConfigAdapter) -> None:
    """Test that multiple loads with different env vars return different configs."""
    env_vars_1 = {
        "NEO4J_PASSWORD": "password1",
        "GRPC_PORT": "50054",
    }
    env_vars_2 = {
        "NEO4J_PASSWORD": "password2",
        "GRPC_PORT": "50055",
    }

    with patch.dict(os.environ, env_vars_1, clear=True):
        config1 = adapter.load()

    with patch.dict(os.environ, env_vars_2, clear=True):
        config2 = adapter.load()

    assert config1.neo4j_password == "password1"
    assert config1.grpc_port == "50054"
    assert config2.neo4j_password == "password2"
    assert config2.grpc_port == "50055"
