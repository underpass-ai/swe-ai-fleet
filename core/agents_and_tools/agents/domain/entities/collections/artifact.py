"""Domain entity for artifact."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Artifact:
    """Represents an artifact produced by agent execution."""

    name: str  # Artifact identifier (e.g., "commit_sha", "files_changed")
    value: Any  # Artifact value
    artifact_type: str  # Type of artifact (commit, file, test_result, etc.)

