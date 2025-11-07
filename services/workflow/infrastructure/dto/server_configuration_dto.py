"""Server Configuration DTO.

Configuration data for Workflow Orchestration Service.
Following DDD + Hexagonal Architecture principles.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ServerConfigurationDTO:
    """DTO for server configuration.

    Encapsulates all configuration needed to start the service.
    Used by server.py to initialize infrastructure connections.

    Infrastructure DTO (not application):
    - This is server infrastructure concern, not domain/application
    - Located in infrastructure/dto (not application/dto)
    - Application DTOs are for domain contracts (PlanningEvent, etc)

    Following DDD:
    - DTO does NOT implement to_dict() / from_dict()
    - Immutable (frozen=True)
    - Fail-fast validation

    Domain Invariants:
    - grpc_port must be valid (1-65535)
    - neo4j_uri cannot be empty
    - neo4j_password cannot be empty (security)
    - nats_url cannot be empty
    - fsm_config must be valid dict
    """

    grpc_port: int
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    valkey_host: str
    valkey_port: int
    nats_url: str
    fsm_config: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If any invariant is violated
        """
        # Validate gRPC port range
        if not (1 <= self.grpc_port <= 65535):
            raise ValueError(f"Invalid gRPC port: {self.grpc_port} (must be 1-65535)")

        # Validate required connection strings
        if not self.neo4j_uri:
            raise ValueError("neo4j_uri cannot be empty")

        if not self.neo4j_password:
            raise ValueError(
                "neo4j_password cannot be empty (required for security)"
            )

        if not self.nats_url:
            raise ValueError("nats_url cannot be empty")

        # Validate Valkey port range
        if not (1 <= self.valkey_port <= 65535):
            raise ValueError(
                f"Invalid Valkey port: {self.valkey_port} (must be 1-65535)"
            )

        # Validate FSM config is not empty
        if not self.fsm_config:
            raise ValueError("fsm_config cannot be empty")

        # Validate FSM config has required keys
        required_keys = ["states", "transitions"]
        for key in required_keys:
            if key not in self.fsm_config:
                raise ValueError(
                    f"FSM config missing required key: {key}"
                )
