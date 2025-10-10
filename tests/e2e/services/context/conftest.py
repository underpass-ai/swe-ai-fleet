"""
Fixtures for Context Service E2E tests.
Tests assume services are running via docker-compose.e2e.yml:
  podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml up -d
"""

import json
import time

import grpc
import pytest
from neo4j import GraphDatabase
from redis import Redis


# ============================================================================
# CLIENT FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def neo4j_client():
    """Create Neo4j client for seeding data."""
    # Use service name when running in container, localhost for local dev
    import os
    host = os.getenv("NEO4J_HOST", "localhost")
    port = 7687 if host == "neo4j" else 17687
    uri = f"bolt://{host}:{port}"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "testpassword"))
    
    # Wait for Neo4j to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            break
        except Exception:
            if i == max_retries - 1:
                pytest.skip("Neo4j not available. Run: podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml up -d")
            time.sleep(1)
    
    yield driver
    
    driver.close()


@pytest.fixture(scope="module")
def redis_client():
    """Create Redis client for seeding data."""
    # Use service name when running in container, localhost for local dev
    import os
    host = os.getenv("REDIS_HOST", "localhost")
    port = 6379 if host == "redis" else 16379
    client = Redis(host=host, port=port, decode_responses=True)
    
    # Wait for Redis to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            client.ping()
            break
        except Exception:
            if i == max_retries - 1:
                pytest.skip("Redis not available. Run: podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml up -d")
            time.sleep(1)
    
    yield client
    
    client.close()


@pytest.fixture
def grpc_channel():
    """Create gRPC channel to Context Service."""
    import os
    # Use service name when running in container, localhost for local dev
    host = os.getenv("CONTEXT_HOST", "localhost")
    port = 50054
    address = f"{host}:{port}"
    
    # Wait for service to be ready
    max_retries = 30
    channel = None
    
    for i in range(max_retries):
        try:
            channel = grpc.insecure_channel(address)
            grpc.channel_ready_future(channel).result(timeout=2)
            break
        except Exception:
            if channel:
                channel.close()
            if i == max_retries - 1:
                pytest.skip(f"Context Service not available at {address}. Run: podman-compose -f tests/e2e/services/context/docker-compose.e2e.yml up -d")
            time.sleep(1)
    
    yield channel
    channel.close()


@pytest.fixture
def context_stub(grpc_channel):
    """Create Context Service gRPC stub."""
    from services.context.gen import context_pb2_grpc
    return context_pb2_grpc.ContextServiceStub(grpc_channel)


# ============================================================================
# DATA SEEDING FIXTURES
# ============================================================================

