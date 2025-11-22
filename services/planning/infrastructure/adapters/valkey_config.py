"""Valkey connection configuration for Planning Service."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValkeyConfig:
    """
    Valkey connection configuration.

    Persistence Configuration (K8s ConfigMap):
    - AOF (Append-Only File): appendonly yes
    - RDB Snapshots: save 900 1, save 300 10, save 60 10000
    - This ensures data survives pod restarts
    """

    host: str = field(default_factory=lambda: os.getenv("VALKEY_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("VALKEY_PORT", "6379")))
    db: int = 0
    decode_responses: bool = True

