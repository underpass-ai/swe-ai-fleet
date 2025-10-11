"""Fixtures for Context Service integration tests."""

import json
import os
import time

import pytest
from neo4j import GraphDatabase
from redis import Redis


@pytest.fixture(scope="module")
def neo4j_connection():
    """Create Neo4j connection for integration tests."""
    # Use test database connection
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "testpassword")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # Verify connection
    try:
        with driver.session() as session:
            session.run("RETURN 1")
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
    
    yield driver
    
    # Cleanup
    driver.close()


@pytest.fixture(scope="module")
def redis_connection():
    """Create Redis connection for integration tests."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    
    client = Redis(host=host, port=port, decode_responses=True)
    
    # Verify connection
    try:
        client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")
    
    yield client
    
    # No cleanup needed - each test should clean up after itself


@pytest.fixture
def clean_test_case(neo4j_connection, redis_connection):
    """Create and cleanup a test case."""
    case_id = f"INT-TEST-{int(time.time() * 1000)}"
    
    # Setup: Create minimal case structure in Neo4j
    with neo4j_connection.session() as session:
        session.run("""
            CREATE (c:Case {
                id: $case_id,
                title: 'Integration Test Case',
                status: 'IN_PROGRESS'
            })
            CREATE (p:PlanVersion {
                id: $plan_id,
                case_id: $case_id,
                version: 1,
                status: 'APPROVED'
            })
            CREATE (c)-[:HAS_PLAN]->(p)
        """, case_id=case_id, plan_id=f"PLAN-{case_id}")
    
    # Setup: Create case spec in Redis
    spec = {
        "case_id": case_id,
        "title": "Integration Test Case",
        "description": "Test case for integration tests",
        "acceptance_criteria": ["Test criterion"],
        "constraints": {},
        "requester_id": "test-system",
        "tags": ["integration-test"],
        "created_at_ms": int(time.time() * 1000)
    }
    redis_connection.set(f"swe:case:{case_id}:spec", json.dumps(spec))
    
    yield case_id
    
    # Cleanup: Remove from Neo4j
    with neo4j_connection.session() as session:
        session.run("""
            MATCH (c:Case {id: $case_id})
            OPTIONAL MATCH (c)-[:HAS_PLAN]->(p:PlanVersion)
            OPTIONAL MATCH (p)-[:CONTAINS_DECISION]->(d:Decision)
            OPTIONAL MATCH (p)-[:HAS_SUBTASK]->(s:Subtask)
            OPTIONAL MATCH (e:Event {case_id: $case_id})
            DETACH DELETE c, p, d, s, e
        """, case_id=case_id)
    
    # Cleanup: Remove from Redis
    keys_to_delete = redis_connection.keys(f"swe:case:{case_id}:*")
    if keys_to_delete:
        redis_connection.delete(*keys_to_delete)

