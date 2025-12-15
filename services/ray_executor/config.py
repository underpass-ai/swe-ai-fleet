from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import os


@dataclass(frozen=True)
class RayExecutorConfig:
    """Configuration for Ray Executor Service."""

    port: int
    ray_address: str
    nats_url: str
    enable_nats: bool


def load_ray_executor_config(env: Mapping[str, str] | None = None) -> RayExecutorConfig:
    """Load Ray Executor configuration from environment variables."""
    if env is None:
        env = os.environ

    port_raw = env.get("GRPC_PORT", "50056")
    try:
        port = int(port_raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid GRPC_PORT value: {port_raw}") from exc

    ray_address = env.get(
        "RAY_ADDRESS",
        "ray://ray-gpu-head-svc.ray.svc.cluster.local:10001",
    )
    nats_url = env.get(
        "NATS_URL",
        "nats://nats.swe-ai-fleet.svc.cluster.local:4222",
    )
    enable_nats = env.get("ENABLE_NATS", "true").lower() == "true"

    return RayExecutorConfig(
        port=port,
        ray_address=ray_address,
        nats_url=nats_url,
        enable_nats=enable_nats,
    )
