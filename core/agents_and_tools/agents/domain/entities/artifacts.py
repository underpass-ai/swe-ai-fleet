"""Collection of artifacts."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Artifacts:
    """Collection of artifacts with utility methods."""

    artifacts: dict[str, Any] = field(default_factory=dict)  # Dict of artifact_name -> value

    def add(self, name: str, value: Any, artifact_type: str = "generic") -> None:
        """Add an artifact to the collection."""
        self.artifacts[name] = {"value": value, "type": artifact_type}

    def get(self, name: str) -> Any | None:
        """Get an artifact by name."""
        artifact = self.artifacts.get(name)
        return artifact["value"] if artifact else None

    def get_all(self) -> dict[str, Any]:
        """Get all artifacts."""
        return self.artifacts

    def update(self, other: dict[str, Any]) -> None:
        """Update artifacts from another dictionary."""
        self.artifacts.update(other)

    def count(self) -> int:
        """Get the number of artifacts."""
        return len(self.artifacts)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return self.artifacts

