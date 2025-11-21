"""Unit tests for EnvironmentConfigurationAdapter."""

import os
from unittest.mock import patch

from planning.infrastructure.adapters.environment_config_adapter import (
    EnvironmentConfigurationAdapter,
)


def test_get_neo4j_uri_default():
    """Test get_neo4j_uri returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_neo4j_uri() == "bolt://neo4j:7687"


def test_get_neo4j_uri_from_env():
    """Test get_neo4j_uri reads from environment."""
    with patch.dict(os.environ, {"NEO4J_URI": "bolt://custom:7687"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_neo4j_uri() == "bolt://custom:7687"


def test_get_neo4j_user_default():
    """Test get_neo4j_user returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_neo4j_user() == "neo4j"


def test_get_neo4j_password_default():
    """Test get_neo4j_password returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_neo4j_password() == "password"


def test_get_neo4j_database_none():
    """Test get_neo4j_database returns None when not set."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_neo4j_database() is None


def test_get_neo4j_database_from_env():
    """Test get_neo4j_database reads from environment."""
    with patch.dict(os.environ, {"NEO4J_DATABASE": "testdb"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_neo4j_database() == "testdb"


def test_get_valkey_host_default():
    """Test get_valkey_host returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_valkey_host() == "valkey"


def test_get_valkey_port_default():
    """Test get_valkey_port returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_valkey_port() == 6379


def test_get_valkey_port_from_env():
    """Test get_valkey_port reads from environment."""
    with patch.dict(os.environ, {"VALKEY_PORT": "6380"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_valkey_port() == 6380


def test_get_valkey_db_default():
    """Test get_valkey_db returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_valkey_db() == 0


def test_get_nats_url_default():
    """Test get_nats_url returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_nats_url() == "nats://nats:4222"


def test_get_grpc_port_default():
    """Test get_grpc_port returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_grpc_port() == 50054


def test_get_grpc_port_from_env():
    """Test get_grpc_port reads from environment."""
    with patch.dict(os.environ, {"GRPC_PORT": "50055"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_grpc_port() == 50055


def test_all_config_methods_available():
    """Test that all required configuration methods exist."""
    config = EnvironmentConfigurationAdapter()

    # Verify all methods exist
    assert hasattr(config, 'get_neo4j_uri')
    assert hasattr(config, 'get_neo4j_user')
    assert hasattr(config, 'get_neo4j_password')
    assert hasattr(config, 'get_neo4j_database')
    assert hasattr(config, 'get_valkey_host')
    assert hasattr(config, 'get_valkey_port')
    assert hasattr(config, 'get_valkey_db')
    assert hasattr(config, 'get_nats_url')
    assert hasattr(config, 'get_grpc_port')

