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


def test_get_neo4j_password_default_logs_warning(caplog):
    """Test get_neo4j_password logs warning when using default password."""
    import logging

    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        with caplog.at_level(logging.WARNING):
            config.get_neo4j_password()
    assert "default" in caplog.text.lower() and "production" in caplog.text.lower()


def test_get_neo4j_password_from_env_no_warning(caplog):
    """Test get_neo4j_password does not log warning when env is set."""
    import logging

    with patch.dict(os.environ, {"NEO4J_PASSWORD": "secret"}):
        config = EnvironmentConfigurationAdapter()
        with caplog.at_level(logging.WARNING):
            result = config.get_neo4j_password()
        assert result == "secret"
    assert "default" not in caplog.text and "production" not in caplog.text


def test_get_planning_ceremony_processor_url_none_when_unset():
    """Test get_planning_ceremony_processor_url returns None when not set."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_planning_ceremony_processor_url() is None


def test_get_planning_ceremony_processor_url_none_when_empty_string():
    """Test get_planning_ceremony_processor_url returns None when empty string."""
    with patch.dict(os.environ, {"PLANNING_CEREMONY_PROCESSOR_URL": ""}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_planning_ceremony_processor_url() is None


def test_get_planning_ceremony_processor_url_none_when_whitespace_only():
    """Test get_planning_ceremony_processor_url returns None when whitespace only."""
    with patch.dict(os.environ, {"PLANNING_CEREMONY_PROCESSOR_URL": "   "}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_planning_ceremony_processor_url() is None


def test_get_planning_ceremony_processor_url_from_env():
    """Test get_planning_ceremony_processor_url returns value from environment."""
    with patch.dict(os.environ, {"PLANNING_CEREMONY_PROCESSOR_URL": "pcp:50060"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_planning_ceremony_processor_url() == "pcp:50060"


def test_get_planning_ceremony_processor_url_strips_whitespace():
    """Test get_planning_ceremony_processor_url returns stripped value."""
    with patch.dict(os.environ, {"PLANNING_CEREMONY_PROCESSOR_URL": "  pcp:50060  "}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_planning_ceremony_processor_url() == "pcp:50060"


def test_get_ray_executor_url_default():
    """Test get_ray_executor_url returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_ray_executor_url() == "ray-executor:50055"


def test_get_ray_executor_url_from_env():
    """Test get_ray_executor_url reads from environment."""
    with patch.dict(os.environ, {"RAY_EXECUTOR_URL": "ray:50060"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_ray_executor_url() == "ray:50060"


def test_get_vllm_url_default():
    """Test get_vllm_url returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_vllm_url() == "http://vllm:8000"


def test_get_vllm_url_from_env():
    """Test get_vllm_url reads from environment."""
    with patch.dict(os.environ, {"VLLM_URL": "http://custom:8001"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_vllm_url() == "http://custom:8001"


def test_get_vllm_model_default():
    """Test get_vllm_model returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert "Qwen" in config.get_vllm_model()


def test_get_vllm_model_from_env():
    """Test get_vllm_model reads from environment."""
    with patch.dict(os.environ, {"VLLM_MODEL": "custom/model"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_vllm_model() == "custom/model"


def test_get_context_service_url_default():
    """Test get_context_service_url returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_context_service_url() == "context:50054"


def test_get_context_service_url_from_env():
    """Test get_context_service_url reads from environment."""
    with patch.dict(os.environ, {"CONTEXT_SERVICE_URL": "ctx:50055"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_context_service_url() == "ctx:50055"


def test_get_task_derivation_config_path_default():
    """Test get_task_derivation_config_path returns default value."""
    with patch.dict(os.environ, {}, clear=True):
        config = EnvironmentConfigurationAdapter()
        assert config.get_task_derivation_config_path() == "config/task_derivation.yaml"


def test_get_task_derivation_config_path_from_env():
    """Test get_task_derivation_config_path reads from environment."""
    with patch.dict(os.environ, {"TASK_DERIVATION_CONFIG_PATH": "/etc/derivation.yaml"}):
        config = EnvironmentConfigurationAdapter()
        assert config.get_task_derivation_config_path() == "/etc/derivation.yaml"


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
    assert hasattr(config, 'get_ray_executor_url')
    assert hasattr(config, 'get_vllm_url')
    assert hasattr(config, 'get_vllm_model')
    assert hasattr(config, 'get_context_service_url')
    assert hasattr(config, 'get_task_derivation_config_path')
    assert hasattr(config, 'get_planning_ceremony_processor_url')

