"""Valkey connection configuration for Ceremony Engine."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValkeyConfig:
    """Valkey connection configuration for Ceremony Engine.

    Persistence Configuration (K8s ConfigMap):
    - AOF (Append-Only File): appendonly yes
    - RDB Snapshots: save 900 1, save 300 10, save 60 10000
    - This ensures data survives pod restarts

    Domain Value Object:
    - Immutable configuration
    - Environment variable defaults
    """

    host: str = field(default_factory=lambda: os.getenv("VALKEY_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("VALKEY_PORT", "6379")))
    db: int = 0
    decode_responses: bool = True
