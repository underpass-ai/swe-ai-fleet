"""Neo4j Cypher queries and constraints for Planning Service."""

from enum import Enum


class Neo4jConstraints:
    """
    Neo4j database constraints.

    Ensures data integrity at database level.
    """

    STORY_ID_UNIQUE = "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Story) REQUIRE s.id IS UNIQUE"
    USER_ID_UNIQUE = "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE"
    PROJECT_ID_UNIQUE = "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE"
    EPIC_ID_UNIQUE = "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Epic) REQUIRE e.id IS UNIQUE"
    TASK_ID_UNIQUE = "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE"

    @classmethod
    def all(cls) -> list[str]:
        """Get all constraints."""
        return [
            cls.STORY_ID_UNIQUE,
            cls.USER_ID_UNIQUE,
            cls.PROJECT_ID_UNIQUE,
            cls.EPIC_ID_UNIQUE,
            cls.TASK_ID_UNIQUE,
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

    CREATE_PROJECT_NODE = """
        // Create or update Project node (minimal properties for graph structure)
        MERGE (p:Project {id: $project_id})
        SET p.project_id = $project_id,
            p.name = $name,
            p.status = $status,
            p.created_at = $created_at,
            p.updated_at = $updated_at
        RETURN p
        """

    UPDATE_PROJECT_STATUS = """
        MATCH (p:Project {id: $project_id})
        SET p.status = $status,
            p.updated_at = $updated_at
        RETURN p
        """

    GET_PROJECT_IDS_BY_STATUS = """
        MATCH (p:Project {status: $status})
        RETURN p.id AS project_id
        ORDER BY p.created_at DESC
        """

    CREATE_EPIC_NODE = """
        // Create or update Epic node
        MERGE (e:Epic {id: $epic_id})
        SET e.name = $name,
            e.status = $status,
            e.created_at = $created_at,
            e.updated_at = $updated_at

        // Link to Project
        WITH e
        MATCH (p:Project {id: $project_id})
        MERGE (e)-[:BELONGS_TO]->(p)
        RETURN e
        """

    UPDATE_EPIC_STATUS = """
        MATCH (e:Epic {id: $epic_id})
        SET e.status = $status,
            e.updated_at = $updated_at
        RETURN e
        """

    GET_EPIC_IDS_BY_PROJECT = """
        MATCH (e:Epic)-[:BELONGS_TO]->(p:Project {id: $project_id})
        RETURN e.id AS epic_id
        ORDER BY e.created_at DESC
        """

    CREATE_TASK_NODE = """
        // Create or update Task node (minimal properties for graph structure)
        MERGE (t:Task {id: $task_id})
        SET t.status = $status,
            t.type = $type

        // Link to Story (REQUIRED - domain invariant)
        WITH t
        MATCH (s:Story {id: $story_id})
        MERGE (s)-[:HAS_TASK]->(t)

        RETURN t
        """

    CREATE_TASK_PLAN_RELATIONSHIP = """
        // Link Task to Plan (OPTIONAL - only called if plan_id exists)
        MATCH (t:Task {id: $task_id})
        MATCH (p:Plan {id: $plan_id})
        MERGE (p)-[:HAS_TASK]->(t)
        RETURN t
        """

    GET_TASK_IDS_BY_STORY = """
        MATCH (s:Story {id: $story_id})-[:HAS_TASK]->(t:Task)
        RETURN t.id AS task_id
        ORDER BY t.created_at ASC
        """

    GET_TASK_IDS_BY_PLAN = """
        MATCH (p:Plan {id: $plan_id})-[:HAS_TASK]->(t:Task)
        RETURN t.id AS task_id
        ORDER BY t.id ASC
        """

