"""Tests for ServiceConfiguration entity."""

import pytest
from services.orchestrator.domain.entities.service_configuration import ServiceConfiguration


class TestServiceConfiguration:
    """Test cases for ServiceConfiguration entity."""

    def test_service_configuration_creation(self):
        """Test creating ServiceConfiguration with all fields."""
        config = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://localhost:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056"
        )
        
        assert config.grpc_port == "50055"
        assert config.messaging_url == "nats://localhost:4222"
        assert config.messaging_enabled is True
        assert config.executor_address == "ray-executor:50056"

    def test_is_messaging_enabled_property(self):
        """Test is_messaging_enabled property."""
        # Messaging enabled
        config_enabled = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://localhost:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056"
        )
        assert config_enabled.is_messaging_enabled is True
        
        # Messaging disabled
        config_disabled = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://localhost:4222",
            messaging_enabled=False,
            executor_address="ray-executor:50056"
        )
        assert config_disabled.is_messaging_enabled is False

    def test_to_dict_method(self):
        """Test to_dict method."""
        config = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://localhost:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056"
        )
        
        result = config.to_dict()
        
        expected = {
            "grpc_port": "50055",
            "messaging_url": "nats://localhost:4222",
            "messaging_enabled": True,
            "executor_address": "ray-executor:50056"
        }
        
        assert result == expected
        assert isinstance(result, dict)

    def test_from_dict_method(self):
        """Test from_dict class method."""
        data = {
            "grpc_port": "50055",
            "messaging_url": "nats://localhost:4222",
            "messaging_enabled": True,
            "executor_address": "ray-executor:50056"
        }
        
        config = ServiceConfiguration.from_dict(data)
        
        assert config.grpc_port == "50055"
        assert config.messaging_url == "nats://localhost:4222"
        assert config.messaging_enabled is True
        assert config.executor_address == "ray-executor:50056"

    def test_from_dict_with_different_types(self):
        """Test from_dict with different data types."""
        data = {
            "grpc_port": "8080",
            "messaging_url": "redis://localhost:6379",
            "messaging_enabled": False,
            "executor_address": "k8s-executor:8080"
        }
        
        config = ServiceConfiguration.from_dict(data)
        
        assert config.grpc_port == "8080"
        assert config.messaging_url == "redis://localhost:6379"
        assert config.messaging_enabled is False
        assert config.executor_address == "k8s-executor:8080"

    def test_create_default_method(self):
        """Test create_default class method."""
        config = ServiceConfiguration.create_default()
        
        assert config.grpc_port == "50055"
        assert config.messaging_url == "nats://nats:4222"
        assert config.messaging_enabled is True
        assert config.executor_address == "ray-executor.swe-ai-fleet.svc.cluster.local:50056"

    def test_roundtrip_dict_conversion(self):
        """Test roundtrip conversion: object -> dict -> object."""
        original_config = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://localhost:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056"
        )
        
        # Convert to dict and back
        config_dict = original_config.to_dict()
        restored_config = ServiceConfiguration.from_dict(config_dict)
        
        assert restored_config.grpc_port == original_config.grpc_port
        assert restored_config.messaging_url == original_config.messaging_url
        assert restored_config.messaging_enabled == original_config.messaging_enabled
        assert restored_config.executor_address == original_config.executor_address

    def test_service_configuration_equality(self):
        """Test ServiceConfiguration equality."""
        config1 = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://localhost:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056"
        )
        
        config2 = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://localhost:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056"
        )
        
        config3 = ServiceConfiguration(
            grpc_port="8080",  # Different port
            messaging_url="nats://localhost:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056"
        )
        
        assert config1 == config2
        assert config1 != config3

    def test_service_configuration_string_representation(self):
        """Test ServiceConfiguration string representation."""
        config = ServiceConfiguration(
            grpc_port="50055",
            messaging_url="nats://localhost:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056"
        )
        
        str_repr = str(config)
        
        assert "ServiceConfiguration" in str_repr
        assert "50055" in str_repr
        assert "nats://localhost:4222" in str_repr
        assert "True" in str_repr
        assert "ray-executor:50056" in str_repr

    def test_service_configuration_with_empty_strings(self):
        """Test ServiceConfiguration with empty string values."""
        config = ServiceConfiguration(
            grpc_port="",
            messaging_url="",
            messaging_enabled=False,
            executor_address=""
        )
        
        assert config.grpc_port == ""
        assert config.messaging_url == ""
        assert config.messaging_enabled is False
        assert config.executor_address == ""
        assert config.is_messaging_enabled is False
