"""E2E tests for Context Service persistence.

Tests verify that UpdateContext RPC correctly persists changes to Neo4j.
Requires full infrastructure (Neo4j, Redis, NATS, Context Service).
"""

import json
import time

import pytest

from services.context.gen import context_pb2

pytestmark = pytest.mark.integration


class TestDecisionPersistenceE2E:
    """E2E tests for decision persistence via UpdateContext."""
    
    def test_create_decision_persists_to_neo4j(
        self, context_stub, seed_case_data, neo4j_client
    ):
        """Test that creating a decision via UpdateContext persists to Neo4j."""
        case_id = seed_case_data
        decision_id = f"{case_id}-DEC-NEW-001"
        
        # Create decision via UpdateContext
        request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="TASK-001",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=decision_id,
                    payload=json.dumps({
                        "title": "Use Kubernetes for deployment",
                        "rationale": "Better orchestration and scaling",
                        "status": "PROPOSED",
                        "decided_by": "architect-agent"
                    }),
                    reason="Deployment strategy decision"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(request)
        
        # Verify response
        assert response is not None
        assert response.version > 0
        
        # Give Neo4j a moment to persist
        time.sleep(0.5)
        
        # Verify decision was persisted to Neo4j
        with neo4j_client.session() as session:
            result = session.run("""
                MATCH (d:Decision {id: $decision_id})
                RETURN d.id as id, d.title as title, d.status as status,
                       d.rationale as rationale, d.decided_by as decided_by
            """, decision_id=decision_id)
            
            record = result.single()
            assert record is not None, f"Decision {decision_id} not found in Neo4j"
            assert record["id"] == decision_id
            assert record["title"] == "Use Kubernetes for deployment"
            assert record["status"] == "PROPOSED"
            assert record["rationale"] == "Better orchestration and scaling"
            assert record["decided_by"] == "architect-agent"
    
    def test_update_decision_persists_to_neo4j(
        self, context_stub, seed_case_data, neo4j_client
    ):
        """Test that updating a decision via UpdateContext persists to Neo4j."""
        case_id = seed_case_data
        
        # Use one of the seeded decisions
        decision_id = f"{case_id}-DEC-001"
        
        # Update decision via UpdateContext
        request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="TASK-001",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="DECISION",
                    entity_id=decision_id,
                    payload=json.dumps({
                        "status": "APPROVED",
                        "approved_by": "tech-lead",
                        "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }),
                    reason="Decision approved after review"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(request)
        assert response is not None
        
        # Give Neo4j a moment to persist
        time.sleep(0.5)
        
        # Verify decision was updated in Neo4j
        with neo4j_client.session() as session:
            result = session.run("""
                MATCH (d:Decision {id: $decision_id})
                RETURN d.status as status, d.approved_by as approved_by
            """, decision_id=decision_id)
            
            record = result.single()
            assert record is not None
            assert record["status"] == "APPROVED"
            assert record["approved_by"] == "tech-lead"
    
    def test_delete_decision_marks_as_deleted(
        self, context_stub, seed_case_data, neo4j_client
    ):
        """Test that deleting a decision marks it as DELETED in Neo4j."""
        case_id = seed_case_data
        decision_id = f"{case_id}-DEC-002"
        
        # Delete decision via UpdateContext
        request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="TASK-001",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="DELETE",
                    entity_type="DECISION",
                    entity_id=decision_id,
                    payload=json.dumps({}),
                    reason="Decision superseded by new architecture"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(request)
        assert response is not None
        
        # Give Neo4j a moment to persist
        time.sleep(0.5)
        
        # Verify decision is marked as DELETED (soft delete)
        with neo4j_client.session() as session:
            result = session.run("""
                MATCH (d:Decision {id: $decision_id})
                RETURN d.id as id, d.status as status
            """, decision_id=decision_id)
            
            record = result.single()
            assert record is not None, "Decision should still exist (soft delete)"
            assert record["status"] == "DELETED"


class TestSubtaskPersistenceE2E:
    """E2E tests for subtask persistence via UpdateContext."""
    
    def test_update_subtask_persists_to_neo4j(
        self, context_stub, seed_case_data, neo4j_client
    ):
        """Test that updating a subtask via UpdateContext persists to Neo4j."""
        case_id = seed_case_data
        subtask_id = f"{case_id}-TASK-1"
        
        # Update subtask via UpdateContext
        request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id=subtask_id,
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="SUBTASK",
                    entity_id=subtask_id,
                    payload=json.dumps({
                        "status": "IN_PROGRESS",
                        "assignee": "dev-agent-42",
                        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }),
                    reason="Subtask picked up by agent"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(request)
        assert response is not None
        
        # Give Neo4j a moment to persist
        time.sleep(0.5)
        
        # Verify subtask was updated in Neo4j
        with neo4j_client.session() as session:
            result = session.run("""
                MATCH (s:Subtask {id: $subtask_id})
                RETURN s.status as status, s.assignee as assignee
            """, subtask_id=subtask_id)
            
            record = result.single()
            assert record is not None
            assert record["status"] == "IN_PROGRESS"
            assert record["assignee"] == "dev-agent-42"


class TestMilestonePersistenceE2E:
    """E2E tests for milestone persistence via UpdateContext."""
    
    def test_create_milestone_persists_to_neo4j(
        self, context_stub, seed_case_data, neo4j_client
    ):
        """Test that creating a milestone via UpdateContext persists to Neo4j."""
        case_id = seed_case_data
        event_id = f"{case_id}-MILESTONE-001"
        
        # Create milestone via UpdateContext
        request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="TASK-001",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="MILESTONE",
                    entity_id=event_id,
                    payload=json.dumps({
                        "event_type": "task_completed",
                        "description": "First DEV task completed successfully",
                        "actor": "dev-agent-42"
                    }),
                    reason="Recording task completion"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(request)
        assert response is not None
        
        # Give Neo4j a moment to persist
        time.sleep(0.5)
        
        # Verify milestone was persisted to Neo4j
        with neo4j_client.session() as session:
            result = session.run("""
                MATCH (e:Event {id: $event_id})
                RETURN e.id as id, e.event_type as event_type,
                       e.description as description, e.case_id as case_id,
                       e.timestamp_ms as timestamp_ms
            """, event_id=event_id)
            
            record = result.single()
            assert record is not None, f"Event {event_id} not found in Neo4j"
            assert record["id"] == event_id
            assert record["event_type"] == "task_completed"
            assert record["description"] == "First DEV task completed successfully"
            assert record["case_id"] == case_id
            assert record["timestamp_ms"] > 0


class TestMultipleChangesPersistence:
    """E2E tests for multiple changes in single UpdateContext call."""
    
    def test_multiple_changes_all_persist(
        self, context_stub, seed_case_data, neo4j_client
    ):
        """Test that multiple changes in one request all persist correctly."""
        case_id = seed_case_data
        decision_id = f"{case_id}-DEC-MULTI-001"
        subtask_id = f"{case_id}-TASK-1"
        event_id = f"{case_id}-EVENT-MULTI-001"
        
        # Send multiple changes in one request
        request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="TASK-001",
            role="DEV",
            changes=[
                # Create a decision
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=decision_id,
                    payload=json.dumps({
                        "title": "Use FastAPI for API",
                        "status": "PROPOSED"
                    }),
                    reason="Tech stack decision"
                ),
                # Update a subtask
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="SUBTASK",
                    entity_id=subtask_id,
                    payload=json.dumps({
                        "status": "COMPLETED"
                    }),
                    reason="Task finished"
                ),
                # Create a milestone
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="MILESTONE",
                    entity_id=event_id,
                    payload=json.dumps({
                        "event_type": "batch_update",
                        "description": "Multiple context changes applied"
                    }),
                    reason="Batch update"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(request)
        assert response is not None
        assert len(response.warnings) == 0
        
        # Give Neo4j time to persist all changes
        time.sleep(0.8)
        
        # Verify decision was created
        with neo4j_client.session() as session:
            result = session.run("""
                MATCH (d:Decision {id: $decision_id})
                RETURN d.title as title
            """, decision_id=decision_id)
            record = result.single()
            assert record is not None
            assert record["title"] == "Use FastAPI for API"
        
        # Verify subtask was updated
        with neo4j_client.session() as session:
            result = session.run("""
                MATCH (s:Subtask {id: $subtask_id})
                RETURN s.status as status
            """, subtask_id=subtask_id)
            record = result.single()
            assert record is not None
            assert record["status"] == "COMPLETED"
        
        # Verify milestone was created
        with neo4j_client.session() as session:
            result = session.run("""
                MATCH (e:Event {id: $event_id})
                RETURN e.event_type as event_type
            """, event_id=event_id)
            record = result.single()
            assert record is not None
            assert record["event_type"] == "batch_update"


class TestPersistenceErrorHandling:
    """E2E tests for error handling in persistence."""
    
    def test_invalid_json_payload_does_not_crash(
        self, context_stub, seed_case_data
    ):
        """Test that invalid JSON payload is handled gracefully."""
        case_id = seed_case_data
        
        # Send request with invalid JSON
        request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="TASK-001",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=f"{case_id}-DEC-BAD",
                    payload="{ invalid json ::::",
                    reason="Testing error handling"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        # Should not crash, but may return warning
        response = context_stub.UpdateContext(request)
        assert response is not None
        # Service should continue to function
        assert response.version > 0

