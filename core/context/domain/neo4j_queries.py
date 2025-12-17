"""Neo4j Cypher queries as domain constants.

All Neo4j queries are defined here for maintainability and testability.
Using string constants ensures queries are centralized and version-controlled.
"""

from enum import Enum


class Neo4jQuery(str, Enum):
    """Neo4j Cypher query templates.

    These queries define how we retrieve context data from the graph database.
    Parameterized with $placeholder syntax for safe query execution.

    Organized by:
    - Decision Graph Read Queries (for reports/analytics)
    - Write Queries (for projection use cases)
    """

    # ========================================
    # DECISION GRAPH READ QUERIES
    # ========================================

    # Get Epic by Story
    GET_EPIC_BY_STORY = """
MATCH (e:Epic)-[:CONTAINS_STORY]->(s:Story {story_id: $story_id})
RETURN e.epic_id AS epic_id, e.title AS title,
       e.description AS description, e.status AS status
LIMIT 1
    """

    # Get Plan by Story
    GET_PLAN_BY_STORY = """
MATCH (s:Story {story_id: $story_id})-[:HAS_PLAN]->(p:PlanVersion)
RETURN p.id AS plan_id, p.story_id AS story_id,
       p.version AS version, p.status AS status,
       p.author_id AS author_id, p.rationale AS rationale,
       p.created_at_ms AS created_at_ms
ORDER BY coalesce(p.version, 0) DESC
LIMIT 1
    """

    # List decisions by Story (supports both story_id and legacy case_id)
    LIST_DECISIONS_BY_STORY = """
MATCH (d:Decision)
WHERE d.story_id = $story_id OR d.case_id = $story_id OR d.id CONTAINS $story_id
OPTIONAL MATCH (d)-[:AUTHORED_BY]->(a:Actor)
RETURN d.id AS id, d.title AS title, d.rationale AS rationale,
       d.status AS status,
       coalesce(d.created_at_ms, 0) AS created_at_ms,
       coalesce(d.author_id, a.id, 'unknown') AS author_id
ORDER BY created_at_ms ASC, id ASC
    """

    # List decision dependencies
    LIST_DECISION_DEPENDENCIES = """
MATCH (s:Story {story_id: $story_id})-[:HAS_PLAN]->(:PlanVersion)-[:CONTAINS_DECISION]->(d1:Decision)
MATCH (d1)-[r]->(d2:Decision)
WHERE type(r) IS NOT NULL
RETURN d1.id AS src,
       type(r) AS rel,
       d2.id AS dst
    """

    # List decision impacts on tasks
    LIST_DECISION_IMPACTS = """
MATCH (s:Story {story_id: $story_id})-[:HAS_PLAN]->(:PlanVersion)-[:CONTAINS_DECISION]->(d:Decision)
MATCH (t:Task)-[:INFLUENCED_BY]->(d)
RETURN d.id AS did, t.id AS tid,
       t.title AS ttitle,
       t.role AS trole
ORDER BY did, tid
    """

    # ========================================
    # RBAC L3 - ROLE-FILTERED QUERIES
    # ========================================

    # List decision impacts filtered by role (RBAC L3 - Defense in Depth)
    LIST_DECISION_IMPACTS_BY_ROLE = """
MATCH (s:Story {story_id: $story_id})-[:HAS_PLAN]->(:PlanVersion)-[:CONTAINS_DECISION]->(d:Decision)
MATCH (t:Task)-[:INFLUENCED_BY]->(d)
WHERE t.role = $role
RETURN d.id AS did, t.id AS tid,
       t.title AS ttitle,
       t.role AS trole
ORDER BY did, tid
    """

    # Get tasks filtered by role
    GET_TASKS_BY_ROLE = """
MATCH (s:Story {story_id: $story_id})-[:HAS_PLAN]->(p:PlanVersion)-[:CONTAINS_TASK]->(t:Task)
WHERE t.role = $role
RETURN t.id AS task_id, t.title AS title, t.description AS description,
       t.role AS role, t.status AS status, t.type AS type
ORDER BY t.created_at_ms ASC
    """

    # Get decisions authored by role (approximate - uses author_id pattern)
    GET_DECISIONS_BY_ROLE = """
MATCH (s:Story {story_id: $story_id})-[:HAS_PLAN]->(:PlanVersion)-[:CONTAINS_DECISION]->(d:Decision)
MATCH (d)-[:AUTHORED_BY]->(a:Actor)
WHERE a.role = $role OR d.author_id CONTAINS $role
RETURN d.id AS id, d.title AS title, d.rationale AS rationale,
       d.status AS status, d.created_at_ms AS created_at_ms,
       coalesce(d.author_id, a.id) AS author_id
ORDER BY created_at_ms ASC
    """

    # Check if story is assigned to user (RBAC L2 authorization)
    CHECK_STORY_ASSIGNED_TO_USER = """
MATCH (s:Story {story_id: $story_id})
WHERE s.assigned_to = $user_id OR s.owner = $user_id
RETURN count(s) > 0 AS is_assigned
    """

    # Check if epic is assigned to user (RBAC L2 authorization)
    CHECK_EPIC_ASSIGNED_TO_USER = """
MATCH (e:Epic {epic_id: $epic_id})
WHERE e.assigned_to = $user_id OR e.owner = $user_id
RETURN count(e) > 0 AS is_assigned
    """

    # Check if story is in testing phase (RBAC L2 authorization)
    CHECK_STORY_IN_TESTING = """
MATCH (s:Story {story_id: $story_id})
WHERE s.status IN ['TESTING', 'QA_REVIEW', 'ACCEPTANCE_TESTING']
RETURN count(s) > 0 AS in_testing
    """

    # ========================================
    # WRITE QUERIES (Projection Use Cases)
    # ========================================

    # Story queries
    GET_STORY_BY_ID = """
        MATCH (s:Story {id: $story_id})
        RETURN s.id AS story_id, s.name AS name, s.title AS title,
               s.description AS description, s.acceptance_criteria AS acceptance_criteria,
               s.business_notes AS business_notes, s.created_by AS created_by
    """

    # Plan queries (legacy - for backward compatibility)
    GET_PLAN_FOR_STORY = """
        MATCH (s:Story {id: $story_id})-[:HAS_PLAN]->(p:PlanVersion)
        RETURN p.id AS plan_id, p.version AS version, p.story_id AS story_id
        ORDER BY p.version DESC
    """

    GET_PLAN_BY_ID = """
        MATCH (p:PlanVersion {id: $plan_id})
        RETURN p.id AS plan_id, p.version AS version, p.story_id AS story_id
    """

    # Task queries (formerly Subtask)
    GET_TASK_BY_ID = """
        MATCH (t:Task {id: $task_id})
        RETURN t.id AS task_id, t.title AS title, t.description AS description,
               t.status AS status, t.dependencies AS dependencies,
               t.assigned_to AS assigned_to, t.estimated_hours AS estimated_hours
    """

    GET_TASKS_FOR_STORY = """
        MATCH (s:Story {id: $story_id})-[:HAS_PLAN]->(p:PlanVersion)-[:HAS_TASK]->(t:Task)
        RETURN t.id AS task_id, t.title AS title, t.description AS description,
               t.status AS status, t.dependencies AS dependencies
        ORDER BY t.priority, t.id
    """

    # Task Decision Context Queries (from Backlog Review Ceremony)
    GET_TASK_DECISION_METADATA = """
        MATCH (p:Plan)-[ht:HAS_TASK]->(t:Task {id: $task_id})
        RETURN
          ht.decided_by AS decided_by,
          ht.decision_reason AS decision_reason,
          ht.council_feedback AS council_feedback,
          ht.decided_at AS decided_at,
          ht.source AS source
        LIMIT 1
    """

    # Epic queries
    GET_EPIC_FOR_STORY = """
        MATCH (e:Epic)-[:CONTAINS]->(s:Story {id: $story_id})
        RETURN e.id AS epic_id
    """

    GET_EPIC_BY_ID = """
        MATCH (e:Epic {id: $epic_id})
        RETURN e.id AS epic_id, e.title AS title, e.description AS description,
               e.business_notes AS business_notes
    """

    GET_STORIES_FOR_EPIC = """
        MATCH (e:Epic {id: $epic_id})-[:CONTAINS]->(s:Story)
        RETURN s.id AS story_id, s.title AS title, s.description AS description,
               s.status AS status
        ORDER BY s.priority, s.id
    """

    # Decision queries
    LIST_DECISIONS_FOR_STORY = """
        MATCH (s:Story {id: $story_id})<-[:RELATES_TO]-(d:Decision)
        RETURN d.id AS decision_id, d.title AS title, d.rationale AS rationale,
               d.status AS status, d.category AS category
        ORDER BY d.decided_at DESC
    """

    LIST_DECISIONS_FOR_EPIC = """
        MATCH (e:Epic {id: $epic_id})<-[:RELATES_TO]-(d:Decision)
        RETURN d.id AS decision_id, d.title AS title, d.rationale AS rationale,
               d.status AS status, d.category AS category
        ORDER BY d.decided_at DESC
    """

    GET_DECISIONS_AFFECTING_TASK = """
        MATCH (d:Decision)-[:AFFECTS]->(t:Task {id: $task_id})
        RETURN d.id AS decision_id, d.title AS title, d.summary AS summary,
               d.category AS category
        ORDER BY d.decided_at DESC
    """

    # Generic queries
    NODE_WITH_NEIGHBORS = """
        MATCH (n {id: $node_id})-[r*1..$depth]-(neighbor)
        RETURN n, collect(DISTINCT neighbor) AS neighbors, collect(DISTINCT r) AS relationships
    """

    # Get graph relationships with detailed node and relationship info
    GET_GRAPH_RELATIONSHIPS = """
        MATCH (n)
        WHERE n.project_id = $node_id OR n.epic_id = $node_id OR n.story_id = $node_id OR n.task_id = $node_id OR n.id = $node_id
        WITH n
        OPTIONAL MATCH path = (n)-[r*1..$depth]-(neighbor)
        WITH n, 
             collect(DISTINCT {
               node: neighbor,
               rel: last(r),
               path: path
             }) AS neighbors_data
        RETURN {
          node: {
            id: coalesce(n.project_id, n.epic_id, n.story_id, n.task_id, n.id),
            labels: labels(n),
            properties: properties(n)
          },
          neighbors: neighbors_data
        } AS result
    """

    def __str__(self) -> str:
        """Return the query string."""
        return self.value

