"""Neo4j graph labels as domain value object."""

from enum import Enum


class GraphLabel(str, Enum):
    """Neo4j node labels used in context graph.

    These labels define the types of entities in our knowledge graph.
    Using an enum ensures type safety and prevents typos.
    """

    # Core entities
    STORY = "Story"  # Formerly Case
    TASK = "Task"  # Formerly Subtask
    EPIC = "Epic"  # Parent of Stories

    # Planning entities
    PLAN_VERSION = "PlanVersion"

    # Decision tracking
    DECISION = "Decision"

    # Actors
    ACTOR = "Actor"

    def __str__(self) -> str:
        """Return the string value for Neo4j queries."""
        return self.value