@pytest.fixture
def seed_case_data(neo4j_client, redis_client):
    """Seed a complete case with decisions, subtasks, and planning data."""
    case_id = f"TEST-{int(time.time() * 1000) % 100000}"
    
    # Seed Neo4j graph
    with neo4j_client.session() as session:
        # Create Case node
        session.run("""
            CREATE (c:Case {
                id: $case_id,
                title: 'Test Case for E2E',
                description: 'E2E test case description',
                status: 'IN_PROGRESS',
                created_at: datetime(),
                created_by: 'test-system'
            })
        """, case_id=case_id)
        
        # Create PlanVersion node
        session.run("""
            MATCH (c:Case {id: $case_id})
            CREATE (p:PlanVersion {
                id: $plan_id,
                case_id: $case_id,
                version: 1,
                status: 'APPROVED',
                created_at: datetime()
            })
            CREATE (c)-[:HAS_PLAN]->(p)
        """, case_id=case_id, plan_id=f"PLAN-{case_id}")
        
        # Create Subtasks
        for i, role in enumerate(['DEV', 'QA', 'DEVOPS']):
            session.run("""
                MATCH (p:PlanVersion {id: $plan_id})
                CREATE (s:Subtask {
                    id: $subtask_id,
                    title: $title,
                    description: $description,
                    role: $role,
                    status: 'PENDING',
                    priority: $priority
                })
                CREATE (p)-[:HAS_SUBTASK]->(s)
            """, 
                plan_id=f"PLAN-{case_id}",
                subtask_id=f"{case_id}-TASK-{i+1}",
                title=f"{role} Task {i+1}",
                description=f"Test task for {role} role",
                role=role,
                priority=i+1
            )
        
        # Create Decisions
        session.run("""
            MATCH (p:PlanVersion {id: $plan_id})
            CREATE (d1:Decision {
                id: $dec1_id,
                title: 'Use PostgreSQL for database',
                rationale: 'Better performance and ACID compliance',
                status: 'APPROVED',
                decided_by: 'architect',
                decided_at: datetime()
            })
            CREATE (d2:Decision {
                id: $dec2_id,
                title: 'Use React for frontend',
                rationale: 'Component-based architecture',
                status: 'APPROVED',
                decided_by: 'architect',
                decided_at: datetime()
            })
            CREATE (p)-[:CONTAINS_DECISION]->(d1)
            CREATE (p)-[:CONTAINS_DECISION]->(d2)
            CREATE (d2)-[:DEPENDS_ON]->(d1)
        """, plan_id=f"PLAN-{case_id}", dec1_id=f"{case_id}-DEC-001", dec2_id=f"{case_id}-DEC-002")
        
        # Link decisions to subtasks
        session.run("""
            MATCH (d:Decision {id: $dec_id})
            MATCH (s:Subtask {id: $subtask_id})
            CREATE (d)-[:AFFECTS]->(s)
        """, dec_id=f"{case_id}-DEC-001", subtask_id=f"{case_id}-TASK-1")
    
    # Seed Redis cache
    # Case spec
    spec = {
        "case_id": case_id,
        "title": "Test Case for E2E",
        "description": "E2E test case description",
        "acceptance_criteria": ["Criterion 1", "Criterion 2"],
        "constraints": {"budget": "medium", "timeline": "2 weeks"},
        "requester_id": "test-user",
        "tags": ["test", "e2e"],
        "created_at_ms": int(time.time() * 1000)
    }
    redis_client.set(f"swe:case:{case_id}:spec", json.dumps(spec))
    
    # Plan draft
    plan_draft = {
        "plan_id": f"PLAN-{case_id}",
        "case_id": case_id,
        "version": 1,
        "status": "APPROVED",
        "author_id": "test-planner",
        "rationale": "Initial plan for test case",
        "subtasks": [
            {
                "subtask_id": f"{case_id}-TASK-1",
                "title": "DEV Task 1",
                "description": "Test task for DEV role",
                "role": "DEV",
                "suggested_tech": ["Python", "FastAPI"],
                "depends_on": [],
                "estimate_points": 3.0,
                "priority": 1,
                "risk_score": 0.3,
                "notes": "High priority task"
            },
            {
                "subtask_id": f"{case_id}-TASK-2",
                "title": "QA Task 2",
                "description": "Test task for QA role",
                "role": "QA",
                "suggested_tech": ["pytest", "testcontainers"],
                "depends_on": [f"{case_id}-TASK-1"],
                "estimate_points": 2.0,
                "priority": 2,
                "risk_score": 0.2,
                "notes": ""
            },
            {
                "subtask_id": f"{case_id}-TASK-3",
                "title": "DEVOPS Task 3",
                "description": "Test task for DEVOPS role",
                "role": "DEVOPS",
                "suggested_tech": ["Docker", "Kubernetes"],
                "depends_on": [f"{case_id}-TASK-1"],
                "estimate_points": 4.0,
                "priority": 3,
                "risk_score": 0.4,
                "notes": ""
            }
        ],
        "created_at_ms": int(time.time() * 1000)
    }
    redis_client.set(f"swe:case:{case_id}:planning:draft", json.dumps(plan_draft))
    
    # Planning events stream
    stream_key = f"swe:case:{case_id}:planning:stream"
    events = [
        {
            "event": "create_case_spec",
            "actor": "test-user",
            "ts": str(int(time.time() * 1000) - 10000),
            "payload": json.dumps({"case_id": case_id})
        },
        {
            "event": "propose_plan",
            "actor": "test-planner",
            "ts": str(int(time.time() * 1000) - 5000),
            "payload": json.dumps({"plan_id": f"PLAN-{case_id}", "version": 1})
        },
        {
            "event": "approve_plan",
            "actor": "test-po",
            "ts": str(int(time.time() * 1000)),
            "payload": json.dumps({"plan_id": f"PLAN-{case_id}", "approved": True})
        }
    ]
    
    for event in events:
        redis_client.xadd(stream_key, event)
    
    yield case_id
    
    # Cleanup Neo4j
    with neo4j_client.session() as session:
        session.run("MATCH (n) WHERE n.id STARTS WITH $prefix DETACH DELETE n", prefix=case_id)
    
    # Cleanup Redis
    redis_client.delete(f"swe:case:{case_id}:spec")
    redis_client.delete(f"swe:case:{case_id}:planning:draft")
    redis_client.delete(f"swe:case:{case_id}:planning:stream")


@pytest.fixture
def empty_case_id():
    """Provide a case ID that doesn't exist (for error testing)."""
    return "NONEXISTENT-999"
