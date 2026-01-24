"""Tests for EnvironmentConfig."""

import os

import pytest

from services.planning_ceremony_processor.infrastructure.adapters.environment_config_adapter import (
    EnvironmentConfig,
)


def test_environment_config_from_env_defaults(monkeypatch) -> None:
    monkeypatch.delenv("NATS_URL", raising=False)
    monkeypatch.delenv("RAY_EXECUTOR_URL", raising=False)
    monkeypatch.delenv("VLLM_URL", raising=False)
    monkeypatch.delenv("VLLM_MODEL", raising=False)
    monkeypatch.delenv("CEREMONIES_DIR", raising=False)
    monkeypatch.delenv("VALKEY_HOST", raising=False)
    monkeypatch.delenv("VALKEY_PORT", raising=False)
    monkeypatch.delenv("VALKEY_DB", raising=False)

    config = EnvironmentConfig.from_env()

    assert config.nats_url == "nats://nats:4222"
    assert config.ceremonies_dir == "/app/config/ceremonies"
    assert config.valkey_host == "valkey"


def test_environment_config_rejects_empty_values(monkeypatch) -> None:
    monkeypatch.setenv("NATS_URL", " ")
    monkeypatch.setenv("RAY_EXECUTOR_URL", "ray-executor:50056")
    monkeypatch.setenv("VLLM_URL", "http://vllm")
    monkeypatch.setenv("VLLM_MODEL", "model")
    monkeypatch.setenv("CEREMONIES_DIR", "/app/config/ceremonies")
    monkeypatch.setenv("VALKEY_HOST", "valkey")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("VALKEY_DB", "0")

    with pytest.raises(ValueError, match="NATS_URL cannot be empty"):
        EnvironmentConfig.from_env()


def test_environment_config_rejects_empty_valkey_host(monkeypatch) -> None:
    monkeypatch.setenv("NATS_URL", "nats://nats:4222")
    monkeypatch.setenv("RAY_EXECUTOR_URL", "ray-executor:50056")
    monkeypatch.setenv("VLLM_URL", "http://vllm")
    monkeypatch.setenv("VLLM_MODEL", "model")
    monkeypatch.setenv("CEREMONIES_DIR", "/app/config/ceremonies")
    monkeypatch.setenv("VALKEY_HOST", " ")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("VALKEY_DB", "0")

    with pytest.raises(ValueError, match="VALKEY_HOST cannot be empty"):
        EnvironmentConfig.from_env()


def test_environment_config_rejects_empty_ray_executor_url(monkeypatch) -> None:
    monkeypatch.setenv("NATS_URL", "nats://nats:4222")
    monkeypatch.setenv("RAY_EXECUTOR_URL", " ")
    monkeypatch.setenv("VLLM_URL", "http://vllm")
    monkeypatch.setenv("VLLM_MODEL", "model")
    monkeypatch.setenv("CEREMONIES_DIR", "/app/config/ceremonies")
    monkeypatch.setenv("VALKEY_HOST", "valkey")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("VALKEY_DB", "0")

    with pytest.raises(ValueError, match="RAY_EXECUTOR_URL cannot be empty"):
        EnvironmentConfig.from_env()


def test_environment_config_rejects_empty_vllm_url(monkeypatch) -> None:
    monkeypatch.setenv("NATS_URL", "nats://nats:4222")
    monkeypatch.setenv("RAY_EXECUTOR_URL", "ray-executor:50056")
    monkeypatch.setenv("VLLM_URL", " ")
    monkeypatch.setenv("VLLM_MODEL", "model")
    monkeypatch.setenv("CEREMONIES_DIR", "/app/config/ceremonies")
    monkeypatch.setenv("VALKEY_HOST", "valkey")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("VALKEY_DB", "0")

    with pytest.raises(ValueError, match="VLLM_URL cannot be empty"):
        EnvironmentConfig.from_env()


def test_environment_config_rejects_empty_vllm_model(monkeypatch) -> None:
    monkeypatch.setenv("NATS_URL", "nats://nats:4222")
    monkeypatch.setenv("RAY_EXECUTOR_URL", "ray-executor:50056")
    monkeypatch.setenv("VLLM_URL", "http://vllm")
    monkeypatch.setenv("VLLM_MODEL", " ")
    monkeypatch.setenv("CEREMONIES_DIR", "/app/config/ceremonies")
    monkeypatch.setenv("VALKEY_HOST", "valkey")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("VALKEY_DB", "0")

    with pytest.raises(ValueError, match="VLLM_MODEL cannot be empty"):
        EnvironmentConfig.from_env()


def test_environment_config_rejects_empty_ceremonies_dir(monkeypatch) -> None:
    monkeypatch.setenv("NATS_URL", "nats://nats:4222")
    monkeypatch.setenv("RAY_EXECUTOR_URL", "ray-executor:50056")
    monkeypatch.setenv("VLLM_URL", "http://vllm")
    monkeypatch.setenv("VLLM_MODEL", "model")
    monkeypatch.setenv("CEREMONIES_DIR", " ")
    monkeypatch.setenv("VALKEY_HOST", "valkey")
    monkeypatch.setenv("VALKEY_PORT", "6379")
    monkeypatch.setenv("VALKEY_DB", "0")

    with pytest.raises(ValueError, match="CEREMONIES_DIR cannot be empty"):
        EnvironmentConfig.from_env()


def test_environment_config_custom_values(monkeypatch) -> None:
    monkeypatch.setenv("NATS_URL", "nats://custom:4222")
    monkeypatch.setenv("RAY_EXECUTOR_URL", "ray-executor:9999")
    monkeypatch.setenv("VLLM_URL", "http://vllm:8000")
    monkeypatch.setenv("VLLM_MODEL", "custom-model")
    monkeypatch.setenv("CEREMONIES_DIR", "/custom/ceremonies")
    monkeypatch.setenv("VALKEY_HOST", "valkey-host")
    monkeypatch.setenv("VALKEY_PORT", "6380")
    monkeypatch.setenv("VALKEY_DB", "1")

    config = EnvironmentConfig.from_env()

    assert config.nats_url == "nats://custom:4222"
    assert config.ray_executor_url == "ray-executor:9999"
    assert config.vllm_url == "http://vllm:8000"
    assert config.vllm_model == "custom-model"
    assert config.ceremonies_dir == "/custom/ceremonies"
    assert config.valkey_host == "valkey-host"
    assert config.valkey_port == 6380
    assert config.valkey_db == 1
