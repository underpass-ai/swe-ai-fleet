"""Mapper for CeremonyInstance ↔ Storage formats.

Following Hexagonal Architecture:
- Mappers live in infrastructure layer
- Convert between domain entities and storage formats
- NO business logic - pure data transformation
"""

import json
from datetime import datetime
from typing import Any

from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_output_entry import StepOutputEntry
from core.ceremony_engine.domain.value_objects.step_output_map import StepOutputMap
from core.ceremony_engine.domain.value_objects.step_status_entry import StepStatusEntry
from core.ceremony_engine.domain.value_objects.step_status_map import StepStatusMap


class CeremonyInstanceMapper:
    """
    Mapper for CeremonyInstance ↔ Storage formats.

    Responsibilities:
    - Convert domain entity to Neo4j dict format
    - Convert Neo4j dict to domain entity
    - Convert domain entity to Valkey JSON string
    - Convert Valkey JSON to domain entity

    NO business logic - pure data transformation.
    """

    @staticmethod
    def to_neo4j_dict(instance: CeremonyInstance) -> dict[str, Any]:
        """Convert CeremonyInstance to Neo4j node properties.

        Args:
            instance: Domain entity to convert

        Returns:
            Dict with Neo4j node properties
        """
        # Serialize step_status to JSON for Neo4j storage
        step_status_dict = {
            entry.step_id.value: entry.status.value for entry in instance.step_status.entries
        }
        step_status_json = json.dumps(step_status_dict)
        step_outputs_dict = {
            entry.step_id.value: entry.output for entry in instance.step_outputs.entries
        }
        step_outputs_json = json.dumps(step_outputs_dict)

        # Serialize idempotency_keys to JSON
        idempotency_keys_list = list(instance.idempotency_keys)
        idempotency_keys_json = json.dumps(idempotency_keys_list)

        # Serialize definition name (reference, not full definition)
        # Full definition is stored separately or loaded from YAML
        definition_name = instance.definition.name

        return {
            "instance_id": instance.instance_id,
            "definition_name": definition_name,
            "current_state": instance.current_state,
            "step_status_json": step_status_json,
            "step_outputs_json": step_outputs_json,
            "correlation_id": instance.correlation_id,
            "idempotency_keys_json": idempotency_keys_json,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
        }

    @staticmethod
    def from_neo4j_dict(
        data: dict[str, Any],
        definition: Any,  # CeremonyDefinition - avoid circular import
    ) -> CeremonyInstance:
        """Convert Neo4j dict to CeremonyInstance.

        Args:
            data: Neo4j node properties
            definition: CeremonyDefinition (must be loaded separately)

        Returns:
            CeremonyInstance domain entity

        Raises:
            ValueError: If data is invalid (fail-fast)
        """
        from core.ceremony_engine.domain.value_objects.step_status import StepStatus

        # Parse step_status from JSON
        step_status_json = data.get("step_status_json", "{}")
        step_status_dict = json.loads(step_status_json)
        step_status_entries = tuple(
            StepStatusEntry(step_id=StepId(step_id), status=StepStatus(status_str))
            for step_id, status_str in step_status_dict.items()
        )
        step_status = StepStatusMap(entries=step_status_entries)

        # Parse step_outputs from JSON
        step_outputs_json = data.get("step_outputs_json", "{}")
        step_outputs_dict = json.loads(step_outputs_json)
        step_output_entries = tuple(
            StepOutputEntry(step_id=StepId(step_id), output=output)
            for step_id, output in step_outputs_dict.items()
        )
        step_outputs = StepOutputMap(entries=step_output_entries)

        # Parse idempotency_keys from JSON
        idempotency_keys_json = data.get("idempotency_keys_json", "[]")
        idempotency_keys_list = json.loads(idempotency_keys_json)
        idempotency_keys = frozenset(idempotency_keys_list)

        # Parse timestamps
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])

        return CeremonyInstance(
            instance_id=data["instance_id"],
            definition=definition,
            current_state=data["current_state"],
            step_status=step_status,
            step_outputs=step_outputs,
            correlation_id=data["correlation_id"],
            idempotency_keys=idempotency_keys,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def to_valkey_json(instance: CeremonyInstance) -> str:
        """Convert CeremonyInstance to Valkey JSON string.

        Args:
            instance: Domain entity to convert

        Returns:
            JSON string for Valkey storage
        """
        # Serialize step_status
        step_status_dict = {
            entry.step_id.value: entry.status.value for entry in instance.step_status.entries
        }
        step_outputs_dict = {
            entry.step_id.value: entry.output for entry in instance.step_outputs.entries
        }

        # Serialize idempotency_keys
        idempotency_keys_list = list(instance.idempotency_keys)

        # Serialize definition (just name, full definition loaded from YAML)
        definition_name = instance.definition.name

        instance_dict = {
            "instance_id": instance.instance_id,
            "definition_name": definition_name,
            "current_state": instance.current_state,
            "step_status": step_status_dict,
            "step_outputs": step_outputs_dict,
            "correlation_id": instance.correlation_id,
            "idempotency_keys": idempotency_keys_list,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
        }

        return json.dumps(instance_dict)

    @staticmethod
    def from_valkey_json(
        json_str: str,
        definition: Any,  # CeremonyDefinition - avoid circular import
    ) -> CeremonyInstance:
        """Convert Valkey JSON to CeremonyInstance.

        Args:
            json_str: JSON string from Valkey
            definition: CeremonyDefinition (must be loaded separately)

        Returns:
            CeremonyInstance domain entity

        Raises:
            ValueError: If JSON is invalid (fail-fast)
        """
        from core.ceremony_engine.domain.value_objects.step_status import StepStatus

        instance_dict = json.loads(json_str)

        # Parse step_status
        step_status_dict = instance_dict.get("step_status", {})
        step_status_entries = tuple(
            StepStatusEntry(step_id=StepId(step_id), status=StepStatus(status_str))
            for step_id, status_str in step_status_dict.items()
        )
        step_status = StepStatusMap(entries=step_status_entries)

        # Parse step_outputs
        step_outputs_dict = instance_dict.get("step_outputs", {})
        step_output_entries = tuple(
            StepOutputEntry(step_id=StepId(step_id), output=output)
            for step_id, output in step_outputs_dict.items()
        )
        step_outputs = StepOutputMap(entries=step_output_entries)

        # Parse idempotency_keys
        idempotency_keys_list = instance_dict.get("idempotency_keys", [])
        idempotency_keys = frozenset(idempotency_keys_list)

        # Parse timestamps
        created_at = datetime.fromisoformat(instance_dict["created_at"])
        updated_at = datetime.fromisoformat(instance_dict["updated_at"])

        return CeremonyInstance(
            instance_id=instance_dict["instance_id"],
            definition=definition,
            current_state=instance_dict["current_state"],
            step_status=step_status,
            step_outputs=step_outputs,
            correlation_id=instance_dict["correlation_id"],
            idempotency_keys=idempotency_keys,
            created_at=created_at,
            updated_at=updated_at,
        )
