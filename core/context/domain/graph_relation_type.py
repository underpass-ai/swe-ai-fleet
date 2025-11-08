"""Neo4j graph relationship types as domain value object."""

from enum import Enum


class GraphRelationType(str, Enum):
    """Neo4j relationship types used in context graph.

    These define the types of relationships between entities.
    Using an enum ensures type safety and prevents typos.
    """

    # Hierarchy relationships
    CONTAINS = "CONTAINS"  # Epic → Story
    HAS_PLAN = "HAS_PLAN"  # Story → PlanVersion
    HAS_TASK = "HAS_TASK"  # PlanVersion → Task (formerly HAS_SUBTASK)

    # Decision relationships
    AFFECTS = "AFFECTS"  # Decision → Task
    DEPENDS_ON = "DEPENDS_ON"  # Decision → Decision
    RELATES_TO = "RELATES_TO"  # Decision → Story/Epic

    # Actor relationships
    AUTHORED_BY = "AUTHORED_BY"  # Decision → Actor
    ASSIGNED_TO = "ASSIGNED_TO"  # Task → Actor

    # Dependency relationships
    PART_OF = "PART_OF"  # Task → Story (alternative hierarchy)
    BLOCKS = "BLOCKS"  # Task → Task

    def __str__(self) -> str:
        """Return the string value for Neo4j queries."""
        return self.value

