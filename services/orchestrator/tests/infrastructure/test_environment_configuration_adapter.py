"""Tests for EnvironmentConfigurationAdapter."""



from services.orchestrator.infrastructure.adapters import EnvironmentConfigurationAdapter


class TestEnvironmentConfigurationAdapter:
    """Test suite for EnvironmentConfigurationAdapter."""
    
    def test_get_service_configuration_defaults(self, monkeypatch):
        """Test getting service configuration with default values."""
        # Clear env vars to use defaults
        monkeypatch.delenv("GRPC_PORT", raising=False)
        monkeypatch.delenv("NATS_URL", raising=False)
        monkeypatch.delenv("ENABLE_NATS", raising=False)
        monkeypatch.delenv("RAY_EXECUTOR_ADDRESS", raising=False)
        
        adapter = EnvironmentConfigurationAdapter()
        config = adapter.get_service_configuration()
        
        assert config.grpc_port == "50055"
        assert config.messaging_url == "nats://nats:4222"
        assert config.messaging_enabled is True
        assert "ray-executor" in config.executor_address
    
    def test_get_service_configuration_custom(self, monkeypatch):
        """Test getting service configuration with custom values."""
        monkeypatch.setenv("GRPC_PORT", "9999")
        monkeypatch.setenv("NATS_URL", "nats://custom:4222")
        monkeypatch.setenv("ENABLE_NATS", "false")
        monkeypatch.setenv("RAY_EXECUTOR_ADDRESS", "custom-executor:50056")
        
        adapter = EnvironmentConfigurationAdapter()
        config = adapter.get_service_configuration()
        
        assert config.grpc_port == "9999"
        assert config.messaging_url == "nats://custom:4222"
        assert config.messaging_enabled is False
        assert config.executor_address == "custom-executor:50056"
    
    def test_get_config_value(self, monkeypatch):
        """Test getting a specific config value."""
        monkeypatch.setenv("TEST_KEY", "test_value")
        
        adapter = EnvironmentConfigurationAdapter()
        value = adapter.get_config_value("TEST_KEY", "default")
        
        assert value == "test_value"
    
    def test_get_config_value_default(self, monkeypatch):
        """Test getting config value with default."""
        monkeypatch.delenv("MISSING_KEY", raising=False)
        
        adapter = EnvironmentConfigurationAdapter()
        value = adapter.get_config_value("MISSING_KEY", "default_value")
        
        assert value == "default_value"

