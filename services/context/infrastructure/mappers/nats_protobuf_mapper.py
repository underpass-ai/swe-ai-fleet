"""Mapper from NATS JSON messages to protobuf requests.

Infrastructure layer mapper for converting NATS message payloads (JSON)
to gRPC protobuf requests.

Following Hexagonal Architecture:
- Infrastructure concern: serialization/deserialization
- Separates external format (JSON) from internal format (protobuf)
- No domain logic, pure data transformation
"""

import json
import time
from typing import Any

from services.context.gen import context_pb2


class NatsProtobufMapper:
    """Mapper that converts NATS JSON messages to protobuf requests.

    Responsibility:
    - NATS JSON payload → Protobuf request
    - Handle all field mappings and type conversions
    - Provide defaults for missing fields
    - Validate required fields (fail-fast)

    This is infrastructure-level serialization logic.
    Should NOT be in handlers or servicers.
    """

    @staticmethod
    def to_update_context_request(data: dict[str, Any]) -> context_pb2.UpdateContextRequest:
        """Convert NATS JSON message to UpdateContextRequest.

        Args:
            data: JSON payload from NATS message

        Returns:
            Protobuf UpdateContextRequest

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields (fail-fast)
        if not data.get("story_id"):
            raise ValueError("story_id is required in update context request")

        # Convert changes list
        changes = []
        for change_data in data.get("changes", []):
            change = context_pb2.ContextChange(
                operation=change_data.get("operation", ""),
                entity_type=change_data.get("entity_type", ""),
                entity_id=change_data.get("entity_id", ""),
                payload=NatsProtobufMapper._serialize_payload(change_data.get("payload")),
                reason=change_data.get("reason", ""),
            )
            changes.append(change)

        # Build request with defaults
        timestamp = data.get("timestamp")
        if not timestamp:
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return context_pb2.UpdateContextRequest(
            story_id=data.get("story_id", ""),
            task_id=data.get("task_id", ""),
            role=data.get("role", ""),
            changes=changes,
            timestamp=timestamp,
        )

    @staticmethod
    def to_rehydrate_session_request(data: dict[str, Any]) -> context_pb2.RehydrateSessionRequest:
        """Convert NATS JSON message to RehydrateSessionRequest.

        Args:
            data: JSON payload from NATS message

        Returns:
            Protobuf RehydrateSessionRequest

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields (fail-fast)
        if not data.get("case_id"):
            raise ValueError("case_id is required in rehydrate session request")

        return context_pb2.RehydrateSessionRequest(
            case_id=data.get("case_id", ""),
            roles=list(data.get("roles", [])),
            include_timeline=data.get("include_timeline", False),
            include_summaries=data.get("include_summaries", False),
            timeline_events=data.get("timeline_events", 50),
            persist_bundle=data.get("persist_bundle", False),
            ttl_seconds=data.get("ttl_seconds", 3600),
        )

    @staticmethod
    def _serialize_payload(payload: Any) -> str:
        """Serialize payload to JSON string.

        Args:
            payload: Payload value (dict, str, or None)

        Returns:
            JSON string representation
        """
        if payload is None:
            return ""

        if isinstance(payload, dict):
            return json.dumps(payload)

        if isinstance(payload, str):
            return payload

        # For other types, convert to string
        return str(payload)

