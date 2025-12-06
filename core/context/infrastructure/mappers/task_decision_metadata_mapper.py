"""Mapper for TaskDecisionMetadata - Infrastructure layer.

Handles conversion between Neo4j records and TaskDecisionMetadata domain value object.
Following Hexagonal Architecture: Infrastructure layer responsibility.
"""

from typing import Any

from core.context.domain.task_decision_metadata import TaskDecisionMetadata


class TaskDecisionMetadataMapper:
    """Mapper for TaskDecisionMetadata conversions.

    Infrastructure Layer Responsibility:
    - Convert Neo4j query results to domain value objects
    - Handle missing fields with sensible defaults
    - Apply defensive programming (infrastructure concern)

    Does NOT mutate domain objects or use reflection.
    """

    @staticmethod
    def from_neo4j_record(record: dict[str, Any]) -> TaskDecisionMetadata:
        """Create TaskDecisionMetadata from Neo4j HAS_TASK relationship properties.

        This mapper extracts decision metadata from the HAS_TASK relationship properties
        that are created by Planning Service's Backlog Review Ceremony (FASE 1+2).

        Args:
            record: Neo4j query result record with relationship properties

        Returns:
            TaskDecisionMetadata domain value object

        Raises:
            ValueError: If domain value object validation fails
        """
        # Extract fields with defensive defaults (infrastructure concern)
        # Planning Service should always provide these, but we handle missing gracefully
        decided_by = record.get("decided_by", "UNKNOWN")
        decision_reason = record.get("decision_reason", "No reason provided")
        council_feedback = record.get("council_feedback", "No feedback available")
        decided_at = record.get("decided_at", "UNKNOWN")
        source = record.get("source", "UNKNOWN")

        # Domain value object will validate invariants in __post_init__
        # If validation fails, ValueError will be raised (fail-fast)
        return TaskDecisionMetadata(
            decided_by=decided_by,
            decision_reason=decision_reason,
            council_feedback=council_feedback,
            decided_at=decided_at,
            source=source,
        )



