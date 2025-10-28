"""Mapper for converting artifacts from infrastructure to domain entities."""

from typing import Any

from core.agents_and_tools.agents.domain.entities.artifact import Artifact


class ArtifactMapper:
    """
    Mapper for converting artifact dictionaries to domain entities.

    This mapper handles the conversion between infrastructure-specific
    artifact dictionaries and domain Artifact entities.

    Following the cursorrules:
    - No to_dict() or from_dict() in domain entities
    - Mappers handle conversions in infrastructure layer
    - Explicit type conversion, no reflection
    """

    def to_entity(self, name: str, value: Any, artifact_type: str = "generic") -> Artifact:
        """
        Convert artifact data to Artifact entity.

        Args:
            name: Artifact identifier
            value: Artifact value
            artifact_type: Type of artifact

        Returns:
            Artifact entity
        """
        return Artifact(
            name=name,
            value=value,
            artifact_type=artifact_type,
        )

    def from_dict_entry(self, name: str, data: dict[str, Any] | Any) -> Artifact:
        """
        Convert dictionary entry to Artifact entity.

        Handles both structured dict {"value": x, "type": y} and simple values.
        This is used for legacy code that returns dicts.

        Args:
            name: Artifact name
            data: Either a dict with "value" and "type", or a simple value

        Returns:
            Artifact entity
        """
        # Handle structured dict
        if isinstance(data, dict) and "value" in data:
            return Artifact(
                name=name,
                value=data["value"],
                artifact_type=data["type"] if "type" in data else "generic",
            )

        # Handle simple value
        return Artifact(
            name=name,
            value=data,
            artifact_type="generic",
        )

    def from_dict_batch(self, artifacts_dict: dict[str, Any]) -> list[Artifact]:
        """
        Convert a dictionary of artifacts to list of Artifact entities.

        Args:
            artifacts_dict: Dictionary mapping artifact names to values or structures

        Returns:
            List of Artifact entities
        """
        return [
            self.from_dict_entry(name, data)
            for name, data in artifacts_dict.items()
        ]

