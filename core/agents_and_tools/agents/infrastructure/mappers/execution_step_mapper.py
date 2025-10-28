"""Mapper for converting execution steps from infrastructure to domain entities."""

from typing import Any

from core.agents_and_tools.agents.domain.entities.execution_step import ExecutionStep


class ExecutionStepMapper:
    """
    Mapper for converting execution step dictionaries to domain entities.

    This mapper handles the conversion between infrastructure-specific
    execution step dictionaries and domain ExecutionStep entities.

    Following the cursorrules:
    - No to_dict() or from_dict() in domain entities
    - Mappers handle conversions in infrastructure layer
    - Explicit type conversion, no reflection
    """

    def to_entity(self, step_dict: dict[str, Any]) -> ExecutionStep:
        """
        Convert step dictionary to ExecutionStep entity.

        This method explicitly extracts required fields from the dictionary
        without using reflection (no .get(), hasattr(), etc.).

        Args:
            step_dict: Dictionary with keys: tool, operation, params (optional)

        Returns:
            ExecutionStep entity

        Raises:
            KeyError: If required keys (tool, operation) are missing
            ValueError: If tool or operation are empty (validated by entity)
        """
        # Explicit field extraction - no reflection
        tool = step_dict["tool"]
        operation = step_dict["operation"]
        params = step_dict.get("params") if "params" in step_dict else None

        return ExecutionStep(
            tool=tool,
            operation=operation,
            params=params,
        )

    def to_entity_list(self, steps: list[dict[str, Any]]) -> list[ExecutionStep]:
        """
        Convert list of step dictionaries to ExecutionStep entities.

        Args:
            steps: List of step dictionaries

        Returns:
            List of ExecutionStep entities
        """
        return [self.to_entity(step) for step in steps]

