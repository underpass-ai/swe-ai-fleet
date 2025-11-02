"""Port for Neo4j validation operations."""

from typing import Protocol


class Neo4jValidatorPort(Protocol):
    """Interface for Neo4j graph database validation."""

    async def validate_story_node_exists(
        self,
        story_id: str,
        expected_title: str,
        expected_phase: str
    ) -> bool:
        """Validate that a ProjectCase node exists with correct properties.
        
        Args:
            story_id: Story identifier to find
            expected_title: Expected title value
            expected_phase: Expected current_phase value
            
        Returns:
            True if node exists and properties match
            
        Raises:
            AssertionError: If validation fails
        """
        ...

    async def validate_decision_nodes_exist(
        self,
        story_id: str,
        min_decisions: int
    ) -> list[dict[str, str]]:
        """Validate that decision nodes exist for a story.
        
        Args:
            story_id: Story identifier
            min_decisions: Minimum number of decisions expected
            
        Returns:
            List of decision nodes with their properties
            
        Raises:
            AssertionError: If validation fails
        """
        ...

    async def validate_task_nodes_exist(
        self,
        story_id: str,
        min_tasks: int,
        expected_roles: list[str]
    ) -> list[dict[str, str]]:
        """Validate that task nodes exist for a story.
        
        Args:
            story_id: Story identifier
            min_tasks: Minimum number of tasks expected
            expected_roles: Roles that should have tasks
            
        Returns:
            List of task nodes with their properties
            
        Raises:
            AssertionError: If validation fails
        """
        ...

    async def validate_relationships_exist(
        self,
        story_id: str,
        relationship_type: str,
        min_count: int
    ) -> int:
        """Validate that relationships exist in the graph.
        
        Args:
            story_id: Story identifier
            relationship_type: Type of relationship (HAS_DECISION, HAS_TASK, etc.)
            min_count: Minimum number of relationships expected
            
        Returns:
            Actual count of relationships found
            
        Raises:
            AssertionError: If validation fails
        """
        ...

    async def cleanup_story_data(self, story_id: str) -> None:
        """Clean up all data for a story (for test isolation).
        
        Args:
            story_id: Story identifier to clean up
        """
        ...

