"""Unit tests for Neo4j queries and constraints."""


from planning.infrastructure.adapters.neo4j_queries import Neo4jConstraints, Neo4jQuery


def test_neo4j_constraints_story_id_unique():
    """Test STORY_ID_UNIQUE constraint is defined."""
    assert "Story" in Neo4jConstraints.STORY_ID_UNIQUE
    assert "UNIQUE" in Neo4jConstraints.STORY_ID_UNIQUE
    assert "s.id" in Neo4jConstraints.STORY_ID_UNIQUE


def test_neo4j_constraints_user_id_unique():
    """Test USER_ID_UNIQUE constraint is defined."""
    assert "User" in Neo4jConstraints.USER_ID_UNIQUE
    assert "UNIQUE" in Neo4jConstraints.USER_ID_UNIQUE
    assert "u.id" in Neo4jConstraints.USER_ID_UNIQUE


def test_neo4j_constraints_all():
    """Test Neo4jConstraints.all() returns all constraints."""
    constraints = Neo4jConstraints.all()

    assert isinstance(constraints, list)
    assert len(constraints) == 4
    assert Neo4jConstraints.STORY_ID_UNIQUE in constraints
    assert Neo4jConstraints.USER_ID_UNIQUE in constraints
    assert Neo4jConstraints.PROJECT_ID_UNIQUE in constraints
    assert Neo4jConstraints.EPIC_ID_UNIQUE in constraints


def test_neo4j_query_create_story_node_structure():
    """Test CREATE_STORY_NODE query structure."""
    query = Neo4jQuery.CREATE_STORY_NODE.value

    # Verify it's a MERGE query (idempotent)
    assert "MERGE" in query
    assert "Story" in query
    assert "$story_id" in query
    assert "$state" in query
    assert "$created_by" in query

    # Verify it creates User node
    assert "User" in query

    # Verify it creates relationship
    assert "CREATED" in query or "[:CREATED]" in query


def test_neo4j_query_update_story_state_structure():
    """Test UPDATE_STORY_STATE query structure."""
    query = Neo4jQuery.UPDATE_STORY_STATE.value

    # Verify it's a MATCH + SET query
    assert "MATCH" in query
    assert "SET" in query
    assert "Story" in query
    assert "$story_id" in query
    assert "$state" in query
    assert "RETURN" in query


def test_neo4j_query_delete_story_node_structure():
    """Test DELETE_STORY_NODE query structure."""
    query = Neo4jQuery.DELETE_STORY_NODE.value

    # Verify it's a MATCH + DELETE query
    assert "MATCH" in query
    assert "DELETE" in query
    assert "DETACH DELETE" in query  # Ensures relationships are deleted
    assert "Story" in query
    assert "$story_id" in query


def test_neo4j_query_get_story_ids_by_state_structure():
    """Test GET_STORY_IDS_BY_STATE query structure."""
    query = Neo4jQuery.GET_STORY_IDS_BY_STATE.value

    # Verify it's a MATCH + RETURN query
    assert "MATCH" in query
    assert "RETURN" in query
    assert "Story" in query
    assert "$state" in query
    assert "story_id" in query

    # Should have ORDER BY for consistent results
    assert "ORDER BY" in query


def test_neo4j_query_relate_story_to_user_structure():
    """Test RELATE_STORY_TO_USER query structure."""
    query = Neo4jQuery.RELATE_STORY_TO_USER.value

    # Verify it's a MATCH + MERGE query
    assert "MATCH" in query
    assert "MERGE" in query
    assert "Story" in query
    assert "User" in query
    assert "$story_id" in query
    assert "$user_id" in query
    assert "$relationship_type" in query
    assert "INVOLVED_IN" in query


def test_all_queries_are_string_enum():
    """Test that all queries are string enums."""
    for query in Neo4jQuery:
        assert isinstance(query.value, str)
        assert len(query.value) > 0


def test_all_queries_use_parameterized_queries():
    """Test that all queries use parameters (prevent injection)."""
    for query in Neo4jQuery:
        # All queries should use $param syntax (parameterized)
        # This prevents SQL/Cypher injection
        if "MATCH" in query.value or "MERGE" in query.value:
            # Queries with MATCH/MERGE should use parameters
            assert "$" in query.value, f"{query.name} should use parameterized queries"


def test_neo4j_query_enum_has_all_operations():
    """Test that Neo4jQuery enum has all CRUD operations."""
    query_names = [q.name for q in Neo4jQuery]

    # Verify we have queries for all operations
    assert "CREATE_STORY_NODE" in query_names
    assert "UPDATE_STORY_STATE" in query_names
    assert "DELETE_STORY_NODE" in query_names
    assert "GET_STORY_IDS_BY_STATE" in query_names
    assert "RELATE_STORY_TO_USER" in query_names

