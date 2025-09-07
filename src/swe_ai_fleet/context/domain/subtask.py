# src/swe_ai_fleet/context/domain/subtask.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from swe_ai_fleet.context.domain.graph_relationship import GraphRelationship


@dataclass(frozen=True)
class Subtask:
    """Domain model representing a Subtask entity in the context graph.
    
    A Subtask represents a specific task within a plan that needs to be completed.
    It can have different types (development, testing, etc.) and status updates.
    """
    
    sub_id: str
    title: str
    type: str
    plan_id: str
    last_status: str | None = None
    
    @staticmethod
    def from_payload(payload: dict[str, Any]) -> Subtask:
        """Create a Subtask from event payload data."""
        return Subtask(
            sub_id=payload["sub_id"],
            title=payload.get("title", ""),
            type=payload.get("type", "task"),
            plan_id=payload["plan_id"]
        )
    
    @staticmethod
    def from_status_payload(payload: dict[str, Any]) -> Subtask:
        """Create a Subtask from status update payload data."""
        return Subtask(
            sub_id=payload["sub_id"],
            title="",  # Not provided in status updates
            type="task",  # Default type
            plan_id="",  # Not provided in status updates
            last_status=payload.get("status")
        )
    
    @staticmethod
    def from_status_update_payload(payload: dict[str, Any]) -> Subtask:
        """Create a Subtask from status update payload data (alias for from_status_payload)."""
        return Subtask.from_status_payload(payload)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert Subtask to dictionary representation."""
        return {
            "sub_id": self.sub_id,
            "title": self.title,
            "type": self.type,
            "plan_id": self.plan_id,
            "last_status": self.last_status,
        }
    
    def to_graph_properties(self) -> dict[str, Any]:
        """Convert Subtask to properties suitable for graph storage."""
        props = {}
        
        # For status-only updates (when plan_id is empty), only include last_status
        if self.plan_id == "":
            if self.last_status is not None:
                props["last_status"] = self.last_status
            else:
                props["last_status"] = None
        else:
            # For regular subtasks, include title and type
            props["title"] = self.title
            props["type"] = self.type
            if self.last_status is not None:
                props["last_status"] = self.last_status
                
        return props
    
    def get_relationship_to_plan(self) -> GraphRelationship:
        """Get the relationship details to connect this subtask to its plan."""
        return GraphRelationship(
            src_id=self.plan_id,
            rel_type="HAS_SUBTASK",
            dst_id=self.sub_id,
            src_labels=["PlanVersion"],
            dst_labels=["Subtask"]
        )
    
    def update_status(self, new_status: str | None) -> Subtask:
        """Create a new Subtask instance with updated status."""
        return Subtask(
            sub_id=self.sub_id,
            title=self.title,
            type=self.type,
            plan_id=self.plan_id,
            last_status=new_status
        )
