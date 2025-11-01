"""Tests for ServiceConfiguration entity."""

from services.orchestrator.domain.entities import ServiceConfiguration


class TestServiceConfiguration:
    """Test suite for ServiceConfiguration entity."""
    
    def test_creation(self):
        """Test creating service configuration."""
        config = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://nats:4222",
            messaging_enabled=True,
            executor_address="ray_executor:50056"
        )
        
        assert config.grpc_port == "50055"
        assert config.messaging_url == "nats://nats:4222"
        assert config.messaging_enabled is True
        assert config.executor_address == "ray_executor:50056"
    
    def test_is_messaging_enabled(self):
        """Test is_messaging_enabled property."""
        config_enabled = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://nats:4222",
            messaging_enabled=True,
            executor_address="ray_executor:50056"
        )
        config_disabled = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://nats:4222",
            messaging_enabled=False,
            executor_address="ray_executor:50056"
        )
        
        assert config_enabled.is_messaging_enabled is True
        assert config_disabled.is_messaging_enabled is False
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        config = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://nats:4222",
            messaging_enabled=True,
            executor_address="ray_executor:50056"
        )
        
        result = config.to_dict()
        
        assert result["grpc_port"] == "50055"
        assert result["messaging_url"] == "nats://nats:4222"
        assert result["messaging_enabled"] is True
        assert result["executor_address"] == "ray_executor:50056"
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "grpc_port": "9999",
            "messaging_url": "nats://custom:4222",
            "messaging_enabled": False,
            "executor_address": "custom-executor:50056"
        }
        
        config = ServiceConfiguration.from_dict(data)
        
        assert config.grpc_port == "9999"
        assert config.messaging_url == "nats://custom:4222"
        assert config.messaging_enabled is False
        assert config.executor_address == "custom-executor:50056"
    
    def test_create_default(self):
        """Test creating default configuration."""
        config = ServiceConfiguration.create_default()
        
        assert config.grpc_port == "50055"
        assert config.messaging_url == "nats://nats:4222"
        assert config.messaging_enabled is True
        assert "ray_executor" in config.executor_address

