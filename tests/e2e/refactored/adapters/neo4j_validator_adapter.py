"""Neo4j validator adapter."""

from neo4j import AsyncGraphDatabase, AsyncDriver


class Neo4jValidatorAdapter:
    """Adapter for validating Neo4j graph data."""

    def __init__(self, uri: str, username: str, password: str) -> None:
        """Initialize adapter.
        
        Args:
            uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
        """
        if not uri:
            raise ValueError("uri cannot be empty")
        if not username:
            raise ValueError("username cannot be empty")
        if not password:
            raise ValueError("password cannot be empty")

        self._uri = uri
        self._username = username
        self._password = password
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        self._driver = AsyncGraphDatabase.driver(
            self._uri,
            auth=(self._username, self._password)
        )

    async def close(self) -> None:
        """Close connection."""
        if self._driver:
            await self._driver.close()

    async def validate_story_node_exists(
        self,
        story_id: str,
        expected_title: str,
        expected_phase: str
    ) -> bool:
        """Validate that a ProjectCase node exists with correct properties."""
        if not self._driver:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:ProjectCase {story_id: $story_id})
                RETURN s.title as title, s.current_phase as current_phase
                """,
                story_id=story_id
            )
            record = await result.single()

            if not record:
                raise AssertionError(f"Story node not found: {story_id}")

            if record["title"] != expected_title:
                raise AssertionError(
                    f"Title mismatch: expected '{expected_title}', got '{record['title']}'"
                )

            if record["current_phase"] != expected_phase:
                raise AssertionError(
                    f"Phase mismatch: expected '{expected_phase}', got '{record['current_phase']}'"
                )

            return True

    async def validate_decision_nodes_exist(
        self,
        story_id: str,
        min_decisions: int
    ) -> list[dict[str, str]]:
        """Validate that decision nodes exist for a story."""
        if not self._driver:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:ProjectCase {story_id: $story_id})-[:MADE_DECISION]->(d:ProjectDecision)
                RETURN d.decision_id as decision_id, d.title as title, 
                       d.decision_type as decision_type, d.made_by_role as made_by_role
                """,
                story_id=story_id
            )
            records = await result.data()

            if len(records) < min_decisions:
                raise AssertionError(
                    f"Expected at least {min_decisions} decisions, found {len(records)}"
                )

            return records

    async def validate_task_nodes_exist(
        self,
        story_id: str,
        min_tasks: int,
        expected_roles: list[str]
    ) -> list[dict[str, str]]:
        """Validate that task nodes exist for a story."""
        if not self._driver:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (s:ProjectCase {story_id: $story_id})-[:HAS_TASK]->(t:Task)
                RETURN t.task_id as task_id, t.role as role, 
                       t.description as description
                """,
                story_id=story_id
            )
            records = await result.data()

            if len(records) < min_tasks:
                raise AssertionError(
                    f"Expected at least {min_tasks} tasks, found {len(records)}"
                )

            # Validate that all expected roles have tasks
            found_roles = {record["role"] for record in records}
            missing_roles = set(expected_roles) - found_roles

            if missing_roles:
                raise AssertionError(
                    f"Missing tasks for roles: {missing_roles}"
                )

            return records

    async def validate_relationships_exist(
        self,
        story_id: str,
        relationship_type: str,
        min_count: int
    ) -> int:
        """Validate that relationships exist in the graph."""
        if not self._driver:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH (s:ProjectCase {{story_id: $story_id}})-[r:{relationship_type}]->(n)
                RETURN count(r) as count
                """,
                story_id=story_id
            )
            record = await result.single()
            count = record["count"] if record else 0

            if count < min_count:
                raise AssertionError(
                    f"Expected at least {min_count} {relationship_type} relationships, found {count}"
                )

            return count

    async def cleanup_story_data(self, story_id: str) -> None:
        """Clean up all data for a story (for test isolation)."""
        if not self._driver:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (s:ProjectCase {story_id: $story_id})
                DETACH DELETE s
                """,
                story_id=story_id
            )

