"""Neo4j Cypher queries for Ceremony Engine.

Following Hexagonal Architecture:
- Queries are infrastructure concerns
- Centralized for maintainability and testability
"""

from enum import Enum


class CeremonyInstanceNeo4jQueries(str, Enum):
    """Cypher queries for CeremonyInstance operations."""

    # Create/Update CeremonyInstance node
    MERGE_CEREMONY_INSTANCE = """
        MERGE (ci:CeremonyInstance {instance_id: $instance_id})
        SET ci.definition_name = $definition_name,
            ci.current_state = $current_state,
            ci.step_status_json = $step_status_json,
            ci.correlation_id = $correlation_id,
            ci.idempotency_keys_json = $idempotency_keys_json,
            ci.created_at = $created_at,
            ci.updated_at = $updated_at
        RETURN ci
    """

    # Load CeremonyInstance by ID
    GET_CEREMONY_INSTANCE = """
        MATCH (ci:CeremonyInstance {instance_id: $instance_id})
        RETURN ci
    """

    # Find instances by correlation_id
    FIND_BY_CORRELATION_ID = """
        MATCH (ci:CeremonyInstance {correlation_id: $correlation_id})
        RETURN ci
        ORDER BY ci.created_at ASC
    """

    # Count ceremony instances with optional filters
    COUNT_CEREMONY_INSTANCES = """
        MATCH (ci:CeremonyInstance)
        WHERE ($state_filter IS NULL OR toLower(ci.current_state) = toLower($state_filter))
          AND ($definition_filter IS NULL OR toLower(ci.definition_name) = toLower($definition_filter))
          AND ($story_id IS NULL OR last(split(ci.instance_id, ':')) = $story_id)
        RETURN count(ci) AS total
    """

    # List ceremony instances with optional filters and pagination
    LIST_CEREMONY_INSTANCES = """
        MATCH (ci:CeremonyInstance)
        WHERE ($state_filter IS NULL OR toLower(ci.current_state) = toLower($state_filter))
          AND ($definition_filter IS NULL OR toLower(ci.definition_name) = toLower($definition_filter))
          AND ($story_id IS NULL OR last(split(ci.instance_id, ':')) = $story_id)
        RETURN ci
        ORDER BY ci.created_at DESC
        SKIP $offset
        LIMIT $limit
    """

    # Create relationship: CeremonyInstance -> CeremonyDefinition (by name)
    # Note: CeremonyDefinition nodes are created separately if needed
    CREATE_DEFINITION_RELATIONSHIP = """
        MATCH (ci:CeremonyInstance {instance_id: $instance_id})
        MERGE (cd:CeremonyDefinition {name: $definition_name})
        MERGE (ci)-[:INSTANCE_OF]->(cd)
    """
