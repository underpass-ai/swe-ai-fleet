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

    def update_from_dict(self, other: dict[str, Any], mapper: Any = None) -> None:
        """
        Update artifacts from a dictionary of artifact structures.
        
        Expected format: {name: {"value": ..., "type": ...}} or {name: value}
        This is a convenience method for legacy code that still returns dicts.
        For new code, use add() directly.
        
        Args:
            other: Dictionary of artifacts to add
            mapper: ArtifactMapper instance (injected dependency)
        """
        if mapper is None:
            # Fallback: import mapper if not provided (for backward compatibility)
            from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
            mapper = ArtifactMapper()
        
        # Use mapper to convert dict entries to entities
        for name, data in other.items():
            artifact_entity = mapper.from_dict_entry(name, data)
            self.artifacts[name] = artifact_entity

    def count(self) -> int:
        """Get the number of artifacts."""
        return len(self.artifacts)

