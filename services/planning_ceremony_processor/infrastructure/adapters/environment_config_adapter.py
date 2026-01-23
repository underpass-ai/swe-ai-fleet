"""Environment configuration for planning ceremony processor."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentConfig:
    """Environment configuration (fail-fast)."""

    nats_url: str
    ray_executor_url: str
    vllm_url: str
    vllm_model: str
    ceremonies_dir: str
    valkey_host: str
    valkey_port: int
    valkey_db: int

    @staticmethod
    def from_env() -> "EnvironmentConfig":
        nats_url = os.getenv("NATS_URL", "nats://nats:4222")
        ray_executor_url = os.getenv("RAY_EXECUTOR_URL", "ray-executor:50056")
        vllm_url = os.getenv("VLLM_URL", "http://vllm-server:8000")
        vllm_model = os.getenv("VLLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
        ceremonies_dir = os.getenv("CEREMONIES_DIR", "/app/config/ceremonies")
        valkey_host = os.getenv("VALKEY_HOST", "valkey")
        valkey_port = int(os.getenv("VALKEY_PORT", "6379"))
        valkey_db = int(os.getenv("VALKEY_DB", "0"))

        if not nats_url.strip():
            raise ValueError("NATS_URL cannot be empty")
        if not ray_executor_url.strip():
            raise ValueError("RAY_EXECUTOR_URL cannot be empty")
        if not vllm_url.strip():
            raise ValueError("VLLM_URL cannot be empty")
        if not vllm_model.strip():
            raise ValueError("VLLM_MODEL cannot be empty")
        if not ceremonies_dir.strip():
            raise ValueError("CEREMONIES_DIR cannot be empty")
        if not valkey_host.strip():
            raise ValueError("VALKEY_HOST cannot be empty")

        return EnvironmentConfig(
            nats_url=nats_url,
            ray_executor_url=ray_executor_url,
            vllm_url=vllm_url,
            vllm_model=vllm_model,
            ceremonies_dir=ceremonies_dir,
            valkey_host=valkey_host,
            valkey_port=valkey_port,
            valkey_db=valkey_db,
        )
