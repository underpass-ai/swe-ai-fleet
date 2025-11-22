"""Neo4j Cypher queries and constraints for Planning Service."""

from enum import Enum


class Neo4jConstraints:
    """
    Neo4j database constraints.

    Ensures data integrity at database level.
    """

    STORY_ID_UNIQUE = "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Story) REQUIRE s.id IS UNIQUE"
    USER_ID_UNIQUE = "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE"

    @classmethod
    def all(cls) -> list[str]:
        """Get all constraints."""
        return [
            cls.STORY_ID_UNIQUE,
            cls.USER_ID_UNIQUE,
        ]


class Neo4jQuery(str, Enum):
    """
    Cypher queries for Planning Service.

    Centralizes all Cypher queries in one place:
    - Easy to version and evolve
    - Easy to review for security (injection prevention)
    - Easy to optimize
    - Easy to test
    """

    CREATE_STORY_NODE = """
        // Create or update Story node (minimal properties)
        MERGE (s:Story {id: $story_id})
        SET s.state = $state

        // Create or get User node
        MERGE (u:User {id: $created_by})

        // Create CREATED_BY relationship
        MERGE (u)-[:CREATED]->(s)

        RETURN s
        """

    UPDATE_STORY_STATE = """
        MATCH (s:Story {id: $story_id})
        SET s.state = $state
        RETURN s
        """

    DELETE_STORY_NODE = """
        MATCH (s:Story {id: $story_id})
        DETACH DELETE s
        """

    GET_STORY_IDS_BY_STATE = """
        MATCH (s:Story {state: $state})
        RETURN s.id AS story_id
        ORDER BY s.id
        """

    RELATE_STORY_TO_USER = """
        MATCH (s:Story {id: $story_id})
        MERGE (u:User {id: $user_id})
        MERGE (u)-[:INVOLVED_IN {role: $relationship_type}]->(s)
        """

    CREATE_TASK_DEPENDENCY = """
        // Create DEPENDS_ON relationship between tasks
        MATCH (from:Task {id: $from_task_id})
        MATCH (to:Task {id: $to_task_id})
        MERGE (from)-[r:DEPENDS_ON]->(to)
        SET r.reason = $reason
        RETURN r
        """

