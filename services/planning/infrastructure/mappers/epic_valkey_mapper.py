"""Mapper: Domain Epic ↔ Valkey dict format."""

from datetime import datetime

from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus


class EpicValkeyMapper:
    """
    Mapper: Convert domain Epic to/from Valkey dict format.

    Infrastructure Layer Responsibility:
    - Domain entities should not know about Redis hash format
    - Conversions live in dedicated mappers (Hexagonal Architecture)

    Following the same pattern as ProjectValkeyMapper for consistency.
    """

    @staticmethod
    def to_dict(epic: Epic) -> dict[str, str]:
        """
        Convert domain Epic to Valkey hash dict.

        Args:
            epic: Domain Epic entity.

        Returns:
            Dict suitable for Redis HSET (all values as strings).
        """
        return {
            "epic_id": epic.epic_id.value,
            "project_id": epic.project_id.value,
            "title": epic.title,
            "description": epic.description or "",
            "status": epic.status.value,  # Enum string value
            "created_at": epic.created_at.isoformat(),
            "updated_at": epic.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[str, str] | dict[bytes, bytes]) -> Epic:
        """
        Convert Valkey hash dict to domain Epic.

        Args:
            data: Redis hash data (string keys/values if decode_responses=True,
                  bytes keys/values if decode_responses=False).

        Returns:
            Domain Epic entity.

        Raises:
            ValueError: If data is invalid or missing required fields.
        """
        if not data:
            raise ValueError("Cannot create Epic from empty dict")

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

        return Epic(
            epic_id=EpicId(get_str("epic_id")),
            project_id=ProjectId(get_str("project_id")),
            title=get_str("title"),
            description=get_str("description") or "",
            status=EpicStatus(get_str("status")),
            created_at=datetime.fromisoformat(get_str("created_at")),
            updated_at=datetime.fromisoformat(get_str("updated_at")),
        )

