from __future__ import annotations

import pytest

from services.ray_executor.config import RayExecutorConfig, load_ray_executor_config


class _EnvMock(dict[str, str]):
    """Simple mapping to simulate environment variables in tests."""

    def __init__(self, initial: Mapping[str, str] | None = None) -> None:
        super().__init__(initial or {})


def test_load_ray_executor_config_defaults() -> None:
    env = _EnvMock()

    config = load_ray_executor_config(env)

    assert isinstance(config, RayExecutorConfig)
    assert config.port == 50056
    assert config.ray_address == "ray://ray-gpu-head-svc.ray.svc.cluster.local:10001"
    assert config.nats_url == "nats://nats.swe-ai-fleet.svc.cluster.local:4222"
    assert config.enable_nats is True


def test_load_ray_executor_config_custom_values() -> None:
    env = _EnvMock(
        {
            "GRPC_PORT": "60000",
            "RAY_ADDRESS": "ray://custom:10001",
            "NATS_URL": "nats://custom:4222",
            "ENABLE_NATS": "false",
        }
    )

    config = load_ray_executor_config(env)

    assert config.port == 60000
    assert config.ray_address == "ray://custom:10001"
    assert config.nats_url == "nats://custom:4222"
    assert config.enable_nats is False


def test_load_ray_executor_config_invalid_port_raises() -> None:
    env = _EnvMock({"GRPC_PORT": "not-an-int"})

    with pytest.raises(ValueError) as exc_info:
        load_ray_executor_config(env)

    assert "Invalid GRPC_PORT value" in str(exc_info.value)
