# core/context/domain/domain_event.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DomainEvent:
    """Base domain event representing something that happened in the system.

    Domain events are immutable representations of business events that have occurred.
    They serve as the input to the projector use cases.
    """

    event_type: str
    payload: dict[str, Any]

    @staticmethod
    def case_created(case_id: str, name: str = "") -> DomainEvent:
        """Create a case.created domain event."""
        return DomainEvent(event_type="case.created", payload={"case_id": case_id, "name": name})

    @staticmethod
    def plan_versioned(case_id: str, plan_id: str, version: int = 1) -> DomainEvent:
        """Create a plan.versioned domain event."""
        return DomainEvent(
            event_type="plan.versioned", payload={"case_id": case_id, "plan_id": plan_id, "version": version}
        )

    @staticmethod
    def subtask_created(plan_id: str, sub_id: str, title: str = "", type: str = "task") -> DomainEvent:
        """Create a subtask.created domain event."""
        return DomainEvent(
            event_type="subtask.created",
            payload={"plan_id": plan_id, "sub_id": sub_id, "title": title, "type": type},
        )

    @staticmethod
    def subtask_status_changed(sub_id: str, status: str | None) -> DomainEvent:
        """Create a subtask.status_changed domain event."""
        return DomainEvent(event_type="subtask.status_changed", payload={"sub_id": sub_id, "status": status})

    @staticmethod
    def decision_made(
        node_id: str, kind: str = "", summary: str = "", sub_id: str | None = None
    ) -> DomainEvent:
        """Create a decision.made domain event."""
        payload = {"node_id": node_id, "kind": kind, "summary": summary}
        if sub_id is not None:
            payload["sub_id"] = sub_id
        return DomainEvent(event_type="decision.made", payload=payload)

    def to_dict(self) -> dict[str, Any]:
        """Convert DomainEvent to dictionary representation."""
        return {
            "event_type": self.event_type,
            "payload": self.payload,
        }

    def get_entity_id(self) -> str | None:
        """Extract the primary entity ID from the event payload."""
        # For different event types, return the appropriate entity ID
        if self.event_type == "case.created":
            return self.payload.get("case_id")
        elif self.event_type == "plan.versioned":
            return self.payload.get("plan_id")
        elif self.event_type == "subtask.created":
            return self.payload.get("sub_id")
        elif self.event_type == "subtask.status_changed":
            return self.payload.get("sub_id")
        elif self.event_type == "decision.made":
            return self.payload.get("node_id")

        # Fallback to generic ID fields
        id_fields = ["case_id", "plan_id", "sub_id", "node_id"]
        for field in id_fields:
            if field in self.payload:
                return self.payload[field]
        return None
