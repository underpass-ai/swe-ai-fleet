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
    CEREMONY_ID_UNIQUE = "CREATE CONSTRAINT IF NOT EXISTS FOR (c:BacklogReviewCeremony) REQUIRE c.id IS UNIQUE"

    @classmethod
    def all(cls) -> list[str]:
        """Get all constraints."""
        return [
            cls.STORY_ID_UNIQUE,
            cls.USER_ID_UNIQUE,
            cls.PROJECT_ID_UNIQUE,
            cls.EPIC_ID_UNIQUE,
            cls.TASK_ID_UNIQUE,
            cls.CEREMONY_ID_UNIQUE,
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
        SET s.state = $state,
            s.title = $title

        // Create or get User node
        MERGE (u:User {id: $created_by})

        // Create CREATED_BY relationship
        MERGE (u)-[:CREATED]->(s)

        // Link to Epic (REQUIRED - domain invariant)
        WITH s
        MATCH (e:Epic {id: $epic_id})
        MERGE (s)-[:BELONGS_TO]->(e)

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

    # ========== Backlog Review Ceremony Queries ==========

    CREATE_CEREMONY_NODE = """
        // Create or update BacklogReviewCeremony node
        MERGE (c:BacklogReviewCeremony {id: $ceremony_id})
        SET c.ceremony_id = $ceremony_id,
            c.created_by = $created_by,
            c.status = $status,
            c.created_at = $created_at,
            c.updated_at = $updated_at,
            c.started_at = $started_at,
            c.completed_at = $completed_at,
            c.story_count = $story_count,
            c.review_results_json = COALESCE($review_results_json, '[]')
        RETURN c
        """

    CREATE_CEREMONY_STORY_RELATIONSHIP = """
        // Link Ceremony to Story (REVIEWS relationship)
        MATCH (c:BacklogReviewCeremony {id: $ceremony_id})
        MATCH (s:Story {id: $story_id})
        MERGE (c)-[:REVIEWS]->(s)
        RETURN c
        """

    CREATE_CEREMONY_PROJECT_RELATIONSHIP = """
        // Link Ceremony to Project (BELONGS_TO relationship)
        MATCH (c:BacklogReviewCeremony {id: $ceremony_id})
        MATCH (p:Project {id: $project_id})
        MERGE (c)-[:BELONGS_TO]->(p)
        RETURN c
        """

    GET_PROJECT_FROM_STORY = """
        // Get project_id from story (Story → Epic → Project)
        MATCH (s:Story {id: $story_id})
        MATCH (s)-[:BELONGS_TO]->(e:Epic)
        MATCH (e)-[:BELONGS_TO]->(p:Project)
        RETURN p.id AS project_id
        LIMIT 1
        """

    GET_CEREMONY_NODE = """
        // Get ceremony node with properties and related story IDs
        MATCH (c:BacklogReviewCeremony {id: $ceremony_id})
        OPTIONAL MATCH (c)-[:REVIEWS]->(s:Story)
        WITH c, collect(s.id) AS story_ids
        RETURN {
            properties: {
                ceremony_id: c.ceremony_id,
                created_by: c.created_by,
                status: c.status,
                created_at: c.created_at,
                updated_at: c.updated_at,
                started_at: c.started_at,
                completed_at: COALESCE(c.completed_at, null),
                story_count: c.story_count
            },
            story_ids: story_ids,
            review_results_json: COALESCE(c.review_results_json, '[]')
        } AS result
        """

    LIST_CEREMONY_NODES = """
        // List ceremony nodes with pagination
        MATCH (c:BacklogReviewCeremony)
        OPTIONAL MATCH (c)-[:REVIEWS]->(s:Story)
        WITH c, collect(s.id) AS story_ids
        RETURN {
            properties: {
                ceremony_id: c.ceremony_id,
                created_by: c.created_by,
                status: c.status,
                created_at: c.created_at,
                updated_at: c.updated_at,
                started_at: c.started_at,
                completed_at: COALESCE(c.completed_at, null),
                story_count: c.story_count
            },
            story_ids: story_ids,
            review_results_json: COALESCE(c.review_results_json, '[]')
        } AS result
        ORDER BY c.created_at DESC
        SKIP $offset
        LIMIT $limit
        """

