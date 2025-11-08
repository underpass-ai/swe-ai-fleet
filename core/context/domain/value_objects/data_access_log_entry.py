"""DataAccessLogEntry Value Object - Audit log for data access (RBAC L3)."""

from dataclasses import dataclass
from datetime import datetime

from core.context.domain.role import Role
from core.context.domain.entity_ids.story_id import StoryId


@dataclass(frozen=True)
class DataAccessLogEntry:
    """Audit log entry for data access.

    Records who accessed what data, when, and with which role.
    Critical for RBAC L3 compliance and security audits.

    Immutable by design (frozen=True) - audit logs must not be modified.
    """

    user_id: str
    role: Role
    story_id: StoryId
    accessed_at: datetime

    # What was accessed
    accessed_entities: dict[str, int]  # entity_type → count (e.g., {"task": 5, "decision": 12})

    # Access result
    access_granted: bool
    denial_reason: str | None = None  # If access denied, why?

    # Context
    source_ip: str | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        """Validate audit log entry.

        Raises:
            ValueError: If validation fails
        """
        if not self.user_id:
            raise ValueError("user_id is required for audit logging")

        if self.accessed_at > datetime.now():
            raise ValueError("accessed_at cannot be in the future")

        # If access denied, denial_reason must be provided
        if not self.access_granted and not self.denial_reason:
            raise ValueError("denial_reason is required when access_granted=False")

    def was_denied(self) -> bool:
        """Check if access was denied.

        Returns:
            True if access was denied
        """
        return not self.access_granted

    def was_granted(self) -> bool:
        """Check if access was granted.

        Returns:
            True if access was granted
        """
        return self.access_granted

    def get_total_entities_accessed(self) -> int:
        """Get total count of entities accessed.

        Returns:
            Sum of all entity counts
        """
        return sum(self.accessed_entities.values())

    def accessed_entity_type(self, entity_type: str) -> bool:
        """Check if specific entity type was accessed.

        Args:
            entity_type: Entity type to check (e.g., "task", "decision")

        Returns:
            True if entity type was accessed
        """
        return entity_type in self.accessed_entities

    def get_log_message(self) -> str:
        """Get human-readable log message.

        Returns:
            Formatted log message for audit trail
        """
        status = "GRANTED" if self.access_granted else "DENIED"
        entity_summary = ", ".join(
            f"{count} {entity_type}(s)"
            for entity_type, count in self.accessed_entities.items()
        )

        msg = (
            f"[{status}] User {self.user_id} (role={self.role.value}) "
            f"accessed story {self.story_id.to_string()}: {entity_summary}"
        )

        if self.denial_reason:
            msg += f" | Reason: {self.denial_reason}"

        return msg

