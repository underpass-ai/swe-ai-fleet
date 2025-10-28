"""Collection of artifacts."""

from dataclasses import dataclass, field
from typing import Any

from core.agents_and_tools.agents.domain.entities.artifact import Artifact


@dataclass
class Artifacts:
    """Collection of artifacts with utility methods."""

    artifacts: dict[str, Artifact] = field(default_factory=dict)  # Dict of artifact_name -> Artifact entity

    def add(self, name: str, value: Any, artifact_type: str = "generic") -> None:
        """Add an artifact to the collection."""
        artifact_entity = Artifact(
            name=name,
            value=value,
            artifact_type=artifact_type,
        )
        self.artifacts[name] = artifact_entity

    def get(self, name: str) -> Any | None:
        """Get an artifact by name."""
        artifact = self.artifacts.get(name)
        return artifact.value if artifact else None

    def get_all(self) -> dict[str, Artifact]:
        """Get all artifacts."""
        return self.artifacts

    def update_from_dict(self, other: dict[str, Any]) -> None:
        """
        Update artifacts from a dictionary of artifact structures.
        
        Expected format: {name: {"value": ..., "type": ...}} or {name: value}
        This is a convenience method for legacy code that still returns dicts.
        For new code, use add() directly.
        """
        # Legacy support: handle both {"value": x, "type": y} and simple values
        for name, data in other.items():
            if isinstance(data, dict):
                value = data["value"] if "value" in data else data
                artifact_type = data["type"] if "type" in data else "generic"
            else:
                value = data
                artifact_type = "generic"
            
            artifact_entity = Artifact(
                name=name,
                value=value,
                artifact_type=artifact_type,
            )
            self.artifacts[name] = artifact_entity

    def count(self) -> int:
        """Get the number of artifacts."""
        return len(self.artifacts)

