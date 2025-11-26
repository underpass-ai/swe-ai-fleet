"""Mapper: Domain Project ↔ Valkey dict format."""

from datetime import datetime

from planning.domain.entities.project import Project
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.project_status import ProjectStatus


class ProjectValkeyMapper:
    """
    Mapper: Convert domain Project to/from Valkey dict format.

    Infrastructure Layer Responsibility:
    - Domain entities should not know about Redis hash format
    - Conversions live in dedicated mappers (Hexagonal Architecture)

    Following the same pattern as StoryValkeyMapper for consistency.
    """

    @staticmethod
    def to_dict(project: Project) -> dict[str, str]:
        """
        Convert domain Project to Valkey hash dict.

        Args:
            project: Domain Project entity.

        Returns:
            Dict suitable for Redis HSET (all values as strings).
        """
        return {
            "project_id": project.project_id.value,
            "name": project.name,
            "description": project.description or "",
            "status": project.status.value,  # Enum string value
            "owner": project.owner or "",
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[str, str] | dict[bytes, bytes]) -> Project:
        """
        Convert Valkey hash dict to domain Project.

        Args:
            data: Redis hash data (string keys/values if decode_responses=True,
                  bytes keys/values if decode_responses=False).

        Returns:
            Domain Project entity.

        Raises:
            ValueError: If data is invalid or missing required fields.
        """
        if not data:
            raise ValueError("Cannot create Project from empty dict")

        # Handle both string and bytes keys (depending on decode_responses config)
        # ValkeyConfig has decode_responses=True, so strings are expected
        # But we handle both for robustness
        def get_str(key: str) -> str:
            """Get string value from dict, handling both string and bytes keys."""
            # Try string key first (decode_responses=True)
            if key in data:
                return str(data[key])
            # Try bytes key (decode_responses=False)
            key_bytes = key.encode("utf-8")
            if key_bytes in data:
                value = data[key_bytes]
                if isinstance(value, bytes):
                    return value.decode("utf-8")
                return str(value)
            raise ValueError(f"Missing required field: {key}")

        return Project(
            project_id=ProjectId(get_str("project_id")),
            name=get_str("name"),
            description=get_str("description") or "",
            status=ProjectStatus(get_str("status")),
            owner=get_str("owner") or "",
            created_at=datetime.fromisoformat(get_str("created_at")),
            updated_at=datetime.fromisoformat(get_str("updated_at")),
        )

