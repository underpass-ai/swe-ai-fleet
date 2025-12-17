"""Neo4j Cypher queries for workflow state persistence.

Centralizes all Cypher queries in one place.
Following Single Source of Truth principle.
"""

from enum import Enum


class Neo4jWorkflowQueries(str, Enum):
    """Neo4j Cypher queries for workflow operations.

    Centralized query repository for:
    - Maintainability (update queries in one place)
    - Testability (mock queries easily)
    - Documentation (queries serve as schema documentation)
    """

    GET_WORKFLOW_STATE = """
        MATCH (t:Task {id: $task_id})-[:HAS_WORKFLOW_STATE]->(ws:WorkflowState)
        OPTIONAL MATCH (ws)-[:HAS_TRANSITION]->(st:StateTransition)
        RETURN ws, collect(st) as transitions
        ORDER BY st.timestamp ASC
    """

    SAVE_WORKFLOW_STATE = """
        MATCH (t:Task {id: $task_id})
        MERGE (t)-[:HAS_WORKFLOW_STATE]->(ws:WorkflowState {task_id: $task_id})
        SET ws.story_id = $story_id,
            ws.current_state = $current_state,
            ws.role_in_charge = $role_in_charge,
            ws.required_action = $required_action,
            ws.feedback = $feedback,
            ws.updated_at = $updated_at,
            ws.retry_count = $retry_count

        WITH ws
        UNWIND $transitions as trans
        CREATE (ws)-[:HAS_TRANSITION]->(st:StateTransition)
        SET st = trans
    """

    GET_PENDING_BY_ROLE = """
        MATCH (t:Task)-[:HAS_WORKFLOW_STATE]->(ws:WorkflowState)
        WHERE ws.role_in_charge = $role
        AND ws.current_state IN [
            'pending_arch_review', 'arch_reviewing',
            'pending_qa', 'qa_testing',
            'pending_po_approval'
        ]
        OPTIONAL MATCH (ws)-[:HAS_TRANSITION]->(st:StateTransition)
        WITH ws, collect(st) as transitions
        ORDER BY ws.updated_at ASC
        LIMIT $limit
        RETURN ws, transitions
    """

    GET_ALL_BY_STORY = """
        MATCH (t:Task)-[:HAS_WORKFLOW_STATE]->(ws:WorkflowState {story_id: $story_id})
        OPTIONAL MATCH (ws)-[:HAS_TRANSITION]->(st:StateTransition)
        WITH ws, collect(st) as transitions
        ORDER BY ws.updated_at ASC
        RETURN ws, transitions
    """

    GET_ALL_STATES = """
        MATCH (t:Task)-[:HAS_WORKFLOW_STATE]->(ws:WorkflowState)
        WHERE ($story_id IS NULL OR ws.story_id = $story_id)
        AND ($role IS NULL OR ws.role_in_charge = $role)
        OPTIONAL MATCH (ws)-[:HAS_TRANSITION]->(st:StateTransition)
        WITH ws, collect(st) as transitions
        ORDER BY ws.updated_at ASC
        RETURN ws, transitions
    """

    DELETE_WORKFLOW_STATE = """
        MATCH (t:Task {id: $task_id})-[:HAS_WORKFLOW_STATE]->(ws:WorkflowState)
        OPTIONAL MATCH (ws)-[:HAS_TRANSITION]->(st:StateTransition)
        DETACH DELETE ws, st
    """

    def __str__(self) -> str:
        """String representation (returns the query)."""
        return self.value

