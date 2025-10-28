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

    def update(self, other: dict[str, Any]) -> None:
        """Update artifacts from another dictionary."""
        # Convert dict values to Artifact entities
        for name, data in other.items():
            if isinstance(data, dict) and "value" in data:
                # Already has structure
                artifact_entity = Artifact(
                    name=name,
                    value=data.get("value"),
                    artifact_type=data.get("type", "generic"),
                )
            else:
                # Simple value
                artifact_entity = Artifact(
                    name=name,
                    value=data,
                    artifact_type="generic",
                )
            self.artifacts[name] = artifact_entity

    def count(self) -> int:
        """Get the number of artifacts."""
        return len(self.artifacts)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return {name: {"value": artifact.value, "type": artifact.artifact_type} for name, artifact in self.artifacts.items()}

