"""Mapper for AgentResponsePayload from NATS messages.

Infrastructure layer mapper for converting NATS JSON messages to
generated DTOs from AsyncAPI specification.

Following Hexagonal Architecture:
- Infrastructure concern: serialization/deserialization
- Separates external format (JSON/dict) from internal format (generated DTO)
- No domain logic, pure data transformation
- Fail-fast validation
"""

import json
from typing import Any

from backlog_review_processor.gen.agent_response_payload import (
    AgentResponsePayload,
    Constraints,
    Metadata,
    Status,
)


class AgentResponseMapper:
    """Mapper that converts NATS JSON messages to AgentResponsePayload DTO.

    Responsibility:
    - NATS JSON payload (dict) → AgentResponsePayload DTO
    - Handle all field mappings and type conversions
    - Validate required fields (fail-fast)
    - Convert nested structures (constraints, metadata)

    This is infrastructure-level serialization logic.
    Should NOT be in handlers or consumers directly.
    """

    @staticmethod
    def from_nats_json(payload: dict[str, Any]) -> AgentResponsePayload:
        """Convert NATS JSON payload to AgentResponsePayload DTO.

        Args:
            payload: JSON payload from NATS message (already parsed from bytes)

        Returns:
            AgentResponsePayload DTO

        Raises:
            KeyError: If required field missing (fail-fast)
            ValueError: If data is invalid (fail-fast)
        """
        # Extract and convert status enum
        status_str = payload.get("status", "")
        try:
            status = Status(status_str)
        except ValueError:
            raise ValueError(f"Invalid status: {status_str} (must be 'completed' or 'failed')")

        # Extract constraints if present
        constraints = None
        if "constraints" in payload and payload["constraints"]:
            constraints_dict = payload["constraints"]

            # Extract metadata if present
            metadata = None
            if "metadata" in constraints_dict and constraints_dict["metadata"]:
                metadata_dict = constraints_dict["metadata"]
                metadata = Metadata(
                    story_id=metadata_dict.get("story_id"),
                    ceremony_id=metadata_dict.get("ceremony_id"),
                    task_type=metadata_dict.get("task_type"),
                    task_id=metadata_dict.get("task_id"),
                    num_agents=metadata_dict.get("num_agents"),
                )

            constraints = Constraints(
                story_id=constraints_dict.get("story_id"),
                plan_id=constraints_dict.get("plan_id"),
                timeout_seconds=constraints_dict.get("timeout_seconds"),
                max_retries=constraints_dict.get("max_retries"),
                metadata=metadata,
            )

        # Create DTO (DTO validates invariants in __post_init__)
        return AgentResponsePayload(
            task_id=payload["task_id"],  # Required - fail-fast if missing
            status=status,
            agent_id=payload.get("agent_id"),
            role=payload.get("role"),
            num_agents=payload.get("num_agents"),
            proposal=payload.get("proposal"),
            duration_ms=payload.get("duration_ms"),
            timestamp=payload.get("timestamp"),
            constraints=constraints,
            artifacts=payload.get("artifacts"),
            summary=payload.get("summary"),
            metrics=payload.get("metrics"),
            workspace_report=payload.get("workspace_report"),
        )

    @staticmethod
    def from_nats_bytes(message_data: bytes) -> AgentResponsePayload:
        """Convert NATS message bytes to AgentResponsePayload DTO.

        Args:
            message_data: Raw NATS message bytes

        Returns:
            AgentResponsePayload DTO

        Raises:
            json.JSONDecodeError: If JSON is malformed
            KeyError: If required field missing
            ValueError: If data is invalid
        """
        # Deserialize JSON
        payload: dict[str, Any] = json.loads(message_data.decode("utf-8"))

        # Convert to DTO
        return AgentResponseMapper.from_nats_json(payload)
